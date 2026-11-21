# -*- coding: utf-8 -*-
"""Mapa de conferência da fase 2: desenho das redes nos _GEO (cor clara, larga) × trechos extraídos (cor forte, fina).
Uso: .venv/Scripts/python.exe -X utf8 olindina/rede/onn_mapa_fase2.py [xmin ymin xmax ymax]"""
import sys, os, re, csv
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import casar
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

G = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\dxf_geo\24-049-ONN-CTO-ETIB-IMP-PE-'
F2 = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS\FASE2_REDES_2026-10-21'
box = [float(v) for v in sys.argv[1:5]] if len(sys.argv) >= 5 else [573880, 8743230, 573960, 8743350]
COR = {'AP': 'tab:green', 'ESG': 'tab:brown', 'AF': 'tab:blue', 'ELE': 'tab:orange', 'HID': 'tab:red'}


def linhas(g, f):
    out = []
    for s in g['segs']:
        if f(s):
            P = [(p[0], p[1]) for p in s['p']]; out += list(zip(P[:-1], P[1:]))
    return out


fig, ax = plt.subplots(figsize=(15, 20))
sit = casar.cache_load(G + 'URB-001-SIT-R01_GEO.dxf')
ax.add_collection(LineCollection(linhas(sit, lambda s: True), colors='0.75', linewidths=0.2))
for nm, rx, cor in (('ESG-001-HIG-R00', r'^(AP-Cond|TQ-Cond|Tubula|AP-Caixa)', 'palegreen'), ('AF-001-AFR-R00', r'^(AF-Cond|Tubula)', 'lightblue'),
                    ('EL-001-ELG-R00', r'^02\.', 'navajowhite'), ('IN-001-ING-R00', r'^HI-Cond', 'pink')):
    g = casar.cache_load(G + nm + '_GEO.dxf'); r = re.compile(rx)
    ax.add_collection(LineCollection(linhas(g, lambda s: bool(r.search(s['lay']))), colors=cor, linewidths=3.0))
for disc in ('AP', 'ESG'):
    for r in csv.DictReader(open(os.path.join(F2, f'ONN_fase2_{disc}_trechos.csv'), encoding='utf-8-sig'), delimiter=';'):
        a, b = (float(r['E_ini']), float(r['N_ini'])), (float(r['E_fim']), float(r['N_fim']))
        ax.plot(*zip(a, b), color=COR[disc], lw=0.9, ls='-' if r['situacao'] == 'novo' else '--')
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, r['trecho'], fontsize=5, color=COR[disc])
    for r in csv.DictReader(open(os.path.join(F2, f'ONN_fase2_{disc}_caixas.csv'), encoding='utf-8-sig'), delimiter=';'):
        ax.plot(float(r['E']), float(r['N']), 's', ms=4, mfc='none', color=COR[disc]); ax.text(float(r['E']) + 0.4, float(r['N']), r['caixa'], fontsize=5)
for r in csv.DictReader(open(os.path.join(F2, 'ONN_fase2_ELE_caixas.csv'), encoding='utf-8-sig'), delimiter=';'):
    ax.add_patch(plt.Rectangle((float(r['E']) - 0.5, float(r['N']) - 0.5), 1.0, 1.0, fill=False, color='tab:orange')); ax.text(float(r['E']) + 0.6, float(r['N']), r['no'], fontsize=6)
for r in csv.DictReader(open(os.path.join(F2, 'ONN_fase2_pressurizadas.csv'), encoding='utf-8-sig'), delimiter=';'):
    P = [tuple(map(float, v.split(','))) for v in r['vertices_UTM'].split()]
    ax.plot(*zip(*P), color=COR[r['sistema']], lw=0.9, ls='-' if r['situacao'] == 'novo' else '--')
    ax.text(*P[len(P) // 2], r['trecho'], fontsize=5, color=COR[r['sistema']])
ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain')
ax.set_title('ETIB Olindina — fase 2: desenho (claro) × extraído (forte; tracejado = existente)')
fig.savefig(os.environ.get('ONN_MAPA') or os.path.join(F2, 'ONN_fase2_mapa.png'), dpi=110, bbox_inches='tight')
