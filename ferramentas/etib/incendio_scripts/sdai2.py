import json, math, numpy as np
R=json.load(open('sdai_raw.json'))
polys=[[tuple(v) for v in p] for p in R['polys'] if max(q[0] for q in p)<110]
boxes=R['boxes']; NUM=R['num']
LEG={1:'L01-L06+24Vcc',2:'L03-L06+24Vcc',3:'L05,L06+24Vcc',4:'L06+24Vcc',5:'L06+24Vcc',6:'L01+24Vcc',7:'L02+24Vcc',8:'L03+24Vcc',9:'L03+24Vcc',10:'L04+24Vcc',11:'L05+24Vcc'}
def proj(p,a,b):
    a,b,p=map(np.array,(a,b,p)); ab=b-a; L2=float(np.dot(ab,ab))
    if L2<1e-12: return float(np.linalg.norm(p-a)),0.0,tuple(a)
    t=float(np.clip(np.dot(p-a,ab)/L2,0,1)); q=a+t*ab; return float(np.linalg.norm(p-q)),t,tuple(q)
TOL=0.6
# 1) pontas sobre outras polilinhas -> tê
for it in range(50):
    ch=False
    for i,P in enumerate(polys):
        for k in (0,-1):
            p=P[k]
            for j,Q in enumerate(polys):
                if j==i: continue
                for s in range(len(Q)-1):
                    dd,t,q=proj(p,Q[s],Q[s+1])
                    if dd<TOL:
                        if math.dist(q,Q[s])<TOL: q=Q[s]
                        elif math.dist(q,Q[s+1])<TOL: q=Q[s+1]
                        else: Q.insert(s+1,q); ch=True
                        if P[k]!=q: P[k]=q; ch=True
                        break
                if ch: break
            if ch: break
        if ch: break
    if not ch: break
# 2) caixas: projeta centro na polilinha mais próxima e insere vértice
bnodes=[]
for b in boxes:
    best=None
    for j,Q in enumerate(polys):
        for s in range(len(Q)-1):
            dd,t,q=proj(b['c'],Q[s],Q[s+1])
            if best is None or dd<best[0]: best=(dd,j,s,q)
    dd,j,s,q=best; Q=polys[j]
    if math.dist(q,Q[s])<0.3: q=Q[s]
    elif math.dist(q,Q[s+1])<0.3: q=Q[s+1]
    else: Q.insert(s+1,q)
    # todas as polilinhas que passam pelo mesmo ponto usam o mesmo q
    bnodes.append(dict(c=q,w=b['w'],r=b['r'],dist=dd))
print('caixas projetadas, desvio máx %.2f m'%max(b['dist'] for b in bnodes))
key=lambda p:(round(float(p[0]),3),round(float(p[1]),3))
adj={}
for P in polys:
    for a,b in zip(P,P[1:]):
        if math.dist(a,b)<1e-3: continue
        adj.setdefault(key(a),set()).add(key(b)); adj.setdefault(key(b),set()).add(key(a))
bset={key(b['c']) for b in bnodes}
deg={k:len(v) for k,v in adj.items()}
stops=[k for k in adj if deg[k]!=2 or k in bset]
seen=set(); runs=[]
for n in stops:
    for m in adj[n]:
        if (n,m) in seen: continue
        path=[n,m]; seen.add((n,m)); seen.add((m,n))
        while path[-1] not in stops:
            nx=[z for z in adj[path[-1]] if z!=path[-2]][0]; seen.add((path[-1],nx)); seen.add((nx,path[-1])); path.append(nx)
        runs.append(path)
out=[]
for i,r in enumerate(runs):
    L=sum(math.dist(r[k],r[k+1]) for k in range(len(r)-1))
    # laço: número circulado mais próximo do trecho
    best=(9e9,None)
    for x,y,n in NUM:
        for k in range(len(r)-1):
            dd,_,_=proj((x,y),r[k],r[k+1])
            if dd<best[0]: best=(dd,n)
    n=best[1] if best[0]<2.0 else None
    out.append(dict(id=f'S{i+1:02d}',pts=[list(p) for p in r],L=L,num=n,laco=LEG.get(n,'?'),dnum=best[0]))
    print(f'S{i+1:02d}',r[0],'->',r[-1],'L=%.1f'%L,'nº',n,LEG.get(n,'?'),'(dist %.2f)'%best[0])
print('total %.1f m'%sum(o['L'] for o in out))
json.dump({'runs':out,'boxes':[dict(c=list(b['c']),w=b['w'],r=b['r']) for b in bnodes]},open('sdai_runs.json','w'))
# pontos de terreno
pts={}
for o in out:
    r=o['pts']
    for a,b in zip(r,r[1:]):
        Ln=math.dist(a,b); n=max(1,int(math.ceil(Ln/0.5)))
        for k in range(n+1): t=k/n; pts[(round(a[0]+(b[0]-a[0])*t,3),round(a[1]+(b[1]-a[1])*t,3))]=1
for b in bnodes:
    for dx in (-0.34,0,0.34):
        for dy in (-0.34,0,0.34): pts[(round(b['c'][0]+dx,3),round(b['c'][1]+dy,3))]=1
open('terrain_pts_sdai.txt','w').write('\n'.join(f'{x:.3f};{y:.3f}' for x,y in pts)); print('pontos de terreno',len(pts))
