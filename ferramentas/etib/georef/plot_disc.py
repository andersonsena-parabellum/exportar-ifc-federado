# -*- coding: utf-8 -*-
"""Plota uma região de uma disciplina (_GEO, UTM) com os layers da rede coloridos e os textos escritos,
para entender o desenho antes de extrair. Uso: python -I -X utf8 plot_disc.py ESG x0 y0 x1 y1 saida.png [layers...]"""
import sys, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from comum import carrega

ARQ = ('zw$7D57', 'zw$44A6', 'zw$D46B', 'ARQ BASE IMP', 'ARQ_IMP')


def plota(tag, x0, y0, x1, y1, saida, layers=None, textos=True, dpi=150, larg=18):
    D = carrega(tag)
    def dentro(p): return np.any((p[:, 0] > x0) & (p[:, 0] < x1) & (p[:, 1] > y0) & (p[:, 1] < y1))
    segs = collections.defaultdict(list); arq = []
    tx = []
    for d in D:
        p = d['pts'][:, :2]
        if not dentro(p): continue
        eh_arq = d['path'].startswith(ARQ) or d['layer'].upper().replace('-', '_').startswith('ARQ')
        if d['tipo'] in ('LINE', 'PL', 'MLINE'):
            q = p if not d.get('fechada') else np.vstack([p, p[:1]])
            s = list(zip(q[:-1], q[1:]))
            if eh_arq: arq.extend(s)
            elif layers is None or d['layer'] in layers: segs[d['layer'] + (' [MLINE]' if d['tipo'] == 'MLINE' else '')].extend(s)
        elif d['tipo'] in ('CIRCLE', 'ARC') and not eh_arq and (layers is None or d['layer'] in layers):
            t = np.linspace(0, 2 * np.pi, 25); c = p[0]
            q = np.column_stack([c[0] + d['r'] * np.cos(t), c[1] + d['r'] * np.sin(t)])
            segs[d['layer'] + ' (círculo)'].extend(zip(q[:-1], q[1:]))
        elif d['tipo'] == 'TEXT' and textos and not eh_arq and (layers is None or d['layer'] in layers or d['layer'] in ('Simbolos', 'TEXTOS')):
            tx.append((p[0], d['texto'], d['rot'], d['layer']))
    h = (y1 - y0) / (x1 - x0) * larg
    fig, ax = plt.subplots(figsize=(larg, max(6, h)))
    ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
    cores = plt.cm.tab10.colors
    for i, (k, v) in enumerate(sorted(segs.items(), key=lambda kv: -len(kv[1]))):
        ax.add_collection(LineCollection(v, colors=[cores[i % 10]], linewidths=0.9, label=f'{k} ({len(v)})'))
    for p, t, r, l in tx:
        ax.text(p[0], p[1], t, fontsize=5.5, rotation=r if r < 90 or r > 270 else r - 180, color='k' if 'Simb' not in l else 'purple', clip_on=True)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.legend(fontsize=7, loc='upper left')
    ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    fig.savefig(saida, dpi=dpi, bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    a = sys.argv
    plota(a[1], *map(float, a[2:6]), a[6], layers=a[7:] or None)
