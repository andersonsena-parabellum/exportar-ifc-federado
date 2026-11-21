"""Drenagem v2 - extração "como o projetista": nós de projeto (lançamentos, PVs, caixas, prumadas)
primeiro, trechos ligando nós, sentido pela árvore a partir dos lançamentos (setas só conferem),
cotas pelas caixas/PVs. Saída: work/v2_net.json + work/v2_relatorio.txt"""
import sys, math, pickle, json, collections, re
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import CACHE
import numpy as np
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
E, segs_raw, mlines, arrows, P = pickle.load(open(CACHE, 'rb'))
R, nomatch = pickle.load(open(W + 'runs.pkl', 'rb'))
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); rep.append(s); print(s)
L = lambda p: (p[0] - 561500, p[1] - 8658000)
X0, X1, Y0, Y1 = -90, 110, -125, 75          # implantação (fora disso = detalhes/cortes do desenho)
inb = lambda p: X0 < p[0] < X1 and Y0 < p[1] < Y1
def dseg(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; n2 = dx * dx + dy * dy
    t = 0 if n2 == 0 else max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / n2))
    return math.hypot(q[0] - a[0] - t * dx, q[1] - a[1] - t * dy), t
def ang(a, b): return math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi
def adiff(x, y): d = abs(x - y); return min(d, math.pi - d)

# ---------------------------------------------------------------- 1. paredes
walls = []
for e in E:
    if e[1] == 'AP-Condutos' and e[0] in ('LINE', 'LWPOLYLINE'):
        pts = [L(q) for q in e[3]]
        for a, b in zip(pts, pts[1:]):
            if math.dist(a, b) >= 0.2 and inb(a) and inb(b): walls.append((a, b))
say('paredes de conduto na implantação:', len(walls))

# ---------------------------------------------------------------- 2. eixos candidatos
cand = []
for r in R:
    a, b = L(r['p0']), L(r['p1'])
    if inb(a): cand.append({'a': a, 'b': b, 'd': r['d'], 'flow': r['flow'], 'src': 'seta'})
WA = [ang(a, b) for a, b in walls]
used_w = [0.0] * len(walls)
# pares de parede (parceiro paralelo mais próximo)
for i, (a, b) in enumerate(walls):
    ux, uy = math.cos(WA[i]), math.sin(WA[i]); nx, ny = -uy, ux
    best = None
    for j, (c, d) in enumerate(walls):
        if j == i or adiff(WA[i], WA[j]) > 0.02: continue
        off = ((c[0] - a[0]) * nx + (c[1] - a[1]) * ny + (d[0] - a[0]) * nx + (d[1] - a[1]) * ny) / 2
        if not (0.015 < abs(off) < 0.45): continue
        pa = lambda p: (p[0] - a[0]) * ux + (p[1] - a[1]) * uy
        lo = max(min(pa(a), pa(b)), min(pa(c), pa(d))); hi = min(max(pa(a), pa(b)), max(pa(c), pa(d)))
        if hi - lo < 0.2: continue
        if best is None or abs(off) < abs(best[0]): best = (off, lo, hi)
    if best:
        off, lo, hi = best; ox, oy = nx * off / 2, ny * off / 2
        cand.append({'a': (a[0] + ux * lo + ox, a[1] + uy * lo + oy), 'b': (a[0] + ux * hi + ox, a[1] + uy * hi + oy), 'd': abs(off), 'flow': None, 'src': 'par'})
        used_w[i] = (hi - lo) / max(math.dist(a, b), 1e-6)
# paredes sem par = conduto em linha simples (drenos de 32 mm nas fachadas)
single = 0
for i, (a, b) in enumerate(walls):
    if used_w[i] < 0.3 and math.dist(a, b) >= 0.5:
        cand.append({'a': a, 'b': b, 'd': None, 'flow': None, 'src': 'linha'}); single += 1
for m in mlines:
    a, b = L(m[0]), L(m[-1])
    if inb(a): cand.append({'a': a, 'b': b, 'd': None, 'flow': None, 'src': 'mline'})
