# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 da drenagem pluvial das edificações e do pátio (parte AP do ESG-001-HIG-R00_GEO, UTM):
PVPs (bloco zw$12D9), CAs, prumadas AP, conexões verticais, filtros de água de chuva, trechos (Ø/material/i do rótulo),
sentido, cotas CT/CF e canaletas/calhas. A macrodrenagem (DRE-001/002) e o campo society (CPS DRE) vão em scripts próprios.
Uso: python -I -X utf8 ap_sat.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import Rede, ligar_pontas, unit, dist_pt_seg
import gravidade_lib as gl
from esg_sat import arq_sit

ARQ = ('ARQ_BASE', 'ARQ_LETRAS')
L_TQ = ('TQ-Condutos', 'TQ-Condutos Gordura', 'TQ-Condutos Espuma')


def dn_desenho(d):
    for lim, dn in ((0.05, 40), (0.085, 75), (0.12, 100), (0.17, 150), (0.22, 200), (0.27, 250), (0.33, 300)):
        if d < lim: return dn
    return 400


def limpa_eixos(eixos, nos=(), tique=0.8, gap=0.6):
    """Tira os tiques (< 0,8 m, oblíquos, encostados num eixo longo) e emenda eixos colineares com folga de até 0,6 m
    (os drenos PVC-DR estão desenhados em pedaços de ~4,5 m com tiques nas emendas)."""
    E = [dict(e) for e in eixos]
    L = lambda e: float(np.linalg.norm(e['p1'] - e['p0']))
    longos = [e for e in E if L(e) > 2.0]
    def e_tique(e):
        if L(e) >= tique: return False
        for n in nos:   # ligação curta de prumada/caixa não é tique
            if min(np.linalg.norm(e['p0'] - n['c']), np.linalg.norm(e['p1'] - n['c'])) < n['raio'] + n.get('snap', 0.75) + 0.1: return False
        for n in nos:   # ligação curta de prumada/caixa não é tique
            if min(np.linalg.norm(e['p0'] - n['c']), np.linalg.norm(e['p1'] - n['c'])) < n['raio'] + n.get('snap', 0.75) + 0.1: return False
        u = unit(e['p1'] - e['p0'])
        for f in longos:
            v = unit(f['p1'] - f['p0'])
            if abs(u @ v) > math.cos(math.radians(30)): continue
            for q in (e['p0'], e['p1']):
                if dist_pt_seg(q, f['p0'], f['p1'])[0] < 0.6: return True
        return False
    E = [e for e in E if not e_tique(e)]
    n_tiq = len(eixos) - len(E)
    mudou = True
    while mudou:
        mudou = False
        for i in range(len(E)):
            a = E[i]; ua = unit(a['p1'] - a['p0'])
            for j in range(i + 1, len(E)):
                b = E[j]; ub = unit(b['p1'] - b['p0'])
                if abs(ua @ ub) < math.cos(math.radians(3)) or abs(a['d'] - b['d']) > 0.03: continue
                # pontas mais próximas
                pares = [(np.linalg.norm(pa - pb), pa, pb, oa, ob_) for pa, oa in ((a['p0'], a['p1']), (a['p1'], a['p0'])) for pb, ob_ in ((b['p0'], b['p1']), (b['p1'], b['p0']))]
                dmin_, pa, pb, oa, ob_ = min(pares, key=lambda x: x[0])
                if dmin_ > gap or dmin_ < 1e-6: continue
                nrm = np.array([-ua[1], ua[0]])
                if abs((pb - pa) @ nrm) > 0.06: continue
                E[i] = {**a, 'p0': oa, 'p1': ob_, 'origem': a.get('origem', '') + '+emenda'}
                del E[j]; mudou = True; break
            if mudou: break
    return E, n_tiq


