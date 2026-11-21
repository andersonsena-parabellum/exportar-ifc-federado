# -*- coding: utf-8 -*-
"""Planta local das redes da Catu (como o adaptador do preclash carrega) numa janela: E N meia_largura [arquivo.png].
Uso: .venv/Scripts/python.exe -X utf8 georef/catu_plot_local.py 567723 8634671 12 saida.png"""
import sys, os
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from escolas import catu

COR = {'AF': '#1f77b4', 'ESG': '#8c564b', 'DRE': '#17becf', 'HID': '#d62728', 'SDAI': '#ff7f0e', 'ELE': '#2ca02c'}


def main(E0, N0, r, fn):
    D = catu.carregar()
    fig, ax = plt.subplots(figsize=(12, 12))
    arq = np.load(catu.TERRENO)['arq']
    for a, b in arq:
        if min(abs(a[0] - E0), abs(b[0] - E0)) < r * 1.5 and min(abs(a[1] - N0), abs(b[1] - N0)) < r * 1.5:
            ax.plot([a[0], b[0]], [a[1], b[1]], color='#bbbbbb', lw=0.8)
    for e in D['elementos']:
        p = e['pts']
        if not ((np.abs(p[:, 0] - E0) < r) & (np.abs(p[:, 1] - N0) < r)).any(): continue
        ax.plot(p[:, 0], p[:, 1], color=COR.get(e['disc'], 'k'), lw=1.2 if e['disc'] in ('ESG', 'DRE') else 0.9)
        m = p[len(p) // 2]
        ax.text(m[0], m[1], f"{e['trecho']}\n{p[:, 2].min():.2f}", fontsize=6, color=COR.get(e["disc"], "k"), clip_on=True)
    for c in D['caixas']:
        if abs(c['E'] - E0) > r or abs(c['N'] - N0) > r: continue
        h = c.get('meia', c.get('r', 0.3))
        ax.add_patch(plt.Rectangle((c['E'] - h, c['N'] - h), 2 * h, 2 * h, fill=False, ec=COR.get(c['disc'], 'k'), lw=1))
        ax.text(c['E'], c['N'], f"{c['info'].get('nome')}\nCT{c['zt']:.2f} F{c['zb']:.2f}", fontsize=6, clip_on=True)
    ax.set_xlim(E0 - r, E0 + r); ax.set_ylim(N0 - r, N0 + r); ax.set_aspect('equal'); ax.grid(lw=0.3)
    fig.savefig(fn, dpi=130, bbox_inches='tight'); print(fn)


if __name__ == '__main__':
    main(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
