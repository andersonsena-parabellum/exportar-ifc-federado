"""Trechos (runs) de conduto ancorados nas setas de sentido.
Para cada seta: acha as duas paredes simetricas em torno do centro da seta (=eixo) e estende ate o fim das paredes.
Saida: work/runs.pkl"""
import sys, math, pickle, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *

E, segs, mlines, arrows, P = pickle.load(open(CACHE, 'rb'))
SA = np.array([[s[0][0], s[0][1], s[1][0], s[1][1]] for s in segs])
SANG = np.array([ang(s) for s in segs])

def merge_contig(iv, start, gap=0.5):
    """iv: lista de (lo,hi); devolve intervalo contiguo que contem 'start'"""
    iv = sorted(iv)
    cur = None
    out = []
    for lo, hi in iv:
        if cur and lo <= cur[1] + gap:
            cur[1] = max(cur[1], hi)
        else:
            if cur: out.append(cur)
            cur = [lo, hi]
    if cur: out.append(cur)
    best = None
    for lo, hi in out:
        if lo - gap <= start <= hi + gap:
            if best is None or (hi - lo) > (best[1] - best[0]):
                best = (lo, hi)
    return best

SYMTOL = 0.006
def run_for_arrow(a, b):
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ux, uy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(ux, uy); ux, uy = ux / n, uy / n
    nx, ny = -uy, ux
    aa = math.atan2(uy, ux) % math.pi
    da = np.abs(SANG - aa); da = np.minimum(da, math.pi - da)
    idx = np.where(da < 0.006)[0]
    walls = []
    for k in idx:
        x1, y1, x2, y2 = SA[k]
        o1 = (x1 - cx) * nx + (y1 - cy) * ny; o2 = (x2 - cx) * nx + (y2 - cy) * ny
        o = (o1 + o2) / 2
        if abs(o) > 0.26 or abs(o) < 0.008: continue
        p1 = (x1 - cx) * ux + (y1 - cy) * uy; p2 = (x2 - cx) * ux + (y2 - cy) * uy
        lo, hi = min(p1, p2), max(p1, p2)
        if lo > 0.5 or hi < -0.5: continue
        walls.append((o, lo, hi, k))
    best = None
    for w1 in walls:
        if w1[0] <= 0: continue
        for w2 in walls:
            if w2[0] >= 0: continue
            if abs(w1[0] + w2[0]) < SYMTOL:
                d = w1[0] - w2[0]
                if best is None or d < best[0]:
                    best = (d, w1[0], w2[0])
    if not best: return None
    d, op, om = best
    iv1 = [(w[1], w[2]) for w in walls if abs(w[0] - op) < 0.004]
    iv2 = [(w[1], w[2]) for w in walls if abs(w[0] - om) < 0.004]
    # estender: busca de todas as paredes na mesma linha (alem do filtro de cobertura do centro)
    allw1 = []; allw2 = []
    for k in idx:
        x1, y1, x2, y2 = SA[k]
        o = (((x1 - cx) * nx + (y1 - cy) * ny) + ((x2 - cx) * nx + (y2 - cy) * ny)) / 2
        p1 = (x1 - cx) * ux + (y1 - cy) * uy; p2 = (x2 - cx) * ux + (y2 - cy) * uy
        if abs(o - op) < 0.004: allw1.append((min(p1, p2), max(p1, p2)))
        if abs(o - om) < 0.004: allw2.append((min(p1, p2), max(p1, p2)))
    r1 = merge_contig(allw1, 0); r2 = merge_contig(allw2, 0)
    if not r1 or not r2: return None
    lo = max(r1[0], r2[0]); hi = min(r1[1], r2[1])
    if hi - lo < 0.15: return None
    mx, my = (op + om) / 2, 0
    ex, ey = cx + nx * mx, cy + ny * mx
    return {'d': d, 'p0': (ex + ux * lo, ey + uy * lo), 'p1': (ex + ux * hi, ey + uy * hi),
            'c': (cx, cy), 'flow': (ux, uy), 'lo': lo, 'hi': hi, 'off': mx, 'ang': aa}

runs = []
nomatch = []
for k, (a, b) in enumerate(arrows):
    SYMTOL = 0.006
    r = run_for_arrow(a, b)
    if not r:
        SYMTOL = 0.04
        r = run_for_arrow(a, b)
        if r: r['loose'] = True
    if r: r['arrow'] = k; runs.append(r)
    else: nomatch.append(k)
print('arrows', len(arrows), 'runs(raw)', len(runs), 'sem parede simetrica', len(nomatch))

# agrupar duplicatas: mesmo eixo (offset<0.01), mesma direcao, extensoes que se sobrepoem
def key(r):
    return r
groups = []
for r in runs:
    placed = False
    for g in groups:
        q = g[0]
        da = abs(r['ang'] - q['ang']); da = min(da, math.pi - da)
        if da > 0.006 or abs(r['d'] - q['d']) > 0.01: continue
        # distancia perpendicular do centro de r ao eixo de q e overlap
        ux, uy = q['flow']; nx, ny = -uy, ux
        o = (r['c'][0] - q['c'][0]) * nx + (r['c'][1] - q['c'][1]) * ny
        if abs(o + 0) > 0.01 + 0.0 and abs(o - (r['off'] - q['off'])) > 0.01: pass
        # posicao do eixo
        # reconstruir eixos: distancia entre pontos p0 de r e a reta de q
        dx, dy = r['p0'][0] - q['p0'][0], r['p0'][1] - q['p0'][1]
        perp = abs(dx * nx + dy * ny)
        if perp > 0.012: continue
        along = lambda p: (p[0] - q['p0'][0]) * ux + (p[1] - q['p0'][1]) * uy
        l1, h1 = sorted([along(q['p0']), along(q['p1'])]); l2, h2 = sorted([along(r['p0']), along(r['p1'])])
        if l2 <= h1 + 0.05 and l1 <= h2 + 0.05:
            g.append(r); placed = True; break
    if not placed: groups.append([r])
print('grupos', len(groups))
R = []
for g in groups:
    q = g[0]; ux, uy = q['flow']
    pts = []
    for r in g:
        pts += [r['p0'], r['p1']]
    al = [(p[0] - q['p0'][0]) * ux + (p[1] - q['p0'][1]) * uy for p in pts]
    lo, hi = min(al), max(al)
    p0 = (q['p0'][0] + ux * lo, q['p0'][1] + uy * lo); p1 = (q['p0'][0] + ux * hi, q['p0'][1] + uy * hi)
    # sentido por voto das setas (todas apontam o mesmo sentido?)
    sign = [1 if (r['flow'][0] * ux + r['flow'][1] * uy) > 0 else -1 for r in g]
    R.append({'p0': p0, 'p1': p1, 'd': float(np.median([r['d'] for r in g])), 'flow': (ux, uy), 'votes': sign,
              'arrows': [r['arrow'] for r in g], 'L': math.dist(p0, p1)})
print('runs', len(R), 'comprimento total', round(sum(r['L'] for r in R), 1), 'm')
print(collections.Counter(round(r['d'], 2) for r in R).most_common(20))
print('votos divergentes', sum(1 for r in R if len(set(r['votes'])) > 1))
pickle.dump((R, nomatch), open('D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/runs.pkl', 'wb'))
