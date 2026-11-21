# -*- coding: utf-8 -*-
"""Ponta da alimentação do QDLT-CAMPO no JAN-ELE (interno) e onde o QDLT cai com o CPS girado -5,38° ou 174,62°."""
import sys, re, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
S, M = JD.carregar(g=r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo", est=None, discs=('ELE',)); JD.agrupar_caixas(S, M)
ss = [s for s in S if re.search(r'Circuitos: QDLT-CAMPO\s*\|', s['desc'] or '')]
P = np.array([p for s in ss for p in (s['a'], s['b'])]); C = np.array([90.952, 114.112])
pon = P[np.argmin(np.linalg.norm(P[:, :2] - C, axis=1))]
print('trechos só QDLT-CAMPO:', [s['trecho'] for s in ss]); print('ponta mais perto do campo:', pon.round(2), 'dist ao centro %.1f m' % np.linalg.norm(pon[:2] - C))
eq = [(m['grupo'], ((m['glo'] + m['ghi']) / 2).round(2)) for m in M if m.get('glo') is not None and np.linalg.norm(((m['glo'] + m['ghi']) / 2)[:2] - pon[:2]) < 4]
print('caixas/equipamentos perto da ponta:', eq)
for ang in (-5.3818, 174.6182):
    t = np.radians(ang); R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    q = R @ (np.array([12.7, 74.46]) - np.array([43.983, 58.077])) + C
    print('rot %.2f°: QDLT-CAMPO do CPS em %s, a %.1f m da ponta do modelo' % (ang, q.round(2), np.linalg.norm(q - pon[:2])))
