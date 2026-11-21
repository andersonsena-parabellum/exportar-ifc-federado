# -*- coding: utf-8 -*-
"""Soluções SÓ DE PROFUNDIDADE (o traçado em planta não muda — regra do projeto: traçado novo = executivo novo).
Para cada conflito, a rede que pode mudar de cota (pressurizada, na ordem regras['ordem_mover']) faz um MERGULHO local:
  - janela = trecho em planta onde ela fica a menos de (rA + rB + folga) do obstáculo, + 0,15 m de cada lado;
  - dentro da janela o eixo vai para a cota que dá a folga mínima (por baixo, ou por cima se o recobrimento mínimo deixar);
  - nas pontas da janela, conexão VERTICAL (nunca forçar inclinação — regra do projeto).
Redes por gravidade (ESG, AP, DRE) e caixas ficam fixas. Conflito sem solução dentro dos limites (dz_max, profundidade
máxima, caixa atravessada, duas redes por gravidade) vai para PENDENTES, com o que seria preciso.
Repete clash -> solução até não sobrar conflito resolvível."""
import collections
import numpy as np
from . import clash as cl
from .modelo import comprimento_planta

MARGEM = 0.02          # folga extra na cota (m)
CONEXAO = 0.15         # comprimento extra de cada lado da janela (curva/conexão), m
JUNTA = 0.30           # janelas a menos disso se fundem (evita degrau curto)


def _base(e):
    if 'S' not in e:
        e['S'] = comprimento_planta(e['pts']); e['dips'] = []
    return e['S']


def _pos(e, s):
    S = _base(e); P = e['pts']
    return np.column_stack([np.interp(s, S, P[:, 0]), np.interp(s, S, P[:, 1])])


def _zb(e, s):
    return np.interp(s, _base(e), e['pts'][:, 2])


def janelas(e):
    """funde as janelas que se sobrepõem; 'baixo' manda sobre 'cima'."""
    D = sorted(e.get('dips', []), key=lambda d: d['s0'])
    out = []
    for d in D:
        if out and d['s0'] <= out[-1]['s1'] + JUNTA:
            o = out[-1]; o['s1'] = max(o['s1'], d['s1']); o['motivos'] = o['motivos'] | d['motivos']
            if o['modo'] == d['modo']:
                o['z'] = min(o['z'], d['z']) if d['modo'] == 'baixo' else max(o['z'], d['z'])
            elif d['modo'] == 'baixo':
                o['modo'], o['z'] = 'baixo', d['z']
        else:
            out.append(dict(d, motivos=set(d['motivos'])))
    return out


def reconstruir(e):
    S = _base(e); L = S[-1]
    W = janelas(e)
    br = sorted(set(np.round(S, 6)) | {round(w['s0'], 6) for w in W} | {round(w['s1'], 6) for w in W})
    br = sorted({min(max(b, 0.0), L) for b in br})

    def z_em(s, w):
        z = _zb(e, s)
        if w is None: return z
        return min(z, w['z']) if w['modo'] == 'baixo' else max(z, w['z'])

    pts = []
    for s0, s1 in zip(br[:-1], br[1:]):
        if s1 - s0 < 1e-6: continue
        m = (s0 + s1) / 2
        w = next((w for w in W if w['s0'] - 1e-9 <= m <= w['s1'] + 1e-9), None)
        p0 = _pos(e, [s0])[0]; p1 = _pos(e, [s1])[0]
        a = (p0[0], p0[1], z_em(s0, w)); b = (p1[0], p1[1], z_em(s1, w))
        if not pts or np.linalg.norm(np.subtract(pts[-1], a)) > 1e-6: pts.append(a)
        pts.append(b)
    e['pts_sol'] = np.array(pts)
    e['janelas'] = W


def _amostra_planta(e, passo=0.05):
    S = _base(e); n = max(2, int(np.ceil(S[-1] / passo)) + 1)
    s = np.linspace(0, S[-1], n)
    return s, _pos(e, s)


