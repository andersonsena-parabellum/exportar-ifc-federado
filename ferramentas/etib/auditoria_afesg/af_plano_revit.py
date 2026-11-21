"""Plano de execução no Revit do renivelamento da AF (gera af_plano_revit.txt para o C#).
- Tubos totalmente na zona das bombas/reservatório: intactos.
- Grupos de tê/cotovelo com tocos (tocos de 0,3 m): movidos inteiros em Z (fitting + tocos).
- Demais tubos AF: apagados e recriados por trecho (af_renivel.json); conexões refeitas.
"""
import sys, json, math, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from common import pipes, D

ZONA = lambda p: 91.5 < p[0] < 99.5 and 2.0 < p[1] < 14.0
P = {p['id']: p for p in pipes('Água fria')}
J = json.load(open(D + 'af_renivel.json'))
legs = J['legs']; tz = {t['id']: t['z'] for t in J['tocos']}

# topologia do Revit
sec = None; FIT = []; DIRECT = set(); OUT = []
for l in open(D + 'af_topologia_revit.txt', encoding='utf-8-sig'):
    l = l.rstrip('\n')
    if l.startswith('#'): sec = l.split()[0]; continue
    if sec == '#FITTINGS':
        fid, nome, sym, cs = l.split('|')
        con = []
        for c in cs.split(';'):
            pid, xyz = c.split('@'); con.append((pid, tuple(map(float, xyz.split(',')))))
        FIT.append(dict(id=fid, nome=nome, con=con))
    elif sec == '#DIRECT':
        a, b = l.split('-'); DIRECT.add(frozenset((a, b)))
    elif sec == '#OUTROS':
        OUT.append(l.split('|'))

zona_ids = {i for i, p in P.items() if ZONA(p['a']) and ZONA(p['b'])}
toco_ids = {i for i in tz}
recriar = [i for i in P if i not in zona_ids and i not in toco_ids]
# grupos de tocos fora da zona: fitting + tocos, com dz
grupos = []
for f in FIT:
    ps = [c[0] for c in f['con'] if c[0] != '-']
    if ps and all(p in toco_ids for p in ps) and not ZONA(f['con'][0][1]):
        zold = P[ps[0]]['a'][2]; znew = tz[ps[0]]
        grupos.append(dict(fit=[f['id']], tocos=ps, dz=znew - zold, xy=f['con'][0][1][:2]))
# a bucha 443851 fica ligada ao tê 443846 (conector '-'): entra no mesmo grupo
for f in FIT:
    ps = [c[0] for c in f['con'] if c[0] != '-']
    if len(ps) == 1 and ps[0] in toco_ids and any(c[0] == '-' for c in f['con']):
        for g in grupos:
            if ps[0] in g['tocos'] or math.dist(g['xy'], f['con'][0][1][:2]) < 0.2:
                if f['id'] not in g['fit']: g['fit'].append(f['id'])
                if ps[0] not in g['tocos']: g['tocos'].append(ps[0])
# remove grupo contido em outro (bucha ligada ao tê) e usa o menor dz do conjunto (mais fundo = recobrimento garantido)
grupos = [g for g in grupos if not any(h is not g and set(g['fit']) < set(h['fit']) for h in grupos)]
for g in grupos: g['dz'] = min(tz[t] - P[t]['a'][2] for t in g['tocos'])
dz_toco = {t: g['dz'] for g in grupos for t in g['tocos']}
# conferência: tocos dos grupos devem estar na lista
print('grupos de tocos a mover:', len(grupos), [(g['fit'], g['tocos'], round(g['dz'], 3)) for g in grupos])
print('tocos fora de grupo:', [t for t in toco_ids if t not in dz_toco and not (ZONA(P[t]['a']))])

# trechos novos, numerados
NL = []
porig = collections.defaultdict(list)
for L in legs:
    if L['orig'] in zona_ids: continue
    porig[L['orig']].append(L)
for o, ls in porig.items():
    for k, L in enumerate(ls):
        NL.append(dict(key=f'{o}_{k}', orig=o, k=k, n=len(ls), dn=L['dn'], a=(L['a'][0], L['a'][1], L['za']), b=(L['b'][0], L['b'][1], L['zb']),
                       cov_min=L['cov_min'], cov_req=L['cov_req'], ta=L['terr_a'], tb=L['terr_b']))
# ponto de ligação: cada ponta de trecho novo -> alvo
def ends():
    for L in NL:
        yield L, 0, L['a']
        yield L, 1, L['b']
fit_of = {}  # par de tubos originais -> fitting
for f in FIT:
    ps = [c[0] for c in f['con'] if c[0] != '-']
    if len(ps) == 2: fit_of[frozenset(ps)] = f['nome']
JOIN = []; usados = set()
# 1) entre trechos do mesmo tubo original
for o, ls in porig.items():
    for k in range(len(ls) - 1):
        JOIN.append(('direto', f'{o}_{k}', 1, f'{o}_{k+1}', 0, 'quebra do perfil'))
# 2) entre tubos originais diferentes (cotovelo/bucha/direto) e com tocos/tubos da zona
for L, e, p in ends():
    if (L['k'] != 0 and e == 0) or (L['k'] != L['n'] - 1 and e == 1): continue
    for M, f, q in ends():
        if M is L or M['orig'] == L['orig']: continue
        if (M['k'] != 0 and f == 0) or (M['k'] != M['n'] - 1 and f == 1): continue
        if math.dist(p[:2], q[:2]) < 0.07:
            par = frozenset((L['orig'], M['orig'])); kk = frozenset(((L['key'], e), (M['key'], f)))
            if kk in usados: continue
            usados.add(kk)
            nome = fit_of.get(par)
            tipo = 'direto' if par in DIRECT else ('bucha' if nome and 'Bucha' in nome else ('cotovelo' if nome else 'direto?'))
            JOIN.append((tipo, L['key'], e, M['key'], f, nome or ''))
    # tocos e tubos da zona (existentes)
    for t in list(dz_toco) + [i for i in zona_ids]:
        for f, q in ((0, P[t]['a']), (1, P[t]['b'])):
            if math.dist(p[:2], q[:2]) < 0.07 and frozenset((L['orig'], t)) in DIRECT:
                JOIN.append(('existente', L['key'], e, t, f, 'toco' if t in dz_toco else 'zona'))
