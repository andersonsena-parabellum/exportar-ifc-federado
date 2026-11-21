# -*- coding: utf-8 -*-
"""Biblioteca de extração de redes de DWG QiBuilder (já em UTM), sem Revit.

Fluxo: paredes duplas -> eixos (pares exclusivos, mesma extensão) + linhas únicas (MLINE/PL) -> fundir colineares ->
grafo com as caixas como nós (snap pela face) -> trechos entre nós reais (caixa, tê, ponta) -> sentido (setas) e rótulos.
"""
import math, collections
import numpy as np

DIAM_DESENHO = [0.04, 0.05, 0.075, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40]


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


# ---------------------------------------------------------------- paredes -> eixos
def parear_paredes(segs, dmin=0.03, dmax=0.45, ang=2.0, tol_ponta=0.08):
    """segs: lista de (p0, p1) 2D. Devolve (eixos, sobras).
    eixo = {'p0','p1','d' (espaçamento = Ø de desenho), 'origem': 'par'}; cada parede usada uma vez (guloso pelo melhor par)."""
    S = [(np.asarray(a, float)[:2], np.asarray(b, float)[:2]) for a, b in segs]
    S = [s for s in S if np.linalg.norm(s[1] - s[0]) > 0.02]
    n = len(S)
    U = [unit(b - a) for a, b in S]
    L = [np.linalg.norm(b - a) for a, b in S]
    cand = []
    sa = math.sin(math.radians(ang))
    mid = np.array([(a + b) / 2 for a, b in S]) if n else np.zeros((0, 2))
    for i in range(n):
        a, b = S[i]; u = U[i]
        # vizinhos próximos pelo ponto médio (raio = metade do maior comprimento + dmax)
        r = L[i] / 2 + dmax + 0.5
        js = np.where(np.hypot(*(mid - mid[i]).T) < r + np.array(L) / 2)[0]
        for j in js:
            if j <= i: continue
            if abs(u[0] * U[j][1] - u[1] * U[j][0]) > sa: continue
            c, e = S[j]
            nrm = np.array([-u[1], u[0]])
            d = abs((c - a) @ nrm)
            if not (dmin <= d <= dmax): continue
            # projeções no eixo de i
            t = sorted([(c - a) @ u, (e - a) @ u])
            ov = min(L[i], t[1]) - max(0.0, t[0])
            if ov <= 0.5 * min(L[i], L[j]): continue
            desal = abs(t[0] - 0.0) + abs(t[1] - L[i])          # pontas iguais = 0
            cand.append((desal / max(ov, 1e-6) + 0.2 * abs(L[i] - L[j]) / max(L[i], L[j]), i, j, d, t))
    cand.sort(key=lambda c: c[0])
    usado = set(); eixos = []
    for sc, i, j, d, t in cand:
        if i in usado or j in usado: continue
        a, b = S[i]; u = U[i]; c, e = S[j]
        nrm = np.array([-u[1], u[0]]); lado = (c - a) @ nrm
        t0, t1 = max(0.0, t[0]), min(L[i], t[1])
        # se as pontas diferem muito, usa a união (desenho às vezes recua uma parede)
        if sc < 0.5:
            t0, t1 = min(0.0, t[0]), max(L[i], t[1])
        p0 = a + u * t0 + nrm * lado / 2; p1 = a + u * t1 + nrm * lado / 2
        eixos.append({'p0': p0, 'p1': p1, 'd': d, 'origem': 'par'})
        usado.add(i); usado.add(j)
    sobras = [S[k] for k in range(n) if k not in usado]
    return eixos, sobras


def fundir_colineares(eixos, tol=0.06, ang=3.0, mesmo_d=True):
    """Funde eixos que continuam um ao outro (ponta com ponta, mesma direção)."""
    E = [dict(e) for e in eixos]
    mudou = True
    sa = math.sin(math.radians(ang))
    while mudou:
        mudou = False
        for i in range(len(E)):
            if E[i] is None: continue
            for j in range(len(E)):
                if i == j or E[j] is None: continue
                a, b = E[i], E[j]
                if mesmo_d and abs(a['d'] - b['d']) > 0.015: continue
                ua = unit(a['p1'] - a['p0']); ub = unit(b['p1'] - b['p0'])
                if abs(ua[0] * ub[1] - ua[1] * ub[0]) > sa: continue
                pares = [('p1', 'p0'), ('p1', 'p1'), ('p0', 'p0'), ('p0', 'p1')]
                for ka, kb in pares:
                    if np.linalg.norm(a[ka] - b[kb]) < tol:
                        # nova reta: pontas mais distantes
                        pts = [a['p0'], a['p1'], b['p0'], b['p1']]
                        best = max(((p, q) for p in pts for q in pts), key=lambda pq: np.linalg.norm(pq[0] - pq[1]))
                        E[i] = {'p0': best[0], 'p1': best[1], 'd': (a['d'] + b['d']) / 2, 'origem': a['origem']}
                        E[j] = None; mudou = True
                        break
                if mudou: break
            if mudou: break
    return [e for e in E if e is not None]


