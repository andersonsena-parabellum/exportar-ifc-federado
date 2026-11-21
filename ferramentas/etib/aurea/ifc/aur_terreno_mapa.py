# -*- coding: utf-8 -*-
"""Mapa de conferência do terreno da Áurea: IMP as built (UTM) × TOP-001, com o platô da TER, as redes e as caixas.
Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_terreno_mapa.py <png> [npz_final]"""
import csv, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno

D = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados'
F2 = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\GEORREF_E_REDES_2026-10-18'


def ler(fn):
    t = open(fn, encoding='utf-8-sig').readline()
    return list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';' if ';' in t else ','))


def main():
    out = sys.argv[1]
    ti = Terreno(os.path.join(D, 'apora_aurea_terreno_imp.npz')); tt = Terreno(os.path.join(D, 'apora_aurea_terreno_top.npz'))
    fin = Terreno(sys.argv[2]) if len(sys.argv) > 2 else None
    box = (599990, 8711200, 600190, 8711560)
    X, Y = np.meshgrid(np.arange(box[0], box[2], 1.0), np.arange(box[1], box[3], 1.0))
    Q = np.column_stack([X.ravel(), Y.ravel()])
    zi = ti.z(Q).reshape(X.shape); zt = tt.z(Q).reshape(X.shape)
    pan = [('IMP as built (UTM)', zi), ('TOP-001 + platô 188', zt), ('IMP − TOP', zi - zt)]
    if fin: pan.append(('final', fin.z(Q).reshape(X.shape)))
    fig, axs = plt.subplots(1, len(pan), figsize=(7 * len(pan), 11))
    dre = ler(os.path.join(F2, 'dre_trechos.csv')) if os.path.exists(os.path.join(F2, 'dre_trechos.csv')) else []
    ele = ler(os.path.join(F2, 'ele_trechos.csv'))
    cx = ler(os.path.join(F2, 'revit', 'dre_caixas.csv')); en = ler(os.path.join(F2, 'ele_nos.csv'))
    for ax, (tit, Z) in zip(axs, pan):
        if 'TOP' in tit and '−' in tit:
            im = ax.pcolormesh(X, Y, Z, cmap='RdBu_r', vmin=-2, vmax=2, shading='auto')
        else:
            im = ax.pcolormesh(X, Y, Z, cmap='terrain', vmin=184, vmax=192, shading='auto')
            cs = ax.contour(X, Y, Z, levels=np.arange(184, 193, 0.5), colors='k', linewidths=0.3)
        fig.colorbar(im, ax=ax, shrink=0.5)
        for P, z in tt.plat: ax.plot(*np.vstack([P, P[:1]]).T, 'm-', lw=1)
        for r in ele: ax.plot([float(r['x0']), float(r['x1'])], [float(r['y0']), float(r['y1'])], 'r-', lw=1)
        for r in dre:
            try: ax.plot([float(r['x0']), float(r['x1'])], [float(r['y0']), float(r['y1'])], 'b-', lw=0.8)
            except (KeyError, ValueError): pass
        for r in cx:
            ax.plot(float(r['x_utm']), float(r['y_utm']), 'bs', ms=3); ax.text(float(r['x_utm']), float(r['y_utm']), f" {r['id']} {float(r['CT']):.0f}", fontsize=6)
        for r in en:
            ax.plot(float(r['x']), float(r['y']), 'r^', ms=3); ax.text(float(r['x']), float(r['y']), ' ' + r['no'], fontsize=6, color='r')
        ax.set_title(tit); ax.set_aspect('equal'); ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3])
    fig.tight_layout(); fig.savefig(out, dpi=110)
    print(out)


if __name__ == '__main__':
    main()
