"""Prepara a rede elétrica/dados para o Revit (fase 4).
Entradas: work/cotas_<TAG>.json (fase 3), work/amostras_z.csv (terreno), work/estrut_pegadas.csv e work/estrut_lajes.csv (vínculos estruturais).
1) Contorno dos blocos (face externa):
   - BA2: laje do 1º pavimento (contorno externo, sem o pátio);
   - demais: pilares + vigas baldrame + paredes/lajes da fundação + lajes da estrutura, com fechamento de 1,0 m e buracos preenchidos.
2) Perfil 3D de cada pedaço: vértices em planta do DWG + quebras de cota da fase 3 (z interpolado no perfil por abscissa).
3) Corte na face dos blocos (o que fica dentro do bloco é instalação interna, fora do escopo). Caixas dentro de bloco são descartadas.
4) Eletroduto termina na face da caixa (não no centro). Caixa orientada pelo eletroduto mais longo que chega nela.
5) "2xØ": dois eletrodutos lado a lado (eixos afastados DE + 5 cm).
Saídas: work/modelo_<TAG>.json, RELATORIOS/ELE_fase4_cortes_<data>.csv, png de conferência."""
import json, csv, math, collections
from shapely.geometry import MultiPoint, Polygon, LineString, Point
from shapely.ops import unary_union
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
R = 'D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/'
TAGS = ['EL1', 'EL2', 'CF1', 'CF2']
TIPO = {'EL1': 458808, 'EL2': 458810, 'CF1': 458812, 'CF2': 458814}
DISC = {'EL1': 'ELE', 'EL2': 'ELE', 'CF1': 'TEL', 'CF2': 'TEL'}
DWG = {'EL1': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R07', 'EL2': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R05',
       'CF1': '24-049-ALH-SLJ-ETIB-IMP-PE-CF-001-ELG-R05', 'CF2': '24-049-ALH-SLJ-ETIB-IMP-PE-CF-002-ELG-R04'}
# nominal EXATO da tabela "Tabela RNC 40" do Revit (designação métrica, mm): se não casar exatamente, o Revit desenha o eletroduto com o nominal e não com o DE
NOMINAL_MM = {'3/4': 21, '1': 27, '1.1/4': 35, '1 1/4': 35, '1.1/2': 41, '1 1/2': 41, '2': 53, '3': 78, '4': 103, '6': 155}
NOMINAL_POL = {k: v / 25.4 for k, v in NOMINAL_MM.items()}
V1 = [(-22, 33), (17, 33), (18, 36.6), (86.5, 46.3), (87.2, 47.5), (92, 70), (-22, 70)]
V1P = Polygon(V1)
def cover_req(tag, p): return (1.00 if V1P.contains(Point(p)) else 0.70) if tag.startswith('EL') else 0.60

# ---------- 1) blocos ----------
EL = collections.defaultdict(list)
for l in open(W + 'estrut_pegadas.csv', encoding='utf-8'):
    b, nm, cat, i, z0, z1, pts = l.rstrip('\n').split(';', 6)
    EL[b].append(dict(arq=nm.split('-')[7], cat=cat.replace('OST_', ''), z0=float(z0), z1=float(z1), P=[tuple(map(float, q.split(','))) for q in pts.split()]))
LJ = collections.defaultdict(list)
for l in open(W + 'estrut_lajes.csv', encoding='utf-8'):
    b, arq, i, z, A, k, pts = l.rstrip('\n').split(';', 6)
    LJ[b].append(dict(arq=arq, id=int(i), z=float(z), k=int(k), poly=Polygon([tuple(map(float, q.split(','))) for q in pts.split()])))
