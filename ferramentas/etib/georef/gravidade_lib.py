# -*- coding: utf-8 -*-
"""Extração de redes por gravidade (esgoto, drenagem) de DWG QiBuilder em UTM — partes comuns da ETIB Catu.
Usada por esg_catu.py e dre_catu.py. Método da skill (redes-gravidade.md): nós de projeto primeiro (PVs, caixas, prumadas),
depois eixos (pares de parede exclusivos + linhas únicas), sentido (seta > CF > ramal > continuidade) e rótulos."""
import re, math, csv, json, os, collections
import numpy as np
from rede_lib import parear_paredes, fundir_colineares, Rede, sentido_por_setas, dist_pt_seg, unit
from catu_comum import num


def pvs_por_bloco(ob, bloco, tipo):
    out = []
    for d in ob:
        if d['tipo'] == 'INSERT' and d['nome'] == bloco:
            rs = [x['r'] for x in ob if x['tipo'] == 'CIRCLE' and x['path'].endswith(bloco) and np.linalg.norm(x['pts'][0, :2] - d['pts'][0, :2]) < 0.05]
            out.append({'tipo': tipo, 'c': d['pts'][0, :2].copy(), 'raio': max(rs or [0.5]), 'origem': f'bloco {bloco}'})
    return out


def caixas_quadradas(ob, caixas, layers_linhas, layers_contorno, rotulos, tipo_padrao='CX', lado=(0.4, 1.3)):
    """Caixas de alvenaria: laços de LINEs (layers_linhas) e/ou contornos fechados (layers_contorno) perto dos rótulos."""
    segs = [d['pts'][:, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] in layers_linhas]
    segs = [s for s in segs if lado[0] < np.linalg.norm(s[1] - s[0]) < lado[1]]
    grupo = list(range(len(segs)))
    def raiz(i):
        while grupo[i] != i: grupo[i] = grupo[grupo[i]]; i = grupo[i]
        return i
    P0 = np.array([s[0] for s in segs]) if segs else np.zeros((0, 2)); P1 = np.array([s[1] for s in segs]) if segs else np.zeros((0, 2))
    for i in range(len(segs)):
        for P in (P0, P1):
            for q in (segs[i][0], segs[i][1]):
                for j in np.where(np.hypot(*(P - q).T) < 0.005)[0]:
                    if j != i: grupo[raiz(i)] = raiz(int(j))
    G = collections.defaultdict(list)
    for i in range(len(segs)): G[raiz(i)].append(i)
    for g in G.values():
        if len(g) < 3: continue
        P = np.array([p for i in g for p in segs[i]]); c = P.mean(0)
        l = float(np.median([np.linalg.norm(segs[i][1] - segs[i][0]) for i in g]))
        if all(np.linalg.norm(c - x['c']) > 0.3 for x in caixas):
            caixas.append({'tipo': tipo_padrao, 'c': c, 'raio': l / 2, 'lado': l, 'origem': 'laço de linhas'})
    # tipo pelo rótulo mais próximo
    for c in caixas:
        if c['tipo'] != tipo_padrao: continue
        best = min(rotulos, key=lambda t: np.linalg.norm(t['pts'][0, :2] - c['c']), default=None)
        if best is not None and np.linalg.norm(best['pts'][0, :2] - c['c']) < max(0.8, c['raio'] + 0.3):
            c['tipo'] = best['texto'].strip()
    # rótulo sem caixa: contorno fechado mais próximo
    quad = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] in layers_contorno and len(d['pts']) >= 4]
    quad = [q for q in quad if (np.linalg.norm(q[0] - q[-1]) < 0.01 or True) and lado[0] * 0.8 < np.ptp(q[:, 0]) < 2.0]
    for t in rotulos:
        p = t['pts'][0, :2]
        if any(np.linalg.norm(c['c'] - p) < 0.8 for c in caixas): continue
        cand = [q for q in quad if np.linalg.norm(q.mean(0) - p) < 1.0 and all(np.linalg.norm(q.mean(0) - c['c']) > 0.3 for c in caixas)]
        if not cand: continue
        q = min(cand, key=lambda q: (round(np.linalg.norm(q.mean(0) - p), 1), np.ptp(q[:, 0]) * np.ptp(q[:, 1])))
        qq = q[:-1] if np.linalg.norm(q[0] - q[-1]) < 0.01 else q
        l = float(np.median(np.hypot(*np.diff(q, axis=0).T)))
        caixas.append({'tipo': t['texto'].strip(), 'c': qq.mean(0), 'raio': l / 2, 'lado': l, 'origem': 'contorno do símbolo'})
    return caixas


