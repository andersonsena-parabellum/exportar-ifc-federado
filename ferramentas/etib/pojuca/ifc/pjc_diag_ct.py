# -*- coding: utf-8 -*-
"""Pojuca — terreno do IMP as built × CT das caixas de esgoto e drenagem das pranchas (base)."""
import csv, os, sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno
REL = r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS'
T = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\pojuca_terreno.npz')
for fn in ('PJC_fase2_ESG_caixas.csv', 'PJC_fase2_DRE_caixas.csv', 'PJC_fase2_CPS_DRE_caixas.csv'):
    R = []
    for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
        try: ct = float(r['CT'])
        except (TypeError, ValueError, KeyError): continue
        z = float(T.z([[float(r['E']), float(r['N'])]])[0]); R.append((r['caixa'], ct, z, ct - z))
    if not R: print(fn, 'sem CT'); continue
    d = np.array([x[3] for x in R])
    print(f'{fn}: {len(R)} CT, CT-IMP mediana {np.median(d):+.2f}, min {d.min():+.2f}, max {d.max():+.2f}, |d|>0,20: {int((abs(d) > 0.20).sum())}')
    for x in sorted(R, key=lambda x: -abs(x[3]))[:12]:
        if abs(x[3]) > 0.10: print(f'   {x[0]:8s} CT {x[1]:.2f} IMP {x[2]:.2f} d {x[3]:+.2f}')
