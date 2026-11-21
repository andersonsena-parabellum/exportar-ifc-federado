"""Monta a rede: segmentos unificados (runs + sobras de pares + MLINE), caixas, nos.  Saida work/net.pkl"""
import sys, math, pickle, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
E, segs, mlines, arrows, P = pickle.load(open(CACHE, 'rb'))
R, nomatch = pickle.load(open(W + 'runs.pkl', 'rb'))
left = pickle.load(open(W + 'left.pkl', 'rb'))

def sd(p, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; n2 = dx * dx + dy * dy
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)

# --- 1. segmentos candidatos
cand = []
for r in R:
    cand.append({'p0': r['p0'], 'p1': r['p1'], 'd': r['d'], 'flow': r['flow'], 'src': 'run'})
for p in left:
    g = p['g']
    n = math.dist(*g); u = ((g[1][0] - g[0][0]) / n, (g[1][1] - g[0][1]) / n)
    cand.append({'p0': g[0], 'p1': g[1], 'd': p['d'], 'flow': None, 'src': 'par'})
for m in mlines:
    n = math.dist(m[0], m[-1])
    cand.append({'p0': m[0], 'p1': m[-1], 'd': None, 'flow': None, 'src': 'mline'})

# --- 2. unir colineares (mesmo angulo, mesma reta, intervalos contiguos)
def angl(c): return math.atan2(c['p1'][1] - c['p0'][1], c['p1'][0] - c['p0'][0]) % math.pi
used = [False] * len(cand)
merged = []
order = sorted(range(len(cand)), key=lambda i: -math.dist(cand[i]['p0'], cand[i]['p1']))
for i in order:
    if used[i]: continue
    a = cand[i]; used[i] = True
    ux, uy = a['p1'][0] - a['p0'][0], a['p1'][1] - a['p0'][1]; n = math.hypot(ux, uy); ux, uy = ux / n, uy / n
    nx, ny = -uy, ux
    grp = [a]
    changed = True
    while changed:
        changed = False
        for j in range(len(cand)):
            if used[j]: continue
            c = cand[j]
            da = abs(angl(c) - angl(a)); da = min(da, math.pi - da)
            if da > 0.01: continue
            o = ((c['p0'][0] - a['p0'][0]) * nx + (c['p0'][1] - a['p0'][1]) * ny + (c['p1'][0] - a['p0'][0]) * nx + (c['p1'][1] - a['p0'][1]) * ny) / 2
            if abs(o) > 0.02: continue
            if c['d'] is not None and a['d'] is not None and abs(c['d'] - a['d']) > 0.025: continue
            al = lambda p: (p[0] - a['p0'][0]) * ux + (p[1] - a['p0'][1]) * uy
            lo = min(al(q) for g in grp for q in (g['p0'], g['p1'])); hi = max(al(q) for g in grp for q in (g['p0'], g['p1']))
            l2, h2 = sorted([al(c['p0']), al(c['p1'])])
            if l2 <= hi + 0.3 and h2 >= lo - 0.3:
                grp.append(c); used[j] = True; changed = True
    al = lambda p: (p[0] - a['p0'][0]) * ux + (p[1] - a['p0'][1]) * uy
    lo = min(al(q) for g in grp for q in (g['p0'], g['p1'])); hi = max(al(q) for g in grp for q in (g['p0'], g['p1']))
    ds = [g['d'] for g in grp if g['d'] is not None]
    fl = [g['flow'] for g in grp if g['flow']]
    sgn = 0
    for f in fl: sgn += 1 if (f[0] * ux + f[1] * uy) > 0 else -1
    merged.append({'p0': (a['p0'][0] + ux * lo, a['p0'][1] + uy * lo), 'p1': (a['p0'][0] + ux * hi, a['p0'][1] + uy * hi),
                   'd': float(np.median(ds)) if ds else None, 'dir': (ux, uy), 'sgn': sgn, 'n': len(grp),
                   'src': ','.join(sorted(set(g['src'] for g in grp)))})
print('candidatos', len(cand), 'segmentos unidos', len(merged), 'comp', round(sum(math.dist(m['p0'], m['p1']) for m in merged), 1))

# --- 3. caixas
Lb = [e for e in E if e[1] == 'AP-Caixa de alvenaria' and e[0] == 'LINE' and math.dist(*e[3]) > 0.05]
par = list(range(len(Lb)))
def f(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for i in range(len(Lb)):
    for j in range(i + 1, len(Lb)):
        if any(math.dist(p, q) < 0.03 for p in Lb[i][3] for q in Lb[j][3]): par[f(i)] = f(j)
cl = collections.defaultdict(list)
for i in range(len(Lb)): cl[f(i)].append(i)
boxes = []
for v in cl.values():
    xs = [p[0] for i in v for p in Lb[i][3]]; ys = [p[1] for i in v for p in Lb[i][3]]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w < 0.4 or h < 0.4: continue
    boxes.append({'xmin': min(xs), 'xmax': max(xs), 'ymin': min(ys), 'ymax': max(ys), 'c': ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), 'w': w, 'h': h})
print('caixas', len(boxes))
pickle.dump((merged, boxes), open(W + 'net.pkl', 'wb'))
