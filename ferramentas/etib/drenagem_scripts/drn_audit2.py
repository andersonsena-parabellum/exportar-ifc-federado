"""Auditoria rigorosa: toda parede de conduto (AP-Condutos) precisa de um tubo PARALELO a <= 0,30 m. Paredes descobertas -> pares -> tubos faltantes."""
import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,csv,math,json,collections
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
L=lambda p:(p[0]-561500,p[1]-8658000)
X0,X1,Y0,Y1=-90,110,-125,75
fix=list(csv.reader(open('work/revit_pipes_fix.csv'),delimiter=';'))
pipes=[(float(r[1]),float(r[2]),float(r[4]),float(r[5])) for r in fix if r[0]!='378']
for r in csv.reader(open('work/new_pipes.csv',encoding='utf-8'),delimiter=';'): pipes.append((float(r[3]),float(r[4]),float(r[6]),float(r[7])))
def ang(a,b): return math.atan2(b[1]-a[1],b[0]-a[0])%math.pi
def dseg(px,py,ax,ay,bx,by):
    dx,dy=bx-ax,by-ay; n2=dx*dx+dy*dy
    t=0 if n2==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/n2)); return math.hypot(px-ax-t*dx,py-ay-t*dy)
PA=[(p,ang(p[:2],p[2:])) for p in pipes]
walls=[]
for e in E:
    if e[1]=='AP-Condutos' and e[0] in('LINE','LWPOLYLINE'):
        pts=[L(q) for q in e[3]]
        for a,b in zip(pts,pts[1:]):
            if math.dist(a,b)>=0.3 and X0<a[0]<X1 and Y0<a[1]<Y1: walls.append((a,b))
unc=[]
for a,b in walls:
    aw=ang(a,b); Lg=math.dist(a,b); n=max(2,int(Lg/0.4)); bad=0
    cand=[p for p,ap in PA if min(abs(ap-aw),math.pi-abs(ap-aw))<0.18 and min(p[0],p[2])-1<max(a[0],b[0]) and max(p[0],p[2])+1>min(a[0],b[0]) and min(p[1],p[3])-1<max(a[1],b[1]) and max(p[1],p[3])+1>min(a[1],b[1])]
    for k in range(n+1):
        x=a[0]+(b[0]-a[0])*k/n; y=a[1]+(b[1]-a[1])*k/n
        if min((dseg(x,y,*p) for p in cand),default=9)>0.30: bad+=1
    if bad>(n+1)*0.6: unc.append((a,b))
print('paredes',len(walls),'descobertas',len(unc),'comprimento %.0f m'%sum(math.dist(a,b) for a,b in unc))
# parear paredes descobertas
U=unc; used=set(); miss=[]
for i,(a,b) in enumerate(U):
    if i in used: continue
    aw=ang(a,b); ux,uy=math.cos(aw),math.sin(aw); nx,ny=-uy,ux
    best=None
    for j,(c,d) in enumerate(U):
        if j==i or j in used: continue
        if min(abs(ang(c,d)-aw),math.pi-abs(ang(c,d)-aw))>0.03: continue
        off=((c[0]-a[0])*nx+(c[1]-a[1])*ny+(d[0]-a[0])*nx+(d[1]-a[1])*ny)/2
        if not(0.02<abs(off)<0.45): continue
        pa=lambda p:(p[0]-a[0])*ux+(p[1]-a[1])*uy
        lo=max(min(pa(a),pa(b)),min(pa(c),pa(d))); hi=min(max(pa(a),pa(b)),max(pa(c),pa(d)))
        if hi-lo<0.3: continue
        if best is None or abs(off)<abs(best[0]): best=(off,j,lo,hi)
    if best:
        off,j,lo,hi=best; used.add(i); used.add(j)
        ox,oy=nx*off/2,ny*off/2
        p0=(a[0]+ux*lo+ox,a[1]+uy*lo+oy); p1=(a[0]+ux*hi+ox,a[1]+uy*hi+oy)
        miss.append({'a':p0,'b':p1,'d':abs(off),'L':hi-lo})
# unir colineares contiguos
miss.sort(key=lambda m:-m['L'])
print('tubos faltantes (pares):',len(miss),'comprimento %.0f m'%sum(m['L'] for m in miss))
by=collections.Counter(round(m['d'],2) for m in miss); print(by.most_common(10))
json.dump(miss,open('work/miss2.json','w'))
sol=[(a,b) for i,(a,b) in enumerate(U) if i not in used]
print('paredes descobertas sem par:',len(sol),'%.0f m'%sum(math.dist(a,b) for a,b in sol))
json.dump(sol,open('work/miss2_solo.json','w'))
