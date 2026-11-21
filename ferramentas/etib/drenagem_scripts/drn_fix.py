"""Fecha lacunas (une nos ligados por trechos minusculos, encosta pontas no no) e classifica interno/externo."""
import json,math,pickle,collections,csv,sys
sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
W='work/'
d=json.load(open(W+'network_drn.json'))
N={n['id']:n for n in d['nodes']}
E=d['edges']
nodes,edges0,boxes,segs3=pickle.load(open(W+'topo.pkl','rb'))
# union de nos por trechos minusculos removidos
par=list(range(len(nodes)))
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
nm=0
for e in edges0:
    if e['a']!=e['b'] and e['L']<0.35:
        a,b=f(e['a']),f(e['b'])
        if a!=b: par[a]=b; nm+=1
print('nos unidos por elos minusculos:',nm)
# alvo por grupo
ends=collections.defaultdict(list)
for i,e in enumerate(E):
    ends[f(e['a'])].append(e['p_up']); ends[f(e['b'])].append(e['p_dn'])
tgt={}
for g,pts in ends.items():
    members=[n for n in range(len(nodes)) if f(n)==g]
    bx=[n for n in members if nodes[n]['kind']=='box']
    if bx: tgt[g]=tuple(nodes[bx[0]]['pos'])
    else:
        if len(pts)>=2: tgt[g]=(sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts))
# floors -> poligonos (even-odd por laje)
fl=collections.defaultdict(list)
for l in open(W+'floors.csv',encoding='utf-8-sig'):
    c=l.strip().split(';'); fl[(c[0],c[1])].append((float(c[2]),float(c[3]),float(c[4]),float(c[5])))
def inside(x,y):
    for k,segs in fl.items():
        n=0
        for x1,y1,x2,y2 in segs:
            if (y1>y)!=(y2>y):
                xi=x1+(y-y1)*(x2-x1)/(y2-y1)
                if xi>x: n+=1
        if n%2==1: return True
    return False
rows=list(csv.reader(open(W+'revit_pipes.csv'),delimiter=';'))
byi={}
order=sorted(range(len(E)),key=lambda i:(round(-E[i]['p_up'][1]/20),E[i]['p_up'][0]))
idmap={E[i]['i']:k+1 for k,i in enumerate(order)}   # csv id por edge original
out=[]; moved=0; far=0; interno=0
for i,e in enumerate(E):
    pu=list(e['p_up']); pd=list(e['p_dn'])
    for key,node in (('u',e['a']),('d',e['b'])):
        g=f(node); t=tgt.get(g)
        if not t: continue
        p=pu if key=='u' else pd
        dist=math.dist(p,t)
        if dist>1.8: far+=1; continue
        if dist>0.02: moved+=1
        if key=='u': pu=list(t)
        else: pd=list(t)
    L=math.dist(pu,pd)
    mid=((pu[0]+pd[0])/2-561500,(pu[1]+pd[1])/2-8658000)
    inte = e['dn']<=50 or (e['dn']<=100 and inside(*mid))
    interno+=inte
    out.append([idmap[e['i']],pu[0]-561500,pu[1]-8658000,e['zu']+e['od']/2000,pd[0]-561500,pd[1]-8658000,e['zd']+e['od']/2000,
                'INT' if inte else ('AC' if False else 'AP'),f(e['a']),f(e['b']),L,(e['zu']-e['zd'])/max(L,0.01)*100])
out.sort()
with open(W+'revit_pipes_fix.csv','w',newline='') as fo:
    w=csv.writer(fo,delimiter=';')
    for r in out: w.writerow([f'{x:.4f}' if isinstance(x,float) else x for x in r])
print('pontas movidas',moved,'longe(>1,8 m, nao movidas)',far,'internos',interno,'de',len(out))
lint=sum(e['L'] for e,r in zip(E,[None]*len(E)) if False)
print('comprimento interno m',round(sum(r[10] for r in out if r[7]=='INT'),1),'externo',round(sum(r[10] for r in out if r[7]!='INT'),1))
