"""Auditoria DWG x modelo: caixas (CA/PVP) e trechos de conduto sem tubo. Saida: work/audit.json"""
import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,csv,math,json,re,collections
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
X0,X1,Y0,Y1=-90,110,-125,75
def L(p): return (p[0]-561500,p[1]-8658000)
inb=lambda p: X0<p[0]<X1 and Y0<p[1]<Y1
fix=list(csv.reader(open('work/revit_pipes_fix.csv'),delimiter=';'))
pipes=[(float(r[1]),float(r[2]),float(r[4]),float(r[5]),r[7],int(r[0])) for r in fix]
bx=list(csv.reader(open('work/revit_boxes.csv'),delimiter=';'))
# caixas do modelo apos dedupe (as duplicatas/PV falsos serao apagados)
keep=[];drop=[]
for b in bx:
    p=(float(b[2]),float(b[3]))
    if any(math.dist(p,(float(k[2]),float(k[3])))<0.3 for k in keep): drop.append(b); continue
    keep.append(b)
fakes=[b for b in keep if b[0]=='PV' and any(k is not b and k[0]!='PV' and math.dist((float(b[2]),float(b[3])),(float(k[2]),float(k[3])))<2.0 for k in keep)]
for f in fakes: keep.remove(f); drop.append(f)
# simbolos DWG
sym=[('CA',L(e[3])) for e in E if e[0]=='MTEXT' and e[1]=='Simbolos' and e[5]=='CA']
sym+=[('PVP',L(e[3])) for e in E if e[0]=='INSERT' and e[5]=='zw$12D9']
sym=[s for s in sym if inb(s[1])]
T=[e for e in E if e[0]=='MTEXT' and e[1]=='TQ-Textos conduto']
def val(s):
    m=re.search(r'([\d.]+)',s.split(':')[-1]); return float(m.group(1)) if m else None
CT=[(L(t[3]),val(t[5])) for t in T if t[5].startswith('CT')]; CF=[(L(t[3]),val(t[5])) for t in T if t[5].startswith('CF')]
def near(lst,p,r):
    c=[(math.dist(p,q),v) for q,v in lst if math.dist(p,q)<r]; return min(c)[1] if c else None
miss_box=[]
for k,p in sym:
    d=min((math.dist(p,(float(b[2]),float(b[3]))) for b in keep),default=99)
    if d>1.2:
        # pipes passando perto?
        dp=min(math.hypot(*(0,0)) for _ in [0])
        miss_box.append({'tipo':k,'x':p[0],'y':p[1],'ct':near(CT,p,6),'cf':near(CF,p,6),'dist_caixa_modelo':round(d,1)})
# trechos sem tubo: usa pares de parede (P) como eixos candidatos
def dseg(px,py,ax,ay,bx_,by):
    dx,dy=bx_-ax,by-ay; n2=dx*dx+dy*dy
    t=0 if n2==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/n2)); return math.hypot(px-ax-t*dx,py-ay-t*dy)
R,nom=pickle.load(open('work/runs.pkl','rb')); left=pickle.load(open('work/left.pkl','rb'))
cands=[(L(r['p0']),L(r['p1']),r['d']) for r in R]+[(L(p['g'][0]),L(p['g'][1]),p['d']) for p in left]
cands+=[(L(m[0]),L(m[-1]),None) for m in ml]
# todos os pares (P) tambem, para pegar o que runs/left perderam
cands+=[(L(p['g'][0]),L(p['g'][1]),p['d']) for p in P if p['len']>1.5 and p['d']<=0.42]
unc=[]
for a,b,dd in cands:
    if not (inb(a) and inb(b)): continue
    Lg=math.dist(a,b)
    if Lg<1.5: continue
    n=max(3,int(Lg/0.5)); bad=[]
    near_p=[q for q in pipes if min(q[0],q[2])-2<max(a[0],b[0]) and max(q[0],q[2])+2>min(a[0],b[0]) and min(q[1],q[3])-2<max(a[1],b[1]) and max(q[1],q[3])+2>min(a[1],b[1])]
    for k in range(n+1):
        px=a[0]+(b[0]-a[0])*k/n; py=a[1]+(b[1]-a[1])*k/n
        dmin=min((dseg(px,py,*q[:4]) for q in near_p),default=99)
        bad.append(dmin>0.35)
    # maior sequencia continua sem tubo
    best=cur=0;bs=be=0;s0=0
    for k,v in enumerate(bad):
        if v:
            if cur==0: s0=k
            cur+=1
            if cur>best: best=cur;bs=s0;be=k
        else: cur=0
    lenu=best/n*Lg
    if lenu>=1.5:
        pa=(a[0]+(b[0]-a[0])*bs/n,a[1]+(b[1]-a[1])*bs/n); pb=(a[0]+(b[0]-a[0])*be/n,a[1]+(b[1]-a[1])*be/n)
        unc.append({'a':pa,'b':pb,'L':round(lenu,1),'d':dd})
# dedupe colineares sobrepostos
out=[]
for u in sorted(unc,key=lambda u:-u['L']):
    m=((u['a'][0]+u['b'][0])/2,(u['a'][1]+u['b'][1])/2)
    if any(dseg(m[0],m[1],*o['a'],*o['b'])<0.4 for o in out): continue
    out.append(u)
json.dump({'drop':drop,'keep':len(keep),'miss_box':miss_box,'miss_pipe':out},open('work/audit.json','w'),indent=1,default=float)
print('caixas modelo',len(bx),'-> apagar',len(drop),'(dup',len(drop)-len(fakes),'PV falso',len(fakes),') ficam',len(keep))
print('simbolos DWG na planta',len(sym),collections.Counter(k for k,_ in sym),' caixas faltando',len(miss_box))
for m in miss_box: print('  ',m)
print('trechos sem tubo >=1,5 m:',len(out),'total',round(sum(u['L'] for u in out),1),'m')
for u in out: print('   L=%.1f d=%s (%.1f,%.1f)-(%.1f,%.1f)'%(u['L'],u['d'] and round(u['d'],2),*u['a'],*u['b']))
