"""v2 corrigida (14/10, feixes + mergulhos) -> CSVs para o Revit.
work/v2_boxes.csv  : tipo;id;x;y;CT;CF;lado;ISO;obs
work/v2_pipes.csv  : n;trecho;DN;mat;sys;x1;y1;z1;x2;y2;z2;GIm;GIj;i%;Tm;Tj;recob;peça;obs   (z = eixo do tubo)
peça: H = horizontal (declividade do projeto), VP = vertical do pé de prumada/subida (até o terreno),
      VM = vertical do mergulho (chegada na caixa), E = entrada na caixa após o mergulho"""
import math, pickle, collections, csv
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
D = pickle.load(open(W + 'v2_net.pkl', 'rb'))
nodes, edges, boxes = D['nodes'], D['edges'], D['boxes']
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
for k, e in enumerate(edges): inc[e['up']].append(k); inc[e['dn']].append(k)
bad = collections.defaultdict(list)
for bid, k, v, top in D.get('bad_lab', []): bad[bid].append('%s %.2f' % (k, v))
# ---------------- caixas
brows = []
for b in boxes:
    n = b['n']; nd = nodes[n]
    inv = [edges[k]['zu'] if edges[k]['up'] == n else edges[k].get('entry') or edges[k]['zd'] for k in inc[n]]
    ct = b['CT'] if b['CT'] else nd['g']; obs = []
    if bad[b['id']]: obs.append('RÓTULO(S) %s ACIMA DA TAMPA - descartado(s), registrar no relatório' % ', '.join(bad[b['id']]))
    if not b['CT']: obs.append('CT = terreno de projeto estimado (sem rótulo)')
    cf = b['CF']
    if cf is not None and cf > ct - 0.1: obs.append('CF do rótulo (%.2f) incoerente com CT - desconsiderada' % cf); cf = None
    if cf is None:
        cf = (min(inv) - 0.10) if inv else ct - 0.60
        obs.append('CF INFERIDA (geratriz inferior - 0,10 m)' if inv else 'CF INFERIDA (profundidade 0,60 adotada)')
    else:
        obs.append('CT/CF do projeto' if b['CT'] else 'CF do projeto')
        if inv and cf > min(inv) + 0.02: obs.append('CF do projeto ACIMA da geratriz do tubo (%.2f) - registrar no relatório' % min(inv))
    if not inc[n]: obs.insert(0, 'CAIXA SEM TUBULAÇÃO NO PROJETO R04 - registrar no relatório')
    sz, so = (1.10, 'PV Ø1,10 m') if b['tipo'] == 'PV' else box_size(nd['p'])
    obs.append(so)
    brows.append([b['tipo'], b['id'], '%.4f' % nd['p'][0], '%.4f' % nd['p'][1], '%.3f' % ct, '%.3f' % cf, '%.2f' % sz,
                  'ISO' if not inc[n] else '', ' | '.join(obs).replace(';', ',')])
