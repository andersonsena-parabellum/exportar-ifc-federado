# -*- coding: utf-8 -*-
"""Verifica a correção das sobreposições lida de volta do Revit:
 1) sobreposições internas (mesma regra do planejador: isenta encontro dentro de caixa);
 2) nenhum ponto ficou mais raso que antes (z novo <= z original interpolado no mesmo lugar, em planta);
 3) comprimento total por rede preservado (em planta)."""
import sys, math, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work" + "\\"
src = open(r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\ele_fix_sobreposicoes.py", encoding='utf-8').read()
# reaproveita leitura/corridas/overlaps do planejador, trocando a entrada pelo arquivo pós-correção
head = src.split("log = []")[0].replace("revit_conduits_atual_2026-10-16.tsv", "revit_conduits_pos_fix_2026-10-16.tsv")
g = {}; exec(head, g)
ov = g['overlaps'](g['P'])
print('1) sobreposições internas após a correção:', len(ov))
for o in ov[:10]: print('   ', o)


def load(fn):
    out = []
    for l in open(W + fn, encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) >= 10: out.append((r[2].split('.')[0], float(r[3]), np.array(list(map(float, r[4:7]))), np.array(list(map(float, r[7:10])))))
    return out
A = load('revit_conduits_atual_2026-10-16.tsv'); B = load('revit_conduits_pos_fix_2026-10-16.tsv')
# 2) para cada ponto amostrado dos novos (a cada 0,1 m), z original no ponto mais próximo em planta do mesmo trecho
orig = collections.defaultdict(list)
for t, de, a, b in A: orig[t].append((a, b))
pior = (0, None); n = 0
for t, de, a, b in B:
    L = np.linalg.norm((b - a)[:2])
    for f in np.linspace(0, 1, max(2, int(L / 0.1) + 1)):
        q = a + (b - a) * f; best = (9e9, None)
        for oa, ob in orig[t]:
            d = ob - oa; dd = d[:2] @ d[:2]
            s = 0 if dd < 1e-12 else np.clip(((q - oa)[:2] @ d[:2]) / dd, 0, 1)
            pp = oa + d * s; dist = np.linalg.norm((q - pp)[:2])
            if dist < best[0]: best = (dist, pp[2])
        if best[0] < 0.25:
            n += 1; dz = q[2] - best[1]
            if dz > pior[0]: pior = (dz, (t, q.round(3)))
print(f'2) pontos conferidos {n}; maior SUBIDA em relação ao original: {pior[0]*1000:.1f} mm {pior[1]}')
# 3) comprimento em planta por rede
def comp(X):
    c = collections.Counter()
    for t, de, a, b in X: c[t[:3]] += np.linalg.norm((b - a)[:2])
    return c
ca, cb = comp(A), comp(B)
print('3) comprimento em planta (m) antes/depois:', {k: (round(ca[k], 1), round(cb[k], 1)) for k in sorted(ca)})
print('   eletrodutos antes/depois:', len(A), len(B))