def _dist_planta_caixa(P, c):
    if c['forma'] == 'c':
        return np.maximum(np.hypot(P[:, 0] - c['E'], P[:, 1] - c['N']) - c['meia'], 0)
    from .modelo import planta_local
    qx, qy = planta_local(c, P[:, 0], P[:, 1]); qx = np.maximum(qx, 0); qy = np.maximum(qy, 0)
    return np.hypot(qx, qy)


PROF_MAX_GERAL = 2.0   # teto do terreno ao topo do tubo; o valor do projeto por escola vem de parametros.py em REGRAS['prof_max_geral'] (EXE 1,5; demais 2,0)


def opcoes(m, obst, conf, regras, ter, caixa=False):
    """opções de mergulho do elemento móvel m para livrar o obstáculo (elemento ou caixa)."""
    folga = regras['folga']; rA = m['de'] / 2
    s, PA = _amostra_planta(m)
    if caixa:
        rO = 0.0; d = _dist_planta_caixa(PA, obst)
    else:
        rO = obst['de'] / 2; Q = cl.amostra(obst['pts_sol'], 0.05)
        d = np.full(len(PA), np.inf)
        for k in range(0, len(Q), 2000):
            dd = np.hypot(PA[:, None, 0] - Q[None, k:k + 2000, 0], PA[:, None, 1] - Q[None, k:k + 2000, 1]); d = np.minimum(d, dd.min(1))
    lim = rA + rO + folga + 0.05
    perto = d < lim
    if not perto.any(): return [], None
    # sequência de amostras próximas que contém o ponto do conflito
    i0 = int(np.argmin(np.hypot(PA[:, 0] - conf['E'], PA[:, 1] - conf['N'])))
    if not perto[i0]: i0 = int(np.nonzero(perto)[0][np.argmin(np.abs(np.nonzero(perto)[0] - i0))])
    a = i0
    while a > 0 and perto[a - 1]: a -= 1
    b = i0
    while b < len(perto) - 1 and perto[b + 1]: b += 1
    s0 = max(0.0, s[a] - CONEXAO); s1 = min(s[-1], s[b] + CONEXAO)
    Wp = PA[a:b + 1]
    if caixa:
        bot, top = obst['zb'], obst['zt']
    else:
        dq = np.full(len(Q), np.inf)
        for k in range(0, len(Wp), 2000):
            dd = np.hypot(Q[:, None, 0] - Wp[None, k:k + 2000, 0], Q[:, None, 1] - Wp[None, k:k + 2000, 1]); dq = np.minimum(dq, dd.min(1))
        zq = Q[dq < lim, 2]
        if not len(zq): zq = Q[[int(np.argmin(dq))], 2]
        bot, top = zq.min() - rO, zq.max() + rO
    zc = float(_zb(m, s[i0]))
    sw = np.linspace(s0, s1, max(2, int((s1 - s0) / 0.25) + 1))
    zt = ter.z(_pos(m, sw))
    zt = np.where(np.isnan(zt), np.nanmin(zt) if np.isfinite(zt).any() else zc + 1, zt)
    ops = []
    existente_baixo = any(w['modo'] == 'baixo' and w['s0'] < s1 and w['s1'] > s0 for w in janelas(m))
    zw = bot - folga - rA - MARGEM
    prof = float(np.max(zt - (np.minimum(_zb(m, sw), zw) + rA)))
    ops.append({'modo': 'baixo', 'z': zw, 'dz': zw - zc, 'prof_topo': prof})
    if not caixa and not existente_baixo:
        zw = top + folga + rA + MARGEM
        cob = float(np.min(zt - (np.maximum(_zb(m, sw), zw) + rA)))
        ops.append({'modo': 'cima', 'z': zw, 'dz': zw - zc, 'cob': cob})
    for o in ops:
        o.update(s0=s0, s1=s1, E=float(PA[i0, 0]), N=float(PA[i0, 1]), z_antes=zc)
        prob = []
        if o['modo'] == 'cima' and o['cob'] < (m.get('cob_min') or 0) - 0.005: prob.append(f"recobrimento ficaria {o['cob']:.2f} m (mín. {m['cob_min']:.2f})")
        if abs(o['dz']) > regras['dz_max'].get(m['disc'], 0.5) + 1e-6: prob.append(f"Δz {o['dz']:+.2f} m passa do limite de {regras['dz_max'].get(m['disc'], 0.5):.2f} m")
        pmax = min(regras['prof_max_topo'].get(m['disc'], 2.0), regras.get('prof_max_geral', PROF_MAX_GERAL))
        if o['modo'] == 'baixo' and o['prof_topo'] > pmax + 1e-6:
            prob.append(f"topo a {o['prof_topo']:.2f} m de profundidade (máx. {pmax:.2f})")
        if o['modo'] == 'cima' and o['dz'] <= 0.005: prob.append('já está acima')
        if o['modo'] == 'baixo' and o['dz'] >= -0.005: prob.append('já está abaixo')
        o['problemas'] = prob
    return ops, (bot, top)


