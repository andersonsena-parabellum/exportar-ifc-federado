# -*- coding: utf-8 -*-
"""Contorno dos prédios (face externa) para a regra "só rede externa" (Anderson, 21/10/2026): o que fica dentro não é modelado
nem conta como conflito. Fonte: FERRAMENTAS/eletrica/work/blocos.json (15/10/2026: pilares, baldrames e fundação de cada bloco
as built, fecho convexo por peça, união com fechamento de 0,30 m, buracos preenchidos), em coordenadas internas
(UTM − 561500/8658000). Uso como módulo (contornos(), dentro(), cortar()) ou direto para a imagem de conferência."""
import json, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

ARQ = r'D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\blocos.json'
O = np.array([561500.0, 8658000.0])


def contornos(utm=True):
    out = []
    for b in json.load(open(ARQ, encoding='cp1252')):
        P = np.array(b['coords'], float)
        if utm: P = P + O
        out.append((b['bloco'], Polygon(P)))
    return out


def uniao(utm=True):
    return unary_union([p for _, p in contornos(utm)])


def dentro(U, p, tol=0.0):
    """ponto (E, N) dentro de algum prédio (tol > 0 encolhe o prédio: a face fica de fora)."""
    return U.buffer(-tol).contains(Point(float(p[0]), float(p[1])))


def cortar(U, P):
    """polilinha 3D -> pedaços FORA dos prédios (lista de arrays n×3), com a cota interpolada no corte."""
    P = np.asarray(P, float)
    if len(P) < 2: return [P]
    L = LineString(P[:, :2])
    if not L.intersects(U): return [P]
    fora = L.difference(U)
    if fora.is_empty: return []
    S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
    pecas = []
    for g in (fora.geoms if hasattr(fora, 'geoms') else [fora]):
        if g.length < 0.05: continue
        Q = np.array(g.coords)
        s = np.array([L.project(Point(q)) for q in Q])
        z = np.interp(s, S, P[:, 2]) if S[-1] > 0 else np.full(len(Q), P[0, 2])
        pecas.append(np.column_stack([Q, z]))
    return pecas


if __name__ == '__main__':
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import alh_modelo as AM
    fig, ax = plt.subplots(figsize=(14, 18))
    for f, cor in (('HS', 'tab:blue'), ('DRN', 'tab:green'), ('ELE', 'tab:orange'), ('INC', 'tab:red')):
        for s in AM.ler_segs(f): ax.plot([s['a'][0], s['b'][0]], [s['a'][1], s['b'][1]], color=cor, lw=0.6)
    for b, p in contornos(utm=False):
        x, y = p.exterior.xy; ax.fill(x, y, alpha=0.25, color='k'); ax.text(p.centroid.x, p.centroid.y, b, fontsize=9)
    ax.set_aspect('equal'); fig.savefig(r'C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\02bc9bcd-33aa-469b-90c1-598fe5356696\scratchpad\predios.png', dpi=70)
    print([(b, round(p.area, 1)) for b, p in contornos()])
