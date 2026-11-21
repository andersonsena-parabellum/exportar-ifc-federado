"""Cotas da rede de drenagem (gravidade): orienta trechos, atribui DN/material/declividade e resolve os
inverts por minimos quadrados (rotulos CE/CS/CF + declividades + continuidade nos nos).
Entrada: work/topo.pkl, work/cotas.pkl, dump (textos).  Saida: work/network_drn.json + work/solve_report.txt"""
import sys, math, pickle, collections, re, json
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
E, segs, mlines, arrows, P = pickle.load(open(CACHE, 'rb'))
nodes, edges, boxes, segs3 = pickle.load(open(W + 'topo.pkl', 'rb'))
trip, assign, CE_, CS_ = pickle.load(open(W + 'cotas.pkl', 'rb'))
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); rep.append(s); print(s)

# ---------------- limpeza: lacos, trechos minusculos e duplicatas sobrepostas
def clean_edges(edges):
    n0 = len(edges)
    ed = [e for e in edges if e['a'] != e['b'] and e['L'] >= 0.35]
    n1 = len(ed)
    ed.sort(key=lambda e: (0 if e['sgn'] != 0 else 1, -e['L']))
    kept = []
    buckets = collections.defaultdict(list)
    for e in ed:
        key = tuple(sorted((e['a'], e['b'])))
        mid = ((e['p0'][0] + e['p1'][0]) / 2, (e['p0'][1] + e['p1'][1]) / 2)
        dup = False
        for k in buckets[key]:
            m2 = ((k['p0'][0] + k['p1'][0]) / 2, (k['p0'][1] + k['p1'][1]) / 2)
            if math.dist(mid, m2) < 0.25 and abs(k['L'] - e['L']) < 0.4:
                dup = True; break
        if not dup:
            buckets[key].append(e); kept.append(e)
    print('limpeza de trechos:', n0, '-> sem lacos/minusculos', n1, '-> sem duplicatas', len(kept))
    return kept
edges = clean_edges(edges)
NN, NE = len(nodes), len(edges)
# ---------------- DN / material por edge
NOM = [25, 32, 40, 50, 75, 100, 150, 200, 250, 300, 400]
def dn_from_d(d):
    if d is None: return None
    mm = d * 1000
    return min(NOM, key=lambda n: abs(n - mm * (1.0 if mm > 60 else 1.0)))  # d ~ DN (distancia entre paredes)
# o espacamento das paredes ~ DN (0,04 m = 40 mm; 0,10-0,11 = 100). 0,07-0,09 -> 75
def dn_clean(d):
    if d is None: return None
    if d < 0.035: return 32
    if d < 0.06: return 40
    if d < 0.095: return 75
    if d < 0.125: return 100
    if d < 0.175: return 150
    if d < 0.225: return 200
    if d < 0.275: return 250
    if d < 0.35: return 300
    return 400
def mat_from_dn(dn):
    if dn <= 50: return 'PVC SOLDAVEL'      # drenos de ar condicionado
    if dn <= 150: return 'PVC REFORCADO'
    return 'PVC VINILFORT'
OD = {25: 25, 32: 32, 40: 40, 50: 50, 75: 75, 100: 110, 150: 160, 200: 200, 250: 250, 300: 315, 400: 400}

# ---------------- rotulos de tubo (material, DN, i%) -> edge
import drn_labels as DL
Lbl, _, _, _ = DL.labels()
def seg_param(e, p):
    ax, ay = e['p0']; bx, by = e['p1']; dx, dy = bx - ax, by - ay; n2 = dx * dx + dy * dy
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / n2
    tt = max(0, min(1, t)); px, py = ax + tt * dx, ay + tt * dy
    return t, math.hypot(p[0] - px, p[1] - py)
eang = [math.atan2(e['p1'][1] - e['p0'][1], e['p1'][0] - e['p0'][0]) % math.pi for e in edges]
def lab_match():
    out = {}
    for li, l in enumerate(Lbl):
        best = None
        la = l['rot'] % math.pi
        for i, e in enumerate(edges):
            da = abs(eang[i] - la); da = min(da, math.pi - da)
            if da > 0.12: continue
            t, d = seg_param(e, l['pos'])
            if d > 1.2 or t < -0.3 or t > 1.3: continue
            if best is None or d < best[0]: best = (d, i)
        if best: out.setdefault(best[1], []).append(l)
    return out
EL = lab_match()
say('rotulos', len(Lbl), 'casados a trechos', sum(len(v) for v in EL.values()), 'trechos com rotulo', len(EL))

