# -*- coding: utf-8 -*-
"""Extensão da base do campo (layer ARQ_BASE*) em cada DXF do CPS e da SIT perto do campo."""
import sys, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
D = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-"
for f in ('CPS-PE-DRE-001-DRG-R01', 'CPS-PE-EL-001-ELG-R01', 'CPS-PE-IN-001-ING-R01'):
    g = dxfgeo.load(D + f + '.dxf')
    P = np.array([q[:2] for s in g['segs'] if s['lay'].startswith('ARQ_BASE') for q in s['p']])
    lo, hi = P.min(0), P.max(0); print(f, 'ARQ_BASE bbox %.3f x %.3f  centro %s' % (*(hi - lo), ((lo + hi) / 2).round(3)))
    big = [s for s in g['segs'] if s['lay'].startswith('ARQ_BASE') and len(s['p']) > 8]
    for s in sorted(big, key=lambda s: -len(s['p']))[:4]:
        Q = np.array([q[:2] for q in s['p']]); print('   polilinha %d vért: %.3f x %.3f' % (len(Q), *(Q.max(0) - Q.min(0))))
