"""v2 -> CSVs para o Revit (substituição da rede). Saída: work/v2_boxes.csv, work/v2_pipes.csv
Coordenadas internas (m); cotas absolutas (m)."""
import sys, math, pickle, collections, csv
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
D = pickle.load(open(W + 'v2_net.pkl', 'rb'))
nodes, edges, boxes = D['nodes'], D['edges'], D['boxes']
# ---- lajes dos blocos (interno = dentro da projeção, como no reclass de 13/10)
fl = collections.defaultdict(list)
for l in open(W + 'floors.csv', encoding='utf-8-sig'):
    c = l.strip().split(';')
    if c[0].startswith('IMP'): continue
    fl[(c[0], c[1])].append(tuple(map(float, c[2:6])))
def inside(x, y):
    for segs in fl.values():
        n = 0
        for x1, y1, x2, y2 in segs:
            if (y1 > y) != (y2 > y) and x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x: n += 1
        if n % 2: return True
    return False
# ---- tamanhos de caixa do modelo antigo (desenho do DWG)
old = []
for r in csv.reader(open(W + 'revit_boxes.csv'), delimiter=';'):
    if r[0] != 'PV': old.append((float(r[2]), float(r[3]), max(float(r[4]), float(r[5]))))
rot = math.radians(8.06)
def box_size(p):
    c = [o for o in old if math.dist(p, o[:2]) < 0.5]
    if not c: return 0.60, 'tamanho 0,60 adotado (legenda: 60x60 ou 80x80)'
    raw = c[0][2] / (math.cos(rot) + math.sin(rot))
    return min((0.6, 0.8, 1.0, 1.2), key=lambda v: abs(v - raw)), 'tamanho medido no DWG'
inc = collections.defaultdict(list)
for k, e in enumerate(edges):
    if e['up'] != e['dn'] and e['L'] > 0.05: inc[e['up']].append(k); inc[e['dn']].append(k)
# ---- caixas
brows = []
for n, nd in enumerate(nodes):
    b = nd.get('box')
    if not b: continue
    inv = [edges[k]['zu'] if edges[k]['up'] == n else edges[k]['zd'] for k in inc[n]]
    ct = b['CT'] if b['CT'] else nd['g']; obs = []
    if not b['CT']: obs.append('CT = terreno de projeto estimado (sem rótulo)')
    cf = b['CF']
    if cf is not None and cf > ct - 0.1: obs.append('CF do rótulo (%.2f) incoerente com CT - desconsiderada' % cf); cf = None
    if cf is None:
        cf = (min(inv) - 0.10) if inv else ct - 0.60
        obs.append('CF INFERIDA (geratriz inferior - 0,10 m)' if inv else 'CF INFERIDA (profundidade 0,60 adotada)')
    else:
        obs.append('CT/CF do projeto' if b['CT'] else 'CF do projeto')
        if inv and cf > min(inv) + 0.02: obs.append('CF do projeto ACIMA da geratriz do tubo (%.2f) - registrar no relatório' % min(inv))
    if b.get('rot_incoerente'): obs.insert(0, 'RÓTULO CE/CS %s ACIMA DO TERRENO - descartado; registrar no relatório' % '/'.join('%.2f' % v for v in b['rot_incoerente']))
    if not inc[n]: obs.insert(0, 'CAIXA SEM TUBULAÇÃO NO PROJETO R04 - registrar no relatório')
    if b['tipo'] == 'PV': sz, so = 1.10, 'PV Ø1,10 m'
    else: sz, so = box_size(nd['p'])
    obs.append(so)
    brows.append([b['tipo'], b['id'], '%.4f' % nd['p'][0], '%.4f' % nd['p'][1], '%.3f' % ct, '%.3f' % cf, '%.2f' % sz,
                  'ISO' if not inc[n] else '', ' | '.join(obs).replace(';', ',')])
# ---- tubos
order = sorted([k for k in range(len(edges)) if k in set(sum(inc.values(), []))],
               key=lambda k: (round(-nodes[edges[k]['up']]['p'][1] / 20), nodes[edges[k]['up']]['p'][0]))
prow = []; nint = 0
for j, k in enumerate(order):
    e = edges[k]; pu, pd = nodes[e['up']]['p'], nodes[e['dn']]['p']
    mid = ((pu[0] + pd[0]) / 2, (pu[1] + pd[1]) / 2)
    sysc = 'INT' if (e['DN'] <= 150 and inside(*pu) and inside(*pd) and inside(*mid)) else 'AP'
    nint += sysc == 'INT'
    L = math.dist(pu, pd); i = (e['zu'] - e['zd']) / max(L, 0.01)
    obs = []
    if e['dirsrc'] != 'seta': obs.append('sentido deduzido pela rede (sem seta no DWG)')
    obs.append('declividade do rótulo' if e['sl_src'] == 'rótulo' else 'declividade padrão 1% adotada (sem rótulo)')
    if i < -0.001 and L > 1: obs.insert(0, 'TRECHO SUBINDO (cotas do projeto) - registrar no relatório')
    elif i > 0.05 and L > 1: obs.insert(0, 'DECLIVIDADE > 5% (degrau entre cotas do projeto) - registrar no relatório')
    cov = min(e['cov_u'], e['cov_d'])
    if cov < 0.20: obs.insert(0, 'RECOBRIMENTO < 0,20 m - registrar no relatório')
    od = e['od']
    prow.append([j + 1, 'DRN-%03d' % (j + 1), e['DN'], e['mat'], sysc,
                 '%.4f' % pu[0], '%.4f' % pu[1], '%.4f' % (e['zu'] + od / 2), '%.4f' % pd[0], '%.4f' % pd[1], '%.4f' % (e['zd'] + od / 2),
                 '%.4f' % e['zu'], '%.4f' % e['zd'], '%.3f' % (i * 100), '%.3f' % nodes[e['up']]['g'], '%.3f' % nodes[e['dn']]['g'],
                 '%.3f' % cov, e['up'], e['dn'], ' | '.join(obs).replace(';', ',')])
csv.writer(open(W + 'v2_boxes.csv', 'w', newline='', encoding='utf-8'), delimiter=';').writerows(brows)
csv.writer(open(W + 'v2_pipes.csv', 'w', newline='', encoding='utf-8'), delimiter=';').writerows(prow)
print('caixas', len(brows), collections.Counter(r[0] for r in brows), 'isoladas', sum(r[7] == 'ISO' for r in brows))
print('tubos', len(prow), 'internos', nint, 'comprimento m', round(sum(math.dist((float(r[5]), float(r[6])), (float(r[8]), float(r[9]))) for r in prow), 1))
print('flags:', collections.Counter(o.split(' (')[0].split(' -')[0] for r in prow for o in r[-1].split(' | ') if o.isupper() or o[:6].isupper()))
print('CF acima do tubo:', sum('ACIMA' in r[-1] for r in brows), '| CF inferida:', sum('INFERIDA' in r[-1] for r in brows))
