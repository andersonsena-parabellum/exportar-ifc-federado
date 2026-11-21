"""Atribui Ø e circuito a cada eletroduto seguindo as chamadas do PDF (texto Ø -> linha preta -> círculo sobre o eletroduto).
Uso: python ele_labels.py TAG  -> work/rotulos_<TAG>.json"""
import sys, json, math, re, collections
import numpy as np
import pymupdf as fitz
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
from pdf_calib import PDF

tag = sys.argv[1]
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
T = json.load(open(W + f'pdf_T_{tag}.json')); s, R, t = T['s'], np.array(T['R']), np.array(T['t'])
def to_m(x, y): return (s * R @ np.array([x, -y]) + t).tolist()
X = json.load(open(W + f'rede_{tag}.json'))
page = fitz.open(PDF[tag])[0]

spans = []
for b in page.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for sp in l['spans']:
            if sp['text'].strip(): spans.append(dict(t=sp['text'].strip(), bb=sp['bbox']))
segs, circ = [], []
for d in page.get_drawings():
    c = d.get('color')
    if not c or max(c) > 0.15: continue          # só preto
    its = d['items']
    if its and all(i[0] == 'c' for i in its) and d['rect'].width < 5:
        circ.append(((d['rect'].x0 + d['rect'].x1) / 2, (d['rect'].y0 + d['rect'].y1) / 2)); continue
    for i in its:
        if i[0] == 'l': segs.append(((i[1].x, i[1].y), (i[2].x, i[2].y)))
# índice de pontas
def key(p): return (round(p[0] / 0.8), round(p[1] / 0.8))
idx = collections.defaultdict(list)
for k, (a, b) in enumerate(segs):
    for p in (a, b):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): idx[(key(p)[0] + dx, key(p)[1] + dy)].append(k)

def dist_run(p):
    best = (99, None, None)
    for ri, r in enumerate(X['runs']):
        for a, b in zip(r['pts'], r['pts'][1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]; n = dx * dx + dy * dy
            u = 0 if n == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
            d = math.hypot(a[0] + u * dx - p[0], a[1] + u * dy - p[1])
            if d < best[0]: best = (d, ri, (a[0] + u * dx, a[1] + u * dy))
    return best

out = []
for sp in spans:
    if 'Ø' not in sp['t'] or len(sp['t']) > 40 or 'cotad' in sp['t']: continue
    x0, y0, x1, y1 = sp['bb']; yc = (y0 + y1) / 2
    # segmento de chamada que chega no texto (ponta a até 8 pt à esquerda do texto, na altura dele)
    start = [k for k, (a, b) in enumerate(segs) for p in (a, b) if x0 - 8 < p[0] < x0 + 2 and abs(p[1] - yc) < 6]
    if not start: out.append(dict(texto=sp['t'], erro='sem linha de chamada')); continue
    seen, stack, pts = set(), list(set(start)), []
    while stack:
        k = stack.pop()
        if k in seen: continue
        seen.add(k); a, b = segs[k]; pts += [a, b]
        for p in (a, b):
            for j in idx[key(p)]:
                if j not in seen and min(math.dist(p, segs[j][0]), math.dist(p, segs[j][1])) < 0.8: stack.append(j)
        if len(seen) > 60: break
    dots = [c for c in circ if any(math.dist(c, p) < 2.2 for p in pts)]
    if dots: dot = max(dots, key=lambda c: abs(c[0] - x0) + abs(c[1] - yc))
    else: dot = max(pts, key=lambda p: math.dist(p, (x0, yc)))     # chamada sem círculo (multileader): ponta mais distante
    pm = to_m(*dot); d, ri, foot = dist_run(pm)
    # textos da linha da chamada (quadros e bitolas): acima/abaixo da horizontal, entre o círculo e o Ø
    xs = [p[0] for p in pts]; hx0 = min(xs)
    ctx = [o['t'] for o in spans if hx0 - 2 < o['bb'][0] < x0 and abs((o['bb'][1] + o['bb'][3]) / 2 - yc) < 22 and o is not sp]
    m = re.search(r'(\d)\s*x\s*Ø', sp['t'])
    out.append(dict(texto=sp['t'], n_tubos=int(m.group(1)) if m else 1, ponto_m=pm, trecho=ri, dist_trecho_m=round(d, 3), contexto=ctx))
json.dump(out, open(W + f'rotulos_{tag}.json', 'w'), indent=1, ensure_ascii=False)
ok = [o for o in out if 'trecho' in o and o['dist_trecho_m'] < 0.3]
print(f"{tag}: rótulos Ø {len(out)} | ligados a um eletroduto (<0,3 m) {len(ok)} | sem chamada {sum(1 for o in out if o.get('erro')=='sem linha de chamada')} | sem círculo {sum(1 for o in out if o.get('erro')=='chamada sem círculo')} | longe {sum(1 for o in out if 'trecho' in o and o['dist_trecho_m']>=0.3)}")
for o in out: print('  ', o['texto'], o.get('trecho'), o.get('dist_trecho_m'), ' '.join(o.get('contexto', []))[:90], o.get('erro', ''))
