# -*- coding: utf-8 -*-
"""Campo de deslocamento local: base da disciplina (_GEO, já em UTM) x base de referência, por quadrículas.
Para cada quadrícula, ajusta só translação (ICP com raio decrescente) e informa o vetor e a aderência.
Uso: python -I campo_desloc.py <disc_GEO.dxf> <prefixo_caminho> <ref.dxf> <saida.png> [--tam 30]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.stdout.reconfigure(encoding='utf-8')

a = sys.argv
disc, pref, ref, out = a[1], a[2], a[3], a[4]
tam = float(a[a.index('--tam') + 1]) if '--tam' in a else 30.0
ign = ('CARIMBO', 'carimbo', 'FORMATO', 'Q-TABELA', 'TEXTO', 'TXT', 'COTA', 'DI-')
A = casar.cache_load(disc)
B = casar.cache_load(ref)
pa = casar.amostrar(A, lambda s: s['path'].startswith(pref) and not any(k in s['lay'] for k in ign), passo=0.25)
S = casar.segmentos(B, lambda s: not any(k in s['lay'] for k in ign))
G = casar.GradeSeg(S)
ij = np.floor(pa / tam).astype(int)
res = []
for key in sorted(set(map(tuple, ij))):
    m = (ij[:, 0] == key[0]) & (ij[:, 1] == key[1])
    P = pa[m]
    if len(P) < 200:
        continue
    t = np.zeros(2)
    for r in (2.0, 1.0, 0.5, 0.2, 0.1, 0.05):
        for _ in range(4):
            d, cp = G.consulta(P + t, r)
            ok = np.isfinite(d)
            if ok.sum() < 30:
                break
            t = t + np.median(cp[ok] - (P[ok] + t), axis=0)
    d, _ = G.consulta(P + t, 0.6)
    d0, _ = G.consulta(P, 0.6)
    res.append((P.mean(0), t, len(P), float(np.mean(d0 <= 0.02)), float(np.mean(d <= 0.02))))
print('%-24s %6s %8s %8s %8s %7s %7s' % ('centro da quadrícula', 'pts', 'dx mm', 'dy mm', '|t| mm', 'ader0', 'ader1'))
for c, t, n, a0, a1 in res:
    print('E %.0f N %.0f        %6d %8.0f %8.0f %8.0f %6.0f%% %6.0f%%' % (c[0], c[1], n, t[0]*1000, t[1]*1000, np.hypot(*t)*1000, a0*100, a1*100))
fig, ax = plt.subplots(figsize=(14, 12), dpi=110)
Ls = [np.array([[s[0], s[1]], [s[2], s[3]]]) for s in S[::3]]
ax.add_collection(LineCollection(Ls, colors='0.8', linewidths=0.3))
for c, t, n, a0, a1 in res:
    col = 'green' if np.hypot(*t) < 0.05 else ('orange' if np.hypot(*t) < 0.3 else 'red')
    if a1 > 0.15:
        ax.annotate('', xy=(c[0] + t[0]*20, c[1] + t[1]*20), xytext=(c[0], c[1]), arrowprops=dict(arrowstyle='->', color=col, lw=2))
        ax.text(c[0], c[1] - 3, '%.0f mm' % (np.hypot(*t)*1000), fontsize=7, color=col)
ax.set_xlim(pa[:, 0].min() - 10, pa[:, 0].max() + 10); ax.set_ylim(pa[:, 1].min() - 10, pa[:, 1].max() + 10)
ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain')
ax.set_title('Deslocamento local (seta x20) da base de %s sobre %s' % (os.path.basename(disc)[27:40], os.path.basename(ref)[27:40]))
plt.tight_layout(); plt.savefig(out); print('ok', out)
