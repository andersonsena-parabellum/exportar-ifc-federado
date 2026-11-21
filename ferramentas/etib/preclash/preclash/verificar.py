# -*- coding: utf-8 -*-
"""Verificação automática da continuidade das redes, depois das soluções e antes do IFC (Anderson, 20/10/2026: o incêndio da
Jandaíra R03 saiu "picotado" na casa de bombas — pedaços curtos, soltos e desalinhados). Roda em todo cenário do rodar.py e grava
<SIGLA>_preclash_<cen>_verificacao.csv; o resumo vai para o LEIA-ME da rodada. Itens:
  - 'ponta solta': ponta de trecho a 5 cm–1 m de outra ponta da mesma rede (vão), sem encostar, nem fica dentro de caixa/equipamento,
    nem no meio de outro trecho da mesma rede (derivação) — rede interrompida ou peça (válvula, tê, redução) que faltou no modelo;
  - 'degrau': duas pontas da mesma rede no mesmo ponto em planta com cotas diferentes (> 2 cm) e sem peça vertical entre elas;
  - 'pedaço curto': trecho com menos de 'curto' m (padrão 0,15) que não é subida/descida vertical — sobra de recorte;
  - 'rede fora do lugar': pressurizada a mais de 'prof_max' + 0,30 m do terreno ou acima do terreno (o estudo não devia deixar).
Nenhum item bloqueia a rodada: a lista diz o que conferir no 3D antes de entregar."""
import collections
import numpy as np
from . import clash as cl

TOL = 0.05          # pontas a menos disso (planta) são o mesmo nó: o modelo do Revit deixa folgas de 3 a 4 cm nas uniões
VAO = 1.00          # ponta com outra ponta da rede a mais disso é fim de rede (entrada de edificação, equipamento): não é 'solta'
DEGRAU = {'pressao': 0.05, 'gravidade': 0.10}


def _dentro_caixa(p, caixas, folga=0.05):
    for c in caixas:
        if abs(p[0] - c['E']) > c['meia'] + folga or abs(p[1] - c['N']) > c['meia'] + folga: continue
        if cl._sd_planta(np.array([p[:2]]), c)[0] < folga and c['zb'] - 0.10 <= p[2] <= c['zt'] + 0.10: return True
    return False


def _na_vertical(P, q, tol=0.02):
    """q está sobre um segmento vertical da polilinha P (mesmo ponto em planta, cota dentro do segmento)?"""
    for a, b in zip(P[:-1], P[1:]):
        if np.hypot(*(b[:2] - a[:2])) < 0.01 and np.hypot(*(q[:2] - a[:2])) < TOL and min(a[2], b[2]) - tol <= q[2] <= max(a[2], b[2]) + tol:
            return True
    return False


