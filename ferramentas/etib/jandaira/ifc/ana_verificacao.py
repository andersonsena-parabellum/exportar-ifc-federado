# -*- coding: utf-8 -*-
"""Contexto de cada item da verificação de continuidade (pontas soltas, degraus, pedaços curtos) de uma rodada da Jandaíra:
ponta, pontas vizinhas da mesma rede (distância e Δz), caixa/equipamento mais perto, para decidir se é erro de dado ou esperado.
Uso: python -X utf8 ana_verificacao.py <pasta da rodada>"""
import os, sys, csv, json
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
P = sys.argv[1]
J = json.load(open(os.path.join(P, 'JAN.json'), encoding='utf-8')); O = np.array([631578.10, 8721003.57]); zr = J['zref']
els = []
for e in J['elementos']:
    if 'AD' not in e.get('cen', ['AD']): continue
    Q = np.array((e.get('sol') or {}).get('AD') or e['p'], float); Q[:, :2] += O; Q[:, 2] += zr
    els.append((e, Q))
cx = [(c, np.array([c['x'] + O[0], c['y'] + O[1]]), c['zb'] + zr, c['zt'] + zr) for c in J['caixas']]
R = list(csv.DictReader(open(os.path.join(P, 'JAN_preclash_AD_verificacao.csv'), encoding='utf-8-sig'), delimiter=';'))
f = lambda s: float(str(s).replace(',', '.'))
for r in R:
    if r['disc'] == 'DRE' and r['tipo'] == 'ponta solta' and f(r['valor']) > 1.0: continue
    p = np.array([f(r['E']), f(r['N']), f(r['z'])])
    viz = []
    for e, Q in els:
        if e['rede'] != r['rede'] or e['trecho'] == r['trecho']: continue
        for k in (0, -1):
            d = float(np.hypot(*(Q[k, :2] - p[:2])))
            if d < 1.5: viz.append((round(d, 2), e['trecho'], 'ini' if k == 0 else 'fim', round(float(Q[k, 2] - p[2]), 2)))
        # meio do trecho (derivação)
        if len(Q) > 1:
            for a, b in zip(Q[:-1], Q[1:]):
                dv = b[:2] - a[:2]; L2 = dv @ dv
                t = 0 if L2 < 1e-12 else np.clip((p[:2] - a[:2]) @ dv / L2, 0, 1); pp = a + (b - a) * t
                d = float(np.hypot(*(pp[:2] - p[:2])))
                if d < 0.6 and 0.02 < t < 0.98: viz.append((round(d, 2), e['trecho'], 'meio', round(float(pp[2] - p[2]), 2)))
    cc = sorted(((float(np.hypot(*(xy - p[:2]))), c['id'], round(zb, 2), round(zt, 2)) for c, xy, zb, zt in cx), key=lambda x: x[0])[:2]
    print(f"{r['tipo'][:6]} {r['disc']:4} {r['trecho']:14} {r['outro']:12} v={r['valor']:6} z={f(r['z']):.2f} | viz {sorted(viz)[:3]} | caixa {[(round(a, 2), b, c_, d_) for a, b, c_, d_ in cc]}")