def dist_pt_seg(p, a, b):
    v = b - a; L2 = v @ v
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p - a) @ v) / L2))
    q = a + t * v
    return float(np.linalg.norm(p - q)), t, q


# ---------------------------------------------------------------- grafo
class Rede:
    def __init__(self, caixas, snap_caixa=0.75, snap_ponta=0.35, snap_te=0.30):
        """caixas: lista de dict {'id','tipo','c' (xy),'raio' (meia-largura)}."""
        self.cx = caixas
        self.snap_caixa, self.snap_ponta, self.snap_te = snap_caixa, snap_ponta, snap_te
        self.nos = []          # {'id','tipo','c','caixa'}
        self.arestas = []      # {'a','b','pts','d','origem'}

    def _no(self, p, tipo='vert', caixa=None):
        for n in self.nos:
            if caixa is not None and n.get('caixa') == caixa:
                return n['id']
            if caixa is None and n.get('caixa') is None and np.linalg.norm(n['c'] - p) < self.snap_ponta:
                return n['id']
        self.nos.append({'id': len(self.nos), 'tipo': tipo, 'c': np.asarray(p, float), 'caixa': caixa})
        return len(self.nos) - 1

    def monta(self, eixos):
        # 1) pontas na face de caixa
        E = [dict(e) for e in eixos]
        def caixa_de(p):
            best = None
            for c in self.cx:
                d = np.linalg.norm(p - c['c'])
                if d < c['raio'] + c.get('snap', self.snap_caixa) and (best is None or d < best[0]): best = (d, c)
            return best[1] if best else None
        # 2) eixos que atravessam caixa: cortar
        cortados = []
        for e in E:
            pts = [e['p0'], e['p1']]
            cortes = []
            for c in self.cx:
                d, t, q = dist_pt_seg(c['c'], e['p0'], e['p1'])
                L = np.linalg.norm(e['p1'] - e['p0'])
                if c.get('corta', True) and d < c['raio'] and c['raio'] < t * L < L - c['raio']:
                    cortes.append((t, c))
            if not cortes:
                cortados.append(e); continue
            cortes.sort(key=lambda x: x[0])
            ts = [0.0] + [t for t, _ in cortes] + [1.0]
            for k in range(len(ts) - 1):
                p0 = e['p0'] + (e['p1'] - e['p0']) * ts[k]; p1 = e['p0'] + (e['p1'] - e['p0']) * ts[k + 1]
                cortados.append({**e, 'p0': p0, 'p1': p1})
        E = cortados
        # 3) tês: ponta solta sobre o corpo de outro eixo -> dividir o outro
        mudou = True
        while mudou:
            mudou = False
            for i, e in enumerate(E):
                for k in ('p0', 'p1'):
                    p = e[k]
                    if caixa_de(p) is not None: continue
                    for j, f in enumerate(E):
                        if i == j: continue
                        d, t, q = dist_pt_seg(p, f['p0'], f['p1'])
                        L = np.linalg.norm(f['p1'] - f['p0'])
                        if d < self.snap_te and 0.3 < t * L < L - 0.3:
                            e[k] = q
                            E[j] = {**f, 'p1': q}; E.append({**f, 'p0': q})
                            mudou = True; break
                    if mudou: break
                if mudou: break
        # 4) nós
        for e in E:
            ids = []
            for k in ('p0', 'p1'):
                c = caixa_de(e[k])
                ids.append(self._no(c['c'], 'caixa', c['id']) if c else self._no(e[k]))
            if ids[0] == ids[1]: continue
            self.arestas.append({'a': ids[0], 'b': ids[1], 'pts': [e['p0'], e['p1']], 'd': e['d'], 'origem': e.get('origem', ''),
                                 'layer': e.get('layer', '')})
        return self

    def grau(self):
        g = collections.Counter()
        for a in self.arestas: g[a['a']] += 1; g[a['b']] += 1
        return g

    def dedup(self):
        """Arestas repetidas entre os mesmos dois nós (tubo desenhado duas vezes) ficam uma só."""
        # repetida = mesmo par de nós E mesma geometria (ponto médio a < 5 cm); eletrodutos lado a lado num banco ficam
        visto = collections.defaultdict(list); out = []
        for a in self.arestas:
            k = frozenset((a['a'], a['b']))
            m = (np.asarray(a['pts'][0]) + np.asarray(a['pts'][-1])) / 2
            if any(np.linalg.norm(m - q) < 0.05 for q in visto[k]): self.duplicadas = getattr(self, 'duplicadas', 0) + 1; continue
            visto[k].append(m); out.append(a)
        self.arestas = out
        return self

    def trechos(self):
        """Une arestas em série (nós de grau 2 que não são caixa) em trechos nó real -> nó real."""
        self.dedup()
        g = self.grau()
        adj = collections.defaultdict(list)
        for k, a in enumerate(self.arestas):
            adj[a['a']].append(k); adj[a['b']].append(k)
        real = lambda n: self.nos[n]['caixa'] is not None or g[n] != 2
        usado = set(); out = []
        for k, a in enumerate(self.arestas):
            if k in usado: continue
            # anda para trás até nó real
            cad = [k]; usado.add(k)
            for lado in ('a', 'b'):
                n = a[lado]; prev = k
                while not real(n):
                    nxt = [m for m in adj[n] if m != prev and m not in usado]
                    if not nxt: break
                    m = nxt[0]; usado.add(m)
                    if lado == 'a': cad.insert(0, m)
                    else: cad.append(m)
                    am = self.arestas[m]; n = am['b'] if am['a'] == n else am['a']; prev = m
            # ordena os pontos da cadeia
            pts, nos = self._encadeia(cad)
            ds = [self.arestas[m]['d'] for m in cad]
            out.append({'nos': (nos[0], nos[-1]), 'pts': pts, 'arestas': cad, 'd': float(np.median(ds)),
                        'L': float(sum(np.linalg.norm(np.subtract(pts[i + 1], pts[i])) for i in range(len(pts) - 1))),
                        'layers': sorted({self.arestas[m]['layer'] for m in cad})})
        return out

    def _encadeia(self, cad):
        if len(cad) == 1:
            a = self.arestas[cad[0]]
            return [self.nos[a['a']]['c'] if self.nos[a['a']]['caixa'] is not None else a['pts'][0],
                    self.nos[a['b']]['c'] if self.nos[a['b']]['caixa'] is not None else a['pts'][1]], [a['a'], a['b']]
        # descobre a ordem dos nós
        a0, a1 = self.arestas[cad[0]], self.arestas[cad[1]]
        ini = a0['a'] if a0['a'] not in (a1['a'], a1['b']) else a0['b']
        nos = [ini]; cur = ini
        for m in cad:
            am = self.arestas[m]; cur = am['b'] if am['a'] == cur else am['a']; nos.append(cur)
        pts = [self.nos[n]['c'] for n in nos]
        return pts, nos


