# -*- coding: utf-8 -*-
"""Agrupa os pontos de clash por par de disciplinas e proximidade (encadeamento a < EPS m) e resume cada grupo:
quantidade de colisões/folgas, trechos envolvidos, profundidade (terreno − eixo) de cada lado.
Saída: RELATORIOS/compat_R02/grupos.csv + console."""
import sys, csv, collections, math
import numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral")
from terreno import zt
sys.stdout.reconfigure(encoding='utf-8')
EPS = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
F = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash.csv"
rows = list(csv.DictReader(open(F, encoding='utf-8-sig'), delimiter=';'))
for r in rows:
    r['x'] = float(r['x']); r['y'] = float(r['y']); r['z'] = float(r['z']); r['f'] = float(r['folga_m'])
    t = zt(r['x'], r['y']); r['zt'] = t; r['prof'] = t - r['z']
bypar = collections.defaultdict(list)
for i, r in enumerate(rows): bypar[r['par']].append(i)
grupos = []
for par, idx in bypar.items():
    rest = set(idx)
    while rest:
        i = rest.pop(); g = [i]; fila = [i]
        while fila:
            k = fila.pop()
            for j in list(rest):
                if math.hypot(rows[j]['x'] - rows[k]['x'], rows[j]['y'] - rows[k]['y']) < EPS:
                    rest.discard(j); g.append(j); fila.append(j)
        grupos.append((par, g))
out = []
for gi, (par, g) in enumerate(sorted(grupos, key=lambda t: (t[0], -len(t[1])))):
    R = [rows[i] for i in g]
    nc = sum(1 for r in R if r['gravidade'] == 'CRÍTICA'); na = sum(1 for r in R if r['gravidade'] == 'ATENÇÃO'); ni = len(R) - nc - na
    cx, cy = np.mean([r['x'] for r in R]), np.mean([r['y'] for r in R])
    tA = collections.Counter(r['trechoA'].split('.')[0] for r in R); tB = collections.Counter(r['trechoB'].split('.')[0] for r in R)
    out.append([f'G{gi:03d}', par, len(R), nc, na, ni, f'{cx:.1f}', f'{cy:.1f}', f"{min(r['f'] for r in R):.3f}",
                ' '.join(f'{k}' for k, _ in tA.most_common(6)), ' '.join(f'{k}' for k, _ in tB.most_common(6)),
                f"{np.nanmin([r['prof'] for r in R]):.2f}..{np.nanmax([r['prof'] for r in R]):.2f}", ','.join(str(i) for i in g)])
with open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\grupos.csv", 'w', encoding='utf-8-sig') as f:
    f.write('grupo;par;n;colisões;folgas;info;x;y;folga_min;trechos_A;trechos_B;prof_eixo_m;linhas\n')
    for o in out: f.write(';'.join(map(str, o)) + '\n')
# pontos com profundidade, para os próximos passos
with open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash_prof.csv", 'w', encoding='utf-8-sig') as f:
    cols = list(rows[0].keys())
    f.write(';'.join(cols) + '\n')
    for r in rows: f.write(';'.join(str(r[c]) for c in cols) + '\n')
print('grupos', len(out))
for o in out:
    if o[3] > 0 or o[2] >= 4: print(';'.join(map(str, o[:12])))
