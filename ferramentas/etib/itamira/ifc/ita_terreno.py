# -*- coding: utf-8 -*-
"""Aporá Itamira — terreno acabado (22/10/2026): o npz de 18/10 (georef/work/ITAMIRA/scr/asbuilt_terreno.py) só tinha o sólido
topográfico do IFC as built do IMP (~237,85 no campo), e as tampas das caixas, os ralos e os eletrodutos executados do campo estão
referidos ao piso acabado (grama sintética e pista de concreto, topo 238,08; pisos de 238,00 a 238,25 em volta). Vale a superfície
de cima: onde há piso no as built (IfcSlab, faces de topo), a cota é a do piso; fora dele, o sólido topográfico.
Grava escolas/dados/itamira_terreno.npz (pts; a ferramenta triangula) e guarda o anterior em itamira_terreno_solido.npz.
Uso: .venv/Scripts/python.exe -X utf8 itamira/ifc/ita_terreno.py"""
import os, sys, shutil
import numpy as np
import ifcopenshell, ifcopenshell.geom as G
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno

DADOS = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados'
NPZ = os.path.join(DADOS, 'itamira_terreno.npz'); ANT = os.path.join(DADOS, 'itamira_terreno_solido.npz')
IFC = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA\REFERENCIAS_RVT\IFC\24-049-APR-ITA-ETIB-IMP-PE-001-MOD-R00.ifc'
PASSO = 0.5


def topos():
    """triângulos de topo (normal para cima) de todos os pisos do as built, em UTM (o IFC do IMP já está nas coordenadas UTM)."""
    f = ifcopenshell.open(IFC); s = G.settings(); s.set(s.USE_WORLD_COORDS, True)
    T = []
    for e in f.by_type('IfcSlab'):
        try: sh = G.create_shape(s, e)
        except Exception: continue
        v = np.array(sh.geometry.verts).reshape(-1, 3); fc = np.array(sh.geometry.faces).reshape(-1, 3)
        for a, b, c in v[fc]:
            n = np.cross(b - a, c - a)
            if np.linalg.norm(n) > 1e-9 and n[2] / np.linalg.norm(n) > 0.9: T.append((a, b, c))
    return np.array(T)


def main():
    if not os.path.exists(ANT): shutil.copy2(NPZ, ANT)
    ter = Terreno(ANT)
    T = topos(); print('faces de topo dos pisos', len(T))
    polis = [Polygon(t[:, :2]) for t in T if Polygon(t[:, :2]).area > 1e-6]
    U = unary_union(polis); Up = prep(U)
    x0, y0, x1, y1 = U.bounds
    X, Y = np.meshgrid(np.arange(x0, x1 + PASSO, PASSO), np.arange(y0, y1 + PASSO, PASSO))
    Q = np.column_stack([X.ravel(), Y.ravel()])
    Q = np.array([q for q in Q if Up.contains(Point(q))])
    # cota do piso em cada ponto: a face de topo mais alta que contém o ponto (baricêntrica)
    Z = np.full(len(Q), np.nan)
    for a, b, c in T:
        mn = np.minimum(np.minimum(a, b), c)[:2]; mx = np.maximum(np.maximum(a, b), c)[:2]
        k = np.nonzero((Q[:, 0] >= mn[0] - 1e-6) & (Q[:, 0] <= mx[0] + 1e-6) & (Q[:, 1] >= mn[1] - 1e-6) & (Q[:, 1] <= mx[1] + 1e-6))[0]
        if not len(k): continue
        M = np.array([[b[0] - a[0], c[0] - a[0]], [b[1] - a[1], c[1] - a[1]]])
        if abs(np.linalg.det(M)) < 1e-12: continue
        uv = np.linalg.solve(M, (Q[k] - a[:2]).T).T
        ok = (uv[:, 0] >= -1e-6) & (uv[:, 1] >= -1e-6) & (uv.sum(1) <= 1 + 1e-6)
        z = a[2] + uv[ok, 0] * (b[2] - a[2]) + uv[ok, 1] * (c[2] - a[2])
        Z[k[ok]] = np.fmax(Z[k[ok]], z)
    Q, Z = Q[~np.isnan(Z)], Z[~np.isnan(Z)]
    P0 = ter.pts
    fora = np.array([not Up.contains(Point(p[:2])) for p in P0])
    P = np.vstack([P0[fora], np.column_stack([Q, Z])])
    d0 = np.load(ANT, allow_pickle=True)
    extra = {k: d0[k] for k in d0.files if k not in ('pts', 'tri')}
    np.savez_compressed(NPZ, pts=P, fonte=np.array('IFC as built do IMP: sólido topográfico + topo dos pisos (22/10/2026)'),
                        **{k: v for k, v in extra.items() if k != 'fonte'})
    print(f'terreno: {fora.sum()} pontos do sólido fora dos pisos + {len(Q)} pontos de piso (cota {Z.min():.2f} a {Z.max():.2f}) -> {NPZ}')


if __name__ == '__main__':
    main()
