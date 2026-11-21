import json, numpy as np, math
S=json.load(open('sdai_runs.json'))
TZ=np.array([[float(v) for v in l.split(';')] for l in open('terrain_z_sdai.txt')])
def terr(p):
    d=np.hypot(TZ[:,0]-p[0],TZ[:,1]-p[1]); i=np.argsort(d)[:3]
    if d[i[0]]<1e-3: return float(TZ[i[0],2])
    w=1/d[i]**2; return float((TZ[i,2]*w).sum()/w.sum())
OD=0.060; COV=0.50
NUMFIX={'S01':4,'S02':4,'S03':4,'S04':4,'S05':4,'S06':5,'S07':4,'S08':4,'S09':11,'S10':3,'S11':9,'S12':2,'S13':8,'S14':10,'S15':1,'S16':1,'S17':1,'S18':6,'S19':7,'S20':2,'S21':2,'S22':9,'S23':2}
LEG={1:'L01-L06+24Vcc',2:'L03-L06+24Vcc',3:'L05,L06+24Vcc',4:'L06+24Vcc',5:'L06+24Vcc',6:'L01+24Vcc',7:'L02+24Vcc',8:'L03+24Vcc',9:'L03+24Vcc',10:'L04+24Vcc',11:'L05+24Vcc'}
zreq=lambda p: terr(p)-COV-OD/2
key=lambda p:(round(p[0],3),round(p[1],3))
EPS=0.20; MINL=2.0
def dp(s,z,i0,i1,out):
    if i1<=i0+1: return
    line=z[i0]+(z[i1]-z[i0])*(s[i0+1:i1]-s[i0])/(s[i1]-s[i0]); dev=np.abs(z[i0+1:i1]-line); k=int(np.argmax(dev))+i0+1
    if dev.max()>EPS and s[k]-s[i0]>=MINL and s[i1]-s[k]>=MINL: dp(s,z,i0,k,out); out.append(k); dp(s,z,k,i1,out)
legs=[]
for r in S['runs']:
    for a,b in zip(r['pts'],r['pts'][1:]):
        a=np.array(a);b=np.array(b);Ln=np.linalg.norm(b-a); n=max(2,int(np.ceil(Ln/0.5))+1); s=np.linspace(0,Ln,n); P=[a+(b-a)*t/Ln for t in s]
        z=np.array([zreq(p) for p in P]); ks=[]; dp(s,z,0,n-1,ks); idx=[0]+sorted(ks)+[n-1]
        for i0,i1 in zip(idx,idx[1:]): legs.append(dict(run=r['id'],num=NUMFIX[r['id']],laco=LEG[NUMFIX[r['id']]],a=[float(P[i0][0]),float(P[i0][1])],b=[float(P[i1][0]),float(P[i1][1])]))
Z={}
for L in legs:
    for p in (L['a'],L['b']): Z[key(p)]=min(Z.get(key(p),1e9),zreq(p))
for it in range(300):
    ch=False
    for L in legs:
        a=np.array(L['a']);b=np.array(L['b']);n=max(2,int(np.ceil(np.linalg.norm(b-a)/0.5))+1); za,zb=Z[key(L['a'])],Z[key(L['b'])]; viol=0;tv=0
        for t in np.linspace(0,1,n):
            v=(za+(zb-za)*t)-zreq(a+(b-a)*t)
            if v>viol: viol=v;tv=t
        if viol>1e-4:
            if tv<0.5: Z[key(L['a'])]-=viol/(1-tv)
            else: Z[key(L['b'])]-=viol/tv
            ch=True
    if not ch: break
cm=9;cM=0
for L in legs:
    a=np.array(L['a']);b=np.array(L['b']);za,zb=Z[key(L['a'])],Z[key(L['b'])]; n=max(2,int(np.ceil(np.linalg.norm(b-a)/0.5))+1)
    cov=[terr(a+(b-a)*t)-(za+(zb-za)*t+OD/2) for t in np.linspace(0,1,n)]
    L.update(za=za,zb=zb,cov_min=min(cov),cov_max=max(cov),ta=terr(L['a']),tb=terr(L['b']),length=float(np.linalg.norm(b-a))); cm=min(cm,min(cov)); cM=max(cM,max(cov))
boxes=[]
for k,bx in enumerate(S['boxes']):
    c=bx['c']; zs=[Z[kk] for kk in Z if math.dist(kk,c)<0.01]
    zc=min(zs) if zs else zreq(c)
    tt=max(terr((c[0]+dx,c[1]+dy)) for dx in (-0.34,0,0.34) for dy in (-0.34,0,0.34))
    boxes.append(dict(id=f'CX{k+1:02d}',c=c,w=bx['w'],r=bx['r'],top=terr(c),bottom=zc-OD/2-0.10))
json.dump({'legs':legs,'boxes':boxes},open('sdai_legs.json','w'))
print('iterações',it,'| trechos',len(legs),'| recobrimento mín %.3f máx %.3f'%(cm,cM),'| L total %.1f m'%sum(L['length'] for L in legs))
for b in boxes: print(b['id'],[round(v,2) for v in b['c']],'topo %.2f fundo %.2f prof %.2f'%(b['top'],b['bottom'],b['top']-b['bottom']))
