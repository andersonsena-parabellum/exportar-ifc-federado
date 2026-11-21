# -*- coding: utf-8 -*-
"""Terreno da pré-compatibilização: TIN (pontos + triângulos) com platôs horizontais por cima.
Formato do arquivo (.npz): pts (n,3) E,N,z | tri (m,3) | plat_n, plat_xy, plat_z (polígonos dos platôs, opcional) | arq (linhas 2D da SIT, opcional)."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.tri as mtri


def dentro_poligono(p, poly):
    x, y = p[..., 0], p[..., 1]; xs, ys = poly[:, 0], poly[:, 1]; res = np.zeros(x.shape, bool); j = len(poly) - 1
    for i in range(len(poly)):
        c = ((ys[i] > y) != (ys[j] > y)) & (x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i] + 1e-300) + xs[i]); res ^= c; j = i
    return res


class Terreno:
    def __init__(self, npz):
        D = np.load(npz, allow_pickle=False)
        self.pts = D['pts']
        # sem 'tri' no arquivo: Delaunay dos pontos (basta gravar os pontos do terreno)
        self.T = mtri.Triangulation(self.pts[:, 0], self.pts[:, 1], D['tri']) if 'tri' in D else mtri.Triangulation(self.pts[:, 0], self.pts[:, 1])
        self.tri = self.T.triangles
        self.f = mtri.LinearTriInterpolator(self.T, self.pts[:, 2])
        self.plat = []
        if 'plat_n' in D:
            k = 0
            for n, z in zip(D['plat_n'], D['plat_z']):
                self.plat.append((D['plat_xy'][k:k + n], float(z))); k += n
        self.arq = D['arq'] if 'arq' in D else np.zeros((0, 2, 2))
        self.fonte = str(D['fonte']) if 'fonte' in D else ''

    def z(self, p):
        p = np.atleast_2d(np.asarray(p, float))[:, :2]
        z = np.array(self.f(p[:, 0], p[:, 1]).filled(np.nan), float)
        for P, zp in self.plat:
            z[dentro_poligono(p, P)] = zp
        return z

    def grade(self, box, passo=2.0):
        """malha regular (para IFC e visualizador): vértices (k,3) e triângulos (só onde há terreno)."""
        xs = np.arange(box[0], box[2] + passo, passo); ys = np.arange(box[1], box[3] + passo, passo)
        X, Y = np.meshgrid(xs, ys); Z = self.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
        ny, nx = Z.shape; idx = -np.ones(Z.shape, int); ok = ~np.isnan(Z)
        idx[ok] = np.arange(ok.sum())
        V = np.column_stack([X[ok], Y[ok], Z[ok]])
        F = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
                if a >= 0 and b >= 0 and c >= 0: F.append((a, b, c))
                if a >= 0 and c >= 0 and d >= 0: F.append((a, c, d))
        return V, np.array(F, int)


def ajustar(entrada, pontos_base, saida, modo='local', raio=12.0, inserir=True, fonte=''):
    """Terreno ajustado às cotas dos arquivos de base (parâmetro do Anderson, 19/10/2026): quando o terreno do modelo
    (IMP as built, IFC) e as cotas de base (CT das caixas de DRE/ESG das pranchas, implantação, TOP, TER) divergem, vale a base.
    pontos_base: (n,3) E, N, cota. modo 'constante': desloca tudo pela mediana dos resíduos; 'local': correção suave
    (núcleo gaussiano de alcance ~raio m, some longe dos pontos) + os próprios pontos entram no TIN (inserir=True).
    Platôs do arquivo andam pela mediana dos resíduos dos pontos de dentro deles. Grava o .npz e devolve o relatório."""
    T = Terreno(entrada); D = dict(np.load(entrada, allow_pickle=False))
    P = np.atleast_2d(np.asarray(pontos_base, float))
    z0 = T.z(P); ok = np.isfinite(z0); P, z0 = P[ok], z0[ok]
    r = P[:, 2] - z0
    rel = {'pontos': int(len(P)), 'fora_do_terreno': int((~ok).sum()), 'antes_mediana': float(np.median(r)) if len(r) else 0.0,
           'antes_p95_abs': float(np.percentile(np.abs(r), 95)) if len(r) else 0.0, 'modo': modo}
    V = T.pts.copy()
    if modo == 'constante':
        V[:, 2] += rel['antes_mediana']
    else:
        sig = raio / 2.0; w0 = np.exp(-(raio / sig) ** 2)
        corr = np.zeros(len(V))
        for k in range(0, len(V), 20000):
            d2 = (V[k:k + 20000, None, 0] - P[None, :, 0]) ** 2 + (V[k:k + 20000, None, 1] - P[None, :, 1]) ** 2
            w = np.exp(-d2 / sig ** 2)
            corr[k:k + 20000] = (w * r[None]).sum(1) / (w.sum(1) + w0)
        V[:, 2] += corr
    out = {k: v for k, v in D.items() if k not in ('pts', 'tri')}
    if inserir and modo != 'constante':
        V = np.vstack([V, P])
        out['pts'] = V                          # sem 'tri': Delaunay dos pontos (o Terreno refaz)
    else:
        out['pts'] = V
        if 'tri' in D: out['tri'] = D['tri']
    if 'plat_n' in D:
        pz = D['plat_z'].astype(float).copy(); k = 0
        for i, n in enumerate(D['plat_n']):
            poly = D['plat_xy'][k:k + n]; k += n
            m = dentro_poligono(P[:, :2], poly)
            if m.any(): pz[i] += float(np.median(r[m]))
        out['plat_z'] = pz
    out['fonte'] = (str(D.get('fonte', '')) + f' + ajustado às cotas de base ({len(P)} pontos, {modo})' + (f' — {fonte}' if fonte else '')).strip(' +')
    np.savez_compressed(saida, **out)
    T2 = Terreno(saida); r2 = P[:, 2] - T2.z(P)
    rel.update(depois_mediana=float(np.nanmedian(r2)), depois_p95_abs=float(np.nanpercentile(np.abs(r2), 95)))
    return rel
