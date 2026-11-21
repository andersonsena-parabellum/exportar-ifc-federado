# -*- coding: utf-8 -*-
"""Catu — mapa do terreno de entrega (catu_terreno_base.npz) com as CT das caixas e o contorno dos prédios, para conferência."""
import sys, os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preclash.terreno import Terreno
import cat_terreno as ct, predios as PR

T = Terreno(ct.OUT); xs = np.arange(ct.CAIXA[0], ct.CAIXA[2], 0.5); ys = np.arange(ct.CAIXA[1], ct.CAIXA[3], 0.5)
X, Y = np.meshgrid(xs, ys); Z = T.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
gy, gx = np.gradient(Z, 0.5); inc = np.degrees(np.arctan(np.hypot(gx, gy)))
fig, ax = plt.subplots(1, 2, figsize=(22, 11))
im = ax[0].pcolormesh(X, Y, Z, cmap='terrain', shading='auto'); ax[0].contour(X, Y, Z, levels=np.arange(76, 92, 0.5), colors='k', linewidths=0.3)
plt.colorbar(im, ax=ax[0]); im2 = ax[1].pcolormesh(X, Y, inc, cmap='magma_r', vmin=0, vmax=60, shading='auto'); plt.colorbar(im2, ax=ax[1], label='inclinação (°)')
B = ct.base(); r = B[:, 2] - T.z(B)
for a in ax:
    for n, p in PR.contornos(): a.plot(*p.exterior.xy, 'b-', lw=0.8)
    a.scatter(B[:, 0], B[:, 1], c='r', s=8)
    a.set_aspect('equal')
for (e, n, z), d in zip(B, r): ax[0].text(e, n, f'{z:.2f}' + (f' ({d:+.2f})' if abs(d) > 0.1 else ''), fontsize=5)
ax[0].set_title('Terreno de entrega (IMP com os platôs na base)'); ax[1].set_title('Inclinação')
fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'terreno_base.png'); fig.savefig(fn, dpi=90, bbox_inches='tight'); print(fn)