say('eixos candidatos:', len(cand), '(linhas simples', single, ')')

# ---------------------------------------------------------------- 3. unir colineares
def merge(cand):
    used = [False] * len(cand); out = []
    order = sorted(range(len(cand)), key=lambda i: (0 if cand[i]['src'] == 'seta' else 1, -math.dist(cand[i]['a'], cand[i]['b'])))
    for i in order:
        if used[i]: continue
        a = cand[i]; used[i] = True; grp = [a]
        th = ang(a['a'], a['b']); ux, uy = math.cos(th), math.sin(th); nx, ny = -uy, ux
        al = lambda p: (p[0] - a['a'][0]) * ux + (p[1] - a['a'][1]) * uy
        changed = True
        while changed:
            changed = False
            lo = min(al(q) for g in grp for q in (g['a'], g['b'])); hi = max(al(q) for g in grp for q in (g['a'], g['b']))
            for j in range(len(cand)):
                if used[j]: continue
                c = cand[j]
                if adiff(ang(c['a'], c['b']), th) > 0.02: continue
                o = ((c['a'][0] - a['a'][0]) * nx + (c['a'][1] - a['a'][1]) * ny + (c['b'][0] - a['a'][0]) * nx + (c['b'][1] - a['a'][1]) * ny) / 2
                tol = 0.035 if (c['d'] is None or a['d'] is None) else 0.025
                if abs(o) > tol: continue
                if c['d'] is not None and a['d'] is not None and abs(c['d'] - a['d']) > 0.03: continue
                l2, h2 = sorted([al(c['a']), al(c['b'])])
                if l2 <= hi + 0.25 and h2 >= lo - 0.25:
                    grp.append(c); used[j] = True; changed = True
        lo = min(al(q) for g in grp for q in (g['a'], g['b'])); hi = max(al(q) for g in grp for q in (g['a'], g['b']))
        ds = [g['d'] for g in grp if g['d'] is not None]
        fl = 0
        for g in grp:
            if g['flow']: fl += 1 if (g['flow'][0] * ux + g['flow'][1] * uy) > 0 else -1
        out.append({'a': (a['a'][0] + ux * lo, a['a'][1] + uy * lo), 'b': (a['a'][0] + ux * hi, a['a'][1] + uy * hi),
                    'd': float(np.median(ds)) if ds else None, 'fl': fl, 'src': sorted(set(g['src'] for g in grp))})
    return out
segs = [s for s in merge(cand) if math.dist(s['a'], s['b']) >= 0.3]
say('trechos após unir colineares:', len(segs), 'comprimento %.0f m' % sum(math.dist(s['a'], s['b']) for s in segs))

# ---------------------------------------------------------------- 4. nós de projeto
T = [e for e in E if e[0] == 'MTEXT']
boxes = []
for e in T:
    if e[1] == 'Simbolos' and e[5] == 'CA' and inb(L(e[3])): boxes.append({'tipo': 'CA', 'p': L(e[3]), 'r': 0.45})
for e in E:
    if e[0] == 'INSERT' and e[5] == 'zw$12D9' and inb(L(e[3])): boxes.append({'tipo': 'PV', 'p': L(e[3]), 'r': 0.65})
bx = []
for b in sorted(boxes, key=lambda b: 0 if b['tipo'] == 'PV' else 1):
    if all(math.dist(b['p'], k['p']) > 0.5 for k in bx): bx.append(b)
boxes = bx
for k, b in enumerate(boxes): b['id'] = ('PV%02d' if b['tipo'] == 'PV' else 'CA%02d') % (k + 1)
say('caixas/PVs do projeto (símbolos):', len(boxes), collections.Counter(b['tipo'] for b in boxes))
# rótulos de cota
TQ = [e for e in T if e[1] == 'TQ-Textos conduto']
def val(s):
    m = re.search(r'([\d.]+)', s.split(':')[-1]); return float(m.group(1)) if m else None
