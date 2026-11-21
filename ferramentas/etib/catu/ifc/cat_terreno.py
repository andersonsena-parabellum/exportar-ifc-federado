# -*- coding: utf-8 -*-
"""Catu — terreno de entrega (decisão C1 da entrada, recomendada: vale a base).
1) IMP as built (lido no Revit em 19/10: FERRAMENTAS/georef/work/CATU/imp/imp_topo.csv e imp_pisos.csv, triângulos em UTM): face de
   cima dos sólidos topográficos e dos pisos numa grade de 0,50 m -> escolas/dados/catu_terreno_imp.npz. Os pisos (platôs dos prédios
   e do campo, níveis +83,35 / +84,11 / +86,30 / +86,46) também vão como platôs horizontais.
2) Levado às CT das caixas de esgoto e drenagem das pranchas (FASE3_COTAS_2026-10-18): cada platô anda pela mediana dos resíduos das
   CT dentro dele (o campo desce de 83,35 para 78,25, por exemplo) e o resto tem a correção local (núcleo gaussiano, preclash.terreno.
   ajustar). Depois a malha é reamostrada em 0,50 m (a do IFC de entrega) -> escolas/dados/catu_terreno_base.npz.
Uso: .venv/Scripts/python.exe -X utf8 catu/ifc/cat_terreno.py"""
import csv, os, sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro\imp')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import imp_terreno_lib as it          # noqa: E402
from shapely.geometry import Polygon  # noqa: E402
from shapely.ops import unary_union   # noqa: E402
from preclash import terreno as tr    # noqa: E402

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp'
F3 = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\FASE3_COTAS_2026-10-18'
DADOS = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados'
OUT_IMP = os.path.join(DADOS, 'catu_terreno_imp.npz')
OUT = os.path.join(DADOS, 'catu_terreno_base.npz')
CAIXA = (567620.0, 8634530.0, 567806.0, 8634722.0)
PASSO = 0.5
TALUDE = 10.0
RAIO_CT = 15.0
FOLGA_CAMPO = 3.0
# piso do campo no IMP: entra na malha (senão fica um buraco), mas quem manda no campo é o platô da SIT abaixo
PISOS_MALHA = {'688586'}
# platô desenhado na SIT que o IMP não tem como piso inteiro: o campo society (bloco da SIT, retângulo das linhas) em 78,25
PLATOS_SIT = {'BLOCO CAMPO SOCIETY': (78.25, 83.35, 'campo society: SIT 78,25 e CT 78,25 das caixas em volta (retângulo do bloco da SIT)')}
# platôs grandes do IMP e a cota da base (SIT R02 e CT das caixas em volta); os pisos pequenos (varandas, rampas) não entram
PLATOS = {'688506': (82.50, 'bloco ao sul do restaurante: SIT 82,50 e CT 82,35 a 82,55'),
          '723134': (82.50, 'restaurante: SIT 82,50 e CT 82,50 a 82,55'),
          '688720': (82.00, 'bloco a oeste (RF1): SIT 82,00 e CT 82,00 das caixas em volta'),
          '689202': (84.50, 'teatro: SIT 84,50'),
          '689012': (86.30, 'bloco principal existente: fica a cota do IMP (as CT em volta vão de 86,27 a 88,36, no terreno)')}


def _tri(fn):
    out = {}
    for r in csv.DictReader(open(os.path.join(IMP, fn), encoding='utf-8'), delimiter=';'):
        if float(r['nz']) <= 0.05: continue
        out.setdefault(r['id'], []).append([list(map(float, r[k].split(','))) for k in 'abc'])
    return {k: np.array(v) for k, v in out.items()}


def Tplat_imp(T, P):
    z = T.z(P)
    return np.where(np.isnan(z), np.nanmedian(z), z)


# caixa sem cota no projeto, ao lado de uma com CT, no mesmo ramal: a CT da vizinha (o terreno da base, no talude do bloco a oeste,
# dava 85,07 na CES-05, abaixo da GI 85,62 do ESG-36 que sai dela, e o AF-11 passava a 2,17 m sob o degrau)
CT_ADOTADA = {'CES-05': 86.18}       # CE-07, a 2 m


