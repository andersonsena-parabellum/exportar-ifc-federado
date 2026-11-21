# -*- coding: utf-8 -*-
"""Conferência da posição da quadra: SIT R01 (base, para UTM), AF-002 _GEO (caixas da drenagem), pilares e pisos do IMP as built
(para UTM pela mesma transformação da SIT). Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_conf_quadra.py <png>"""
import csv, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\APORA\scr')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxflite import DXF                       # noqa: E402
from aur_terreno_imp import utm, imp_utm, IMP          # noqa: E402

BOX = (600015, 8711335, 600105, 8711415)


def main():
    fig, ax = plt.subplots(figsize=(14, 13))
    d = DXF(r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\APORA\dxf\24-049-APR-CTO-ETIB-IMP-PE-URB-001-SIT-R01.dxf')
    for e in d.walk(space='model'):
        if not e.pts or len(e.pts) < 2: continue
        P = utm(np.array(e.pts))[:, :2]
        if not ((P[:, 0] > BOX[0]) & (P[:, 0] < BOX[2]) & (P[:, 1] > BOX[1]) & (P[:, 1] < BOX[3])).any(): continue
        ax.plot(P[:, 0], P[:, 1], '-', color='0.6', lw=0.4)
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_pisos.csv'), encoding='utf-8'), delimiter=';'):
        A = imp_utm(np.array([list(map(float, r[k].split(','))) for k in 'abc']))
        ax.fill(A[:, 0], A[:, 1], color='orange', alpha=0.15, lw=0)
    est = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aur_estrutura.json'), encoding='utf-8'))['pecas']
    for p in est: ax.plot(p['x'], p['y'], 'ks', ms=6)
    F2 = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\GEORREF_E_REDES_2026-10-18'
    for r in csv.DictReader(open(os.path.join(F2, 'revit', 'dre_caixas.csv'), encoding='utf-8-sig'), delimiter=';'):
        ax.plot(float(r['x_utm']), float(r['y_utm']), 'bs', ms=5); ax.text(float(r['x_utm']), float(r['y_utm']), ' ' + r['id'], fontsize=7, color='b')
    for r in csv.DictReader(open(os.path.join(F2, 'revit', 'dre_tubos_B.csv'), encoding='utf-8-sig'), delimiter=';'):
        ax.plot([float(r['x0_utm']), float(r['x1_utm'])], [float(r['y0_utm']), float(r['y1_utm'])], 'b-', lw=0.8)
    ax.set_xlim(BOX[0], BOX[2]); ax.set_ylim(BOX[1], BOX[3]); ax.set_aspect('equal'); ax.grid(lw=0.3)
    fig.savefig(sys.argv[1], dpi=100); print(sys.argv[1])


if __name__ == '__main__':
    main()
