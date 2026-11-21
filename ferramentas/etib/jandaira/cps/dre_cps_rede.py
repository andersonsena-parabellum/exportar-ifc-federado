# -*- coding: utf-8 -*-
"""Rede de drenagem do CPS DRE-001 R01 limpa: junta as linhas duplas dos tubos em eixos, agrupa as caixas (CA) e grava
compat_R01/cps_dre_rede.json em coordenadas do campo (origem no centro do campo 54,3x34,3; x ao longo, y transversal)."""
import sys, json, math, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
DXF = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dxf"
OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\cps_dre_rede.json"
c0 = np.array([27.15, 17.15]); g = dxfgeo.load(DXF)
L = []
for s in g['segs']:
    if s['lay'] != 'AP-Condutos': continue
    P = np.array([q[:2] for q in s['p']]) - c0
    for k in range(len(P) - 1):
        if np.linalg.norm(P[k + 1] - P[k]) > 0.3: L.append((P[k], P[k + 1]))
usado = set(); eixos = []
for i, (a, b) in enumerate(L):
    if i in usado: continue
    u = (b - a) / np.linalg.norm(b - a); best = None
    for j, (c, d) in enumerate(L):
        if j == i or j in usado: continue
        v = (d - c) / np.linalg.norm(d - c)
        if abs(abs(np.dot(u, v)) - 1) > 1e-3: continue
        off = abs(np.cross(u, c - a))
        if not (0.05 < off < 0.30): continue
        if np.dot(v, u) < 0: c, d = d, c
        if abs(np.dot(c - a, u)) > 1.0 or abs(np.dot(d - b, u)) > 1.0: continue
        if best is None or off < best[0]: best = (off, j, c, d)
    if best:
        usado |= {i, best[1]}; eixos.append(dict(a=((a + best[2]) / 2).round(3).tolist(), b=((b + best[3]) / 2).round(3).tolist(), larg=round(best[0], 3)))
    else: usado.add(i); eixos.append(dict(a=a.round(3).tolist(), b=b.round(3).tolist(), larg=0.0))
# caixas: quadrados de 0,6 (interno) — centro dos 4 lados
lados = [np.array([q[:2] for q in s['p']]) - c0 for s in g['segs'] if s['lay'] == 'AP-Caixa de alvenaria']
cent = []
for P in lados:
    m = P.mean(0); ln = np.linalg.norm(P[-1] - P[0])
    if abs(ln - 0.6) < 0.02: cent.append(m)
cx = []
for m in cent:
    for c in cx:
        if np.linalg.norm(c['acc'] / c['n'] - m) < 0.6: c['acc'] += m; c['n'] += 1; break
    else: cx.append(dict(acc=m.copy(), n=1))
caixas = [dict(c=(c['acc'] / c['n']).round(3).tolist()) for c in cx if c['n'] >= 3]
inter = [(np.array(x['p'][:2]) - c0).round(2).tolist() for x in g['texts'] if 'INTERLIGAR' in x['t'].upper()]
print('eixos de tubo:', len(eixos), '| caixas:', len(caixas), '| saídas "interligar":', len(inter))
for e in sorted(eixos, key=lambda e: (e['a'][1] > 1, e['a'][0])): print('  tubo %s -> %s  L%.1f  larg %.2f' % (e['a'], e['b'], np.linalg.norm(np.subtract(e['b'], e['a'])), e['larg']))
for c in caixas: print('  CA', c['c'])
for p in inter: print('  interligar', p)
json.dump(dict(origem='centro do campo 54,3x34,3 do CPS DRE-001 R01 (local 27,15/17,15)', eixos=eixos, caixas=caixas, interligar=inter), open(OUT, 'w', encoding='utf-8'), indent=1)
