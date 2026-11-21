import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work')
from load import *
import math,collections,numpy as np
E=parse(load())
segs=[]
for e in E:
    if e[1]!='AP-Condutos': continue
    if e[0]=='LINE': pts=e[3]
    elif e[0]=='LWPOLYLINE': pts=e[3]
    else: continue
    for i in range(len(pts)-1):
        a,b=pts[i],pts[i+1]
        if math.dist(a,b)>=0.25: segs.append((a,b,e[0],e[2]))
print('segs',len(segs))
def ang(s):
    (x1,y1),(x2,y2)=s[0],s[1]; return math.atan2(y2-y1,x2-x1)%math.pi
A=np.array([ang(s) for s in segs])
cands=[]
for i,s in enumerate(segs):
    (x1,y1),(x2,y2)=s[0],s[1]; dx,dy=x2-x1,y2-y1; n=math.hypot(dx,dy); ux,uy=dx/n,dy/n
    for j in range(i+1,len(segs)):
        da=abs(A[i]-A[j]); da=min(da,math.pi-da)
        if da>0.006: continue
        t=segs[j]
        # perpendicular distance of t endpoints to line s
        d1=(-(t[0][0]-x1)*uy+(t[0][1]-y1)*ux); d2=(-(t[1][0]-x1)*uy+(t[1][1]-y1)*ux)
        d=(d1+d2)/2
        if abs(d)>0.45 or abs(d)<0.005: continue
        # overlap along s
        p1=(t[0][0]-x1)*ux+(t[0][1]-y1)*uy; p2=(t[1][0]-x1)*ux+(t[1][1]-y1)*uy
        lo=max(0,min(p1,p2)); hi=min(n,max(p1,p2))
        if hi-lo<0.2: continue
        cands.append((i,j,abs(d),hi-lo))
print('cands',len(cands))
h=collections.Counter(round(c[2]*200)/200 for c in cands)
for k,v in sorted(h.items()): print(k,v)

# ---- centerlines from pairs
def cl(i,j):
    s,t=segs[i],segs[j]; (x1,y1),(x2,y2)=s[0],s[1]; dx,dy=x2-x1,y2-y1; n=math.hypot(dx,dy); ux,uy=dx/n,dy/n
    p1=(t[0][0]-x1)*ux+(t[0][1]-y1)*uy; p2=(t[1][0]-x1)*ux+(t[1][1]-y1)*uy
    lo=max(0,min(p1,p2)); hi=min(n,max(p1,p2))
    # perpendicular offset of t relative to s (signed, avg of endpoints)
    d1=(-(t[0][0]-x1)*uy+(t[0][1]-y1)*ux); d2=(-(t[1][0]-x1)*uy+(t[1][1]-y1)*ux); d=(d1+d2)/2
    # midline: s shifted by d/2 perpendicular (normal = (-uy,ux))
    ox,oy=-uy*d/2,ux*d/2
    return ((x1+ux*lo+ox,y1+uy*lo+oy),(x1+ux*hi+ox,y1+uy*hi+oy)),abs(d)
CL=[]
for i,j,d,ov in cands:
    if 0.03<=d<=0.45:
        g,dd=cl(i,j); CL.append((g,dd,i,j))
print('CL',len(CL))
arrows=[e for e in E if e[1]=='AP-Sentido conduto' and e[0]=='LWPOLYLINE']
AR=[((e[3][0][0]+e[3][-1][0])/2,(e[3][0][1]+e[3][-1][1])/2,e[3][0],e[3][-1],e[2]) for e in arrows if len(e[3])==2]
print('arrows',len(AR))
