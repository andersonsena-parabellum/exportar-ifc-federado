# -*- coding: utf-8 -*-
"""Conferência das cópias revisadas (DXF reexportado do DWG _REV-R01): conta as entidades dos layers R01, compara com o original
e desenha uma imagem de conferência por prancha (desenho original em cinza, revisão em vermelho, notas numeradas)."""
import sys, os, collections, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
RV = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\rev"
OR = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf"
OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R01"
for f in sorted(os.listdir(RV)):
    if not f.endswith('_REV-R01.dxf'): continue
    g = dxfgeo.load(os.path.join(RV, f)); o = dxfgeo.load(os.path.join(OR, f.replace('_REV-R01', '')))
    r01 = collections.Counter(s['lay'] for s in g['segs'] if s['lay'].startswith('R01'))
    tx = [t for t in g['texts'] if t['lay'].startswith('R01')]
    print('%-50s segs %d -> %d (R01: %s) | textos R01 %d | original intacto: %s' % (f[19:-12], len(o['segs']), len(g['segs']), dict(r01), len(tx),
          len([s for s in g['segs'] if not s['lay'].startswith('R01')]) == len(o['segs'])))
    R = [s for s in g['segs'] if s['lay'].startswith('R01') and s['lay'] != 'R01-NOTA']
    P = np.array([q[:2] for s in R for q in s['p']]); lo, hi = P.min(0) - 8, P.max(0) + 8
    fig, ax = plt.subplots(figsize=(12, 12 * (hi[1] - lo[1]) / max(hi[0] - lo[0], 1)), dpi=110)
    for s in o['segs']:
        Q = np.array([q[:2] for q in s['p']])
        if Q[:, 0].max() < lo[0] or Q[:, 0].min() > hi[0] or Q[:, 1].max() < lo[1] or Q[:, 1].min() > hi[1]: continue
        ax.plot(Q[:, 0], Q[:, 1], color='#c8c8c8', lw=0.3)
    cor = {'R01-NOVO': '#d32f2f', 'R01-SUBSTITUIDO': '#555555', 'R01-NUVEM': '#e53935'}
    for s in R:
        Q = np.array([q[:2] for q in s['p']] + ([s['p'][0][:2]] if s.get('closed') else []))
        ax.plot(Q[:, 0], Q[:, 1], color=cor.get(s['lay'], 'r'), lw=1.4 if s['lay'] == 'R01-NOVO' else 0.8, ls='--' if s['lay'] == 'R01-SUBSTITUIDO' else '-')
    for t in tx:
        if t['t'].startswith('R01-') and len(t['t']) < 8: ax.text(t['p'][0], t['p'][1], t['t'][4:], color='#b71c1c', fontsize=6, fontweight='bold')
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f[:-4] + ' — conferência da revisão (vermelho: R01-NOVO e nuvens; tracejado: sai)', fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f.replace('.dxf', '_conferencia.png'))); plt.close(fig)
