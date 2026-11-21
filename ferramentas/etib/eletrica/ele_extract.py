"""Extrai as redes enterradas dos 4 DWGs de elétrica/dados (coordenadas locais do modelo = UTM - 561500/8658000).
Saída: work/rede_<TAG>.json com trechos (polilinha), caixas e rótulos.
- Eletroduto = cada LINE/LWPOLYLINE/ARC do layer 02. F_ELETRODUTO*, encadeado pelas pontas (< 0,05 m) e
  cortado nas caixas. Linhas paralelas de um banco ficam como trechos separados (cada linha = 1 eletroduto).
- Caixa = bloco Cx60x60 ou polilinha fechada quadrada (0,15–1,2 m de lado); tamanho pelo texto "Cx. AxB" mais próximo.
"""
import sys, json, math, re, os, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
from ld import load, pts
from geo import tf

def arcpts(r, f):
    m = re.match(r'(-?[\d.]+),(-?[\d.]+) r=([\d.]+) a=([-\d.]+),([-\d.]+)', r[3])
    cx, cy, rr, a0, a1 = map(float, m.groups())
    if a1 < a0: a1 += 2 * math.pi
    n = max(4, int(rr * (a1 - a0) / 0.5) + 1)
    return [f((cx + rr * math.cos(a0 + (a1 - a0) * i / n), cy + rr * math.sin(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

def txt(r, f):
    m = re.match(r'(-?[\d.]+),(-?[\d.]+) h=([\d.]+) rot=([-\d.]+) (.*)', r[3], re.S)
    if not m: return None
    t = re.sub(r'\\[A-Za-z][^;]*;', '', m.group(5)); t = t.replace('%%C', 'Ø').replace('%%c', 'Ø').replace('{', '').replace('}', '').strip()
    return dict(p=f((float(m.group(1)), float(m.group(2)))), t=t, h=float(m.group(3)))

def extract(tag):
    R = load(tag); f = tf(tag)
    segs = []
    for r in R:
        if not r[1].startswith('02. F_ELETRODUTO'): continue
        if r[0] in ('LINE', 'LWPOLYLINE'):
            q = [f(p) for p in pts(r[3].split(' ', 1)[1] if r[3].startswith('c=') else r[3])]
            if len(q) >= 2 and sum(math.dist(a, b) for a, b in zip(q, q[1:])) > 0.05: segs.append(q)
        elif r[0] == 'ARC':
            segs.append(arcpts(r, f))
    # caixas
    box = []
    for r in R:
        if r[0] == 'INSERT' and r[3].endswith('Cx60x60'):
            m = re.match(r'(-?[\d.]+),(-?[\d.]+)', r[3]); box.append(dict(c=f((float(m.group(1)), float(m.group(2)))), src='bloco Cx60x60'))
        if r[0] == 'LWPOLYLINE' and not r[1].startswith('02.'):
            q = pts(r[3].split(' ', 1)[1])
            if len(q) == 5 and math.dist(q[0], q[-1]) < 0.01: q = q[:4]
            if len(q) == 4 and (r[3].startswith('c=1') or True):
                sides = [math.dist(q[i], q[(i + 1) % 4]) for i in range(4)]
                if 0.15 < min(sides) and max(sides) < 1.2 and max(sides) / min(sides) < 1.3:
                    c = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4); box.append(dict(c=f(c), src='quadrado ' + r[1], lado=round(sum(sides) / 4, 2)))
    # dedupe (quadrado interno/externo)
    out = []
    for b in box:
        if any(math.dist(b['c'], o['c']) < 0.4 for o in out): continue
        out.append(b)
    box = out
    T = [txt(r, f) for r in R if r[0] in ('MTEXT', 'TEXT')]; T = [t for t in T if t]
    cxt = [t for t in T if re.search(r'(?i)cx\.?\s*\d+\s*x\s*\d+', t['t'])]
    for b in box:
        c = min(cxt, key=lambda t: math.dist(t['p'], b['c']), default=None)
        if c and math.dist(c['p'], b['c']) < 4.0:
            m = re.search(r'(?i)cx\.?\s*(\d+)\s*x\s*(\d+)', c['t']); b['dim_cm'] = (int(m.group(1)), int(m.group(2))); b['dist_txt'] = round(math.dist(c['p'], b['c']), 2)
        else:
            b['dim_cm'] = (60, 60) if 'Cx60' in b['src'] else (int(round(b.get('lado', 0.6) * 100)),) * 2; b['dist_txt'] = None
    # encadeia segmentos pelas pontas
    chains = [list(s) for s in segs]
    changed = True
    while changed:
        changed = False
        for i in range(len(chains)):
            for j in range(len(chains)):
                if i == j or not chains[i] or not chains[j]: continue
                a, b = chains[i], chains[j]
                if math.dist(a[-1], b[0]) < 0.05: chains[i] = a + b[1:]; chains[j] = []; changed = True
                elif math.dist(a[-1], b[-1]) < 0.05: chains[i] = a + b[::-1][1:]; chains[j] = []; changed = True
                elif math.dist(a[0], b[-1]) < 0.05: chains[i] = b + a[1:]; chains[j] = []; changed = True
                elif math.dist(a[0], b[0]) < 0.05: chains[i] = b[::-1] + a[1:]; chains[j] = []; changed = True
        chains = [c for c in chains if c]
    runs = []
    for c in chains:
        L = sum(math.dist(a, b) for a, b in zip(c, c[1:]))
        if L < 0.3: continue
        def nb(p):
            d = min(((math.dist(p, b['c']), k) for k, b in enumerate(box)), default=(99, None))
            return d
        runs.append(dict(pts=[(round(x, 3), round(y, 3)) for x, y in c], L=round(L, 2), ini=nb(c[0]), fim=nb(c[-1])))
    return dict(tag=tag, runs=runs, boxes=box, textos=[t for t in T if re.search(r'(Ø|#|FO|UTP|IE-|Cx)', t['t'], re.I)])

if __name__ == '__main__':
    os.makedirs('D:/Projeto Modelagem/FERRAMENTAS/eletrica/work', exist_ok=True)
    for tag in ['EL1', 'EL2', 'CF1', 'CF2']:
        X = extract(tag)
        json.dump(X, open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/rede_{tag}.json', 'w'), indent=0)
        nb = collections.Counter(b['src'].split(' ')[0] for b in X['boxes'])
        sem = sum(1 for b in X['boxes'] if b['dist_txt'] is None)
        pf = [r for r in X['runs'] if r['ini'][0] > 1.0 or r['fim'][0] > 1.0]
        print(f"{tag}: {len(X['runs'])} trechos, {sum(r['L'] for r in X['runs']):.0f} m | caixas {len(X['boxes'])} {dict(nb)} (sem texto de dimensão: {sem}) | trechos com ponta a >1 m de caixa: {len(pf)}")
