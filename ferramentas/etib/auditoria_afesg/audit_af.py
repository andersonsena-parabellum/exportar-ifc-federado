import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from common import *
rows=load('AGF')
walls=[];arrows=[]
for r in rows:
    if r[0]=='LINE' and (r[1].startswith('AF-Condutos') or r[1].startswith('AL-Condutos')):
        p=pts(r[3])
        if len(p)>=2 and math.dist(p[0],p[1])>0.5: walls.append((L(p[0]),L(p[1]),r[1]))
    if r[0]=='LWPOLYLINE' and ('Sentido' in r[1]):
        p=[L(q) for q in pts(r[3])]
        if len(p)>=2: arrows.append((p[0],p[-1],r[1]))
P=pipes('Água fria')
print('DWG AF: paredes >0,5 m: %d (%.0f m), setas %d'%(len(walls),sum(math.dist(a,b) for a,b,_ in walls),len(arrows)))
print('Modelo AF: tubos %d, %.1f m'%(len(P),sum(p['L'] for p in P)), dict(collections.Counter(p['sis'] for p in P)))
def dpipe(q): return min(dseg(q,(p['a'][0],p['a'][1]),(p['b'][0],p['b'][1])) for p in P)
miss=[]
for a,b,ly in walls:
    n=max(2,int(math.dist(a,b)/0.4)); bad=sum(1 for k in range(n+1) if dpipe((a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n))>0.30)
    if bad/(n+1)>0.4: miss.append((round(math.dist(a,b),1),a,b,ly))
print('\n[A] paredes do DWG sem tubo próximo: %d, %.1f m'%(len(miss),sum(m[0] for m in miss)))
for m in sorted(miss,reverse=True)[:25]: print('   L=%.1f (%.1f,%.1f)-(%.1f,%.1f) %s'%(m[0],*m[1],*m[2],m[3]))
nb=[]
for a,b,ly in arrows:
    c=((a[0]+b[0])/2,(a[1]+b[1])/2); d=dpipe(c)
    if d>0.35: nb.append((c,d,ly))
print('\n[B] setas sem tubo: %d de %d'%(len(nb),len(arrows)))
for c,d,ly in nb: print('   (%.1f,%.1f) d=%.2f %s'%(c[0],c[1],d,ly))
print('\n[C] tubos modelados sem parede DWG a < 0,5 m (ponto médio):')
nc=0
for p in P:
    m=((p['a'][0]+p['b'][0])/2,(p['a'][1]+p['b'][1])/2)
    d=min(dseg(m,a,b) for a,b,_ in walls)
    if d>0.5: nc+=1; print('   id=%s %s DN%s L=%.1f mid(%.1f,%.1f) d=%.2f'%(p['id'],p['sis'][:22],p['dn'],p['L'],*m,d))
print('   total',nc)
# D DN
T=[txt(r) for r in rows if r[0]=='MTEXT' and r[1] in ('AF-Textos conduto','TEXTOS')]; T=[t for t in T if t]
D_=[]
for t in T:
    m=re.search(r'^(?:Ø|\D)?\s*(\d{2})(?: ?mm)?$',t[3]) 
    if m and int(m.group(1)) in (20,25,32,40,50,60,75,85,110): D_.append((t[0],t[1],int(m.group(1))))
print('\n[D] DN: %d rótulos lidos'%len(D_))
nd=0
for p in P:
    c=[(dseg((d[0],d[1]),(p['a'][0],p['a'][1]),(p['b'][0],p['b'][1])),d[2]) for d in D_]
    c=[x for x in c if x[0]<1.0]
    if c:
        vals=set(x[1] for x in c)
        if not any(abs(v-p['dn'])<=3 for v in vals):
            nd+=1; print('   id=%s %s modelo DN%.0f x rótulos %s'%(p['id'],p['sis'][:20],p['dn'],sorted(vals)))
print('   divergências:',nd)
c=collections.defaultdict(float)
for p in P: c[(p['sis'],p['dn'])]+=p['L']
print('   metros por sistema/DN:',{k:round(v,1) for k,v in sorted(c.items())})
# E sobreposição
ne=0
for i,p in enumerate(P):
    for q in P[i+1:]:
        pa=(p['a'][0],p['a'][1]);pb=(p['b'][0],p['b'][1]);qa=(q['a'][0],q['a'][1]);qb=(q['b'][0],q['b'][1])
        cnt=sum(1 for k in range(9) if dseg((pa[0]+(pb[0]-pa[0])*k/8,pa[1]+(pb[1]-pa[1])*k/8),qa,qb)<0.05)
        if cnt>=3: ne+=1; print('   [E] sobrepostos %s x %s (%d/9)'%(p['id'],q['id'],cnt))
print('\n[E] pares sobrepostos:',ne)
# H pontas soltas e conectores
print('\n[H] tubos com conector livre: %d; pontas soltas (sem outro tubo/acessório a 0,15 m):'%sum(1 for p in P if p['livres']>0))
O=rd('hs_outros.csv');G=rd('hs_generic.csv')
oth=[(num(o['x']),num(o['y'])) for o in O+G if 'COMP_Disciplina=AF' in o['param_comp'] or o.get('cat') in ('MechanicalEquipment','PipeFitting')]
nh=0
for p in P:
    for e in (p['a'],p['b']):
        ok=any(q is not p and (math.dist(e,q['a'])<0.15 or math.dist(e,q['b'])<0.15) for q in P) or any(math.dist((e[0],e[1]),o)<0.8 for o in oth)
        if not ok: nh+=1; print('   id=%s ponta (%.1f,%.1f,%.2f) %s'%(p['id'],e[0],e[1],e[2],p['sis'][:18]))
print('   pontas soltas:',nh)
# F recobrimento nas pontas: usa so z do tubo (terreno não está neste documento) -> saída para checagem posterior
