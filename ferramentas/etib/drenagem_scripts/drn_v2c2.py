"""v2c2 (14/10/2026): cotas da rede v2 como o projetista desenhou.
- declividade de cada tubo horizontal = rótulo (ou 1% adotado) -> não se "força" inclinação para vencer desnível;
- desnível vencido nas CONEXÕES VERTICAIS do desenho (círculos duplos Simbolos/Simbolos_int):
    * MERGULHO na chegada à caixa: o tubo chega mais alto e desce na vertical até a CE;
    * PÉ DE PRUMADA / subida de dreno: joelho no início do ramal, trecho vertical até o terreno;
- CE/CS valem para o tubo ao qual o rótulo se refere (o mais próximo), não para todas as entradas/saídas;
- fundo (CF) de CA sem CE/CS é limite inferior (caixa de areia tem rebaixo), não cota do tubo;
- incoerências do projeto (rótulos de caixa x declividade) ficam no modelo como o projeto manda e vão para o relatório.
Saída: work/v2_net.pkl (campos zu, zd, i, drop, riser...) + work/v2c2_relatorio.txt"""
import sys, math, pickle, collections, re
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import numpy as np
import drn_labels as DL
from drn_geom import CACHE
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
D = pickle.load(open(W + 'v2_net.pkl', 'rb'))
nodes, boxes, outs = D['nodes'], D['boxes'], D['outs']
D['edges'] = [e for e in D['edges'] if e['up'] != e['dn'] and e['L'] > 0.05]
edges = D['edges']
E = pickle.load(open(CACHE, 'rb'))[0]
rep = []
def say(*a):
    s = ' '.join(str(x) for x in a); rep.append(s); print(s)
L = lambda p: (p[0] - 561500, p[1] - 8658000)
inb = lambda p: -90 < p[0] < 110 and -125 < p[1] < 75
def dseg(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; n2 = dx * dx + dy * dy
    t = 0 if n2 == 0 else max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / n2))
    return math.hypot(q[0] - a[0] - t * dx, q[1] - a[1] - t * dy), t
def ang(a, b): return math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi
P = lambda n: nodes[n]['p']
for e in edges: e['P0'], e['P1'] = P(e['up']), P(e['dn'])       # ponto de montante / jusante
# ------------------------------------------------ 1. DN, material, declividade (rótulos)
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
    for lim, dn in ((0.035, 32), (0.06, 40), (0.09, 75), (0.125, 100), (0.175, 150), (0.225, 200), (0.275, 250), (0.35, 300)):
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
for it in range(6):     # rótulo vale para o trecho inteiro entre caixas (colineares contíguos)
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
say('trechos', len(edges), '| DN:', sorted(collections.Counter(e['DN'] for e in edges).items()), '| declividade de rótulo:', sum(e['sl_src'] == 'rótulo' for e in edges))
# ------------------------------------------------ 2. terreno de projeto
Zt = {}
for l in open(W + 'terreno_z.csv'):
    x, y, z = l.strip().split(';')
    if z != 'NaN': Zt[(float(x), float(y))] = float(z)
ZP = np.array(list(Zt.keys())); ZV = np.array(list(Zt.values()))
def zimp(p): return ZV[np.argmin((ZP[:, 0] - p[0]) ** 2 + (ZP[:, 1] - p[1]) ** 2)]
ref = [(b['p'], b['CT'], zimp(b['p'])) for b in boxes if b['CT']]
def ground(p):
    zi = zimp(p); r = min(ref, key=lambda r: math.dist(p, r[0]) + 40 * abs(zi - r[2])); return r[1] + (zi - r[2])
for n in nodes: n['g'] = n['box']['CT'] if n.get('box') and n['box'].get('CT') else ground(n['p'])
# ------------------------------------------------ 3. conexões verticais (círculo duplo) -> mergulho / pé de prumada
VF = [L(e[3]) for e in E if e[0] == 'CIRCLE' and e[1] == 'Simbolos' and e[4] >= 0.02 and inb(L(e[3]))]
VFa = np.array(VF)
def vf_near(p, r):
    d = np.hypot(VFa[:, 0] - p[0], VFa[:, 1] - p[1]); i = int(np.argmin(d)); return VF[i] if d[i] < r else None
