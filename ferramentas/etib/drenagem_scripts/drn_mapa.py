"""Mapa da rede (como o projetista): grafo com sentido de escoamento, bacias por lançamento,
componentes órfãos, prumadas AP sem ligação, caixas sem entrada/saída."""
import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,csv,math,json,collections
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
L=lambda p:(p[0]-561500,p[1]-8658000)
inb=lambda p:-90<p[0]<110 and -125<p[1]<75
W='work/'
# ---- tubos atuais do modelo
pipes=[]
dn={r[0]:int(r[2]) for r in csv.reader(open(W+'revit_pipes.csv'),delimiter=';')}
for r in csv.reader(open(W+'revit_pipes_fix.csv'),delimiter=';'):
    if r[0]=='378': continue
    pipes.append({'id':'DRN-%03d'%int(r[0]),'a':(float(r[1]),float(r[2])),'b':(float(r[4]),float(r[5])),'za':float(r[3]),'zb':float(r[6]),'dn':dn[r[0]]})
for i,r in enumerate(csv.reader(open(W+'new_pipes.csv',encoding='utf-8'),delimiter=';')):
    pipes.append({'id':'DRN-A%02d'%(i+1),'a':(float(r[3]),float(r[4])),'b':(float(r[6]),float(r[7])),'za':float(r[5]),'zb':float(r[8]),'dn':int(r[0])})
for p in pipes:   # orienta montante->jusante pela cota
    if p['zb']>p['za']+0.005: p['a'],p['b'],p['za'],p['zb']=p['b'],p['a'],p['zb'],p['za']
    p['L']=math.dist(p['a'],p['b'])
# ---- caixas
boxes=[]
aud=json.load(open(W+'audit.json')); drop={(d[0],d[1]) for d in aud['drop']}
for b in csv.reader(open(W+'revit_boxes.csv'),delimiter=';'):
    if (b[0],b[1]) in drop: continue
    boxes.append({'id':('PV-' if b[0]=='PV' else 'CX-')+b[1],'p':(float(b[2]),float(b[3])),'r':0.6 if b[0]!='PV' else 0.6})
for k,b in enumerate(csv.reader(open(W+'new_boxes.csv',encoding='utf-8'),delimiter=';')):
    if b[0]=='CA' and abs(float(b[1])-16.812)<0.1: continue
    boxes.append({'id':('PV-A' if b[0]=='PVP' else 'CX-A')+'%02d'%(k+1),'p':(float(b[1]),float(b[2])),'r':0.6})
# ---- nós: agrupar pontas
ends=[]
for i,p in enumerate(pipes): ends+= [(i,'a',p['a']),(i,'b',p['b'])]
par=list(range(len(ends)))
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
for i in range(len(ends)):
    for j in range(i+1,len(ends)):
        if math.dist(ends[i][2],ends[j][2])<0.6: par[f(i)]=f(j)
node_of={}; nodes=collections.defaultdict(list)
for k,(i,s,pt) in enumerate(ends): node_of[(i,s)]=f(k); nodes[f(k)].append((i,s,pt))
nbox={}
for g,lst in nodes.items():
    c=(sum(q[2][0] for q in lst)/len(lst),sum(q[2][1] for q in lst)/len(lst))
    b=min(boxes,key=lambda b:math.dist(b['p'],c)); 
    if math.dist(b['p'],c)<1.0: nbox[g]=b['id']
# ---- lancamentos: pontas de jusante ao norte (y>50)
G=collections.defaultdict(list)   # jusante: no_a -> no_b
for i,p in enumerate(pipes): G[node_of[(i,'a')]].append((node_of[(i,'b')],i))
indeg=collections.Counter(); outdeg=collections.Counter()
for i,p in enumerate(pipes): outdeg[node_of[(i,'a')]]+=1; indeg[node_of[(i,'b')]]+=1
outfalls=[g for g in nodes if outdeg[g]==0 and max(q[2][1] for q in nodes[g])>50]
print('lancamentos (pontas finais ao norte):',[(round(nodes[g][0][2][0],1),round(nodes[g][0][2][1],1)) for g in outfalls])
# bacia: percorre de cada no para jusante ate um lancamento
def downstream(g,seen=None):
    seen=seen or set(); stack=[g]
    while stack:
        x=stack.pop()
        if x in outfalls: return x
        if x in seen: continue
        seen.add(x)
        for y,i in G[x]: stack.append(y)
        # se e caixa, pode sair por outro no da mesma caixa
        if x in nbox:
            for y in nbox:
                if nbox[y]==nbox[x] and y not in seen: stack.append(y)
    return None
bacia={}
for i,p in enumerate(pipes): bacia[i]=downstream(node_of[(i,'a')])
names={g:'L%d (x=%.0f)'%(k+1,nodes[g][0][2][0]) for k,g in enumerate(sorted(outfalls,key=lambda g:nodes[g][0][2][0]))}
agg=collections.defaultdict(float); cnt=collections.Counter()
for i,p in enumerate(pipes): agg[names.get(bacia[i],'SEM LANÇAMENTO')]+=p['L']; cnt[names.get(bacia[i],'SEM LANÇAMENTO')]+=1
print('bacias:',{k:(cnt[k],round(v,1)) for k,v in agg.items()})
orf=[p for i,p in enumerate(pipes) if bacia[i] is None]
# agrupar orfaos em componentes
oc=collections.defaultdict(list)
for i,p in enumerate(pipes):
    if bacia[i] is None: oc[f(ends.index((i,'a',p['a'])) if False else 0)].append(p)
# componentes conexos (sem sentido) dos orfaos
par2={}
def f2(x):
    par2.setdefault(x,x)
    while par2[x]!=x: x=par2[x]
    return x
for i,p in enumerate(pipes):
    if bacia[i] is None: par2[f2(node_of[(i,'a')])]=f2(node_of[(i,'b')])
comp=collections.defaultdict(list)
for i,p in enumerate(pipes):
    if bacia[i] is None: comp[f2(node_of[(i,'a')])].append(p)
print('componentes SEM chegar a lancamento:',len(comp))
rep=[]
for c in sorted(comp.values(),key=lambda c:-sum(p['L'] for p in c)):
    Lc=sum(p['L'] for p in c); 
    # ponto mais baixo (fim do componente)
    low=min(c,key=lambda p:p['zb'])
    rep.append({'n':len(c),'L':round(Lc,1),'dn':sorted(set(p['dn'] for p in c)),'fim':[round(v,1) for v in low['b']],'z_fim':round(low['zb'],2),'ids':[p['id'] for p in c][:8]})
for r in rep[:40]: print('  ',r)
# ---- prumadas AP: hatch do layer AP-Colunas
cols=[L(e[3]) for e in E if e[1]=='AP-Colunas' and e[0]=='HATCH']
cols=[c for c in cols if inb(c)]
# cluster
cl=[]
for c in cols:
    if all(math.dist(c,k)>0.5 for k in cl): cl.append(c)
def dseg(q,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; n2=dx*dx+dy*dy
    t=0 if n2==0 else max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/n2)); return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
semlig=[c for c in cl if min(dseg(c,p['a'],p['b']) for p in pipes)>1.0]
print('prumadas AP (simbolo):',len(cl),' sem tubo a <1 m:',len(semlig))
for c in semlig: print('   prumada sem ligacao',[round(v,1) for v in c])
json.dump({'bacias':{k:round(v,1) for k,v in agg.items()},'orfaos':rep,'prumadas_sem_ligacao':semlig},open(W+'mapa_rede.json','w'),indent=1)