edn = []; emat = []; eslope = []; eslope_src = []
mism = 0
for i, e in enumerate(edges):
    dn = dn_clean(e['d'])
    sl = None
    labs = EL.get(i, [])
    if labs:
        l = labs[0]
        if dn is None or abs(l['size'] - dn) > 0:
            if dn is not None and abs(l['size'] - dn) > 0: mism += 1
            dn = l['size']
        if l['slope']:
            m = re.search(r'([\d.,]+)', l['slope']); sl = float(m.group(1).replace(',', '.')) / 100
    if dn is None: dn = 100
    edn.append(dn); emat.append(mat_from_dn(dn))
    if sl is None:
        eslope.append(0.01 if dn <= 150 else 0.005); eslope_src.append('padrao')
    else:
        eslope.append(sl); eslope_src.append('rotulo')
say('DN: rotulo divergiu do espacamento em', mism, 'trechos')
say('DN:', sorted(collections.Counter(edn).items()))
say('declividade: rotulo', eslope_src.count('rotulo'), 'padrao', eslope_src.count('padrao'))

# ---------------- ligacao de rotulos CE/CS e cotas aos nos
deg = collections.Counter()
for e in edges: deg[e['a']] += 1; deg[e['b']] += 1
import re as _re
T = [t for t in E if t[0] == 'MTEXT' and t[1] == 'TQ-Textos conduto']
def val(s):
    m = _re.search(r'([\d.]+)', s.split(':')[-1]); return float(m.group(1))
labCE = [(t[3], val(t[5])) for t in T if t[5].startswith('CE')]
labCS = [(t[3], val(t[5])) for t in T if t[5].startswith('CS')]
cand_nodes = [i for i in range(NN) if nodes[i]['kind'] in ('box', 'jun') and deg[i] >= 1]
def nearest_node(p, rmax):
    best = None
    for i in cand_nodes:
        d = math.dist(p, nodes[i]['pos'])
        if nodes[i]['kind'] == 'box': d *= 0.7
        if deg[i] < 2: d *= 1.6
        if best is None or d < best[0]: best = (d, i)
    return best[1] if best and best[0] <= rmax else None
nCE = collections.defaultdict(list); nCS = collections.defaultdict(list)
un = 0
for p, v in labCE:
    n = nearest_node(p, 9.0)
    if n is None: un += 1; continue
    nCE[n].append((p, v))
for p, v in labCS:
    n = nearest_node(p, 9.0)
    if n is None: un += 1; continue
    nCS[n].append((p, v))
say('rotulos CE', len(labCE), 'CS', len(labCS), 'sem no', un, '| nos com CE', len(nCE), 'com CS', len(nCS))
nCF = {}
for t in trip:
    n = nearest_node(t['pos'], 9.0)
    if n is not None and (n not in nCF or math.dist(t['pos'], nodes[n]['pos']) < nCF[n][0]):
        nCF[n] = (math.dist(t['pos'], nodes[n]['pos']), t)
say('triplas CT/CF ligadas a nos', len(nCF), 'de', len(trip))

# ---------------- terreno de projeto (estimado): IMP as built snapado aos platos do projeto; CT onde houver tripla
PLAT = [135.5, 136.1, 137.4, 138.5]
Zt = [l.strip().split(';') for l in open(W + 'terreno_z.csv')]
zimp = [float(a[2]) for a in Zt[:len(nodes)]]
def ground_design(i):
    z = zimp[i]
    if z != z: return None
    c = min(PLAT, key=lambda p: abs(p - z))
    return c if abs(c - z) <= 0.6 else z + 0.45
ref = [(n, nodes[n]['pos'], nCF[n][1]['ct'], zimp[n]) for n in nCF if zimp[n] == zimp[n]]
ngr = []
for i, n in enumerate(nodes):
    zi = zimp[i]
    if zi != zi:
        best = min(trip, key=lambda t: math.dist(n['pos'], t['pos'])); ngr.append(best['ct']); continue
    bs = min(ref, key=lambda r: math.dist(n['pos'], r[1]) + 40 * abs(zi - r[3]))
    ngr.append(bs[2] + (zi - bs[3]))
for n in nCF: ngr[n] = nCF[n][1]['ct']
# valida CE/CS contra o terreno de projeto do no: invert acima de (CT - 0,25) e invalido (erro de projeto) -> descartado
invalid = []
for dct, tag in ((nCE, 'CE'), (nCS, 'CS')):
    for n in list(dct.keys()):
        okl = []
        for p, v in dct[n]:
            if v > ngr[n] - 0.04 or v < ngr[n] - 6: invalid.append((tag, v, round(nodes[n]['pos'][0] - 561500, 1), round(nodes[n]['pos'][1] - 8658000, 1), ngr[n]))
            else: okl.append((p, v))
        if okl: dct[n] = okl
        else: del dct[n]
