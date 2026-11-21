# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — terreno do IMP as built (lido no Revit em 19/10/2026, triângulos em imp_topo.csv / imp_pisos.csv).
Superfície acabada = pisos (+233/+236) > subdivisões > platôs (sólidos 638740/638752/655856) > terreno 637242 > 638628.
Grava imp_raster_1m.npz, confere com as CT das caixas do projeto e com o terreno provisório da fase 3, e desenha o mapa.
Uso: .venv/Scripts/python.exe -X utf8 imp/imp_terreno.py"""
import sys, os, csv
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.dirname(AQUI))
import imp_terreno_lib as it          # noqa: E402
import sat_comum as sc                # noqa: E402
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


ORDEM = [['639613', '645901', '654990', '655359', '655406', '663654', '668222'],   # pisos
         ['640327', '641199'],                                                       # subdivisões
         ['638740', '638752', '655856'],                                             # platôs
         ['637242'], ['638628']]                                                     # terreno
NOME_FONTE = ['piso', 'subdivisão', 'platô', 'terreno 637242', 'terreno 638628']
BOX = (545800.0, 8716040.0, 546100.0, 8716325.0)
OUT = os.path.join(AQUI, 'imp_raster_1m.npz')


def montar(passo=1.0):
    G = it.triangulos()
    xs = np.arange(BOX[0], BOX[2] + 0.01, passo); ys = np.arange(BOX[1], BOX[3] + 0.01, passo); X, Y = np.meshgrid(xs, ys)
    Z = np.full(X.shape, np.nan); fonte = np.full(X.shape, -1)
    for n, grp in enumerate(ORDEM):
        Zg = it.raster([t for k in grp for t in G.get(k, [])], X, Y)
        m = np.isnan(Z) & ~np.isnan(Zg); Z[m] = Zg[m]; fonte[m] = n
    np.savez_compressed(OUT, X=X, Y=Y, Z=Z, fonte=fonte)
    return X, Y, Z, fonte


def interp(npz=OUT):
    """bilinear na grade (NaN fora ou onde falta canto)."""
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


def main():
    X, Y, Z, fonte = montar()
    print('cobertura', int((~np.isnan(Z)).sum()), 'de', Z.size, '| por fonte', {NOME_FONTE[n]: int((fonte == n).sum()) for n in range(len(ORDEM))})
    f = interp()
    linhas = []
    for fn in ('SAT_fase2_ESG_caixas.csv', 'SAT_fase2_AP_caixas.csv', 'SAT_fase2_CPS-DRE_caixas.csv'):
        R = list(csv.DictReader(open(os.path.join(sc.REL, fn), encoding='utf-8-sig'), delimiter=';'))
        d = []
        for r in R:
            z = float(f([[float(r['E']), float(r['N'])]])[0])
            ct = float(r['CT']) if r.get('CT') else None
            linhas.append({'arquivo': fn, 'caixa': r['caixa'], 'tipo': r['tipo'], 'E': r['E'], 'N': r['N'], 'CT_projeto': ct, 'terreno_IMP': round(z, 3),
                           'CT_menos_IMP': round(ct - z, 3) if ct is not None and not np.isnan(z) else ''})
            if ct is not None and not np.isnan(z): d.append(ct - z)
        if d:
            d = np.array(d); print(fn, 'CT − IMP: mediana %.2f | p10 %.2f | p90 %.2f | |Δ|>0,30: %d de %d' % (np.median(d), np.percentile(d, 10), np.percentile(d, 90), (abs(d) > 0.3).sum(), len(d)))
    fo = os.path.join(sc.REL, '..', 'FASE3_COTAS_2026-10-18', 'SAT_fase3_caixas_CT_x_terreno_IMP.csv')
    with open(fo, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()), delimiter=';'); w.writeheader(); w.writerows(linhas)
    # mapa
    from esg_sat import arq_sit
    fig, ax = plt.subplots(figsize=(13, 12))
    im = ax.imshow(Z, origin='lower', extent=(X[0, 0], X[0, -1], Y[0, 0], Y[-1, 0]), cmap='terrain'); plt.colorbar(im, shrink=0.7, label='cota (m)')
    ax.contour(X, Y, Z, levels=np.arange(226, 242, 0.5), colors='k', linewidths=0.3)
    ax.add_collection(LineCollection(arq_sit(), colors='r', linewidths=0.3))
    ax.set_xlim(545840, 546070); ax.set_ylim(8716060, 8716300); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain')
    ax.set_title('ETIB Sátiro Dias — terreno acabado do IMP as built (sólidos topográficos + pisos), curvas a cada 0,50 m; vermelho = SIT R06')
    fig.savefig(os.path.join(sc.REL, '..', 'FASE3_COTAS_2026-10-18', 'SAT_fase3_terreno_IMP.png'), dpi=90, bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    main()
