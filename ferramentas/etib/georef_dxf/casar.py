# -*- coding: utf-8 -*-
"""Casamento disciplina -> base por blocos de mesmo nome + verificação geométrica (pontos sobre linhas).

Funções:
  cache_load(dxf)               -> geometria expandida (dxfgeo), com cache pickle ao lado do DXF
  cand_blocos(A, B)             -> transformações candidatas (rotação + translação) de cada bloco único comum
  agrupar(cands)                -> grupos de candidatos coincidentes (o maior é a transformação)
  amostrar(g, filtro, passo)    -> pontos ao longo dos segmentos (filtro por layer/caminho)
  aderencia(pts, alvo, T, tols) -> fração de pontos da disciplina (transformados) a menos de tol de alguma linha da base
  icp(pts_src, pts_dst, T0)     -> refina a transformação rígida (ponto-a-ponto, grade hash)
"""
import math
import os
import pickle
import collections
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxfgeo  # noqa: E402
import numpy as np  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8")


def cache_load(dxf, skip_layers=None):
    pk = dxf + '.pkl'
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(dxf):
        with open(pk, 'rb') as f:
            return pickle.load(f)
    g = dxfgeo.load(dxf, skip_layers)
    g.pop('blocks', None)
    with open(pk, 'wb') as f:
        pickle.dump(g, f)
    return g


def por_nome(g):
    d = collections.defaultdict(list)
    for i in g['inserts']:
        d[i['name']].append(i)
    return d


def cand_blocos(A, B, so_unicos=True, ignorar_anonimos=True):
    a, b = por_nome(A), por_nome(B)
    out = []
    for nome in set(a) & set(b):
        if ignorar_anonimos and nome.startswith('*'):
            continue
        la, lb = a[nome], b[nome]
        if so_unicos and (len(la) != 1 or len(lb) != 1):
            continue
        for x in la:
            for y in lb:
                if abs(x['s'] - y['s']) > 1e-4 or x['mir'] != y['mir']:
                    continue
                dth = (y['rot'] - x['rot'] + 180) % 360 - 180
                c, s = math.cos(math.radians(dth)), math.sin(math.radians(dth))
                tx = y['p'][0] - (c*x['p'][0] - s*x['p'][1])
                ty = y['p'][1] - (s*x['p'][0] + c*x['p'][1])
                out.append({'nome': nome, 'dth': dth, 'tx': tx, 'ty': ty, 'a': x, 'b': y})
    return out


def agrupar(cands, tol_ang=0.01, tol_t=0.05):
    grupos = []
    for c in sorted(cands, key=lambda c: c['nome']):
        for g in grupos:
            r = g[0]
            if abs(c['dth'] - r['dth']) < tol_ang and math.hypot(c['tx'] - r['tx'], c['ty'] - r['ty']) < tol_t:
                g.append(c)
                break
        else:
            grupos.append([c])
    return sorted(grupos, key=len, reverse=True)


def T_from(dth_deg, tx, ty):
    return (math.radians(dth_deg), tx, ty)


def aplicar(T, P):
    th, tx, ty = T
    c, s = math.cos(th), math.sin(th)
    P = np.asarray(P, float)
    return np.column_stack([c*P[:, 0] - s*P[:, 1] + tx, s*P[:, 0] + c*P[:, 1] + ty])


def amostrar(g, filtro=None, passo=0.10, max_seg=200.0):
    pts = []
    for s in g['segs']:
        if filtro and not filtro(s):
            continue
        p = s['p'] + ([s['p'][0]] if s['closed'] else [])
        for (x1, y1, *_), (x2, y2, *_) in zip(p[:-1], p[1:]):
            L = math.hypot(x2 - x1, y2 - y1)
            if L < 1e-9 or L > max_seg:
                continue
            k = max(1, int(L / passo))
            for j in range(k + 1):
                t = j / k
                pts.append((x1 + (x2 - x1)*t, y1 + (y2 - y1)*t))
    return np.array(pts) if pts else np.zeros((0, 2))


