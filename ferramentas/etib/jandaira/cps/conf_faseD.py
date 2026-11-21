# -*- coding: utf-8 -*-
"""Conferência da fase D no modelo: clash das peças do campo society (comentário 'campo society') do JAN-ELE exportado contra tudo."""
import sys, os, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo_exec"
S, M = JD.carregar(g=C, est='daniel'); JD.agrupar_caixas(S, M)
cps = lambda E: 'campo society' in (E.get('desc') or '')
IDX = mt.Indice(S, M); res = set()
for i, s in enumerate(S):
    if not cps(s): continue
    for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
        B = S[j] if t == 'S' else M[j]
        if cps(B) or B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes') or (B['disc'] == 'ELE' and B['cat'].startswith(('Equip', 'Conex'))): continue
        res.append if False else res.add((s['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1)))
for j, E in enumerate(M):
    if not cps(E): continue
    for t, k, g, pt in mt.avaliar_mesh(j, IDX, 0.20):
        B = S[k] if t == 'S' else M[k]
        if cps(B) or B['disc'] == 'ELE' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        res.add((E['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1)))
n = sum(1 for s in S if cps(s)); L = sum(np.linalg.norm(s['b'] - s['a']) for s in S if cps(s))
print('peças do campo no modelo: %d eletrodutos (%.1f m), %d sólidos' % (n, L, sum(1 for m in M if cps(m))))
print('colisões:', sum(1 for r in res if r[3] < -0.2), '| folgas < 20 cm:', sum(1 for r in res if r[3] >= -0.2))
for r in sorted(res, key=lambda r: r[3]): print('  ', r)