# ---------------- tubos
order = sorted(range(len(edges)), key=lambda k: (round(-edges[k]['P0'][1] / 20), edges[k]['P0'][0]))
prow = []; nint = 0; cnt = collections.Counter()
f4 = lambda v: '%.4f' % v
for j, k in enumerate(order):
    e = edges[k]; name = 'DRN-%03d' % (j + 1); od = e['od']
    p0 = e['vf_up'] or e['P0']; p1 = e['vf_dn'] or e['P1']
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    sysc = 'INT' if (e['DN'] <= 150 and inside(*p0) and inside(*p1) and inside(*mid)) else 'AP'
    nint += sysc == 'INT'
    obs = []
    if e.get('dirsrc') not in ('seta',): obs.append('sentido deduzido pela rede (sem seta no DWG)')
    obs.append(('declividade do rótulo %g%%' % round(e['sl'] * 100, 2)) if e['sl_src'] == 'rótulo' else 'declividade padrão 1% adotada (sem rótulo)')
    if 'CS' in e: obs.append('CS %.2f do projeto' % e['CS'])
    if 'CE' in e: obs.append('CE %.2f do projeto' % e['CE'])
    if e['sl_src'] == 'rótulo' and e['Lm'] > 1 and abs(e['i'] - e['sl']) > 0.0025:
        obs.insert(0, 'DECLIVIDADE %.2f%% IMPOSTA PELAS COTAS DAS CAIXAS (rótulo %.0f%%) - registrar no relatório' % (e['i'] * 100, e['sl'] * 100))
    elif e['Lm'] > 1 and e['i'] < 0.005: obs.insert(0, 'DECLIVIDADE < 0,5%% (%.2f%%) IMPOSTA PELAS COTAS DO PROJETO - registrar no relatório' % (e['i'] * 100))
    cov = min(e['cov_u'], e['cov_d'])
    if cov < 0.195: obs.insert(0, 'RECOBRIMENTO %.2f m < 0,20 (%s) - registrar no relatório' % (cov, 'terreno x cota do projeto' if e['cov_conflito'] else 'cota da caixa'))
    sl = e['i'] * 100
    base = [e['DN'], e['mat'], sysc]
    def row(tr, a, za, b, zb, gim, gij, ii, peca, ob):
        prow.append([len(prow) + 1, tr] + base + [f4(a[0]), f4(a[1]), f4(za), f4(b[0]), f4(b[1]), f4(zb), f4(gim), f4(gij), '%.3f' % ii,
                     '%.3f' % e['g_up'], '%.3f' % e['g_dn'], '%.3f' % cov, peca, ' | '.join(ob).replace(';', ',')]); cnt[peca] += 1
    if math.dist(p0, p1) >= 0.15: row(name, p0, e['zu'] + od / 2, p1, e['zd'] + od / 2, e['zu'], e['zd'], sl, 'H', obs)   # (<15 cm: mergulho logo no início, sem horizontal)
    if e['vf_up'] and e['riser'] > 0.05:
        row(name + '-VP', p0, e['zu'] + od / 2, p0, e['g_up'], e['zu'], e['g_up'], 0, 'VP',
            ['pé de prumada / subida: joelho do desenho (Simbolos) - vertical enterrada até o terreno (%.2f m)' % e['riser']])
    if e['vf_dn']:
        ent = e['entry'] if e['entry'] is not None else e['zd']
        if e['zd'] - ent > 0.02:
            row(name + '-VM', p1, e['zd'] + od / 2, p1, ent + od / 2, e['zd'], ent, 0, 'VM',
                ['mergulho na chegada à caixa (conexão do desenho): desce %.2f m até %s %.2f' % (e['zd'] - ent, 'CE' if 'CE' in e else 'saída/fundo', ent)])
        if math.dist(p1, e['P1']) > 0.1:
            row(name + '-E', p1, ent + od / 2, e['P1'], ent + od / 2, ent, ent, 0, 'E', ['entrada na caixa após o mergulho'])
csv.writer(open(W + 'v2_boxes.csv', 'w', newline='', encoding='utf-8'), delimiter=';').writerows(brows)
csv.writer(open(W + 'v2_pipes.csv', 'w', newline='', encoding='utf-8'), delimiter=';').writerows(prow)
print('caixas', len(brows), collections.Counter(r[0] for r in brows), 'isoladas', sum(r[7] == 'ISO' for r in brows))
print('peças', dict(cnt), '| trechos', len(edges), '| internos', nint)
print('comprimento horizontal %.1f m | vertical %.1f m' % (
    sum(math.dist((float(r[5]), float(r[6])), (float(r[8]), float(r[9]))) for r in prow if r[-2] in ('H', 'E')),
    sum(abs(float(r[7]) - float(r[10])) for r in prow if r[-2] in ('VP', 'VM'))))
