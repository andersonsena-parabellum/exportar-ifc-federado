import json, collections, sys
J=json.load(open(sys.argv[1],encoding='utf-8'))
T=J['trechos']
saida=collections.defaultdict(list)
for t in T: saida[t['de']].append(t)
def destino(n, vis):
    if n in vis: return 'LAÇO'
    vis.add(n)
    if not saida[n]: return n
    return destino(saida[n][0]['para'], vis)
fim=collections.Counter(destino(t['para'], set()) for t in T)
L=collections.Counter()
for t in T: L[destino(t['para'], set())]+=t['L_m']
print('destinos finais (n trechos, m):', [(k,v,round(L[k],1)) for k,v in fim.most_common(25)])
print('indefinidos:', [(t['trecho'],t['de'],t['para'],t['L_m'],t['DN_mm']) for t in T if t['sentido']=='indefinido'][:70])
