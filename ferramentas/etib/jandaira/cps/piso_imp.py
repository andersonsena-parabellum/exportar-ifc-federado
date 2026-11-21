# -*- coding: utf-8 -*-
"""Contorno do piso do campo no IMP as built (retângulo de menor área dos vértices do topo) e vértices distintos."""
import sys, os, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"
imp = [os.path.join(G, f) for f in os.listdir(G) if f.startswith('IMP') and f.endswith('_mesh.tsv')][0]
for l in open(imp, encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) < 9 or not r[8] or r[2] != 'Pisos': continue
    v = np.array(r[8].split(','), dtype=float).reshape(-1, 3)
    lo, hi = v.min(0), v.max(0)
    if (hi - lo)[0] < 30: continue
    top = v[np.abs(v[:, 2] - hi[2]) < 1e-3]; P = np.unique(top[:, :2].round(3), axis=0)
    print('piso', r[1], r[3], 'z topo %.3f' % hi[2], 'vértices distintos no topo:', len(P))
    best = None
    for a in np.arange(0, 180, 0.01):
        t = np.radians(a); U = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]]); Q = P @ U.T
        w, h = Q.max(0) - Q.min(0)
        if best is None or w * h < best[0]: best = (w * h, a, w, h, (Q.max(0) + Q.min(0)) / 2 @ U)
    print('  retângulo mínimo: %.3f x %.3f, ang %.3f°, centro %s' % (best[2], best[3], best[1], np.round(best[4], 3)))
    if len(P) <= 40: print('  vértices:', P.tolist())