blocos = []
for b in sorted(EL):
    if b == 'BA2':
        lj = [o for o in LJ[b] if o['id'] == 2104546 and o['k'] == 0]
        polys = [Polygon(lj[0]['poly'].exterior)]
        crit = 'laje do 1º pavimento (ECC 2104546), contorno externo'
    else:
        els = EL[b]; fr = [e for e in els if e['cat'] == 'StructuralFraming']
        zb = min(e['z1'] for e in fr) if fr else -1e9
        sel = [MultiPoint(e['P']).convex_hull for e in els if len(e['P']) >= 3 and (e['cat'] == 'StructuralColumns'
               or (e['cat'] == 'StructuralFraming' and e['z1'] <= zb + 1.0) or (e['arq'] == 'FUN' and e['cat'] in ('Walls', 'Floors')))]
        sel += [o['poly'] for o in LJ[b] if o['poly'].area > 1 and o['arq'] == 'FUN']   # só lajes térreas (a cobertura tem beiral)
        U = unary_union([h.buffer(1.0, join_style=2) for h in sel]).buffer(-1.0, join_style=2)
        polys = [Polygon(g.exterior) for g in (U.geoms if hasattr(U, 'geoms') else [U]) if g.area > 2]
        crit = 'pilares + baldrame + paredes e lajes da fundação (fechamento 1,0 m)'
    for g in polys: blocos.append(dict(bloco=b, poly=g, crit=crit))
# casa de bombas de incêndio (DirectShape do MODELAGEM-INCENDIO, id 8677034): recebe a alimentação das bombas
cb = MultiPoint([tuple(map(float, q.split(','))) for q in open(W + 'casa_bombas_INC.txt').read().split()]).convex_hull
blocos.append(dict(bloco='CB', poly=cb, crit='casa de bombas de incêndio (DirectShape INC 8677034)'))
json.dump([dict(bloco=o['bloco'], area=round(o['poly'].area, 1), crit=o['crit'], coords=[list(c) for c in o['poly'].exterior.coords]) for o in blocos], open(W + 'blocos.json', 'w'), indent=0, ensure_ascii=False)
def bloco_de(p, tol=0.0):
    for o in blocos:
        if o['poly'].buffer(tol).contains(Point(p)): return o['bloco']
    return None

# ---------- terreno (amostras da fase 3) ----------
AM = collections.defaultdict(list)
for r in csv.DictReader(open(W + 'amostras_z.csv'), delimiter=';'):
    if not r['peca'].startswith('CX'): AM[(r['tag'], int(r['peca']))].append((float(r['s']), float(r['zt'])))
def interp(xs, ys, x):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            u = (x - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] > xs[i] else 0
            return ys[i] + u * (ys[i + 1] - ys[i])

