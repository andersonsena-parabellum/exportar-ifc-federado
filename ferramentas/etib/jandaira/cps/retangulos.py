# -*- coding: utf-8 -*-
"""Lista retângulos (polilinhas fechadas de 4 lados) de um DXF, com dimensões, centro e ângulo. Uso: python -I retangulos.py <dxf> [lmin] [lmax]"""
import sys, os, math, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')


def retangulos(g, lmin=20, lmax=80):
    out = []
    for s in g['segs']:
        p = np.array([q[:2] for q in s['p']])
        if len(p) >= 5 and np.linalg.norm(p[0] - p[-1]) < 1e-3: p = p[:-1]
        if not (s.get('closed') or len(p) == 4) or len(p) != 4: continue
        e = [p[(i + 1) % 4] - p[i] for i in range(4)]; L = [np.linalg.norm(v) for v in e]
        if abs(np.dot(e[0], e[1])) > 1e-3 * L[0] * L[1] or abs(L[0] - L[2]) > 0.01 or abs(L[1] - L[3]) > 0.01: continue
        a, b = max(L[0], L[1]), min(L[0], L[1])
        if not (lmin <= a <= lmax): continue
        v = e[0] if L[0] >= L[1] else e[1]; ang = math.degrees(math.atan2(v[1], v[0])) % 180
        out.append(dict(lay=s['lay'], a=a, b=b, c=p.mean(0), ang=ang))
    return out


if __name__ == '__main__':
    g = dxfgeo.load(sys.argv[1]); lo = float(sys.argv[2]) if len(sys.argv) > 2 else 20; hi = float(sys.argv[3]) if len(sys.argv) > 3 else 80
    for r in sorted(retangulos(g, lo, hi), key=lambda r: -r['a']): print('%-28s %7.3f x %7.3f  c=(%.3f, %.3f)  ang=%.4f' % (r['lay'][:28], r['a'], r['b'], r['c'][0], r['c'][1], r['ang']))
