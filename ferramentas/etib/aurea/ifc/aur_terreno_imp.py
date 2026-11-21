# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — terreno do IMP as built (decisão A2 da página de entrada: IMP ajustado às cotas da base).
O IMP foi lido no Revit em 22/10/2026 (georef/work/AUREA/imp/imp_topo.csv e imp_pisos.csv), mas o modelo não está em UTM: as
coordenadas compartilhadas dele são as da SIT R01 (sistema próprio do levantamento). Passa para UTM 24S pela mesma transformação
do referenciamento da SIT (CAD_GEORREFERENCIADO/transformacao_BASE-SIT-PAV_para_UTM.json), rasteriza a face de cima (topo e
pisos, o maior z) numa grade de 0,50 m e grava escolas/dados/apora_aurea_terreno_imp.npz.
--diag compara com o terreno provisório de 18/10 e com as CT das caixas da drenagem.
Terreno da ferramenta (apora_aurea_terreno_imp_base.npz): o IMP só cobre a quadra e o entorno e está 1,00 m acima da base
(platô 189,00 no IMP x 188,00 na TER, no TOP e nas CT da drenagem): IMP deslocado DZ_IMP; fora do IMP, o TOP-001 (com o platô
188 da TER); por fim ajustado (modo local) às CT das caixas da drenagem, com a CT 188,00 a leste (decisão A3).
Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_terreno_imp.py [--diag]"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro\imp')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import imp_terreno_lib as it          # noqa: E402

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\AUREA\imp'
TRF = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\CAD_GEORREFERENCIADO\transformacao_BASE-SIT-PAV_para_UTM.json'
DADOS = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados'
OUT = os.path.join(DADOS, 'apora_aurea_terreno_imp.npz')                 # IMP como está (só UTM), para conferência
FINAL = os.path.join(DADOS, 'apora_aurea_terreno_imp_base.npz')         # terreno da ferramenta
TOP = os.path.join(DADOS, 'apora_aurea_terreno_top.npz')                # TOP-001 + platô 188 (18/10), fora do IMP
CAIXAS = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\GEORREF_E_REDES_2026-10-18\revit\dre_caixas.csv'
PASSO = 0.5
DZ_IMP = -1.00   # o platô da quadra no IMP está em 189,00; na TER (e no TOP) é 188,00, e as CT da drenagem a oeste são 188,00


def matriz():
    j = json.load(open(TRF, encoding='utf-8'))
    return np.array(j['matriz_2x3'])


def utm(p, M=None):
    M = matriz() if M is None else M
    p = np.asarray(p, float)
    xy = p[..., :2] @ M[:, :2].T + M[:, 2]
    return np.concatenate([xy, p[..., 2:]], axis=-1)


# O IMP não está no sistema da SIT por inteiro: as coordenadas dele são as da SIT, mas a quadra (e com ela o modelo todo) está
# girada. A posição da base vale: o centro e a direção da grade de pilares do IMP (14 pilares, 24,50 x 33,20 m) vão para o centro e a
# direção do alambrado da quadra na SIT R01 (layer ARQ-ESQ, retângulo 24,7 x 33,4 m nos pilares, eixo maior a 100,71°), depois da
# transformação SIT -> UTM. Conferência: aur_conf_quadra.py.
IMP_C0 = np.array([600053.745, 8711374.527])     # centro da grade de pilares do IMP (UTM pela matriz da SIT)
IMP_C1 = np.array([600059.900, 8711376.410])     # centro do retângulo ARQ-ESQ da SIT (UTM)
IMP_ROT = np.radians(100.71 - 92.114)            # eixo maior: SIT 100,71° x IMP 92,114°


def imp_utm(p, M=None):
    """coordenadas do IMP (sistema da SIT) -> UTM, com o giro e o deslocamento da quadra."""
    q = utm(p, M); c, s = np.cos(IMP_ROT), np.sin(IMP_ROT)
    d = q[..., :2] - IMP_C0
    xy = np.stack([c * d[..., 0] - s * d[..., 1], s * d[..., 0] + c * d[..., 1]], axis=-1) + IMP_C1
    return np.concatenate([xy, q[..., 2:]], axis=-1)


def triangulos(tags=('TOPO', 'PISO'), nz_min=0.2):
    M = matriz(); T = []; ids = []
    for fn in ('imp_topo.csv', 'imp_pisos.csv'):
        for r in csv.DictReader(open(os.path.join(IMP, fn), encoding='utf-8'), delimiter=';'):
            if r['tag'] not in tags: continue
            A = np.array([list(map(float, r[k].split(','))) for k in 'abc'])
            n = np.cross(A[1] - A[0], A[2] - A[0]); nn = np.linalg.norm(n)
            if nn < 1e-9 or n[2] / nn < nz_min: continue       # só face de cima (a normal do CSV vem pela ordem dos vértices)
            T.append(imp_utm(A, M)); ids.append(r['id'])
    return np.array(T), ids


def grade(T):
    x0, y0 = np.floor(T[..., 0].min()), np.floor(T[..., 1].min()); x1, y1 = np.ceil(T[..., 0].max()), np.ceil(T[..., 1].max())
    X, Y = np.meshgrid(np.arange(x0, x1 + 1e-6, PASSO), np.arange(y0, y1 + 1e-6, PASSO))
    return X, Y, it.raster(list(T), X, Y)


