# -*- coding: utf-8 -*-
"""Conferência rápida de um DXF (espaço do modelo): PNG com as linhas coloridas por layer e a lista de textos e layers.
Uso: .venv/Scripts/python.exe -X utf8 aurea/cad/aur_ver_dxf.py <dxf> <png> [filtro_layer]"""
import collections, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\APORA\scr')
from dxflite import DXF


def main():
    fn, png = sys.argv[1], sys.argv[2]; filt = sys.argv[3].upper() if len(sys.argv) > 3 else None
    d = DXF(fn)
    lay = collections.Counter(); txt = []; segs = collections.defaultdict(list)
    for e in d.walk(space='model'):
        if filt and filt not in e.layer.upper(): continue
        lay[(e.layer, e.type)] += 1
        if e.type in ('TEXT', 'MTEXT', 'ATTRIB') and e.text:
            txt.append((e.layer, e.text.strip()[:80], e.pts[0][:2] if e.pts else None))
        elif e.pts and len(e.pts) > 1:
            P = np.array(e.pts)[:, :2]
            segs[e.layer].append(P)
    fig, ax = plt.subplots(figsize=(18, 14))
    cm = plt.get_cmap('tab20')
    for i, (l, Ps) in enumerate(sorted(segs.items())):
        for P in Ps: ax.plot(P[:, 0], P[:, 1], '-', color=cm(i % 20), lw=0.4)
    ax.set_aspect('equal'); fig.savefig(png, dpi=110); print(png)
    for (l, t), n in sorted(lay.items(), key=lambda k: -k[1])[:60]: print(f'{n:6d} {t:10s} {l}')
    c = collections.Counter(t for _, t, _ in txt)
    print('--- textos mais comuns'); [print(f'{n:4d} {t}') for t, n in c.most_common(80)]


if __name__ == '__main__':
    main()