def verificar(E, caixas, ter=None, regras=None, campo='pts_sol', curto=0.15):
    regras = regras or {}
    out = []
    pontas = collections.defaultdict(list)
    for e in E:
        P = e[campo]
        if len(P) < 2: continue
        for k in (0, len(P) - 1): pontas[e['rede']].append((e, k, P[k]))
    for rede, lst in pontas.items():
        A = np.array([p for _, _, p in lst])
        els = [e for e in E if e['rede'] == rede]
        amo = {o['id']: cl.amostra(o[campo], 0.05) for o in els}
        for i, (e, k, p) in enumerate(lst):
            d = np.hypot(A[:, 0] - p[0], A[:, 1] - p[1]); d[i] = np.inf
            perto = np.nonzero(d < TOL)[0]
            if len(perto):
                dz = np.abs(A[perto, 2] - p[2])
                if np.all(dz > DEGRAU.get(e['tipo'], 0.05)) and not _dentro_caixa(p, caixas):
                    j = perto[int(np.argmin(dz))]
                    # uma ponta nasce no meio da vertical do outro trecho (dois ramais do mesmo ralo, DRN-332/333): derivação, não degrau
                    o_ = lst[j][0]
                    na_vertical = _na_vertical(o_[campo], p) or _na_vertical(e[campo], A[j])
                    # ramal que entra no tubo maior fora do eixo, dentro do diâmetro dele (DRN-190 no DRN-187 Ø450): ligado
                    na_vertical = na_vertical or dz.min() <= abs(o_['de'] - e['de']) / 2 + 0.005
                    if i < j and not na_vertical:
                        out.append({'tipo': 'degrau', 'rede': rede, 'disc': e['disc'], 'trecho': e['trecho'], 'outro': lst[j][0]['trecho'],
                                    'E': float(p[0]), 'N': float(p[1]), 'z': float(p[2]), 'valor': float(dz.min()),
                                    'o_que_fazer': 'pôr a peça vertical (subida/descida) ou alinhar as cotas'})
                continue
            if _dentro_caixa(p, caixas): continue
            # derivação: a ponta encosta no meio de outro trecho da mesma rede
            meio = any(np.min(np.linalg.norm(amo[o['id']] - p, axis=1)) < o['de'] / 2 + TOL for o in els if o is not e
                       and np.all(o[campo].min(0) - 0.5 <= p) and np.all(o[campo].max(0) + 0.5 >= p))
            if meio: continue
            viz = d[np.isfinite(d)]
            if not len(viz) or viz.min() >= VAO: continue          # fim de rede
            out.append({'tipo': 'ponta solta', 'rede': rede, 'disc': e['disc'], 'trecho': e['trecho'], 'outro': '',
                        'E': float(p[0]), 'N': float(p[1]), 'z': float(p[2]), 'valor': float(viz.min()) if len(viz) else None,
                        'o_que_fazer': 'ligar à rede/caixa ou incluir a peça que falta (válvula, tê, redução); valor = distância à ponta mais próxima'})
    for e in E:
        P = e[campo]; dP = np.diff(P, axis=0)
        L = float(np.sum(np.linalg.norm(dP, axis=1))); Lh = float(np.sum(np.hypot(dP[:, 0], dP[:, 1])))
        if L < curto and Lh > 0.5 * L:
            out.append({'tipo': 'pedaço curto', 'rede': e['rede'], 'disc': e['disc'], 'trecho': e['trecho'], 'outro': '',
                        'E': float(P[0, 0]), 'N': float(P[0, 1]), 'z': float(P[0, 2]), 'valor': L,
                        'o_que_fazer': 'juntar ao trecho vizinho ou trocar pela peça (conexão) que ele representa'})
    if ter is not None:
        pm = (regras.get('estudo') or {}).get('prof_max') or regras.get('prof_max_geral') or 2.0
        for e in E:
            if e['tipo'] != 'pressao' or e['info'].get('estudo') is False or not e.get('estudo'): continue
            Q = cl.amostra(e[campo], 0.5); zt = ter.z(Q); ok = np.isfinite(zt)
            if not ok.any(): continue
            prof = zt[ok] - (Q[ok, 2] + e['de'] / 2)
            if prof.max() > pm + 0.30 or prof.min() < 0:
                i = int(np.argmax(prof)) if prof.max() > pm + 0.30 else int(np.argmin(prof))
                out.append({'tipo': 'rede fora do lugar', 'rede': e['rede'], 'disc': e['disc'], 'trecho': e['trecho'], 'outro': '',
                            'E': float(Q[ok][i, 0]), 'N': float(Q[ok][i, 1]), 'z': float(Q[ok][i, 2]), 'valor': float(prof[i]),
                            'o_que_fazer': f'topo a {prof[i]:.2f} m do terreno (fora de 0 a {pm:.2f} m): conferir o terreno ou o trecho'})
    return out


def marcar(itens, esperados):
    """itens conhecidos e explicados no adaptador (S.VERIFICACAO_ESPERADA = {(tipo, trecho): motivo}) saem como 'esperado'."""
    for i in itens:
        m = esperados.get((i['tipo'], i['trecho'])) or esperados.get((i['tipo'], '*' + i['trecho'].split('.')[0]))
        if m: i['esperado'] = m
    return itens


def resumo(itens):
    r = collections.Counter(i['tipo'] for i in itens if not i.get('esperado'))
    e = sum(1 for i in itens if i.get('esperado'))
    return dict(r, **({'esperados': e} if e else {}))
