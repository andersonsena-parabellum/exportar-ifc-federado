# -*- coding: utf-8 -*-
"""Terreno as built (IMP) interpolado a partir de todas as amostras lidas do Revit (ReferenceIntersector).
Uso como módulo: from terreno import zt; zt(x, y) -> cota (m). IDW com os 8 vizinhos num raio de 6 m."""
import numpy as np, os
F = r"D:\Projeto Modelagem\FERRAMENTAS"
_pts = []
for fn, cols in ((F + r"\eletrica\work\amostras_z.csv", (3, 4, 5)), (F + r"\auditoria_afesg\af_amostras_z.csv", (2, 3, 4)),
                 (F + r"\drenagem_scripts\work\terreno_z.csv", (0, 1, 2)), (F + r"\contencao\work\amostras_cnt_z.csv", (4, 5, 6)),
                 (F + r"\contencao\work\amostras_cnt2_z.csv", (4, 5, 6)), (F + r"\compat_geral\work\amostras_extra_z.csv", (1, 2, 3))):
    if not os.path.exists(fn): continue
    for line in open(fn, encoding='utf-8-sig'):
        q = line.strip().split(';')
        try:
            x, y, z = float(q[cols[0]]), float(q[cols[1]]), float(q[cols[2]])
            if 120 < z < 150: _pts.append((x, y, z))
        except Exception: pass
P = np.array(_pts)
_cell = {}
for i, (x, y, z) in enumerate(P): _cell.setdefault((int(x // 4), int(y // 4)), []).append(i)


def zt(x, y, r=6.0):
    cx, cy = int(x // 4), int(y // 4); idx = []
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2): idx += _cell.get((cx + dx, cy + dy), [])
    if not idx: return float('nan')
    Q = P[idx]; d = np.hypot(Q[:, 0] - x, Q[:, 1] - y); k = np.argsort(d)[:8]
    if d[k[0]] > r: return float('nan')
    w = 1 / np.maximum(d[k], 0.05) ** 2
    return float((Q[k, 2] * w).sum() / w.sum())
