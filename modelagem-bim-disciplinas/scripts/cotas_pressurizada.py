"""Cotas de rede que segue o terreno (água fria, incêndio, GLP, SDAI, eletrodutos enterrados).

Para cada trecho: amostra o terreno a cada --passo m, quebra onde o terreno desvia mais que
--eps da reta (Douglas-Peucker, segmento mínimo --min), e itera abaixando os nós até nenhum
ponto ficar com recobrimento menor que o exigido. Nós compartilhados entre trechos têm uma
cota só (a mais baixa exigida).

Entradas:
  runs.json      saída do topologia_rede.py ({"runs": {"T01": [[x,y],...], ...}})
  terreno.txt    amostras "x;y;z" (m), uma por linha (ReferenceIntersector no Toposolid)
Opções:
  --de 75                     diâmetro externo padrão (mm)
  --de-trechos de.json        {"T05": 85, ...} DE por trecho
  --recobrimento 0.30         recobrimento padrão (m), medido no topo do tubo
  --veiculos poligonos.json   [[[x,y],...], ...] áreas de veículos
  --recobrimento-veiculos 0.60

Saída: <saida>_legs.json e <saida>_legs.csv com cota do EIXO em cada ponta (za, zb),
recobrimento mín/máx real, exigido e terreno nas pontas.
"""
import argparse, csv, json, math, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument('runs'); ap.add_argument('terreno')
ap.add_argument('--de', type=float, default=75.0)
ap.add_argument('--de-trechos')
ap.add_argument('--recobrimento', type=float, default=0.30)
ap.add_argument('--veiculos')
ap.add_argument('--recobrimento-veiculos', type=float, default=0.60)
ap.add_argument('--eps', type=float, default=0.20)
ap.add_argument('--min', type=float, default=2.0)
ap.add_argument('--passo', type=float, default=0.5)
ap.add_argument('--saida', default='rede')
a = ap.parse_args()

runs = json.load(open(a.runs, encoding='utf-8'))['runs']
if isinstance(runs, list):
    runs = {f'T{i + 1:02d}': r for i, r in enumerate(runs)}
TZ = np.array([[float(v) for v in l.replace(',', '.').split(';')[:3]]
               for l in open(a.terreno, encoding='utf-8') if l.strip() and not l.startswith('#')])
DE = json.load(open(a.de_trechos, encoding='utf-8')) if a.de_trechos else {}
POLYS = json.load(open(a.veiculos, encoding='utf-8')) if a.veiculos else []


def terr(p):
    d = np.hypot(TZ[:, 0] - p[0], TZ[:, 1] - p[1]); i = np.argsort(d)[:3]
    if d[i[0]] < 1e-3: return float(TZ[i[0], 2])
    if d[i[0]] > 5 * a.passo:
        print(f'AVISO: ponto {tuple(np.round(p, 2))} a {d[i[0]]:.1f} m da amostra de terreno mais próxima')
    w = 1 / d[i] ** 2; return float((TZ[i, 2] * w).sum() / w.sum())


def inpoly(p, poly):
    x, y = p; c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c


def cover(p): return a.recobrimento_veiculos if any(inpoly(p, P) for P in POLYS) else a.recobrimento
def zreq(p, de): return terr(p) - cover(p) - de / 2000.0   # cota máxima do eixo
key = lambda p: (round(float(p[0]), 3), round(float(p[1]), 3))


def dp(s, z, i0, i1, out):
    if i1 <= i0 + 1: return
    line = z[i0] + (z[i1] - z[i0]) * (s[i0 + 1:i1] - s[i0]) / (s[i1] - s[i0])
    dev = np.abs(z[i0 + 1:i1] - line); k = int(np.argmax(dev)) + i0 + 1
    if dev.max() > a.eps and s[k] - s[i0] >= a.min and s[i1] - s[k] >= a.min:
        dp(s, z, i0, k, out); out.append(k); dp(s, z, k, i1, out)


