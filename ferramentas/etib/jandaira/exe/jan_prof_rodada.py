# -*- coding: utf-8 -*-
"""Profundidade do topo (m) de trechos numa rodada do preclash da Jandaíra, para atualizar notas de prancha depois de uma
decisão: por trecho (sem o .N) o maior "PROF." ao longo dele (pressurizadas) e, por nó de junção da gravidade, a do tubo mais fundo
que chega no nó (como o jan_mudancas_ifc faz). Uso: python -X utf8 jan_prof_rodada.py <pasta da rodada> <trecho|E,N> ..."""
import os, sys, json, re
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno
sys.stdout.reconfigure(encoding='utf-8')
P = sys.argv[1]
J = json.load(open(os.path.join(P, 'JAN.json'), encoding='utf-8')); O = np.array([631578.10, 8721003.57]); zr = J['zref']
TT = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\jandaira_terreno.npz')
els = []
for e in J['elementos']:
    if 'AD' not in e.get('cen', ['AD']): continue
    Q = np.array((e.get('sol') or {}).get('AD') or e['p'], float); Q[:, :2] += O; Q[:, 2] += zr
    els.append((e, Q))


def prof_trecho(base):
    out = []
    for e, Q in els:
        if re.sub(r'\.\d+$', '', e['trecho']) != base: continue
        zt = np.array(TT.z(Q[:, :2]), float); ok = np.isfinite(zt)
        if ok.any(): out.append(float(np.max(zt[ok] - (Q[ok, 2] + e['de'] / 2))))
    return max(out) if out else None


def prof_no(p):
    perto = [(Q[k], e) for e, Q in els if e['disc'] in ('DRE', 'ESG') for k in (0, -1) if np.hypot(*(Q[k, :2] - p)) < 0.20]
    if not perto: return None
    q, e = min(perto, key=lambda x: x[0][2])
    return float(TT.z(np.array([q[:2]]))[0] - (q[2] + e['de'] / 2)), e['trecho']


for a in sys.argv[2:]:
    if ',' in a:
        p = np.array([float(x) for x in a.split(',')]); r = prof_no(p); print(a, '->', None if r is None else (round(r[0], 2), r[1]))
    else:
        r = prof_trecho(a); print(a, '->', None if r is None else round(r, 2))