def numerar(caixas, prefixo=''):
    caixas.sort(key=lambda c: (-round(c['c'][1], 1), c['c'][0]))
    cont = collections.Counter()
    for c in caixas:
        cont[c['tipo']] += 1; c['id'] = f"{prefixo}{c['tipo']}-{cont[c['tipo']]:02d}"
    return caixas


def cotas_caixas(ob, caixas, layer_txt, layer_chamada, tipos_fundos=('PVE', 'PVP', 'PV')):
    """CT/CF/(prof) com chamada; atribuição global (distância da ponta da chamada + coerência da profundidade com o tipo)."""
    tx = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == layer_txt]
    cts = [d for d in tx if d['texto'].upper().startswith('CT')]
    cfs = [d for d in tx if d['texto'].upper().startswith('CF')]
    profs = [d for d in tx if re.fullmatch(r'\(\s*[\d.,]+\s*\)', d['texto'].strip())]
    chamadas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] == layer_chamada]
    rot_cx = []
    for f in cfs:
        p = f['pts'][0, :2]
        ct = min(cts, key=lambda t: np.linalg.norm(t['pts'][0, :2] - p), default=None)
        ct = ct if ct is not None and np.linalg.norm(ct['pts'][0, :2] - p) < 0.4 else None
        # profundidade "(0.72)": entre as próximas, a que bate com CT − CF; senão a mais próxima
        viz = [t for t in profs if np.linalg.norm(t['pts'][0, :2] - p) < 3.5]
        pr = None
        if viz:
            if ct is not None:
                dif = num(ct['texto']) - num(f['texto'])
                ok = [t for t in viz if abs(num(t['texto']) - dif) < 0.015]
                if ok: pr = min(ok, key=lambda t: np.linalg.norm(t['pts'][0, :2] - p))
            if pr is None: pr = min(viz, key=lambda t: np.linalg.norm(t['pts'][0, :2] - p))
        alvo, dch = None, 0.6
        for ch in chamadas:
            if len(ch) < 2: continue
            ds = [dist_pt_seg(p, ch[i], ch[i + 1])[0] for i in range(len(ch) - 1)]
            k = int(np.argmin(ds))
            if ds[k] < dch:
                dch = ds[k]; alvo = ch[0] if k == len(ch) - 2 else ch[-1]
        rot_cx.append({'CT': num(ct['texto']) if ct else None, 'CF': num(f['texto']), 'prof': num(pr['texto']) if pr else None,
                       'p': p, 'alvo': alvo, 'txt': (ct['texto'] if ct else '') + ' / ' + f['texto'] + (' ' + pr['texto'] if pr else '')})
    custos = []
    for i, r in enumerate(rot_cx):
        ref = r['alvo'] if r['alvo'] is not None else r['p']
        prof = r['prof'] if r['prof'] is not None else ((r['CT'] - r['CF']) if r['CT'] is not None else None)
        for j, c in enumerate(caixas):
            if c['tipo'] in ('AP', 'PONTA'): continue
            d = float(np.linalg.norm(c['c'] - ref))
            if d > 3.0: continue
            pen = 0.0
            if prof is not None:
                if c['tipo'] in tipos_fundos and prof < 0.8: pen = 1.0
                if c['tipo'] not in tipos_fundos and prof > 1.2: pen = 2.0
            custos.append((d + pen, i, j, d))
    custos.sort()
    fr, fc = set(), set()
    for cst, i, j, d in custos:
        if i in fr or j in fc: continue
        r, c = rot_cx[i], caixas[j]
        c['CT'], c['CF'], c['prof'], c['rot_dist'], c['rot_txt'] = r['CT'], r['CF'], r['prof'], d, r['txt']
        fr.add(i); fc.add(j)
    sobras = [r for i, r in enumerate(rot_cx) if i not in fr]
    for r in sobras:
        c = min([c for c in caixas if c['tipo'] not in ('AP', 'PONTA')], key=lambda c: np.linalg.norm(c['c'] - r['p']))
        c.setdefault('rotulos_extra', []).append(r['txt'])
    return rot_cx, sobras