# ---------------------------------------------------------------- rótulos e setas
def sentido_por_setas(trecho_pts, setas, tol=0.35, ang=15.0):
    """setas: lista de (p0, p1). Devolve +1 (do 1º ao último ponto), -1, ou 0 (sem seta)."""
    voto = 0
    ca = math.cos(math.radians(ang))
    for s0, s1 in setas:
        m = (s0 + s1) / 2; us = unit(s1 - s0)
        for i in range(len(trecho_pts) - 1):
            a, b = np.asarray(trecho_pts[i]), np.asarray(trecho_pts[i + 1])
            d, t, q = dist_pt_seg(m, a, b)
            if d < tol:
                c = us @ unit(b - a)
                if abs(c) > ca: voto += 1 if c > 0 else -1
                break
    return int(np.sign(voto)), abs(voto)


def _dir_ponta(R, n):
    """Direção (unitária) do tubo que chega ao nó n, apontando para fora (do tubo para a ponta)."""
    for a in R.arestas:
        if a['a'] == n: return unit(np.asarray(R.nos[n]['c']) - np.asarray(R.nos[a['b']]['c']))
        if a['b'] == n: return unit(np.asarray(R.nos[n]['c']) - np.asarray(R.nos[a['a']]['c']))
    return np.zeros(2)