lab = {k: [(L(e[3]), val(e[5])) for e in TQ if e[5].startswith(k)] for k in ('CT', 'CF', 'CE', 'CS')}
for b in boxes:
    for k in ('CT', 'CF'):
        c = sorted((math.dist(b['p'], q), v) for q, v in lab[k] if math.dist(b['p'], q) < 5)
        b[k] = c[0][1] if c else None
    for k in ('CE', 'CS'):
        b[k] = [v for q, v in lab[k] if math.dist(b['p'], q) < 5 and (b['CT'] is None or v < b['CT'] - 0.04)]
# prumadas AP (ponta do leader oposta ao balão)
circ = [L(e[3]) for e in E if e[1].startswith('AP-Indica') and e[0] == 'CIRCLE']
cols = []
for e in E:
    if e[1].startswith('AP-Indica') and e[0] == 'LINE':
        a, b = L(e[3][0]), L(e[3][1])
        if not inb(a): continue
        da = min((math.dist(a, c) for c in circ), default=9); db = min((math.dist(b, c) for c in circ), default=9)
        p = b if da < db else a
        if max(da, db) < 1.45: continue          # diâmetro interno do balão, não é chamada
        if all(math.dist(p, q) > 0.3 for q in cols): cols.append(p)
say('prumadas AP (pontas de chamada):', len(cols))

# ---------------------------------------------------------------- 5. topologia
# 5a corta trechos que atravessam caixas
def split_at(s, ts):
    out = []; ts = sorted(set([0.0] + ts + [1.0]))
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-6: continue
        a = (s['a'][0] + (s['b'][0] - s['a'][0]) * t0, s['a'][1] + (s['b'][1] - s['a'][1]) * t0)
        b = (s['a'][0] + (s['b'][0] - s['a'][0]) * t1, s['a'][1] + (s['b'][1] - s['a'][1]) * t1)
        if math.dist(a, b) >= 0.15: out.append(dict(s, a=a, b=b))
    return out
s2 = []
for s in segs:
    ts = []
    for b in boxes:
        d, t = dseg(b['p'], s['a'], s['b'])
        if d < b['r'] and 0.02 < t < 0.98: ts.append(t)
    s2 += split_at(s, ts)
segs = s2
# 5b junções em T: ponta de um trecho no corpo de outro
for it in range(3):
    new = []
    for i, s in enumerate(segs):
        ts = []
        for j, o in enumerate(segs):
            if i == j: continue
            for q in (o['a'], o['b']):
                d, t = dseg(q, s['a'], s['b']); Ls = math.dist(s['a'], s['b'])
                if d < 0.45 and 0.35 / Ls < t < 1 - 0.35 / Ls: ts.append(t)
        ts = sorted(ts); tt = []
        for t in ts:
            if not tt or (t - tt[-1]) * math.dist(s['a'], s['b']) > 0.4: tt.append(t)
        new += split_at(s, tt) if tt else [s]
    if len(new) == len(segs): break
    segs = new
say('trechos após cortes (caixas e tês):', len(segs))
# 5c nós
ends = [(i, 0, s['a']) for i, s in enumerate(segs)] + [(i, 1, s['b']) for i, s in enumerate(segs)]
node_of = {}; nodes = []
for b in boxes:
    b['n'] = len(nodes); nodes.append({'kind': b['tipo'], 'p': b['p'], 'box': b})
for i, e_, p in ends:
    bb = min(boxes, key=lambda b: math.dist(b['p'], p))
    if math.dist(bb['p'], p) < bb['r'] + 0.5: node_of[(i, e_)] = bb['n']
