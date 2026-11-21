import json, numpy as np, math
R=json.load(open('inc_runs.json'))['runs']
TZ=np.array([[float(v) for v in l.split(';')] for l in open('terrain_z.txt')])
def terr(p):
    d=np.hypot(TZ[:,0]-p[0],TZ[:,1]-p[1]); i=np.argsort(d)[:3]
    if d[i[0]]<1e-3: return float(TZ[i[0],2])
    w=1/d[i]**2; return float((TZ[i,2]*w).sum()/w.sum())
V1=[(-22,33),(17,33),(18,36.6),(86.5,46.3),(87.2,47.5),(92,70),(-22,70)]
def inpoly(p,poly):
    x,y=p; c=False
    for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]):
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
def cover(p): return 0.60 if inpoly(p,V1) else 0.50
def zreq(p,de): return terr(p)-cover(p)-de/2000.0   # cota do eixo
key=lambda p:(round(p[0],3),round(p[1],3))
EPS=0.20; MINL=2.0
def dp(s,z,i0,i1,out):
    if i1<=i0+1: return
    line=z[i0]+(z[i1]-z[i0])*(s[i0+1:i1]-s[i0])/(s[i1]-s[i0])
    dev=np.abs(z[i0+1:i1]-line); k=int(np.argmax(dev))+i0+1
    if dev.max()>EPS and s[k]-s[i0]>=MINL and s[i1]-s[k]>=MINL:
        dp(s,z,i0,k,out); out.append(k); dp(s,z,k,i1,out)
SPLIT=(97.916,-3.781)
legs=[]
for ri,r in enumerate(R):
    big=False
    for k,(a,b) in enumerate(zip(r,r[1:])):
        de=75
        if ri==4:  # T05: depois de SPLIT é o trecho de 3"
            if big: de=85
            if math.dist(b,SPLIT)<0.01: big=True
        a=np.array(a);b=np.array(b);Ln=np.linalg.norm(b-a)
        n=max(2,int(np.ceil(Ln/0.5))+1); s=np.linspace(0,Ln,n); P=[a+(b-a)*t/Ln for t in s]
        z=np.array([zreq(p,de) for p in P]); ks=[]; dp(s,z,0,n-1,ks); idx=[0]+sorted(ks)+[n-1]
        for i0,i1 in zip(idx,idx[1:]):
            legs.append(dict(run=f'T{ri+1:02d}',d=de,a=[float(P[i0][0]),float(P[i0][1])],b=[float(P[i1][0]),float(P[i1][1])]))
Z={}
for L in legs:
    for p in (L['a'],L['b']): Z[key(p)]=min(Z.get(key(p),1e9),zreq(p,L['d']))
for it in range(300):
    ch=False
    for L in legs:
        a=np.array(L['a']);b=np.array(L['b']);n=max(2,int(np.ceil(np.linalg.norm(b-a)/0.5))+1)
        za,zb=Z[key(L['a'])],Z[key(L['b'])]; viol=0;tv=0
        for t in np.linspace(0,1,n):
            v=(za+(zb-za)*t)-zreq(a+(b-a)*t,L['d'])
            if v>viol: viol=v;tv=t
        if viol>1e-4:
            if tv<0.5: Z[key(L['a'])]-=viol/(1-tv)
            else: Z[key(L['b'])]-=viol/tv
            ch=True
    if not ch: break
cmax=0; cmin=9
for r in sorted(set(L['run'] for L in legs)):
    for i,L in enumerate([M for M in legs if M['run']==r]): L['leg']=i+1
for L in legs:
    a=np.array(L['a']);b=np.array(L['b']);za,zb=Z[key(L['a'])],Z[key(L['b'])]
    n=max(2,int(np.ceil(np.linalg.norm(b-a)/0.5))+1); cov=[]
    for t in np.linspace(0,1,n):
        p=a+(b-a)*t; cov.append(terr(p)-(za+(zb-za)*t+L['d']/2000.0))
    L.update(za=float(za),zb=float(zb),cov_min=float(min(cov)),cov_max=float(max(cov)),cov_req=cover(L['a']),ta=terr(L['a']),tb=terr(L['b']),length=float(np.linalg.norm(b-a)))
    cmax=max(cmax,L['cov_max']); cmin=min(cmin,L['cov_min'])
json.dump(legs,open('inc_legs.json','w'),indent=0)
print('iterações',it,'| trechos retos',len(legs),'| recobrimento mín %.3f máx %.3f'%(cmin,cmax))
print('comprimento DE75 %.1f m | DE85 %.1f m'%(sum(L['length'] for L in legs if L['d']==75),sum(L['length'] for L in legs if L['d']==85)))
print('terreno na rede: %.2f a %.2f'%(min(min(L['ta'],L['tb']) for L in legs),max(max(L['ta'],L['tb']) for L in legs)))
