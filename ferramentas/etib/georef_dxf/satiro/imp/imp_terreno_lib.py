# -*- coding: utf-8 -*-
"""Terreno do IMP as built (Sátiro Dias): lê os triângulos exportados do Revit (imp_topo.csv / imp_pisos.csv, UTM e cota
absoluta) e rasteriza a superfície de cima de cada sólido topográfico/piso numa grade regular."""
import csv, os, collections
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))


def ler(fn):
    R = []
    for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
        a, b, c = [np.array(list(map(float, r[k].split(',')))) for k in ('a', 'b', 'c')]
        R.append((r['tag'], r['id'], a, b, c, float(r['nz'])))
    return R


def triangulos(ids=None, nz_min=0.2):
    T = ler(os.path.join(AQUI, 'imp_topo.csv')) + ler(os.path.join(AQUI, 'imp_pisos.csv'))
    g = collections.defaultdict(list)
    for t in T:
        if t[5] > nz_min and (ids is None or t[1] in ids): g[t[1]].append(np.array([t[2], t[3], t[4]]))
    return {k: np.array(v) for k, v in g.items()}


def raster(tris, X, Y):
    """z da face de cima (o maior z entre as faces que cobrem o ponto) na grade X, Y; NaN onde não há face."""
    Z = np.full(X.shape, np.nan)
    x0, y0 = X[0, 0], Y[0, 0]; dx = X[0, 1] - X[0, 0]; dy = Y[1, 0] - Y[0, 0]
    for A in tris:
        p = A[:, :2]
        i0 = max(0, int(np.floor((p[:, 0].min() - x0) / dx))); i1 = min(X.shape[1] - 1, int(np.ceil((p[:, 0].max() - x0) / dx)))
        j0 = max(0, int(np.floor((p[:, 1].min() - y0) / dy))); j1 = min(X.shape[0] - 1, int(np.ceil((p[:, 1].max() - y0) / dy)))
        if i1 < i0 or j1 < j0: continue
        xs = X[j0:j1 + 1, i0:i1 + 1]; ys = Y[j0:j1 + 1, i0:i1 + 1]
        v0 = p[1] - p[0]; v1 = p[2] - p[0]; den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12: continue
        wx = xs - p[0, 0]; wy = ys - p[0, 1]
        u = (wx * v1[1] - v1[0] * wy) / den; v = (v0[0] * wy - wx * v0[1]) / den
        m = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
        if not m.any(): continue
        z = A[0, 2] + u * (A[1, 2] - A[0, 2]) + v * (A[2, 2] - A[0, 2])
        blk = Z[j0:j1 + 1, i0:i1 + 1]
        blk[m] = np.where(np.isnan(blk[m]), z[m], np.maximum(blk[m], z[m]))
    return Z