rest = [x for x in ends if (x[0], x[1]) not in node_of]
par = list(range(len(rest)))
def f(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
pts = np.array([r[2] for r in rest])
for i in range(len(rest)):
    d = np.hypot(pts[:, 0] - pts[i, 0], pts[:, 1] - pts[i, 1])
    for j in np.where(d < 0.55)[0]:
        if j > i: par[f(i)] = f(int(j))
grp = collections.defaultdict(list)
for k, r in enumerate(rest): grp[f(k)].append(r)
for g in grp.values():
    c = (sum(r[2][0] for r in g) / len(g), sum(r[2][1] for r in g) / len(g))
    nid = len(nodes); nodes.append({'kind': 'jun' if len(g) > 1 else 'ponta', 'p': c})
    for r in g: node_of[(r[0], r[1])] = nid
edges = []
for i, s in enumerate(segs):
    a, b = node_of[(i, 0)], node_of[(i, 1)]
    if a == b: continue
    edges.append({'u': a, 'v': b, 'pa': s['a'], 'pb': s['b'], 'd': s['d'], 'fl': s['fl'], 'src': s['src'], 'L': math.dist(s['a'], s['b'])})
# remove duplicatas (mesmo par de nós, mesma geometria)
seen = {}; ed2 = []
for e in sorted(edges, key=lambda e: (0 if 'seta' in e['src'] else 1)):
    k = tuple(sorted((e['u'], e['v'])))
    if k in seen and abs(seen[k]['L'] - e['L']) < 0.5 and (e['d'] is None or seen[k]['d'] is None or abs(e['d'] - seen[k]['d']) < 0.03): continue
    seen[k] = e; ed2.append(e)
edges = ed2
say('nós:', len(nodes), collections.Counter(n['kind'] for n in nodes), '| trechos:', len(edges), 'comp %.0f m' % sum(e['L'] for e in edges))
# 5d pontas livres a poucos cm/dm de caixa ou de outro trecho: ligar (desenho não encostou)
bridged = 0
for it in range(2):
    deg = collections.Counter()
    for e in edges: deg[e['u']] += 1; deg[e['v']] += 1
    for n, nd in enumerate(nodes):
        if nd['kind'] != 'ponta' or deg[n] != 1: continue
        p = nd['p']
        inc = [e for e in edges if n in (e['u'], e['v'])]
        bb = min(boxes, key=lambda b: math.dist(b['p'], p))
        if math.dist(bb['p'], p) < bb['r'] + 1.2:
            for e in inc:
                if e['u'] == n: e['u'] = bb['n']
                if e['v'] == n: e['v'] = bb['n']
            nd['kind'] = 'ligada'; bridged += 1; continue
        best = None
        for k, e in enumerate(edges):
            if n in (e['u'], e['v']): continue
            d, t = dseg(p, e['pa'], e['pb'])
            if d < 0.9 and (best is None or d < best[0]): best = (d, k, t)
        if best:
            d, k, t = best; e = edges[k]
            if t < 0.05 or t > 0.95:
                tgt = e['u'] if t < 0.5 else e['v']
            else:
                q = (e['pa'][0] + (e['pb'][0] - e['pa'][0]) * t, e['pa'][1] + (e['pb'][1] - e['pa'][1]) * t)
                tgt = len(nodes); nodes.append({'kind': 'jun', 'p': q})
                e2 = dict(e); e2['u'] = tgt; e2['pa'] = q; e2['L'] = math.dist(q, e['pb'])
                e['v'] = tgt; e['pb'] = q; e['L'] = math.dist(e['pa'], q)
                edges.append(e2)
            for e in inc:
                if e['u'] == n: e['u'] = tgt
                if e['v'] == n: e['v'] = tgt
            nd['kind'] = 'ligada'; bridged += 1
edges = [e for e in edges if e['u'] != e['v']]
say('pontas livres ligadas a caixa/trecho próximo (desenho não encostava):', bridged)

# ---------------------------------------------------------------- 6. lançamentos e árvore
adj = collections.defaultdict(list)
for k, e in enumerate(edges): adj[e['u']].append((e['v'], k)); adj[e['v']].append((e['u'], k))
OUTP = [(1.2, 59.0), (28.5, 57.8), (77.5, 55.8)]
outs = []
for p in OUTP:
    n = min(range(len(nodes)), key=lambda i: math.dist(nodes[i]['p'], p) if adj[i] else 99)
    outs.append(n); nodes[n]['kind'] = 'LANÇAMENTO'
say('lançamentos:', [(round(nodes[n]['p'][0], 1), round(nodes[n]['p'][1], 1)) for n in outs])
# Dijkstra multi-fonte (distância hidráulica até a saída)
import heapq
dist = {n: 0.0 for n in outs}; root = {n: n for n in outs}; parent = {}
h = [(0.0, n) for n in outs]
while h:
    d, x = heapq.heappop(h)
    if d > dist.get(x, 1e9): continue
    for y, k in adj[x]:
        nd = d + edges[k]['L']
        if nd < dist.get(y, 1e9): dist[y] = nd; root[y] = root[x]; parent[y] = (x, k); heapq.heappush(h, (nd, y))
# orienta: montante = nó mais longe da saída
conf = 0; noarrow = 0
for e in edges:
    du, dv = dist.get(e['u']), dist.get(e['v'])
    if du is None or dv is None: e['dir'] = None; continue
    if du >= dv: e['up'], e['dn'] = e['u'], e['v']
    else: e['up'], e['dn'] = e['v'], e['u']
    e['bacia'] = root[e['dn']]
    # confere com seta: fl>0 = sentido pa->pb
    pu = e['pa'] if e['up'] == e['u'] else e['pb']
    if e['fl']:
        seta_up_is_pa = e['fl'] > 0
        if seta_up_is_pa != (pu == e['pa']): conf += 1; e['conflito_seta'] = True
    else: noarrow += 1
orph = [e for e in edges if e.get('bacia') is None]
say('trechos sem caminho até lançamento:', len(orph), '%.0f m' % sum(e['L'] for e in orph))
say('trechos com sentido da árvore CONTRA a seta do projeto:', conf, '| sem seta:', noarrow)
bac = collections.defaultdict(float)
for e in edges:
    if e.get('bacia') is not None: bac[e['bacia']] += e['L']
say('bacias (m):', {str((round(nodes[k]['p'][0]), round(nodes[k]['p'][1]))): round(v) for k, v in bac.items()})
# componentes órfãos
par2 = {}
def f2(x):
    par2.setdefault(x, x)
    while par2[x] != x: x = par2[x]
    return x
for e in orph: par2[f2(e['u'])] = f2(e['v'])
comp = collections.defaultdict(list)
for e in orph: comp[f2(e['u'])].append(e)
say('componentes sem lançamento:', len(comp))
for c in sorted(comp.values(), key=lambda c: -sum(e['L'] for e in c))[:25]:
    xs = [p for e in c for p in (e['pa'], e['pb'])]
    say('   %.1f m, %d trechos, perto de (%.1f, %.1f)' % (sum(e['L'] for e in c), len(c), sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs)))
# caixas sem ligação / prumadas sem ligação
deg = collections.Counter()
for e in edges: deg[e['u']] += 1; deg[e['v']] += 1
semtubo = [b for b in boxes if deg[b['n']] == 0]
say('caixas/PVs sem nenhum tubo:', len(semtubo), [(b['id'], round(b['p'][0], 1), round(b['p'][1], 1)) for b in semtubo])
semcol = [c for c in cols if min(dseg(c, e['pa'], e['pb'])[0] for e in edges) > 1.0]
say('prumadas AP sem tubo a < 1 m:', len(semcol), [tuple(round(v, 1) for v in c) for c in semcol])
pontas = [n for i, n in enumerate(nodes) if n['kind'] == 'ponta']
say('pontas livres (início de ramal):', len(pontas))
pickle.dump({'nodes': nodes, 'edges': edges, 'boxes': boxes, 'cols': cols, 'outs': outs, 'dist': dist}, open(W + 'v2_net.pkl', 'wb'))
open(W + 'v2_relatorio.txt', 'w', encoding='utf-8').write('\n'.join(rep))