def caixas_ct():
    for fn in ('CAT_fase3_ESG_caixas.csv', 'CAT_fase3_DRE_caixas.csv'):
        for r in csv.DictReader(open(os.path.join(F3, fn), encoding='utf-8-sig'), delimiter=';'):
            if not (r.get('CT') or '').strip() and r['caixa'] in CT_ADOTADA: r = dict(r, CT=str(CT_ADOTADA[r['caixa']]))
            yield r


def base():
    P = []
    for r in caixas_ct():
        try: P.append((float(r['E']), float(r['N']), float(r['CT'])))
        except (TypeError, ValueError): pass
    return np.array(P)


def main():
    topo, pisos = _tri('imp_topo.csv'), _tri('imp_pisos.csv')
    xs = np.arange(CAIXA[0], CAIXA[2] + 1e-6, PASSO); ys = np.arange(CAIXA[1], CAIXA[3] + 1e-6, PASSO); X, Y = np.meshgrid(xs, ys)
    # os pisos pequenos (varandas, rampas, calçadas dos prédios) ficam de fora: nos platôs que andam até a base eles ficavam 4 m acima
    Z = it.raster([t for T in list(topo.values()) + [v for k, v in pisos.items() if k in PLATOS or k in PISOS_MALHA] for t in T], X, Y)
    ok = ~np.isnan(Z); idx = -np.ones(Z.shape, int); idx[ok] = np.arange(ok.sum())
    V = np.column_stack([X[ok], Y[ok], Z[ok]]); F = []
    for j in range(Z.shape[0] - 1):
        for i in range(Z.shape[1] - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if min(a, b, c, d) >= 0: F += [(a, b, c), (a, c, d)]
    # platôs: contorno de cada piso (união dos triângulos de cima) na cota do topo
    pxy, pn, pz, pid = [], [], [], []
    for k, T in pisos.items():
        if k not in PLATOS: continue
        U =unary_union([Polygon(t[:, :2]) for t in T if Polygon(t[:, :2]).area > 1e-6]).buffer(0.01).buffer(-0.01)
        for g in (U.geoms if hasattr(U, 'geoms') else [U]):
            if g.area < 4.0: continue
            q = np.array(g.exterior.coords)[:-1]; pxy.append(q); pn.append(len(q)); pz.append(float(T[:, :, 2].max())); pid.append(k)
    np.savez_compressed(OUT_IMP, pts=V, tri=np.array(F), plat_xy=np.vstack(pxy), plat_n=np.array(pn), plat_z=np.array(pz),
                        plat_id=np.array(pid), fonte=np.array('IMP as built (Revit, 19/10/2026): sólidos topográficos e pisos (platôs)'))
    print('IMP:', len(V), 'vértices,', len(F), 'triângulos,', len(pn), 'platôs; z', V[:, 2].min().round(2), '–', V[:, 2].max().round(2))
    B = base()
    # cada platô anda até a cota da base e leva junto o talude em volta: a correção cai linearmente de 100 % na beira do platô a
    # zero a TALUDE m dele (sem degrau na beira); onde dois platôs se influenciam, média ponderada
    import shapely
    from shapely.geometry import Polygon as _P, MultiPoint
    pts = shapely.points(V[:, 0], V[:, 1]); num = np.zeros(len(V)); den = np.zeros(len(V)); fixo = np.full(len(V), np.nan); k0 = 0
    polis = []
    for n, z0, k in zip(pn, pz, pid):
        polis.append((_P(np.vstack(pxy)[k0:k0 + n]), z0, PLATOS[k][0], f'platô do IMP {k}: {PLATOS[k][1]}', False)); k0 += n
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
    from catu_comum import carrega
    S = carrega('SIT')
    for nome, (alvo, z_imp, txt) in PLATOS_SIT.items():
        P = [tuple(p) for d in S if d['path'].split('|')[0] == nome and d['tipo'] in ('LINE', 'PL') for p in d['pts'][:, :2]]
        poly = MultiPoint(P).minimum_rotated_rectangle.buffer(FOLGA_CAMPO, join_style=2)      # o platô passa do alambrado até as caixas
        print('  ', nome, 'retângulo', np.round(np.array(poly.bounds), 1), f'{poly.area:.0f} m²')
        polis.append((poly, z_imp, alvo, txt, True))
    # o platô do IMP anda inteiro (o piso já é plano); dois platôs vizinhos com alvos diferentes (bloco a oeste 82,00 × bloco de salas
    # 86,30) se encontram numa rampa de TALUDE m em vez de um degrau vertical; só o campo (que no IMP não é um piso inteiro) é fixado
    Timp = tr.Terreno(OUT_IMP)
    for poly, z0, alvo, txt, fixar in polis:
        d = alvo - z0
        dist = shapely.distance(poly, pts); w = np.clip(1.0 - dist / TALUDE, 0.0, 1.0)
        # correção na beira do platô: d (piso plano do IMP) ou, no platô fixado, alvo − terreno do IMP na beira; fora dele ela cai até
        # zero a TALUDE m, a partir do valor da beira mais próxima (sem degrau na beira)
        R = poly.exterior; sb = np.arange(0, R.length, 0.5); Bb = np.array([R.interpolate(x).coords[0] for x in sb])
        cb = (alvo - Tplat_imp(Timp, Bb)) if fixar else np.full(len(Bb), d)
        j = np.clip(np.round(shapely.line_locate_point(R, pts) / 0.5).astype(int), 0, len(Bb) - 1); c = np.where(dist <= 0, (alvo - V[:, 2]) if fixar else d, cb[j])
        num += w * c; den += w
        if fixar: fixo[dist <= 0] = alvo
        print(f'  {z0:.2f} -> {alvo:.2f} ({d:+.2f}) {txt}')
    V2 = V.copy(); V2[:, 2] += num / np.maximum(den, 1.0); V2[~np.isnan(fixo), 2] = fixo[~np.isnan(fixo)]
    np.savez_compressed(OUT, pts=V2, tri=np.array(F), fonte=np.array('IMP as built (Revit, 19/10/2026) com os platôs na cota da base e o talude '
                                                                    'em volta acompanhando; malha de 0,50 m da entrega'))
    r0 = B[:, 2] - tr.Terreno(OUT).z(B)
    print(f'platôs na base: resíduo nas CT mediana {np.nanmedian(r0):+.3f}, p95 {np.nanpercentile(np.abs(r0), 95):.3f}')
    # ajuste local às CT das caixas (o contorno do piso do IMP passa alguns metros da crista da SIT): resíduo interpolado pelo
    # inverso do quadrado da distância, exato na caixa e sumindo a RAIO_CT m dela
    D = dict(np.load(OUT, allow_pickle=False)); W = D['pts'].copy()
    T0 = tr.Terreno(OUT); r = B[:, 2] - T0.z(B); ok = np.isfinite(r); Bk, r = B[ok], r[ok]
    corr = np.zeros(len(W))
    for a in range(0, len(W), 20000):
        dd = np.hypot(W[a:a + 20000, None, 0] - Bk[None, :, 0], W[a:a + 20000, None, 1] - Bk[None, :, 1])
        w = np.where(dd < RAIO_CT, 1.0 / np.maximum(dd, 0.05) ** 2, 0.0)
        taper = np.clip(1.0 - dd.min(1) / RAIO_CT, 0.0, 1.0)
        corr[a:a + 20000] = np.where(w.sum(1) > 0, (w * r[None]).sum(1) / np.maximum(w.sum(1), 1e-12), 0.0) * taper
    W[:, 2] += corr
    # tampa no terreno: dentro da caixa (e 0,25 m em volta) o terreno fica na CT da prancha
    for r in caixas_ct():
        try: e, n, ct, l = float(r['E']), float(r['N']), float(r['CT']), float(r['lado_ou_raio_m'] or 0.6)
        except (TypeError, ValueError): continue
        W[(np.abs(W[:, 0] - e) <= l / 2 + 0.35) & (np.abs(W[:, 1] - n) <= l / 2 + 0.35), 2] = ct
    D['pts'] = W; D['fonte'] = str(D['fonte']) + ' + levado às CT das caixas de esgoto e drenagem (decisão C1)'
    np.savez_compressed(OUT, **D)
    T2 = tr.Terreno(OUT); r2 = B[:, 2] - T2.z(B)
    print(f'final: resíduo nas CT mediana {np.nanmedian(r2):+.3f}, p95 {np.nanpercentile(np.abs(r2), 95):.3f}, máx {np.nanmax(np.abs(r2)):.3f}')
    for (e, n, z), d in zip(B, r2):
        if abs(d) > 0.10: print(f'  CT {z:.2f} em {e:.1f},{n:.1f}: terreno {z - d:.2f} ({d:+.2f})')


if __name__ == '__main__':
    main()