used_vf = set()
for k, e in enumerate(edges):
    e['vf_dn'] = e['vf_up'] = None
    nb = nodes[e['dn']]
    A, B = (e['pa'], e['pb']) if e['up'] == e['u'] else (e['pb'], e['pa'])   # eixo DESENHADO (montante->jusante)
    e['A'], e['B'] = A, B
    if nb.get('box'):            # mergulho: círculo sobre o eixo do tubo, perto da caixa
        ux, uy = B[0] - A[0], B[1] - A[1]; Le = math.hypot(ux, uy); ux, uy = ux / Le, uy / Le
        best = None
        for q in VF:
            s = (q[0] - B[0]) * ux + (q[1] - B[1]) * uy          # <0: antes da ponta
            lat = abs(-(q[0] - B[0]) * uy + (q[1] - B[1]) * ux)
            if -2.2 < s < 0.35 and lat < 0.08 and (best is None or lat < best[0]): best = (lat, q)
        if best: e['vf_dn'] = best[1]; used_vf.add(best[1])
    if not nodes[e['up']].get('box') and not [j for j in inc[e['up']] if edges[j]['dn'] == e['up']]:
        q = vf_near(e['P0'], 0.6)                 # início de ramal com joelho (pé de prumada / subida de dreno)
        if q: e['vf_up'] = q; used_vf.add(q)
for n, nd in enumerate(nodes):                     # junção com conexão vertical (desnível permitido)
    nd['vf'] = (not nd.get('box')) and vf_near(nd['p'], 0.3) is not None and len(inc[n]) > 1
say('conexões verticais no desenho:', len(VF), '| mergulhos na chegada à caixa:', sum(e['vf_dn'] is not None for e in edges),
    '| pés de prumada/subidas no início de ramal:', sum(e['vf_up'] is not None for e in edges), '| junções com desnível:', sum(nd['vf'] for nd in nodes),
    '| sem tubo associado:', len(VF) - len(used_vf))
# ------------------------------------------------ 4. rótulos CE/CS por tubo (o mais próximo do texto)
def val(s):
    m = re.search(r'([\d.]+)', s.split(':')[-1]); return float(m.group(1)) if m else None
TQ = [e for e in E if e[0] == 'MTEXT' and e[1] == 'TQ-Textos conduto']
LAB = {k: [(L(e[3]), val(e[5])) for e in TQ if e[5].startswith(k)] for k in ('CE', 'CS')}
# cada rótulo pertence à caixa mais próxima do texto (antes: toda caixa a < 5 m pegava rótulos da vizinha)
CTl = [(L(e[3]), val(e[5])) for e in TQ if e[5].startswith('CT')]
def owner(q):
    b = min(boxes, key=lambda b: math.dist(q, b['p']))
    return b['n'] if math.dist(q, b['p']) < 5 else None
OWN = {k: [(q, v, owner(q)) for q, v in LAB[k]] for k in LAB}
bad_lab = []
for b in boxes:
    n = b['n']; top = b['CT'] or nodes[n]['g']
    for k, side in (('CE', 'dn'), ('CS', 'up')):
        pipes = [j for j in inc[n] if edges[j][side] == n]
        labs = [(q, v) for q, v, o in OWN[k] if o == n]
        good = [(q, v) for q, v in labs if v <= top - 0.15]
        bad_lab += [(b['id'], k, v, top) for q, v in labs if v > top - 0.15]
        pairs = sorted((dseg(q, edges[j]['pa'], edges[j]['pb'])[0], i, j) for i, (q, v) in enumerate(good) for j in pipes)
        li, pj = set(), set()
        for d, i, j in pairs:
            if i in li or j in pj or d > 3.0: continue
            li.add(i); pj.add(j); edges[j]['CE' if k == 'CE' else 'CS'] = good[i][1]
        b[k + '_sobra'] = [good[i][1] for i in range(len(good)) if i not in li]
say('rótulos CE/CS acima da tampa/terreno (descartados, relatório):', bad_lab)
say('tubos com CE própria:', sum('CE' in e for e in edges), '| com CS própria:', sum('CS' in e for e in edges))
# ------------------------------------------------ 5. mínimos quadrados com restrições de desigualdade (conjunto ativo)
COV = 0.30
NE = len(edges); eqs = []; ineq = []; ENTRY = {}
def EQ(c, r, w, tag): eqs.append((c, r, w, tag))
def GE(c, r, tag): ineq.append((c, r, tag))          # c·x >= r
def Lmain(e): return math.dist(e['P0'], e['vf_dn']) if e['vf_dn'] else math.dist(e['P0'], e['P1'])
for k, e in enumerate(edges):
    EQ({2 * k: 1, 2 * k + 1: -1}, e['sl'] * max(Lmain(e), 0.3), 10, 'decl')
    if 'CS' in e: EQ({2 * k: 1}, e['CS'], 100, 'CS')
    if 'CE' in e:
        if e['vf_dn']: GE({2 * k + 1: 1}, e['CE'], 'mergulho>=CE')
        else: EQ({2 * k + 1: 1}, e['CE'], 100, 'CE')
