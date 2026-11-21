"""v2c: DN/material/declividade por trecho + cotas (mínimos quadrados com sentido fixo) + validação."""
import sys, math, pickle, json, collections, re, csv
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import numpy as np
import drn_labels as DL
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
D = pickle.load(open(W + 'v2_net.pkl', 'rb'))
nodes, edges, boxes, outs = D['nodes'], D['edges'], D['boxes'], D['outs']
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); rep.append(s); print(s)
L = lambda p: (p[0] - 561500, p[1] - 8658000)
def dseg(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; n2 = dx * dx + dy * dy
    t = 0 if n2 == 0 else max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / n2))
    return math.hypot(q[0] - a[0] - t * dx, q[1] - a[1] - t * dy), t
def ang(a, b): return math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi
# ---- rótulos de tubo
Lbl, _, _, _ = DL.labels()
for l in Lbl: l['p'] = L(l['pos'])
for e in edges:
    e['ang'] = ang(e['pa'], e['pb']); best = None
    for l in Lbl:
        da = abs(e['ang'] - l['rot'] % math.pi); da = min(da, math.pi - da)
        if da > 0.15: continue
        d, t = dseg(l['p'], e['pa'], e['pb'])
        if d < 1.3 and (best is None or d < best[0]): best = (d, l)
    e['lab'] = best[1] if best else None
def dn_from_d(d):
    if d is None: return None
    for lim, dn in ((0.035, 32), (0.06, 40), (0.095, 75), (0.125, 100), (0.175, 150), (0.225, 200), (0.275, 250), (0.35, 300)):
        if d < lim: return dn
    return 400
for e in edges:
    e['DN'] = dn_from_d(e['d']); e['sl'] = None
    if e['lab']:
        if e['DN'] is None or e['DN'] == e['lab']['size'] or e['d'] is None: e['DN'] = e['lab']['size']
        if e['lab']['slope']:
            m = re.search(r'([\d.,]+)', e['lab']['slope']); e['sl'] = float(m.group(1).replace(',', '.')) / 100
inc = collections.defaultdict(list)
for k, e in enumerate(edges): inc[e['up']].append(k); inc[e['dn']].append(k)
# rótulo vale para o trecho inteiro entre caixas (colineares contíguos)
for it in range(6):
    for k, e in enumerate(edges):
        if e['DN'] is not None and e['sl'] is not None: continue
        for n in (e['up'], e['dn']):
            if nodes[n]['kind'] in ('CA', 'PV'): continue
            for j in inc[n]:
                o = edges[j]
                if j == k: continue
                da = abs(o['ang'] - e['ang']); da = min(da, math.pi - da)
                if da < 0.05:
                    if e['DN'] is None and o['DN'] is not None: e['DN'] = o['DN']
                    if e['sl'] is None and o['sl'] is not None: e['sl'] = o['sl']
for e in edges:
    if e['DN'] is None: e['DN'] = 32 if e['d'] is None else 40
    if e['DN'] == 25: e['DN'] = 32
    e['mat'] = 'PVC SOLDAVEL' if e['DN'] <= 50 else ('PVC REFORCADO' if e['DN'] <= 150 else 'PVC VINILFORT')
    e['sl_src'] = 'rótulo' if e['sl'] is not None else 'padrão 1%'
    if e['sl'] is None: e['sl'] = 0.01
    e['od'] = {32: 32, 40: 40, 50: 50, 75: 75, 100: 110, 150: 160, 200: 200, 250: 250, 300: 315, 400: 400}[e['DN']] / 1000
say('DN:', sorted(collections.Counter(e['DN'] for e in edges).items()), '| declividade de rótulo:', sum(1 for e in edges if e['sl_src'] == 'rótulo'), 'de', len(edges))
# ---- terreno de projeto
Zt = {}
for l in open(W + 'terreno_z.csv'):
    x, y, z = l.strip().split(';')
    if z != 'NaN': Zt[(float(x), float(y))] = float(z)
ZP = np.array(list(Zt.keys())); ZV = np.array(list(Zt.values()))
def zimp(p):
    i = np.argmin((ZP[:, 0] - p[0]) ** 2 + (ZP[:, 1] - p[1]) ** 2); return ZV[i]