# ---------- 2..5) ----------
log = []; resumo = {}
for tag in TAGS:
    N = json.load(open(W + f'cotas_{tag}.json'))
    boxes = N['boxes']
    for j, bx in enumerate(boxes):
        bx['id'] = f'{tag}-CX{j:02d}'; bx['bloco'] = bloco_de(bx['c'], -0.05); bx['usada'] = False
        if bx['bloco']: log.append([tag, bx['id'], 'caixa', '', '', '', f"caixa dentro do bloco {bx['bloco']}: não modelada"])
    conduits = []
    for i, p in enumerate(N['pieces']):
        pid = f'{tag}-{i:03d}'
        line = LineString(p['pts']); Ltot = line.length
        # perfil z(s): pontas dos trechos da fase 3 projetadas na polilinha
        prof = sorted({round(line.project(Point(l['a'][:2])), 4): l['a'][2] for l in p['legs']}.items() | {round(line.project(Point(l['b'][:2])), 4): l['b'][2] for l in p['legs']}.items())
        ps, pz = [q[0] for q in prof], [q[1] for q in prof]
        sv = sorted(set([round(line.project(Point(q)), 4) for q in line.simplify(0.05).coords] + ps))   # vértices em planta (simplificados a 5 cm: arcos do DWG) + quebras de cota
        terr = sorted(AM[(tag, i)]); ts, tz = [q[0] for q in terr], [q[1] for q in terr]
        # 3) corte nos blocos: intervalos de s fora dos blocos
        dentro = []
        for o in blocos:
            X = line.intersection(o['poly'])
            nucleo = o['poly'].buffer(-0.50)   # entra no bloco = passa 50 cm além da face ou termina dentro dele (eletroduto rente à face não é cortado)
            for g in (X.geoms if hasattr(X, 'geoms') else [X]):
                if g.is_empty or g.length < 1e-3: continue
                c = list(g.coords); s0, s1 = sorted((line.project(Point(c[0])), line.project(Point(c[-1]))))
                if not (g.intersects(nucleo) or s0 < 0.05 or s1 > Ltot - 0.05): continue
                dentro.append((s0, s1, o['bloco']))
        dentro.sort(); fora = []; cur = 0.0; fim_tipo = {}
        for s0, s1, b in dentro:
            if s0 - cur > 0.05: fora.append([cur, s0])
            if s0 > 0.05: fim_tipo[round(s0, 4)] = b
            if s1 < Ltot - 0.05: fim_tipo[round(s1, 4)] = b
            cur = max(cur, s1)
        if Ltot - cur > 0.05: fora.append([cur, Ltot])
        if dentro:
            Ldentro = sum(s1 - s0 for s0, s1, b in dentro)
            log.append([tag, pid, 'eletroduto', f'{Ltot:.2f}', f'{Ltot - Ldentro:.2f}', f'{Ldentro:.2f}', 'cortado na face do bloco ' + '/'.join(sorted({b for *_, b in dentro}))])
        for k, (s0, s1) in enumerate(fora):
            sub = pid + ('abcdefgh'[k] if len(fora) > 1 else '')
            ends = []
            for s, key in ((s0, 'cx_ini'), (s1, 'cx_fim')):
                at_end = (s < 0.05) if key == 'cx_ini' else (s > Ltot - 0.05)
                j = p[key] if at_end else None
                if j is not None and boxes[j]['bloco']: j = None
                ends.append(dict(s=s, box=j, face=None if at_end else fim_tipo.get(round(s, 4), '?')))
            conduits.append(dict(pid=pid, sub=sub, i=i, piece=p, ends=ends, line=line, ps=ps, pz=pz, sv=sv, ts=ts, tz=tz, Ltot=Ltot))
    # 4) orientação das caixas: direção do eletroduto mais longo que chega nela
    for j, bx in enumerate(boxes):
        best = None
        for c in conduits:
            for e in c['ends']:
                if e['box'] != j: continue
                s = e['s']; s2 = min(c['Ltot'], s + 1.0) if s < c['Ltot'] / 2 else max(0, s - 1.0)
                a, b2 = c['line'].interpolate(s), c['line'].interpolate(s2)
                ang = math.atan2(b2.y - a.y, b2.x - a.x)
                if best is None or c['Ltot'] > best[0]: best = (c['Ltot'], ang)
        bx['ang'] = (best[1] % (math.pi / 2)) if best else 0.0
        bx['usada'] = best is not None
    # recorte na face da caixa
    out = []
    for c in conduits:
        p = c['piece']; de = p['de_mm'] / 1000
        s0, s1 = c['ends'][0]['s'], c['ends'][1]['s']
        for idx, e in enumerate(c['ends']):
            if e['box'] is None: continue
            bx = boxes[e['box']]; h = bx['dim'][0] / 200.0
            s = e['s']; s2 = min(c['Ltot'], s + 0.5) if idx == 0 else max(0, s - 0.5)
            a, b2 = c['line'].interpolate(s), c['line'].interpolate(s2)
            ph = math.atan2(b2.y - a.y, b2.x - a.x) - bx['ang']
            d = h / max(abs(math.cos(ph)), abs(math.sin(ph)), 1e-6)
            if idx == 0: s0 = s0 + d
            else: s1 = s1 - d
        if s1 - s0 < 0.10:
            log.append([tag, c['sub'], 'eletroduto', f"{c['Ltot']:.2f}", '0', '', 'descartado: menor que 10 cm entre as faces das caixas']); continue
        svals = [s0] + [s for s in c['sv'] if s0 + 0.01 < s < s1 - 0.01] + [s1]
        P3 = []
        for s in svals:
            q = c['line'].interpolate(s); P3.append([q.x, q.y, interp(c['ps'], c['pz'], s), s])
        # 5) bancos "2xØ"
        ntub = p.get('n_tubos', 1)
        offs = [0.0] if ntub == 1 else [-(de + 0.05) / 2, (de + 0.05) / 2]
        for t, off in enumerate(offs):
            segs = []
            for k in range(len(P3) - 1):
                a, b2 = P3[k], P3[k + 1]
                L = math.hypot(b2[0] - a[0], b2[1] - a[1])
                if L < 0.005: continue
                nx, ny = -(b2[1] - a[1]) / L, (b2[0] - a[0]) / L
                A = [a[0] + off * nx, a[1] + off * ny, a[2]]; B = [b2[0] + off * nx, b2[1] + off * ny, b2[2]]
                # recobrimento real no segmento (amostras do terreno da fase 3)
                cv = []
                for ss, zt in zip(c['ts'], c['tz']):
                    if a[3] - 1e-6 <= ss <= b2[3] + 1e-6:
                        u = (ss - a[3]) / (b2[3] - a[3]) if b2[3] > a[3] else 0
                        cv.append(zt - (a[2] + u * (b2[2] - a[2]) + de / 2))
                ta, tb = interp(c['ts'], c['tz'], a[3]), interp(c['ts'], c['tz'], b2[3])
                cv += [ta - (a[2] + de / 2), tb - (b2[2] + de / 2)]
                segs.append(dict(a=A, b=B, cov_min=round(min(cv), 3), terr_a=round(ta, 3), terr_b=round(tb, 3)))
            if not segs: continue
            obs = []
            e0, e1 = c['ends']
            for e in (e0, e1):
                if e['face']: obs.append(f"cortado na face do bloco {e['face']} (rede interna fora do escopo)")
            org = p['rot']['origem']
            if org != 'rótulo': obs.append('Ø ' + org)
            if ntub > 1: obs.append(f'banco {ntub} eletrodutos ({t + 1}/{ntub})')
            if e0['box'] is None and not e0['face'] or e1['box'] is None and not e1['face']: obs.append('ponta sem caixa no projeto')
            out.append(dict(trecho=c['sub'] + (f'/{t + 1}' if ntub > 1 else ''), tipo=TIPO[tag], pol=p['pol'], nominal_pol=NOMINAL_POL[p['pol']], de_mm=p['de_mm'],
                            disc=DISC[tag], desc=(f"{N['rede']} - Ø{p['pol']}\"" + (f" - {p['rot'].get('contexto', '')[:90]}" if p['rot'].get('contexto') else '')).strip(),
                            coment=(p['rot']['texto'] + ' ' + p['rot'].get('contexto', '')).strip()[:250],
                            cov_req=cover_req(tag, P3[0][:2]), origem=DWG[tag], obs='; '.join(obs), segs=segs,
                            ini='caixa ' + boxes[e0['box']]['id'] if e0['box'] is not None else ('face ' + e0['face'] if e0['face'] else 'ponta'),
                            fim='caixa ' + boxes[e1['box']]['id'] if e1['box'] is not None else ('face ' + e1['face'] if e1['face'] else 'ponta')))
    for b in boxes:   # caixa do projeto sem eletroduto ligado: modelada assim mesmo, orientada como a caixa vizinha
        if not b['bloco'] and not b['usada']:
            viz = min((q for q in boxes if q['usada']), key=lambda q: (q['c'][0] - b['c'][0]) ** 2 + (q['c'][1] - b['c'][1]) ** 2)
            b['ang'] = viz['ang']; b['obs'] = 'caixa do projeto sem eletroduto ligado a ela'
            log.append([tag, b['id'], 'caixa', '', '', '', 'caixa sem eletroduto ligado: modelada (orientação da vizinha)'])
    bxs = [dict(id=b['id'], c=b['c'], dim=b['dim'], ang=b['ang'], ct=b['ct'], cf=b['cf'], prof=b['prof'], fonte=b['fonte'], n=b['n_eletrodutos'], obs=b.get('obs', ''))
           for b in boxes if not b['bloco']]
    json.dump(dict(tag=tag, rede=N['rede'], conduits=out, boxes=bxs), open(W + f'modelo_{tag}.json', 'w'), indent=0, ensure_ascii=False)
    L = sum(math.dist(s['a'][:2], s['b'][:2]) for c in out for s in c['segs'])
    resumo[tag] = (len(out), sum(len(c['segs']) for c in out), L, len(bxs), min(s['cov_min'] for c in out for s in c['segs']))
    print(f"{tag}: {len(out)} eletrodutos (trechos) -> {resumo[tag][1]} segmentos Revit, {L:.1f} m | {len(bxs)} caixas | recobr. mín {resumo[tag][4]:.2f}")
with open(R + 'ELE_fase4_cortes_2026-10-15.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['rede', 'trecho/caixa', 'elemento', 'comp_original_m', 'comp_modelado_m', 'comp_dentro_bloco_m', 'o que foi feito']); w.writerows(log)
for o in blocos: print('bloco', o['bloco'], round(o['poly'].area, 1), 'm2')
print('log', len(log))
