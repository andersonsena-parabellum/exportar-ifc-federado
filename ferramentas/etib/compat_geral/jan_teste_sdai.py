# -*- coding: utf-8 -*-
"""Testa a solução do Daniel para o alarme (item INC-02/04): espinha 1,4 m a leste (+x) a 0,65 m; trecho sul contornando pelo norte (+y ~1,7 m) a 1,10 m;
chegada à guarita a 0,95 m. Junto com a descida dos hidrantes. Conta só PCI × demais (caixas agrupadas)."""
import sys, os, json, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, jan_clash as JC, jan_resumo as JR, jan_teste_daniel as TD, motor
sys.stdout.reconfigure(encoding='utf-8')
SEG, MESH = JD.carregar(est='daniel')
m = TD.mods_inc(SEG, MESH)
Z = {'PCI-EL-02': (0.65, (1.4, 0)), 'PCI-EL-04': (0.65, (1.4, 0)), 'PCI-EL-05': (0.65, (1.4, 0)), 'PCI-EL-06': (0.65, (1.4, 0)), 'PCI-EL-07': (0.65, (1.4, 0)),
     'PCI-EL-03': (1.10, (0, 1.7)), 'PCI-EL-01': (0.95, (0, 0))}
for s in SEG:
    if s['trecho'] in Z:
        p, d = Z[s['trecho']]; m['seg'][s['id']] = {'dz': p - 0.68, 'dxy': list(d)}
for M in MESH:   # caixas do alarme acompanham a espinha
    if M['trecho'] in ('CX-SDAI-01', 'CX-SDAI-03', 'CX-SDAI-04'): m['mesh'][M['id']] = {'dxy': [1.4, 0]}
for nome, mods in (('hoje', None), ('Daniel: hidrantes + novo caminho do alarme', m)):
    L = JR.rodar(mods)
    c = collections.Counter((r['par'], r['sev']) for r in L if ('INC' in (r['da'], r['db']) or 'SDAI' in (r['da'], r['db'])) and not (r['da'] in ('INC', 'SDAI') and r['db'] in ('INC', 'SDAI')))
    print('==', nome, 'colisões', sum(v for (p, s), v in c.items() if s == 'CRITICA'), 'atenção', sum(v for (p, s), v in c.items() if s == 'ATENCAO'))
    print('  ', dict(sorted(c.items())))
    if mods:
        for r in sorted(L, key=lambda r: r['g']):
            if r['sev'] == 'CRITICA' and ('SDAI' in (r['da'], r['db']) or 'INC' in (r['da'], r['db'])): print(f"   {r['da']} {r['ga']} × {r['db']} {r['gb']} {r['g']*100:.1f} cm ({r['pt'][0]:.1f};{r['pt'][1]:.1f})")
