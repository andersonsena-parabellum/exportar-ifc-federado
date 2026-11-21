"""Auditoria ESG: DWG (dump_ESG.tsv) x modelo Revit (hs_*.csv). Tudo em coordenadas locais (UTM - 561500/8658000)."""
import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from common import *
rows=load('ESG')
walls=[];arrows=[]
for r in rows:
    if r[0]=='LINE' and r[1].startswith('TQ-Condutos'):
        p=pts(r[3])
        if len(p)>=2 and math.dist(p[0],p[1])>0.5: walls.append((L(p[0]),L(p[1])))
    if r[0]=='MLINE' and r[1].startswith('TQ-Condutos'):
        p=[L(q) for q in pts(r[3])]
        if len(p)>=2: walls.append((p[0],p[-1]))
    if r[0]=='LWPOLYLINE' and r[1].startswith('TQ-Sentido'):
        p=[L(q) for q in pts(r[3])]
        if len(p)>=2: arrows.append((p[0],p[-1]))
T=[txt(r) for r in rows if r[0]=='MTEXT' and r[1].startswith('TQ-Textos')]; T=[t for t in T if t]
sym=[txt(r) for r in rows if r[0]=='MTEXT' and r[1]=='Simbolos']; sym=[s for s in sym if s]
P=pipes('Esgoto')
print('DWG: paredes %d (%.0f m), setas %d, textos %d, simbolos %d %s'%(len(walls),sum(math.dist(a,b) for a,b in walls),len(arrows),len(T),len(sym),dict(collections.Counter(s[3] for s in sym))))
print('Modelo: tubos %d, %.1f m'%(len(P),sum(p['L'] for p in P)))
def dpipe(q): return min(dseg(q,(p['a'][0],p['a'][1]),(p['b'][0],p['b'][1])) for p in P)
# A paredes do DWG sem tubo
miss=[]
for a,b in walls:
    n=max(2,int(math.dist(a,b)/0.4)); bad=sum(1 for k in range(n+1) if dpipe((a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n))>0.30)
    if bad/(n+1)>0.4: miss.append((round(math.dist(a,b),1),a,b))
print('\n[A] paredes do DWG (>0,5 m) sem tubo próximo (>40%%): %d, %.1f m'%(len(miss),sum(m[0] for m in miss)))
for m in sorted(miss,reverse=True)[:20]: print('   L=%.1f (%.1f,%.1f)-(%.1f,%.1f)'%(m[0],*m[1],*m[2]))
# B setas sem tubo
nb=[]
for a,b in arrows:
    c=((a[0]+b[0])/2,(a[1]+b[1])/2)
    d=dpipe(c)
    if d>0.35: nb.append((c,d))
print('\n[B] setas de sentido sem tubo: %d de %d'%(len(nb),len(arrows)))
for c,d in nb: print('   (%.1f,%.1f) d=%.2f'%(c[0],c[1],d))
# C tubos sem parede
print('\n[C] tubos modelados sem parede de DWG a < 0,5 m do ponto médio:')
nc=0
for p in P:
    m=((p['a'][0]+p['b'][0])/2,(p['a'][1]+p['b'][1])/2)
    d=min(dseg(m,a,b) for a,b in walls)
    if d>0.5: nc+=1; print('   id=%s DN%s L=%.1f mid(%.1f,%.1f) d=%.2f'%(p['id'],p['dn'],p['L'],*m,d))
print('   total',nc)
# D caixas
O=rd('hs_outros.csv'); G=rd('hs_generic.csv')
bx=[]
for o in O:
    if o['cat']=='PipeAccessory' and 'COMP_Disciplina=ESG' in o['param_comp']:
        m=re.search(r'COMP_Trecho=([^|]*)',o['param_comp']); bx.append((m.group(1),num(o['x']),num(o['y']),num(o['zmin']),num(o['zmax']),o['nome']))
for g in G:
    if 'COMP_Disciplina=ESG' in g['param_comp']:
        m=re.search(r'COMP_Trecho=([^|]*)',g['param_comp']); bx.append((m.group(1),num(g['x']),num(g['y']),num(g['zmin']),num(g['zmax']),g['nome']))
print('\n[D] caixas modeladas ESG: %d'%len(bx), dict(collections.Counter(re.sub(r'[-\d]+$','',b[0]) for b in bx)))
# caixas do DWG: clusters das linhas TQ-Caixa de alvenaria
bl=[]
for r in rows:
    if r[0]=='LINE' and r[1].startswith('TQ-Caixa'):
        p=pts(r[3]);
        if len(p)>=2: bl.append(((L(p[0])[0]+L(p[1])[0])/2,(L(p[0])[1]+L(p[1])[1])/2))
cl=[]
for q in bl:
    for c in cl:
        if math.dist(q,c['m'])<1.6: c['n']+=1; c['pts'].append(q); c['m']=(sum(x for x,_ in c['pts'])/len(c['pts']),sum(y for _,y in c['pts'])/len(c['pts'])); break
    else: cl.append({'m':q,'n':1,'pts':[q]})