def eixos_tubos(ob, layers_tubo, dmin=0.02, dmax=0.45):
    paredes = [tuple(d['pts'][:2, :2]) for d in ob if d['tipo'] == 'LINE' and d['layer'] in layers_tubo]
    eixos, sobras = parear_paredes(paredes, dmin=dmin, dmax=dmax)
    for e in eixos: e['layer'] = layers_tubo[0]
    for d in ob:
        if d['tipo'] == 'MLINE' and d['layer'] in layers_tubo:
            p = d['pts'][:, :2]
            for a, b in zip(p[:-1], p[1:]):
                eixos.append({'p0': a, 'p1': b, 'd': d.get('escala', 0.1), 'origem': 'mline', 'layer': d['layer']})
    eixos = fundir_colineares(eixos)
    return [e for e in eixos if np.linalg.norm(e['p1'] - e['p0']) > 0.10], sobras


def rotulos_tubos(tx, T, mats=('PVC', 'PVCR', 'PVC-V', 'PVC-DR')):
    """Rótulo = "NNN mm" (+ material, + "i=N%") girado com o tubo; também "PVC 150 mm" numa linha."""
    grupos = []
    mm = [d for d in tx if re.search(r'\d+\s*mm\s*$', d['texto'].strip())]
    for m in mm:
        p = m['pts'][0, :2]
        t = m['texto'].strip()
        mt = re.match(r'(PVC[-A-Z]*)\s*(\d+)\s*mm', t)
        perto = [d for d in tx if np.linalg.norm(d['pts'][0, :2] - p) < 1.2 and abs(((d['rot'] - m['rot']) + 180) % 360 - 180) < 4]
        mat = mt.group(1) if mt else next((d['texto'].strip() for d in perto if re.fullmatch(r'PVC[-A-Z]*', d['texto'].strip())), '')
        dec = next((num(d['texto']) for d in perto if d['texto'].strip().lower().startswith('i=')), None)
        grupos.append({'p': p, 'rot': m['rot'], 'dn': float(mt.group(2)) if mt else num(t), 'mat': mat, 'i': dec})
    for t in T: t['rot'] = []
    for g in grupos:
        best = None
        for k, t in enumerate(T):
            for a, b in zip(t['pts'][:-1], t['pts'][1:]):
                a, b = np.asarray(a), np.asarray(b)
                if np.linalg.norm(b - a) < 0.05: continue
                d, s, q = dist_pt_seg(g['p'], a, b)
                ang = math.degrees(math.atan2(*(b - a)[::-1])) % 180
                da = abs(((g['rot'] % 180) - ang + 90) % 180 - 90)
                if d < 1.5 and da < 12 and (best is None or d < best[0]): best = (d, k)
        if best: T[best[1]]['rot'].append(g)
    return grupos