ref = [(b['p'], b['CT'], zimp(b['p'])) for b in boxes if b['CT']]
def ground(p):
    zi = zimp(p); r = min(ref, key=lambda r: math.dist(p, r[0]) + 40 * abs(zi - r[2])); return r[1] + (zi - r[2])
for n in nodes: n['g'] = n['box']['CT'] if n.get('box') and n['box'].get('CT') else ground(n['p'])
# ---- cotas
NE = len(edges); rows = []; rhs = []; wts = []
def add(c, r, w): rows.append(c); rhs.append(r); wts.append(w)
for k, e in enumerate(edges):
    add({2 * k: 1, 2 * k + 1: -1}, e['sl'] * max(e['L'], 0.3), 3.0 if e['sl_src'] == 'rótulo' else 1.0)
    for s, n in ((0, e['up']), (1, e['dn'])):
        add({2 * k + s: 1}, nodes[n]['g'] - 0.6 - e['od'], 0.02)
for n, nd in enumerate(nodes):
    ups = [k for k in inc[n] if edges[k]['up'] == n]; dns = [k for k in inc[n] if edges[k]['dn'] == n]
    b = nd.get('box')
    if b:
        cs, ce, cf = b['CS'], b['CE'], b['CF']
        if cf is not None and b['CT'] is not None and cf > b['CT'] - 0.1: cf = None
        top = b['CT'] or nd['g']   # rótulo de CE/CS acima da tampa/terreno = erro do projeto: não usar, registrar
        badl = [v for v in (cs or []) + (ce or []) if v > top - 0.15]
        if badl:
            b['rot_incoerente'] = badl; say('rótulo CE/CS acima da tampa/terreno descartado:', b['id'], badl, 'topo %.2f' % top)
            cs = [v for v in (cs or []) if v <= top - 0.15]; ce = [v for v in (ce or []) if v <= top - 0.15]
        for k in ups:
            if cs: add({2 * k: 1}, min(cs), 10)
            elif cf: add({2 * k: 1}, cf, 8)
        for k in dns:
            if ce: add({2 * k + 1: 1}, max(ce), 10)
            elif cf: add({2 * k + 1: 1}, cf, 6)
            elif cs: add({2 * k + 1: 1}, max(cs), 4)
    else:
        allv = [2 * k for k in ups] + [2 * k + 1 for k in dns]
        for v in allv[1:]: add({allv[0]: 1, v: -1}, 0.0, 15)
A = np.zeros((len(rows), 2 * NE)); bvec = np.zeros(len(rows))
for r, (c, y, w) in enumerate(zip(rows, rhs, wts)):
    for kk, v in c.items(): A[r, kk] += v * w
    bvec[r] = y * w
sol = np.linalg.lstsq(A, bvec, rcond=None)[0]
for k, e in enumerate(edges):
    e['zu'], e['zd'] = float(sol[2 * k]), float(sol[2 * k + 1])
    e['i'] = (e['zu'] - e['zd']) / max(e['L'], 0.01)
    e['cov_u'] = nodes[e['up']]['g'] - e['zu'] - e['od']; e['cov_d'] = nodes[e['dn']]['g'] - e['zd'] - e['od']
up_ = [e for e in edges if e['i'] < -0.001 and e['L'] > 1]
flat = [e for e in edges if 0 <= e['i'] < 0.003 and e['L'] > 1]
steep = [e for e in edges if e['i'] > 0.05 and e['L'] > 1]
shallow = [e for e in edges if min(e['cov_u'], e['cov_d']) < 0.20]
say('trechos subindo (contra o escoamento):', len(up_), '| quase planos <0,3%:', len(flat), '| >5%:', len(steep), '| recobrimento <0,20 m:', len(shallow))
say('declividade p5/p50/p95:', np.percentile([e['i'] for e in edges if e['L'] > 1], [5, 50, 95]).round(4))
for e in sorted(up_, key=lambda e: e['i'])[:20]:
    pu = nodes[e['up']]['p']
    say('   sobe: L=%.1f DN%d i=%.2f%% em (%.1f,%.1f) %s->%s' % (e['L'], e['DN'], e['i'] * 100, pu[0], pu[1], nodes[e['up']]['kind'], nodes[e['dn']]['kind']))
pickle.dump(D, open(W + 'v2_net.pkl', 'wb'))
open(W + 'v2c_relatorio.txt', 'w', encoding='utf-8').write('\n'.join(rep))
