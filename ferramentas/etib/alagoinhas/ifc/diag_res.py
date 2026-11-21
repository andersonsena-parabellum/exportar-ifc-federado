# -*- coding: utf-8 -*-
"""procura o contorno dos reservatórios (RES, taça) na SIT R04 (DXF), pelo leitor dxf_ler."""
import sys, re, numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler
D = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\ALAGOINHAS_BA2\dxf_base\24-049-ALH-SLJ-ETIB-IMP-PE-URB-001-SIT-R04.dxf'
P = ler(D)
print(len(P), 'primitivas; exemplo', {k: P[0][k] for k in P[0] if k != 'pts'})
txt = [p for p in P if p['tipo'] == 'TEXT' and re.search(r'RESERV|^RES$|TA[CÇ]A|CISTERN|BOMB', str(p.get('texto', '')), re.I)]
for t in txt:
    x, y = t['pts'][0][:2]; print('TXT', repr(str(t['texto'])[:50]), round(x, 2), round(y, 2), t['layer'], t.get('blocos'))
    for q in P:
        if q['tipo'] not in ('PL', 'CIRCLE') or len(q['pts']) == 0: continue
        Q = q['pts'][:, :2]; c = Q.mean(0)
        if q['tipo'] == 'CIRCLE':
            if np.hypot(*(c - [x, y])) < 10: print('   CIRCLE r=%.2f c=(%.2f,%.2f) %s' % (q.get('r', 0), c[0], c[1], q['layer']))
        elif np.hypot(*(c - [x, y])) < 10 and np.ptp(Q[:, 0]) < 20 and np.ptp(Q[:, 1]) < 20 and len(Q) >= 4:
            print('   PL n=%d c=(%.2f,%.2f) %.2fx%.2f %s fechada=%s' % (len(Q), c[0], c[1], np.ptp(Q[:, 0]), np.ptp(Q[:, 1]), q['layer'], q.get('fechada')))
