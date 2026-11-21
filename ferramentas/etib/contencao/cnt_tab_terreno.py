# -*- coding: utf-8 -*-
"""Tabela do terreno amostrado (estaca × offset). Uso: cnt_tab_terreno.py arquivo_z.csv [passo_estaca]"""
import sys, collections
sys.stdout.reconfigure(encoding='utf-8')
fn = sys.argv[1]; passo = float(sys.argv[2]) if len(sys.argv) > 2 else 6
rows = [l.strip().split(';') for l in open(fn, encoding='utf-8') if l.strip()]
by = collections.defaultdict(dict); offs = []
for r in rows:
    o = float(r[3]); by[(r[1], float(r[2]))][o] = float(r[6]) if r[6] != 'nan' else float('nan')
    if o not in offs: offs.append(o)
offs.sort()
print('sec    est ' + ' '.join(f'{o:>7.1f}' for o in offs))
ult = -1e9
for k in sorted(by, key=lambda k: k[1]):
    if k[1] - ult < passo - 0.01: continue
    ult = k[1]; z = by[k]
    print(k[0], f'{k[1]:6.1f} ' + ' '.join(f'{z.get(o, float("nan")):7.2f}' for o in offs))
