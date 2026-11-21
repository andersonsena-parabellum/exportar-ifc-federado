# -*- coding: utf-8 -*-
"""Confere a cópia _GEO contra o original transformado: mesmas entidades, desvio máximo dos vértices.
Uso: python -I conferir_geo.py <orig.dxf> <geo.dxf> <rot_graus> <tx> <ty>"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxfgeo
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')

o, g, rot, tx, ty = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
A = dxfgeo.load(o); B = dxfgeo.load(g)
c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))


def tr(p):
    return (c*p[0] - s*p[1] + tx, s*p[0] + c*p[1] + ty)


res = {}
for k in ('segs', 'texts', 'inserts', 'circles', 'points'):
    la, lb = A[k], B[k]
    if len(la) != len(lb):
        res[k] = 'CONTAGEM DIFERENTE %d x %d' % (len(la), len(lb))
        continue
    dmax = 0.0
    for ea, eb in zip(la, lb):
        if k == 'segs':
            pa, pb = ea['p'], eb['p']
            if len(pa) != len(pb):
                dmax = max(dmax, 999); continue
            for x, y in zip(pa, pb):
                q = tr(x); dmax = max(dmax, math.hypot(q[0]-y[0], q[1]-y[1]))
        elif k == 'circles':
            q = tr(ea['c']); dmax = max(dmax, math.hypot(q[0]-eb['c'][0], q[1]-eb['c'][1]))
        else:
            q = tr(ea['p']); dmax = max(dmax, math.hypot(q[0]-eb['p'][0], q[1]-eb['p'][1]))
    res[k] = '%d entidades, desvio máx %.3f mm' % (len(la), dmax*1000)
P = np.array([p[:2] for sg in B['segs'] for p in sg['p']])
lo, hi = np.percentile(P, 0.5, axis=0), np.percentile(P, 99.5, axis=0)
print(os.path.basename(g))
for k, v in res.items():
    print('   %-8s %s' % (k, v))
print('   extensão (0,5%%–99,5%%): E %.1f–%.1f  N %.1f–%.1f' % (lo[0], hi[0], lo[1], hi[1]))
