"""Renivelamento da AF sobre o terreno "as built" (IMP), mantendo o traçado em planta.
Premissa de modelagem (o projeto AF não tem cotas): topo do tubo = terreno - recobrimento
(0,30 m; 0,60 m dentro da área de veículos V1). Mesmo método do incêndio (elev.py):
Douglas-Peucker com desvio 0,20 m e trecho mínimo 2 m; iteração até nenhum ponto ficar raso.
Tocos de tê (0,3 m, horizontais) ficam na mesma cota do centro do tê.
Saída: af_renivel.json (trechos novos) + af_renivel_resumo.csv
"""
import sys, json, csv, math, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from common import pipes, D
import numpy as np

V1 = [(-22, 33), (17, 33), (18, 36.6), (86.5, 46.3), (87.2, 47.5), (92, 70), (-22, 70)]
EPS, MINL, TOL = 0.20, 2.0, 0.06
ZONA = lambda p: 91.5 < p[0] < 99.5 and 2.0 < p[1] < 14.0   # bombas/reservatório: cotas atuais (decisão 14/10)

def inpoly(p, poly):
    x, y = p; c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def cover(p): return 0.60 if inpoly(p, V1) else 0.30

P = pipes('Água fria')
S = collections.defaultdict(list)
for r in csv.DictReader(open(D + 'af_amostras_z.csv'), delimiter=';'):
    S[r['id']].append((float(r['s']), float(r['x']), float(r['y']), float(r['zt'])))
for k in S: S[k].sort()

# --- nós (pontas agrupadas) e união pelos tocos horizontais
pts = []
def node(p):
    for i, q in enumerate(pts):
        if math.dist(p[:2], q[:2]) < TOL and abs(p[2] - q[2]) < 0.05: return i
    pts.append(p); return len(pts) - 1
par = {}
def find(i):
    while par.setdefault(i, i) != i: i = par[i]
    return i
def union(a, b): par[find(a)] = find(b)
for p in P:
    p['na'], p['nb'] = node(p['a']), node(p['b'])
    p['Lh'] = math.dist(p['a'][:2], p['b'][:2])
    p['toco'] = p['Lh'] < 0.45 and abs(p['b'][2] - p['a'][2]) < 0.005
    if p['toco']: union(p['na'], p['nb'])
# centros de tê: pontas de tocos que se tocam (0,04 m) -> mesmo grupo
for i in range(len(pts)):
    for j in range(i + 1, len(pts)):
        if math.dist(pts[i][:2], pts[j][:2]) < 0.06: union(i, j)
FIX = {}
for i, q in enumerate(pts):
    if ZONA(q): FIX[('N', find(i))] = q[2]
grau = collections.Counter()
for p in P: grau[find(p['na'])] += 1; grau[find(p['nb'])] += 1

def zreq_sample(s, de): return s[3] - cover((s[1], s[2])) - de / 2000.0

def dp(s, z, i0, i1, out):
    if i1 <= i0 + 1: return
    line = z[i0] + (z[i1] - z[i0]) * (s[i0 + 1:i1] - s[i0]) / (s[i1] - s[i0])
    dev = np.abs(z[i0 + 1:i1] - line); k = int(np.argmax(dev)) + i0 + 1
    if dev.max() > EPS and s[k] - s[i0] >= MINL and s[i1] - s[k] >= MINL:
        dp(s, z, i0, k, out); out.append(k); dp(s, z, k, i1, out)

# --- trechos (legs): cada tubo principal vira 1+ trechos retos
Z = {}      # variável de cota (eixo) por chave
legs = []
for p in P:
    if p['toco']: continue
    sm = S[p['id']]
    s = np.array([q[0] for q in sm]); z = np.array([zreq_sample(q, p['dn']) for q in sm])
    ks = []
    if not (ZONA(p['a']) and ZONA(p['b'])): dp(s, z, 0, len(s) - 1, ks)
    idx = [0] + sorted(ks) + [len(s) - 1]
    keys = []
    for j, i in enumerate(idx):
        if i == 0: keys.append(('N', find(p['na'])))
        elif i == len(s) - 1: keys.append(('N', find(p['nb'])))
        else: keys.append(('I', p['id'], i))
    for (i0, i1), (ka, kb) in zip(zip(idx, idx[1:]), zip(keys, keys[1:])):
        legs.append(dict(orig=p['id'], dn=p['dn'], sis=p['sis'], ka=ka, kb=kb, smp=sm[i0:i1 + 1],
                         a=(sm[i0][1], sm[i0][2]), b=(sm[i1][1], sm[i1][2])))
        for k, smp in ((ka, sm[i0]), (kb, sm[i1])):
            Z[k] = min(Z.get(k, 1e9), zreq_sample(smp, p['dn']))
