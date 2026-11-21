"""Monta as redes de eletroduto por pedaço (caixa a caixa), com Ø e circuito.
Entrada: work/rede_<TAG>.json (ele_extract), work/rotulos_<TAG>.json (ele_labels). Saída: work/pecas_<TAG>.json + csv.
Regras:
- caixas: EL1/CF2 = quadrados do DWG; EL2/CF1 = texto "Cx. AxB" encaixado no vértice/ponto do eletroduto mais próximo (< 3 m)
- corta cada eletroduto onde passa a < 0,5 m do centro de uma caixa
- cada pedaço recebe o rótulo mais próximo (ponto da chamada a < 0,3 m; EL2: texto do DWG a < 3 m)
- pedaço sem rótulo herda do vizinho no mesmo eletroduto (antes/depois da caixa); senão, Ø da nota do projeto
"""
import sys, json, math, re, csv, collections
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
POL = {'3/4': 27, '1': 33, '1.1/4': 42, '1 1/4': 42, '1.1/2': 48, '1 1/2': 48, '2': 60, '3': 89, '4': 114, '6': 168}
NOTA = {'EL1': '3/4', 'EL2': '3/4', 'CF1': '1', 'CF2': '1'}
REDE = {'EL1': 'ELE - Alimentação BT', 'EL2': 'ELE - Iluminação externa', 'CF1': 'TEL - CFTV', 'CF2': 'TEL - Dados e telefonia'}

