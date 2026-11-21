# -*- coding: utf-8 -*-
"""ETIB Catu — fase 2 da drenagem (DRE-001-DRG-R02_GEO, UTM): nós de projeto (PVP, CA, CE, prumadas AP, conexões verticais,
lançamentos), eixos (pares de parede exclusivos + MLINE), sentido, rótulos, cotas CT/CF das caixas e canaletas.
Saídas em RELATORIOS: CSV de trechos, de caixas/nós e de canaletas + mapa de validação.
Uso: python -I -X utf8 dre_catu.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from catu_comum import carrega, na_obra, num, REL, WRK
from rede_lib import Rede, dist_pt_seg, unit, ligar_pontas
import gravidade_lib as gl

DATA = '2026-10-18'
ARQ = ('zw$D46B', 'zw$7D57', 'zw$44A6')


def dn_desenho(d):
    for lim, dn in ((0.05, 40), (0.085, 75), (0.12, 100), (0.17, 150), (0.22, 200), (0.27, 250), (0.33, 300)):
        if d < lim: return dn
    return 400


def main():
    E = carrega('DRE')
    ob = [d for d in E if not d['path'].startswith(ARQ) and not d['layer'].upper().startswith('ARQ')
          and d['layer'] != 'TQ-Aparelho sanitário' and na_obra(d['pts']).all()]

    # ---------------- nós de projeto
    caixas = gl.pvs_por_bloco(ob, 'zw$12D9', 'PVP')
    rot = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'Simbolos' and d['texto'].strip() in ('CA', 'CI', 'CS', 'CR', 'CX')]   # CE/TQ = caixa do esgoto copiada na prancha
    gl.caixas_quadradas(ob, caixas, ('AP-Caixa de alvenaria',), ('AP-Caixa de alvenaria', 'Simbolos', 'Simbolos_int'), rot)
    gl.numerar(caixas)
    # prumadas: chamada (LINE do layer AP-Indicação coluna que não é diâmetro do balão); a ponta longe do balão é a coluna
    circ = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'AP-Indicação coluna']
    cen = np.array([d['pts'][0, :2] for d in circ]); rr = np.array([d['r'] for d in circ])
    txt_ap = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'AP-Indicação coluna']
    prumadas = []
    for d in ob:
        if d['tipo'] != 'LINE' or d['layer'] != 'AP-Indicação coluna': continue
        a, b = d['pts'][0, :2], d['pts'][1, :2]
        da = np.min(np.abs(np.hypot(*(cen - a).T) - rr)); db = np.min(np.abs(np.hypot(*(cen - b).T) - rr))
        if abs(da) < 0.02 and abs(db) < 0.02: continue          # diâmetro/divisão do balão
        col, bal = (b, a) if db > da else (a, b)
        k = int(np.argmin(np.abs(np.hypot(*(cen - bal).T) - rr)))
        c0, r0 = cen[k], rr[k]
        dentro = [t for t in txt_ap if np.linalg.norm(t['pts'][0, :2] - c0) < r0 * 1.05]
        ids = [t['texto'].strip() for t in dentro if re.fullmatch(r'AP-\s*\d+', t['texto'].strip())]
        dns = [num(t['texto']) for t in dentro if t['texto'].strip().endswith('mm')]
        prumadas.append({'tipo': 'AP', 'c': col.copy(), 'raio': 0.05, 'snap': 0.35, 'corta': False,
                         'ap': ids[0] if ids else '', 'dn_prumada': dns[0] if dns else None, 'balao': c0})
    # deduplica prumadas (mesma ponta)
    pr2 = []
    for p in prumadas:
        if all(np.linalg.norm(p['c'] - q['c']) > 0.10 for q in pr2): pr2.append(p)
    for i, p in enumerate(pr2): p['id'] = p['ap'] if p['ap'] else f'AP-s{i+1:02d}'
    ids_rep = collections.Counter(p['id'] for p in pr2); vistos = collections.Counter()
    for p in pr2:
        base = p['id']
        if ids_rep[base] > 1:
            vistos[base] += 1; p['id'] = f'{base}#{vistos[base]}'
    # conexões verticais: círculo duplo pequeno (Simbolos + Simbolos_int concêntricos, r < 0,15 m)
    cs = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'Simbolos' and d['r'] < 0.15 and not d['path'].endswith('zw$12D9')]
    ci = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'Simbolos_int' and d['r'] < 0.15]
    verticais = []
    for d in cs:
        p = d['pts'][0, :2]
        if any(np.linalg.norm(x['pts'][0, :2] - p) < 0.005 for x in ci):
            if all(np.linalg.norm(v['c'] - p) > 0.02 for v in verticais):
                verticais.append({'c': p, 'r': d['r'], 'dn': 40 if d['r'] < 0.04 else (100 if d['r'] < 0.07 else 150)})
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    lanc = [d['pts'][0, :2] for d in tx if 'INTERLIGAR' in d['texto'].upper()]

    # ---------------- cotas das caixas
    rot_cx, sobras_rot = gl.cotas_caixas(ob, caixas, 'TQ-Textos conduto', 'TEXTOS', tipos_fundos=('PVP',))

    # ---------------- eixos e rede
    eixos, sobras = gl.eixos_tubos(ob, ('AP-Condutos',), dmin=0.02, dmax=0.45)
    # canaletas: PL longas do layer AP-Condutos (semicirculares com grelha, i=3 %) ficam fora da rede de tubos
    canaletas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] == 'AP-Condutos' and np.hypot(*np.diff(d['pts'][:, :2], axis=0).T).sum() > 5]
    nos_proj = caixas + pr2
    R = Rede(nos_proj, snap_caixa=0.75, snap_ponta=0.10, snap_te=0.25).monta(eixos)
    n_lig = ligar_pontas(R, gap=0.9, gap_caixa=1.2)
    T = R.trechos()
    for t in T:
        t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
    laco = [t for t in T if t['nos'][0] == t['nos'][1]]
    T = [t for t in T if t['L'] > 0.15 and t['nos'][0] != t['nos'][1]]
    json.dump([{'L': t['L'], 'd': t['d'], 'no': int(t['nos'][0]), 'c': [float(x) for x in R.nos[t['nos'][0]]['c']], 'pts': [list(map(float, p)) for p in t['pts']]} for t in laco],
              open(os.path.join(WRK, 'dre_lacos.json'), 'w'), indent=0)
    cx_por_id = {c['id']: c for c in nos_proj}
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and d['layer'] == 'AP-Sentido conduto']
    gl.rotulos_tubos([d for d in tx if d['layer'] == 'AP-Textos conduto'], T)
    gl.sentido(T, R, setas, cx_por_id, lanc)
    # classe: coletor (entre caixas/PV ou DN >= 150) × ramal de prumada × dreno (DN <= 50)
    for t in T:
        dn = t['rot'][0]['dn'] if t['rot'] else dn_desenho(t['d'])
        a, b = R.nos[t['de']], R.nos[t['para']]
        ta = cx_por_id.get(a['caixa'], {}).get('tipo'); tb = cx_por_id.get(b['caixa'], {}).get('tipo')
        if dn <= 50: t['classe'] = 'dreno'
        elif ta in ('PVP', 'CA', 'CE') and tb in ('PVP', 'CA', 'CE') or dn >= 150: t['classe'] = 'coletor'
        else: t['classe'] = 'ramal'
        # conexão vertical na ponta de montante (pé de prumada) ou perto da caixa de jusante (mergulho)
        t['vert'] = []
        for v in verticais:
            for nome, p in (('montante', t['pts_fluxo'][0]), ('jusante', t['pts_fluxo'][-1])):
                if np.linalg.norm(v['c'] - p) < 0.6: t['vert'].append((nome, v['dn']))
    linhas = gl.tabela(T, R, cx_por_id, 'DRE', dn_padrao=dn_desenho)
    for l, t in zip(linhas, T):
        l['conexao_vertical'] = '; '.join(f'{n} Ø{d}' for n, d in t['vert'])
        if t['presumido']: l['obs'] = (l['obs'] + ' | ' if l['obs'] else '') + 'tem ligação presumida (desenho não encosta, < 0,9 m)'
    gl.grau_caixas(nos_proj, R)

    # ---------------- saídas
    fn_t = os.path.join(REL, f'DRE_fase2_trechos_{DATA}.csv'); fn_n = os.path.join(REL, f'DRE_fase2_caixas_{DATA}.csv')
    gl.salva_csv(linhas, caixas, fn_t, fn_n)
    with open(os.path.join(REL, f'DRE_fase2_prumadas_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['prumada', 'E', 'N', 'DN_rotulo_mm', 'tubos_ligados', 'obs'])
        for p in pr2:
            w.writerow([p['id'], round(float(p['c'][0]), 3), round(float(p['c'][1]), 3), p['dn_prumada'], p['grau'],
                        '' if p['grau'] else 'prumada sem tubo ligado'])
    with open(os.path.join(REL, f'DRE_fase2_canaletas_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['canaleta', 'L_m', 'E_ini', 'N_ini', 'E_fim', 'N_fim', 'descricao'])
        for i, c in enumerate(canaletas):
            w.writerow([f'CAN-{i+1:02d}', round(float(np.hypot(*np.diff(c, axis=0).T).sum()), 2), *np.round(c[0], 3), *np.round(c[-1], 3),
                        'canaleta semicircular em concreto com grelha metálica, i=3% (texto do projeto)'])
    json.dump({'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in nos_proj],
               'verticais': [{'c': v['c'].tolist(), 'dn': v['dn']} for v in verticais],
               'canaletas': [c.tolist() for c in canaletas],
               'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)]},
              open(os.path.join(WRK, 'dre_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    mapa(linhas, T, caixas, pr2, canaletas, lanc)
    # resumo
    print('caixas', len(caixas), collections.Counter(c['tipo'] for c in caixas), '| prumadas', len(pr2), '| verticais', len(verticais), '| canaletas', len(canaletas))
    print('trechos', len(linhas), f"{sum(l['L_m'] for l in linhas):.1f} m", collections.Counter(l['classe'] for l in linhas))
    print('por DN', sorted(collections.Counter(l['DN_mm'] for l in linhas).items(), key=lambda x: x[0] or 0))
    print('sentido', collections.Counter(l['sentido'] for l in linhas))
    print('sem caixa a jusante', sum(1 for l in linhas if l['para'].startswith(('PONTA', 'NO'))), '| prumadas sem tubo', sum(1 for p in pr2 if not p['grau']))
    print('caixas sem cota', [c['id'] for c in caixas if c.get('CF') is None], '| rótulos sobrando', [r['txt'] for r in sobras_rot])
    print('paredes sem par', len(sobras), '| ligações presumidas', n_lig, '| arestas duplicadas', getattr(R, 'duplicadas', 0), '| laços descartados', len(laco), f"({sum(t['L'] for t in laco):.1f} m)")
    return linhas, T, caixas, pr2


def mapa(linhas, T, caixas, pr2, canaletas, lanc):
    S = carrega('SIT')
    arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO', 'PAGINA')):
            p = d['pts'][:, :2]
            if p[:, 0].min() > 567620 and p[:, 1].min() > 8634540 and p[:, 0].max() < 567800: arq.extend(zip(p[:-1], p[1:]))
    cor = {'coletor': '#1f77b4', 'ramal': '#17becf', 'dreno': '#9edae5'}
    for nome, lim in (('geral', None), ('norte', (567650, 567745, 8634625, 8634712)), ('sul', (567660, 567795, 8634545, 8634640))):
        fig, ax = plt.subplots(figsize=(18, 18))
        ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
        for c in canaletas: ax.plot(c[:, 0], c[:, 1], '-', color='#bcbd22', lw=3, alpha=0.6)
        for l, t in zip(linhas, T):
            p = np.array(t['pts_fluxo'])
            c = cor.get(l['classe'], 'k') if l['sentido'] != 'indefinido' else 'r'
            lw = {40: 0.8, 75: 1.0, 100: 1.4, 150: 2.2, 200: 2.8, 250: 3.2, 300: 3.6}.get(int(l['DN_mm'] or 100), 2)
            ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=lw)
            L = np.cumsum(np.r_[0, np.hypot(*np.diff(p, axis=0).T)]); m = L[-1] / 2
            k = max(0, np.searchsorted(L, m) - 1); u = unit(p[k + 1] - p[k]); q = p[k] + u * (m - L[k])
            if l['L_m'] > 1.5:
                ax.annotate('', xy=q + u * 0.5, xytext=q - u * 0.5, arrowprops=dict(arrowstyle='-|>', color=c, lw=1))
            if nome != 'geral' and l['classe'] == 'coletor':
                ax.text(*(q + [0.3, 0.3]), f"Ø{int(l['DN_mm'] or 0)} i={l['i_rotulo_pct']}", fontsize=6, color=c, clip_on=True)
        for c in caixas:
            ax.plot(*c['c'], 'o' if c['tipo'] == 'PVP' else 'D', ms=8 if c['tipo'] == 'PVP' else 6, mfc='w', mec='k')
            if nome != 'geral': ax.text(c['c'][0] + 0.5, c['c'][1] - 0.8, f"{c['id']}\nCT {c.get('CT')} CF {c.get('CF')}", fontsize=6, color='navy', clip_on=True)
        for p in pr2:
            ax.plot(*p['c'], '^', ms=4, color='purple' if p['grau'] else 'r')
        for q in lanc: ax.plot(*q, 'r*', ms=14)
        if lim: ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
        else: ax.set_xlim(567625, 567800); ax.set_ylim(8634540, 8634715)
        ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
        ax.set_title(f'ETIB Catu — DRE-001-DRG-R02 extraída (fase 2): azul = coletor, ciano = ramal, claro = dreno, vermelho = sentido indefinido; '
                     f'▲ prumada AP (vermelho = sem tubo), ★ lançamento, amarelo = canaleta', fontsize=9)
        fig.savefig(os.path.join(REL, f'DRE_fase2_mapa_{nome}_{DATA}.png'), dpi=100, bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    main()
