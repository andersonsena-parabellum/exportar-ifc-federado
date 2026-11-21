# -*- coding: utf-8 -*-
"""Sátiro Dias — contorno dos prédios (face externa) para a regra "só rede externa" (Anderson, 21/10/2026): o que fica dentro não
é modelado nem conta como conflito. Fonte: estrutura as built dos RVT de fundação (ETIB-SATIRO-DIAS/RELATORIOS/FASE2_REDES_2026-10-18/
SAT_fase2_estrutura.csv, georef_dxf/satiro/est_sat.py; BP4 ajustado pelos pilares): por arquivo de fundação (um prédio ou um corpo
do BP4), o fecho convexo da seção dos pilares (face externa do pilar = face da parede); a união dos corpos é fechada com 0,30 m e
os buracos são preenchidos. Bate com a base de arquitetura das pranchas de elétrica/incêndio (edificações a 37,96°).
Uso como módulo (contornos(), uniao(), dentro(), cortar()) ou direto para a imagem de conferência."""
import csv, os, math
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPoint, box
from shapely.ops import unary_union
from shapely import affinity

EST = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS\FASE2_REDES_2026-10-18\SAT_fase2_estrutura.csv'
FECHA = 4.5          # m: metade do maior vão entre pilares de fachada


def _secao(r):
    lx, ly = float(r['lx']), float(r['ly'])
    b = affinity.rotate(box(-lx / 2, -ly / 2, lx / 2, ly / 2), float(r['rot_graus']), origin=(0, 0))
    return affinity.translate(b, float(r['E']), float(r['N']))


def contornos():
    por = {}
    for r in csv.DictReader(open(EST, encoding='utf-8-sig'), delimiter=';'):
        por.setdefault(r['arquivo'], []).append(r)
    out = []
    for arq, rs in sorted(por.items()):
        pil = [_secao(r) for r in rs if 'Pilar' in r['categoria']] or [_secao(r) for r in rs]
        if 'BP4' in arq:
            # corpos do BP4: fechamento de R metros (vão entre pilares da fachada) em vez do fecho convexo, para o corpo em L não
            # engolir o pátio descoberto do canto
            h = unary_union(pil).buffer(FECHA, join_style=2, mitre_limit=10).buffer(-FECHA, join_style=2, mitre_limit=10)
            h = unary_union([Polygon(g.exterior) for g in (h.geoms if hasattr(h, 'geoms') else [h])])
        else:                                   # prédios retangulares (quadra coberta, guarita, vestiário, subestação...)
            h = MultiPoint([p for b in pil for p in b.exterior.coords]).convex_hull
        nome = arq.split('-ETIB-')[1].split('-')[0] + ('' if 'BP4' not in arq else ' ' + arq.split('R00_')[-1].replace('.rvt', ''))
        out.append((nome, h))
    return out


def uniao():
    U = unary_union([p for _, p in contornos()]).buffer(0.30, join_style=2).buffer(-0.30, join_style=2)
    gs = U.geoms if hasattr(U, 'geoms') else [U]
    return unary_union([Polygon(g.exterior) for g in gs])


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
    F2 = os.path.dirname(EST)
    fig, ax = plt.subplots(figsize=(18, 17))
    for fn, cor in (('SAT_fase2_ESG_trechos.csv', 'brown'), ('SAT_fase2_AP_trechos.csv', 'c'), ('SAT_fase2_ELE_trechos.csv', 'orange'),
                    ('SAT_fase2_PCI_trechos.csv', 'm'), ('SAT_fase2_AF_trechos.csv', 'b'), ('SAT_fase2_CPS-DRE_trechos.csv', 'g')):
        for r in csv.DictReader(open(os.path.join(F2, fn), encoding='utf-8-sig'), delimiter=';'):
            ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color=cor, lw=0.7)
    U = uniao()
    for g in (U.geoms if hasattr(U, 'geoms') else [U]):
        x, y = g.exterior.xy; ax.fill(x, y, alpha=0.25, color='k')
    for n, p in contornos(): ax.text(p.centroid.x, p.centroid.y, n, fontsize=7); [ax.plot(*g.exterior.xy, lw=0.8) for g in (p.geoms if hasattr(p, "geoms") else [p])]
    ax.set_aspect('equal'); ax.set_xlim(545840, 546070); ax.set_ylim(8716080, 8716290)
    fig.savefig(sys.argv[1] if len(sys.argv) > 1 else 'predios_sat.png', dpi=60, bbox_inches='tight')
    print([(n, round(p.area, 1)) for n, p in contornos()], round(U.area, 1))