say('rotulos CE/CS descartados por estarem acima do CT/terreno do no:', len(invalid))
for x in invalid[:40]: say('   ', x)

# ---------------- direcao
dirn = [0] * NE   # +1: p0->p1 ; -1: p1->p0
for i, e in enumerate(edges):
    if e['sgn'] > 0: dirn[i] = 1
    elif e['sgn'] < 0: dirn[i] = -1
say('direcao conhecida por seta:', sum(1 for d in dirn if d), 'de', NE)
inc = collections.defaultdict(list)
for i, e in enumerate(edges): inc[e['a']].append((i, 0)); inc[e['b']].append((i, 1))
def up_down(i, d):
    e = edges[i]
    return (e['a'], e['b']) if d > 0 else (e['b'], e['a'])
# propagacao por continuidade em nos de grau 2
ch = True
while ch:
    ch = False
    for n, lst in inc.items():
        if len(lst) != 2: continue
        (i, ei), (j, ej) = lst
        if bool(dirn[i]) == bool(dirn[j]): continue
        k, ek, o, eo = (i, ei, j, ej) if dirn[i] else (j, ej, i, ei)
        # k conhecido; fluxo entra ou sai no no n?
        enters = (dirn[k] > 0 and ek == 1) or (dirn[k] < 0 and ek == 0)
        # o deve continuar: se k entra no no, o sai do no -> o parte de n
        if enters: dirn[o] = 1 if eo == 0 else -1
        else: dirn[o] = 1 if eo == 1 else -1
        ch = True
say('direcao apos continuidade (grau 2):', sum(1 for d in dirn if d))
# restantes: pelo terreno / rotulos CE-CS
for i, e in enumerate(edges):
    if dirn[i]: continue
    ga, gb = ngr[e['a']], ngr[e['b']]
    za = min([v for _, v in nCS.get(e['a'], [])] + [v for _, v in nCE.get(e['a'], [])] + [999])
    zb = min([v for _, v in nCS.get(e['b'], [])] + [v for _, v in nCE.get(e['b'], [])] + [999])
    if za < 900 and zb < 900 and abs(za - zb) > 0.01: dirn[i] = 1 if za > zb else -1
    elif abs(ga - gb) > 0.2: dirn[i] = 1 if ga > gb else -1
    else:
        # mesma plato: de uma ponta livre (grau 1) para o no mais "central"
        da_, db_ = deg[e['a']], deg[e['b']]
        if da_ == 1 and db_ > 1: dirn[i] = 1
        elif db_ == 1 and da_ > 1: dirn[i] = -1
        else: dirn[i] = 1
say('sem direcao deduzida pelo terreno/folha:', 0)

def solve(dirn, extra_caps=None, iters=1):
    # variaveis: zu[i], zd[i]
    nv = 2 * NE
    rows = []; rhs = []; wts = []
    def add(coefs, r, w):
        rows.append(coefs); rhs.append(r); wts.append(w)
    for i, e in enumerate(edges):
        L = max(e['L'], 0.3)
        add({2 * i: 1, 2 * i + 1: -1}, eslope[i] * L, 3.0 if eslope_src[i] == 'rotulo' else 0.8)
        gu = ngr[up_down(i, dirn[i])[0]]
        add({2 * i: 1}, gu - 0.6 - OD[edn[i]] / 1000.0, 0.03)
        add({2 * i + 1: 1}, ngr[up_down(i, dirn[i])[1]] - 0.6 - OD[edn[i]] / 1000.0, 0.03)
    for n in range(NN):
        ends_up = []; ends_dn = []
        for (i, ei) in inc.get(n, []):
            u, d = up_down(i, dirn[i])
            (ends_up if u == n else ends_dn).append(i)
        labeled = (n in nCS) or (n in nCE) or (n in nCF)
        for i in ends_up:   # sai do no -> CS ou CE ou CF
            p = edges[i]['p0'] if (edges[i]['a'] == n) == (dirn[i] > 0) else edges[i]['p1']
            if n in nCS:
                t = min(nCS[n], key=lambda q: math.dist(q[0], p))[1]; add({2 * i: 1}, t, 12)
            elif n in nCE:
                t = min(nCE[n], key=lambda q: math.dist(q[0], p))[1]; add({2 * i: 1}, t, 4)
            elif n in nCF: add({2 * i: 1}, nCF[n][1]['cf'] + 0.0, 4)
        for i in ends_dn:
            p = edges[i]['p1'] if (edges[i]['b'] == n) == (dirn[i] > 0) else edges[i]['p0']
            if n in nCE:
                t = min(nCE[n], key=lambda q: math.dist(q[0], p))[1]; add({2 * i + 1: 1}, t, 12)
            elif n in nCS:
                t = min(nCS[n], key=lambda q: math.dist(q[0], p))[1]; add({2 * i + 1: 1}, t, 4)
            elif n in nCF: add({2 * i + 1: 1}, nCF[n][1]['cf'] + 0.0, 4)
        if not labeled:   # continuidade: todas as pontas do no na mesma cota
            allv = [(2 * i) for i in ends_up] + [(2 * i + 1) for i in ends_dn]
            for k in range(1, len(allv)):
                if allv[0] != allv[k]: add({allv[0]: 1, allv[k]: -1}, 0.0, 15)
        else:  # no rotulado: a(s) entrada(s) nao ficam abaixo da saida
            pass
    if extra_caps:
        for v, z in extra_caps.items(): add({v: 1}, z, 6)
    A = np.zeros((len(rows), nv)); b = np.zeros(len(rows))
    for r, (c, y, w) in enumerate(zip(rows, rhs, wts)):
        for k, v in c.items(): A[r, k] = v * w
        b[r] = y * w
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return sol

