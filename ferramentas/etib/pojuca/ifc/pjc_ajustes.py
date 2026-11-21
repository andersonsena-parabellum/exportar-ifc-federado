# -*- coding: utf-8 -*-
"""Pojuca — ajustes (cópia de catu/ifc/cat_ajustes.py com os arquivos PJC_) em planta antes do preclash, sobre os pares críticos da rodada anterior (mesmo método da
Jandaíra, FERRAMENTAS/jandaira/ifc/jan_ajustes.py):
  - CONTORNO CURTO: pressurizada (ELE, SDAI, HID, AF) que atravessa em planta um PV/caixa de DRE/ESG ou uma peça da estrutura
    (sapata, bloco, estaca, pilar) sem cota livre até 2,00 m: contorna pela lateral mais curta da peça (folga 0,30 m), em ângulos de
    90° nos cantos (peças comerciais); a cota vem do estudo;
  - CAIXA DESLOCADA: caixa de passagem de ELE/SDAI ou alçapão da AF atravessada por tubo/caixa de outra rede: desliza até 1,50 m
    (direções dos eletrodutos + rosa de 15°); os eletrodutos/tubos que chegam nela acompanham (só a ponta).
Pares lidos de <SAIDA>/PJC_ajustes_pares.json (gerado por sat_pares.py a partir dos críticos da rodada anterior).
Registro em <SAIDA>/PJC_contornos.json e PJC_caixas_movidas.json (UTM), para as pranchas."""
import os, json, math
import numpy as np
from preclash import clash as cl, modelo as md

FOLGA_OK = 0.10