def main():
    E = sc.carrega('ESG')
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(ARQ)]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    # ---------------- nós de projeto
    caixas = gl.pvs_por_bloco(ob, 'zw$12D9', 'PVP')
    rot = [d for d in tx if d['layer'] == 'Simbolos' and d['texto'].strip() in ('CA', 'CS', 'CR', 'CX', 'CAG')]
    gl.caixas_quadradas(ob, caixas, ('AP-Caixa de alvenaria',), ('AP-Caixa de alvenaria', 'Simbolos', 'Simbolos_int'), rot)
    gl.numerar(caixas)
    # caixas do esgoto (só para disputar os rótulos de CT/CF, que estão no mesmo layer)
    cx_tq = gl.pvs_por_bloco(ob, 'zw$B504', 'PVE')
    rot_tq = [d for d in tx if d['layer'] == 'Simbolos' and d['texto'].strip() in ('CI', 'CE', 'CES', 'CG', 'CIS', 'CP')]
    gl.caixas_quadradas(ob, cx_tq, ('TQ-Caixa de alvenaria',), ('TQ-Caixa de alvenaria',), rot_tq)
    for i, c in enumerate(cx_tq): c['id'] = f'TQ#{i}'
    # filtros de água de chuva (desenho no layer AP-Filtro de água da chuva): agrupa por proximidade
    fl = [d['pts'][:, :2] for d in ob if d['layer'] == 'AP-Filtro de água da chuva']
    grupos = []
    for p in fl:
        c = p.mean(0)
        for g in grupos:
            if np.linalg.norm(g['c'] - c) < 1.5: g['pts'].append(p); g['c'] = np.vstack(g['pts']).mean(0); break
        else: grupos.append({'pts': [p], 'c': c})
    filtros = []
    for i, g in enumerate(grupos):
        P = np.vstack(g['pts']); lo, hi = P.min(0), P.max(0)
        filtros.append({'id': f'FILTRO-{i+1:02d}', 'tipo': 'FILTRO', 'c': (lo + hi) / 2, 'raio': float(max(hi - lo)) / 2, 'snap': 0.4, 'corta': False})
    # prumadas: balão com chamada (layer AP-Indicação coluna)
    circ = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'AP-Indicação coluna']
    cen = np.array([d['pts'][0, :2] for d in circ]); rr = np.array([d['r'] for d in circ])
    txt_ap = [d for d in tx if d['layer'] == 'AP-Indicação coluna']
    prumadas = []
    for d in ob:
        if d['tipo'] != 'LINE' or d['layer'] != 'AP-Indicação coluna': continue
        a, b = d['pts'][0, :2], d['pts'][1, :2]
        da = np.min(np.abs(np.hypot(*(cen - a).T) - rr)); db = np.min(np.abs(np.hypot(*(cen - b).T) - rr))
        if abs(da) < 0.02 and abs(db) < 0.02: continue
        col, bal = (b, a) if db > da else (a, b)
        k = int(np.argmin(np.abs(np.hypot(*(cen - bal).T) - rr)))
        c0, r0 = cen[k], rr[k]
        dentro = [t for t in txt_ap if np.linalg.norm(t['pts'][0, :2] - c0) < r0 * 1.05]
        ids = [t['texto'].strip() for t in dentro if re.fullmatch(r'AP-\s*\d+', t['texto'].strip())]
        dns = [sc.num(t['texto']) for t in dentro if t['texto'].strip().endswith('mm') or t['texto'].strip().startswith('ø')]
        prumadas.append({'tipo': 'AP', 'c': col.copy(), 'raio': 0.05, 'snap': 0.35, 'corta': False,
                         'ap': ids[0] if ids else '', 'dn_prumada': dns[0] if dns else None, 'balao': c0})
    pr2 = []
    for p in prumadas:
        if all(np.linalg.norm(p['c'] - q['c']) > 0.10 for q in pr2): pr2.append(p)
    for i, p in enumerate(pr2): p['id'] = p['ap'] if p['ap'] else f'AP-s{i+1:02d}'
    rep = collections.Counter(p['id'] for p in pr2); vis = collections.Counter()
    for p in pr2:
        if rep[p['id']] > 1: vis[p['id']] += 1; p['id'] = f"{p['id']}#{vis[p['id']]}"
    # conexões verticais: círculo duplo pequeno (Simbolos + Simbolos_int concêntricos, r < 0,15 m), fora dos blocos de PV
    cs = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'Simbolos' and d['r'] < 0.15 and not d['path'].endswith(('zw$12D9', 'zw$B504'))]
    ci = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'Simbolos_int' and d['r'] < 0.15]
    verticais = []
    for d in cs:
        p = d['pts'][0, :2]
        if any(np.linalg.norm(x['pts'][0, :2] - p) < 0.005 for x in ci) and all(np.linalg.norm(v['c'] - p) > 0.02 for v in verticais):
            verticais.append({'c': p, 'r': d['r'], 'dn': 40 if d['r'] < 0.04 else (100 if d['r'] < 0.07 else 150)})
    lanc_txt = [d for d in tx if 'CONECTAR A REDE' in d['texto'].upper() or 'SEGUE PARA O RESERV' in d['texto'].upper()]
    lanc = [d['pts'][0, :2] for d in lanc_txt]
    # ---------------- cotas (disputa com as caixas do esgoto)
    todos = caixas + cx_tq
    rot_cx, sobras_rot = gl.cotas_caixas(ob, todos, 'TQ-Textos conduto', 'TEXTOS', tipos_fundos=('PVP', 'PVE'))
    # ---------------- eixos e rede
    eixos, sobras = gl.eixos_tubos(ob, ('AP-Condutos',), dmin=0.02, dmax=0.45)
    eixos, n_tiq = limpa_eixos(eixos, caixas + pr2 + filtros)
    print('tiques descartados', n_tiq, '| eixos depois da emenda', len(eixos))
    canaletas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] == 'AP-Condutos' and np.hypot(*np.diff(d['pts'][:, :2], axis=0).T).sum() > 5]
    nos_proj = caixas + pr2 + filtros
    R = Rede(nos_proj, snap_caixa=0.75, snap_ponta=0.10, snap_te=0.25).monta(eixos)
    n_lig = ligar_pontas(R, gap=0.9, gap_caixa=1.2)
    T = R.trechos()
    for t in T: t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
    laco = [t for t in T if t['nos'][0] == t['nos'][1]]
    T = [t for t in T if t['L'] > 0.15 and t['nos'][0] != t['nos'][1]]
    # 2ª passada: tiques de < 0,8 m soltos numa ponta (traço do símbolo de dreno) saem, e a rede é remontada
    gr = R.grau()
    solto = lambda n: R.nos[n]['caixa'] is None and gr[n] == 1
    tiques = [t for t in T if t['L'] < 0.8 and (solto(t['nos'][0]) or solto(t['nos'][1]))]
    if tiques:
        fora = {m for t in tiques for m in t['arestas']}
        eixos2 = [{'p0': np.asarray(a['pts'][0], float), 'p1': np.asarray(a['pts'][1], float), 'd': a['d'], 'origem': a['origem'], 'layer': a['layer']}
                  for k, a in enumerate(R.arestas) if k not in fora]
        R = Rede(nos_proj, snap_caixa=0.75, snap_ponta=0.10, snap_te=0.25).monta(eixos2)
        n_lig += ligar_pontas(R, gap=0.9, gap_caixa=1.2)
        T = R.trechos()
        for t in T: t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
        T = [t for t in T if t['L'] > 0.15 and t['nos'][0] != t['nos'][1]]
    print('tiques de dreno descartados:', len(tiques))
    cx_por_id = {c['id']: c for c in nos_proj}
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and d['layer'] == 'AP-Sentido conduto']
    # rótulos: AP-Textos conduto, menos os que estão junto de um tubo de esgoto
    tq = [d['pts'][:2, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] in L_TQ]
    ap = [d['pts'][:2, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] == 'AP-Condutos']
    def dmin(p, S, rot):
        best = 9.0
        for a, b in S:
            if np.linalg.norm(b - a) < 0.05: continue
            ang = math.degrees(math.atan2(*(b - a)[::-1])) % 180
            if abs(((rot % 180) - ang + 90) % 180 - 90) > 12: continue
            best = min(best, dist_pt_seg(p, a, b)[0])
        return best
    rot_ap = [d for d in tx if d['layer'] == 'AP-Textos conduto' and not (dmin(d['pts'][0, :2], tq, d['rot']) < min(1.5, dmin(d['pts'][0, :2], ap, d['rot'])))]
    gl.rotulos_tubos(rot_ap, T, mats=('PVC', 'PVCR', 'PVC-V', 'PVC-DR'))
    gl.sentido(T, R, setas, cx_por_id, lanc)
    # calhas metálicas da cobertura ("Calha Metálica" + "400 x 150 mm" / "650 x 350 mm"): não são rede enterrada
    secoes = [(d['pts'][0, :2], d['rot'], d['texto'].strip()) for d in tx if d['layer'] == 'AP-Textos conduto' and re.fullmatch(r'\d+\s*x\s*\d+\s*mm', d['texto'].strip())]
    for t in T:
        t['secao'] = ''
        P = [np.asarray(q) for q in t['pts']]
        for (q, r_, txt) in secoes:
            for a, b in zip(P[:-1], P[1:]):
                if np.linalg.norm(b - a) < 0.05: continue
                ang = math.degrees(math.atan2(*(b - a)[::-1])) % 180
                if abs(((r_ % 180) - ang + 90) % 180 - 90) < 12 and dist_pt_seg(q, a, b)[0] < 1.5: t['secao'] = txt
        if not t['secao'] and t['d'] > 0.33 and not any(r['mat'].startswith('PVC') for r in t['rot']): t['secao'] = 'largura %.2f m' % t['d']
    for t in T:
        dn = t['rot'][0]['dn'] if t['rot'] else dn_desenho(t['d'])
        mat = t['rot'][0]['mat'] if t['rot'] else ''
        if t['secao']:
            t['classe'] = 'calha metálica (cobertura)'; t['vert'] = []; continue
        a, b = R.nos[t['de']], R.nos[t['para']]
        ta = cx_por_id.get(a['caixa'], {}).get('tipo'); tb = cx_por_id.get(b['caixa'], {}).get('tipo')
        if mat == 'PVC-DR': t['classe'] = 'dreno (PVC-DR)'
        elif dn <= 50: t['classe'] = 'dreno'
        elif (ta in ('PVP', 'CA') and tb in ('PVP', 'CA')) or dn >= 150: t['classe'] = 'coletor'
        else: t['classe'] = 'ramal'
        t['vert'] = []
        for v in verticais:
            for nome, p in (('montante', t['pts_fluxo'][0]), ('jusante', t['pts_fluxo'][-1])):
                if np.linalg.norm(v['c'] - p) < 0.6: t['vert'].append((nome, v['dn']))
    linhas = gl.tabela(T, R, cx_por_id, 'AP', dn_padrao=dn_desenho)
    for l, t in zip(linhas, T):
        if t['secao']:
            l['DN_mm'] = None; l['material'] = 'Calha metálica ' + t['secao']
            l['obs'] = 'calha da cobertura (aérea): não entra na rede enterrada'
        l['conexao_vertical'] = '; '.join(f'{n} Ø{d}' for n, d in t['vert'])
        if t['presumido']: l['obs'] = (l['obs'] + ' | ' if l['obs'] else '') + 'ligação presumida (desenho não encosta, < 0,9 m)'
    gl.grau_caixas(nos_proj, R)
    # espinha de drenos sob o campo society desenhada no ESG-001: o usuário decidiu (18/10/2026) seguir o CPS DRE-001
    # e não representar drenagem do campo no projeto de esgoto -> sai o componente da rede que está no campo (> 50 % dos pontos)
    C0 = np.array([545903.871, 8716168.206]); th = math.radians(127.743934)
    u_ = np.array([math.cos(th), math.sin(th)]); v_ = np.array([-u_[1], u_[0]])
    no_campo = lambda q: abs((np.asarray(q[:2]) - C0) @ u_) <= 52.8 / 2 + 2 and abs((np.asarray(q[:2]) - C0) @ v_) <= 33.4 / 2 + 2
    adj = collections.defaultdict(set)
    for i, l in enumerate(linhas): adj[l['de']].add(i); adj[l['para']].add(i)
    vis, fora_campo = set(), set()
    for i in range(len(linhas)):
        if i in vis: continue
        pilha, comp = [i], []
        while pilha:
            k = pilha.pop()
            if k in vis: continue
            vis.add(k); comp.append(k)
            for n_ in (linhas[k]['de'], linhas[k]['para']): pilha.extend(adj[n_] - vis)
        pts = [q for k in comp for q in T[k]['pts_fluxo']]
        if np.mean([no_campo(q) for q in pts]) > 0.5: fora_campo |= set(comp)
    removidos = [linhas[k] for k in sorted(fora_campo)]
    cx_rem = {l[x] for l in removidos for x in ('de', 'para') if l[x].startswith('CA')}
    cx_rem = {c for c in cx_rem if all(l['de'] != c and l['para'] != c for k, l in enumerate(linhas) if k not in fora_campo)}
    if removidos:
        with open(os.path.join(sc.REL, 'SAT_fase2_AP_removidos_campo.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(removidos[0].keys()), delimiter=';'); w.writeheader(); w.writerows(removidos)
    print(f'espinha do campo retirada: {len(removidos)} trechos, {sum(l["L_m"] for l in removidos):.1f} m, caixas {sorted(cx_rem)}')
    linhas = [l for k, l in enumerate(linhas) if k not in fora_campo]
    T = [t for k, t in enumerate(T) if k not in fora_campo]
    caixas = [c for c in caixas if c['id'] not in cx_rem]
    # ---------------- saídas
    gl.salva_csv(linhas, caixas + filtros, os.path.join(sc.REL, 'SAT_fase2_AP_trechos.csv'), os.path.join(sc.REL, 'SAT_fase2_AP_caixas.csv'))
    with open(os.path.join(sc.REL, 'SAT_fase2_AP_prumadas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['prumada', 'E', 'N', 'DN_rotulo_mm', 'tubos_ligados', 'obs'])
        for p in pr2: w.writerow([p['id'], round(float(p['c'][0]), 3), round(float(p['c'][1]), 3), p['dn_prumada'], p['grau'], '' if p['grau'] else 'prumada sem tubo ligado'])
    with open(os.path.join(sc.REL, 'SAT_fase2_AP_canaletas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['canaleta', 'L_m', 'E_ini', 'N_ini', 'E_fim', 'N_fim'])
        for i, c in enumerate(canaletas):
            w.writerow([f'CAN-{i+1:02d}', round(float(np.hypot(*np.diff(c, axis=0).T).sum()), 2), *np.round(c[0], 3), *np.round(c[-1], 3)])
    json.dump({'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in nos_proj],
               'verticais': [{'c': v['c'].tolist(), 'dn': v['dn']} for v in verticais], 'canaletas': [c.tolist() for c in canaletas],
               'lancamentos': [{'c': d['pts'][0, :2].tolist(), 'texto': d['texto']} for d in lanc_txt],
               'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)]},
              open(os.path.join(sc.WRK, 'ap_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---------------- mapa
    arq = arq_sit()
    cor = {'coletor': '#1f77b4', 'ramal': '#17becf', 'dreno': '#9edae5', 'dreno (PVC-DR)': '#2ca02c', 'calha metálica (cobertura)': '#ff7f0e'}
    fig, ax = plt.subplots(figsize=(18, 18))
    ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
    for c in canaletas: ax.plot(c[:, 0], c[:, 1], '-', color='#bcbd22', lw=3, alpha=0.6)
    for l, t in zip(linhas, T):
        p = np.array(t['pts_fluxo']); c = cor.get(l['classe'], 'k') if l['sentido'] != 'indefinido' else 'r'
        lw = {40: 0.8, 75: 1.0, 100: 1.4, 150: 2.2, 200: 2.8, 250: 3.2, 300: 3.6}.get(int(l['DN_mm'] or 100), 2)
        if l['classe'].startswith('calha'): ax.plot(p[:, 0], p[:, 1], '--', color=c, lw=1.6); continue
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=lw)
        L = np.cumsum(np.r_[0, np.hypot(*np.diff(p, axis=0).T)]); m = L[-1] / 2
        k = max(0, np.searchsorted(L, m) - 1); u = unit(p[k + 1] - p[k]); q = p[k] + u * (m - L[k])
        if l['L_m'] > 1.5: ax.annotate('', xy=q + u * 0.5, xytext=q - u * 0.5, arrowprops=dict(arrowstyle='-|>', color=c, lw=1))
        if l['classe'] == 'coletor': ax.text(*(q + [0.3, 0.3]), f"Ø{int(l['DN_mm'] or 0)} i={l['i_rotulo_pct']}", fontsize=5.5, color=c)
    for c in caixas:
        ax.plot(*c['c'], 'o' if c['tipo'] == 'PVP' else 'D', ms=8 if c['tipo'] == 'PVP' else 6, mfc='w', mec='k')
        ax.text(c['c'][0] + 0.5, c['c'][1] - 0.8, f"{c['id']} CF {c.get('CF')}", fontsize=5.5, color='navy')
    for f_ in filtros: ax.plot(*f_['c'], 'h', ms=8, color='teal')
    for p in pr2: ax.plot(*p['c'], '^', ms=4, color='purple' if p['grau'] else 'r')
    for q in lanc: ax.plot(*q, 'r*', ms=14)
    ax.set_xlim(545845, 546050); ax.set_ylim(8716085, 8716270)
    ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title('ETIB Sátiro Dias — ESG-001 (AP) pluvial extraída (fase 2): azul = coletor, ciano = ramal, verde = dreno PVC-DR, laranja tracejado = calha metálica da cobertura, vermelho = sentido indefinido; '
                 '▲ prumada (vermelha = sem tubo), ⬢ filtro, ★ lançamento, amarelo = canaleta/calha', fontsize=9)
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_AP_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print('caixas', len(caixas), collections.Counter(c['tipo'] for c in caixas), '| filtros', len(filtros), '| prumadas', len(pr2), '| verticais', len(verticais), '| canaletas', len(canaletas))
    print('trechos', len(linhas), f"{sum(l['L_m'] for l in linhas):.1f} m", collections.Counter(l['classe'] for l in linhas))
    print('por DN', sorted(collections.Counter(l['DN_mm'] for l in linhas).items(), key=lambda x: x[0] or 0))
    print('sentido', collections.Counter(l['sentido'] for l in linhas))
    print('sem caixa a jusante (sem calhas)', sum(1 for l in linhas if l['para'].startswith(('PONTA', 'NO')) and not l['classe'].startswith('calha')), '| prumadas sem tubo', [p['id'] for p in pr2 if not p['grau']])
    print('caixas sem cota', [c['id'] for c in caixas if c.get('CF') is None], '| rótulos sobrando', [r['txt'] for r in sobras_rot])
    print('paredes sem par', len(sobras), '| ligações presumidas', n_lig, '| laços descartados', len(laco))
    print('lançamentos', [(d['texto'][:50], np.round(d['pts'][0, :2], 1).tolist()) for d in lanc_txt])


if __name__ == '__main__':
    main()