def ligar_pontas(R, gap=0.9, gap_caixa=1.2, ang_col=25.0):
    """O desenho não encosta: liga pontas soltas (grau 1, fora de caixa) a
    1) outra ponta solta colinear a < gap; 2) caixa a < gap_caixa da face; 3) corpo de outro tubo a < gap (tê).
    As ligações entram como arestas com origem 'ligação presumida'."""
    nov = 0
    def soltas():
        g = R.grau()
        return [n['id'] for n in R.nos if n['caixa'] is None and g[n['id']] == 1]
    # 1) ponta-ponta colinear
    usados = set()
    S = soltas()
    for i in S:
        if i in usados: continue
        pi = np.asarray(R.nos[i]['c']); ui = _dir_ponta(R, i)
        best = None
        for j in S:
            if j == i or j in usados: continue
            pj = np.asarray(R.nos[j]['c']); d = np.linalg.norm(pj - pi)
            if d > gap or d < 1e-6: continue
            uj = _dir_ponta(R, j)
            v = unit(pj - pi)
            if ui @ v > math.cos(math.radians(ang_col)) and uj @ (-v) > math.cos(math.radians(ang_col)):
                if best is None or d < best[0]: best = (d, j)
        if best:
            j = best[1]
            da = [a for a in R.arestas if i in (a['a'], a['b'])][0]
            R.arestas.append({'a': i, 'b': j, 'pts': [R.nos[i]['c'], R.nos[j]['c']], 'd': da['d'], 'origem': 'ligação presumida', 'layer': da.get('layer', '')})
            usados.update((i, j)); nov += 1
    def vizinhanca(i, raio=3.0):
        """Arestas e nós a até `raio` m de i pelo grafo (o próprio tubo): não servem de alvo da ligação."""
        adj = collections.defaultdict(list)
        for k, a in enumerate(R.arestas):
            L = float(np.linalg.norm(np.asarray(R.nos[a['a']]['c']) - np.asarray(R.nos[a['b']]['c'])))
            adj[a['a']].append((a['b'], L, k)); adj[a['b']].append((a['a'], L, k))
        dist = {i: 0.0}; fila = [i]; ks = set()
        while fila:
            n = fila.pop()
            for m, L, k in adj[n]:
                if dist[n] + L <= raio:
                    ks.add(k)
                    if m not in dist or dist[n] + L < dist[m]:
                        dist[m] = dist[n] + L; fila.append(m)
        return ks, set(dist)
    # 2) ponta perto de caixa
    for i in soltas():
        pi = np.asarray(R.nos[i]['c'])
        ks, ns = vizinhanca(i)
        best = None
        for c in R.cx:
            nc = next((n['id'] for n in R.nos if n['caixa'] == c['id']), None)
            if nc is not None and nc in ns: continue
            d = np.linalg.norm(np.asarray(c['c']) - pi) - c['raio']
            if d < gap_caixa and (best is None or d < best[0]): best = (d, c)
        if best:
            c = best[1]
            n = R._no(c['c'], 'caixa', c['id'])
            da = [a for a in R.arestas if i in (a['a'], a['b'])][0]
            R.arestas.append({'a': i, 'b': n, 'pts': [pi, np.asarray(c['c'])], 'd': da['d'], 'origem': 'ligação presumida (caixa)', 'layer': da.get('layer', '')})
            nov += 1
    # 3) ponta perto do corpo de outro tubo (tê)
    for i in soltas():
        pi = np.asarray(R.nos[i]['c'])
        ks, ns = vizinhanca(i)
        best = None
        for k, a in enumerate(R.arestas):
            if i in (a['a'], a['b']) or k in ks: continue
            pa, pb = np.asarray(R.nos[a['a']]['c']), np.asarray(R.nos[a['b']]['c'])
            d, t, q = dist_pt_seg(pi, pa, pb)
            L = np.linalg.norm(pb - pa)
            if d < gap and (best is None or d < best[0]): best = (d, k, t, q, L)
        if best:
            d, k, t, q, L = best
            a = R.arestas[k]
            if t * L < 0.15: alvo = a['a']
            elif t * L > L - 0.15: alvo = a['b']
            else:
                R.nos.append({'id': len(R.nos), 'tipo': 'te', 'c': q, 'caixa': None}); alvo = len(R.nos) - 1
                R.arestas[k] = {**a, 'b': alvo, 'pts': [a['pts'][0], q]}
                R.arestas.append({**a, 'a': alvo, 'pts': [q, a['pts'][1]]})
            da = [x for x in R.arestas if i in (x['a'], x['b'])][0]
            R.arestas.append({'a': i, 'b': alvo, 'pts': [pi, np.asarray(R.nos[alvo]['c'])], 'd': da['d'], 'origem': 'ligação presumida (tê)', 'layer': da.get('layer', '')})
            nov += 1
    return nov
