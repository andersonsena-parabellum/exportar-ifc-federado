# -*- coding: utf-8 -*-
"""Sátiro Dias — planta de conferência de um ponto (modelo carregado pelo adaptador, antes do estudo de cota): trechos por
disciplina, caixas e contorno dos prédios. Uso: python sat_planta.py E N raio saida.png"""
import sys, os
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import escolas.satiro as S
import predios as PR
from preclash.export_ifc import COR

E0, N0, R = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
D = S.carregar()
fig, ax = plt.subplots(figsize=(11, 11))
U = PR.uniao()
for g in (U.geoms if hasattr(U, 'geoms') else [U]): ax.fill(*g.exterior.xy, color='0.85')
for e in D['elementos']:
    P = e['pts']
    if np.min(np.hypot(P[:, 0] - E0, P[:, 1] - N0)) > 2 * R: continue
    ax.plot(P[:, 0], P[:, 1], color=COR.get(e['disc'], (0, 0, 0)), lw=1.5)
    m = P[len(P) // 2]; ax.text(m[0], m[1], e['trecho'], fontsize=7, color=COR.get(e['disc'], (0, 0, 0)), clip_on=True)
for c in D['caixas']:
    if abs(c['E'] - E0) > 2 * R or abs(c['N'] - N0) > 2 * R: continue
    mx, my, rot = c.get('mx', c['meia']), c.get('my', c['meia']), c.get('rot', 0.0)
    u = np.array([np.cos(rot), np.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([c['E'], c['N']])
    Q = np.array([p + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))])
    ax.plot(Q[:, 0], Q[:, 1], color=COR.get(c['disc'], (0, 0, 0)), lw=1)
    ax.text(c['E'], c['N'], c['info'].get('nome', c['id']), fontsize=6, clip_on=True)
ax.set_xlim(E0 - R, E0 + R); ax.set_ylim(N0 - R, N0 + R); ax.set_aspect('equal'); ax.grid(lw=0.3)
fig.savefig(sys.argv[4], dpi=80, bbox_inches='tight')