for b in boxes:
    n = b['n']; cf = b['CF']
    if cf is not None and b['CT'] is not None and cf > b['CT'] - 0.1: cf = None
    outs_ = [j for j in inc[n] if edges[j]['up'] == n]; ins_ = [j for j in inc[n] if edges[j]['dn'] == n]
    css = [edges[j]['CS'] for j in outs_ if 'CS' in edges[j]]
    cs_min = min(css) if css else None
    for j in outs_:
        if 'CS' in edges[j]: continue
        if cf is not None:
            if b['tipo'] == 'PV': EQ({2 * j: 1}, cf, 30, 'CF do PV')
            else: GE({2 * j: 1}, cf, 'saída>=CF da CA')
    for j in ins_:
        if 'CE' in edges[j]: continue
        lo = max([v for v in (cs_min, cf) if v is not None], default=None)
        if lo is not None: GE({2 * j + 1: 1}, lo, 'entrada>=saída/CF'); ENTRY[j] = lo
        for o in outs_: GE({2 * j + 1: 1, 2 * o: -1}, 0.0, 'entrada>=saída')
for n, nd in enumerate(nodes):
    if nd.get('box'): continue
    ins_ = [j for j in inc[n] if edges[j]['dn'] == n]; outs_ = [j for j in inc[n] if edges[j]['up'] == n]
    ends = [2 * j + 1 for j in ins_] + [2 * j for j in outs_]
    if nd['vf']:
        for i in ins_:
            for o in outs_: GE({2 * i + 1: 1, 2 * o: -1}, 0.0, 'junção c/ desnível')
    else:
        for v in ends[1:]: EQ({ends[0]: 1, v: -1}, 0.0, 30, 'continuidade')
    if not ins_:                                  # início de ramal: recobrimento mínimo (alvo suave)
        for o in outs_: EQ({2 * o: 1}, nd['g'] - COV - edges[o]['od'], 0.3, 'recobrimento')
COVMIN = 0.20
for k, e in enumerate(edges):      # recobrimento mínimo (geratriz superior <= terreno - 0,20) em ponta sem rótulo de cota
    # (nas pontas em caixa quem manda é a cota da caixa: CE/CS/CF do projeto)
    if not nodes[e['up']].get('box'): GE({2 * k: -1}, -(nodes[e['up']]['g'] - COVMIN - e['od']), 'recobrimento mín.')
    if not nodes[e['dn']].get('box'): GE({2 * k + 1: -1}, -(nodes[e['dn']]['g'] - COVMIN - e['od']), 'recobrimento mín.')
active = set(); disabled = set()
def solve():
    rows = eqs + [(ineq[i][0], ineq[i][1], 100, ineq[i][2]) for i in sorted(active - disabled)]
    A = np.zeros((len(rows), 2 * NE)); bv = np.zeros(len(rows))
    for r, (c, y, w, t) in enumerate(rows):
        for kk, v in c.items(): A[r, kk] += v * w
        bv[r] = y * w
    return np.linalg.lstsq(A, bv, rcond=None)[0]
# ramais (trechos ligados por nós que não são caixa): se o recobrimento mínimo obriga o tubo a subir,
# o recobrimento é que cede (terreno estimado x cotas do projeto) -> relatório
comp = list(range(NE))
def fc(a):
    while comp[a] != a: comp[a] = comp[comp[a]]; a = comp[a]
    return a
for n, nd in enumerate(nodes):
    if nd.get('box'): continue
    ks = inc[n]
    for k2 in ks[1:]: comp[fc(k2)] = fc(ks[0])
def gval(i, x):
    c, r, t = ineq[i]; return sum(v * x[kk] for kk, v in c.items()) - r