def malha(X, Y, Z):
    ok = ~np.isnan(Z); idx = -np.ones(Z.shape, int); idx[ok] = np.arange(ok.sum())
    V = np.column_stack([X[ok], Y[ok], Z[ok]]); F = []
    for j in range(Z.shape[0] - 1):
        for i in range(Z.shape[1] - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if min(a, b, c, d) < 0: continue
            F += [(a, b, c), (a, c, d)]
    return V, np.array(F)


def final(X, Y, Z):
    from preclash import terreno as tr
    D = dict(np.load(TOP, allow_pickle=False))
    ok = ~np.isnan(Z)
    Vi = np.column_stack([X[ok], Y[ok], Z[ok] + DZ_IMP])
    # pontos do TOP fora da área do IMP (célula da grade sem face e a mais de 1 m da borda)
    P = D['pts']; i = np.clip(np.round((P[:, 0] - X[0, 0]) / PASSO).astype(int), 0, X.shape[1] - 1)
    j = np.clip(np.round((P[:, 1] - Y[0, 0]) / PASSO).astype(int), 0, X.shape[0] - 1)
    cob = ok.copy()
    for _ in range(2):                                   # dilata 2 células (sem scipy no .venv)
        c2 = cob.copy(); c2[1:] |= cob[:-1]; c2[:-1] |= cob[1:]; c2[:, 1:] |= cob[:, :-1]; c2[:, :-1] |= cob[:, 1:]; cob = c2
    dentro = (P[:, 0] >= X[0, 0]) & (P[:, 0] <= X[0, -1]) & (P[:, 1] >= Y[0, 0]) & (P[:, 1] <= Y[-1, 0]) & cob[j, i]
    Vt = P[~dentro]
    tmp = FINAL.replace('.npz', '_sem_ajuste.npz')
    out = {k: v for k, v in D.items() if k not in ('pts', 'tri', 'fonte')}
    np.savez_compressed(tmp, pts=np.vstack([Vi, Vt]), fonte=np.array(f'IMP as built em UTM deslocado {DZ_IMP:+.2f} m (platô 189 -> 188 da TER) + TOP-001 fora do IMP'), **out)
    base = []
    t = open(CAIXAS, encoding='utf-8-sig').readline(); sep = ';' if ';' in t else ','
    # as caixas de areia da quadra já executadas (aur_asbuilt.py) entram pela tampa do as built (188,00); do AF-002, só as caixas
    # novas (CA-10 e PVP), com a CT 188,00 a leste (A3)
    for r in csv.DictReader(open(CAIXAS, encoding='utf-8-sig'), delimiter=sep):
        if r['id'] not in ('CA-10', 'PVP-01', 'PVP-02', 'PVP-03', 'PVP-04', 'PVP-05', 'PVP-06'): continue
        ct = float(r['CT'])
        if ct > 188.0: ct = 188.0                       # A3: CT 188,00 a leste (CA-10, PVP-01/02), mesma profundidade
        base.append((float(r['x_utm']), float(r['y_utm']), ct))
    AB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AUR_asbuilt_caixas.csv')
    for r in csv.DictReader(open(AB, encoding='utf-8-sig'), delimiter=';'):
        if r['disc'] == 'DRE': base.append((float(r['E']), float(r['N']), float(r['zt'])))
    rel = tr.ajustar(tmp, np.array(base), FINAL, modo='local', raio=6.0,
                     fonte='tampas das caixas de areia executadas (as built) e CT das caixas novas do AF-002 (CT 188 a leste, A3)')
    os.remove(tmp)
    print('terreno final', FINAL, rel)


def main():
    T, ids = triangulos()
    X, Y, Z = grade(T)
    V, F = malha(X, Y, Z)
    np.savez_compressed(OUT, pts=V, tri=F, fonte=np.array('IMP as built (Revit, 22/10/2026), SIT -> UTM: sólidos topográficos e pisos, face de cima'))
    final(X, Y, Z)
    print('gravado', OUT, '| vértices', len(V), '| triângulos', len(F), '| z', V[:, 2].min().round(2), '–', V[:, 2].max().round(2),
          '| caixa', V[:, 0].min().round(1), V[:, 1].min().round(1), V[:, 0].max().round(1), V[:, 1].max().round(1))
    if '--diag' in sys.argv:
        from preclash.terreno import Terreno
        ti = Terreno(OUT); tp = Terreno(os.path.join(DADOS, 'apora_aurea_terreno.npz')); tt = Terreno(os.path.join(DADOS, 'apora_aurea_terreno_top.npz'))
        F2 = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\GEORREF_E_REDES_2026-10-18'
        print(f'{"caixa":8s} {"CT":>7s} {"IMP":>7s} {"SIT+pl":>7s} {"TOP":>7s}')
        for r in csv.DictReader(open(os.path.join(F2, 'revit', 'dre_caixas.csv'), encoding='utf-8-sig'), delimiter=';' if ';' in open(os.path.join(F2, 'revit', 'dre_caixas.csv'), encoding='utf-8-sig').readline() else ','):
            x, y = float(r['x_utm']), float(r['y_utm'])
            zi, zp, zt = (float(t.z([[x, y]])[0]) for t in (ti, tp, tt))
            print(f'{r["id"]:8s} {float(r["CT"]):7.2f} {zi:7.2f} {zp:7.2f} {zt:7.2f}')
        for fn in ('ele_nos.csv',):
            for r in csv.DictReader(open(os.path.join(F2, fn), encoding='utf-8-sig'), delimiter=';' if ';' in open(os.path.join(F2, fn), encoding='utf-8-sig').readline() else ','):
                x, y = float(r['x']), float(r['y'])
                zi, zp, zt = (float(t.z([[x, y]])[0]) for t in (ti, tp, tt))
                print(f'{r["no"]:8s} {"":7s} {zi:7.2f} {zp:7.2f} {zt:7.2f}')


if __name__ == '__main__':
    main()
