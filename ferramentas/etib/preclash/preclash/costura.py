# -*- coding: utf-8 -*-
"""Costura das pontas: peças da mesma rede que deviam se encostar e ficaram com folga (Revisão de qualidade da Jandaíra R03,
20/10/2026: 85 pontos — 2,9 cm na AF, 7,5 cm na DRE, 2,3 cm na ELE, 14 cm no incêndio — e "dois tubos sobrepostos em 4 cm").
Pontas da mesma rede a menos de 'tol' (padrão 0,15 m) em planta e de 'tol_z' (0,05 m) em cota viram UM ponto (a média), fora de
caixa da disciplina (dentro da caixa a ligação é a própria caixa). A cota muda no máximo alguns centímetros, a planta na mesma
ordem: nenhuma rede muda de profundidade. Roda depois das soluções, antes das conexões, da verificação e do IFC."""
import numpy as np
from . import clash as cl


def _na_caixa(p, caixas, disc):
    for c in caixas:
        if c['disc'] != disc: continue
        if abs(p[0] - c['E']) > c['meia'] + 0.05 or abs(p[1] - c['N']) > c['meia'] + 0.05: continue
        if cl._sd_planta(np.array([p[:2]]), c)[0] < 0.0 and c['zb'] - 0.10 <= p[2] <= c['zt'] + 0.10: return True
    return False


def costurar(E, caixas, tol=0.15, tol_z=0.05, campo='pts_sol', log=print):
    pontas = []
    for i, e in enumerate(E):
        P = e[campo]
        if len(P) < 2: continue
        for k in (0, len(P) - 1): pontas.append((i, k))
    pai = list(range(len(pontas)))

    def raiz(a):
        while pai[a] != a: pai[a] = pai[pai[a]]; a = pai[a]
        return a
    X = np.array([E[i][campo][k] for i, k in pontas]) if pontas else np.zeros((0, 3))
    rede = [E[i]['rede'] for i, k in pontas]
    for a in range(len(pontas)):
        d = np.hypot(X[:, 0] - X[a, 0], X[:, 1] - X[a, 1]); dz = np.abs(X[:, 2] - X[a, 2])
        for b in np.nonzero((d < tol) & (dz < tol_z))[0]:
            if b <= a or rede[b] != rede[a] or pontas[b][0] == pontas[a][0]: continue
            pai[raiz(a)] = raiz(b)
    grupos = {}
    for a in range(len(pontas)): grupos.setdefault(raiz(a), []).append(a)
    n = 0; maior = 0.0
    for g in grupos.values():
        if len(g) < 2: continue
        Q = X[g]
        if np.max(np.hypot(Q[:, 0] - Q[0, 0], Q[:, 1] - Q[0, 1])) < 1e-4 and np.ptp(Q[:, 2]) < 1e-4: continue
        e0 = E[pontas[g[0]][0]]
        if _na_caixa(Q.mean(0), caixas, e0['disc']): continue
        m = Q.mean(0)
        for a in g:
            i, k = pontas[a]; e = E[i]
            maior = max(maior, float(np.linalg.norm(e[campo][k] - m)))
            e[campo] = e[campo].copy(); e[campo][k] = m
            if campo == 'pts_sol' and not e.get('janelas') and not e.get('desvio'):
                e['pts'] = e['pts'].copy(); e['pts'][k] = m       # o "projeto" mostrado no visualizador acompanha
            e.pop('S', None)
        n += 1
    if n: log(f'  costura: {n} nós com folga entre peças fechados (maior ajuste {maior * 100:.1f} cm)')
    return n


def costurar_colinear(E, caixas, tol=0.30, ang=10.0, tol_z=0.05, campo='pts_sol', log=print):
    """vão de até 'tol' m entre duas pontas da mesma rede que seguem na mesma direção (o vão é a peça que faltou no modelo:
    registro, luva): a ponta avança até a outra (Jandaíra R03: PCI-AH-05/08, 0,21 m)."""
    pontas = [(e, k) for e in E for k in (0, -1) if len(e[campo]) >= 2]
    feitos = 0
    for i, (e, k) in enumerate(pontas):
        p = e[campo][k]; q = e[campo][1 if k == 0 else -2]
        u = (p - q)[:2]; nu = np.linalg.norm(u)
        if nu < 1e-6 or _na_caixa(p, caixas, e['disc']): continue
        u = u / nu
        for o, j in pontas[i + 1:]:
            if o is e or o['rede'] != e['rede']: continue
            r = o[campo][j]; s = o[campo][1 if j == 0 else -2]
            d = (r - p)[:2]; dn = np.linalg.norm(d)
            if not (0.02 < dn < tol) or abs(r[2] - p[2]) > tol_z: continue
            v = (s - r)[:2]; nv = np.linalg.norm(v)
            if nv < 1e-6: continue
            v = v / nv
            if np.degrees(np.arccos(np.clip(u @ (d / dn), -1, 1))) > ang or np.degrees(np.arccos(np.clip(u @ v, -1, 1))) > ang: continue
            e[campo] = e[campo].copy(); e[campo][k] = r.copy(); e.pop('S', None)
            if campo == 'pts_sol' and not e.get('janelas') and not e.get('desvio'): e['pts'] = e[campo].copy()
            feitos += 1; break
    if feitos: log(f'  costura colinear: {feitos} vão(s) fechados (peça que faltava no modelo)')
    return feitos
