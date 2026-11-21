# -*- coding: utf-8 -*-
"""Regra de 19/10 (Anderson): nenhuma rede pressurizada/elétrica com o topo a mais de 1,50 m do terreno. Confere nos modelos revisados."""
import sys, os, re, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo_exec"
S, M = JD.carregar(g=G, est=None); T = JD.Terreno(g=G)
viol = []
for s in S:
    if s['disc'] not in ('AF', 'ELE', 'INC', 'SDAI'): continue
    a, b = s['a'], s['b']
    if np.linalg.norm(b[:2] - a[:2]) < 0.05: continue              # trechos verticais (subidas) não contam
    for u in np.linspace(0, 1, 5):
        p = a + (b - a) * u; zt = T.z(p[0], p[1])
        if np.isnan(zt): continue
        d = zt - (p[2] + s['de'] / 2)
        if d > 1.50: viol.append((s['disc'], s['trecho'], round(float(d), 2), round(float(147 + p[2]), 2), tuple(np.round(p[:2], 1)))); break
print('trechos com topo a mais de 1,50 m do terreno:', len(viol))
for v in sorted(viol, key=lambda v: -v[2])[:40]: print('  ', v)
