# -*- coding: utf-8 -*-
"""conferência: linhas de edificação da SIT R04 (layers de prédio) sobre as redes e os contornos da estrutura."""
import sys, os, re, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxf_ler import ler
import alh_modelo as AM, predios as PR
D = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\ALAGOINHAS_BA2\dxf_base\24-049-ALH-SLJ-ETIB-IMP-PE-URB-001-SIT-R04.dxf'
P = ler(D)
lay = collections.Counter(p['layer'] for p in P if p['tipo'] in ('PL', 'LINE'))
print(lay.most_common(40))
fig, ax = plt.subplots(figsize=(14, 18))
for p in P:
    if p['tipo'] not in ('PL', 'LINE') or not re.search(r'EDIFIC|Predio|ARQ_PAR|PAREDE|_URB_BLOCOS|ARQ_DEMOL', p['layer'], re.I): continue
    Q = p['pts'][:, :2] - AM.O[:2]
    if np.abs(Q).max() > 400: continue
    ax.plot(Q[:, 0], Q[:, 1], color='red' if 'DEMOL' in p['layer'] else 'k', lw=0.4)
for f, cor in (('DRN', 'tab:green'), ('HS', 'tab:blue')):
    for s in AM.ler_segs(f): ax.plot([s['a'][0], s['b'][0]], [s['a'][1], s['b'][1]], color=cor, lw=0.6)
for b, p in PR.contornos(utm=False):
    x, y = p.exterior.xy; ax.fill(x, y, alpha=0.2, color='orange')
ax.set_xlim(-30, 110); ax.set_ylim(-120, 70); ax.set_aspect('equal')
fig.savefig(r'C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\02bc9bcd-33aa-469b-90c1-598fe5356696\scratchpad\sit_predios.png', dpi=70)