def sentido(T, R, setas, cx_por_id, lancamentos):
    nos = R.nos; gr = R.grau()
    for t in T:
        a, b = t['nos']
        s, n = sentido_por_setas(t['pts'], setas)
        t['fonte'] = 'seta' if s else ''
        if s == 0:
            ca = cx_por_id.get(nos[a]['caixa']); cb = cx_por_id.get(nos[b]['caixa'])
            if ca and cb and ca.get('CF') is not None and cb.get('CF') is not None and ca['CF'] != cb['CF']:
                s = 1 if ca['CF'] > cb['CF'] else -1; t['fonte'] = 'CF'
            else:
                for lado, sg in ((a, 1), (b, -1)):
                    c_ = cx_por_id.get(nos[lado]['caixa'])
                    livre = (nos[lado]['caixa'] is None and gr[lado] == 1) or (c_ is not None and c_['tipo'] == 'AP')
                    if livre:
                        perto_lanc = any(np.linalg.norm(nos[lado]['c'] - q) < 6 for q in lancamentos)
                        s = -sg if perto_lanc else sg; t['fonte'] = 'lançamento' if perto_lanc else 'ramal chega'
                        break
        t['s'] = s
    for _ in range(15):
        for t in T:
            if t['s']: continue
            a, b = t['nos']
            ent = lambda n_: sum(1 for u in T if u['s'] and ((u['s'] > 0 and u['nos'][1] == n_) or (u['s'] < 0 and u['nos'][0] == n_)))
            sai = lambda n_: sum(1 for u in T if u['s'] and ((u['s'] > 0 and u['nos'][0] == n_) or (u['s'] < 0 and u['nos'][1] == n_)))
            if ent(a) and not sai(a): t['s'], t['fonte'] = 1, 'continuidade'
            elif ent(b) and not sai(b): t['s'], t['fonte'] = -1, 'continuidade'
            elif sai(b) and not ent(b): t['s'], t['fonte'] = 1, 'continuidade'
            elif sai(a) and not ent(a): t['s'], t['fonte'] = -1, 'continuidade'
    # distância hidráulica (pelo grafo, sem sentido) até um lançamento: orienta o que ficou sem seta/CF
    import heapq
    adj = collections.defaultdict(list)
    for k, t in enumerate(T):
        a, b = t['nos']; adj[a].append((b, t['L'], k)); adj[b].append((a, t['L'], k))
    fontes = [n['id'] for n in nos if any(np.linalg.norm(np.asarray(n['c']) - q) < 6 for q in lancamentos) and len(adj[n['id']]) == 1]
    dist = {n: 0.0 for n in fontes}; hp = [(0.0, n) for n in fontes]
    while hp:
        d0, n = heapq.heappop(hp)
        if d0 > dist.get(n, 9e9): continue
        for m, L, k in adj[n]:
            if d0 + L < dist.get(m, 9e9):
                dist[m] = d0 + L; heapq.heappush(hp, (d0 + L, m))
    for t in T:
        a, b = t['nos']
        if t['fonte'] in ('', 'continuidade') or not t['s']:
            da, db = dist.get(a), dist.get(b)
            if da is not None and db is not None and da != db:
                s_new = 1 if da > db else -1
                if s_new != t['s']: t['s'] = s_new; t['fonte'] = 'distância ao lançamento'
    for t in T:
        a, b = t['nos']
        if t['s'] < 0:
            t['de'], t['para'] = b, a; t['pts_fluxo'] = [np.asarray(p) for p in t['pts'][::-1]]
        else:
            t['de'], t['para'] = a, b; t['pts_fluxo'] = [np.asarray(p) for p in t['pts']]


