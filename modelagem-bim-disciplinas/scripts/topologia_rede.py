"""Polilinhas da rede (extraídas do CAD) -> grafo -> trechos e nós.

Entrada: JSON com uma lista de polilinhas, cada uma {"layer": "...", "pts": [[x, y], ...]}
(também aceita a chave "l" no lugar de "layer"). Coordenadas em metros, já no sistema do modelo.

Uso:
  python topologia_rede.py geom.json --layers "HI-Condutos" --saida inc
  python topologia_rede.py geom.json --layers "TQ-Condutos,TQ-Condutos Gordura" --tol 0.6 \
      --elos elos.json --saida esg

  --elos: JSON [[[x1,y1],[x2,y2]], ...] com ligações curtas que o snap colapsaria
          (ex.: elo de 0,37 m num cruzamento). Viram trechos explícitos.

Saídas: <saida>_runs.json (trechos com vértices), <saida>_trechos.csv, <saida>_nos.csv.
Confira os CSVs e um gráfico antes de seguir: nó de grau 1 = ponta, 3 = tê, 4 = cruzamento.
"""
import argparse, csv, json, math, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument('entrada')
ap.add_argument('--layers', required=True, help='prefixos de layer separados por vírgula')
ap.add_argument('--tol', type=float, default=0.6, help='tolerância de snap (m)')
ap.add_argument('--min-len', type=float, default=1.0, help='descarta polilinhas mais curtas (símbolos)')
ap.add_argument('--ang', type=float, default=1.0, help='graus abaixo dos quais o vértice é colinear')
ap.add_argument('--elos', help='JSON com elos explícitos')
ap.add_argument('--prefixo', default='T', help='prefixo do nome dos trechos')
ap.add_argument('--saida', default='rede')
a = ap.parse_args()

prefs = [p.strip() for p in a.layers.split(',') if p.strip()]
geom = json.load(open(a.entrada, encoding='utf-8'))
polys = []
for g in geom:
    lay = g.get('layer', g.get('l', ''))
    if not any(lay.startswith(p) for p in prefs):
        continue
    p = [tuple(map(float, q[:2])) for q in g['pts']]
    L = sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    if L > a.min_len:
        polys.append(p)
print(f'polilinhas aceitas: {len(polys)}')


def clean(p):
    """Remove vértices duplicados e colineares."""
    q = [p[0]]
    for v in p[1:]:
        if math.dist(v, q[-1]) > 0.02:
            q.append(v)
    r = [q[0]]
    s = math.sin(math.radians(a.ang))
    for i in range(1, len(q) - 1):
        u = np.subtract(q[i], r[-1]); w = np.subtract(q[i + 1], q[i])
        if abs(u[0] * w[1] - u[1] * w[0]) / (np.linalg.norm(u) * np.linalg.norm(w)) > s:
            r.append(q[i])
    r.append(q[-1])
    return r


polys = [clean(p) for p in polys]


def proj(p, A, B):
    A, B, p = map(np.array, (A, B, p)); ab = B - A
    t = np.clip(np.dot(p - A, ab) / np.dot(ab, ab), 0, 1); q = A + t * ab
    return float(np.linalg.norm(p - q)), tuple(map(float, q))


# Snap: ponta próxima de outra polilinha vai para o vértice (se perto) ou cria vértice (tê).
moves = []
changed = True
while changed:
    changed = False
    for i in range(len(polys)):
        for k in (0, -1):
            p = polys[i][k]
            for j, P in enumerate(polys):
                if j == i:
                    continue
                hit = False
                for s in range(len(P) - 1):
                    dd, q = proj(p, P[s], P[s + 1])
                    if dd < a.tol:
                        if math.dist(q, P[s]) < a.tol: q = P[s]
                        elif math.dist(q, P[s + 1]) < a.tol: q = P[s + 1]
                        else:
                            P.insert(s + 1, q); changed = True
                        if polys[i][k] != q:
                            moves.append((p, q, math.dist(p, q))); polys[i][k] = q; changed = True
                        hit = True
                        break
                if hit: break
            if changed: break
        if changed: break

if a.elos:
    allv = [v for P in polys for v in P]
    for e in json.load(open(a.elos, encoding='utf-8')):
        c1 = min(allv, key=lambda v: math.dist(v, e[0])); c2 = min(allv, key=lambda v: math.dist(v, e[1]))
        if math.dist(c1, c2) > 0.01:
            polys.append([c1, c2]); print(f'elo explícito {c1} -> {c2} ({math.dist(c1, c2):.3f} m)')
        else:
            print(f'AVISO: elo {e} colapsou num único vértice; reduza --tol')

key = lambda p: (round(float(p[0]), 3), round(float(p[1]), 3))
adj = {}
for P in polys:
    for u, v in zip(P, P[1:]):
        if key(u) == key(v):
            continue
        adj.setdefault(key(u), set()).add(key(v)); adj.setdefault(key(v), set()).add(key(u))
deg = {k: len(v) for k, v in adj.items()}
nodes = sorted(k for k, d in deg.items() if d != 2)

seen = set(); runs = []
for n in nodes:
    for m in sorted(adj[n]):
        if (n, m) in seen:
            continue
        path = [n, m]; seen.update({(n, m), (m, n)})
        while deg[path[-1]] == 2:
            nx = [z for z in adj[path[-1]] if z != path[-2]][0]
            seen.update({(path[-1], nx), (nx, path[-1])}); path.append(nx)
        runs.append(path)
# anéis sem nó de grau != 2
for k in adj:
    for m in adj[k]:
        if (k, m) not in seen:
            print('AVISO: há anel fechado sem nós; confira a geometria perto de', k)
            break

tipo = {1: 'ponta', 3: 'tê', 4: 'cruzamento'}
nid = {n: f'N{i + 1:02d}' for i, n in enumerate(nodes)}
tot = 0
with open(f'{a.saida}_trechos.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['trecho', 'no_ini', 'no_fim', 'x_ini', 'y_ini', 'x_fim', 'y_fim', 'vertices', 'comprimento_m'])
    for i, r in enumerate(runs):
        L = sum(math.dist(r[k], r[k + 1]) for k in range(len(r) - 1)); tot += L
        w.writerow([f'{a.prefixo}{i + 1:02d}', nid[r[0]], nid[r[-1]], *r[0], *r[-1], len(r), f'{L:.3f}'])
        if L < a.tol * 1.5:
            print(f'AVISO: {a.prefixo}{i + 1:02d} tem só {L:.2f} m (elo curto? símbolo?)')
with open(f'{a.saida}_nos.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['no', 'x', 'y', 'grau', 'tipo'])
    for n in nodes:
        w.writerow([nid[n], *n, deg[n], tipo.get(deg[n], f'grau {deg[n]}')])
json.dump({'runs': {f'{a.prefixo}{i + 1:02d}': [list(p) for p in r] for i, r in enumerate(runs)},
           'nos': {nid[n]: {'xy': list(n), 'grau': deg[n]} for n in nodes}},
          open(f'{a.saida}_runs.json', 'w', encoding='utf-8'), indent=1)

big = [m for m in moves if m[2] > a.tol * 0.5]
print(f'nós: {len(nodes)} | trechos: {len(runs)} | comprimento total: {tot:.1f} m')
print('graus:', {d: sum(1 for n in nodes if deg[n] == d) for d in sorted(set(deg[n] for n in nodes))})
if big:
    print(f'AVISO: {len(big)} pontas movidas mais de {a.tol * 0.5:.2f} m pelo snap; confira:')
    for p, q, d in big[:10]:
        print(f'   {p} -> {q} ({d:.2f} m)')