class Grade:
    """Vizinho mais próximo vetorizado (numpy), em grade multirresolução. Pontos deduplicados a 1 cm."""
    NIV = ((0.1, 24), (0.25, 24), (0.6, 24))

    def __init__(self, P, cel=None, dedup=0.01):
        P = np.asarray(P, float)
        self.o = P.min(0) - 2.0
        q = np.unique(np.round((P - self.o) / dedup).astype(np.int64), axis=0)
        self.P = q * dedup + self.o
        self.niv = [self._monta(c, M) for c, M in self.NIV]

    def _monta(self, cel, M):
        ij = np.floor((self.P - self.o) / cel).astype(np.int64)
        key = ij[:, 0] * 10_000_000 + ij[:, 1]
        order = np.argsort(key, kind='stable')
        uk, st, cnt = np.unique(key[order], return_index=True, return_counts=True)
        idx = np.empty((len(uk), M), np.int64)
        for m in range(M):
            idx[:, m] = order[st + (m * cnt) // M]
        return cel, uk, self.P[idx], idx

    def consulta(self, Q, r):
        Q = np.asarray(Q, float)
        cel, uk, dense, idx = next((n for n in self.niv if n[0] >= r), self.niv[-1])
        ij = np.floor((Q - self.o) / cel).astype(np.int64)
        best = np.full(len(Q), np.inf)
        bi = np.full(len(Q), -1, np.int64)
        ar = np.arange(len(Q))
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                k = (ij[:, 0] + di) * 10_000_000 + ij[:, 1] + dj
                pos = np.clip(np.searchsorted(uk, k), 0, len(uk) - 1)
                ok = uk[pos] == k
                d = np.hypot(dense[pos, :, 0] - Q[:, None, 0], dense[pos, :, 1] - Q[:, None, 1])
                d[~ok] = np.inf
                m = np.argmin(d, axis=1)
                dm = d[ar, m]
                up = dm < best
                best[up] = dm[up]
                bi[up] = idx[pos[up], m[up]]
        fora = best > r
        best[fora] = np.inf
        bi[fora] = -1
        return best, bi


def aderencia(pts_src, grade_dst, T, tols=(0.01, 0.02, 0.05, 0.10, 0.30)):
    Q = aplicar(T, pts_src)
    ds, _ = grade_dst.consulta(Q, max(tols))
    return {t: float(np.mean(ds <= t)) for t in tols}, ds


def kabsch(A, B):
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    D = np.diag([1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    th = math.atan2(R[1, 0], R[0, 0])
    t = cb - R @ ca
    return th, t[0], t[1]


def icp(pts_src, grade_dst, T0, raios=(0.5, 0.2, 0.1, 0.05, 0.03, 0.02), it_por_raio=5):
    T = T0
    n = 0
    for r in raios:
        for _ in range(it_por_raio):
            Q = aplicar(T, pts_src)
            d, j = grade_dst.consulta(Q, r)
            ok = j >= 0
            n = int(ok.sum())
            if n < 10:
                return T, 0
            T = kabsch(pts_src[ok], grade_dst.P[j[ok]])
    return T, n


def segmentos(g, filtro=None, d=(0.0, 0.0), max_seg=500.0):
    """Segmentos 2D (n,4) das primitivas que passam no filtro, deslocados por d."""
    S = []
    for s in g['segs']:
        if filtro and not filtro(s):
            continue
        p = s['p'] + ([s['p'][0]] if s['closed'] else [])
        for (x1, y1, *_), (x2, y2, *_) in zip(p[:-1], p[1:]):
            L = math.hypot(x2 - x1, y2 - y1)
            if 1e-6 < L < max_seg:
                S.append((x1 + d[0], y1 + d[1], x2 + d[0], y2 + d[1]))
    return np.array(S) if S else np.zeros((0, 4))


class GradeSeg:
    """Distância exata ponto-segmento, vetorizada: cada segmento é registrado nas células que atravessa."""
    NIV = ((0.25, 64), (0.6, 64), (2.0, 64))

    def __init__(self, S):
        self.S = np.asarray(S, float)
        self.o = np.minimum(self.S[:, :2].min(0), self.S[:, 2:].min(0)) - 2.0
        self.niv = [self._monta(c, M) for c, M in self.NIV]

    def _monta(self, cel, M):
        S = self.S
        L = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])
        k = np.maximum(1, np.ceil(L / (cel / 3)).astype(np.int64))
        sid = np.repeat(np.arange(len(S)), k + 1)
        offs = np.repeat(np.cumsum(k + 1) - (k + 1), k + 1)
        t = (np.arange(len(sid)) - offs) / np.repeat(k, k + 1)
        x = S[sid, 0] + (S[sid, 2] - S[sid, 0]) * t
        y = S[sid, 1] + (S[sid, 3] - S[sid, 1]) * t
        ij0 = np.floor((x - self.o[0]) / cel).astype(np.int64)
        ij1 = np.floor((y - self.o[1]) / cel).astype(np.int64)
        key = ij0 * 10_000_000 + ij1
        par = np.unique(np.column_stack([key, sid]), axis=0)
        uk, st, cnt = np.unique(par[:, 0], return_index=True, return_counts=True)
        idx = np.empty((len(uk), M), np.int64)
        for m in range(M):
            idx[:, m] = par[st + (m * cnt) // M, 1]
        self.cheias = int((cnt > M).sum())
        return cel, uk, idx

    def consulta(self, Q, r):
        """-> distância, ponto mais próximo (n,2); inf onde > r."""
        Q = np.asarray(Q, float)
        cel, uk, idx = next((n for n in self.niv if n[0] >= r), self.niv[-1])
        ij = np.floor((Q - self.o) / cel).astype(np.int64)
        best = np.full(len(Q), np.inf)
        bp = np.zeros((len(Q), 2))
        ar = np.arange(len(Q))
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                kk = (ij[:, 0] + di) * 10_000_000 + ij[:, 1] + dj
                pos = np.clip(np.searchsorted(uk, kk), 0, len(uk) - 1)
                ok = uk[pos] == kk
                if not ok.any():
                    continue
                qi = ar[ok]
                sg = self.S[idx[pos[ok]]]                       # (m, M, 4)
                ax, ay = sg[..., 0], sg[..., 1]
                vx, vy = sg[..., 2] - ax, sg[..., 3] - ay
                px, py = Q[qi, 0][:, None], Q[qi, 1][:, None]
                tt = np.clip(((px - ax) * vx + (py - ay) * vy) / np.maximum(vx * vx + vy * vy, 1e-18), 0, 1)
                cx, cy = ax + tt * vx, ay + tt * vy
                d = np.hypot(px - cx, py - cy)
                m = np.argmin(d, axis=1)
                dm = d[np.arange(len(qi)), m]
                up = dm < best[qi]
                best[qi[up]] = dm[up]
                bp[qi[up], 0] = cx[np.arange(len(qi)), m][up]
                bp[qi[up], 1] = cy[np.arange(len(qi)), m][up]
        fora = best > r
        best[fora] = np.inf
        return best, bp


def aderencia_seg(pts_src, gs, T, tols=(0.005, 0.01, 0.02, 0.05, 0.10, 0.30)):
    d, _ = gs.consulta(aplicar(T, pts_src), max(tols))
    return {t: float(np.mean(d <= t)) for t in tols}, d


def icp_seg(pts_src, gs, T0, raios=(0.25, 0.10, 0.03, 0.01), it_por_raio=4):
    T = T0
    n = 0
    for r in raios:
        for _ in range(it_por_raio):
            d, cp = gs.consulta(aplicar(T, pts_src), r)
            ok = np.isfinite(d)
            n = int(ok.sum())
            if n < 10:
                return T, 0
            T = kabsch(pts_src[ok], cp[ok])
    return T, n