def proj(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; n = dx * dx + dy * dy
    u = 0 if n == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    q = (a[0] + u * dx, a[1] + u * dy); return math.dist(p, q), u, q

def polyproj(p, P):
    """dist, abscissa s, ponto"""
    best = (1e9, 0, None); s0 = 0
    for a, b in zip(P, P[1:]):
        L = math.dist(a, b); d, u, q = proj(p, a, b)
        if d < best[0]: best = (d, s0 + u * L, q)
        s0 += L
    return best

def cut(P, ss):
    """corta polilinha nas abscissas ss -> lista de polilinhas"""
    cum = [0]
    for a, b in zip(P, P[1:]): cum.append(cum[-1] + math.dist(a, b))
    def at(s):
        for i in range(len(P) - 1):
            if cum[i] <= s <= cum[i + 1] + 1e-9:
                L = cum[i + 1] - cum[i]; u = 0 if L == 0 else (s - cum[i]) / L
                return i, (P[i][0] + u * (P[i + 1][0] - P[i][0]), P[i][1] + u * (P[i + 1][1] - P[i][1]))
        return len(P) - 2, P[-1]
    ss = sorted(s for s in ss if 0.05 < s < cum[-1] - 0.05)
    out = []; prev = 0
    for s in ss + [cum[-1]]:
        i0, p0 = at(prev); i1, p1 = at(s)
        piece = [p0] + [P[k] for k in range(i0 + 1, i1 + 1)] + [p1]
        piece = [q for k, q in enumerate(piece) if k == 0 or math.dist(q, piece[k - 1]) > 1e-4]
        if len(piece) >= 2 and sum(math.dist(a, b) for a, b in zip(piece, piece[1:])) > 0.1: out.append(piece)
        prev = s
    return out

def build(tag):
    X = json.load(open(W + f'rede_{tag}.json')); Lb = json.load(open(W + f'rotulos_{tag}.json'))
    runs = [r['pts'] for r in X['runs']]
    LOT = lambda p: -38 < p[0] < 110 and -118 < p[1] < 70
    if tag in ('EL1', 'CF2'):
        boxes = [dict(c=b['c'], dim=b['dim_cm'], fonte='quadrado DWG') for b in X['boxes'] if LOT(b['c'])]
    else:
        boxes = []
        for tx in X['textos']:
            m = re.search(r'(?i)cx\.?\s*(\d+)\s*x\s*(\d+)', tx['t'])
            if not m or not LOT(tx['p']): continue
            cand = [(math.dist(tx['p'], v), v) for P in runs for v in (P[0], P[-1])]
            cand += [(math.dist(tx['p'], v) + 0.5, v) for P in runs for v in P[1:-1]]
            d, v = min(cand)
            if d > 2.5:
                d2, s, q = min((polyproj(tx['p'], P) for P in runs), key=lambda x: x[0]); v = q if d2 < 4.5 else None
            if v is None: continue
            if any(math.dist(v, b['c']) < 1.0 for b in boxes): continue
            boxes.append(dict(c=list(v), dim=(int(m.group(1)), int(m.group(2))), fonte='texto Cx (encaixado)', d_txt=round(min(d, 9), 2)))
    # cortes nas caixas
    pieces = []
    for ri, P in enumerate(runs):
        ss = []
        for b in boxes:
            d, s, q = polyproj(b['c'], P)
            if d < 0.5: ss.append(s)
        for k, pc in enumerate(cut(P, ss)): pieces.append(dict(run=ri, k=k, pts=pc))
    for p in pieces:
        p['L'] = round(sum(math.dist(a, b) for a, b in zip(p['pts'], p['pts'][1:])), 2)
        for e, key in ((p['pts'][0], 'cx_ini'), (p['pts'][-1], 'cx_fim')):
            d, j = min(((math.dist(e, b['c']), j) for j, b in enumerate(boxes)), default=(99, None))
            p[key] = j if d < 0.6 else None
    # rótulos
    for p in pieces: p['rot'] = None
    if tag == 'EL2':
        cand = [dict(texto=t['t'], ponto_m=t['p'], contexto=[]) for t in X['textos'] if 'Ø' in t['t'] and len(t['t']) < 10]
        tolr = 3.0
    else:
        cand = [o for o in Lb if 'ponto_m' in o]; tolr = 0.3
    for o in cand:
        d, j = min(((polyproj(o['ponto_m'], p['pts'])[0], j) for j, p in enumerate(pieces)), default=(99, None))
        if d < tolr and (pieces[j]['rot'] is None or d < pieces[j]['rot']['d']):
            pieces[j]['rot'] = dict(texto=o['texto'], contexto=' '.join(o.get('contexto', [])), d=round(d, 3), origem='rótulo')
    # propagação no mesmo eletroduto
    for it in range(20):
        ch = False
        for p in pieces:
            if p['rot']: continue
            viz = [q for q in pieces if q['run'] == p['run'] and abs(q['k'] - p['k']) == 1 and q['rot']]
            if viz:
                p['rot'] = dict(viz[0]['rot']); p['rot']['origem'] = 'herdado do mesmo eletroduto'; ch = True
        if not ch: break
    # propagação através da caixa: pareamento 1-a-1 pela ponta mais próxima dentro da mesma caixa
    for it in range(30):
        pares = []
        for i, p in enumerate(pieces):
            if p['rot']: continue
            for e, kb in ((p['pts'][0], 'cx_ini'), (p['pts'][-1], 'cx_fim')):
                B = p[kb]
                if B is None: continue
                for j, q in enumerate(pieces):
                    if j == i or not q['rot']: continue
                    for f, kq in ((q['pts'][0], 'cx_ini'), (q['pts'][-1], 'cx_fim')):
                        if q[kq] == B: pares.append((math.dist(e, f), i, j, B))
        if not pares: break
        usados_i, usados_j, ch = set(), set(), False
        for d, i, j, B in sorted(pares):
            if i in usados_i or (j, B) in usados_j: continue
            usados_i.add(i); usados_j.add((j, B))
            pieces[i]['rot'] = dict(pieces[j]['rot']); pieces[i]['rot']['origem'] = 'herdado pela caixa (continuidade presumida)'; ch = True
        if not ch: break
        # depois de cada rodada, de novo a herança no mesmo eletroduto
        for p in pieces:
            if p['rot']: continue
            viz = [q for q in pieces if q['run'] == p['run'] and abs(q['k'] - p['k']) == 1 and q['rot']]
            if viz: p['rot'] = dict(viz[0]['rot']); p['rot']['origem'] = 'herdado do mesmo eletroduto'
    for p in pieces:
        if not p['rot']: p['rot'] = dict(texto=f'Ø{NOTA[tag]}"', contexto='', d=None, origem='nota do projeto (não cotado)')
        m = re.search(r'Ø\s*([\d./ ]+?)"?\s*$', p['rot']['texto'].replace('"', '"'))
        pol = (m.group(1).strip() if m else NOTA[tag]).replace('Z', '2')
        p['pol'] = pol; p['de_mm'] = POL.get(pol, POL[NOTA[tag]])
        p['n_tubos'] = 2 if re.search(r'2\s*x\s*Ø', p['rot']['texto']) else 1
    return dict(tag=tag, rede=REDE[tag], boxes=boxes, pieces=pieces)

if __name__ == '__main__':
    tot = []
    for tag in ['EL1', 'EL2', 'CF1', 'CF2']:
        N = build(tag); json.dump(N, open(W + f'pecas_{tag}.json', 'w'), indent=0, ensure_ascii=False)
        org = collections.Counter(p['rot']['origem'] for p in N['pieces'])
        pol = collections.Counter(p['pol'] for p in N['pieces'])
        L = sum(p['L'] for p in N['pieces'])
        livres = sum(1 for p in N['pieces'] for k in ('cx_ini', 'cx_fim') if p[k] is None)
        print(f"{tag} {N['rede']}: {len(N['pieces'])} pedaços, {L:.0f} m, {len(N['boxes'])} caixas | Ø {dict(pol)} | origem {dict(org)} | pontas sem caixa {livres}")