cl=[c for c in cl if c['n']>=3]
print('    clusters de caixa no DWG (TQ-Caixa de alvenaria): %d'%len(cl))
nobox=[]
for c in cl:
    d=min((math.dist(c['m'],(b[1],b[2])),b[0]) for b in bx)
    if d[0]>1.2: nobox.append((c['m'],d))
print('    caixas do DWG sem caixa no modelo (>1,2 m): %d'%len(nobox))
for m,d in nobox: print('      (%.1f,%.1f) mais próxima %s a %.1f m'%(m[0],m[1],d[1],d[0]))
nod=[]
for b in bx:
    d=min(math.dist((b[1],b[2]),c['m']) for c in cl)
    if d>1.2: nod.append((b,d))
print('    caixas do modelo sem caixa de DWG (>1,2 m): %d'%len(nod))
for b,d in nod: print('      %s (%.1f,%.1f) %s d=%.1f'%(b[0],b[1],b[2],b[5],d))
# rótulos de símbolo CE/CES/CG vs caixa
ns=[s for s in sym if min(math.dist((s[0],s[1]),(b[1],b[2])) for b in bx)>2.0]
print('    rótulos CE/CES/CG do DWG a > 2 m de qualquer caixa modelada: %d'%len(ns))
for s in ns: print('      %s (%.1f,%.1f)'%(s[3],s[0],s[1]))
# E sobreposição de tubos
print('\n[E] pares de tubos sobrepostos/duplicados (eixos a < 5 cm em trecho > 0,3 m):')
ne=0
for i,p in enumerate(P):
    for q in P[i+1:]:
        pa=(p['a'][0],p['a'][1]);pb=(p['b'][0],p['b'][1])
        qa=(q['a'][0],q['a'][1]);qb=(q['b'][0],q['b'][1])
        cnt=0;n=8
        for k in range(n+1):
            t=k/n; s=(pa[0]+(pb[0]-pa[0])*t,pa[1]+(pb[1]-pa[1])*t)
            if dseg(s,qa,qb)<0.05: cnt+=1
        if cnt>=3: ne+=1; print('   %s x %s (%d/9 pontos)'%(p['id'],q['id'],cnt))
print('   total',ne)
# F inclinação x rótulo i=%
print('\n[F] inclinação do tubo x rótulo i=%% (rótulo mais próximo a < 2 m do eixo):')
I=[(t[0],t[1],float(re.search(r'i=([\d.,]+)%',t[3]).group(1).replace(',','.'))) for t in T if re.search(r'i=([\d.,]+)%',t[3])]
nf=0;sem=0;lst=[]
for p in P:
    dx=p['b'][0]-p['a'][0];dy=p['b'][1]-p['a'][1];Lh=math.hypot(dx,dy)
    if Lh<0.5: continue
    sl=abs(p['b'][2]-p['a'][2])/Lh*100
    m=((p['a'][0]+p['b'][0])/2,(p['a'][1]+p['b'][1])/2)
    c=[(dseg((i[0],i[1]),(p['a'][0],p['a'][1]),(p['b'][0],p['b'][1])),i[2]) for i in I]
    c=[x for x in c if x[0]<2.0]
    if not c: sem+=1; continue
    lab=min(c)[1]
    if abs(sl-lab)>0.35: nf+=1; lst.append((p['id'],p['dn'],round(Lh,1),round(sl,2),lab))
print('   tubos com declividade fora do rótulo (±0,35 p.p.): %d; sem rótulo próximo: %d'%(nf,sem))
for x in lst[:25]: print('   id=%s DN%s Lh=%s modelo=%s%% rótulo=%s%%'%x)
# G DN
print('\n[G] DN modelado x rótulo "NNN mm"/"Ø" mais próximo:')
D_=[(t[0],t[1],int(re.search(r'(\d{2,3})',t[3]).group(1))) for t in T if re.search(r'^\D*\d{2,3} ?mm$',t[3]) or t[3].startswith('Ø')]
nd=0
for p in P:
    c=[(dseg((d[0],d[1]),(p['a'][0],p['a'][1]),(p['b'][0],p['b'][1])),d[2]) for d in D_]
    c=[x for x in c if x[0]<1.5]
    if c and abs(min(c)[1]-p['dn'])>12: nd+=1; print('   id=%s modelo DN%.0f x rótulo %s'%(p['id'],p['dn'],min(c)[1]))
print('   divergências:',nd,'| rótulos DN lidos:',len(D_))
# H conectores livres / pontas soltas
print('\n[H] conectividade: tubos com conector livre: %d; pontas a > 0,3 m de caixa/outro tubo:'%sum(1 for p in P if p['livres']>0))
nh=0
for p in P:
    for e in (p['a'],p['b']):
        ok=any(math.dist((e[0],e[1]),(b[1],b[2]))<0.9 for b in bx) or any(q is not p and (math.dist(e,q['a'])<0.1 or math.dist(e,q['b'])<0.1) for q in P) or any(dseg((e[0],e[1]),(q['a'][0],q['a'][1]),(q['b'][0],q['b'][1]))<0.1 for q in P if q is not p)
        if not ok: nh+=1; print('   id=%s ponta (%.1f,%.1f,%.2f)'%(p['id'],e[0],e[1],e[2]))
print('   pontas soltas:',nh)
