# -*- coding: utf-8 -*-
"""Jandaíra — pequenos deslocamentos de caixas de DRE/ESG antes do preclash (Anderson, 19/10/2026 noite: "pequenas mudanças na
alocação das caixas de drenagem e esgoto podem ser feitas para que a compatibilização seja atingida").
Para cada colisão de rede por gravidade com a estrutura as built (tubo em pilar/sapata, caixa em sapata/viga) e caixa × caixa
entre DRE e ESG: testa deslocar em planta uma caixa de ponta do trecho (ou a própria caixa), de 0,05 em 0,05 m até 0,60 m,
perpendicular ao trecho ou para longe do obstáculo; os tubos que chegam na caixa acompanham (só a ponta, CF/GI mantidos).
Fica o menor deslocamento que tira a colisão sem criar outra com a estrutura ou com a outra rede por gravidade (folga ≥ 0,05 m).
Grava o registro em ETIB-JANDAIRA/RELATORIOS/IFC_R02/JAN_ajustes_gravidade.json (UTM) para as pranchas DRE-001 e ESG-001."""
import os, json, math, re, copy
import numpy as np
from preclash import clash as cl

SAIDA = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02'
FOLGA_OK = 0.05
PASSOS = np.arange(0.05, 0.6001, 0.05)
PASSOS_PILAR = np.arange(0.05, 1.5001, 0.05)     # tubo atravessando pilar: o nó pode andar até 1,50 m (Anderson, 20/10: "Sim. Tudo")


def _nos(e):
    m = re.match(r'(.+?) -> (.+)', e['info'].get('de_ate', ''))
    return (m.group(1), m.group(2)) if m else (None, None)


