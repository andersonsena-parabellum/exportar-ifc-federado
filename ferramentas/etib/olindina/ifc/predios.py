# -*- coding: utf-8 -*-
"""Olindina — contorno dos prédios (face externa) para a regra "só rede externa" (Anderson, 21/10/2026): o que fica dentro não é
modelado nem conta como conflito. Fontes (lidas no Revit em 22/10/2026, FERRAMENTAS/georef/work/OLINDINA/imp/):
  - BA5 (ampliação): fecho convexo da seção dos pilares as built (ba5_ECC_tri.csv, posicionado pelo vínculo do BA5 no IMP; a fila
    de pilares bate com as paredes do BA5 na base das pranchas);
  - prédios existentes: não entram. O IMP só os traz como massas aproximadas (imp_massas.csv), que caem por cima do esgoto e da
    pluvial existentes do cadastro; as redes novas só chegam no BA5 (a elétrica sai do QGBT, na ponta desenhada).
Uso como módulo (contornos(), uniao(), dentro(), cortar(), ba5_utm()) ou direto para a imagem de conferência."""
import csv, os, math
import numpy as np
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import unary_union

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\imp'
# vínculo do BA5 no IMP (imp_vinculos.csv: ARQ, FUN e ECC com a mesma transformação): origem UTM/cota e giro
BA5_O = np.array([573794.1702, 8743245.0360, 168.2200]); BA5_ANG = 135.270833


def ba5_utm(P):
    """coordenadas internas do RVT do BA5 (m) -> UTM / cota."""
    P = np.asarray(P, float); a = math.radians(BA5_ANG); c, s = math.cos(a), math.sin(a)
    return np.column_stack([BA5_O[0] + c * P[:, 0] - s * P[:, 1], BA5_O[1] + s * P[:, 0] + c * P[:, 1], BA5_O[2] + P[:, 2]])


def tri_ba5(arq):
    """{id: (categoria, tipo, triângulos n×3×3 em UTM)} de ba5_<FUN|ECC>_tri.csv."""
    out = {}
    for r in csv.DictReader(open(os.path.join(IMP, arq), encoding='utf-8'), delimiter=';'):
        T = np.array([[float(r[k + c]) for c in 'xyz'] for k in 'abc'])
        out.setdefault(r['id'], [r['categoria'], r['tipo'], []])[2].append(ba5_utm(T))
    return {k: (v[0], v[1], np.array(v[2])) for k, v in out.items()}


def contornos():
    out = []
    pil = [T for cat, _, T in tri_ba5('ba5_ECC_tri.csv').values() if cat == 'pilar']
    out.append(('BA5', MultiPoint([tuple(p[:2]) for T in pil for p in T.reshape(-1, 3)]).convex_hull))
    return out


def uniao():
    return unary_union([p for _, p in contornos()])


def dentro(U, p, tol=0.0):
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
    import sys
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    F2 = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS\FASE2_REDES_2026-10-21'
    fig, ax = plt.subplots(figsize=(14, 16))
    for fn, cor in (('ONN_fase2_ESG_trechos.csv', 'brown'), ('ONN_fase2_AP_trechos.csv', 'g')):
        for r in csv.DictReader(open(os.path.join(F2, fn), encoding='utf-8-sig'), delimiter=';'):
            ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color=cor, lw=0.7)
    for r in csv.DictReader(open(os.path.join(F2, 'ONN_fase2_pressurizadas.csv'), encoding='utf-8-sig'), delimiter=';'):
        P = np.array([list(map(float, v.split(','))) for v in r['vertices_UTM'].split()]); ax.plot(P[:, 0], P[:, 1], lw=0.7)
    for n, p in contornos():
        for g in (p.geoms if hasattr(p, 'geoms') else [p]): ax.fill(*g.exterior.xy, alpha=0.2); ax.text(g.centroid.x, g.centroid.y, n, fontsize=8)
    ax.set_aspect('equal'); ax.set_xlim(573860, 573980); ax.set_ylim(8743220, 8743360); ax.ticklabel_format(useOffset=False, style='plain')
    fig.savefig(sys.argv[1] if len(sys.argv) > 1 else 'predios_onn.png', dpi=70, bbox_inches='tight')
    print([(n, round(p.area, 1)) for n, p in contornos()])
