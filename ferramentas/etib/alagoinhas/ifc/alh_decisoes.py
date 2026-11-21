# -*- coding: utf-8 -*-
"""Alagoinhas R03 — decisões do Anderson e do Daniel nas 25 fichas da página de pendências (22/10/2026,
<link privado da página>, coleção "decisoes"). Cada ficha -> uma ação:

  antes do estudo de cota (carregar):
    caixas que andam, com as pontas das redes da mesma disciplina que chegam nelas (fichas 6, 7, 20, 24):
      EL2-CX06 (elétrica, sai de cima do PV12), PV27 (drenagem, sai do ESG-11), caixa de esgoto na ponta sul do ESG-11
      (o ESG-11 sai do PV28), PV20 (drenagem, sai do PVE-08);
    desvio a 45° da drenagem em volta de caixa de esgoto (fichas 3 e 23): DRN-120 em volta do PVE-02 e o nó DRN-237/238
      fora da CI-15 (os dois tubos seguem até as caixas deles);
  depois do estudo (desvio.aplicar):
    desvio lateral dos trechos de pressão aceitos (fichas 2, 12, 14, 15, 18, 21, 22, 25 e 10 pelo mesmo desvio da EL1-044):
      EL1-067, T11, T01, EL1-044, SDAI S09, EL2-030, T16;
    cota da gravidade (fichas 5, 8, 9, 11, 13, 16): DRN-167, ESG-36, DRN-376 (só a chegada), DRN-374, DRN-122, DRN-237 —
      o tubo inteiro sobe (se o recobrimento deixar) ou desce o mínimo para sair do cruzamento, a caixa de jusante acompanha
      o fundo;
    ficha 17: a rede AL (AL-02) o mais rasa possível sem colisão nova e com a elétrica por cima; se não resolver, cota do ESG-11;
  ficam para o projetista (fichas 1, 4, 19): DRN-164 × CX03, DRN-165 × reservatório, ESG-07 × DRN-191.
Registro: <SAIDA>/ALI_decisoes.json (alh_mudancas junta às mudanças das pranchas)."""
import os, json, math
import numpy as np
from preclash import clash as cl, modelo as md, desvio as dv
from preclash.modelo import comprimento_planta as cp
from preclash.leitura import perfil_por_recobrimento as perfil

REG = []
FOLGA = 0.20
TRECHOS_LATERAIS = {'EL1-067', 'T11', 'T01', 'EL1-044', 'SDAI S09', 'EL2-030', 'T16'}
COTA_GRAV = {'DRN-167': 'tubo', 'ESG-36': 'tubo', 'DRN-376': 'chegada', 'DRN-374': 'tubo', 'DRN-122': 'tubo', 'DRN-237': 'tubo'}
br = lambda v: ('%.2f' % v).replace('.', ',')


def _cx(C, nome):
    return next((c for c in C if c['info'].get('nome') == nome or c['id'].split(':')[-1] == nome), None)


def _criticos(alvo_ids, E, C, regras, campo='pts'):
    """colisões críticas (sem as ligações) que envolvem os elementos/caixas de alvo_ids, só com a vizinhança."""
    xs = [e for e in E if e['id'] in alvo_ids]; cs = [c for c in C if c['id'] in alvo_ids]
    pts = [e[campo][:, :2] for e in xs] + [np.array([[c['E'], c['N']]]) for c in cs]
    if not pts: return []
    lo = np.vstack(pts).min(0) - 6; hi = np.vstack(pts).max(0) + 6
    ev = [e for e in E if e['id'] in alvo_ids or (np.all(e[campo][:, :2].max(0) >= lo) and np.all(e[campo][:, :2].min(0) <= hi))]
    cv = [c for c in C if c['disc'] != 'EST' and lo[0] <= c['E'] <= hi[0] and lo[1] <= c['N'] <= hi[1]]
    return [c for c in cl.detectar(ev, cv, regras, campo=campo) if not c['ligacao'] and c['gravidade'] == 'CRÍTICA'
            and (c['a'] in alvo_ids or c['b'] in alvo_ids)]


def _pontas_na_caixa(c, E, disc):
    out = []
    for e in E:
        if e['disc'] != disc: continue
        for k in (0, -1):
            qx, qy = md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])
            if qx < 0.15 and qy < 0.15: out.append((e, k))
    return out