def contornar(E, C, prof_lim=1.40, folga=0.30, log=print, extra=()):
    """pressurizada que cruza em planta uma caixa de DRE/ESG funda demais para passar por baixo (fundo além de 1,40 m):
    contorno curto em planta pela lateral mais curta da caixa (folga 0,30 m), como na prancha; a cota vem do estudo."""
    from preclash import modelo as md
    extra = set(map(tuple, extra))
    G = [c for c in C if c['disc'] in ('DRE', 'ESG') and 'canaleta' not in c['info'].get('tipo', '')]
    # caixa de passagem/registro de outra pressurizada (o fundo desce até o eletroduto/tubo mais fundo): só nos pares da rodada anterior
    G += [c for c in C if c['disc'] in ('ELE', 'SDAI', 'AF') and not c['info'].get('equipamento') and c['info'].get('nome')
          and c['info'].get('tipo') != 'reservatório enterrado' and any(c['info'].get('nome') == b for _, b in extra)]
    reg = []
    for e in E:
        if e['tipo'] != 'pressao': continue
        for c in G:
            if c['disc'] == e['disc']: continue
            # caixa funda demais para passar por baixo, ou par que sobrou crítico na rodada anterior (contornar_extra.json)
            grav = c['disc'] in ('DRE', 'ESG')
            if not ((grav and c['zt'] - c['zb'] > prof_lim) or (e['trecho'], c['info'].get('nome')) in extra): continue
            P = e['pts']; cs, sn = (math.cos(c.get('rot', 0.0)), math.sin(c.get('rot', 0.0)))
            hx = (c.get('mx', c['meia'])) + folga + e['de'] / 2; hy = (c.get('my', c['meia'])) + folga + e['de'] / 2
            loc = lambda p: np.array([(p[0] - c['E']) * cs + (p[1] - c['N']) * sn, -(p[0] - c['E']) * sn + (p[1] - c['N']) * cs])
            glo = lambda q: np.array([c['E'] + q[0] * cs - q[1] * sn, c['N'] + q[0] * sn + q[1] * cs])
            novo = None
            def corta(i):
                a, b = loc(P[i]), loc(P[i + 1]); d = b - a
                t0, t1 = 0.0, 1.0
                for p_, q_ in ((-d[0], a[0] + hx), (d[0], hx - a[0]), (-d[1], a[1] + hy), (d[1], hy - a[1])):   # Liang-Barsky
                    if abs(p_) < 1e-12:
                        if q_ < 0: return None
                        continue
                    r = q_ / p_
                    if p_ < 0: t0 = max(t0, r)
                    else: t1 = min(t1, r)
                return (t0, t1, a, d) if t0 < t1 else None
            for i in range(len(P) - 1):
                ci = corta(i)
                if not ci or ci[0] <= 0: continue                         # o trecho entra na caixa neste segmento
                t0, t1, a, d = ci; pin = a + d * t0; j = i
                # sai no mesmo segmento ou num dos seguintes (vértice dentro da caixa ampliada, ex.: ELE-I-15 no PI-01)
                while ci and ci[1] >= 1 and j + 1 < len(P) - 1:
                    j += 1; ci = corta(j)
                if not ci or ci[1] >= 1: break                            # termina dentro da caixa: não é travessia
                pout = ci[2] + ci[3] * ci[1]
                cantos = [np.array(v) for v in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]
                def lado(p):
                    if abs(p[1] - hy) < 1e-6: return 0
                    if abs(p[0] + hx) < 1e-6: return 1
                    if abs(p[1] + hy) < 1e-6: return 2
                    return 3
                l0, l1 = lado(pin), lado(pout); melhor = None
                # cantos em sentido anti-horário: lado 0 = topo (c0 -> c1), 1 = esquerda, 2 = base, 3 = direita
                for sentido in (1, -1):
                    cam = [pin]; l = l0
                    for _ in range(4):
                        if l == l1: break
                        if sentido == 1: cam.append(cantos[(l + 1) % 4]); l = (l + 1) % 4
                        else: cam.append(cantos[l]); l = (l - 1) % 4
                    cam.append(pout)
                    comp = sum(np.hypot(*(cam[j + 1] - cam[j])) for j in range(len(cam) - 1))
                    if melhor is None or comp < melhor[0]: melhor = (comp, cam)
                Q = [glo(q) for q in melhor[1]]
                z = P[i][2]
                novo = np.vstack([P[:i + 1], np.array([[q[0], q[1], z] for q in Q]), P[j + 1:]])
                break
            if novo is not None:
                antigo = e.get('pts_planta0', e['pts']).copy(); e['pts_planta0'] = antigo
                e['pts'] = novo; e['pts_sol'] = novo.copy()
                reg.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa=c['info'].get('nome'), status='contorno em planta',
                                antigo=[list(map(float, p[:2])) for p in antigo], pontos=[list(map(float, p[:2])) for p in novo]))
                log(f"  {e['trecho']} contorna {c['info'].get('nome')} em planta (caixa com {c['zt'] - c['zb']:.2f} m" + (": não passa por baixo até 1,50 m)" if grav else ", par crítico da rodada anterior)"))
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(reg, open(os.path.join(SAIDA, 'JAN_contornos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return reg


def mover_ele(E, C, regras, log=print, passo_max=1.00, extra=(), ref=None, refzb=None):
    """caixa de passagem de elétrica/SDAI atravessada por tubo ou caixa de drenagem/esgoto (ou em pilar/sapata): desliza a caixa
    ao longo de um dos eletrodutos que chegam nela (ou na perpendicular), de 0,10 em 0,10 m até 1,00 m; os eletrodutos que
    chegam na caixa acompanham (só a ponta). A cota dos eletrodutos sai depois do estudo."""
    from preclash import modelo as md
    R = dict(regras, folga=FOLGA_OK)
    GRAV = [e for e in E if e['tipo'] == 'gravidade']
    FIX = [c for c in C if c['disc'] in ('DRE', 'ESG', 'EST')]
    B = [c for c in C if c['disc'] in ('ELE', 'SDAI') and c['id'].startswith(('ELE:', 'SDAI:')) and c['info'].get('nome')]
    reg = []

    refzb = refzb or {}
    pares, extra = (extra or ()), {}
    for cxn, tr in pares: extra.setdefault(cxn, set()).add(tr)

    def ruins(cx):
        out = []
        for tr in extra.get(cx['info'].get('nome'), ()):        # tubo de outra pressurizada que atravessava a caixa na rodada anterior: folga em planta
            for e in E:
                if e['trecho'] != tr or e['disc'] == cx['disc']: continue
                Q = cl.amostra(e['pts'], 0.05); qx, qy = md.planta_local(cx, Q[:, 0], Q[:, 1])
                if np.any((qx < 0.15) & (qy < 0.15)): out.append(tr)
        cx = dict(cx, zb=min(cx['zb'], cx['zt'] - 0.85))       # o fundo ainda vai descer até o eletroduto do estudo (0,60 m + diâmetro + 10 cm)
        perto = [e for e in GRAV if e['pts'][:, 0].min() - 3 < cx['E'] < e['pts'][:, 0].max() + 3 and e['pts'][:, 1].min() - 3 < cx['N'] < e['pts'][:, 1].max() + 3]
        lst = out + ([x for x in cl.detectar(perto, [cx], R) if not x['ligacao'] and x['folga'] < FOLGA_OK and cx['id'] in (x['a'], x['b'])] if perto else [])
        for f in FIX:
            if abs(f['E'] - cx['E']) > 6 or abs(f['N'] - cx['N']) > 6: continue
            fo, _ = cl.folga_caixas(cx, f)
            if fo < FOLGA_OK: lst.append(f['id'])
        if ref:
            # pressurizada de outra disciplina na cota da rodada anterior, com a caixa no fundo da rodada anterior
            c3 = dict(cx, zb=min(cx['zb'], refzb.get(cx['id'], cx['zb'])))
            rp = [e for e in ref if e['disc'] != cx['disc'] and e['pts'][:, 0].min() - 2 < cx['E'] < e['pts'][:, 0].max() + 2
                  and e['pts'][:, 1].min() - 2 < cx['N'] < e['pts'][:, 1].max() + 2]
            lst += [x for x in cl.detectar(rp, [c3], R) if not x['ligacao'] and x['folga'] < FOLGA_OK and c3['id'] in (x['a'], x['b'])] if rp else []
        return lst

    for b in B:
        if not ruins(b): continue
        pecas = []
        for e in E:
            if e['tipo'] != 'pressao' or e['disc'] != b['disc']: continue
            for k in (0, -1):
                qx, qy = md.planta_local(b, e['pts'][k, 0], e['pts'][k, 1])
                if qx < 0.10 and qy < 0.10: pecas.append((e, k))
        dirs = []
        for e, k in pecas:
            j = 1 if k == 0 else -2
            u = e['pts'][j, :2] - e['pts'][k, :2]; n = np.hypot(*u)
            if n > 1e-6: u = u / n; dirs += [u, -u, np.array([-u[1], u[0]]), np.array([u[1], -u[0]])]
        # direções dos eletrodutos + a rosa de 15 em 15 graus (a posição livre pode estar na diagonal)
        dirs += [np.array([math.cos(a), math.sin(a)]) for a in np.radians(np.arange(0, 360, 15))]
        feito = None
        for p in np.arange(0.10, passo_max + 1e-6, 0.10):
            for u in dirs:
                b2 = dict(b, E=b['E'] + u[0] * p, N=b['N'] + u[1] * p)
                if ruins(b2): continue
                # os eletrodutos que acompanham não podem passar a atravessar caixa de DRE/ESG ou peça da estrutura em planta
                ok = True
                for e, k in pecas:
                    P = e['pts'].copy(); P[k, :2] += u * p
                    Q = cl.amostra(P, 0.10)
                    for f in FIX:
                        if f['disc'] == 'EST' and f['zt'] < np.min(Q[:, 2]) - 0.5: continue
                        qx, qy = md.planta_local(f, Q[:, 0], Q[:, 1])
                        dentro = (qx < 0) & (qy < 0)
                        if np.any(dentro[3:-3]): ok = False; break
                    if not ok: break
                if ok: feito = (u * p, b2); break
            if feito: break
        if not feito:
            reg.append(dict(caixa=b['info']['nome'], disc=b['disc'], status=f'sem deslocamento até {passo_max:.2f} m')); continue
        v, b2 = feito
        de = (b['E'], b['N']); b['E0'], b['N0'] = de; b['E'], b['N'] = b2['E'], b2['N']
        for e, k in pecas:
            e.setdefault('pts_planta0', e['pts'].copy())
            e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy()
        reg.append(dict(caixa=b['info']['nome'], disc=b['disc'], elemento=b['id'], status='caixa deslocada', de=list(de), E=b['E'], N=b['N'],
                        desloc=round(float(np.hypot(*v)), 2), lado=round(2 * b.get('mx', b['meia']), 3), lado_y=round(2 * b.get('my', b['meia']), 3),
                        rot=float(b.get('rot', 0.0)), tubos=[e['trecho'] for e, _ in pecas]))
        log(f"  caixa {b['info']['nome']} ({b['disc']}) anda {np.hypot(*v):.2f} m: saía de cima de drenagem/esgoto/estrutura; eletrodutos acompanham")
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(reg, open(os.path.join(SAIDA, 'JAN_caixas_ele.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return reg


def ajustar(E, C, regras, log=print):
    G = [e for e in E if e['tipo'] == 'gravidade']
    CXG = {c['info'].get('nome'): c for c in C if c['disc'] in ('DRE', 'ESG') and c['info'].get('nome') and 'canaleta' not in c['info'].get('tipo', '')}
    EST = [c for c in C if c['disc'] == 'EST']
    por_cx = {}; no_de = {}; J = []
    for e in G:
        for k, n in zip((0, -1), _nos(e)):
            if n in CXG and n != '-': por_cx.setdefault(n, []).append((e, k)); no_de[(e['id'], k)] = n; continue
            # ponta sem caixa (junção de tubos sob o bloco, pé da descida pluvial): nó que também pode andar até 0,60 m
            p = e['pts'][k, :2]; j = next((i for i, q in enumerate(J) if np.hypot(*(q - p)) < 0.10), None)
            if j is None: J.append(p.copy()); j = len(J) - 1
            nj = f'junção {e["disc"]} J{j + 1:03d}'; por_cx.setdefault(nj, []).append((e, k)); no_de[(e['id'], k)] = nj
    for e in G: e.setdefault('pts_planta0', e['pts'].copy())
    R = dict(regras, folga=FOLGA_OK)

    def conflitos(els, cxs):
        out = []
        for c in cl.detectar(els, cxs, R):
            if c['ligacao'] or c['folga'] >= FOLGA_OK: continue
            out.append(c)
        return out

    def avaliar(nome, v):
        """conflitos críticos/curtos (< 5 cm) dos tubos da caixa e da caixa, depois de mover nome por v."""
        cx = CXG.get(nome); c2 = dict(cx, E=cx['E'] + v[0], N=cx['N'] + v[1]) if cx else None
        els = []
        for e, k in por_cx.get(nome, []):
            e2 = dict(e); P = e['pts_sol'].copy(); P[k, :2] += v; e2['pts_sol'] = P; els.append(e2)
        outras = [c for n, c in CXG.items() if n != nome]
        cand = conflitos(els, ([c2] if c2 else []) + EST + outras)
        # a caixa contra a estrutura e contra caixas/tubos da outra rede por gravidade
        if c2: cand += conflitos([e for e in G if all(e['id'] != x['id'] for x in els)], [c2])
        return cand, c2, els

    reg = []; tot = {}; lim = {}; ESTd = {c['id']: c for c in EST}
    for it in range(4):
        base = conflitos(G, list(CXG.values()) + EST)
        alvo = [c for c in base if (c['b'].startswith('EST:') or (c['tipo'] == 'caixa×caixa' and 'EST:' not in c['a'] + c['b']
                                                                  and {c['a'].split(':')[0], c['b'].split(':')[0]} == {'DRE', 'ESG'}))]
        alvo = [c for c in alvo if c['folga'] < -0.002]
        if not alvo: break
        feito = 0
        for c in sorted(alvo, key=lambda c: c['folga']):
            if c['tipo'] == 'tubo×caixa':
                e = next(x for x in G if x['id'] == c['a']); P = e['pts_sol']
                d = P[-1, :2] - P[0, :2]; d = d / max(1e-9, np.hypot(*d)); nrm = np.array([-d[1], d[0]])
                s = np.array([c['E'], c['N']]) - P[0, :2]; t = float(np.clip(s @ d / max(1e-9, np.hypot(*(P[-1, :2] - P[0, :2]))), 0, 1))
                nos = [(no_de[(e['id'], 0)], 0), (no_de[(e['id'], -1)], 1)]
                # caixa (ou junção) mais perto do ponto de colisão primeiro; os dois lados da perpendicular
                nos = [n for n, _ in sorted(nos, key=lambda x: abs(x[1] - t))]
                tp = (ESTd.get(c['b'], {}).get('info') or {}).get('tipo')
                pil = tp == 'pilar'
                # pilar: o nó anda até 1,50 m; sapata: só junção (sem caixa) anda até 1,50 m
                longe = [n for n in nos if pil or (tp == 'fundação' and n not in CXG)]
                cands = [(n, nrm * sgn * p) for p in PASSOS_PILAR for n in nos for sgn in (1, -1) if n in longe or p <= PASSOS[-1] + 1e-9]
                lim.update({n: PASSOS_PILAR[-1] for n in longe})
            else:
                a, b = c['a'], c['b']
                nome = next((CXG[x.split(':', 1)[1]] and x.split(':', 1)[1] for x in (a, b) if x.split(':', 1)[0] in ('DRE', 'ESG') and x.split(':', 1)[1] in CXG), None)
                if not nome: continue
                cx = CXG[nome]; d = np.array([cx['E'] - c['E'], cx['N'] - c['N']]); d = d / max(1e-9, np.hypot(*d))
                cands = [(nome, d * p) for p in PASSOS] + [(nome, np.array([-d[1], d[0]]) * s * p) for p in PASSOS for s in (1, -1)]
            ok = None; dor = lambda L: sum(max(0.0, FOLGA_OK - x['folga']) for x in L); par = {c['a'], c['b']}
            base0 = {n: dor(avaliar(n, np.zeros(2))[0]) for n in {n for n, _ in cands}}
            for nome, v in cands:
                if np.hypot(*(tot.get(nome, np.zeros(2)) + v)) > lim.get(nome, PASSOS[-1]) + 1e-6: continue      # deslocamento total até 0,60 m (1,50 m no pilar)
                cand, c2, els = avaliar(nome, v)
                # resolve o par e não piora o resto (soma do que falta para 5 cm de folga nos tubos e na caixa que andam)
                alvo_ok = not any({x['a'], x['b']} == par or ({x['b']} & par and x['a'] in {e2['id'] for e2 in els}) and x['b'] in par for x in cand if x['folga'] < 0.0)
                if alvo_ok and not any(x['folga'] < -0.002 for x in cand if {x['a'], x['b']} & par == par) and dor(cand) < base0[nome] - 0.01:
                    ok = (nome, v, c2, els); break
            if not ok:
                reg.append(dict(conflito=f"{c['a']} × {c['b']}", folga=round(c['folga'], 3), status='sem deslocamento até 0,60 m'))
                continue
            nome, v, c2, els = ok
            tot[nome] = tot.get(nome, np.zeros(2)) + v
            if c2: CXG[nome].update(E=c2['E'], N=c2['N'])
            for e2 in els:
                e = next(x for x in G if x['id'] == e2['id']); e['pts_sol'] = e2['pts_sol']; e['pts'] = e2['pts_sol'].copy()
            reg.append(dict(conflito=f"{c['a']} × {c['b']}", folga=round(c['folga'], 3), caixa=nome, dE=round(float(v[0]), 3), dN=round(float(v[1]), 3),
                            desloc=round(float(np.hypot(*v)), 2), status='caixa deslocada' if c2 else 'junção deslocada',
                            E=c2['E'] if c2 else None, N=c2['N'] if c2 else None, tubos=[e2['trecho'] for e2 in els]))
            log(f"  {'caixa' if c2 else ''} {nome} anda {np.hypot(*v):.2f} m ({c['a']} × {c['b']}, folga {c['folga']:+.2f}); tubos que acompanham: {', '.join(e2['trecho'] for e2 in els)}")
            feito += 1
        if not feito: break
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(reg, open(os.path.join(SAIDA, 'JAN_ajustes_gravidade.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    # posição final (para as pranchas DRE-001/ESG-001): caixa de -> para; tubo que muda em planta por junção deslocada
    fin = {'caixas': [], 'tubos': []}
    for nome, v in tot.items():
        if nome not in CXG or np.hypot(*v) < 0.005: continue
        c = CXG[nome]
        fin['caixas'].append(dict(caixa=nome, disc=c['disc'], elemento=c['id'], de=[c['E'] - v[0], c['N'] - v[1]], E=c['E'], N=c['N'], desloc=round(float(np.hypot(*v)), 2),
                                  lado=round(2 * c.get('mx', c['meia']), 3), lado_y=round(2 * c.get('my', c['meia']), 3), rot=float(c.get('rot', 0.0)), forma=c['forma']))
    juncoes = {n for n, v in tot.items() if n not in CXG and np.hypot(*v) >= 0.005}
    for e in G:
        if not {no_de[(e['id'], 0)], no_de[(e['id'], -1)]} & juncoes: continue
        if np.max(np.hypot(*(e['pts'][:, :2] - e['pts_planta0'][:, :2]).T)) < 0.005: continue
        fin['tubos'].append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], antigo=e['pts_planta0'][:, :2].tolist(), novo=e['pts'][:, :2].tolist()))
    json.dump(fin, open(os.path.join(SAIDA, 'JAN_ajustes_gravidade_final.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    n_ok = sum(1 for r in reg if r['status'] == 'caixa deslocada')
    log(f'  ajustes de gravidade: {n_ok} caixas deslocadas; {len(reg) - n_ok} colisões sem deslocamento possível até 0,60 m')
    return reg

