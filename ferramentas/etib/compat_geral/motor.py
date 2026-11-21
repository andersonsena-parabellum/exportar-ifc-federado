# -*- coding: utf-8 -*-
"""Motor de interferências reutilizável (R02): leitura da geometria exportada e avaliação incremental de folgas.
Usado por solucoes.py (teste de soluções) e pelo gerador do relatório."""
import os, math, collections
import numpy as np
G = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo"
FOLGA = 0.20; TOL = -0.002
NAO = {('EST', 'IMP'), ('IMP', 'EST'), ('EST', 'EST'), ('IMP', 'IMP')}
SO_COL = {frozenset(('ELE', 'TEL'))}


def disc_seg(f, r):
    if f == 'HS': return 'AF' if r[4].startswith('Água') else 'ESG'
    if f == 'INC': return 'SDAI' if (r[2] == 'Conduites' or 'SDAI' in r[3]) else 'INC'
    if f == 'ELE': return 'TEL' if r[3].startswith('TEL') else 'ELE'
    return f


def disc_mesh(f, r):
    nome, trecho = r[3], r[4]
    if f == 'HS': return 'AF' if nome.startswith('AF') else 'ESG'
    if f == 'INC': return 'SDAI' if 'SDAI' in nome else 'INC'
    if f == 'ELE': return 'TEL' if trecho.startswith('CF') else 'ELE'
    if f == 'EST': return 'IMP' if '-IMP_' in r[4] else 'EST'
    return f


def carregar(g=G):
    SEG, MESH = [], []
    for f in ('HS', 'DRN', 'INC', 'ELE'):
        for l in open(os.path.join(g, f + '_segs.tsv'), encoding='utf-8'):
            r = l.rstrip('\n').split('\t')
            if len(r) < 13: continue
            a = np.array(list(map(float, r[7:10]))); b = np.array(list(map(float, r[10:13])))
            if np.linalg.norm(b - a) < 1e-4: continue
            SEG.append(dict(k='S', disc=disc_seg(f, r), id=r[1], cat=r[2], tipo=r[3], sis=r[4], trecho=r[5] or r[4], de=float(r[6]), a=a, b=b, a0=a.copy(), b0=b.copy(), dz=0.0))
    for f in ('HS', 'DRN', 'INC', 'ELE', 'CNT', 'EST'):
        for l in open(os.path.join(g, f + '_mesh.tsv'), encoding='utf-8'):
            r = l.rstrip('\n').split('\t')
            if len(r) < 8: continue
            if f == 'EST' and 'PISO-TÁTIL' in r[3]: continue
            v = np.array(r[7].split(','), dtype=float).reshape(-1, 3, 3)
            bloco = r[1].split(':')[0] if f == 'EST' else ''
            MESH.append(dict(k='M', disc=disc_mesh(f, r), id=r[1], cat=r[2], nome=r[3], trecho=r[4] if f != 'EST' else (bloco + ' ' + r[3].split(' : ')[0]),
                             desc=r[5] if f != 'EST' else r[4], tri=v, lo=v.reshape(-1, 3).min(0), hi=v.reshape(-1, 3).max(0), bloco=bloco))
    return SEG, MESH


def segdist(p1, q1, p2, q2):
    d1 = q1 - p1; d2 = q2 - p2; r = p1 - p2; a = d1 @ d1; e = d2 @ d2; f = d2 @ r; c = d1 @ r; b = d1 @ d2; den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-12 else 0.0
    t = (b * s + f) / e if e > 1e-12 else 0
    if t < 0: t = 0; s = np.clip(-c / a, 0, 1)
    elif t > 1: t = 1; s = np.clip((b - c) / a, 0, 1)
    P = p1 + d1 * s; Q = p2 + d2 * t
    return float(np.linalg.norm(P - Q)), (P + Q) / 2


def pt_tri_dist(P, T):
    A = T[:, 0][None]; B = T[:, 1][None]; C = T[:, 2][None]; p = P[:, None, :]
    ab = B - A; ac = C - A; ap = p - A
    d1 = (ab * ap).sum(-1); d2 = (ac * ap).sum(-1)
    bp = p - B; d3 = (ab * bp).sum(-1); d4 = (ac * bp).sum(-1)
    cp = p - C; d5 = (ab * cp).sum(-1); d6 = (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-18, 1e-18, den)
    v = vb / den; w = vc / den
    res = A + ab * v[..., None] + ac * w[..., None]
    def setr(mask, val):
        nonlocal res
        res = np.where(mask[..., None], val, res)
    setr((d1 <= 0) & (d2 <= 0), np.broadcast_to(A, res.shape))
    setr((d3 >= 0) & (d4 <= d3), np.broadcast_to(B, res.shape))
    setr((d6 >= 0) & (d5 <= d6), np.broadcast_to(C, res.shape))
    with np.errstate(divide='ignore', invalid='ignore'):
        vv = d1 / (d1 - d3); setr((vc <= 0) & (d1 >= 0) & (d3 <= 0), A + ab * np.nan_to_num(vv)[..., None])
        ww = d2 / (d2 - d6); setr((vb <= 0) & (d2 >= 0) & (d6 <= 0), A + ac * np.nan_to_num(ww)[..., None])
        uu = (d4 - d3) / ((d4 - d3) + (d5 - d6)); setr((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), B + (C - B) * np.nan_to_num(uu)[..., None])
    return np.linalg.norm(p - res, axis=-1)


