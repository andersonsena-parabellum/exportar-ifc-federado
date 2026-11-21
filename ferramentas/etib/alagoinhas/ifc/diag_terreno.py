# -*- coding: utf-8 -*-
"""diagnóstico: amostras do terreno do IMP × tampas das caixas de ESG/DRN do modelo (CT das pranchas)."""
import sys, os, numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
import terreno as T
G = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo'
P = T.P
print('amostras', len(P), 'x', P[:, 0].min(), P[:, 0].max(), 'y', P[:, 1].min(), P[:, 1].max(), 'z', P[:, 2].min(), P[:, 2].max())
res = []
for f in ('HS', 'DRN', 'ELE', 'INC'):
    for l in open(os.path.join(G, f + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t', 7)
        if len(r) < 8 or not r[4]: continue
        if not any(k in r[3] for k in ('Caixa', 'Poço', 'CX', 'Alçapão', 'caixa')): continue
        V = np.array(r[7].split(','), float).reshape(-1, 3)
        lo, hi = V.min(0), V.max(0); c = (lo + hi) / 2
        zt = T.zt(c[0], c[1])
        res.append((f, r[4], hi[2], zt, hi[2] - zt, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
for f in ('HS', 'DRN', 'ELE', 'INC'):
    d = np.array([x[4] for x in res if x[0] == f and np.isfinite(x[4])])
    if len(d): print(f, len(d), 'tampa - IMP: mediana %+.3f  p10 %+.3f p90 %+.3f  min %+.3f max %+.3f' % (np.median(d), np.percentile(d, 10), np.percentile(d, 90), d.min(), d.max()))
for x in sorted(res, key=lambda x: -abs(x[4]) if np.isfinite(x[4]) else 0)[:25]:
    print('  %s %-10s tampa %.2f IMP %.2f dif %+.2f  %.2fx%.2fx%.2f' % x)