def mover_caixa(E, C, nome, regras, longe_de=(), dmax=1.5, log=print):
    """anda a caixa o mínimo (passos de 0,05 m, rosa de 15°) até ela e as redes dela não terem colisão crítica com as
    caixas/redes 'longe_de' nem colisão nova; as pontas das redes da mesma disciplina que chegam nela acompanham (só planta)."""
    c = _cx(C, nome)
    if c is None: log(f'  decisão: caixa {nome} não encontrada'); return None
    pontas = _pontas_na_caixa(c, E, c['disc'])
    ids = {c['id']} | {e['id'] for e, _ in pontas}
    alvo = {x['id'] for x in E + C if x.get('trecho', x['info'].get('nome') if 'info' in x else None) in longe_de or (x['info'].get('nome') if 'info' in x else None) in longe_de}
    base = {(k['a'], k['b']) for k in _criticos(ids, E, C, regras)}
    E0, N0 = c['E'], c['N']; P0 = [(e, k, e['pts'][k, :2].copy()) for e, k in pontas]
    melhor = None
    for d in np.arange(0.05, dmax + 1e-6, 0.05):
        for a in np.radians(np.arange(0, 360, 15)):
            v = d * np.array([math.cos(a), math.sin(a)])
            c['E'], c['N'] = E0 + v[0], N0 + v[1]
            for e, k, p in P0: e['pts'][k, :2] = p + v
            ks = _criticos(ids, E, C, regras)
            ruim = [k for k in ks if k['a'] in alvo or k['b'] in alvo]
            novos = [k for k in ks if (k['a'], k['b']) not in base]
            if not ruim and not novos: melhor = v; break
        if melhor is not None: break
    if melhor is None:
        c['E'], c['N'] = E0, N0
        for e, k, p in P0: e['pts'][k, :2] = p
        log(f'  decisão: caixa {nome} sem lugar livre até {dmax:.2f} m'); return None
    c['E'], c['N'] = E0 + melhor[0], N0 + melhor[1]; c['E0'], c['N0'] = E0, N0
    for e, k, p in P0:
        e['pts'][k, :2] = p + melhor; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    REG.append(dict(tipo='caixa deslocada', disc=c['disc'], elemento=c['id'], trecho=nome, de=[E0, N0], E=c['E'], N=c['N'],
                    lado=round(2 * c.get('mx', c['meia']), 3), lado_y=round(2 * c.get('my', c['meia']), 3), rot=float(c.get('rot', 0.0)),
                    forma=c['forma'], desloc=round(float(np.hypot(*melhor)), 2), tubos=[e['trecho'] for e, _ in pontas]))
    log(f"  decisão: caixa {nome} anda {np.hypot(*melhor):.2f} m; {len(pontas)} pontas acompanham")
    return melhor


def _perfil_grav(P_novo2, P_antigo):
    """cotas do tubo de gravidade no traçado novo: a mesma declividade, de ponta a ponta (z pela fração do comprimento)."""
    S0 = cp(P_antigo); S1 = cp(np.column_stack([P_novo2, np.zeros(len(P_novo2))]))
    z = np.interp(S1 / max(S1[-1], 1e-9), S0 / max(S0[-1], 1e-9), P_antigo[:, 2])
    return np.column_stack([P_novo2, z])


