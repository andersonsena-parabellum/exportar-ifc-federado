"""v2b: sentido pelas SETAS do projeto; sem seta -> pela distância à saída. Confere se cada trecho escoa até um lançamento."""
import pickle,math,collections,json
W='D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
D=pickle.load(open(W+'v2_net.pkl','rb'))
nodes,edges,outs,dist=D['nodes'],D['edges'],D['outs'],D['dist']
rep=[]
def say(*a):
    s=' '.join(str(x) for x in a); rep.append(s); print(s)
for e in edges:
    if e['fl']:
        if e['fl']>0: e['up'],e['dn']=e['u'],e['v']
        else: e['up'],e['dn']=e['v'],e['u']
        e['dirsrc']='seta'
    else:
        du,dv=dist.get(e['u'],1e9),dist.get(e['v'],1e9)
        e['up'],e['dn']=(e['u'],e['v']) if du>=dv else (e['v'],e['u'])
        e['dirsrc']='árvore'
def build():
    o=collections.defaultdict(list)
    for k,e in enumerate(edges): o[e['up']].append(k)
    return o
out_of=build()
# reparo: no que recebe e nao tem saida -> inverte um trecho 'árvore' que entra nele, se a outra ponta chega a um lancamento
def reach0(n,ban):
    seen=set(); st=[n]
    while st:
        x=st.pop()
        if x in outs: return True
        if x in seen: continue
        seen.add(x)
        for k in out_of[x]:
            if k!=ban: st.append(edges[k]['dn'])
    return False
for it in range(10):
    inn=collections.Counter(e['dn'] for e in edges); outn=collections.Counter(e['up'] for e in edges)
    sinks=[n for n in inn if outn[n]==0 and n not in outs]
    ch=0
    for n in sinks:
        ks=[k for k,e in enumerate(edges) if e['dn']==n and (e['dirsrc']=='árvore' or (e['dirsrc']=='seta' and e['L']<2.5))]
        for k in sorted(ks,key=lambda k:(0 if edges[k]['dirsrc']=='árvore' else 1,-(edges[k]['d'] or 0.03))):
            e=edges[k]
            if reach0(e['up'],k):
                e['up'],e['dn']=e['dn'],e['up']; e['dirsrc']=('árvore (corrigido)' if e['dirsrc']=='árvore' else 'seta curta contrariada'); ch+=1; out_of=build(); break
    if not ch: break
say('trechos re-orientados para dar saida:',collections.Counter(e['dirsrc'] for e in edges if 'corrig' in e['dirsrc'] or 'contrari' in e['dirsrc']))
# segue para jusante (pode passar por caixa com varias saidas)
def reach(n,seen=None):
    seen=set(); st=[n]
    while st:
        x=st.pop()
        if x in outs: return x
        if x in seen: continue
        seen.add(x)
        for k in out_of[x]: st.append(edges[k]['dn'])
    return None
bad=[]
for k,e in enumerate(edges):
    e['bacia']=reach(e['dn'])
    if e['bacia'] is None: bad.append(k)
say('trechos que NAO escoam ate um lancamento seguindo o sentido:',len(bad),'%.0f m'%sum(edges[k]['L'] for k in bad))
# onde param? nos sem saida (nao lancamento) com entrada
inn=collections.Counter(e['dn'] for e in edges); outn=collections.Counter(e['up'] for e in edges)
sinks=[n for n in inn if outn[n]==0 and n not in outs]
say('nos que recebem agua e nao tem saida (fim cego):',len(sinks))
for n in sinks:
    p=nodes[n]['p']; ks=[k for k,e in enumerate(edges) if e['dn']==n]
    say('   (%.1f,%.1f) %s  entra: %s'%(p[0],p[1],nodes[n]['kind'],[(round(edges[k]['L'],1),edges[k]['d'] and round(edges[k]['d'],2),edges[k]['dirsrc']) for k in ks]))
bac=collections.defaultdict(float)
for e in edges:
    if e['bacia'] is not None: bac[e['bacia']]+=e['L']
say('bacias (m):',{str((round(nodes[k]['p'][0]),round(nodes[k]['p'][1]))):round(v) for k,v in bac.items()})
pickle.dump(D,open(W+'v2_net.pkl','wb'))
open(W+'v2b_relatorio.txt','w',encoding='utf-8').write('\n'.join(rep))
