# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — congela o TERRENO PROVISÓRIO num arquivo próprio do preclash (escolas/dados/apora_aurea_terreno.npz).
Só LÊ os dados da thread da escola (FERRAMENTAS/georef/work/APORA: terreno_provisorio.py / rede/terreno_pts.npz e o DXF da SIT).

Terreno escolhido (o do IMP as built, recomendado, só sai no Revit): superfície da SIT R01 (pontos CotaZ + curvas MDT1),
a única que cobre o trajeto inteiro e a que o projeto de drenagem usou nas CT, com o platô da quadra 188,00 (linhas
Q-PLATO da terraplanagem) por cima. O TOP-001 fica 1,1 m abaixo (mediana) a leste da quadra: ver o LEIA-ME da escola.
Rodar de novo quando vier o terreno do IMP as built.
Uso: .venv/Scripts/python.exe -X utf8 preclash/escolas/apora_aurea_terreno.py
"""
import os, sys, re, json
import numpy as np
import matplotlib.tri as mtri

APORA = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\APORA'
sys.path.insert(0, APORA + r'\scr')
from dxflite import load          # noqa: E402
import geoalign as ga             # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'apora_aurea_terreno.npz')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
O = np.array([600000.0, 8711300.0])
CAIXA = (600000.0, 8711215.0, 600125.0, 8711420.0)

D = np.load(APORA + r'\rede\terreno_pts.npz')
P = D['SIT']                                   # (n,3) E, N, z — CotaZ + MDT1 da SIT, sem picos
hull = D['hull']                               # contorno do platô da quadra (fecho das linhas Q-PLATO, ~188,00)
tri = mtri.Triangulation(P[:, 0] - O[0], P[:, 1] - O[1])            # Delaunay em coordenadas locais (estável)
xy = np.c_[P[:, 0] - O[0], P[:, 1] - O[1]][tri.triangles]
lados = np.max(np.linalg.norm(xy - np.roll(xy, 1, axis=1), axis=2), axis=1)
T = tri.triangles[lados <= 45]                 # sem os triângulos compridos da borda (não extrapola)

# linhas da SIT (edificações, muros, meio-fio, cercas) para o custo dos desvios em planta
T2 = np.array(json.load(open(APORA + r'\transf_SIT_para_UTM.json', encoding='utf-8'))['matriz_2x3'])
sit = load(APORA + r'\dxf\24-049-APR-CTO-ETIB-IMP-PE-URB-001-SIT-R01.dxf')
TOPO = re.compile(r'^(TOP-ARVORE|TOP-COTAS|PONTO|GRADE|MALHA|CurvasTG|COTAS DAS CURVAS|MDT|PN$|HACH|MOB|AC-|PB_ETI_1PAV)', re.I)
S = ga.segmentos([p for p in sit.walk('model') if p.type in ('LINE', 'LWPOLYLINE', 'POLYLINE') and not TOPO.search(p.layer or '')])
S = np.einsum('ij,nkj->nki', T2[:, :2], S) + T2[:, 2]
L = np.linalg.norm(S[:, 1] - S[:, 0], axis=1)
m = (L > 0.3) & np.all((S[:, :, 0] > CAIXA[0]) & (S[:, :, 0] < CAIXA[2]) & (S[:, :, 1] > CAIXA[1]) & (S[:, :, 1] < CAIXA[3]), axis=1)
S = S[m]

np.savez_compressed(OUT, pts=P, tri=T, plat_n=np.array([len(hull)]), plat_xy=hull, plat_z=np.array([188.0]), arq=S,
                    fonte=np.array('provisório: SIT R01 (CotaZ + MDT1) + platô da quadra 188,00 (TER); trocar pelo IMP as built'))
print('gravado', OUT, '| pontos', len(P), '| triângulos', len(T), '| platô 188,00 com', len(hull), 'vértices | linhas SIT', len(S))

# variante para o cenário de sensibilidade: TOP-001 (+ platô) no norte, onde ele existe, e SIT no sul
from matplotlib.path import Path            # noqa: E402
TOP = D['TOP']
hp = sorted(map(tuple, TOP[:, :2])); cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
lo, up = [], []
for q in hp:
    while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
    lo.append(q)
for q in reversed(hp):
    while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0: up.pop()
    up.append(q)
ht = np.array(lo[:-1] + up[:-1])
P2 = np.vstack([TOP, P[~Path(ht).contains_points(P[:, :2], radius=3.0)]])
tri2 = mtri.Triangulation(P2[:, 0] - O[0], P2[:, 1] - O[1])
xy2 = np.c_[P2[:, 0] - O[0], P2[:, 1] - O[1]][tri2.triangles]
T2b = tri2.triangles[np.max(np.linalg.norm(xy2 - np.roll(xy2, 1, axis=1), axis=2), axis=1) <= 45]
OUT2 = OUT.replace('_terreno.npz', '_terreno_top.npz')
np.savez_compressed(OUT2, pts=P2, tri=T2b, plat_n=np.array([len(hull)]), plat_xy=hull, plat_z=np.array([188.0]), arq=S,
                    fonte=np.array('sensibilidade: TOP-001 + platô 188 no norte, SIT no sul'))
print('gravado', OUT2, '| pontos', len(P2), '| triângulos', len(T2b))