def desviar_grav(E, C, trecho, caixa, regras, log=print):
    """desvio a 45° do tubo de gravidade em volta da caixa (decisão: "ao chegar na caixa, desvio de 45°, desviar da caixa,
    voltar ao sentido original"): o trecho do tubo junto da caixa anda de lado com rampas a 45°; as pontas ficam."""
    e = next((x for x in E if x['trecho'] == trecho and x['tipo'] == 'gravidade'), None); c = _cx(C, caixa)
    if e is None or c is None: log(f'  decisão: {trecho}/{caixa} não encontrado'); return False
    P2 = e['pts'][:, :2]; S = cp(e['pts']); s_c = dv._proj_s(P2, S, np.array([c['E'], c['N']]))
    ids = {e['id']}; base = {(k['a'], k['b']) for k in _criticos(ids, E, C, regras)}
    melhor = None
    for meia in (0.6, 0.9, 1.2, 1.6):
        s0, s1 = max(0.31, s_c - meia), min(S[-1] - 0.31, s_c + meia)
        if s1 <= s0: continue
        for o in (0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2):
            for sg in (1, -1):
                Q = dv._deslocar(P2, s0, s1, sg * o)
                P3 = _perfil_grav(Q, e['pts'])
                ks = _criticos(ids, [dict(e, pts=P3) if x is e else x for x in E], C, regras)
                if any(c['id'] in (k['a'], k['b']) for k in ks): continue
                novos = [k for k in ks if (k['a'], k['b']) not in base]
                chave = (len(novos), o, abs(s1 - s0))
                if melhor is None or chave < melhor[0]: melhor = (chave, P3, sg * o)
    if melhor is None: log(f'  decisão: {trecho} sem desvio que tire da {caixa}'); return False
    e['pts_original'] = e['pts'].copy(); e['pts'] = melhor[1]; e['pts_sol'] = melhor[1].copy(); e.pop('S', None)
    REG.append(dict(tipo='contorno', disc=e['disc'], elemento=e['id'], trecho=trecho, antigo=e['pts_original'][:, :2].tolist(),
                    novo=e['pts'][:, :2].tolist(), desloc=float(melhor[2]), caixa=caixa))
    log(f'  decisão: {trecho} desvia {abs(melhor[2]):.2f} m (45°) em volta da {caixa}; colisões novas {melhor[0][0]}')
    return True


def tirar_no_da_caixa(E, C, trechos, caixa, regras, dmax=1.5, log=print):
    """nó entre dois tubos de gravidade colado na caixa de outra rede (DRN-237/DRN-238 na CI-15): o nó anda o mínimo para
    os dois tubos passarem fora da caixa com folga; cada tubo segue até a caixa dele (cotas do nó mantidas)."""
    els = [x for x in E if x['trecho'] in trechos and x['tipo'] == 'gravidade']; c = _cx(C, caixa)
    if len(els) < 2 or c is None: log(f'  decisão: nó {trechos} não encontrado'); return False
    # o nó = a ponta comum
    pts = [(e, k, e['pts'][k, :2].copy()) for e in els for k in (0, -1)]
    alvo = None
    for i, (e1, k1, p1) in enumerate(pts):
        for e2, k2, p2 in pts[i + 1:]:
            if e1 is not e2 and np.hypot(*(p1 - p2)) < 0.05: alvo = p1
    if alvo is None: log('  decisão: nó comum não achado'); return False
    no = [(e, k, p) for e, k, p in pts if np.hypot(*(p - alvo)) < 0.05]
    ids = {e['id'] for e in els}; base = {(k['a'], k['b']) for k in _criticos(ids, E, C, regras)}
    antigos = {e['id']: e['pts'].copy() for e in els}
    for d in np.arange(0.05, dmax + 1e-6, 0.05):
        for a in np.radians(np.arange(0, 360, 15)):
            v = d * np.array([math.cos(a), math.sin(a)])
            for e, k, p in no: e['pts'][k, :2] = p + v
            ks = _criticos(ids, E, C, regras)
            # com a caixa, nem folga curta: a forma real da revisão pegava 0,6 cm com só "sem crítica"
            perto = [x for x in cl.detectar([e for e in E if e['id'] in ids], [c], regras, campo='pts') if not x['ligacao']]
            if not perto and not [x for x in ks if (x['a'], x['b']) not in base]:
                for e in els:
                    e['pts_original'] = antigos[e['id']]; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
                    REG.append(dict(tipo='contorno', disc=e['disc'], elemento=e['id'], trecho=e['trecho'], antigo=antigos[e['id']][:, :2].tolist(),
                                    novo=e['pts'][:, :2].tolist(), desloc=float(d), caixa=caixa))
                log(f'  decisão: nó {"/".join(sorted(trechos))} anda {d:.2f} m para fora da {caixa}')
                return True
    for e, k, p in no: e['pts'][k, :2] = p
    log(f'  decisão: nó {trechos} sem lugar fora da {caixa} até {dmax} m'); return False


