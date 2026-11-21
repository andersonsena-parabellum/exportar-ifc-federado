# -*- coding: utf-8 -*-
"""Pojuca — mapa do as built (IFC da implantação, Forma direta) × redes do projeto (fase 2), por disciplina."""
import csv, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D = os.path.dirname(os.path.abspath(__file__)); REL = r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS'
R = list(csv.DictReader(open(os.path.join(D, 'PJC_ifc_asbuilt_redes.csv'), encoding='utf-8-sig'), delimiter=';'))
def disc(r):
    f = r['tipo_familia'].lower()
    if 'eletroduto' in f: return 'ELE'
    if 'pluvial' in f or 'corrugado' in f or 's\u00e9rie r' in f or 'areia' in f: return 'DRE'
    if 'esgoto' in f or 'ponta-bolsa' in f: return 'ESG'
    if 'cpvc' in f or 'hidrante' in f: return 'PCI'
    if 'torneira de jardim' in f or 'di\u00e2metro interno' in f or '\u00e1gua' in f: return 'AF'
    return None
COR = {'ELE': 'orange', 'DRE': 'green', 'ESG': 'saddlebrown', 'AF': 'blue', 'PCI': 'red'}
proj = {'ESG': 'PJC_fase2_ESG_trechos.csv', 'DRE': 'PJC_fase2_DRE_trechos.csv'}
fig, axs = plt.subplots(2, 3, figsize=(30, 20)); axs = axs.ravel()
for k, d in enumerate(['ESG', 'DRE', 'AF', 'ELE', 'PCI']):
    ax = axs[k]
    if d in proj:
        for r in csv.DictReader(open(os.path.join(REL, proj[d]), encoding='utf-8-sig'), delimiter=';'):
            ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color='0.6', lw=1.2)
    else:
        fn = {'AF': 'PJC_fase2_AF_trechos.csv', 'ELE': 'PJC_fase2_ELE_trechos.csv', 'PCI': 'PJC_fase2_PCI_trechos.csv'}[d]
        for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
            P = np.array([[float(v) for v in xy.split(',')] for xy in r['vertices_UTM'].split(';') if xy]); ax.plot(P[:, 0], P[:, 1], color='0.6', lw=1.2)
    n = 0
    for r in R:
        if disc(r) != d or not r['tipo_familia'].startswith('Forma direta'): continue
        n += 1
        ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color=COR[d], lw=2.0 if r['tipo'] == 'flowsegment' else 4)
    ax.set_title(f'{d}: cinza = projeto (fase 2), cor = as built do IFC ({n} peças)'); ax.set_aspect('equal'); ax.set_xlim(572380, 572560); ax.set_ylim(8626440, 8626600)
fig.savefig(os.path.join(D, 'PJC_asbuilt_x_projeto.png'), dpi=60, bbox_inches='tight')
import collections
print(collections.Counter((disc(r), r['tipo_familia']) for r in R if r['tipo_familia'].startswith('Forma direta')).most_common(60))
