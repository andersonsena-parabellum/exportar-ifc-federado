"""Auditoria da fase 4: lê o que foi criado no Revit (work/revit_leitura_fase4.tsv) e confere
1) contagem e comprimento por rede e Ø; 2) geometria Revit x entrada (pontas, Ø nominal, DE); 3) recobrimento refeito sobre o
terreno as built (amostras do Toposolid do IMP); 4) DWG x modelo (desvio em planta e extensão do DWG não modelada);
5) caixas (CT x terreno, profundidade); 6) duplicatas e sobreposição entre eletrodutos.
Saída: RELATORIOS/ELE_fase4_auditoria_trechos_2026-10-15.csv e resumo no terminal."""
import csv, json, math, collections
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
R = 'D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/'
DE = {'3/4': 26.7, '1': 33.4, '1.1/4': 42.2, '1.1/2': 48.3, '2': 60.3, '3': 88.9, '4': 114.3, '6': 168.3}
NOM = {0.827: '3/4', 1.063: '1', 1.378: '1.1/4', 1.614: '1.1/2', 2.087: '2', 3.071: '3', 4.055: '4', 6.102: '6'}
C, X = [], []
for l in open(W + 'revit_leitura_fase4.tsv', encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if r[0] == 'C': C.append(dict(id=r[1], tipo=r[2], trecho=r[3], nom=float(r[4]), de=float(r[5]), a=np.array(list(map(float, r[6:9]))), b=np.array(list(map(float, r[9:12]))),
                                  disc=r[12], cmin=float(r[13]), creq=float(r[14]), orig=r[17]))
    else: X.append(dict(id=r[1], nome=r[2], trecho=r[3], c=(float(r[4]), float(r[5])), z0=float(r[6]), z1=float(r[7]), ct=float(r[8]), cf=float(r[9]), prof=float(r[10])))
# entrada
ENT = {}
for l in open(W + 'revit_conduits.tsv', encoding='utf-8'):
    c = l.rstrip('\n').split('\t'); ENT[c[1] + '.' + c[2]] = c
# terreno: amostras (x, y, zt)
T = np.array([[float(r['x']), float(r['y']), float(r['zt'])] for r in csv.DictReader(open(W + 'amostras_z.csv'), delimiter=';')])
def terreno(p):
    d = np.hypot(T[:, 0] - p[0], T[:, 1] - p[1]); k = int(np.argmin(d)); return T[k, 2], d[k]
from shapely.geometry import Polygon
V1 = Polygon([(-22, 33), (17, 33), (18, 36.6), (86.5, 46.3), (87.2, 47.5), (92, 70), (-22, 70)])
# perfil do terreno de cada pedaço (as mesmas amostras da fase 3, por abscissa ao longo do traçado do DWG)
PECA, PERF = {}, collections.defaultdict(list)
for t in ['EL1', 'EL2', 'CF1', 'CF2']:
    for i, p in enumerate(json.load(open(W + f'cotas_{t}.json'))['pieces']): PECA[(t, i)] = LineString(p['pts'])
for r in csv.DictReader(open(W + 'amostras_z.csv'), delimiter=';'):
    if not r['peca'].startswith('CX'): PERF[(r['tag'], int(r['peca']))].append((float(r['s']), float(r['zt'])))
for k in PERF: PERF[k].sort()
def terreno_peca(tag, i, p):
    s = PECA[(tag, i)].project(Point(p[0], p[1])); ss = [q[0] for q in PERF[(tag, i)]]; zz = [q[1] for q in PERF[(tag, i)]]
    return float(np.interp(s, ss, zz))
# DWG
RUN = {t: [LineString(r['pts']) for r in json.load(open(W + f'rede_{t}.json'))['runs']] for t in ['EL1', 'EL2', 'CF1', 'CF2']}
out = []; tot = collections.defaultdict(float); porø = collections.defaultdict(float); n = collections.Counter()
erros = collections.Counter(); desv_planta = collections.defaultdict(float); cov_ruim = []
for c in C:
    tag = c['trecho'][:3]; e = ENT.get(c['trecho'])
    L = float(np.linalg.norm(c['b'][:2] - c['a'][:2])); tot[tag] += L; n[tag] += 1
    pol = NOM.get(round(c['nom'], 3), '?'); porø[(tag, pol)] += L
    # 2) geometria x entrada
    dp = max(np.linalg.norm(c['a'] - np.array(list(map(float, e[5:8])))), np.linalg.norm(c['b'] - np.array(list(map(float, e[8:11])))))
    if dp > 0.001: erros['ponta Revit x entrada > 1 mm'] += 1
    if abs(c['nom'] - float(e[4]) * 12) > 0.001: erros['Ø nominal diferente'] += 1
    if abs(c['de'] - DE.get(pol, 0)) > 0.2: erros['DE diferente do RNC 40'] += 1
    if c['orig'] == 'SEM': erros['sem COMP_Origem'] += 1
    # 3) recobrimento a cada 0,25 m
    k = max(2, int(math.ceil(L / 0.25)) + 1); cmin, zt_a, zt_b = 9, None, None
    ip = int(c['trecho'][4:7]); folga = 9   # folga = recobrimento - exigido no ponto (exigido por ponto: 1,00 só dentro da área de veículos V1)
    for u in np.linspace(0, 1, k):
        p = c['a'] + u * (c['b'] - c['a']); zt = terreno_peca(tag, ip, p)
        cv = zt - (p[2] + c['de'] / 2000); cmin = min(cmin, cv)
        req = (1.00 if V1.contains(Point(p[0], p[1])) else 0.70) if tag.startswith('EL') else 0.60
        folga = min(folga, cv - req)
    if folga < -0.01: cov_ruim.append((c['trecho'], round(cmin, 3), round(folga, 3)))
    # 4) desvio em planta x DWG
    ls = LineString([c['a'][:2], c['b'][:2]])
    dmax = max(min(r.distance(ls.interpolate(u, normalized=True)) for r in RUN[tag]) for u in np.linspace(0, 1, max(2, int(L / 0.5) + 1)))
    desv_planta[tag] = max(desv_planta[tag], dmax)
    out.append([tag, c['trecho'], c['id'], pol + '"', f"{c['de']:.1f}", f'{L:.2f}', f"{c['a'][2] + c['de'] / 2000:.3f}", f"{c['b'][2] + c['de'] / 2000:.3f}",
                f"{c['creq']:.2f}", f'{cmin:.3f}', f"{c['cmin']:.3f}", f'{dmax:.3f}', 'OK' if folga >= -0.01 else 'RECOBRIMENTO INSUFICIENTE', e[22], e[23], e[21]])
# duplicatas
seen = collections.Counter(tuple(np.round(np.concatenate([c['a'], c['b']]), 3)) for c in C)
dups = sum(v - 1 for v in seen.values() if v > 1)
# DWG não modelado (fora de blocos e de caixas)
cobre = {t: unary_union([LineString([c['a'][:2], c['b'][:2]]).buffer(0.15) for c in C if c['trecho'].startswith(t)]) for t in RUN}
blocos = unary_union([__import__('shapely.geometry', fromlist=['Polygon']).Polygon(o['coords']) for o in json.load(open(W + 'blocos.json'))])
cx = unary_union([Point(x['c']).buffer(0.75) for x in X])
nao = {}
for t, rs in RUN.items():
    U = unary_union(rs).difference(cobre[t]); nao[t] = (U.length, U.difference(blocos).difference(cx).length)
# caixas
cx_err = []
for x in X:
    zt, dd = terreno(x['c'])
    if abs(x['z1'] - x['ct']) > 0.002 or abs(x['z0'] - x['cf']) > 0.002: cx_err.append((x['trecho'], 'geometria ≠ CT/CF'))
with open(R + 'ELE_fase4_auditoria_trechos_2026-10-15.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['rede', 'trecho.segmento', 'id Revit', 'Ø', 'DE_mm', 'comp_m', 'topo_início', 'topo_fim', 'recobr_exigido', 'recobr_mín_lido_Revit', 'COMP_Recobrimento Mín', 'desvio_planta_DWG_m', 'situação', 'de', 'até', 'observação'])
    w.writerows(out)
print('== Revit:', len(C), 'eletrodutos,', len(X), 'caixas | duplicatas', dups)
for t in ['EL1', 'EL2', 'CF1', 'CF2']:
    nb = sum(1 for x in X if x['trecho'].startswith(t))
    print(f"{t}: {n[t]} eletrodutos {tot[t]:.1f} m | caixas {nb} | desvio máx. em planta x DWG {desv_planta[t]:.3f} m | DWG sem modelo {nao[t][0]:.1f} m (fora de blocos e caixas: {nao[t][1]:.1f} m)")
    print('   por Ø:', {k[1]: round(v, 1) for k, v in sorted(porø.items()) if k[0] == t})
print('erros de conferência:', dict(erros) or 'nenhum')
print('recobrimento abaixo do exigido (lido do Revit):', len(cov_ruim), cov_ruim[:10])
cm = collections.defaultdict(lambda: 9)
for r in out: cm[r[0]] = min(cm[r[0]], float(r[9]))
print('recobrimento mín. lido por rede:', {k: round(v, 3) for k, v in cm.items()})
print('caixas com problema:', cx_err or 'nenhuma', '| prof. caixas', round(min(x['prof'] for x in X), 2), '–', round(max(x['prof'] for x in X), 2))
json.dump(dict(nao_modelado={t: v for t, v in nao.items()}), open(W + 'auditoria_resumo.json', 'w'))

# 7) chegada nas caixas, lida do Revit: a ponta de cada eletroduto que termina em caixa tem de estar na face dela
from shapely.geometry import Polygon as _P
CXP = {}
for l in open(W + 'revit_caixas.tsv', encoding='utf-8'):
    c = l.rstrip(chr(10)).split(chr(9)); cx, cy, h, a = float(c[2]), float(c[3]), float(c[4]) / 200, float(c[6])
    CXP[c[1]] = _P([(cx + h * (math.cos(a) * u - math.sin(a) * v), cy + h * (math.sin(a) * u + math.cos(a) * v)) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
por_trecho = collections.defaultdict(list)
for c in C: por_trecho[c['trecho'].rsplit('.', 1)[0]].append((int(c['trecho'].rsplit('.', 1)[1]), c))
fora = []; nchk = 0
for tr, L in por_trecho.items():
    L.sort(key=lambda x: x[0]); e = ENT[L[0][1]['trecho']]
    for lado, P in ((e[22], L[0][1]['a']), (e[23], L[-1][1]['b'])):
        if not lado.startswith('caixa'): continue
        nchk += 1; d = CXP[lado.split()[1]].exterior.distance(Point(P[0], P[1]))
        if d > 0.01: fora.append((tr, lado, round(d, 3)))
print('chegada nas caixas (lida do Revit):', nchk, 'pontas em caixa |', len(fora), 'fora da face', fora[:10])
