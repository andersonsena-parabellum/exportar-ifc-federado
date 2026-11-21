# -*- coding: utf-8 -*-
"""Compara dois arquivos de pontos (hoje × com a solução) por par e gravidade."""
import csv, collections, sys
sys.stdout.reconfigure(encoding='utf-8')
def c(fn):
    k = collections.Counter()
    for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'): k[(r['par'], r['gravidade'])] += 1
    return k
a = c(sys.argv[1]); b = c(sys.argv[2])
pares = sorted(set(k[0] for k in a) | set(k[0] for k in b))
print(f"{'par':14s} colisões hoje->sol   folgas hoje->sol   info")
for p in pares:
    print(f"{p:14s} {a[(p,'CRÍTICA')]:4d} -> {b[(p,'CRÍTICA')]:4d}       {a[(p,'ATENÇÃO')]:4d} -> {b[(p,'ATENÇÃO')]:4d}     {a[(p,'INFORMAÇÃO')]:3d} -> {b[(p,'INFORMAÇÃO')]:3d}")
for g in ('CRÍTICA', 'ATENÇÃO', 'INFORMAÇÃO'):
    print(g, sum(v for k, v in a.items() if k[1] == g), '->', sum(v for k, v in b.items() if k[1] == g))