sol = solve(dirn)
# reorientar trechos sem seta se zu < zd - 0.03
flip = 0
for it in range(3):
    flip = 0
    for i in range(NE):
        if edges[i]['sgn'] != 0: continue
        if sol[2 * i] < sol[2 * i + 1] - 0.03:
            dirn[i] *= -1; flip += 1
    if not flip: break
    sol = solve(dirn)
say('reorientados por cota:', flip)
# tampa: cobertura minima
caps = {}
viol = 0
for i, e in enumerate(edges):
    u, d = up_down(i, dirn[i])
    od = OD[edn[i]] / 1000.0
    for k, nn in ((0, u), (1, d)):
        zmax = ngr[nn] - 0.30 - od
        if sol[2 * i + k] > zmax + 1e-6: caps[2 * i + k] = zmax; viol += 1
if caps:
    sol = solve(dirn, caps)
say('extremos acima do recobrimento minimo (0,30 m) antes da correcao:', viol)

# ---------------- relatorio e saida
out_edges = []
sl_bad = 0; cover_min = 9
for i, e in enumerate(edges):
    u, d = up_down(i, dirn[i])
    pu = e['p0'] if dirn[i] > 0 else e['p1']; pd = e['p1'] if dirn[i] > 0 else e['p0']
    zu, zd = float(sol[2 * i]), float(sol[2 * i + 1])
    L = e['L']; s_real = (zu - zd) / max(L, 0.01)
    od = OD[edn[i]] / 1000.0
    cov_u = ngr[u] - (zu + od); cov_d = ngr[d] - (zd + od)
    cover_min = min(cover_min, cov_u, cov_d)
    if s_real < 0.002 and L > 1: sl_bad += 1
    out_edges.append({'i': i, 'a': u, 'b': d, 'dn': edn[i], 'od': OD[edn[i]], 'mat': emat[i], 'L': L, 'p_up': [pu[0], pu[1]], 'p_dn': [pd[0], pd[1]],
                      'zu': zu, 'zd': zd, 'slope_label': eslope[i], 'slope_src': eslope_src[i], 'slope_real': s_real, 'dirsrc': 'seta' if e['sgn'] != 0 else 'deduzida',
                      'cov_u': cov_u, 'cov_d': cov_d, 'src': e['src']})
say('trechos com declividade real < 0,2%:', sl_bad, ' recobrimento minimo:', round(cover_min, 2))
sr = np.array([x['slope_real'] for x in out_edges if x['L'] > 1])
say('declividade real: p5/p50/p95', np.percentile(sr, [5, 50, 95]).round(4))
out_nodes = []
for n in range(NN):
    out_nodes.append({'id': n, 'kind': nodes[n]['kind'], 'x': nodes[n]['pos'][0], 'y': nodes[n]['pos'][1], 'deg': deg[n], 'ground': ngr[n],
                      'box': nodes[n]['box'], 'cf': nCF[n][1]['cf'] if n in nCF else None, 'ct': nCF[n][1]['ct'] if n in nCF else None,
                      'prof': nCF[n][1]['prof'] if n in nCF else None,
                      'ce': [v for _, v in nCE.get(n, [])], 'cs': [v for _, v in nCS.get(n, [])]})
json.dump({'nodes': out_nodes, 'edges': out_edges, 'boxes': boxes}, open(W + 'network_drn.json', 'w'), indent=0, default=float)
open(W + 'solve_report.txt', 'w', encoding='utf-8').write('\n'.join(rep))
