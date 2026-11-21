# -*- coding: utf-8 -*-
"""Transformação rígida disciplina -> base pelo casamento de poses de blocos de mesmo nome (vetorizado).
Uso: python -I -u transf_blocos.py <dir_dxf> A:B[:todos] A:B ...   (nomes curtos, ex.: AF-001-HIG-R00)"""
import sys, os, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar
import numpy as np

P = os.path.join(sys.argv[1], '24-049-STK-XXX-ETIB-IMP-PE-%s.dxf')
cache = {}


def g(n):
    if n not in cache:
        cache[n] = casar.por_nome(casar.cache_load(P % n))
    return cache[n]


def cands(a, b, todos):
    out = []
    for nome in set(a) & set(b):
        if nome.startswith('*'):
            continue
        la, lb = a[nome], b[nome]
        if not todos and (len(la) != 1 or len(lb) != 1):
            continue
        if len(la) * len(lb) > 40000:
            continue
        A = np.array([(x['p'][0], x['p'][1], x['rot'], x['s'], x['mir']) for x in la], float)
        B = np.array([(y['p'][0], y['p'][1], y['rot'], y['s'], y['mir']) for y in lb], float)
        ia, ib = np.meshgrid(np.arange(len(A)), np.arange(len(B)), indexing='ij')
        ia, ib = ia.ravel(), ib.ravel()
        ok = (np.abs(A[ia, 3] - B[ib, 3]) < 1e-4) & (A[ia, 4] == B[ib, 4])
        ia, ib = ia[ok], ib[ok]
        dth = (B[ib, 2] - A[ia, 2] + 180) % 360 - 180
        c, s = np.cos(np.radians(dth)), np.sin(np.radians(dth))
        tx = B[ib, 0] - (c * A[ia, 0] - s * A[ia, 1])
        ty = B[ib, 1] - (s * A[ia, 0] + c * A[ia, 1])
        for k in range(len(dth)):
            out.append((dth[k], tx[k], ty[k], nome))
    return out


for arg in sys.argv[2:]:
    p = arg.split(':')
    a, b, todos = p[0], p[1], len(p) > 2
    cs = cands(g(a), g(b), todos)
    if not cs:
        print('%-16s -> %-16s nada' % (a, b)); continue
    C = np.array([c[:3] for c in cs])
    key = np.column_stack([np.round(C[:, 0] / 1e-4), np.round(C[:, 1] / 0.01), np.round(C[:, 2] / 0.01)]).astype(np.int64)
    uk, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    ordem = np.argsort(-cnt)
    for r, gi in enumerate(ordem[:3]):
        m = C[inv == gi].mean(0)
        sel = (np.abs(C[:, 0] - m[0]) < 2e-4) & (np.hypot(C[:, 1] - m[1], C[:, 2] - m[2]) < 0.02)
        G = C[sel]; mm = G.mean(0)
        disp = np.hypot(G[:, 1] - mm[1], G[:, 2] - mm[2]).max()
        nomes = sorted(set(cs[i][3][:28] for i in np.where(sel)[0]))
        print('%s%-16s -> %-16s n=%4d dθ=%+.10f° t=(%.6f, %.6f) disp %.2f mm  %s' % ('' if r == 0 else '     2º/3º ', a, b, len(G), mm[0], mm[1], mm[2], disp*1000, ' | '.join(nomes[:6])))
