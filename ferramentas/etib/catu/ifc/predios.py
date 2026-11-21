# -*- coding: utf-8 -*-
"""Catu — contorno dos prédios (face externa) para a regra "só rede externa" (Anderson, 21/10/2026): o que fica dentro não é
modelado nem conta como conflito. Fonte: os blocos de arquitetura da SIT R02 _GEO (UTM; georef/catu_comum.carrega('SIT')): por
bloco, o menor retângulo (girado) que contém as linhas de parede (#AAA_PAREDE; sem parede, as linhas do bloco tirando piso,
layout, louças e esquadrias) = face externa das paredes; os prédios são todos retangulares (o bloco de salas existente são duas
alas com o corredor coberto no meio, um retângulo só). Campo society, quadra poliesportiva descoberta e a praça do "Bloco Brasil
Profissionalizante" (só piso e jardim na SIT) não são prédio e ficam de fora.
Uso como módulo (contornos(), uniao(), dentro(), cortar()) ou direto para a imagem de conferência."""
import os, sys, json
import numpy as np
from shapely.geometry import LineString, Point, Polygon, MultiPoint
from shapely.ops import unary_union

sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predios.json')
BLOCOS = {'BLOCO AUDITÓRIO': 'Teatro', 'BLOCO RESTAURANTE': 'Restaurante', 'Subestação Jaguarari': 'Subestação',
          'BLOCO DE SALAS': 'Bloco de salas (existente)',
          'BLOCO VESTIÁRIOS': 'Vestiários', 'BLOCO SALAS 1': 'Bloco salas 1', 'BLOCO 3': 'Bloco 3', 'BLOCO 4': 'Guarita',
          'Lixo Jaguarari-flat-1-flat-1': 'Casa de resíduos', 'Gás-flat-1': 'Casa de gás'}
FORA = ('#AAA_PISO', '#AAA_LAYOUT', '#AAA_FIXO SANIT.', '#AAA_ESQUADRIA', '#AAA_PROJEÇÃO')


def _calcular():
    from catu_comum import carrega
    g = {}
    for d in carrega('SIT'):
        top = d['path'].split('|')[0] if d['path'] else '-'
        if top in BLOCOS and d['tipo'] in ('LINE', 'PL') and len(d['pts']) >= 2:
            g.setdefault(top, []).append(d)
    out = []
    for top, ds in g.items():
        par = [d for d in ds if d['layer'] in ('#AAA_PAREDE', '01 - LINHAS EDIFICAÇÕES')] or [d for d in ds if d['layer'] not in FORA] or ds
        R = MultiPoint([tuple(p) for d in par for p in d['pts'][:, :2]]).minimum_rotated_rectangle
        out.append((BLOCOS[top], [list(map(float, p)) for p in R.exterior.coords]))
    json.dump(out, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    return out


def contornos():
    J = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else _calcular()
    return [(n, Polygon(p)) for n, p in J]


def uniao():
    return unary_union([p for _, p in contornos()])


def dentro(U, p, tol=0.0):
    return U.buffer(-tol).contains(Point(float(p[0]), float(p[1])))


def cortar(U, P):
    """polilinha 3D -> pedaços FORA dos prédios (lista de arrays n×3), com a cota interpolada no corte."""
    P = np.asarray(P, float)
    if len(P) < 2: return [P]
    L = LineString(P[:, :2])
    if not L.intersects(U): return [P]
    fora = L.difference(U)
    if fora.is_empty: return []
    S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
    pecas = []
    for g in (fora.geoms if hasattr(fora, 'geoms') else [fora]):
        if g.length < 0.05: continue
        Q = np.array(g.coords)
        s = np.array([L.project(Point(q)) for q in Q])
        z = np.interp(s, S, P[:, 2]) if S[-1] > 0 else np.full(len(Q), P[0, 2])
        pecas.append(np.column_stack([Q, z]))
    return pecas


if __name__ == '__main__':
    import csv, matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if os.path.exists(CACHE): os.remove(CACHE)
    F3 = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\FASE3_COTAS_2026-10-18'
    REDE = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\rede'
    fig, ax = plt.subplots(figsize=(16, 17))
    for fn, cor in (('CAT_fase3_ESG_trechos.csv', 'saddlebrown'), ('CAT_fase3_DRE_trechos.csv', 'g')):
        for r in csv.DictReader(open(os.path.join(F3, fn), encoding='utf-8-sig'), delimiter=';'):
            ax.plot([float(r['E_ini']), float(r['E_fim'])], [float(r['N_ini']), float(r['N_fim'])], color=cor, lw=0.6)
    for t in json.load(open(os.path.join(REDE, 'af_rede.json'), encoding='utf-8'))['trechos']:
        P = np.array(t['pts']); ax.plot(P[:, 0], P[:, 1], color='b', lw=0.6)
    ele = json.load(open(os.path.join(REDE, 'ele_rede.json'), encoding='utf-8'))
    for tag in ('EL1', 'EL2'):
        for t in ele[tag]['eletrodutos']:
            P = np.array(t['pts']); ax.plot(P[:, 0], P[:, 1], color='orange', lw=0.6)
    inc = json.load(open(os.path.join(REDE, 'inc_rede.json'), encoding='utf-8'))
    for t in inc['hidrantes'] + inc['sdai']:
        P = np.array(t['pts']); ax.plot(P[:, 0], P[:, 1], color='r', lw=0.6)
    for n, p in contornos():
        ax.fill(*p.exterior.xy, alpha=0.25, color='gray'); ax.plot(*p.exterior.xy, color='k', lw=0.8)
        ax.text(p.centroid.x, p.centroid.y, n, fontsize=8, ha='center')
    ax.set_aspect('equal'); ax.set_xlim(567625, 567805); ax.set_ylim(8634530, 8634725)
    ax.set_title('Catu: contorno dos prédios (só rede externa) × redes')
    fn = r'D:\Projeto Modelagem\FERRAMENTAS\catu\ifc\predios.png'
    fig.savefig(fn, dpi=110, bbox_inches='tight'); print(fn, len(contornos()), 'contornos')