for k, v in FIX.items(): Z[k] = v
bloq = []
# --- iteração: baixa a ponta até nenhum ponto do trecho ficar raso
for it in range(500):
    ch = False
    for L in legs:
        za, zb = Z[L['ka']], Z[L['kb']]; sm = L['smp']; s0, s1 = sm[0][0], sm[-1][0]
        viol, tv = 0, 0
        for q in sm:
            t = 0 if s1 == s0 else (q[0] - s0) / (s1 - s0)
            v = (za + (zb - za) * t) - zreq_sample(q, L['dn'])
            if v > viol: viol, tv = v, t
        if viol > 1e-4:
            fa, fb = L['ka'] in FIX, L['kb'] in FIX
            if fa and fb: bloq.append(L['orig']); continue
            if (tv < 0.5 and not fa) or fb: Z[L['ka']] -= viol / max(1 - tv, 1e-6)
            else: Z[L['kb']] -= viol / max(tv, 1e-6)
            ch = True
    if not ch: break
# --- resultado
old = {p['id']: p for p in P}
res = []
for L in legs:
    za, zb = Z[L['ka']], Z[L['kb']]; sm = L['smp']; s0, s1 = sm[0][0], sm[-1][0]
    cov = [q[3] - ((za + (zb - za) * ((q[0] - s0) / (s1 - s0) if s1 > s0 else 0)) + L['dn'] / 2000) for q in sm]
    o = old[L['orig']]
    res.append(dict(orig=L['orig'], sis=L['sis'], dn=L['dn'], a=L['a'], b=L['b'], za=za, zb=zb,
                    comp=math.dist(L['a'], L['b']), cov_min=min(cov), cov_max=max(cov),
                    cov_req=cover(L['a']), terr_a=sm[0][3], terr_b=sm[-1][3]))
z_tee = {k: v for k, v in Z.items() if k[0] == 'N'}
json.dump(dict(legs=res, tocos=[dict(id=p['id'], z=Z.get(('N', find(p['na'])))) for p in P if p['toco']]),
          open(D + 'af_renivel.json', 'w'), indent=0, default=str)
# comparação antiga x nova (cota do eixo nas pontas dos tubos originais)
with open(D + 'af_renivel_resumo.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['tubo_original', 'sistema', 'DN', 'trechos_novos', 'comp_m', 'z_eixo_ini_antigo', 'z_eixo_ini_novo', 'z_eixo_fim_antigo', 'z_eixo_fim_novo', 'recobr_min', 'recobr_max', 'recobr_exigido'])
    for pid, p in old.items():
        if p['toco']: continue
        ls = [r for r in res if r['orig'] == pid]
        w.writerow([pid, p['sis'], int(p['dn']), len(ls), f"{p['Lh']:.1f}", f"{p['a'][2]:.2f}", f"{ls[0]['za']:.2f}", f"{p['b'][2]:.2f}", f"{ls[-1]['zb']:.2f}",
                    f"{min(r['cov_min'] for r in ls):.2f}", f"{max(r['cov_max'] for r in ls):.2f}", f"{ls[0]['cov_req']:.2f}"])
print('iterações', it, '| tubos principais', sum(1 for p in P if not p['toco']), '-> trechos', len(res), '| tocos', sum(1 for p in P if p['toco']))
print('recobrimento: mín %.2f  máx %.2f' % (min(r['cov_min'] for r in res), max(r['cov_max'] for r in res)))
print('trechos com recobrimento máx > 1,00 m:', sum(1 for r in res if r['cov_max'] > 1.0), '| > 1,50 m:', sum(1 for r in res if r['cov_max'] > 1.5))
dz = [abs(Z[k] - pts[k[1]][2]) for k in Z if k[0] == 'N']
print('mudança de cota nos nós: média %.2f m, máx %.2f m' % (sum(dz) / len(dz), max(dz)))
print('nós fixos (bombas/reservatório):', len(FIX), '| trechos entre fixos com recobrimento < exigido:', sorted(set(bloq)))
print('trechos na área de veículos V1:', sum(1 for r in res if r['cov_req'] == 0.6))