legs = []
for rn, r in runs.items():
    de = float(DE.get(rn, a.de)); n_leg = 0
    for u, v in zip(r, r[1:]):
        A = np.array(u, float); B = np.array(v, float); Ln = np.linalg.norm(B - A)
        if Ln < 1e-6: continue
        n = max(2, int(np.ceil(Ln / a.passo)) + 1); s = np.linspace(0, Ln, n)
        P = [A + (B - A) * t / Ln for t in s]
        z = np.array([zreq(p, de) for p in P]); ks = []; dp(s, z, 0, n - 1, ks)
        idx = [0] + sorted(ks) + [n - 1]
        for i0, i1 in zip(idx, idx[1:]):
            n_leg += 1
            legs.append(dict(trecho=rn, leg=n_leg, de=de, a=[float(x) for x in P[i0]], b=[float(x) for x in P[i1]]))

Z = {}
for L in legs:
    for p in (L['a'], L['b']): Z[key(p)] = min(Z.get(key(p), 1e9), zreq(p, L['de']))

for it in range(500):
    ch = False
    for L in legs:
        A = np.array(L['a']); B = np.array(L['b'])
        n = max(2, int(np.ceil(np.linalg.norm(B - A) / a.passo)) + 1)
        za, zb = Z[key(L['a'])], Z[key(L['b'])]; viol = 0; tv = 0
        for t in np.linspace(0, 1, n):
            v = (za + (zb - za) * t) - zreq(A + (B - A) * t, L['de'])
            if v > viol: viol = v; tv = t
        if viol > 1e-4:
            if tv < 0.5: Z[key(L['a'])] -= viol / (1 - tv)
            else: Z[key(L['b'])] -= viol / tv
            ch = True
    if not ch: break
else:
    print('AVISO: não convergiu em 500 iterações')

cmin, cmax = 9e9, -9e9
for L in legs:
    A = np.array(L['a']); B = np.array(L['b']); za, zb = Z[key(L['a'])], Z[key(L['b'])]
    n = max(2, int(np.ceil(np.linalg.norm(B - A) / a.passo)) + 1); cov = []; folga = []; req = []
    for t in np.linspace(0, 1, n):
        p = A + (B - A) * t; c = terr(p) - (za + (zb - za) * t + L['de'] / 2000.0)
        cov.append(c); req.append(cover(p)); folga.append(c - req[-1])
    L.update(za=float(za), zb=float(zb), topo_a=float(za + L['de'] / 2000), topo_b=float(zb + L['de'] / 2000),
             rec_min=float(min(cov)), rec_max=float(max(cov)), rec_exigido=float(max(req)), folga_min=float(min(folga)),
             terreno_a=terr(L['a']), terreno_b=terr(L['b']), comprimento=float(np.linalg.norm(B - A)))
    cmin = min(cmin, L['rec_min']); cmax = max(cmax, L['rec_max'])

json.dump(legs, open(f'{a.saida}_legs.json', 'w', encoding='utf-8'), indent=0)
cols = ['trecho', 'leg', 'de', 'comprimento', 'za', 'zb', 'topo_a', 'topo_b', 'terreno_a', 'terreno_b',
        'rec_exigido', 'rec_min', 'rec_max', 'folga_min']
with open(f'{a.saida}_legs.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(cols + ['xa', 'ya', 'xb', 'yb'])
    for L in legs:
        w.writerow([L[c] if not isinstance(L[c], float) else f'{L[c]:.3f}' for c in cols] +
                   [f'{L["a"][0]:.3f}', f'{L["a"][1]:.3f}', f'{L["b"][0]:.3f}', f'{L["b"][1]:.3f}'])

print(f'iterações: {it} | segmentos retos: {len(legs)} | recobrimento real mín {cmin:.3f} / máx {cmax:.3f} m')
for d in sorted(set(L['de'] for L in legs)):
    print(f'  DE {d:g}: {sum(L["comprimento"] for L in legs if L["de"] == d):.1f} m')
bad = [L for L in legs if L['folga_min'] < -0.005]
if bad: print(f'AVISO: {len(bad)} segmentos abaixo do recobrimento exigido')