def antes_do_estudo(E, C, regras, log=print):
    REG.clear()
    mover_caixa(E, C, 'EL2-CX06', regras, longe_de=('PV12',), dmax=2.0, log=log)                 # ficha 6
    mover_caixa(E, C, 'PV27', regras, longe_de=('ESG-11',), dmax=1.2, log=log)                   # ficha 7
    esg11 = next((x for x in E if x['trecho'] == 'ESG-11'), None)                                # ficha 20: caixa na ponta sul do ESG-11
    if esg11 is not None:
        p = esg11['pts'][-1] if esg11['pts'][-1, 1] < esg11['pts'][0, 1] else esg11['pts'][0]
        cxe = min((c for c in C if c['disc'] == 'ESG'), key=lambda c: np.hypot(c['E'] - p[0], c['N'] - p[1]))
        if np.hypot(cxe['E'] - p[0], cxe['N'] - p[1]) < 1.0:
            mover_caixa(E, C, cxe['info'].get('nome', cxe['id'].split(':')[-1]), regras, longe_de=('PV28',), dmax=1.5, log=log)
    mover_caixa(E, C, 'PV20', regras, longe_de=('PVE-08',), dmax=1.0, log=log)                   # ficha 24
    desviar_grav(E, C, 'DRN-120', 'PVE-02', regras, log=log)                                     # ficha 3
    tirar_no_da_caixa(E, C, {'DRN-237', 'DRN-238'}, 'CI-15', regras, log=log)                    # fichas 16 e 23


