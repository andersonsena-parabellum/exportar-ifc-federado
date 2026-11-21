# -*- coding: utf-8 -*-
"""Drenagem do campo (CPS DRE-001 R01) em coordenadas do campo (x ao longo, leste +; y transversal, norte +) e no interno JAN."""
import sys, json, math, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
DXF = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dxf"
c0 = np.array([27.15, 17.15])
g = dxfgeo.load(DXF)
print('layers:', collections.Counter(s['lay'] for s in g['segs']))
for s in g['segs']:
    if s['lay'] not in ('AP-Condutos', 'AP-Caixa de alvenaria', 'AP-Sentido conduto') and 'CANAL' not in s['lay'].upper(): continue
    P = np.array([q[:2] for q in s['p']]) - c0; L = np.linalg.norm(np.diff(P, axis=0), axis=1).sum()
    if s['lay'] == 'AP-Caixa de alvenaria': print('CAIXA  c(%6.2f,%6.2f) dim %s' % (*P.mean(0), (P.max(0) - P.min(0)).round(2)))
    elif s['lay'] == 'AP-Condutos': print('TUBO   %d vért L%5.1f  %s -> %s' % (len(P), L, P[0].round(2), P[-1].round(2)))
for x in g['texts']:
    if any(w in x['t'] for w in ('mm', 'PVC', 'CANALETA', 'i=')): pass
