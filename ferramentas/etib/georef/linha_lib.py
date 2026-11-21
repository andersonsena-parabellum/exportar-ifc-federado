# -*- coding: utf-8 -*-
"""Redes desenhadas em linha única (água fria, hidrantes, SDAI, eletrodutos) — extração genérica para a fase 2.
Linhas da rede -> grafo (nós = caixas/equipamentos, tês, pontas) -> trechos; rótulos de Ø/circuito pela chamada
(linha de chamada do layer de indicação) ou pelo tubo paralelo mais próximo."""
import math, re, collections
import numpy as np
from rede_lib import Rede, ligar_pontas, dist_pt_seg, unit


def linhas_da_rede(ob, layers, so_nivel_superior=True, arco_passo=0.25):
    eixos = []
    for d in ob:
        if d['layer'] not in layers: continue
        if so_nivel_superior and d['path']: continue
        if d['tipo'] in ('LINE', 'PL', 'MLINE'):
            p = d['pts'][:, :2]
            if d.get('fechada'): p = np.vstack([p, p[:1]])
            for a, b in zip(p[:-1], p[1:]):
                if np.linalg.norm(b - a) > 0.02: eixos.append({'p0': a.copy(), 'p1': b.copy(), 'd': 0.0, 'origem': d['tipo'], 'layer': d['layer']})
        elif d['tipo'] == 'ARC' and 'pontas' in d:
            c = d['pts'][0, :2]; r = d['r']
            a0, a1 = d['a']
            if a1 < a0: a1 += 360
            n = max(2, int(math.radians(a1 - a0) * r / arco_passo) + 1)
            # pontos do arco em WCS: usa as pontas transformadas para achar a orientação (arcos de blocos espelhados)
            P0, P1 = d['pontas'][0, :2], d['pontas'][1, :2]
            ang0 = math.atan2(P0[1] - c[1], P0[0] - c[0]); ang1 = math.atan2(P1[1] - c[1], P1[0] - c[0])
            sweep = math.radians(a1 - a0)
            # escolhe o sentido que, a partir de ang0, chega em ang1 com o mesmo ângulo de varredura
            dd = (ang1 - ang0) % (2 * math.pi)
            sg = 1 if abs(dd - sweep) < abs((2 * math.pi - dd) - sweep) else -1
            ts = np.linspace(0, sweep, n)
            pts = np.column_stack([c[0] + r * np.cos(ang0 + sg * ts), c[1] + r * np.sin(ang0 + sg * ts)])
            for a, b in zip(pts[:-1], pts[1:]):
                eixos.append({'p0': a, 'p1': b, 'd': 0.0, 'origem': 'ARC', 'layer': d['layer']})
    return eixos


def monta(eixos, nos, snap_no=0.30, snap_ponta=0.05, snap_te=0.05, gap=0.30, gap_caixa=0.6):
    R = Rede(nos, snap_caixa=snap_no, snap_ponta=snap_ponta, snap_te=snap_te).monta(eixos)
    n = ligar_pontas(R, gap=gap, gap_caixa=gap_caixa)
    T = [t for t in R.trechos() if t['L'] > 0.05 and t['nos'][0] != t['nos'][1]]
    for t in T:
        t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
        t['pts_fluxo'] = [np.asarray(p) for p in t['pts']]
    return R, T, n


def ponta_da_chamada(p, chamadas, tol=0.6):
    """Chamada (polilinha/linha) que passa sob o texto em p: devolve a ponta do lado oposto (a que aponta o objeto)."""
    best = None
    for ch in chamadas:
        if len(ch) < 2: continue
        ds = [dist_pt_seg(p, ch[i], ch[i + 1])[0] for i in range(len(ch) - 1)]
        dpts = [np.linalg.norm(p - ch[0]), np.linalg.norm(p - ch[-1])]
        k = int(np.argmin(ds))
        if ds[k] < tol and (best is None or ds[k] < best[0]):
            # a ponta mais longe do texto é a que aponta
            alvo = ch[0] if dpts[0] > dpts[1] else ch[-1]
            best = (ds[k], alvo)
    return best[1] if best else None


def trecho_mais_proximo(p, T, rot=None, tol=1.5, tol_ang=15):
    best = None
    for k, t in enumerate(T):
        P = t['pts']
        for a, b in zip(P[:-1], P[1:]):
            a, b = np.asarray(a), np.asarray(b)
            if np.linalg.norm(b - a) < 0.02: continue
            d, s, q = dist_pt_seg(p, a, b)
            if rot is not None:
                ang = math.degrees(math.atan2(*(b - a)[::-1])) % 180
                da = abs(((rot % 180) - ang + 90) % 180 - 90)
                if da > tol_ang: continue
            if d < tol and (best is None or d < best[0]): best = (d, k)
    return best


def nome_no(R, n, cx_por_id):
    c = cx_por_id.get(R.nos[n]['caixa'])
    if c: return c['id']
    g = R.grau()[n]
    return ('PONTA' if g == 1 else ('TE' if g == 3 else ('CRUZ' if g == 4 else 'NO'))) + f'-{n}'
