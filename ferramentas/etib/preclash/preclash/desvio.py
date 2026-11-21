# -*- coding: utf-8 -*-
"""Desvios EM PLANTA testados (passo seguinte às soluções só de profundidade).
Só para o que a profundidade não resolve:
  - CONTORNO: rede pressurizada que passa por dentro de PV/CI/CA (pendente 'exige desvio em planta'):
    o trecho afetado é deslocado lateralmente (testa ±0,4 a ±3,0 m, transições a 45°, pontas do trecho fixas),
    a cota é refeita pelo recobrimento mínimo e o candidato é testado contra tudo; fica o de menor custo.
  - CAIXA DESLOCADA: caixa de passagem de ELE/SDAI que encosta em outra rede: a caixa anda perpendicular ao tubo
    (e as pontas dos eletrodutos que chegam nela vão junto).
Depois disto o solver de profundidade roda de novo sobre o traçado novo.
Cada desvio muda o traçado da disciplina (executivo novo): a saída agrupa por disciplina."""
import copy, collections
import numpy as np
from . import clash as cl
from .modelo import comprimento_planta
from .leitura import perfil_por_recobrimento

OFFSETS = [0.4, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
JUNTAR = 12.0          # conflitos a menos disso no mesmo trecho viram um único desvio (m)
PONTA = 0.30           # distância mínima das pontas do trecho (as ligações não mudam)


def _proj_s(P2, S, q):
    best = (1e18, 0.0)
    for a, b, s0 in zip(P2[:-1], P2[1:], S[:-1]):
        d = b - a; L2 = d @ d
        t = 0.0 if L2 < 1e-12 else float(np.clip((q - a) @ d / L2, 0, 1))
        dist = np.linalg.norm(a + d * t - q)
        if dist < best[0]: best = (dist, s0 + t * np.sqrt(L2))
    return best[1]


def _deslocar(P2, s0, s1, o, passo=0.5):
    """desloca o eixo 2D entre s0 e s1 de o (m, + = esquerda), com rampas de comprimento |o| (45°)."""
    S = comprimento_planta(np.column_stack([P2, np.zeros(len(P2))]))
    L = S[-1]; T = abs(o)
    a0, a1 = max(PONTA, s0 - T), min(L - PONTA, s1 + T)
    ss = sorted(set(np.round(np.concatenate([S, np.arange(0, L, passo), [a0, s0, s1, a1]]), 4)))
    ss = [s for s in ss if 0 <= s <= L]
    out = []
    for s in ss:
        k = min(int(np.searchsorted(S, s, side='right')) - 1, len(P2) - 2); k = max(k, 0)
        a, b = P2[k], P2[k + 1]; d = b - a; Lk = np.linalg.norm(d)
        t = 0 if Lk < 1e-9 else (s - S[k]) / Lk
        p = a + d * t
        n = np.array([-d[1], d[0]]) / (Lk + 1e-12)
        # no vértice: normal média (meia-esquadria)
        if abs(s - S[k]) < 1e-6 and k > 0:
            d0 = P2[k] - P2[k - 1]; n0 = np.array([-d0[1], d0[0]]) / (np.linalg.norm(d0) + 1e-12)
            m = n0 + n; m /= (np.linalg.norm(m) + 1e-12); n = m / max(0.5, m @ n)
        if s <= a0 or s >= a1: w = 0.0
        elif s < s0: w = (s - a0) / max(s0 - a0, 1e-9)
        elif s > s1: w = (a1 - s) / max(a1 - s1, 1e-9)
        else: w = 1.0
        out.append(p + n * o * w)
    Q = np.array(out)
    keep = [0]
    for i in range(1, len(Q) - 1):          # tira pontos colineares
        u = Q[i] - Q[keep[-1]]; v = Q[i + 1] - Q[i]
        if abs(u[0] * v[1] - u[1] * v[0]) > 1e-4 * (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12) or np.linalg.norm(u) > 25: keep.append(i)
    keep.append(len(Q) - 1)
    return Q[keep]


def cruzamentos_sit(Q, arq):
    """quantas linhas da SIT (meio-fio, muro, parede…) o eixo 2D Q cruza — indicador de invasão de edificação/rua."""
    if not len(arq) or len(Q) < 2: return 0
    lo = Q.min(0) - 1; hi = Q.max(0) + 1
    m = (arq[:, :, 0].max(1) >= lo[0]) & (arq[:, :, 0].min(1) <= hi[0]) & (arq[:, :, 1].max(1) >= lo[1]) & (arq[:, :, 1].min(1) <= hi[1])
    A = arq[m]
    if not len(A): return 0
    n = 0
    p, q = A[:, 0], A[:, 1]
    cr = lambda o, a, b: (a[..., 0] - o[..., 0]) * (b[..., 1] - o[..., 1]) - (a[..., 1] - o[..., 1]) * (b[..., 0] - o[..., 0])
    for a_, b_ in zip(Q[:-1], Q[1:]):
        d1 = cr(p, q, a_[None]); d2 = cr(p, q, b_[None]); d3 = cr(a_[None], b_[None], p); d4 = cr(a_[None], b_[None], q)
        n += int(np.sum((d1 * d2 < 0) & (d3 * d4 < 0)))
    return n


def _vizinhos(e, E, C, raio=6.0):
    lo = e['pts'][:, :2].min(0) - raio; hi = e['pts'][:, :2].max(0) + raio
    ev = [x for x in E if x['id'] != e['id'] and np.all(x['pts'][:, :2].max(0) >= lo) and np.all(x['pts'][:, :2].min(0) <= hi)]
    cv = [c for c in C if lo[0] <= c['E'] <= hi[0] and lo[1] <= c['N'] <= hi[1]]
    return ev, cv


def _custo(e, E, C, regras):
    ev, cv = _vizinhos(e, E, C)
    conf = [c for c in cl.detectar([e] + ev, cv, regras, campo='pts') if not c['ligacao'] and e['id'] in (c['a'], c['b'])]
    ids = {x['id']: x for x in ev}
    custo = 0.0; fixos = 0
    for c in conf:
        outro = c['b'] if c['a'] == e['id'] else c['a']
        caixa = outro not in ids                      # caixa no caminho: só planta resolve
        grav = not caixa and not ids[outro]['movel']  # cruzamento com gravidade: o mergulho resolve depois
        if c['gravidade'] == 'CRÍTICA':
            custo += 100 if caixa else (5 if grav else 2); fixos += caixa
        else:
            custo += 10 if caixa else 1
    return custo, fixos, conf


def contornos(E, C, pend, regras, ter, log=print):
    ids = {e['id']: e for e in E}
    alvo = collections.defaultdict(list)
    for p in pend:
        if p.get('categoria', '').startswith('exige desvio') and p['a'] in ids and ids[p['a']]['movel']:
            alvo[p['a']].append(p)
    feitos = []
    for eid, ps in alvo.items():
        e = ids[eid]
        for _ in range(3):                                   # até 3 trechos desviados no mesmo elemento
            P2 = e['pts'][:, :2]; S = comprimento_planta(e['pts'])
            c0, f0, conf0 = _custo(e, E, C, regras)
            fix = [c for c in conf0 if c['gravidade'] == 'CRÍTICA' and c['b'] not in ids and c['a'] == eid]
            if not fix: break
            ss = sorted(_proj_s(P2, S, np.array([c['E'], c['N']])) for c in fix)
            grupo = [ss[0]]
            for s in ss[1:]:
                if s - grupo[-1] < JUNTAR: grupo.append(s)
                else: break
            ext = 1.2
            n_sit0 = cruzamentos_sit(P2, ter.arq)
            vaos = {(max(PONTA, grupo[0] - ext), min(S[-1] - PONTA, grupo[-1] + ext)), (max(PONTA, ss[0] - ext), min(S[-1] - PONTA, ss[-1] + ext))}
            melhor = None
            for s0, s1 in vaos:
                for o in OFFSETS:
                    for sg in (1, -1):
                        Q = _deslocar(P2, s0, s1, sg * o)
                        try:
                            P3 = perfil_por_recobrimento(Q, e['de'], e['cob_min'] or 0.3, ter)
                        except ValueError:
                            continue
                        cand = dict(e, pts=P3)
                        c, f, _ = _custo(cand, E, C, regras)
                        acres = comprimento_planta(P3)[-1] - S[-1]
                        sit = max(0, cruzamentos_sit(Q, ter.arq) - n_sit0)
                        custo = c + 2 * o + 0.5 * acres + 20 * sit
                        if melhor is None or custo < melhor[0]: melhor = (custo, f, sg * o, P3, acres, s0, s1, sit)
            if melhor is None or melhor[1] >= f0:
                feitos.append({'tipo': 'contorno', 'elemento': eid, 'disc': e['disc'], 'trecho': e['trecho'], 'status': 'sem desvio que resolva (ver no 3D)',
                               'E': fix[0]['E'], 'N': fix[0]['N'], 's0': ss[0], 's1': ss[-1], 'desloc': None, 'acrescimo': None, 'linhas_sit': None,
                               'evitados': sorted({c['b'] for c in fix}), 'fixos_antes': f0, 'fixos_depois': f0})
                break
            s0, s1 = melhor[5], melhor[6]
            antes = e['pts']
            e['pts'] = melhor[3]; e['pts_sol'] = melhor[3].copy(); e.pop('S', None)
            e.setdefault('desvio', []).append({'s0': s0, 's1': s1, 'o': melhor[2]})
            e['pts_original'] = e.get('pts_original', antes)
            pm = antes[np.argmin(np.abs(S - (s0 + s1) / 2))]
            feitos.append({'tipo': 'contorno', 'elemento': eid, 'disc': e['disc'], 'trecho': e['trecho'], 'status': 'aplicado',
                           'E': float(pm[0]), 'N': float(pm[1]), 's0': s0, 's1': s1, 'desloc': melhor[2], 'acrescimo': melhor[4], 'linhas_sit': melhor[7],
                           'evitados': sorted({c['b'] for c in fix}), 'fixos_antes': f0, 'fixos_depois': melhor[1]})
            log(f"  contorno {eid}: {melhor[2]:+.2f} m entre {s0:.1f} e {s1:.1f} m; colisões com caixas {f0} -> {melhor[1]}; linhas da SIT a mais: {melhor[7]}")
    return feitos


def mover_caixas(E, C, pend, regras, log=print, ter=None):
    """desloca caixa de ELE/SDAI (e de DRE/ESG com 'caixas_moveis_grav') que encosta em outra rede. Só colisão de fato
    (REGRAS['mover_so_colisao'], padrão sim); equipamento (poste, quadro, abrigo) não anda; a caixa de passagem que andou fica
    com a tampa no terreno do lugar novo (ajustes da escola A, 19/10/2026)."""
    cx = {c['id']: c for c in C}; ids = {e['id']: e for e in E}
    eq = {c['id'] for c in C if c['info'].get('equipamento')}
    pend = [p for p in pend if p['a'] not in eq and p['b'] not in eq and (p['folga'] < cl.TOL or not regras.get('mover_so_colisao', True))]
    feitos = []; vistos = set()
    grav = list(regras.get('caixas_moveis_grav') or [])     # 19/10/2026: gravidade × gravidade -> desloca a caixa de DRE/ESG
    for p in sorted(pend, key=lambda p: p['folga']):
        cat = p.get('categoria', '')
        eh_grav = bool(grav) and cat.startswith('gravidade')
        if not (cat.startswith('caixa de ELE') or eh_grav) or p['b'] not in cx: continue
        if eh_grav and p.get('tipo') != 'caixa×caixa' and cx[p['b']]['disc'] not in grav: continue
        dmax = regras.get('desloc_max_grav', 0.60) if eh_grav else 1.5
        outra = None
        if p.get('tipo') == 'caixa×caixa':                      # caixa de ELE/SDAI em cima de outra caixa: a móvel anda
            ordem = grav if eh_grav else regras['ordem_mover']
            if cx[p['a']]['disc'] not in ordem and cx[p['b']]['disc'] not in ordem: continue
            c, outra = (cx[p['a']], cx[p['b']]) if cx[p['a']]['disc'] in ordem else (cx[p['b']], cx[p['a']])
            if c['id'] in vistos: continue
            v = np.array([c['E'] - outra['E'], c['N'] - outra['N']])
            if np.linalg.norm(v) < 1e-3: v = np.array([1.0, 0.0])
        else:
            if p['b'] in vistos: continue
            c = cx[p['b']]; A = ids.get(p['a'])
            if A is None: continue
            Q = cl.amostra(A['pts_sol'], 0.05); k = int(np.argmin(np.hypot(Q[:, 0] - c['E'], Q[:, 1] - c['N'])))
            v = np.array([c['E'], c['N']]) - Q[k, :2]
            if np.linalg.norm(v) < 1e-3:
                t = Q[min(k + 1, len(Q) - 1), :2] - Q[max(k - 1, 0), :2]; v = np.array([-t[1], t[0]])
        vistos.add(c['id'])
        v = v / (np.linalg.norm(v) + 1e-12)
        ligados = [(e, i) for e in E if e['rede'] == c['rede'] for i in (0, len(e['pts']) - 1)
                   if np.hypot(e['pts'][i, 0] - c['E'], e['pts'][i, 1] - c['N']) < c['meia'] + 0.6]

        def avaliar(d):
            c2 = dict(c, E=c['E'] + v[0] * d, N=c['N'] + v[1] * d)
            sd = [float(np.min(cl.sd_caixa(cl.amostra(e['pts_sol'], 0.05), c2) - e['de'] / 2)) for e in E if e['rede'] != c['rede']]
            sd += [cl.folga_caixas(c2, o)[0] for o in C if o['rede'] != c['rede'] and o['id'] != c['id']
                   and np.hypot(o['E'] - c2['E'], o['N'] - c2['N']) < o['meia'] + c2['meia'] + 1.0]
            return min(sd) if sd else 9.0, c2
        f_antes = avaliar(0)[0]
        escolha = None
        for d in np.arange(max(0.05, regras['folga'] - p['folga']), dmax + 0.05, 0.05):
            f, c2 = avaliar(float(d))
            if f >= regras['folga'] - 1e-3: escolha = (float(d), c2, f); break
        if escolha is None:
            feitos.append({'tipo': 'caixa deslocada', 'elemento': c['id'], 'disc': c['disc'], 'trecho': c['info'].get('nome'), 'status': f"não achou posição até {dmax:.2f} m".replace('.', ','),
                           'E': c['E'], 'N': c['N'], 'desloc': None, 'acrescimo': None, 'evitados': [p['a']], 'fixos_antes': 1, 'fixos_depois': 1})
            continue
        d, c2, f = escolha
        c['E0'], c['N0'] = c.get('E0', c['E']), c.get('N0', c['N'])
        c['E'], c['N'] = c2['E'], c2['N']
        if ter is not None and c['disc'] not in grav:
            dz = float(ter.z([[c['E'], c['N']]])[0] - ter.z([[c['E0'], c['N0']]])[0])
            if np.isfinite(dz): c['zt'] += dz; c['zb'] = min(c['zb'] + dz, c['zb'])
        for e, i in ligados:
            e['pts_original'] = e.get('pts_original', e['pts'].copy())
            e['pts'] = e['pts'].copy(); e['pts'][i, 0] += v[0] * d; e['pts'][i, 1] += v[1] * d
            e['pts_sol'] = e['pts'].copy(); e.pop('S', None); e.setdefault('desvio', []).append({'caixa': c['id']})
        feitos.append({'tipo': 'caixa deslocada', 'elemento': c['id'], 'disc': c['disc'], 'trecho': c['info'].get('nome'), 'status': 'aplicado',
                       'E': c['E0'], 'N': c['N0'], 'desloc': d, 'acrescimo': None, 'evitados': [p['a']], 'fixos_antes': int(f_antes < regras['folga']), 'fixos_depois': 0,
                       'ligados': [e['id'] for e, i in ligados]})
        log(f"  caixa {c['id']}: anda {d:.2f} m (folga {f_antes:.2f} -> {f:.2f}); {len(ligados)} trechos acompanham")
    return feitos


def aplicar(E, C, pend, regras, ter, log=print):
    """modifica E e C no lugar; devolve a lista de desvios propostos."""
    cont = contornos(E, C, pend, regras, ter, log) if regras.get('contornos', True) else []
    try:
        mov = mover_caixas(E, C, pend, regras, log, ter=ter)
    except TypeError:                     # mover_caixas trocado por um adaptador antigo (sem 'ter')
        mov = mover_caixas(E, C, pend, regras, log)
    return cont + mov
