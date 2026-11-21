# -*- coding: utf-8 -*-
"""Prévia das notas novas (jan_notas_r03.py --so-comandos) antes de rodar o console: desenho da prancha em cinza, textos da
prancha em preto, notas apagadas em azul claro e notas novas em vermelho, no recorte onde as notas antigas se amontoavam.
Uso: python -X utf8 jan_notas_previa.py <FOLHA> [n_recortes]   -> _copias/notas/previa_<FOLHA>_<k>.png"""
import os, sys, re, math, collections
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import asbuilt as ab, dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
R3 = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'; NOT = os.path.join(R3, '_copias', 'notas')
FINAL = {'AF-001': '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03', 'EL-001': '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R03',
         'EL-002': '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R03', 'IN-001': '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R05',
         'CPS-EL-001': '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R03'}
chave = sys.argv[1]; nrec = int(sys.argv[2]) if len(sys.argv) > 2 else 2
nome = FINAL[chave]
fn = os.path.join(R3, '_copias', nome + '_ler.dxf')
E = ab.entidades(fn); H = {e['h']: e for e in E}
arcos = []
_, model = dxfgeo.parse(fn)
for typ, data in model:
    if typ != 'ARC': continue
    d = dxfgeo._first(data)
    c = np.array([float(d[10]), float(d[20])]); r = float(d[40]); a0, a1 = math.radians(float(d[50])), math.radians(float(d[51]))
    if a1 < a0: a1 += 2 * math.pi
    t = np.linspace(a0, a1, 40); arcos.append(np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)]))
cmd = [l.rstrip('\n').split('\t') for l in open(os.path.join(NOT, f'_cmd_notas_{nome}.txt'), encoding='utf-8')]
apagar = {c[1] for c in cmd if c[0] == 'DEL'}
novas = [(H[c[1]], float(c[2]), float(c[3]), float(c[4]), c[5]) for c in cmd if c[0] == 'TXC']


def txt(ax, s, p, ang, h, cor, z=3):
    s = ab._limpo(s).replace('\\P', ' ')
    if not s.strip(): return
    tp = TextPath((0, 0), s, size=h * 1.0)
    tr = Affine2D().rotate(ang).translate(*p) + ax.transData
    ax.add_patch(PathPatch(tp, transform=tr, color=cor, lw=0, zorder=z))


# recortes: onde as notas apagadas se amontoavam
V = np.array([H[h]['p'] for h in apagar if h in H])
grupos = []
if len(V):
    g = list(range(len(V)))
    def f(i):
        while g[i] != i: g[i] = g[g[i]]; i = g[i]
        return i
    for i in range(len(V)):
        for j in range(i + 1, len(V)):
            if np.hypot(*(V[i] - V[j])) < 6: g[f(i)] = f(j)
    cc = collections.defaultdict(list)
    for i in range(len(V)): cc[f(i)].append(i)
    grupos = sorted(cc.values(), key=len, reverse=True)[:nrec]
for k, gi in enumerate(grupos):
    Q = V[gi]; lo, hi = Q.min(0) - 8, Q.max(0) + 8
    fig, ax = plt.subplots(figsize=(10, 10 * (hi[1] - lo[1]) / max(1e-6, hi[0] - lo[0])))
    dentro = lambda P: not ((P.max(0) < lo).any() or (P.min(0) > hi).any())
    for e in E:
        if 'pts' in e and dentro(e['pts']): ax.plot(*e['pts'].T, color='#888888', lw=0.6)
    for A in arcos:
        if dentro(A): ax.plot(*A.T, color='#888888', lw=0.6)
    for e in E:
        if e['typ'] in ('TEXT', 'MTEXT') and (lo <= e['p']).all() and (e['p'] <= hi).all():
            a, tw, th, p0 = ab.Plano._ret_texto(ab.Plano.__new__(ab.Plano), e)
            txt(ax, e['txt'], p0, a, e['alt'], '#9ecae1' if e['h'] in apagar else 'black', 2)
    for m, x, y, ang, s in novas:
        if (lo[0] <= x <= hi[0]) and (lo[1] <= y <= hi[1]): txt(ax, s, (x, y), ang, m['alt'], '#d62728', 4)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_aspect('equal'); ax.axis('off')
    out = os.path.join(NOT, f'previa_{chave}_{k}.png'); fig.savefig(out, dpi=130, bbox_inches='tight'); plt.close(fig); print(out)
