# -*- coding: utf-8 -*-
"""Mapa da conferência/plano R01 da Jandaíra: redes em planta (coord. internas dos modelos JAN) + colisões de hoje,
coloridas pelo destino no plano (resolvida pelo plano / sobra nas redes móveis / a definir pelo projetista)."""
import sys, os, csv
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD
D = os.path.dirname(JD.G)
SEG, MESH = JD.carregar(est='daniel')
COR = {'AF': '#1f9bd7', 'ESG': '#7a5230', 'DRE': '#2e7d32', 'ELE': '#f39c12', 'INC': '#c62828', 'SDAI': '#7b1fa2'}
fig, ax = plt.subplots(figsize=(11.7, 8.3), dpi=150)
for M in MESH:
    if M['disc'] == 'EST' and M['cat'] in ('Fundações estruturais', 'Pilares estruturais'):
        lo, hi = M['lo'], M['hi']; ax.add_patch(plt.Rectangle(lo[:2], *(hi - lo)[:2], color='#9e9e9e', lw=0, alpha=0.5))
for s in SEG:
    if s['disc'] in COR and np.linalg.norm(s['b0'][:2] - s['a0'][:2]) > 0.05:
        ax.plot([s['a0'][0], s['b0'][0]], [s['a0'][1], s['b0'][1]], color=COR[s['disc']], lw=1.2 if s['disc'] not in ('INC',) else 2.0, alpha=0.85)
def ler(n): return list(csv.DictReader(open(os.path.join(D, n), encoding='utf-8-sig'), delimiter=';'))
H = [r for r in ler('pontos_R01_hoje.csv') if r['gravidade'] == 'CRITICA']
SL = [r for r in ler('pontos_R01_solucao.csv') if r['gravidade'] == 'CRITICA']
S = {(r['disc_a'], r['elem_a'], r['disc_b'], r['elem_b']) for r in SL}
HK = {(r['disc_a'], r['elem_a'], r['disc_b'], r['elem_b']) for r in H}
cats = {'resolvida no plano': ('o', '#2e7d32'), 'sobra ou criada pelo plano (contorno local)': ('s', '#e65100'), 'a definir pelo projetista (DRE/ESG/estrutura)': ('X', '#b71c1c')}
pts = {k: [] for k in cats}
for r in H:
    k = (r['disc_a'], r['elem_a'], r['disc_b'], r['elem_b'])
    c = 'a definir pelo projetista (DRE/ESG/estrutura)' if r['a_definir'] else ('sobra ou criada pelo plano (contorno local)' if k in S else 'resolvida no plano')
    pts[c].append((float(r['x']), float(r['y'])))
for r in SL:
    if (r['disc_a'], r['elem_a'], r['disc_b'], r['elem_b']) not in HK: pts['sobra ou criada pelo plano (contorno local)'].append((float(r['x']), float(r['y'])))
for c, (mk, cor) in cats.items():
    if pts[c]: P = np.array(pts[c]); ax.scatter(P[:, 0], P[:, 1], marker=mk, s=46, facecolor='none' if mk == 'o' else cor, edgecolor=cor, lw=1.4, zorder=5, label=f'{c} ({len(P)})')
for d, c in COR.items(): ax.plot([], [], color=c, lw=2, label={'AF': 'Água fria', 'ESG': 'Esgoto', 'DRE': 'Drenagem', 'ELE': 'Elétrica', 'INC': 'Hidrantes', 'SDAI': 'Alarme (SDAI)'}[d])
ax.add_patch(plt.Rectangle((0, 0), 0, 0, color='#9e9e9e', alpha=0.5, label='Fundações e pilares (as built)'))
ax.set_aspect('equal'); ax.set_xlim(-5, 150); ax.set_ylim(-12, 150)
ax.set_title(f'ETIB Jandaíra — colisões de hoje ({len(H)}) e o que acontece com elas no plano R01', fontsize=11)
ax.legend(loc='upper right', fontsize=7.5, framealpha=0.9); ax.grid(alpha=0.2)
ax.set_xlabel('x (m) — coordenadas internas dos modelos JAN'); ax.set_ylabel('y (m)')
out = os.path.join(os.path.dirname(D), 'JAN_R01_mapa_colisoes_plano.png'); fig.tight_layout(); fig.savefig(out); print(out)
