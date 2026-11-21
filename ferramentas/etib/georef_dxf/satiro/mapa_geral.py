# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — mapa geral da fase 2: todas as redes extraídas sobre a SIT (UTM), uma cor por disciplina.
Uso: python -I -X utf8 mapa_geral.py"""
import sys, os, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from esg_sat import arq_sit

W = sc.WRK
ld = lambda n: json.load(open(os.path.join(W, n), encoding='utf-8'))
camadas = []
af = ld('af_rede.json')
camadas.append(('AF / alimentação / reúso', '#1f77b4', [t['pts'] for t in af['trechos']], 1.4, '-'))
esg = ld('esg_rede.json')
camadas.append(('Esgoto (TQ)', '#8c564b', [t['pts'] for t in esg['trechos']], 2.2, '-'))
ap = ld('ap_rede.json')
camadas.append(('Pluvial enterrada (AP)', '#17becf', [t['pts'] for t in ap['trechos'] if not t['classe'].startswith('calha')], 1.6, '-'))
camadas.append(('Calhas da cobertura (AP, aéreas)', '#ff7f0e', [t['pts'] for t in ap['trechos'] if t['classe'].startswith('calha')], 1.0, ':'))
cps = ld('cps_dre_rede.json')
camadas.append(('Drenagem do campo (CPS DRE)', '#2ca02c', [t['pts'] for t in cps['trechos']], 1.4, '-'))
dre = ld('dre_rede.json') if os.path.exists(os.path.join(W, 'dre_rede.json')) else None
if dre: camadas.append(('Macrodrenagem 2×Ø1200 (rede futura)', '#9467bd', [t['pts'] for t in dre['trechos']], 3.0, '-'))
ele = ld('ele_rede.json')
camadas.append(('Elétrica (EL-001/002 + CPS)', '#d62728', [t['pts'] for k in ele for t in ele[k]['trechos']], 1.2, '--'))
pci = ld('pci_rede.json')
camadas.append(('PCI hidrantes', '#e377c2', [t['pts'] for t in pci['HID']['trechos']], 2.0, '-'))
camadas.append(('PCI SDAI', '#bcbd22', [t['pts'] for t in pci['SDAI']['trechos']], 1.2, '--'))
fig, ax = plt.subplots(figsize=(18, 18))
ax.add_collection(LineCollection(arq_sit(), colors='0.85', linewidths=0.3))
for nome, cor, L, lw, ls in camadas:
    tot = 0.0
    for p in L:
        p = np.array(p); ax.plot(p[:, 0], p[:, 1], ls, color=cor, lw=lw, alpha=0.9)
        tot += float(np.hypot(*np.diff(p, axis=0).T).sum())
    ax.plot([], [], ls, color=cor, lw=2, label=f'{nome}: {tot:.0f} m')
ax.legend(loc='upper left', fontsize=10)
ax.set_xlim(545845, 546060); ax.set_ylim(8716085, 8716275); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
ax.set_title('ETIB Sátiro Dias — redes extraídas dos CADs referenciados (fase 2), UTM SIRGAS 2000 / 24S, sobre a SIT R06 corrigida')
fig.savefig(os.path.join(sc.REL, 'SAT_fase2_mapa_geral.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
print('ok')
