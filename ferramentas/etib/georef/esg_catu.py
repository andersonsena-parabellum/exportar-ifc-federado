# -*- coding: utf-8 -*-
"""ETIB Catu — fase 2 do esgoto: extrai caixas, PVs, trechos, Ø, material, declividade do rótulo, sentido e as cotas
CT/CF das caixas do ESG-001-HIG-R02_GEO (UTM). Saídas em RELATORIOS: CSV de nós e trechos + mapa de validação.
Uso: python -I -X utf8 esg_catu.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from catu_comum import carrega, na_obra, num, REL, WRK, lote
from rede_lib import parear_paredes, fundir_colineares, Rede, sentido_por_setas, dist_pt_seg, unit

DATA = '2026-10-18'
ARQ = ('zw$7D57', 'zw$44A6')
L_TUBO = ('TQ-Condutos', 'TQ-Condutos Gordura', 'TQ-Condutos Espuma')


def main():
    E = carrega('ESG')
    ob = [d for d in E if not d['path'].startswith(ARQ) and not d['layer'].upper().startswith('ARQ') and na_obra(d['pts']).all()]

    # ---------------- caixas
    caixas = []
    for d in ob:   # PV: bloco zw$B504 (círculo duplo)
        if d['tipo'] == 'INSERT' and d['nome'] == 'zw$B504':
            r = max([x['r'] for x in ob if x['tipo'] == 'CIRCLE' and x['path'] == 'zw$B504' and np.linalg.norm(x['pts'][0, :2] - d['pts'][0, :2]) < 0.05] or [0.5])
            caixas.append({'tipo': 'PVE', 'c': d['pts'][0, :2], 'raio': r})
    # quadradas: 4 LINEs de 0,6 m no layer da caixa formando um laço
    segs = [d['pts'][:, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] == 'TQ-Caixa de alvenaria']
    segs = [s for s in segs if 0.4 < np.linalg.norm(s[1] - s[0]) < 1.3]
    pts = np.array([p for s in segs for p in s])
    grupo = list(range(len(segs)))
    def raiz(i):
        while grupo[i] != i: grupo[i] = grupo[grupo[i]]; i = grupo[i]
        return i
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if min(np.linalg.norm(a - b) for a in segs[i] for b in segs[j]) < 0.005:
                grupo[raiz(i)] = raiz(j)
    G = collections.defaultdict(list)
    for i in range(len(segs)): G[raiz(i)].append(i)
    for g in G.values():
        P = np.array([p for i in g for p in segs[i]])
        c = P.mean(0); lado = float(np.median([np.linalg.norm(segs[i][1] - segs[i][0]) for i in g]))
        if len(g) >= 3 and all(np.linalg.norm(c - x['c']) > 0.3 for x in caixas):
            caixas.append({'tipo': 'CX', 'c': c, 'raio': lado / 2, 'lado': lado})
    # tipo pelo rótulo do layer Simbolos (CE, CES, CG, CI...) mais próximo
    rot = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'Simbolos' and d['texto'].strip() in ('CE', 'CES', 'CG', 'CI', 'CIS', 'CP', 'CS')]
    for c in caixas:
        if c['tipo'] != 'CX': continue
        best = min(rot, key=lambda t: np.linalg.norm(t['pts'][0, :2] - c['c']), default=None)
        if best is not None and np.linalg.norm(best['pts'][0, :2] - c['c']) < 0.8:
            c['tipo'] = best['texto'].strip()
    # rótulo sem caixa achada: caixa = centro do quadrado fechado mais próximo (Simbolos / Simbolos_int / TQ-Caixa)
    quad = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] in ('Simbolos', 'Simbolos_int', 'TQ-Caixa de alvenaria') and len(d['pts']) >= 4]
    quad = [q for q in quad if np.linalg.norm(q[0] - q[-1]) < 0.01 and 0.3 < np.ptp(q[:, 0]) + 0.0 < 2.0]
    for t in rot:
        p = t['pts'][0, :2]
        if any(np.linalg.norm(c['c'] - p) < 0.8 for c in caixas): continue
        cand = [q for q in quad if np.linalg.norm(q[:-1].mean(0) - p) < 1.0
                and all(np.linalg.norm(q[:-1].mean(0) - c['c']) > 0.3 for c in caixas)]
        if not cand: continue
        q = min(cand, key=lambda q: (round(np.linalg.norm(q[:-1].mean(0) - p), 1), np.ptp(q[:, 0]) * np.ptp(q[:, 1])))
        c = q[:-1].mean(0)
        lado = float(np.median(np.hypot(*np.diff(q, axis=0).T)))
        caixas.append({'tipo': t['texto'].strip(), 'c': c, 'raio': lado / 2, 'lado': lado, 'origem': 'contorno do símbolo'})
    # numeração
    caixas.sort(key=lambda c: (-c['c'][1], c['c'][0]))
    cont = collections.Counter()
    for c in caixas:
        cont[c['tipo']] += 1; c['id'] = f"{c['tipo']}-{cont[c['tipo']]:02d}"

    # ---------------- cotas das caixas (CT / CF / (prof)) pela chamada (layer TEXTOS)
    tx = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'TQ-Textos conduto']
    cts = [d for d in tx if d['texto'].upper().startswith('CT')]
    cfs = [d for d in tx if d['texto'].upper().startswith('CF')]
    profs = [d for d in tx if re.fullmatch(r'\(\s*[\d.,]+\s*\)', d['texto'].strip())]
    chamadas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] == 'TEXTOS']
    rot_cx = []
    for f in cfs:   # o CF sempre existe; o CT pode faltar
        p = f['pts'][0, :2]
        ct = min(cts, key=lambda t: np.linalg.norm(t['pts'][0, :2] - (p + [0, 0.235])), default=None)
        ct = ct if ct is not None and np.linalg.norm(ct['pts'][0, :2] - (p + [0, 0.235])) < 0.15 else None
        pr = min(profs, key=lambda t: np.linalg.norm(t['pts'][0, :2] - p), default=None)
        pr = pr if pr is not None and np.linalg.norm(pr['pts'][0, :2] - p) < 3.5 else None
        # chamada: polilinha com um vértice perto do texto; a outra ponta aponta a caixa
        # chamada: o texto fica sobre o último (ou o primeiro) segmento; a ponta do lado oposto é a caixa
        alvo, dch = None, 0.6
        for ch in chamadas:
            if len(ch) < 2: continue
            ds = [dist_pt_seg(p, ch[i], ch[i + 1])[0] for i in range(len(ch) - 1)]
            k = int(np.argmin(ds))
            if ds[k] < dch:
                dch = ds[k]; alvo = ch[0] if k == len(ch) - 2 else ch[-1]
        rot_cx.append({'CT': num(ct['texto']) if ct else None, 'CF': num(f['texto']), 'prof': num(pr['texto']) if pr else None,
                       'p': p, 'alvo': alvo, 'txt': (ct['texto'] if ct else '') + ' / ' + f['texto']})
    # atribuição global: custo = distância da ponta da chamada à caixa + penalidade se a profundidade não combina
    # com o tipo (PV fundo, caixa de 60 rasa); cada caixa recebe um rótulo só
    custos = []
    for i, r in enumerate(rot_cx):
        ref = r['alvo'] if r['alvo'] is not None else r['p']
        prof = r['prof'] if r['prof'] is not None else ((r['CT'] - r['CF']) if r['CT'] is not None else None)
        for j, c in enumerate(caixas):
            d = float(np.linalg.norm(c['c'] - ref))
            if d > 3.0: continue
            pen = 0.0
            if prof is not None:
                if c['tipo'] == 'PVE' and prof < 0.8: pen = 1.0
                if c['tipo'] != 'PVE' and prof > 1.0: pen = 2.0
            custos.append((d + pen, i, j, d))
    custos.sort()
    feito_r, feito_c = set(), set()
    for cst, i, j, d in custos:
        if i in feito_r or j in feito_c: continue
        r, c = rot_cx[i], caixas[j]
        c['CT'], c['CF'], c['prof'], c['rot_dist'] = r['CT'], r['CF'], r['prof'], d
        feito_r.add(i); feito_c.add(j)
    for i, r in enumerate(rot_cx):
        if i not in feito_r:
            c = min(caixas, key=lambda c: np.linalg.norm(c['c'] - r['p']))
            c.setdefault('rotulos_extra', []).append(r['txt'])

    # ---------------- eixos dos tubos
    paredes = [tuple(d['pts'][:2, :2]) for d in ob if d['tipo'] == 'LINE' and d['layer'] in L_TUBO]
    eixos, sobras = parear_paredes(paredes, dmin=0.03, dmax=0.25)
    for e in eixos: e['layer'] = 'TQ-Condutos'
    for d in ob:   # linhas únicas
        if d['tipo'] in ('MLINE',) and d['layer'] in L_TUBO:
            p = d['pts'][:, :2]
            for a, b in zip(p[:-1], p[1:]):
                eixos.append({'p0': a, 'p1': b, 'd': d.get('escala', 0.1), 'origem': 'mline', 'layer': d['layer']})
    eixos = fundir_colineares(eixos)
    eixos = [e for e in eixos if np.linalg.norm(e['p1'] - e['p0']) > 0.10]
    R = Rede(caixas, snap_caixa=0.75, snap_ponta=0.12, snap_te=0.30).monta(eixos)
    T = R.trechos()

    # ---------------- setas e rótulos dos tubos
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and d['layer'].startswith('TQ-Sentido')]
    grupos = []   # rótulo de tubo: material + "NNN mm" + "i=N%"
    mm = [d for d in tx if re.fullmatch(r'\d+\s*mm', d['texto'].strip())]
    for m in mm:
        p = m['pts'][0, :2]
        perto = [d for d in tx if np.linalg.norm(d['pts'][0, :2] - p) < 1.0 and abs(((d['rot'] - m['rot']) + 180) % 360 - 180) < 3]
        mat = next((d['texto'].strip() for d in perto if d['texto'].strip().upper().startswith('PVC')), '')
        dec = next((num(d['texto']) for d in perto if d['texto'].strip().lower().startswith('i=')), None)
        grupos.append({'p': p, 'rot': m['rot'], 'dn': num(m['texto']), 'mat': mat, 'i': dec})
    for d in tx:   # rótulo numa linha só ("PVC 50mm")
        mt = re.fullmatch(r'(PVCR?)\s*(\d+)\s*mm', d['texto'].strip())
        if mt: grupos.append({'p': d['pts'][0, :2], 'rot': d['rot'], 'dn': float(mt.group(2)), 'mat': mt.group(1), 'i': None})
    for t in T:
        t['rot'] = []
    for g in grupos:
        best = None
        for k, t in enumerate(T):
            for a, b in zip(t['pts'][:-1], t['pts'][1:]):
                d, s, q = dist_pt_seg(g['p'], np.asarray(a), np.asarray(b))
                ang = math.degrees(math.atan2(*(np.asarray(b) - np.asarray(a))[::-1])) % 180
                da = abs(((g['rot'] % 180) - ang + 90) % 180 - 90)
                if d < 1.5 and da < 12 and (best is None or d < best[0]): best = (d, k)
        if best: T[best[1]]['rot'].append(g)

    # ---------------- tabela de trechos
    nos = R.nos
    cx_por_id = {c['id']: c for c in caixas}
    linhas = []
    # sentido: 1) seta do projeto; 2) CF das duas caixas; 3) ponta solta = ramal que chega (exceto o lançamento);
    # 4) continuidade (nó que só recebe manda para o trecho indefinido)
    lanc = [d['pts'][0, :2] for d in tx if 'INTERLIGAR' in d['texto'].upper() or 'SEGUE' in d['texto'].upper()]
    gr = R.grau()
    for t in T:
        a, b = t['nos']
        s, n = sentido_por_setas(t['pts'], setas)
        t['fonte'] = 'seta' if s else ''
        if s == 0:
            ca = cx_por_id.get(nos[a]['caixa']); cb = cx_por_id.get(nos[b]['caixa'])
            if ca and cb and ca.get('CF') is not None and cb.get('CF') is not None and ca['CF'] != cb['CF']:
                s = 1 if ca['CF'] > cb['CF'] else -1; t['fonte'] = 'CF'
            else:
                for lado, outro, sg in ((a, b, 1), (b, a, -1)):
                    if nos[lado]['caixa'] is None and gr[lado] == 1:
                        perto_lanc = any(np.linalg.norm(nos[lado]['c'] - q) < 6 for q in lanc)
                        s = -sg if perto_lanc else sg; t['fonte'] = 'lançamento' if perto_lanc else 'ramal chega'
                        break
        t['s'] = s
    for _ in range(10):
        for t in T:
            if t['s']: continue
            a, b = t['nos']
            ent = lambda n_: sum(1 for u in T if u['s'] and ((u['s'] > 0 and u['nos'][1] == n_) or (u['s'] < 0 and u['nos'][0] == n_)))
            sai = lambda n_: sum(1 for u in T if u['s'] and ((u['s'] > 0 and u['nos'][0] == n_) or (u['s'] < 0 and u['nos'][1] == n_)))
            if ent(a) and not sai(a): t['s'], t['fonte'] = 1, 'continuidade'
            elif ent(b) and not sai(b): t['s'], t['fonte'] = -1, 'continuidade'
            elif sai(b) and not ent(b): t['s'], t['fonte'] = 1, 'continuidade'
            elif sai(a) and not ent(a): t['s'], t['fonte'] = -1, 'continuidade'
    for k, t in enumerate(T):
        a, b = t['nos']; s = t['s']; fonte = t['fonte'] or 'indefinido'
        ca = cx_por_id.get(nos[a]['caixa']); cb = cx_por_id.get(nos[b]['caixa'])
        if s < 0: a, b, ca, cb = b, a, cb, ca
        t['de'], t['para'] = a, b
        g = t['rot'][0] if t['rot'] else {}
        dn = g.get('dn') or round(t['d'] * 1000 / 25) * 25
        nome = lambda n_, c_: c_['id'] if c_ else ('PONTA' if R.grau()[n_] == 1 else 'NO') + f'-{n_}'
        i_calc = None
        if ca and cb and ca.get('CF') is not None and cb.get('CF') is not None and t['L'] > 0:
            i_calc = (ca['CF'] - cb['CF']) / t['L'] * 100
        obs = []
        if not t['rot']: obs.append('sem rótulo (Ø pela largura de desenho)')
        if len(t['rot']) > 1 and len({(x['dn'], x['i']) for x in t['rot']}) > 1: obs.append('rótulos diferentes no mesmo trecho')
        if not ca: obs.append('montante sem caixa (ramal/ponta)')
        if not cb: obs.append('jusante sem caixa')
        if i_calc is not None and g.get('i') and abs(i_calc - g['i']) > 0.3: obs.append('declividade pelas CF ≠ rótulo')
        if i_calc is not None and i_calc < 0: obs.append('CF sobe no sentido do fluxo')
        # tubo saindo no CF de montante com a declividade do rótulo: onde chega na caixa de jusante?
        z_arr = queda = None
        if ca and cb and ca.get('CF') is not None and cb.get('CF') is not None and g.get('i'):
            z_arr = ca['CF'] - g['i'] / 100 * t['L']
            queda = z_arr - cb['CF']
            if cb.get('CT') is not None and z_arr + dn / 1000 > cb['CT'] - 0.10:
                obs.append(f'com i do rótulo chegaria a {z_arr:.2f}, acima da tampa da caixa de jusante (CT {cb["CT"]:.2f}): rótulo × cotas')
            elif queda < -0.05:
                obs.append(f'com i do rótulo chegaria {-queda:.2f} m abaixo do fundo de jusante')
            elif queda > 0.30:
                obs.append(f'queda de {queda:.2f} m na caixa de jusante')
        linhas.append({'trecho': f'ESG-{k+1:02d}', 'de': nome(a, ca), 'para': nome(b, cb), 'L_m': round(t['L'], 2),
                       'DN_mm': dn, 'material': g.get('mat', ''), 'i_rotulo_pct': g.get('i'),
                       'CF_montante': ca.get('CF') if ca else None, 'CF_jusante': cb.get('CF') if cb else None,
                       'i_pelas_CF_pct': round(i_calc, 2) if i_calc is not None else None,
                       'z_chegada_com_i_rotulo': round(z_arr, 3) if z_arr is not None else None,
                       'queda_na_jusante_m': round(queda, 3) if queda is not None else None,
                       'sentido': fonte, 'layer': '/'.join(t['layers']), 'largura_desenho_m': round(t['d'], 3),
                       'E_ini': round(float(nos[a]['c'][0]), 3), 'N_ini': round(float(nos[a]['c'][1]), 3),
                       'E_fim': round(float(nos[b]['c'][0]), 3), 'N_fim': round(float(nos[b]['c'][1]), 3),
                       'obs': ' | '.join(obs)})
    # ordena de montante para jusante (pelo CF de montante, depois nome)
    for c in caixas:
        g = R.grau()
        n_ = next((n['id'] for n in nos if n['caixa'] == c['id']), None)
        c['grau'] = g[n_] if n_ is not None else 0

    # ---------------- saídas
    os.makedirs(REL, exist_ok=True)
    fn_t = os.path.join(REL, f'ESG_fase2_trechos_{DATA}.csv'); fn_n = os.path.join(REL, f'ESG_fase2_caixas_{DATA}.csv')
    with open(fn_t, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=';'); w.writeheader(); w.writerows(linhas)
    with open(fn_n, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['caixa', 'tipo', 'E', 'N', 'lado_ou_raio_m', 'CT', 'CF', 'prof_rotulo', 'CT-CF', 'tubos_ligados', 'obs'])
        for c in caixas:
            obs = []
            if c.get('CF') is None: obs.append('sem cota no projeto')
            if c.get('rotulos_extra'): obs.append('rótulo extra: ' + ', '.join(c['rotulos_extra']))
            if c['grau'] == 0: obs.append('sem tubo ligado')
            w.writerow([c['id'], c['tipo'], round(float(c['c'][0]), 3), round(float(c['c'][1]), 3), round(c['raio'] * (2 if c['tipo'] != 'PVE' else 1), 2),
                        c.get('CT'), c.get('CF'), c.get('prof'),
                        round(c['CT'] - c['CF'], 2) if c.get('CT') is not None and c.get('CF') is not None else None, c['grau'], ' | '.join(obs)])
    json.dump({'caixas': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in caixas],
               'trechos': [{**l, 'pts': [list(map(float, p)) for p in T[i]['pts']]} for i, l in enumerate(linhas)]},
              open(os.path.join(WRK, 'esg_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # mapa
    S = carrega('SIT')
    arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO', 'PAGINA')):
            p = d['pts'][:, :2]
            if (p[:, 0].min() > 567660) and (p[:, 1].min() > 8634580) and (p[:, 0].max() < 567800): arq.extend(zip(p[:-1], p[1:]))
    fig, ax = plt.subplots(figsize=(17, 17))
    ax.add_collection(LineCollection(arq, colors='0.8', linewidths=0.3))
    cor = {100: '#8c564b', 150: '#d62728', 75: '#9467bd', 50: '#e377c2'}
    for l, t in zip(linhas, T):
        p = np.array([nos[t['de']]['c'], nos[t['para']]['c']]) if len(t['pts']) == 2 else np.array(t['pts'])
        if t['de'] != t['nos'][0]: p = p[::-1] if len(t['pts']) > 2 else p
        c = cor.get(int(l['DN_mm'] or 0), 'k')
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=2.2 if l['sentido'] != 'indefinido' else 1.2)
        m = p[len(p) // 2 - 1] if len(p) > 2 else p.mean(0)
        a0, a1 = (p[-2], p[-1]) if len(p) > 2 else (p[0], p[1])
        u = unit(np.asarray(a1) - np.asarray(a0))
        if l['sentido'] != 'indefinido':
            q = (p[0] + p[-1]) / 2 if len(p) == 2 else m
            ax.annotate('', xy=q + u * 0.8, xytext=q - u * 0.8, arrowprops=dict(arrowstyle='-|>', color=c, lw=1.5))
        ax.text(*((p[0] + p[-1]) / 2 + [0.3, 0.3]), f"{l['trecho']} Ø{int(l['DN_mm'] or 0)} i={l['i_rotulo_pct']}%", fontsize=6.5, color=c)
    for c in caixas:
        ax.plot(*c['c'], 's' if c['tipo'] != 'PVE' else 'o', ms=9 if c['tipo'] == 'PVE' else 7, mfc='w', mec='k')
        ax.text(c['c'][0] + 0.5, c['c'][1] - 0.9, f"{c['id']}\nCT {c.get('CT')} CF {c.get('CF')}", fontsize=6.5, color='navy')
    xs = np.array([c['c'] for c in caixas]); ax.set_xlim(xs[:, 0].min() - 6, xs[:, 0].max() + 8); ax.set_ylim(xs[:, 1].min() - 6, xs[:, 1].max() + 6)
    ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title(f'ETIB Catu — ESG-001-HIG-R02: rede extraída (fase 2) em UTM — {len(linhas)} trechos, {len(caixas)} caixas/PVs')
    fig.savefig(os.path.join(REL, f'ESG_fase2_mapa_{DATA}.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    # resumo
    print(f'caixas: {len(caixas)}', collections.Counter(c['tipo'] for c in caixas))
    print(f'trechos: {len(linhas)}  comprimento {sum(l["L_m"] for l in linhas):.1f} m', collections.Counter(l['DN_mm'] for l in linhas))
    print('sem caixa / pontas:', sum(1 for l in linhas if 'sem caixa' in l['obs']))
    for l in linhas: print(' ', l['trecho'], l['de'], '->', l['para'], l['L_m'], 'Ø', l['DN_mm'], l['material'], 'i', l['i_rotulo_pct'], '| CF', l['CF_montante'], l['CF_jusante'], 'icalc', l['i_pelas_CF_pct'], '|', l['sentido'], '|', l['obs'])
    for c in caixas: print(' ', c['id'], c['c'].round(2), 'CT', c.get('CT'), 'CF', c.get('CF'), 'grau', c['grau'], c.get('rotulos_extra', ''))
    print('eixos sem par (sobras):', len(sobras))


if __name__ == '__main__':
    main()
