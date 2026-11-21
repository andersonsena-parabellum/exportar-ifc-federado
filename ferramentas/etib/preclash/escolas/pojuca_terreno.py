# -*- coding: utf-8 -*-
"""Pojuca — congela o TERRENO para o preclash (escolas/dados/pojuca_terreno.npz). Versão 3 (19/10/2026): IMP AS BUILT.

Fonte: o IMP as built (24-049-PJC-CTO-ETIB-IMP.rvt), lido no Revit sem salvar por FERRAMENTAS/georef/work/POJUCA/scripts/
imp_pojuca_ler.cs (saída em work/POJUCA/imp/). As coordenadas compartilhadas do IMP são o UTM do TOP-001 (as plataformas
caem em cima dos blocos da SIT corrigida e o terreno natural bate com os pontos do TOP: mediana +0,10 m).
Superfície acabada, na ordem de prioridade (o primeiro que existir no ponto):
  1. pisos externos do IMP (topo das lajes "Genérico 150 mm": 61,00 no platô principal, 61,89/61,90 no campo e no pátio, 59,58-60,81 ao norte);
  2. toposolids das plataformas (ids >= 663000);
  3. toposolid do terreno modificado (661883: taludes e cortes em volta das plataformas);
  4. toposolid do terreno natural (619527).
Grade de 1,0 m na caixa do IMP; fora dela, pontos do TOP-001 e uma grade de 10 m por inverso da distância.
Linhas da SIT R04 para o visualizador. Só LÊ os dados da thread da escola.
Uso: .venv/Scripts/python.exe -X utf8 escolas/pojuca_terreno.py
"""
import os, sys, re, csv, json
import numpy as np

W = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\POJUCA'
sys.path.insert(0, os.path.join(W, 'scripts'))
import deep                                   # noqa: E402  (leitor do dump dos DWG)
from pojuca_comum import fundo_sit            # noqa: E402
from imp_raster import raster, X0, Y0, PASSO, NX, NY   # noqa: E402  (rasteriza o topo das faces, máximo z por célula)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'pojuca_terreno.npz')
CAIXA = (572350.0, 8626400.0, 572600.0, 8626640.0)


def triangulos(fn):
    R = list(csv.reader(open(os.path.join(W, 'imp', fn), encoding='utf-8'), delimiter=';'))[1:]
    tri = np.array([[tuple(map(float, x.split(','))) for x in r[2:5]] for r in R])
    return tri, np.array([float(r[5]) for r in R]), np.array([int(r[1]) for r in R])


tt, tnz, tid = triangulos('imp_topo.csv'); pt_, pnz, pid = triangulos('imp_pisos.csv')
camadas = [raster(pt_[pnz > 0.2]),                                  # 1. pisos externos
           raster(tt[(tnz > 0.2) & (tid >= 663000)]),               # 2. plataformas
           raster(tt[(tnz > 0.2) & (tid == 661883)]),               # 3. terreno modificado
           raster(tt[(tnz > 0.2) & (tid == 619527)])]               # 4. terreno natural
Z = np.full((NY, NX), np.nan); fonte_cel = np.zeros((NY, NX), int)
for k, c in enumerate(camadas, 1):
    m = np.isnan(Z) & ~np.isnan(c); Z[m] = c[m]; fonte_cel[m] = k
passo = int(round(1.0 / PASSO))                                    # grade de 1 m a partir do raster de 0,5 m
Zs = Z[::passo, ::passo]; gx = X0 + np.arange(NX)[::passo] * PASSO; gy = Y0 + np.arange(NY)[::passo] * PASSO
GX, GY = np.meshgrid(gx, gy); ok = ~np.isnan(Zs)
imp = np.column_stack([GX[ok], GY[ok], Zs[ok]])
bx = (gx.min(), gy.min(), gx.max(), gy.max())

# ---- fora da caixa do IMP: TOP-001 e grade de 10 m por inverso da distância
TOP = deep.load(os.path.join(W, 'dump', 'deep_TOP-001-PLT-R00.tsv'))
nat = [e['p'][0] for e in TOP if e['t'] == 'POINT' and e['l'] == 'TOP-COTAS']
for e in TOP:
    if e['t'] == 'PL' and e['l'] in ('MalhaTriTG', 'CurvasTG'):
        nat += [p for p in e['p'] if p[2] > 50]
nat = np.unique(np.round(np.array(nat), 3), axis=0)
fora_box = lambda P: (P[:, 0] < bx[0] - 0.5) | (P[:, 0] > bx[2] + 0.5) | (P[:, 1] < bx[1] - 0.5) | (P[:, 1] > bx[3] + 0.5)
fora = nat[fora_box(nat)]
cx = np.arange(CAIXA[0], CAIXA[2] + 0.01, 10.0); cy = np.arange(CAIXA[1], CAIXA[3] + 0.01, 10.0)
C = np.array([(x, y) for y in cy for x in cx]); C = C[fora_box(C)]
ref = np.vstack([nat, imp[::7]])
d = np.hypot(C[:, None, 0] - ref[None, :, 0], C[:, None, 1] - ref[None, :, 1])
k = np.argsort(d, axis=1)[:, :8]; dk = np.take_along_axis(d, k, 1); w = 1 / np.maximum(dk, 0.1) ** 2
cantos = np.column_stack([C, (w * ref[k, 2]).sum(1) / w.sum(1)])

# ---- platôs da SIT (rótulos) só para referência no visualizador
T = json.load(open(os.path.join(W, 'work_translacoes.json')))['URB-001-SIT-R04']
S = deep.load(os.path.join(W, 'dump', 'deepx_URB-001-SIT-R04.tsv'))
rot = np.array([(e['p'][0][0] + T[0], e['p'][0][1] + T[1], float(f'{m.group(1)}.{m.group(2)}'))
                for e in S if e['t'] == 'TEXT' for m in [re.search(r'C:\s*(\d+)[,.](\d+)', e['txt'])] if m])

pts = np.vstack([imp, fora, cantos])
arq = np.array(fundo_sit(), float)
L = np.hypot(*(arq[:, 1] - arq[:, 0]).T)
arq = arq[L > 0.25]                            # tira mobiliário, hachuras e textos explodidos (o visualizador fica leve)
arq = np.unique(np.round(arq, 2).reshape(len(arq), 4), axis=0).reshape(-1, 2, 2)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
np.savez_compressed(OUT, pts=pts, arq=arq, rotulos=rot,
                    fonte=np.array('IMP as built (pisos externos, plataformas e taludes do 24-049-PJC-CTO-ETIB-IMP.rvt); '
                                   'TOP-001 fora da caixa do IMP'))
n = [int((fonte_cel[::passo, ::passo][ok] == k).sum()) for k in (1, 2, 3, 4)]
print('gravado', OUT, '| IMP', len(imp), '(pisos %d, plataformas %d, modificado %d, natural %d)' % tuple(n),
      '| TOP fora', len(fora), '| cantos', len(cantos), '| linhas SIT', len(arq))