def contornar(E, C, pares, saida, folga=0.30, log=print):
    porn = {}
    for c in C: porn.setdefault(c['info'].get('nome', c['id']), []).append(c)
    reg = []
    for trecho, nome in pares:
        alvo = porn.get(nome, [])
        for e in E:
            if e['tipo'] != 'pressao' or e['trecho'] != trecho or e['info'].get('estudo') is False: continue
            for c in alvo:
                if c['disc'] == e['disc']: continue
                P = e['pts']; rot = c.get('rot', 0.0) if c['forma'] == 'r' else 0.0; cs, sn = math.cos(rot), math.sin(rot)
                hx = c.get('mx', c['meia']) + folga + e['de'] / 2; hy = c.get('my', c['meia']) + folga + e['de'] / 2
                loc = lambda p: np.array([(p[0] - c['E']) * cs + (p[1] - c['N']) * sn, -(p[0] - c['E']) * sn + (p[1] - c['N']) * cs])
                glo = lambda q: np.array([c['E'] + q[0] * cs - q[1] * sn, c['N'] + q[0] * sn + q[1] * cs])

                def corta(i):
                    a, b = loc(P[i]), loc(P[i + 1]); d = b - a; t0, t1 = 0.0, 1.0
                    for p_, q_ in ((-d[0], a[0] + hx), (d[0], hx - a[0]), (-d[1], a[1] + hy), (d[1], hy - a[1])):
                        if abs(p_) < 1e-12:
                            if q_ < 0: return None
                            continue
                        r = q_ / p_
                        if p_ < 0: t0 = max(t0, r)
                        else: t1 = min(t1, r)
                    return (t0, t1, a, d) if t0 < t1 else None
                novo = None
                for i in range(len(P) - 1):
                    ci = corta(i)
                    if not ci or ci[0] <= 0: continue
                    t0, t1, a, d = ci; pin = a + d * t0; j = i
                    while ci and ci[1] >= 1 and j + 1 < len(P) - 1:
                        j += 1; ci = corta(j)
                    if not ci or ci[1] >= 1: break
                    pout = ci[2] + ci[3] * ci[1]
                    cantos = [np.array(v) for v in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]
                    def lado(p):
                        if abs(p[1] - hy) < 1e-6: return 0
                        if abs(p[0] + hx) < 1e-6: return 1
                        if abs(p[1] + hy) < 1e-6: return 2
                        return 3
                    l0, l1 = lado(pin), lado(pout); melhor = None
                    for sentido in (1, -1):
                        cam = [pin]; l = l0
                        for _ in range(4):
                            if l == l1: break
                            if sentido == 1: cam.append(cantos[(l + 1) % 4]); l = (l + 1) % 4
                            else: cam.append(cantos[l]); l = (l - 1) % 4
                        cam.append(pout)
                        comp = sum(np.hypot(*(cam[k + 1] - cam[k])) for k in range(len(cam) - 1))
                        if melhor is None or comp < melhor[0]: melhor = (comp, cam)
                    Q = [glo(q) for q in melhor[1]]; z = P[i][2]
                    novo = np.vstack([P[:i + 1], np.array([[q[0], q[1], z] for q in Q]), P[j + 1:]])
                    # entrada/saída do contorno a menos de 10 cm de um vértice do traçado: um trecho de 3 cm entre duas curvas
                    # (EL2-021 em volta da CI-20) ficava com uma curva só — o ponto do meio sai
                    K = [novo[0]]
                    for m_ in range(1, len(novo)):
                        if np.hypot(*(novo[m_][:2] - K[-1][:2])) < 0.10:
                            if m_ == len(novo) - 1:
                                if len(K) > 1: K[-1] = novo[m_]
                                else: K.append(novo[m_])
                            continue
                        K.append(novo[m_])
                    novo = np.array(K)
                    break
                if novo is not None:
                    antigo = e.get('pts_planta0', e['pts']).copy(); e['pts_planta0'] = antigo
                    e['pts'] = novo; e['pts_sol'] = novo.copy(); e.pop('S', None)
                    reg.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa=nome, status='contorno em planta',
                                    antigo=[list(map(float, p[:2])) for p in antigo], pontos=[list(map(float, p[:2])) for p in novo]))
                    log(f"  {e['trecho']} contorna {nome} em planta")
    os.makedirs(saida, exist_ok=True)
    json.dump(reg, open(os.path.join(saida, 'PJC_contornos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return reg


def mover_caixas(E, C, nomes, saida, passo_max=1.50, log=print):
    R = {'folga': FOLGA_OK, 'ligacao_entre': [{'AP', 'DRE'}]}
    FIX = [c for c in C if c['disc'] in ('DRE', 'ESG', 'AP', 'EST')]
    GRAV = [e for e in E if e['tipo'] == 'gravidade']
    reg = []
    # Pojuca: a base do poste também anda (aplicar e avisar: poste até 1,50 m junto com o ramal), levando o poste junto
    for b in [c for c in C if c['info'].get('nome') in nomes and c['disc'] in ('ELE', 'SDAI', 'AF')
              and (not c['info'].get('equipamento') or str(c['info'].get('nome', '')).endswith(':base'))]:
        haste = next((c for c in C if b['info']['nome'].endswith(':base') and c['id'] == b['id'][:-5]), None)
        outros = [e for e in E if e['disc'] != b['disc']]

        def ruins(cx):
            cx = dict(cx, zb=min(cx['zb'], cx['zt'] - 1.00))       # o fundo ainda desce até o tubo mais fundo do estudo
            perto = [e for e in outros if e['pts'][:, 0].min() - 3 < cx['E'] < e['pts'][:, 0].max() + 3 and e['pts'][:, 1].min() - 3 < cx['N'] < e['pts'][:, 1].max() + 3]
            lst = []
            for e in perto:
                Q = cl.amostra(e['pts'], 0.05); qx, qy = md.planta_local(cx, Q[:, 0], Q[:, 1])
                if np.any((qx < e['de'] / 2 + FOLGA_OK) & (qy < e['de'] / 2 + FOLGA_OK) & (Q[:, 2] < cx['zt']) & (Q[:, 2] > cx['zb'] - 0.5)): lst.append(e['id'])
            for f in FIX + [c for c in C if c['disc'] in ('ELE', 'SDAI', 'AF') and c['disc'] != cx['disc']]:
                if abs(f['E'] - cx['E']) > 6 or abs(f['N'] - cx['N']) > 6: continue
                if cl.folga_caixas(cx, f)[0] < FOLGA_OK: lst.append(f['id'])
            return lst
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
        dirs += [np.array([math.cos(a), math.sin(a)]) for a in np.radians(np.arange(0, 360, 15))]
        feito = None
        for p in np.arange(0.10, passo_max + 1e-6, 0.10):
            for u in dirs:
                b2 = dict(b, E=b['E'] + u[0] * p, N=b['N'] + u[1] * p)
                if ruins(b2): continue
                ok = True
                for e, k in pecas:
                    P = e['pts'].copy(); P[k, :2] += u * p; Q = cl.amostra(P, 0.10)
                    for f in FIX:
                        if f['disc'] == 'EST' and f['zt'] < np.min(Q[:, 2]) - 0.5: continue
                        qx, qy = md.planta_local(f, Q[:, 0], Q[:, 1])
                        if np.any(((qx < 0) & (qy < 0))[3:-3]): ok = False; break
                    if not ok: break
                if ok: feito = (u * p, b2); break
            if feito: break
        if not feito:
            reg.append(dict(caixa=b['info']['nome'], disc=b['disc'], status=f'sem deslocamento até {passo_max:.2f} m')); continue
        v, b2 = feito
        de = (b['E'], b['N']); b['E0'], b['N0'] = de; b['E'], b['N'] = b2['E'], b2['N']
        if haste is not None: haste['E0'], haste['N0'] = haste['E'], haste['N']; haste['E'], haste['N'] = haste['E'] + v[0], haste['N'] + v[1]
        for e, k in pecas:
            e.setdefault('pts_planta0', e['pts'].copy()); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
        reg.append(dict(caixa=b['info']['nome'], disc=b['disc'], elemento=b['id'], status='caixa deslocada', de=list(de), E=b['E'], N=b['N'],
                        desloc=round(float(np.hypot(*v)), 2), lado=round(2 * b.get('mx', b['meia']), 3), lado_y=round(2 * b.get('my', b['meia']), 3),
                        rot=float(b.get('rot', 0.0)), forma=b['forma'], tubos=[e['trecho'] for e, _ in pecas]))
        log(f"  caixa {b['info']['nome']} ({b['disc']}) anda {np.hypot(*v):.2f} m; {len(pecas)} trechos acompanham")
    os.makedirs(saida, exist_ok=True)
    json.dump(reg, open(os.path.join(saida, 'PJC_caixas_movidas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return reg


def afastar_pontas(E, C, saida, folga=0.30, log=print):
    """ponta de eletroduto/tubo de pressão (vértice entre dois trechos) caindo dentro de caixa de esgoto/drenagem (EL2-001/007 no
    meio da caixa de areia CA56, EL1-055 na CA65 — Revisão de 21/10): o vértice sai para fora da caixa, a 'folga' da parede, pelo
    lado mais perto; as pontas dos outros trechos da mesma rede nesse vértice vão junto (contorno curto, vai para as pranchas)."""
    reg = []
    for c in [c for c in C if c['disc'] in ('DRE', 'ESG', 'AP')]:
        rot = c.get('rot', 0.0) if c['forma'] == 'r' else 0.0; cs, sn = math.cos(rot), math.sin(rot)
        mx, my = (c['mx'], c['my']) if c['forma'] == 'r' else (c['meia'], c['meia'])
        for e in E:
            if e['tipo'] != 'pressao' or e['disc'] not in ('ELE', 'SDAI') or e['info'].get('estudo') is False: continue
            for k in (0, -1):
                p = e['pts'][k]
                if abs(p[0] - c['E']) > 3 or abs(p[1] - c['N']) > 3: continue
                lx = (p[0] - c['E']) * cs + (p[1] - c['N']) * sn; ly = -(p[0] - c['E']) * sn + (p[1] - c['N']) * cs
                if abs(lx) > mx + 0.10 or abs(ly) > my + 0.10: continue
                # a ponta chega numa caixa da própria rede (EL2-036 na EL2-CX02, que fica sobre a CA32): quem resolve é a caixa
                # deslocada da ferramenta, que leva as pontas junto
                if any(f['disc'] == e['disc'] and abs(f['E'] - p[0]) < 3 and abs(f['N'] - p[1]) < 3
                       and max(md.planta_local(f, p[0], p[1])) < 0.50 for f in C): continue   # Pojuca: ponta do banco ao lado da caixa (EL1-CX06 sobre a PVP-02)
                hx, hy = mx + folga + e['de'] / 2, my + folga + e['de'] / 2
                # saídas possíveis: os 4 lados e os 4 cantos, da mais curta para a mais longa
                opc = [(hx, ly), (-hx, ly), (lx, hy), (lx, -hy), (hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]
                opc.sort(key=lambda t: math.hypot(t[0] - lx, t[1] - ly))
                glob = lambda nl: np.array([c['E'] + nl[0] * cs - nl[1] * sn, c['N'] + nl[0] * sn + nl[1] * cs])
                p0 = p[:2].copy()
                # os trechos que saem do vértice novo não podem atravessar a caixa (EL2-036 na CA32 passava a cruzar a parede)
                # pontas da mesma rede a até 15 cm (EL2-001 e EL2-007 terminam a 11 cm uma da outra dentro da CA56)
                viz = [o['pts'][1 if j == 0 else -2][:2] for o in E if o['tipo'] == 'pressao' and o['disc'] == e['disc']
                       for j in (0, -1) if np.hypot(*(o['pts'][j][:2] - p0)) < 0.15]
                def cruza(a, b):
                    for t in np.linspace(0, 1, 41)[1:]:
                        x = a + (b - a) * t; lx_ = (x[0] - c['E']) * cs + (x[1] - c['N']) * sn; ly_ = -(x[0] - c['E']) * sn + (x[1] - c['N']) * cs
                        if abs(lx_) < mx + 0.05 and abs(ly_) < my + 0.05: return True
                    return False
                # fim de rede dentro da caixa (eletroduto que chega no poste ao lado) fica: o clash trata como ligação e mexer nele
                # criava cruzamento novo (EL2-036 × CA32, ALC-AUD); só o vértice de passagem entre dois trechos sai
                if len(viz) < 2:
                    # fim de rede dentro da caixa (EL1-055 na CA65): só encurta, na direção do próprio trecho, até a folga da parede
                    loc_ = lambda x: ((x[0] - c['E']) * cs + (x[1] - c['N']) * sn, -(x[0] - c['E']) * sn + (x[1] - c['N']) * cs)
                    q = next((p0 + (viz[0] - p0) * t for t in np.linspace(0, 1, 201)[1:]
                              if abs(loc_(p0 + (viz[0] - p0) * t)[0]) > hx or abs(loc_(p0 + (viz[0] - p0) * t)[1]) > hy), None)
                else:
                    q = next((glob(nl) for nl in opc if not any(cruza(glob(nl), v) for v in viz)), None)
                if q is None:
                    log(f"  {e['trecho']}: vértice dentro da {c['info'].get('nome', c['id'])} fica (o trecho cruzaria a caixa)"); continue
                for o in E:
                    if o['tipo'] != 'pressao' or o['disc'] != e['disc']: continue
                    for j in (0, -1):
                        if np.hypot(*(o['pts'][j][:2] - p0)) < 0.15:
                            antigo = o.get('pts_planta0', o['pts']).copy(); o['pts_planta0'] = antigo
                            o['pts'] = o['pts'].copy(); o['pts'][j, :2] = q; o['pts_sol'] = o['pts'].copy(); o.pop('S', None)
                            reg.append(dict(trecho=o['trecho'], disc=o['disc'], elemento=o['id'], caixa=c['info'].get('nome', c['id']),
                                            status='contorno em planta', antigo=[list(map(float, x[:2])) for x in antigo],
                                            pontos=[list(map(float, x[:2])) for x in o['pts']]))
                            log(f"  {o['trecho']}: vértice sai de dentro da {c['info'].get('nome', c['id'])} ({np.hypot(*(q - p0)):.2f} m)")
    fn = os.path.join(saida, 'PJC_contornos.json')
    ant = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    json.dump(ant + reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return reg
