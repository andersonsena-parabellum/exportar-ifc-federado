import sys, math, pickle, collections, json
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
merged, boxes = pickle.load(open(W + 'net.pkl', 'rb'))
TOLB = 0.45   # raio de captura da caixa (alem do retangulo)
TOLJ = 0.55   # captura de juncao

def inbox(p, b, t=TOLB):
    return b['xmin'] - t <= p[0] <= b['xmax'] + t and b['ymin'] - t <= p[1] <= b['ymax'] + t
def boxof(p):
    best = None
    for i, b in enumerate(boxes):
        if inbox(p, b):
            d = math.dist(p, b['c'])
            if best is None or d < best[0]: best = (d, i)
    return best[1] if best else None
def seg_hits_box(s, b):
    # amostra a reta
    n = max(2, int(math.dist(s['p0'], s['p1']) / 0.1))
    inside = []
    for k in range(n + 1):
        t = k / n; p = (s['p0'][0] + (s['p1'][0] - s['p0'][0]) * t, s['p0'][1] + (s['p1'][1] - s['p0'][1]) * t)
        inside.append(inbox(p, b, 0.0))
    return inside
# 1) dividir segmentos que atravessam caixas
segs2 = []
for s in merged:
    L = math.dist(s['p0'], s['p1'])
    if L < 0.2: continue
    cuts = []
    for i, b in enumerate(boxes):
        ins = seg_hits_box(s, b)
        if any(ins) and not ins[0] and not ins[-1]:
            idx = [k for k, v in enumerate(ins) if v]
            cuts.append((idx[0] / (len(ins) - 1), idx[-1] / (len(ins) - 1), i))
    if not cuts: segs2.append(dict(s, via=None)); continue
    cuts.sort(); prev = 0.0; pts = []
    for t0, t1, i in cuts:
        pts.append((prev, t0, None)); prev = t1
    pts.append((prev, 1.0, None))
    for k, (ta, tb, _) in enumerate(pts):
        if tb - ta <= 0: continue
        P0 = (s['p0'][0] + (s['p1'][0] - s['p0'][0]) * ta, s['p0'][1] + (s['p1'][1] - s['p0'][1]) * ta)
        P1 = (s['p0'][0] + (s['p1'][0] - s['p0'][0]) * tb, s['p0'][1] + (s['p1'][1] - s['p0'][1]) * tb)
        if math.dist(P0, P1) > 0.2: segs2.append(dict(s, p0=P0, p1=P1, via=None))
print('apos corte em caixas', len(segs2))
# 2) t-junctions: dividir segmento onde o fim de outro cai no seu corpo
def split_t(segs):
    out = list(segs); changed = True; it = 0
    while changed and it < 5:
        changed = False; it += 1
        new = []
        for a in out:
            cuts = []
            for b in out:
                if b is a: continue
                for q in (b['p0'], b['p1']):
                    if boxof(q) is not None: continue
                    dx, dy = a['p1'][0] - a['p0'][0], a['p1'][1] - a['p0'][1]; n2 = dx * dx + dy * dy
                    t = ((q[0] - a['p0'][0]) * dx + (q[1] - a['p0'][1]) * dy) / n2
                    L = math.sqrt(n2)
                    if 0.4 / L < t < 1 - 0.4 / L:
                        px, py = a['p0'][0] + dx * t, a['p0'][1] + dy * t
                        if math.hypot(q[0] - px, q[1] - py) < TOLJ:
                            cuts.append(t)
            if cuts:
                cuts = sorted(set(round(c, 4) for c in cuts))
                # remover cortes quase iguais
                cc = [cuts[0]]
                for c in cuts[1:]:
                    if (c - cc[-1]) * math.sqrt((a['p1'][0] - a['p0'][0]) ** 2 + (a['p1'][1] - a['p0'][1]) ** 2) > 0.5: cc.append(c)
                ts = [0.0] + cc + [1.0]
                for k in range(len(ts) - 1):
                    P0 = (a['p0'][0] + (a['p1'][0] - a['p0'][0]) * ts[k], a['p0'][1] + (a['p1'][1] - a['p0'][1]) * ts[k])
                    P1 = (a['p0'][0] + (a['p1'][0] - a['p0'][0]) * ts[k + 1], a['p0'][1] + (a['p1'][1] - a['p0'][1]) * ts[k + 1])
                    new.append(dict(a, p0=P0, p1=P1)); changed = True
            else: new.append(a)
        out = new
    return out
segs3 = split_t(segs2)
print('apos T', len(segs3))
# 3) nos: caixas e juncoes (clusters de pontas)
nodes = []  # {'kind','pos','box'}
ends = []
for i, s in enumerate(segs3):
    for e in (0, 1):
        ends.append((i, e, s['p0'] if e == 0 else s['p1']))
node_of = {}
for i, e, p in ends:
    b = boxof(p)
    if b is not None:
        key = ('box', b)
        if key not in node_of:
            node_of[key] = len(nodes); nodes.append({'kind': 'box', 'pos': boxes[b]['c'], 'box': b, 'pts': []})
        nodes[node_of[key]]['pts'].append(p); node_of[(i, e)] = node_of[key]
rest = [(i, e, p) for i, e, p in ends if (i, e) not in node_of]
# juncao: encontrar clusters (ponta-ponta) e ponta-corpo (T) ja dividido => ponta-ponta
used = set()
for a in range(len(rest)):
    if (rest[a][0], rest[a][1]) in used: continue
    grp = [rest[a]]
    for b in range(a + 1, len(rest)):
        if (rest[b][0], rest[b][1]) in used: continue
        if any(math.dist(rest[b][2], g[2]) < TOLJ for g in grp): grp.append(rest[b])
    for g in grp: used.add((g[0], g[1]))
    cx = sum(g[2][0] for g in grp) / len(grp); cy = sum(g[2][1] for g in grp) / len(grp)
    nodes.append({'kind': 'jun' if len(grp) > 1 else 'end', 'pos': (cx, cy), 'box': None, 'pts': [g[2] for g in grp]})
    for g in grp: node_of[(g[0], g[1])] = len(nodes) - 1
edges = []
for i, s in enumerate(segs3):
    edges.append({'a': node_of[(i, 0)], 'b': node_of[(i, 1)], 'd': s['d'], 'sgn': s['sgn'], 'dir': s['dir'], 'L': math.dist(s['p0'], s['p1']), 'src': s['src'], 'p0': s['p0'], 'p1': s['p1']})
deg = collections.Counter()
for e in edges: deg[e['a']] += 1; deg[e['b']] += 1
print('nos', len(nodes), collections.Counter(n['kind'] for n in nodes), 'trechos', len(edges))
print('grau (juncoes):', collections.Counter(deg[i] for i, n in enumerate(nodes) if n['kind'] == 'jun'))
print('pontas livres', sum(1 for i, n in enumerate(nodes) if n['kind'] == 'end'), 'caixas sem trecho', sum(1 for i, n in enumerate(nodes) if n['kind'] == 'box' and deg[i] == 0))
print('caixas totais', len(boxes), 'caixas com no', sum(1 for n in nodes if n['kind'] == 'box'))
pickle.dump((nodes, edges, boxes, segs3), open(W + 'topo.pkl', 'wb'))
