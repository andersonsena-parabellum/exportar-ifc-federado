# -*- coding: utf-8 -*-
"""Pojuca — conferência: pilares e fundações as built (forma real, UTM) × redes do projeto × linhas da SIT."""
import csv, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\POJUCA\scripts')
import pjc_estrutura as ES
from pojuca_comum import fundo_sit
REL = r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS'
fig, ax = plt.subplots(figsize=(22, 20))
for s in fundo_sit():
    ax.plot([s[0][0], s[1][0]], [s[0][1], s[1][1]], color='0.8', lw=.25)
for b in ES.BLOCOS:
    for tipo in ('FUN', 'ECC', 'EMT'):
        pec = ES._tri(b, tipo)
        if not pec: continue
        tr = ES.transformacao(b, tipo, pec)
        for cat, tp, T in pec.values():
            if cat not in ('pilar', 'fundacao'): continue
            P = ES._utm(T.reshape(-1, 3), tr)
            ax.plot(P[:, 0], P[:, 1], ',', color='k' if cat == 'pilar' else 'm', ms=1)
for n, p in ES.contornos():
    ax.plot(*p.exterior.xy, color='r', lw=1); ax.text(p.centroid.x, p.centroid.y, n, color='r')
for fn, cor in (('PJC_fase2_ESG_trechos.csv', 'saddlebrown'), ('PJC_fase2_DRE_trechos.csv', 'g')):
    for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
        ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color=cor, lw=.8)
for fn, cor in (('PJC_fase2_AF_trechos.csv', 'b'), ('PJC_fase2_ELE_trechos.csv', 'orange'), ('PJC_fase2_PCI_trechos.csv', 'r')):
    for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
        P = np.array([[float(v) for v in xy.split(',')] for xy in r['vertices_UTM'].split(';') if xy]); ax.plot(P[:, 0], P[:, 1], color=cor, lw=.8)
ax.set_aspect('equal'); ax.set_xlim(572380, 572560); ax.set_ylim(8626440, 8626610)
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PJC_predios_estrutura.png'), dpi=70, bbox_inches='tight')
