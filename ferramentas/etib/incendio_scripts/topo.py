import json, math, numpy as np
d=json.load(open('in_geom.json',encoding='utf-8'))
H=[x for x in d if x['l'].startswith('HI-Condutos') and x['in'].startswith('24-049') and x['t']!='A']
polys=[]
for x in H:
    p=[tuple(q[:2]) for q in x['pts']]
    L=sum(math.dist(p[i],p[i+1]) for i in range(len(p)-1))
    if L>1.0: polys.append(p)
# remove vértices duplicados/colineares
def clean(p):
    q=[p[0]]
    for v in p[1:]:
        if math.dist(v,q[-1])>0.02: q.append(v)
    r=[q[0]]
    for i in range(1,len(q)-1):
        a,b,c=np.array(r[-1]),np.array(q[i]),np.array(q[i+1])
        u=b-a;w=c-b
        if abs(u[0]*w[1]-u[1]*w[0])/(np.linalg.norm(u)*np.linalg.norm(w))>math.sin(math.radians(1.0)): r.append(q[i])
    r.append(q[-1]); return r
polys=[clean(p) for p in polys]
TOL=0.6
print([ (round(P[0][0],3),round(P[0][1],3),round(P[-1][0],3),round(P[-1][1],3),len(P)) for P in polys])
# 1) junta pontas próximas de pontas (mesmo nó)
ends=[(i,0) for i in range(len(polys))]+[(i,-1) for i in range(len(polys))]
# 2) ponta sobre o interior de outra polilinha -> tê (insere vértice)
def proj(p,a,b):
    a,b,p=map(np.array,(a,b,p)); ab=b-a; t=np.clip(np.dot(p-a,ab)/np.dot(ab,ab),0,1); q=a+t*ab; return np.linalg.norm(p-q),t,tuple(q)
changed=True
while changed:
    changed=False
    for i,k in ends:
        p=polys[i][k]
        for j,P in enumerate(polys):
            if j==i: continue
            for s in range(len(P)-1):
                dd,t,q=proj(p,P[s],P[s+1])
                if dd<TOL:
                    # se q coincide com vértice existente de P, usa o vértice
                    if math.dist(q,P[s])<TOL: q=P[s]
                    elif math.dist(q,P[s+1])<TOL: q=P[s+1]
                    else:
                        P.insert(s+1,q); changed=True
                    if polys[i][k]!=q: polys[i][k]=q; changed=True
                    break
            if changed: break
        if changed: break
# elo de 0,37 m do DWG entre a quina do T16 e a quina do trecho leste
import itertools
c1=min((v for P in polys for v in P), key=lambda v: math.dist(v,(10.52,-0.38)))
c2=min((v for P in polys for v in P), key=lambda v: math.dist(v,(10.88,-0.30)))
print('elo',c1,c2,math.dist(c1,c2))
if math.dist(c1,c2)>0.01: polys.append([c1,c2])
# grafo
key=lambda p:(round(float(p[0]),3),round(float(p[1]),3))
adj={}
for P in polys:
    for a,b in zip(P,P[1:]):
        adj.setdefault(key(a),set()).add(key(b)); adj.setdefault(key(b),set()).add(key(a))
deg={k:len(v) for k,v in adj.items()}
nodes=[k for k,v in deg.items() if v!=2]
print('vértices',len(adj),'nós (grau!=2)',len(nodes))
for k in sorted(nodes): print(' ',k,'grau',deg[k])
# trechos entre nós
seen=set(); runs=[]
for n in nodes:
    for m in adj[n]:
        if (n,m) in seen: continue
        path=[n,m]; seen.add((n,m)); seen.add((m,n))
        while deg[path[-1]]==2:
            nx=[z for z in adj[path[-1]] if z!=path[-2]][0]
            seen.add((path[-1],nx)); seen.add((nx,path[-1])); path.append(nx)
        runs.append(path)
tot=0
for i,r in enumerate(runs):
    L=sum(math.dist(r[k],r[k+1]) for k in range(len(r)-1)); tot+=L
    print(f'T{i+1:02d}', r[0],'->',r[-1],'vértices',len(r),'L=%.2f'%L)
print('total %.1f m'%tot)
json.dump({'runs':[[list(p) for p in r] for r in runs],'deg':{f'{k[0]},{k[1]}':v for k,v in deg.items()}},open('inc_runs.json','w'))
