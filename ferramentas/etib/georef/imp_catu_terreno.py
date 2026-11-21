# -*- coding: utf-8 -*-
"""ETIB Catu — terreno do IMP as built (lido no Revit em 19/10/2026 por imp_catu_ler.cs; triângulos em work/CATU/imp/).
1. Rasteriza a superfície de cima (pisos > subdivisões/terreno) numa grade de 1 m: work/CATU/imp/imp_raster_1m.npz.
2. Confere a posição em planta (contorno dos pisos × linhas dos blocos da SIT _GEO) e a cota (CT das caixas do ESG/DRE,
   níveis escritos na SIT e pontos do TOP-001 fora da obra).
Uso: .venv/Scripts/python.exe -X utf8 georef/imp_catu_terreno.py"""
import os, sys, csv, re, collections
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from catu_comum import carrega          # noqa: E402

IMP = os.path.join(AQUI, 'work', 'CATU', 'imp')
F3 = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\FASE3_COTAS_2026-10-18'
BOX = (567600.0, 8634520.0, 567820.0, 8634730.0)
OUT = os.path.join(IMP, 'imp_raster_1m.npz')


def ler(fn):
    R = []
    for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
        a, b, c = [np.array(list(map(float, r[k].split(',')))) for k in ('a', 'b', 'c')]
        R.append((r['tag'], r['id'], np.array([a, b, c]), float(r['nz'])))
    return R


def raster(tris, X, Y):
    Z = np.full(X.shape, np.nan)
    x0, y0 = X[0, 0], Y[0, 0]; dx = X[0, 1] - X[0, 0]; dy = Y[1, 0] - Y[0, 0]
    for A in tris:
        p = A[:, :2]
        i0 = max(0, int(np.floor((p[:, 0].min() - x0) / dx))); i1 = min(X.shape[1] - 1, int(np.ceil((p[:, 0].max() - x0) / dx)))
        j0 = max(0, int(np.floor((p[:, 1].min() - y0) / dy))); j1 = min(X.shape[0] - 1, int(np.ceil((p[:, 1].max() - y0) / dy)))
        if i1 < i0 or j1 < j0: continue
        xs = X[j0:j1 + 1, i0:i1 + 1]; ys = Y[j0:j1 + 1, i0:i1 + 1]
        v0 = p[1] - p[0]; v1 = p[2] - p[0]; den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12: continue
        wx = xs - p[0, 0]; wy = ys - p[0, 1]
        u = (wx * v1[1] - v1[0] * wy) / den; v = (v0[0] * wy - wx * v0[1]) / den
        m = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
        if not m.any(): continue
        z = A[0, 2] + u * (A[1, 2] - A[0, 2]) + v * (A[2, 2] - A[0, 2])
        blk = Z[j0:j1 + 1, i0:i1 + 1]
        blk[m] = np.where(np.isnan(blk[m]), z[m], np.maximum(blk[m], z[m]))
    return Z


def interp(npz=OUT):
    D = np.load(npz); xs = D['X'][0]; ys = D['Y'][:, 0]; Z = D['Z']; dx = xs[1] - xs[0]; dy = ys[1] - ys[0]

    def f(P):
        P = np.atleast_2d(np.asarray(P, float))
        fx = (P[:, 0] - xs[0]) / dx; fy = (P[:, 1] - ys[0]) / dy
        i = np.floor(fx).astype(int); j = np.floor(fy).astype(int)
        ok = (i >= 0) & (j >= 0) & (i < len(xs) - 1) & (j < len(ys) - 1)
        out = np.full(len(P), np.nan)
        i, j, tx, ty = i[ok], j[ok], fx[ok] - i[ok], fy[ok] - j[ok]
        out[ok] = (Z[j, i] * (1 - tx) * (1 - ty) + Z[j, i + 1] * tx * (1 - ty) + Z[j + 1, i] * (1 - tx) * ty + Z[j + 1, i + 1] * tx * ty)
        return out
    return f


def montar(passo=1.0):
    T = ler(os.path.join(IMP, 'imp_topo.csv')); Pz = ler(os.path.join(IMP, 'imp_pisos.csv'))
    xs = np.arange(BOX[0], BOX[2] + 0.01, passo); ys = np.arange(BOX[1], BOX[3] + 0.01, passo); X, Y = np.meshgrid(xs, ys)
    Zp = raster([t[2] for t in Pz if t[3] > 0.2], X, Y)       # pisos (calçadas/pátios) por cima
    Zt = raster([t[2] for t in T if t[3] > 0.2], X, Y)        # terreno/subdivisões: face de cima
    Z = np.where(np.isnan(Zp), Zt, Zp); fonte = np.where(np.isnan(Zp), np.where(np.isnan(Zt), -1, 1), 0)
    np.savez_compressed(OUT, X=X, Y=Y, Z=Z, fonte=fonte)
    return X, Y, Z, fonte, T, Pz