# ------------------------------------------------------------------ depois do estudo
def _rdp(P, tol):
    if len(P) < 3: return P
    a, b = P[0], P[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(np.cross(ab, P[1:-1] - a)) / L if L > 1e-9 else np.hypot(*(P[1:-1] - a).T)
    i = int(np.argmax(d)) + 1
    if d[i - 1] <= tol: return np.array([a, b])
    return np.vstack([_rdp(P[:i + 1], tol)[:-1], _rdp(P[i:], tol)])


def _simplificar(P2, s0, s1, tol=0.7):
    """tira os desvios curtos do traçado só dentro do pedaço que vai andar de lado (a volta de 0,6 m da EL1-044 em volta de uma
    caixa virava laço quando o trecho inteiro andava 2,5 m)."""
    S = cp(np.column_stack([P2, np.zeros(len(P2))]))
    i0 = int(np.searchsorted(S, s0, 'right')) - 1; i1 = int(np.searchsorted(S, s1, 'left'))
    i0, i1 = max(i0, 0), min(i1, len(P2) - 1)
    if i1 - i0 < 2: return P2
    return np.vstack([P2[:i0], _rdp(P2[i0:i1 + 1], tol), P2[i1 + 1:]])


def _valido(Q):
    """sem volta para trás (> 135° num vértice) e sem segmentos que se cruzam."""
    for a, b, c in zip(Q[:-2], Q[1:-1], Q[2:]):
        u, v = b - a, c - b
        if np.hypot(*u) > 1e-6 and np.hypot(*v) > 1e-6 and np.dot(u, v) / (np.hypot(*u) * np.hypot(*v)) < -0.707: return False
    n = len(Q) - 1
    for i in range(n):
        for j in range(i + 2, n):
            p, r = Q[i], Q[i + 1] - Q[i]; q, t = Q[j], Q[j + 1] - Q[j]; den = r[0] * t[1] - r[1] * t[0]
            if abs(den) < 1e-12: continue
            w = q - p; a_ = (w[0] * t[1] - w[1] * t[0]) / den; b_ = (w[0] * r[1] - w[1] * r[0]) / den
            if 1e-6 < a_ < 1 - 1e-6 and 1e-6 < b_ < 1 - 1e-6: return False
    return True


def lateral(E, C, regras, ter, log=print):
    """desvio lateral (desvio._deslocar, ±0,4 a 3,0 m, rampas a 45°) só nos trechos de pressão aceitos nas fichas."""
    feitos = []
    for e in [x for x in E if x['trecho'] in TRECHOS_LATERAIS and x['tipo'] == 'pressao' and x.get('estudo')]:
        conf0 = _criticos({e['id']}, E, C, regras)
        if not conf0: continue
        P2 = e['pts'][:, :2]; S = cp(e['pts']); cob = e['estudo']['cob']
        ss = sorted(dv._proj_s(P2, S, np.array([k['E'], k['N']])) for k in conf0)
        melhor = None
        for s0, s1 in {(max(dv.PONTA, ss[0] - 1.2), min(S[-1] - dv.PONTA, ss[-1] + 1.2))} | {(max(dv.PONTA, s - 1.2), min(S[-1] - dv.PONTA, s + 1.2)) for s in ss}:
            if s1 <= s0: continue
            for o in dv.OFFSETS:
                Ps = _simplificar(P2, s0 - o - 0.5, s1 + o + 0.5)
                Ss = cp(np.column_stack([Ps, np.zeros(len(Ps))]))
                em = lambda s_: np.array([np.interp(s_, S, P2[:, 0]), np.interp(s_, S, P2[:, 1])])
                t0 = dv._proj_s(Ps, Ss, em(s0)) if len(Ps) != len(P2) else s0
                t1 = dv._proj_s(Ps, Ss, em(s1)) if len(Ps) != len(P2) else s1
                if t1 <= t0: t0, t1 = s0, s1
                for sg in (1, -1):
                    Q = dv._deslocar(Ps, t0, t1, sg * o)
                    if not _valido(Q): continue
                    try: P3 = perfil(Q, e['de'], cob, ter)
                    except ValueError: continue
                    n = len(_criticos({e['id']}, [dict(e, pts=P3) if x is e else x for x in E], C, regras))
                    if melhor is None or (n, o) < melhor[0]: melhor = ((n, o), sg * o, P3, s0, s1)
        if melhor and melhor[0][0] < len(conf0):
            P3 = melhor[2].copy()
            # pontas na cota do vizinho da mesma rede (o perfil novo abaixa as pontas por conta própria: degrau no nó)
            for k in (0, -1):
                viz = [x['pts'][j, 2] for x in E if x is not e and x['rede'] == e['rede'] for j in (0, -1)
                       if np.hypot(*(x['pts'][j, :2] - P3[k, :2])) < 0.05]
                if viz: P3[k, 2] = min(viz)
            melhor = (melhor[0], melhor[1], P3, melhor[3], melhor[4])
            e['pts_original'] = e['pts'].copy(); e['pts'] = melhor[2]; e['pts_sol'] = melhor[2].copy(); e.pop('S', None)
            feitos.append({'tipo': 'contorno', 'elemento': e['id'], 'disc': e['disc'], 'trecho': e['trecho'], 'status': 'aplicado',
                           'E': float(conf0[0]['E']), 'N': float(conf0[0]['N']), 's0': melhor[3], 's1': melhor[4], 'desloc': melhor[1],
                           'acrescimo': float(cp(melhor[2])[-1] - S[-1]), 'linhas_sit': 0,
                           'evitados': sorted({(k['b'] if k['a'] == e['id'] else k['a']) for k in conf0}), 'fixos_antes': len(conf0), 'fixos_depois': melhor[0][0]})
            log(f"  decisão: {e['trecho']} desvio lateral {melhor[1]:+.2f} m: {len(conf0)} -> {melhor[0][0]} críticos")
        else:
            log(f"  decisão: {e['trecho']} sem desvio lateral que reduza ({len(conf0)} críticos)")
    return feitos


def cota_grav(E, C, regras, ter, log=print):
    for trecho, modo in COTA_GRAV.items():
        e = next((x for x in E if x['trecho'] == trecho and x['tipo'] == 'gravidade'), None)
        if e is None: continue
        ids = {e['id']}; conf0 = _criticos(ids, E, C, regras)
        if not conf0: log(f'  decisão: {trecho} já sem colisão'); continue
        base = {(k['a'], k['b']) for k in conf0}
        P0 = e['pts'].copy(); zt = ter.z(P0[:, :2]); melhor = None
        for dz in sorted([s * x for x in np.arange(0.05, 0.81, 0.05) for s in (1, -1)], key=abs):
            P = P0.copy()
            if modo == 'chegada': P[:, 2] += dz * (cp(P0) / max(cp(P0)[-1], 1e-9))       # só a ponta de jusante muda
            else: P[:, 2] += dz
            if np.any(zt - (P[:, 2] + e['de'] / 2) < 0.30): continue                       # recobrimento mínimo de 0,30 m
            if modo == 'chegada' and P[0, 2] - P[-1, 2] < 0.002 * cp(P0)[-1]: continue     # mantém o caimento
            ks = _criticos(ids, [dict(e, pts=P) if x is e else x for x in E], C, regras)
            if not ks or not [k for k in ks if (k['a'], k['b']) not in base] and len(ks) < len(conf0):
                melhor = (dz, P, len(ks))
                if not ks: break
        if melhor is None: log(f'  decisão: {trecho} sem cota que resolva até 0,80 m'); continue
        dz, P, n = melhor
        e['pts_projeto_grav'] = P0; e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None)
        for k, z_ in ((0, P[0, 2]), (-1, P[-1, 2])):                                      # caixa da ponta: fundo acompanha
            for c in C:
                if c['disc'] != e['disc']: continue
                qx, qy = md.planta_local(c, P[k, 0], P[k, 1])
                if qx < 0.15 and qy < 0.15 and z_ - e['de'] / 2 - 0.05 < c['zb']: c['zb'] = z_ - e['de'] / 2 - 0.05
        gm, gj = P[0, 2] - e['de'] / 2, P[-1, 2] - e['de'] / 2
        REG.append(dict(tipo='mergulho', origem='decisao', disc=e['disc'], elemento=e['id'], trecho=trecho, dz=round(float(dz), 3),
                        E=float(P[:, 0].mean()), N=float(P[:, 1].mean()), planta=P[:, :2].tolist(),
                        nota_fixa=f'GI {br(gm)} / {br(gj)}', prof_topo=None))
        log(f"  decisão: {trecho} {'sobe' if dz > 0 else 'desce'} {abs(dz):.2f} m ({modo}); críticos {len(conf0)} -> {n}")