def _desloc_caixa(conf, regras):
    """quanto a caixa teria de andar em planta (perpendicular ao tubo) para ficar com a folga mínima."""
    return max(0.05, regras['folga'] - conf['folga'])


def resolver(elementos, caixas, regras, ter, max_passes=20, log=print):
    ids = {e['id']: e for e in elementos}; cx = {c['id']: c for c in caixas}
    for e in elementos:
        _base(e); e['dips'] = []; e['pts_sol'] = e['pts'].copy(); e['janelas'] = []
    ordem = {d: k for k, d in enumerate(regras['ordem_mover'])}
    pend = {}; tent = collections.Counter(); alertas = []
    chave = lambda c: (c['a'], c['b'])
    for it in range(max_passes):
        conf = [c for c in cl.detectar(elementos, caixas, regras) if not c['ligacao']]
        abertos = [c for c in conf if chave(c) not in pend]
        log(f'  passe {it + 1}: {len(conf)} conflitos ({len(abertos)} a tratar, {len(pend)} pendentes)')
        if not abertos: break
        tocados = collections.defaultdict(list); mexeu = False
        for c in abertos:
            if c['tipo'] == 'caixa×caixa':
                Ca, Cb = cx[c['a']], cx[c['b']]
                estr = regras.get('estrutura', ('EST',))
                mov = [x for x in (Ca, Cb) if x['disc'] in ordem]
                na, nb = Ca['info'].get('nome', Ca['id']), Cb['info'].get('nome', Cb['id'])
                if Ca['disc'] in estr or Cb['disc'] in estr:
                    pend[chave(c)] = dict(c, categoria='estrutura (pilar, viga, fundação)', motivo=f"caixa {na} ({Ca['disc']}) encosta em {nb} ({Cb['disc']})",
                                          necessario='reposicionar a caixa/equipamento ou passagem prevista na estrutura')
                elif mov:
                    m_ = mov[0]
                    pend[chave(c)] = dict(c, categoria='caixa de ELE/PCI no caminho', motivo=f"caixa {na} ({Ca['disc']}) sobre {nb} ({Cb['disc']})",
                                          necessario=f"deslocar a caixa {m_['info'].get('nome', m_['id'])} ≈ {_desloc_caixa(c, regras):.2f} m em planta")
                else:
                    pend[chave(c)] = dict(c, categoria='gravidade × gravidade', motivo=f"caixas {na} ({Ca['disc']}) e {nb} ({Cb['disc']}) sobrepostas",
                                          necessario=f"afastar {regras['folga'] - c['folga']:.2f} m (planta)")
                continue
            A = ids[c['a']]; B = ids.get(c['b']); C = cx.get(c['b'])
            lados = []
            if A['movel'] and A['disc'] in ordem: lados.append((A, C if C else B, C is not None))
            if B is not None and B['movel'] and B['disc'] in ordem: lados.append((B, A, False))
            lados.sort(key=lambda t: ordem[t[0]['disc']])
            est = ((B is not None and (B['disc'] in regras.get('estrutura', ('EST',)) or B['tipo'] == 'estrutura')) or
                   (C is not None and C['disc'] in regras.get('estrutura', ('EST',))) or A['disc'] in regras.get('estrutura', ('EST',)))
            if not lados:
                if est:
                    obs = (C['info'].get('nome', C['id']) if C is not None else (B['trecho'] if B is not None else ''))
                    pend[chave(c)] = dict(c, categoria='estrutura (pilar, viga, fundação)', motivo=f"rede fixa {A['trecho']} ({A['disc']}) encosta na estrutura {obs}",
                                          necessario='passagem/furo previsto na estrutura (projetista estrutural) ou desvio da rede')
                elif C is not None and C['disc'] in ordem:
                    pend[chave(c)] = dict(c, categoria='caixa de ELE/PCI no caminho', motivo=f"caixa {C['info'].get('nome', C['id'])} ({C['disc']}) encosta na rede por gravidade {A['trecho']}",
                                          necessario=f"deslocar a caixa ≈ {_desloc_caixa(c, regras):.2f} m em planta (ajuste pequeno de traçado da {C['disc']})")
                else:
                    pend[chave(c)] = dict(c, categoria='gravidade × gravidade', motivo='duas redes por gravidade (cotas do projeto): ajuste no projeto hidrossanitário',
                                          necessario=f"afastar {regras['folga'] - c['folga']:.2f} m (cota ou planta)")
                continue
            if not regras.get('mergulho_local', True):
                # parâmetro de 19/10/2026: sem mergulho pontual; a cota das pressurizadas vem do estudo (estudo.py)
                m, o, ehcx = lados[0]
                oq = (o['info'].get('nome', o['id']) if ehcx else o['trecho']) if o is not None else ''
                cat = ('estrutura (pilar, viga, fundação)' if est else 'estudo de cota: sem cota livre')
                pend[chave(c)] = dict(c, categoria=cat, motivo=f"{m['trecho']} ({m['disc']}) na cota do estudo ainda encosta em {oq}",
                                      necessario=f"mudar a cota do trecho/rede {m['trecho']} ({m['disc']}) no estudo, deslocar a caixa ou desviar em planta")
                continue
            escolha = None; melhor_inviavel = None
            for m, o, ehcx in lados:
                ops, _ = opcoes(m, o, c, regras, ter, caixa=ehcx)
                ok = [p for p in ops if not p['problemas']]
                if ok:
                    escolha = (m, o, min(ok, key=lambda p: abs(p['dz']))); break
                for p in ops:
                    if 'já está' in ' '.join(p['problemas']): continue
                    if melhor_inviavel is None or abs(p['dz']) < abs(melhor_inviavel[2]['dz']): melhor_inviavel = (m, o, p)
            if escolha is None and regras.get('profundo', True):
                # regra de 19/10/2026 (dono do projeto e sócio de modelagem): pode ir mais fundo que o usual para não mudar o traçado em planta
                # 19/10/2026 (dono do projeto): "até 1,5 m" — o mergulho mais fundo não passa de 1,5 m do terreno ao topo do tubo
                rp = dict(regras, dz_max={d: max(v, regras.get('dz_max_profundo', regras.get('prof_max_geral', PROF_MAX_GERAL))) for d, v in regras['dz_max'].items()},
                          prof_max_topo={d: regras.get('prof_max_profundo', regras.get('prof_max_geral', PROF_MAX_GERAL)) for d in regras['prof_max_topo']})
                for m, o, ehcx in lados:
                    ok = [p for p in opcoes(m, o, c, rp, ter, caixa=ehcx)[0] if not p['problemas']]
                    if ok:
                        escolha = (m, o, min(ok, key=lambda p: abs(p['dz']))); break
            if escolha is None:
                txt = '; '.join(melhor_inviavel[2]['problemas']) if melhor_inviavel else 'sem opção de cota'
                quem = f"{melhor_inviavel[0]['id']} {'por baixo' if melhor_inviavel[2]['modo'] == 'baixo' else 'por cima'}, Δz {melhor_inviavel[2]['dz']:+.2f} m" if melhor_inviavel else ''
                if est:
                    cat = 'estrutura (pilar, viga, fundação)'; nec = f"desviar {A['trecho']} ({A['disc']}) em volta da estrutura ou prever passagem/furo (projetista estrutural)" + (f", ou {quem}" if quem else '')
                elif C is not None and C['disc'] in ordem:
                    cat = 'caixa de ELE/PCI no caminho'; nec = f"deslocar a caixa {C['info'].get('nome', C['id'])} ≈ {_desloc_caixa(c, regras):.2f} m em planta, ou {quem}"
                elif C is not None:
                    cat = 'exige desvio em planta (atravessa PV/CI/CA)'; nec = f"desvio em planta de {A['trecho']} ({A['disc']}) em volta da caixa {C['info'].get('nome', C['id'])}, ou {quem}"
                else:
                    cat = 'Δz acima do limite'; nec = (quem + ' (aceitar o Δz maior ou desviar em planta)') if quem else 'desvio em planta'
                pend[chave(c)] = dict(c, categoria=cat, motivo='não se resolve só com profundidade dentro dos limites: ' + txt, necessario=nec)
                continue
            m, o, p = escolha
            if any(p['s0'] < t1 + JUNTA and p['s1'] > t0 - JUNTA for t0, t1 in tocados[m['id']]): continue   # no próximo passe
            k = (m['id'], o['id'])
            tent[k] += 1
            if tent[k] > 4:
                pend[chave(c)] = dict(c, categoria='Δz acima do limite', motivo='mergulho não convergiu (obstáculos em cotas conflitantes)', necessario='ver no 3D')
                continue
            m['dips'].append({'s0': p['s0'], 's1': p['s1'], 'z': p['z'], 'modo': p['modo'], 'motivos': {o['id']}})
            reconstruir(m); tocados[m['id']].append((p['s0'], p['s1'])); mexeu = True
            if m['disc'] == 'AF' and p['modo'] == 'baixo' and (o.get('disc') in regras.get('agua_acima_de', [])):
                alertas.append(f"{m['id']} passa por baixo de {o['id']} (água sob esgoto: exige proteção/encamisamento ou outra solução)")
        if not mexeu: break
    final = cl.detectar(elementos, caixas, regras)
    return final, list(pend.values()), alertas


def solucoes(elementos, ter):
    """uma linha por janela de mergulho aplicada."""
    out = []
    for e in elementos:
        for w in e.get('janelas', []):
            sm = (w['s0'] + w['s1']) / 2; p = _pos(e, [sm])[0]
            z0 = float(_zb(e, sm)); z1 = min(z0, w['z']) if w['modo'] == 'baixo' else max(z0, w['z'])
            zt = float(ter.z([p])[0]); r = e['de'] / 2
            out.append({'elemento': e['id'], 'disc': e['disc'], 'trecho': e['trecho'], 'modo': 'passa por baixo' if w['modo'] == 'baixo' else 'passa por cima',
                        'E': p[0], 'N': p[1], 's0': w['s0'], 's1': w['s1'], 'extensao': w['s1'] - w['s0'],
                        'eixo_antes': z0, 'eixo_depois': z1, 'dz': z1 - z0, 'terreno': zt,
                        'prof_topo_antes': zt - (z0 + r), 'prof_topo_depois': zt - (z1 + r), 'motivos': sorted(w['motivos'])})
    return out
