# -*- coding: utf-8 -*-
"""Mergulho do ELE-I-14 sob a CX-43, que ficou mais funda com a drenagem do campo 50x30: refaz o mergulho 10 cm abaixo do novo fundo
externo (rampas 1:2), testa o clash e grava compat_R01/ele_i14_instrucoes.tsv (MODSEG id ax ay az bx by bz nota)."""
import sys, os, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"
S, M = JD.carregar(g=os.path.join(C, 'geo_exec'), est='daniel'); JD.agrupar_caixas(S, M)
pc = {s['trecho']: s for s in S if s['disc'] == 'ELE' and s['trecho'].startswith('ELE-I-14')}
cx = [m for m in M if m.get('grupo') == 'CX-43']; lo = np.min([m['lo'] for m in cx], 0); hi = np.max([m['hi'] for m in cx], 0)
a0 = pc['ELE-I-14']['a']; b4 = pc['ELE-I-14.m4']['b']; u = (b4[:2] - a0[:2]) / np.linalg.norm(b4[:2] - a0[:2])
P = lambda s, z: np.array([*(a0[:2] + u * s), z])
cant = [np.dot(np.array([x, y]) - a0[:2], u) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])]
s1, s2 = min(cant) - 0.15, max(cant) + 0.15
de = pc['ELE-I-14']['de']; zf = lo[2] - 0.10 - de / 2
zA, zB = pc['ELE-I-14']['b'][2], pc['ELE-I-14.m4']['a'][2]
sA = s1 - (zA - zf) * 2; sB = s2 + (zB - zf) * 2
novo = {'ELE-I-14': (a0, P(sA, zA)), 'ELE-I-14.m1': (P(sA, zA), P(s1, zf)), 'ELE-I-14.m2': (P(s1, zf), P(s2, zf)), 'ELE-I-14.m3': (P(s2, zf), P(sB, zB)), 'ELE-I-14.m4': (P(sB, zB), b4)}
print('fundo externo da CX-43 %.3f -> eixo do mergulho %.3f (era %.3f); trecho em mergulho de %.1f a %.1f m' % (lo[2], zf, pc['ELE-I-14.m2']['a'][2], sA, sB))
for k, (a, b) in novo.items(): s = pc[k]; s['a'], s['b'] = a, b; s['teste'] = True
IDX = mt.Indice(S, M); res = set()
for i, s in enumerate(S):
    if not s.get('teste'): continue
    for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
        B = S[j] if t == 'S' else M[j]
        if B['disc'] == 'ELE' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        res.add((s['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1)))
print('clash do ELE-I-14 refeito:', sorted(res, key=lambda r: r[3]))
L = ['\t'.join(['MODSEG', pc[k]['id']] + ['%.4f' % v for v in (*a, *b)] + ['R01 18/10: mergulho refeito sob a CX-43 (campo 50x30)']) for k, (a, b) in novo.items()]
open(os.path.join(C, 'ele_i14_instrucoes.tsv'), 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print('\n'.join(L))
