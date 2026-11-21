# -*- coding: utf-8 -*-
"""Catu — lista as entidades da cópia DXF de uma folha perto de um traçado (UTM), para conferir por que o rever.py não acha o
traçado original. Uso: python cat_dxf_perto.py <FOLHA> <trecho> [raio]"""
import sys, json, numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab
import escolas.catu as S

folha, tr = sys.argv[1], sys.argv[2]; R = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
dwg = S._DWG[folha]; rot, t = S.TRANSF_DWG[dwg]; t = np.array(t)
import os
dxf = os.path.join(S.REL, 'EXECUTIVO_2026-10-25', '_copias', os.path.basename(dwg)[:-4] + '.dxf')
E = ab.entidades(dxf)
M = json.load(open(os.path.join(S.SAIDA, 'CAT_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
m = next(m for m in M if tr in m['trecho'] and m['tipo'] in ('contorno',))
A = np.array(m['antigo'])[:, :2] - t


def dseg(q, P):
    best = 99
    for u, v in zip(P[:-1], P[1:]):
        w = v - u; L2 = float(w @ w)
        if L2 < 1e-12: continue
        s = float(np.clip((q - u) @ w / L2, 0, 1)); best = min(best, float(np.hypot(*(u + w * s - q))))
    return best


print(m['trecho'], 'antigo local', np.round(A, 2).tolist())
for e in E:
    if e['typ'] not in ('LINE', 'LWPOLYLINE'): continue
    P = np.asarray(e['pts'], float)[:, :2]
    d = [dseg(q, P) for q in A]
    if min(d) < R: print(e['h'], e['typ'], e['lay'], 'dist min %.2f max %.2f' % (min(d), max(d)), np.round(P, 2).tolist()[:6])