def main():
    X, Y, Z, fonte, T, Pz = montar()
    print('grade', Z.shape, '| cobertura', int((~np.isnan(Z)).sum()), 'de', Z.size, '| pisos', int((fonte == 0).sum()), 'terreno', int((fonte == 1).sum()))
    print('ids do terreno:', collections.Counter(t[1] for t in T if t[3] > 0.2).most_common(30))
    f = interp()
    # ---- cota: CT das caixas do projeto
    for disc in ('ESG', 'DRE'):
        R = list(csv.DictReader(open(os.path.join(F3, f'CAT_fase3_{disc}_caixas.csv'), encoding='utf-8-sig'), delimiter=';'))
        R = [r for r in R if r['CT'] not in ('', None)]
        P = np.array([[float(r['E']), float(r['N'])] for r in R]); ct = np.array([float(r['CT']) for r in R])
        d = f(P) - ct; ok = ~np.isnan(d)
        print(f'{disc}: {ok.sum()} caixas com CT; IMP − CT: mediana {np.median(d[ok]):+.3f}  p10 {np.percentile(d[ok], 10):+.3f}  p90 {np.percentile(d[ok], 90):+.3f}  máx|d| {np.abs(d[ok]).max():.2f}')
        for r, x in sorted(zip(R, d), key=lambda t: -abs(t[1]) if not np.isnan(t[1]) else 0)[:6]:
            print(f'   {r.get("caixa") or r.get("id") or r.get("nome")}: CT {r["CT"]} IMP {x + float(r["CT"]):.2f} ({x:+.2f})')
    # ---- níveis da SIT
    S = carrega('SIT'); L = []
    for d in S:
        if d['tipo'] == 'TEXT':
            m = re.fullmatch(r'\+\s*(\d{2}[.,]\d{2})', d['texto'].strip())
            if m: L.append((d['pts'][0, 0], d['pts'][0, 1], float(m.group(1).replace(',', '.'))))
    L = np.array(L); d = f(L[:, :2]) - L[:, 2]; ok = ~np.isnan(d)
    print(f'níveis da SIT: {ok.sum()}; IMP − nível: mediana {np.median(d[ok]):+.3f}  p10 {np.percentile(d[ok], 10):+.3f} p90 {np.percentile(d[ok], 90):+.3f}')
    # ---- TOP-001 (existente) longe da obra
    Tp = carrega('TOP'); ex = np.array([q['pts'][0] for q in Tp if q['tipo'] == 'POINT' and q['layer'] == 'TOP-COTAS'])
    ex = ex[(ex[:, 0] > BOX[0]) & (ex[:, 0] < BOX[2]) & (ex[:, 1] > BOX[1]) & (ex[:, 1] < BOX[3]) & (ex[:, 2] > 50)]
    d = f(ex[:, :2]) - ex[:, 2]; ok = ~np.isnan(d)
    print(f'TOP-001: {ok.sum()} pontos; IMP − TOP: mediana {np.median(d[ok]):+.3f}; |d|<0,10 m em {np.mean(np.abs(d[ok]) < 0.10) * 100:.0f}%')
    # ---- planta: contorno dos pisos × linhas dos blocos da SIT
    arq = []
    for q in S:
        if q['tipo'] in ('LINE', 'PL') and q['path'].startswith('BLOCO') and 'PAGINA' not in q['path']:
            p = q['pts'][:, :2]; arq += [(a, b) for a, b in zip(p[:-1], p[1:]) if np.linalg.norm(b - a) > 0.3]
    A = np.array([a for a, b in arq]); B = np.array([b for a, b in arq])
    V = np.unique(np.round(np.vstack([t[2][:, :2] for t in Pz]), 3), axis=0)

    def dmin(q):
        ab = B - A; t = np.clip(np.einsum('ij,ij->i', q - A, ab) / np.maximum(np.einsum('ij,ij->i', ab, ab), 1e-12), 0, 1)
        Qp = A + ab * t[:, None]; k = int(np.argmin(np.hypot(*(Qp - q).T))); return Qp[k] - q
    vec = np.array([dmin(q) for q in V]); dist = np.hypot(*vec.T)
    perto = dist < 3.0
    print(f'pisos: {len(V)} vértices; distância à linha de bloco da SIT: mediana {np.median(dist):.3f} m; < 5 cm em {np.mean(dist < 0.05) * 100:.0f}%; vetor médio (perto) {vec[perto].mean(0).round(3)}')
    W = []
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_paredes.csv'), encoding='utf-8'), delimiter=';'):
        for k in ('p0', 'p1'): W.append(list(map(float, r[k].split(',')))[:2])
    W = np.array(W); vw = np.array([dmin(q) for q in W]); dw = np.hypot(*vw.T)
    print(f'paredes: {len(W)} pontas; distância à SIT: mediana {np.median(dw):.3f} m; < 5 cm em {np.mean(dw < 0.05) * 100:.0f}%')


if __name__ == '__main__':
    main()