RAY = np.array([0.8726, 0.3864, 0.2987]); RAY /= np.linalg.norm(RAY)
def inside(P, T):
    v0 = T[:, 0][None]; e1 = (T[:, 1] - T[:, 0])[None]; e2 = (T[:, 2] - T[:, 0])[None]
    h = np.cross(RAY, e2); a = (e1 * h).sum(-1)
    ok = np.abs(a) > 1e-12; f = np.where(ok, 1.0 / np.where(ok, a, 1), 0)
    s = P[:, None, :] - v0; u = f * (s * h).sum(-1)
    q = np.cross(s, e1); v = f * (q * RAY).sum(-1); t = f * (e2 * q).sum(-1)
    hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > 1e-9)
    return (hit.sum(1) % 2) == 1


def signed(P, M):
    d = pt_tri_dist(P, M['tri']).min(1)
    return np.where(inside(P, M['tri']), -d, d)


def par_ok(d1, d2): return d1 != d2 and (d1, d2) not in NAO


class Indice:
    """Grade 2D para pré-filtro. Os segmentos móveis são consultados com a geometria atual."""
    CELL = 5.0
    def __init__(self, SEG, MESH):
        self.SEG, self.MESH = SEG, MESH
        self.gS = collections.defaultdict(set); self.gM = collections.defaultdict(list)
        for i, s in enumerate(SEG): self._addS(i)
        for j, M in enumerate(MESH):
            for c in self.cells(M['lo'] - FOLGA, M['hi'] + FOLGA): self.gM[c].append(j)
    def cells(self, lo, hi):
        C = self.CELL
        return [(i, j) for i in range(int(lo[0] // C), int(hi[0] // C) + 1) for j in range(int(lo[1] // C), int(hi[1] // C) + 1)]
    def bb(self, s, m=FOLGA):
        r = s['de'] / 2 + m; return np.minimum(s['a'], s['b']) - r, np.maximum(s['a'], s['b']) + r
    def _addS(self, i):
        lo, hi = self.bb(self.SEG[i])
        for c in self.cells(lo, hi): self.gS[c].add(i)
    def vizinhos(self, s):
        lo, hi = self.bb(s); si, mj = set(), set()
        for c in self.cells(lo, hi): si |= self.gS.get(c, set()); mj |= set(self.gM.get(c, ()))
        return si, mj, lo, hi


def avaliar_seg(i, IDX, folga=FOLGA):
    """Folgas < folga do segmento i contra tudo. Retorna lista de (tipo, j, folga, ponto)."""
    SEG, MESH = IDX.SEG, IDX.MESH; A = SEG[i]; out = []
    si, mj, lo, hi = IDX.vizinhos(A)
    for j in si:
        if j == i: continue
        B = SEG[j]
        if not par_ok(A['disc'], B['disc']): continue
        blo, bhi = IDX.bb(B, 0)
        if np.any(lo > bhi) or np.any(blo > hi): continue
        d, pt = segdist(A['a'], A['b'], B['a'], B['b']); g = d - (A['de'] + B['de']) / 2
        if g < folga:
            if frozenset((A['disc'], B['disc'])) in SO_COL and g >= TOL: continue
            out.append(('S', j, g, pt))
    P = None
    for j in mj:
        M = MESH[j]
        if not par_ok(A['disc'], M['disc']): continue
        if np.any(lo > M['hi']) or np.any(M['lo'] > hi): continue
        if P is None:
            L = np.linalg.norm(A['b'] - A['a']); n = max(2, int(math.ceil(L / 0.05)) + 1)
            P = A['a'] + (A['b'] - A['a']) * np.linspace(0, 1, n)[:, None]
        m = np.all((P >= M['lo'] - A['de'] / 2 - folga) & (P <= M['hi'] + A['de'] / 2 + folga), axis=1)
        if not m.any(): continue
        sd = signed(P[m], M) - A['de'] / 2; k = int(sd.argmin())
        if sd[k] < folga:
            if frozenset((A['disc'], M['disc'])) in SO_COL and sd[k] >= TOL: continue
            out.append(('M', j, float(sd[k]), P[m][k]))
    return out


def avaliar_mesh(j, IDX, folga=FOLGA):
    """Folgas < folga do sólido j (caixa móvel) contra tubos e outros sólidos."""
    SEG, MESH = IDX.SEG, IDX.MESH; M = MESH[j]; out = []
    lo, hi = M['lo'] - folga, M['hi'] + folga
    si, mj = set(), set()
    for c in IDX.cells(lo, hi): si |= IDX.gS.get(c, set()); mj |= set(IDX.gM.get(c, ()))
    for i in si:
        A = SEG[i]
        if not par_ok(A['disc'], M['disc']): continue
        alo, ahi = IDX.bb(A, 0)
        if np.any(lo > ahi) or np.any(alo > hi): continue
        L = np.linalg.norm(A['b'] - A['a']); n = max(2, int(math.ceil(L / 0.05)) + 1)
        P = A['a'] + (A['b'] - A['a']) * np.linspace(0, 1, n)[:, None]
        m = np.all((P >= M['lo'] - A['de'] / 2 - folga) & (P <= M['hi'] + A['de'] / 2 + folga), axis=1)
        if not m.any(): continue
        sd = signed(P[m], M) - A['de'] / 2; k = int(sd.argmin())
        if sd[k] < folga and not (frozenset((A['disc'], M['disc'])) in SO_COL and sd[k] >= TOL): out.append(('S', i, float(sd[k]), P[m][k]))
    if 'samp' not in M: M['samp'] = amostras_mesh(M)
    for jj in mj:
        if jj == j: continue
        B = MESH[jj]
        if not par_ok(M['disc'], B['disc']) or np.any(lo > B['hi']) or np.any(B['lo'] > hi): continue
        best = 9e9
        for X, Y in ((M, B), (B, M)):
            if 'samp' not in X: X['samp'] = amostras_mesh(X)
            P = X['samp']; mm = np.all((P >= Y['lo'] - folga) & (P <= Y['hi'] + folga), axis=1)
            if mm.any(): best = min(best, float(signed(P[mm], Y).min()))
        if best < folga and not (frozenset((M['disc'], B['disc'])) in SO_COL and best >= TOL): out.append(('M', jj, best, (M['lo'] + M['hi']) / 2))
    return out


def amostras_mesh(M, step=0.15):
    T = M['tri']; pts = [T.reshape(-1, 3), T.mean(1)]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    for i in np.where(area > step * step)[0]:
        k = int(min(12, math.ceil(math.sqrt(area[i]) / step)))
        A, B, C = T[i]; pts.append(np.array([A + (B - A) * (a / k) + (C - A) * (b / k) for a in range(k + 1) for b in range(k + 1 - a)]))
    return np.unique(np.round(np.vstack(pts), 4), axis=0)


def mover_mesh(j, dxy, IDX):
    """Desloca o sólido j em planta (em relação à posição original) e reindexa."""
    M = IDX.MESH[j]
    if 'tri0' not in M: M['tri0'] = M['tri'].copy()
    for c in IDX.cells(M['lo'] - FOLGA, M['hi'] + FOLGA):
        if j in IDX.gM[c]: IDX.gM[c].remove(j)
    off = np.array([dxy[0], dxy[1], 0.0])
    M['tri'] = M['tri0'] + off; M['lo'] = M['tri'].reshape(-1, 3).min(0); M['hi'] = M['tri'].reshape(-1, 3).max(0); M['dxy'] = (float(dxy[0]), float(dxy[1]))
    M.pop('samp', None)
    for c in IDX.cells(M['lo'] - FOLGA, M['hi'] + FOLGA): IDX.gM[c].append(j)


def mover(i, dz, IDX, dxy=None):
    """Aprofunda o segmento i de dz (m) e, opcionalmente, desloca em planta (dxy) em relação à posição original; reindexa."""
    s = IDX.SEG[i]
    if dxy is None: dxy = s.get('dxy', (0.0, 0.0))
    mudou_xy = tuple(dxy) != tuple(s.get('dxy', (0.0, 0.0)))
    if mudou_xy:
        lo, hi = IDX.bb(s)
        for c in IDX.cells(lo, hi): IDX.gS[c].discard(i)
    off = np.array([dxy[0], dxy[1], -dz])
    s['a'] = s['a0'] + off; s['b'] = s['b0'] + off; s['dz'] = dz; s['dxy'] = (float(dxy[0]), float(dxy[1]))
    if mudou_xy: IDX._addS(i)
