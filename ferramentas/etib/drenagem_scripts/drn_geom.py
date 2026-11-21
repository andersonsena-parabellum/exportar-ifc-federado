"""Geometria base da drenagem: paredes de conduto -> eixos, setas de sentido, textos, caixas.
Lê work/dump_GEO.tsv (UTM). Uso: from drn_geom import *"""
import sys, math, pickle, os
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work')
from load import *
import numpy as np

CACHE = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/geom_cache.pkl'

def build():
    E = parse(load())
    segs = []
    for e in E:
        if e[1] != 'AP-Condutos' or e[0] not in ('LINE', 'LWPOLYLINE'):
            continue
        pts = e[3]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if math.dist(a, b) >= 0.25:
                segs.append((a, b))
    mlines = [e[3] for e in E if e[1] == 'AP-Condutos' and e[0] == 'MLINE']
    arrows = []
    for e in E:
        if e[1] == 'AP-Sentido conduto' and e[0] == 'LWPOLYLINE' and len(e[3]) == 2:
            arrows.append((e[3][0], e[3][1]))
    return E, segs, mlines, arrows

def ang(s):
    (x1, y1), (x2, y2) = s[0], s[1]
    return math.atan2(y2 - y1, x2 - x1) % math.pi

def pairs(segs, dmax=0.45, dmin=0.03, amax=0.006, minov=0.15):
    A = np.array([ang(s) for s in segs])
    out = []
    for i, s in enumerate(segs):
        (x1, y1), (x2, y2) = s
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        for j in range(i + 1, len(segs)):
            da = abs(A[i] - A[j]); da = min(da, math.pi - da)
            if da > amax:
                continue
            t = segs[j]
            d1 = (-(t[0][0] - x1) * uy + (t[0][1] - y1) * ux)
            d2 = (-(t[1][0] - x1) * uy + (t[1][1] - y1) * ux)
            d = (d1 + d2) / 2
            if abs(d) > dmax or abs(d) < dmin:
                continue
            p1 = (t[0][0] - x1) * ux + (t[0][1] - y1) * uy
            p2 = (t[1][0] - x1) * ux + (t[1][1] - y1) * uy
            lo = max(0, min(p1, p2)); hi = min(n, max(p1, p2))
            if hi - lo < minov:
                continue
            ox, oy = -uy * d / 2, ux * d / 2
            g = ((x1 + ux * lo + ox, y1 + uy * lo + oy), (x1 + ux * hi + ox, y1 + uy * hi + oy))
            out.append({'g': g, 'd': abs(d), 'i': i, 'j': j, 'len': hi - lo})
    return out

if __name__ == '__main__':
    E, segs, mlines, arrows = build()
    P = pairs(segs)
    pickle.dump((E, segs, mlines, arrows, P), open(CACHE, 'wb'))
    print(len(segs), len(P), len(arrows), len(mlines))
