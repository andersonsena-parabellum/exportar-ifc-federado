# -*- coding: utf-8 -*-
"""Rede extraída (JSON) sobre o DWG da disciplina, numa janela, para depurar ligações."""
import sys, json, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from comum import carrega

def plota(tag, js, x0, y0, x1, y1, saida, layers):
    D = carrega(tag); J = json.load(open(js, encoding='utf-8'))
    segs = []
    for d in D:
        p = d['pts'][:, :2]
        if d['layer'] in layers and d['tipo'] in ('LINE', 'PL', 'MLINE') and np.any((p[:, 0] > x0) & (p[:, 0] < x1) & (p[:, 1] > y0) & (p[:, 1] < y1)):
            segs.extend(zip(p[:-1], p[1:]))
    fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))
    ax.add_collection(LineCollection(segs, colors='0.6', linewidths=0.5))
    for t in J['trechos']:
        p = np.array(t['pts']); c = 'r' if t['sentido'] == 'indefinido' else ('b' if t['classe'] == 'coletor' else 'c')
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=1.2, alpha=0.7)
        ax.plot(*p[0], 'go', ms=3); ax.plot(*p[-1], 'kx', ms=4)
        m = p.mean(0)
        if x0 < m[0] < x1 and y0 < m[1] < y1: ax.text(*m, t['trecho'][4:], fontsize=6, clip_on=True)
    for n in J.get('nos', J.get('caixas', [])):
        c = np.array(n['c'])
        if x0 < c[0] < x1 and y0 < c[1] < y1:
            ax.plot(*c, '^' if n['tipo'] == 'AP' else 's', ms=6, mfc='none', mec='m'); ax.text(*c, n['id'], fontsize=6, color='m', clip_on=True)
    for v in J.get('verticais', []):
        c = np.array(v['c'])
        if x0 < c[0] < x1 and y0 < c[1] < y1: ax.plot(*c, 'o', ms=5, mfc='none', mec='orange')
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain')
    fig.savefig(saida, dpi=110, bbox_inches='tight'); plt.close(fig)

if __name__ == '__main__':
    a = sys.argv
    plota(a[1], a[2], *map(float, a[3:7]), a[7], a[8:])
