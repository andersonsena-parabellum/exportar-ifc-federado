# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — estrutura da quadra para o clash (forma real).
Pilares: os 14 IfcColumn do IFC as built do IMP (pilares metálicos da quadra), passados de coordenadas da SIT para UTM pela
transformação do referenciamento. Sapatas: QDC-FUN-001-LOC R01 e FUN-002-SAP R01 (pré-moldada, 14x SP-01 110x130, corte A com
1,05 m de altura; pedestal 60x75), uma por pilar, com a face de 1,30 m no sentido da fila de pilares (planta FUN-001: P1-P7 e
P8-P14 em duas filas a 24,50 m, vão de 5,53 m). Topo do concreto bruto 0,10 m abaixo do piso pronto da quadra (IFC as built),
fundo 1,05 m abaixo dele. Cotas do IMP com o mesmo deslocamento do terreno (DZ_IMP: platô 189,00 do IMP -> 188,00 da TER). Grava aurea/ifc/aur_estrutura.json (lista de peças em UTM) e confere o vão e a orientação.
Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_estrutura.py"""
import json, os, sys
import numpy as np
import ifcopenshell, ifcopenshell.geom as G
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aur_terreno_imp import imp_utm as utm, matriz, DZ_IMP        # noqa: E402

IFC = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\REFERENCIAS_RVT\IFC\24-049-APR-CTO-ETIB-IMP-PE-001-MOD-R00.ifc'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aur_estrutura.json')
SAP = (1.10, 1.30, 1.05)       # largura x comprimento (no sentido da fila) x altura
PED = (0.60, 0.75)
TOPO_ABAIXO_PISO = 0.10


def main():
    f = ifcopenshell.open(IFC); s = G.settings(); s.set(s.USE_WORLD_COORDS, True)
    M = matriz(); cols = []
    for e in f.by_type('IfcColumn'):
        v = np.array(G.create_shape(s, e).geometry.verts).reshape(-1, 3)
        c = utm(np.array([[(v[:, 0].min() + v[:, 0].max()) / 2, (v[:, 1].min() + v[:, 1].max()) / 2, v[:, 2].min()]]), M)[0]
        cols.append((e.GlobalId, e.Name, c, v[:, 2].max()))
    pisos = []
    for e in f.by_type('IfcSlab'):
        if 'Piso' not in (e.Name or ''): continue
        try: v = np.array(G.create_shape(s, e).geometry.verts).reshape(-1, 3)
        except Exception: continue
        pisos.append(utm(v, M))
    P = np.array([c[2] for c in cols])
    # direção da fila: maior autovetor das posições
    C0 = P[:, :2].mean(0); u, sv, vt = np.linalg.svd(P[:, :2] - C0); d = vt[0]; n = np.array([-d[1], d[0]])
    t = (P[:, :2] - C0) @ d; w = (P[:, :2] - C0) @ n
    print(f'{len(cols)} pilares | fila {np.degrees(np.arctan2(d[1], d[0])):.2f}° | t {np.sort(t).round(2)} | w {np.unique(np.round(w, 1))}')
    pecas = []
    for (gid, nome, c, zt), ti in zip(cols, t):
        # piso pronto junto do pilar: o topo mais alto dos pisos num raio de 1,5 m (base do pilar se não houver)
        zp = c[2]
        for V in pisos:
            k = np.hypot(V[:, 0] - c[0], V[:, 1] - c[1]) < 1.5
            if k.any(): zp = max(zp, V[k, 2].max()) if abs(V[k, 2].max() - c[2]) < 0.6 else zp
        zp += DZ_IMP; c = c + np.array([0, 0, DZ_IMP])
        ztopo = zp - TOPO_ABAIXO_PISO; zfundo = ztopo - SAP[2]
        pecas.append(dict(id=gid, nome=f'SAP-{nome.split(":")[-1][:12]}', pilar=nome, x=float(c[0]), y=float(c[1]), rot=float(np.arctan2(n[1], n[0])),
                          lx=SAP[1], ly=SAP[0], zb=float(zfundo), zt=float(ztopo - 0.0), pedestal=PED, piso=float(zp), base_pilar=float(c[2])))
    json.dump(dict(fonte='IFC as built do IMP (pilares) + QDC-FUN-001/002 R01 (sapatas)', pecas=pecas), open(OUT, 'w', encoding='utf-8'), indent=1)
    for p in pecas: print(f"{p['nome']:16s} {p['x']:.2f} {p['y']:.2f} piso {p['piso']:.2f} base pilar {p['base_pilar']:.2f} sapata {p['zb']:.2f}–{p['zt']:.2f}")
    print('gravado', OUT)


if __name__ == '__main__':
    main()