def tabela(T, R, cx_por_id, prefixo, dn_padrao=None):
    nos = R.nos; gr = R.grau(); linhas = []
    nome = lambda n_, c_: c_['id'] if c_ else ('PONTA' if gr[n_] == 1 else 'NO') + f'-{n_}'
    for k, t in enumerate(T):
        a, b = t['de'], t['para']
        ca, cb = cx_por_id.get(nos[a]['caixa']), cx_por_id.get(nos[b]['caixa'])
        g = t['rot'][0] if t['rot'] else {}
        dn = g.get('dn') or (dn_padrao(t['d']) if dn_padrao else round(t['d'] * 1000 / 25) * 25)
        i_calc = None
        cfa = ca.get('CF') if ca else None; cfb = cb.get('CF') if cb else None
        if cfa is not None and cfb is not None and t['L'] > 0: i_calc = (cfa - cfb) / t['L'] * 100
        obs = []
        if not t['rot']: obs.append('sem rótulo (Ø pela largura de desenho)')
        if len({(x['dn'], x['i']) for x in t['rot']}) > 1: obs.append('rótulos diferentes no mesmo trecho: ' + ', '.join(f"{x['mat']} {x['dn']:.0f} i={x['i']}" for x in t['rot']))
        if t['fonte'] in ('', 'indefinido') or not t['s']: obs.append('sentido indefinido')
        if i_calc is not None and i_calc < 0: obs.append('CF sobe no sentido do fluxo')
        z_arr = queda = None
        if cfa is not None and cfb is not None and g.get('i'):
            z_arr = cfa - g['i'] / 100 * t['L']; queda = z_arr - cfb
            if cb.get('CT') is not None and z_arr + dn / 1000 > cb['CT'] - 0.10:
                obs.append(f'com o i do rótulo chegaria a {z_arr:.2f}, acima da tampa de jusante (CT {cb["CT"]:.2f}): rótulo × cotas')
            elif queda < -0.05:
                obs.append(f'com o i do rótulo chegaria {-queda:.2f} m abaixo do fundo de jusante')
            elif queda > 0.30:
                obs.append(f'queda de {queda:.2f} m na caixa de jusante')
        linhas.append({'trecho': f'{prefixo}-{k+1:03d}', 'de': nome(a, ca), 'para': nome(b, cb), 'L_m': round(t['L'], 2),
                       'DN_mm': dn, 'material': g.get('mat', ''), 'i_rotulo_pct': g.get('i'),
                       'CF_montante': cfa, 'CF_jusante': cfb, 'i_pelas_CF_pct': round(i_calc, 2) if i_calc is not None else None,
                       'z_chegada_com_i_rotulo': round(z_arr, 3) if z_arr is not None else None,
                       'queda_na_jusante_m': round(queda, 3) if queda is not None else None,
                       'sentido': t['fonte'] or 'indefinido', 'classe': t.get('classe', ''), 'layer': '/'.join(t['layers']),
                       'largura_desenho_m': round(t['d'], 3),
                       'E_ini': round(float(t['pts_fluxo'][0][0]), 3), 'N_ini': round(float(t['pts_fluxo'][0][1]), 3),
                       'E_fim': round(float(t['pts_fluxo'][-1][0]), 3), 'N_fim': round(float(t['pts_fluxo'][-1][1]), 3),
                       'obs': ' | '.join(obs)})
    return linhas


def grau_caixas(caixas, R):
    g = R.grau()
    for c in caixas:
        n_ = next((n['id'] for n in R.nos if n['caixa'] == c['id']), None)
        c['grau'] = g[n_] if n_ is not None else 0


def salva_csv(linhas, caixas, fn_t, fn_n, extra_cols=()):
    with open(fn_t, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=';'); w.writeheader(); w.writerows(linhas)
    with open(fn_n, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['caixa', 'tipo', 'E', 'N', 'lado_ou_raio_m', 'CT', 'CF', 'prof_rotulo', 'CT-CF', 'tubos_ligados', 'obs'] + [c for c in extra_cols])
        for c in caixas:
            obs = list(c.get('obs', []))
            if c.get('CF') is None and c['tipo'] not in ('AP',): obs.append('sem cota no projeto')
            if c.get('rotulos_extra'): obs.append('rótulo extra: ' + ', '.join(c['rotulos_extra']))
            if c['grau'] == 0: obs.append('sem tubo ligado')
            if c.get('CT') is not None and c.get('CF') is not None and c.get('prof') is not None and abs(c['CT'] - c['CF'] - c['prof']) > 0.02:
                obs.append(f"CT − CF = {c['CT'] - c['CF']:.2f} ≠ profundidade do rótulo ({c['prof']:.2f})")
            w.writerow([c['id'], c['tipo'], round(float(c['c'][0]), 3), round(float(c['c'][1]), 3),
                        round(c['raio'] * (1 if c['tipo'].startswith('PV') else 2), 2), c.get('CT'), c.get('CF'), c.get('prof'),
                        round(c['CT'] - c['CF'], 2) if c.get('CT') is not None and c.get('CF') is not None else None, c['grau'],
                        ' | '.join(obs)] + [c.get(k, '') for k in extra_cols])
