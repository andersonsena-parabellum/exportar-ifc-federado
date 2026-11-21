# -*- coding: utf-8 -*-
"""Catu — imagem de conferência de um ponto (planta com redes, caixas e prédios), para decidir os ajustes.
Uso: python cat_spot.py E N [raio] [saida.png]  |  python cat_spot.py --criticos [cenário] [raio] (uma imagem por crítico
do <SAIDA>/CAT_preclash_<cen>_pendentes.csv, em <SAIDA>/_spots)"""
import sys, os, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.environ.setdefault('CAT_SEM_AJUSTES', '0')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from escolas import catu as S
from preclash import modelo as md

COR = {'AF': 'b', 'ESG': 'saddlebrown', 'DRE': 'g', 'ELE': 'orange', 'HID': 'r', 'SDAI': 'm', 'EST': '0.5'}


def main():
    D = S.carregar()
    if sys.argv[1] == '--criticos':
        import csv
        cen = sys.argv[2] if len(sys.argv) > 2 else 'AD'; R = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
        pasta = os.path.join(S.SAIDA, '_spots'); os.makedirs(pasta, exist_ok=True)
        for r in csv.DictReader(open(os.path.join(S.SAIDA, f'CAT_preclash_{cen}_pendentes.csv'), encoding='utf-8-sig'), delimiter=';'):
            if r['gravidade'] != 'CRÍTICA': continue
            f = lambda v: float(v.replace(',', '.'))
            desenhar(D, f(r['E']), f(r['N']), R, os.path.join(pasta, f"{int(r['n']):03d}.png"), r['conflito'])
        return
    E0, N0 = float(sys.argv[1]), float(sys.argv[2]); R = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.environ.get('TEMP', '.'), f'cat_spot_{E0:.0f}_{N0:.0f}.png')
    desenhar(D, E0, N0, R, out)


def desenhar(D, E0, N0, R, out, titulo=''):
    ter = D['terreno']
    fig, ax = plt.subplots(figsize=(11, 11))
    for n, p in S.PR.contornos(): ax.fill(*p.exterior.xy, color='0.9')
    for c in D['caixas']:
        if abs(c['E'] - E0) > R + 2 or abs(c['N'] - N0) > R + 2: continue
        rot = c.get('rot', 0.0) if c['forma'] == 'r' else 0.0; mx, my = c.get('mx', c['meia']), c.get('my', c['meia'])
        if c['forma'] == 'c':
            t = np.linspace(0, 2 * math.pi, 40); x, y = c['E'] + c['meia'] * np.cos(t), c['N'] + c['meia'] * np.sin(t)
        else:
            u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]])
            Q = np.array([[c['E'], c['N']] + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]); x, y = Q[:, 0], Q[:, 1]
        ax.plot(x, y, color=COR.get(c['disc'], 'k'), lw=1.2)
        ax.text(c['E'], c['N'], f"{c['info'].get('nome', c['id'])}\n{c['zb']:.2f}/{c['zt']:.2f}", fontsize=6.5, color=COR.get(c["disc"], "k"), clip_on=True)
    for e in D['elementos']:
        P = e['pts']
        if not np.any((np.abs(P[:, 0] - E0) < R) & (np.abs(P[:, 1] - N0) < R)) and not (
                min(P[:, 0]) < E0 < max(P[:, 0]) and min(P[:, 1]) < N0 < max(P[:, 1])): continue
        ax.plot(P[:, 0], P[:, 1], color=COR.get(e['disc'], 'k'), lw=max(0.8, e['de'] * 12), alpha=0.8)
        k = len(P) // 2; m = (P[k - 1] + P[k]) / 2 if len(P) > 1 else P[0]
        ax.text(m[0], m[1], f"{e['trecho']} Ø{e['de'] * 1000:.0f}\n{P[:, 2].min():.2f}", fontsize=6, color=COR.get(e["disc"], "k"), clip_on=True)
    ax.set_xlim(E0 - R, E0 + R); ax.set_ylim(N0 - R, N0 + R); ax.set_aspect('equal'); ax.grid(alpha=0.3)
    ax.set_title(titulo + '\n' + f'Catu {E0:.1f} / {N0:.1f} (terreno {float(ter.z([[E0, N0]])[0]):.2f})', fontsize=9)
    fig.savefig(out, dpi=90, bbox_inches='tight'); plt.close(fig); print(out)


if __name__ == '__main__':
    main()
