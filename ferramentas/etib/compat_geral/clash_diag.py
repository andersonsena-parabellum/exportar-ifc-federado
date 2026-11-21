# -*- coding: utf-8 -*-
"""Diagnóstico dos pontos de clash: amostra por par/tipo. Uso: clash_diag.py PAR [gravidade] [n]"""
import sys, csv, collections
sys.stdout.reconfigure(encoding='utf-8')
F = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash.csv"
par = sys.argv[1]; gv = sys.argv[2] if len(sys.argv) > 2 else 'CRÍTICA'; n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
rows = [r for r in csv.DictReader(open(F, encoding='utf-8-sig'), delimiter=';') if r['par'] == par and r['gravidade'] == gv]
c = collections.Counter((r['tipo'], r['catA'], r['catB']) for r in rows)
print(par, gv, len(rows), dict(c))
for r in rows[:n]:
    print(f"  {r['folga_m']:>7} | {r['trechoA'][:22]:22s} {r['nomeA'][:28]:28s} {r['DE_A_mm']:>4} | {r['trechoB'][:22]:22s} {r['nomeB'][:30]:30s} {r['DE_B_mm']:>4} | ({r['x']},{r['y']},{r['z']}) {r['tipo']}")