for rnd in range(15):
    for it in range(120):
        x = solve()
        viol = [i for i in range(len(ineq)) if i not in active and i not in disabled and gval(i, x) < -0.003]
        if viol: active |= set(viol); continue
        # restrição ativa que está "puxando para o lado errado" (solução quer ficar acima do limite): solta
        rel = sorted((gval(i, x), i) for i in active - disabled if gval(i, x) > 1e-7)
        if not rel: break
        active -= {i for v, i in rel[-max(1, len(rel) // 4):]}
    upk = [k for k in range(NE) if (x[2 * k] - x[2 * k + 1]) < -0.0005 * max(Lmain(edges[k]), 0.3) and Lmain(edges[k]) > 0.3]
    bad_c = {fc(k) for k in upk}
    rm = {i for i in active - disabled if ineq[i][2] == 'recobrimento mín.' and any(fc(kk // 2) in bad_c for kk in ineq[i][0])}
    if not rm: break
    disabled |= rm
cov_conf = set()
for i in disabled: cov_conf |= {kk // 2 for kk in ineq[i][0]}
say('conjunto ativo: rodadas', rnd + 1, '| desigualdades ativas', len(active - disabled), 'de', len(ineq),
    '| recobrimento mínimo liberado (conflito terreno x cota do projeto) em', len(cov_conf), 'trechos')
# ------------------------------------------------ 6. resultados
for k, e in enumerate(edges):
    e['zu'], e['zd'] = float(x[2 * k]), float(x[2 * k + 1])
    e['Lm'] = Lmain(e); e['i'] = (e['zu'] - e['zd']) / max(e['Lm'], 0.01)
    e['entry'] = e.get('CE', ENTRY.get(k))
    e['drop'] = (e['zd'] - e['entry']) if (e['vf_dn'] and e['entry'] is not None) else 0.0
    e['g_up'] = nodes[e['up']]['g']; e['g_dn'] = nodes[e['dn']]['g']
    e['cov_u'] = e['g_up'] - e['zu'] - e['od']; e['cov_d'] = e['g_dn'] - e['zd'] - e['od']
    e['riser'] = (e['g_up'] - e['zu']) if e['vf_up'] else 0.0
    e['cov_conflito'] = k in cov_conf
# ------------------------------------------------ 7. validação
lab = [e for e in edges if e['sl_src'] == 'rótulo' and e['Lm'] > 1]
dev = [e for e in lab if abs(e['i'] - e['sl']) > 0.0025]
up_ = [e for e in edges if e['i'] < -0.0005 and e['Lm'] > 0.5]
steep = [e for e in edges if e['i'] > 0.05 and e['Lm'] > 1]
flat = [e for e in edges if 0 <= e['i'] < 0.005 and e['Lm'] > 1]
cov = [e for e in edges if min(e['cov_u'], e['cov_d']) < 0.195]
a = np.array([e['i'] for e in edges if e['Lm'] > 1])
say('declividade (L>1 m): p5 %.2f%%  p50 %.2f%%  p95 %.2f%%' % tuple(np.percentile(a, [5, 50, 95]) * 100))
say('com rótulo de i:', len(lab), '| modelado = rótulo (±0,25 p.p.):', len(lab) - len(dev), '| diferente:', len(dev))
say('subindo:', len(up_), '| <0,5%:', len(flat), '| >5%:', len(steep), '| recobrimento <0,20 m:', len(cov))
dr = [e['drop'] for e in edges if e['drop'] > 0.005]
say('mergulhos com desnível > 5 mm:', len(dr), '| desnível p50 %.2f m  máx %.2f m' % (np.median(dr) if dr else 0, max(dr) if dr else 0))
rs = [e['riser'] for e in edges if e['vf_up']]
say('pés de prumada: trecho vertical até o terreno p50 %.2f m  máx %.2f m' % (np.median(rs), max(rs)))
def why(e):
    fix_u = 'CS' in e or (nodes[e['up']].get('box') and nodes[e['up']]['box']['tipo'] == 'PV')
    fix_d = 'CE' in e and not e['vf_dn']
    return 'cotas de caixa nas 2 pontas' if fix_u and fix_d else ('restrição de caixa/junção' )
for e in sorted(dev, key=lambda e: -abs(e['i'] - e['sl']))[:40]:
    say('   difere: DN%d L=%.1f rótulo %.2f%% modelado %.2f%% em (%.1f,%.1f) %s->%s | %s | CS=%s CE=%s' % (
        e['DN'], e['Lm'], e['sl'] * 100, e['i'] * 100, e['P0'][0], e['P0'][1], nodes[e['up']]['kind'], nodes[e['dn']]['kind'], why(e), e.get('CS'), e.get('CE')))
for e in sorted(up_, key=lambda e: e['i']):
    say('   SOBE: DN%d L=%.1f i=%.2f%% em (%.1f,%.1f) %s->%s CS=%s CE=%s' % (e['DN'], e['Lm'], e['i'] * 100, e['P0'][0], e['P0'][1], nodes[e['up']]['kind'], nodes[e['dn']]['kind'], e.get('CS'), e.get('CE')))
D['bad_lab'] = bad_lab
pickle.dump(D, open(W + 'v2_net.pkl', 'wb'))
open(W + 'v2c2_relatorio.txt', 'w', encoding='utf-8').write('\n'.join(rep))
