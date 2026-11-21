# -*- coding: utf-8 -*-
"""resumo dos conflitos críticos que sobram numa rodada do preclash (por par de disciplinas e por trecho)."""
import csv, sys, collections, os
pasta = sys.argv[1] if len(sys.argv) > 1 else r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\PRECLASH_IMP_R03'
sig = sys.argv[2] if len(sys.argv) > 2 else 'ALI'; cen = sys.argv[3] if len(sys.argv) > 3 else 'AD'
L = list(csv.DictReader(open(os.path.join(pasta, f'{sig}_preclash_{cen}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'))
C = [r for r in L if r['gravidade'] == 'CRÍTICA']
print(len(C), 'críticos')
par = collections.Counter(tuple(sorted((r['disc_A'], r['disc_B']))) for r in C)
for k, v in par.most_common(): print('  ', k, v)
tipo = collections.Counter(r['tipo'] for r in C); print(' tipos', dict(tipo))
for d in sorted({r['disc_A'] for r in C} | {r['disc_B'] for r in C}):
    t = collections.Counter()
    for r in C:
        if r['disc_A'] == d: t[r['trecho_A']] += 1
        if r['disc_B'] == d: t[r['trecho_B']] += 1
    print(d, len(t), 'trechos/peças:', ', '.join(f'{k}({v})' for k, v in t.most_common(25)))
P = list(csv.DictReader(open(os.path.join(pasta, f'{sig}_preclash_{cen}_pendentes.csv'), encoding='utf-8-sig'), delimiter=';'))
print('pendentes críticos por categoria:', collections.Counter(p['categoria'] for p in P if p['gravidade'] == 'CRÍTICA'))
