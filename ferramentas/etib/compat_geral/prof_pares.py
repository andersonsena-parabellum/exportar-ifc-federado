# -*- coding: utf-8 -*-
"""Profundidade (terreno − cota) de cada elemento em cada ponto de clash: eixo para tubos; topo/fundo para sólidos.
Saída: RELATORIOS/compat_R02/pontos_prof_elem.csv e resumo por par."""
import sys, os, csv, collections
import numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral")
from terreno import zt
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo"
seg = {}; mesh = {}
for f in ('HS', 'DRN', 'INC', 'ELE'):
    for l in open(os.path.join(G, f + '_segs.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) >= 13: seg[r[1]] = (np.array(list(map(float, r[7:10]))), np.array(list(map(float, r[10:13]))), float(r[6]))
for f in ('HS', 'DRN', 'INC', 'ELE', 'CNT', 'EST'):
    for l in open(os.path.join(G, f + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) >= 8:
            v = np.array(r[7].split(','), dtype=float).reshape(-1, 3); mesh[r[1]] = (v[:, 2].min(), v[:, 2].max())
def zaxis(i, x, y):
    a, b, de = seg[i]; d = b - a; L2 = d[0] ** 2 + d[1] ** 2
    t = 0.5 if L2 < 1e-9 else np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / L2, 0, 1)
    return a[2] + d[2] * t, de
rows = list(csv.DictReader(open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash.csv", encoding='utf-8-sig'), delimiter=';'))
out = []
for r in rows:
    x, y = float(r['x']), float(r['y']); t = zt(x, y); rec = dict(r); rec['zt'] = f'{t:.2f}'
    for k in ('A', 'B'):
        i = r['id' + k]
        if i in seg:
            z, de = zaxis(i, x, y); rec['prof' + k] = f'{t - z:.2f}'; rec['topo' + k] = f'{t - z - de / 2:.2f}'; rec['fundo' + k] = f'{t - z + de / 2:.2f}'
        elif i in mesh:
            lo, hi = mesh[i]; rec['prof' + k] = ''; rec['topo' + k] = f'{t - hi:.2f}'; rec['fundo' + k] = f'{t - lo:.2f}'
    out.append(rec)
cols = list(out[0].keys())
with open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_prof_elem.csv", 'w', encoding='utf-8-sig') as f:
    f.write(';'.join(cols) + '\n')
    for r in out: f.write(';'.join(str(r.get(c, '')) for c in cols) + '\n')
# resumo por par (só tubo×tubo): profundidade mediana do eixo de cada lado
agg = collections.defaultdict(list)
for r in out:
    if r['tipo'] == 'tubo×tubo' and r.get('profA') and r.get('profB'):
        agg[(r['par'], r['gravidade'])].append((float(r['profA']), float(r['profB'])))
print('par | gravidade | n | prof eixo A (p10/mediana/p90) | prof eixo B')
for k, v in sorted(agg.items()):
    a = np.array(v)
    print(k[0], k[1], len(v), np.percentile(a[:, 0], [10, 50, 90]).round(2), np.percentile(a[:, 1], [10, 50, 90]).round(2))