def al_rasa(E, C, regras, ter, log=print):
    """ficha 17: a rede AL o mais rasa possível (recobrimento mínimo 0,30 m) sem colisão nova e com a elétrica por cima."""
    al = [e for e in E if e['rede'] == 'AL' and e.get('estudo')]
    if not al: return
    ids = {e['id'] for e in al}; conf0 = _criticos(ids, E, C, regras); cob0 = al[0]['estudo']['cob']
    alvo = {x['id'] for x in E if x['trecho'] == 'ESG-11'}
    base = {(k['a'], k['b']) for k in conf0}
    de_g = max(e['de'] for e in al); orig = {e['id']: e['pts'].copy() for e in al}
    for cob in np.arange(0.30, cob0 - 0.01, 0.05):
        novos = {e['id']: perfil(e['pts'][:, :2], de_g, float(cob), ter) for e in al}
        E2 = [dict(x, pts=novos[x['id']]) if x['id'] in ids else x for x in E]
        ks = _criticos(ids, E2, C, regras)
        # elétrica/alarme por baixo da água em algum cruzamento: não serve
        if any(k['a'] in alvo or k['b'] in alvo for k in ks) or [k for k in ks if (k['a'], k['b']) not in base]: continue
        abaixo = False
        for x in E2:
            if x['disc'] not in ('ELE', 'SDAI') or abaixo: continue
            for e in al:
                A1, B1, A2, B2 = x['pts'][:-1], x['pts'][1:], novos[e['id']][:-1], novos[e['id']][1:]
                n1, n2 = len(A1), len(A2)
                d, C1, C2 = cl.dist_seg_seg(np.repeat(A1, n2, 0), np.repeat(B1, n2, 0), np.tile(A2, (n1, 1)), np.tile(B2, (n1, 1)))
                pl = np.hypot(C1[:, 0] - C2[:, 0], C1[:, 1] - C2[:, 1]) < 0.05
                if np.any(pl & (C1[:, 2] < C2[:, 2])): abaixo = True; break
        if abaixo: continue
        for e in al:
            e['pts'] = novos[e['id']]; e['pts_sol'] = e['pts'].copy(); e.pop('S', None); e['estudo'] = dict(e['estudo'], cob=float(cob))
        log(f'  decisão: rede AL sobe para recobrimento {cob:.2f} m (era {cob0:.2f}); ESG-11 × AL-02 resolvido')
        return True
    log(f'  decisão: rede AL não sobe sem colisão nova (fica em {cob0:.2f} m); vai para a cota do ESG-11')
    COTA_GRAV['ESG-11'] = 'tubo'
    return False


def depois_do_estudo(E, C, regras, ter, log=print):
    feitos = lateral(E, C, regras, ter, log)
    al_rasa(E, C, regras, ter, log)
    cota_grav(E, C, regras, ter, log)
    return feitos


def gravar(saida):
    fn = os.path.join(saida, 'ALI_decisoes.json')
    json.dump(REG, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return fn