byk = {L['key']: L for L in NL}
for j in JOIN:
    if j[0] == 'existente':
        t = j[3]; q = P[t]['a'] if j[4] == 0 else P[t]['b']; zt = q[2] + dz_toco.get(t, 0.0)
        L = byk[j[1]]; old = L['a'] if j[2] == 0 else L['b']
        if abs(old[2] - zt) > 0.001: print('  ajuste ponta', j[1], j[2], 'de %.3f para %.3f' % (old[2], zt))
        if j[2] == 0: L['a'] = (old[0], old[1], zt)
        else: L['b'] = (old[0], old[1], zt)
cnt = collections.Counter(j[0] for j in JOIN)
print('trechos a criar:', len(NL), '| tubos a apagar:', len(recriar), '| ligações:', dict(cnt))
for j in JOIN:
    if j[0] == 'direto?': print('  ATENÇÃO sem fitting nem ligação direta original:', j)
# pontas livres esperadas
lig = collections.Counter()
for j in JOIN:
    lig[(j[1], j[2])] += 1
    if j[0] != 'existente': lig[(j[3], j[4])] += 1
livres = [(L['key'], e) for L in NL for e in (0, 1) if lig[(L['key'], e)] == 0]
print('pontas livres previstas:', livres)
# fittings a apagar (fora da zona e fora dos grupos)
fit_del = [f['id'] for f in FIT if not any(f['id'] in g['fit'] for g in grupos) and not ZONA(f['con'][0][1])]
print('fittings a apagar (serão refeitos):', fit_del)

# DirectShapes AF: registro -> eixo do tubo no ponto; alçapão -> topo no terreno; abrigo -> base no terreno
import csv
S = []
for r in csv.DictReader(open(D + 'af_amostras_z.csv'), delimiter=';'): S.append((float(r['x']), float(r['y']), float(r['zt'])))
def terr(x, y): return min(S, key=lambda s: (s[0] - x) ** 2 + (s[1] - y) ** 2)[2]
def zeixo(x, y):
    best = None
    for L in NL:
        a, b = L['a'], L['b']; dx, dy = b[0] - a[0], b[1] - a[1]; n = dx * dx + dy * dy
        t = 0 if n == 0 else max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / n))
        d = math.hypot(a[0] + t * dx - x, a[1] + t * dy - y)
        if best is None or d < best[0]: best = (d, a[2] + (b[2] - a[2]) * t)
    for t, dz in dz_toco.items():
        p = P[t]; d = min(math.dist((x, y), p['a'][:2]), math.dist((x, y), p['b'][:2]))
        if d < best[0]: best = (d, p['a'][2] + dz)
    return best
MOV = []
for o in OUT:
    if o[3] != 'DirectShape' or o[1] == 'Equipamento mecânico': continue
    x, y, z0, z1 = map(float, o[4].split(','))
    if 'Registro' in o[2]:
        d, ze = zeixo(x, y); MOV.append((o[0], o[2], round(ze - (z0 + z1) / 2, 4), f'eixo {ze:.3f} (tubo a {d:.2f} m)'))
    elif 'Alçapão' in o[2]:
        t = terr(x, y); MOV.append((o[0], o[2], round(t - z1, 4), f'topo no terreno {t:.3f}'))
    elif 'hidrômetro' in o[2]:
        t = terr(x, y); MOV.append((o[0], o[2], round(t - z0, 4), f'base no terreno {t:.3f}'))
for m in MOV: print('  mover', m)

FT = 1 / 0.3048
with open(D + 'af_plano_revit.txt', 'w', encoding='utf-8') as f:
    f.write('#APAGAR_TUBOS\n' + '\n'.join(recriar) + '\n')
    f.write('#APAGAR_FITTINGS\n' + '\n'.join(fit_del) + '\n')
    f.write('#MOVER_GRUPOS fits|tocos|dz_m\n')
    for g in grupos: f.write(','.join(g['fit']) + '|' + ','.join(g['tocos']) + '|' + f"{g['dz']:.4f}\n")
    f.write('#MOVER_DS id|dz_m\n')
    for m in MOV: f.write(f'{m[0]}|{m[2]:.4f}\n')
    f.write('#TRECHOS key|orig|k|n|ax|ay|az|bx|by|bz|recMin|recReq|ta|tb\n')
    for L in NL:
        topo_a = L['a'][2] + L['dn'] / 2000; topo_b = L['b'][2] + L['dn'] / 2000
        f.write('|'.join([L['key'], L['orig'], str(L['k']), str(L['n'])] + [f'{v:.4f}' for v in (*L['a'], *L['b'])] +
                         [f"{L['cov_min']:.4f}", f"{L['cov_req']:.4f}", f"{topo_a:.4f}", f"{topo_b:.4f}", f"{L['ta']:.4f}", f"{L['tb']:.4f}"]) + '\n')
    f.write('#LIGACOES tipo|keyA|endA|keyB|endB\n')
    for j in JOIN: f.write('|'.join(map(str, j[:5])) + '\n')
print('plano gravado')
