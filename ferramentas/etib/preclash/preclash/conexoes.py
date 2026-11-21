# -*- coding: utf-8 -*-
"""Conexões (peças) em toda mudança de direção das redes, horizontal ou vertical, inclusive drenagem e esgoto
(parâmetro do dono do projeto, 19/10/2026). Cada curva vira uma peça comercial: o ângulo real é arredondado para o ângulo
comercial mais próximo de REGRAS['conexoes']['angulos'] (padrão 45° e 90°, as peças usuais; antes 11,25° e 22,5° também); até 'flexivel' graus
(padrão 5°) a deflexão fica na junta e não há peça. Peça cujo ângulo real fica a mais de 'tol' (padrão 3°) do
comercial é marcada 'fora do comercial' (conferir: o desvio da ferramenta usa só 45° e 90°).
  - curva: vértice interno do eixo de um trecho, ou o nó onde dois trechos da mesma rede se encontram fora de caixa;
  - tê/junção: nó com 3 ou mais trechos da mesma rede fora de caixa;
  - nó dentro de caixa/PV (da mesma disciplina) não tem peça: a caixa é a ligação.
Cada peça: E, N, z, disc, rede, de, tipo ('curva' | 'junção'), angulo (real), comercial, plano ('horizontal' | 'vertical' | 'misto'),
u1/u2 (direções de chegada e saída), elementos."""
import collections
import numpy as np
from . import clash as cl

