# -*- coding: utf-8 -*-
"""Jandaíra — conferência do cenário de entrega antes de gerar as pranchas (padrão novo, 19/10/2026):
  1) nenhum degrau no meio do trecho nas pressurizadas (subida/descida > 45° fora de caixa da própria disciplina);
  2) topo das caixas no terreno (nem enterrada nem flutuando, tolerância 5 cm);
  3) profundidade: topo das pressurizadas até 1,50 m; caixas de elétrica com mais de 1,50 m de fundo;
  4) elétrica acima da água em todo cruzamento em planta.
Lê RELATORIOS/PRECLASH_R02/JAN.json e o terreno do adaptador. Grava RELATORIOS/PRECLASH_R02/JAN_verificacao.md."""
import os, sys, json, math, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.stdout.reconfigure(encoding='utf-8')
from preclash.terreno import Terreno
from preclash import clash as cl
PRE = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02'
J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8'))
O = (631578.10, 8721003.57); zref = J['zref']; CEN = 'AD'
T = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\jandaira_terreno.npz')
utm = lambda P: np.array([[p[0] + O[0], p[1] + O[1], p[2] + zref] for p in P])
PRESS = ('AF', 'HID', 'SDAI', 'ELE')
cx = []
for c in J['caixas']:
    q = dict(c); mv = (c.get('mv') or {}).get(CEN)
    if mv: q['x'], q['y'] = mv
    q.update(E=q['x'] + O[0], N=q['y'] + O[1], zb=q['zb'] + zref, zt=q['zt'] + zref, forma=q['f'], meia=q['m']); cx.append(q)
L = ['# Jandaíra — conferência do cenário de entrega (AD)', '']
# 1) degraus
deg = []
for e in J['elementos']:
    if e['disc'] not in PRESS or CEN not in e['cen']: continue
    P = utm((e['sol'] or {}).get(CEN) or e['p'])
    for a, b in zip(P[:-1], P[1:]):
        dxy = math.hypot(*(b[:2] - a[:2])); dz = abs(b[2] - a[2])
        if dz < 0.03 or dz < dxy: continue
        m = (a + b) / 2
        dentro = [c['id'] for c in cx if c['disc'] == e['disc'] and not c['id'].startswith('EQ:') and
                  (lambda q: q[0] < 0.15 and q[1] < 0.15)(__import__('preclash.modelo', fromlist=['x']).planta_local(c, m[0], m[1]))]
        if not dentro: deg.append((e['trecho'], e['disc'], round(float(m[0]), 2), round(float(m[1]), 2), round(dz, 2), round(dxy, 2)))
L += [f'## 1. Degrau no meio do trecho (pressurizadas, > 45° fora de caixa): {len(deg)}', '']
L += [f'- {t} ({d}) em E {x:.2f} / N {y:.2f}: Δz {dz:.2f} m em {dxy:.2f} m' for t, d, x, y, dz, dxy in deg] or ['- nenhum']
# 2) caixas no terreno
cxs = [c for c in cx if c['disc'] in ('DRE', 'ESG', 'ELE', 'SDAI', 'AF') and not c['id'].startswith('EQ:') and c.get('tipo') not in ('canaleta semicircular com grelha', 'reservatório enterrado')]
zt = T.z(np.array([[c['E'], c['N']] for c in cxs]))
fora = [(c['id'], round(float(c['zt'] - z), 3)) for c, z in zip(cxs, zt) if np.isfinite(z) and abs(c['zt'] - z) > 0.05]
L += ['', f'## 2. Topo da caixa fora do terreno (> 5 cm): {len(fora)} de {len(cxs)}', '']
L += [f'- {i}: topo {d:+.3f} m em relação ao terreno' for i, d in sorted(fora, key=lambda x: -abs(x[1]))] or ['- nenhuma']
# 3) profundidades
pmax = []
for e in J['elementos']:
    if e['disc'] not in PRESS or CEN not in e['cen']: continue
    P = utm((e['sol'] or {}).get(CEN) or e['p']); Q = cl.amostra(P, 0.5); z = T.z(Q[:, :2])
    ok = np.isfinite(z)
    if ok.any(): pmax.append((float(np.max(z[ok] - Q[ok, 2] - e['de'] / 2)), e['trecho'], e['disc']))
pmax.sort(reverse=True)
fundas = [(c['id'], round(c['zt'] - c['zb'], 2)) for c in cxs if c['disc'] in ('ELE', 'SDAI') and c['zt'] - c['zb'] > 1.20]
por = collections.defaultdict(list)
for p, t, d in pmax: por[d].append(p)
L += ['', '## 3. Profundidade', '']
L += [f'- {d}: topo do tubo/eletroduto até {max(v):.2f} m (mediana {np.median(v):.2f} m)' for d, v in sorted(por.items())]
L += [f'- acima de 1,50 m: ' + (', '.join(f'{t} ({d}) {p:.2f} m' for p, t, d in pmax if p > 1.51) or 'nenhum')]
L += [f'- caixas de elétrica/SDAI com mais de 1,20 m de fundo: {len(fundas)}' + (' (' + ', '.join(f'{i.split(":")[-1]} {p:.2f} m' for i, p in sorted(fundas, key=lambda x: -x[1])) + ')' if fundas else '')]
# 4) elétrica acima da água
els = {e['id']: e for e in J['elementos'] if CEN in e['cen']}
segs = lambda ds: [(e, a, b) for e in els.values() if e['disc'] in ds for a, b in zip(utm((e['sol'] or {}).get(CEN) or e['p'])[:-1], utm((e['sol'] or {}).get(CEN) or e['p'])[1:])]
EL = segs(('ELE', 'SDAI')); AG = segs(('AF', 'HID'))
abaixo = []
for e1, a1, b1 in EL:
    for e2, a2, b2 in AG:
        if max(a1[0], b1[0]) < min(a2[0], b2[0]) or min(a1[0], b1[0]) > max(a2[0], b2[0]) or max(a1[1], b1[1]) < min(a2[1], b2[1]) or min(a1[1], b1[1]) > max(a2[1], b2[1]): continue
        d, C1, C2 = cl.dist_seg_seg(a1[None], b1[None], a2[None], b2[None])
        if math.hypot(C1[0, 0] - C2[0, 0], C1[0, 1] - C2[0, 1]) < 0.05 and C1[0, 2] < C2[0, 2]:
            abaixo.append((e1['trecho'], e2['trecho'], round(float(C2[0, 2] - C1[0, 2]), 2)))
L += ['', f'## 4. Elétrica/SDAI abaixo da água num cruzamento: {len(abaixo)}', '']
L += [f'- {a} passa {dz:.2f} m abaixo de {b}' for a, b, dz in abaixo] or ['- nenhum']
open(os.path.join(PRE, 'JAN_verificacao.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L))