PADRAO = {'angulos': [45.0, 90.0],     # peças comerciais usuais (dono do projeto, 21/10/2026: "geralmente 90 e 45; outros eu desconheço")
           'flexivel': 5.0, 'tol': 3.0,     # tol: diferença aceita entre o vértice e a peça (= checklist C6)
          # eletroduto curva na própria peça até 30° (o modelo quebra a curva em pedaços de 7° a 17°: Revisão de qualidade, 20/10/2026)
          # eletroduto FLEXÍVEL (PEAD corrugado) curva na própria peça até 30°; o rígido (PVC roscável) leva curva (Revisão, 20/10/2026)
          'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'CFTV': 30.0}, 'materiais_flexiveis': ('corrug', 'flex', 'pead', 'kanaflex')}


def _unit(v):
    n = np.linalg.norm(v); return v / n if n > 1e-9 else v


def _peca(p, u1, u2, e, cfg, tipo='curva', els=None, l1=None, l2=None):
    ang = float(np.degrees(np.arccos(np.clip(np.dot(u1, u2), -1, 1))))
    flex = any(s in str(e['info'].get('material', '')).lower() for s in cfg.get('materiais_flexiveis', ()))
    lim = cfg.get('flexivel_disc', {}).get(e['disc'], cfg['flexivel']) if flex else cfg['flexivel']
    if tipo == 'curva' and ang <= lim: return None
    com = min(cfg['angulos'], key=lambda a: abs(a - ang)) if tipo == 'curva' else None
    combo = None
    if com is not None and abs(com - ang) > cfg['tol']:
        # combinação de duas peças comerciais no mesmo vértice (ex.: 22,5° + 11,25° = 33,75° num vértice de 32,5°), sem mexer em planta
        pares = [(x + y, (y, x)) for i, x in enumerate(cfg['angulos']) for y in cfg['angulos'][i:]]
        s, par = min(pares, key=lambda t: abs(t[0] - ang))
        if abs(s - ang) < abs(com - ang): com, combo = s, list(par)
    h1, h2 = np.hypot(*u1[:2]), np.hypot(*u2[:2])
    dz = abs(u1[2] - u2[2]); dh = np.degrees(np.arccos(np.clip(np.dot(_unit(u1[:2]), _unit(u2[:2])), -1, 1))) if h1 > .05 and h2 > .05 else 0.0
    plano = 'vertical' if dh < 1.0 else ('horizontal' if dz < .02 else 'misto')
    return {'E': float(p[0]), 'N': float(p[1]), 'z': float(p[2]), 'disc': e['disc'], 'rede': e['rede'], 'de': e['de'], 'tipo': tipo,
            'angulo': round(ang, 1), 'comercial': com, 'plano': plano,
            # tubo flexível (PEAD, corrugado) absorve na própria curvatura a diferença entre o vértice e a peça (até o limite flexível)
            'fora': bool(com is not None and abs(com - ang) > (lim if flex else cfg['tol'])), 'curvatura_no_tubo': bool(flex and com is not None and abs(com - ang) > cfg['tol']),
            'deflexao': round(ang - com, 1) if com is not None else None,
            'combinacao': combo,
            'u1': [float(x) for x in u1], 'u2': [float(x) for x in u2], 'elementos': els or [e['id']], 'l1': l1, 'l2': l2, 'material': e['info'].get('material')}


def _dentro_de_caixa(p, caixas, disc):
    for c in caixas:
        if c['disc'] != disc: continue
        if abs(p[0] - c['E']) > c['meia'] + 0.05 or abs(p[1] - c['N']) > c['meia'] + 0.05: continue
        if cl._sd_planta(np.array([p[:2]]), c)[0] < 0.02 and c['zb'] - 0.05 <= p[2] <= c['zt'] + 0.05: return True
    return False


def gerar(E, caixas, regras, campo='pts_sol'):
    cfg = dict(PADRAO, **(regras.get('conexoes') or {}))
    out = []
    # vértices internos
    for e in E:
        P = e[campo]
        P = np.array([P[0]] + [q for a, q in zip(P[:-1], P[1:]) if np.linalg.norm(q - a) > 1e-4])
        for i in range(1, len(P) - 1):
            u1 = _unit(P[i] - P[i - 1]); u2 = _unit(P[i + 1] - P[i])
            pc = _peca(P[i], u1, u2, e, cfg, l1=float(np.linalg.norm(P[i] - P[i - 1])), l2=float(np.linalg.norm(P[i + 1] - P[i])))
            if pc and not _dentro_de_caixa(P[i], caixas, e['disc']): out.append(pc)
    # nós entre trechos da mesma rede
    nos = collections.defaultdict(list)
    for e in E:
        P = e[campo]
        if len(P) < 2: continue
        for p, q, sai in ((P[0], P[1], True), (P[-1], P[-2], False)):
            nos[(e['rede'], e['disc'], round(float(p[0]) / 0.02), round(float(p[1]) / 0.02))].append((e, p, _unit(q - p), float(np.linalg.norm(q - p))))
    # no mesmo ponto em planta, pontas em cotas bem diferentes são nós diferentes (o ramal DRN-333 que nasce no meio da vertical do
    # DRN-332 ganhava uma curva com o topo dela): separa onde o salto em z passa do raio do maior tubo (+5 cm)
    nos2 = {}
    for chave, lst in nos.items():
        lst = sorted(lst, key=lambda x: float(x[1][2])); grupo = [lst[0]]; k = 0
        for x in lst[1:]:
            if float(x[1][2] - grupo[-1][1][2]) > max(x[0]['de'], grupo[-1][0]['de']) / 2 + 0.05:
                nos2[chave + (k,)] = grupo; grupo = []; k += 1
            grupo.append(x)
        nos2[chave + (k,)] = grupo
    nos = nos2
    for (rede, disc, _, _, _), lst in nos.items():
        if len(lst) < 2: continue
        p = lst[0][1]
        if _dentro_de_caixa(p, caixas, disc): continue
        # dois tubos de diâmetros muito diferentes (ramal Ø40 na cabeça do Ø450, DRN-190 × DRN-187): é junção no tubo maior, não curva
        if len(lst) == 2 and (lst[0][0]['tipo'] != 'gravidade' or max(x[0]['de'] for x in lst) <= 2 * min(x[0]['de'] for x in lst)):
            (e1, p1, d1, l1), (e2, p2, d2, l2) = lst
            pc = _peca(p1, -d1, d2, e1, cfg, els=[e1['id'], e2['id']], l1=l1, l2=l2)
            if pc: out.append(pc)
        else:
            e1 = max((x[0] for x in lst), key=lambda e: e['de'])
            p = next(x[1] for x in lst if x[0] is e1)                 # no eixo do tubo maior
            out.append({'E': float(p[0]), 'N': float(p[1]), 'z': float(p[2]), 'disc': disc, 'rede': rede, 'de': e1['de'], 'tipo': 'junção',
                        'angulo': None, 'comercial': None, 'fora': False, 'plano': 'horizontal', 'u1': [float(x) for x in -lst[0][2]],
                        'u2': [float(x) for x in lst[1][2]], 'ramais': [[float(x) for x in d] for _, _, d, _ in lst], 'origens': [[float(x) for x in pp] for _, pp, _, _ in lst], 'elementos': [x[0]['id'] for x in lst],
                        'lmin': min(x[3] for x in lst), 'material': e1['info'].get('material')})
    # ponta que chega no MEIO de outro trecho da mesma rede (fora de caixa): junção no ponto (Revisão de qualidade: DRE-127)
    pontas_livres = [(k, lst) for k, lst in nos.items() if len(lst) == 1]
    for (rede, disc, _, _, _), lst in pontas_livres:
        e, p, d, l = lst[0]
        if _dentro_de_caixa(p, caixas, disc): continue
        for o in E:
            if o is e or o['rede'] != rede: continue
            P = o[campo]
            if np.any(P.min(0) - 0.3 > p) or np.any(P.max(0) + 0.3 < p): continue
            for a, b in zip(P[:-1], P[1:]):
                ab = b - a; L2 = float(ab @ ab)
                if L2 < 1e-8: continue
                s = float(np.clip((p - a) @ ab / L2, 0, 1)); q = a + ab * s
                if 0.02 < s < 0.98 and np.linalg.norm(q - p) < o['de'] / 2 + e['de'] / 2 + 0.03:
                    u = _unit(ab)
                    out.append({'E': float(q[0]), 'N': float(q[1]), 'z': float(q[2]), 'disc': disc, 'rede': rede, 'de': max(e['de'], o['de']),
                                'tipo': 'junção', 'angulo': None, 'comercial': None, 'fora': False, 'plano': 'horizontal', 'u1': [float(x) for x in u],
                                'u2': [float(x) for x in d], 'ramais': [[float(x) for x in -u], [float(x) for x in u], [float(x) for x in d]],
                                'elementos': [o['id'], e['id']], 'lmin': min(l, float(np.sqrt(L2))), 'material': o['info'].get('material')})
                    break
            else:
                continue
            break
    # uma peça por ponto: no mesmo lugar (5 cm) da mesma rede fica a junção ou a curva de maior ângulo (Revisão: peças sobrepostas)
    out.sort(key=lambda pc: (pc['tipo'] != 'junção', -(pc['angulo'] or 0)))
    final = []
    for pc in out:
        if any(q['rede'] == pc['rede'] and np.linalg.norm([q['E'] - pc['E'], q['N'] - pc['N'], q['z'] - pc['z']]) < 0.05 for q in final): continue
        final.append(pc)
    return final


def resumo(pecas):
    c = collections.Counter((p['disc'], p['tipo'], p['comercial']) for p in pecas)
    fora = sum(p['fora'] for p in pecas)
    return c, fora


def ajustar_vertices(E, caixas, regras, campo='pts_sol', max_desloc=0.15, log=print):
    """DESLIGADO por padrão (REGRAS['ajustar_vertices']): a regra do dono do projeto é não mexer no traçado em planta já entregue; use a
    combinação de duas peças ou a peça mais próxima com a deflexão no Pset. vértice cujo ângulo não casa com peça comercial (nem combinação de duas) a 'tol': o vértice anda em PLANTA, entre os vizinhos
    fixos, até o ângulo comercial mais próximo (arco capaz da corda); a cota não muda. Só vértice interno ou nó entre dois trechos,
    fora de caixa, com deslocamento até 'max_desloc' (Revisão de qualidade da escola A, 20/10/2026)."""
    cfg = dict(PADRAO, **(regras.get('conexoes') or {}))
    pares = sorted(cfg['angulos'])          # o vértice vai para o ângulo de UMA peça comercial
    nos = collections.defaultdict(list)
    for e in E:
        P = e[campo]
        if len(P) < 2: continue
        for k in (0, len(P) - 1): nos[(e['rede'], round(float(P[k][0]) / 0.02), round(float(P[k][1]) / 0.02))].append((e, k))
    alvos = []                     # (A, B, C, [(elem, índice)...])
    for e in E:
        P = e[campo]
        for i in range(1, len(P) - 1): alvos.append((e, i - 1, i, i + 1, [(e, i)]))
    for lst in nos.values():
        if len(lst) != 2: continue
        (e1, k1), (e2, k2) = lst
        alvos.append(((e1, k1), (e2, k2)))
    n = 0; maior = 0.0
    for a in alvos:
        if len(a) == 5:
            e, ia, ib, ic, quem = a; P = e[campo]; A, B, C = P[ia], P[ib], P[ic]
        else:
            (e1, k1), (e2, k2) = a; P1, P2 = e1[campo], e2[campo]
            B = P1[k1]; A = P1[1 if k1 == 0 else -2]; C = P2[1 if k2 == 0 else -2]; quem = [(e1, k1), (e2, k2)]; e = e1
        u1 = B - A; u2 = C - B
        if np.linalg.norm(u1[:2]) < 0.05 or np.linalg.norm(u2[:2]) < 0.05: continue
        if abs(u1[2]) > 0.3 * np.linalg.norm(u1) or abs(u2[2]) > 0.3 * np.linalg.norm(u2): continue      # vertical: não mexe
        t1, t2 = u1[:2] / np.linalg.norm(u1[:2]), u2[:2] / np.linalg.norm(u2[:2])
        ang = float(np.degrees(np.arccos(np.clip(t1 @ t2, -1, 1))))
        flex = any(s in str(e['info'].get('material', '')).lower() for s in cfg.get('materiais_flexiveis', ()))
        lim = cfg.get('flexivel_disc', {}).get(e['disc'], cfg['flexivel']) if flex else cfg['flexivel']
        if ang <= lim: continue
        alvo = min(pares, key=lambda s: abs(s - ang))
        if abs(alvo - ang) <= cfg['tol'] or _dentro_de_caixa(B, caixas, e['disc']): continue
        # arco capaz: pontos que veem AC com o ângulo interno 180 - alvo
        a2, c2, b2 = A[:2], C[:2], B[:2]; corda = c2 - a2; L = np.linalg.norm(corda)
        alfa = np.radians(180.0 - alvo)
        if L < 1e-6 or np.sin(alfa) < 1e-6: continue
        R = L / (2 * np.sin(alfa)); m = (a2 + c2) / 2; nrm = np.array([-corda[1], corda[0]]) / L
        lado = np.sign((b2 - m) @ nrm) or 1.0
        h = np.sqrt(max(R * R - (L / 2) ** 2, 0.0)) * (1 if alfa < np.pi / 2 else -1)
        centro = m + nrm * lado * h
        novo = centro + (b2 - centro) / np.linalg.norm(b2 - centro) * R
        d = float(np.linalg.norm(novo - b2))
        if d > max_desloc: continue
        for el, k in quem:
            el[campo] = el[campo].copy(); el[campo][k][:2] = novo; el.pop('S', None)
            if campo == 'pts_sol' and not el.get('janelas') and not el.get('desvio'): el['pts'] = el['pts'].copy(); el['pts'][k][:2] = novo
        n += 1; maior = max(maior, d)
    if n: log(f'  vértices ajustados ao ângulo comercial: {n} (maior deslocamento em planta {maior * 100:.1f} cm; cota igual)')
    return n
