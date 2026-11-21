# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 do esgoto (parte TQ do ESG-001-HIG-R00_GEO, UTM): PVs (bloco zw$B504), caixas (CI, CE...),
trechos com Ø/material/i do rótulo, sentido e CT/CF/(prof) das caixas. Tanque séptico, filtro anaeróbio e sumidouro são ETE:
fora do escopo (a rede vai até a entrada da ETE).
Uso: python -I -X utf8 esg_sat.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import Rede, ligar_pontas, unit
import gravidade_lib as gl

ARQ = ('ARQ_BASE', 'ARQ_LETRAS')
L_TUBO = ('TQ-Condutos', 'TQ-Condutos Gordura', 'TQ-Condutos Espuma')
ETE = ('TQ-Tanque séptico', 'TQ-Filtro anaeróbio', 'TQ-Sumidouro')
CORRECOES = {'PVE-01': (235.99, 234.99), 'CI-03': (235.86, 235.26)}   # caixa: (CF do desenho, CF corrigida)


def dn_desenho(d):
    for lim, dn in ((0.05, 40), (0.085, 75), (0.12, 100), (0.17, 150), (0.22, 200)):
        if d < lim: return dn
    return 250


def arq_sit():
    S = sc.carrega('SIT'); arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and sc.na_obra(d['pts']).all() and 'PISO' not in d['layer'] and 'HATCH' not in d['layer']:
            p = d['pts'][:, :2]; arq.extend(zip(p[:-1], p[1:]))
    return arq


def main():
    E = sc.carrega('ESG')
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(ARQ)]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    # ---------------- nós de projeto
    caixas = gl.pvs_por_bloco(ob, 'zw$B504', 'PVE')
    rot = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'Simbolos' and d['texto'].strip() in ('CI', 'CE', 'CES', 'CG', 'CIS', 'CP', 'CS')]
    gl.caixas_quadradas(ob, caixas, ('TQ-Caixa de alvenaria',), ('TQ-Caixa de alvenaria', 'Simbolos', 'Simbolos_int'), rot)
    # ETE: entrada do tanque séptico vira nó de destino (não é modelada)
    ete = np.array([p for d in ob if d['layer'] in ETE for p in d['pts'][:, :2]])
    if len(ete):
        lo, hi = ete.min(0), ete.max(0)
        caixas.append({'tipo': 'TS', 'c': (lo + hi) / 2, 'raio': float(max(hi - lo)) / 2 + 0.3, 'corta': False,
                       'origem': 'tanque séptico + filtro + sumidouro do vestiário (fora do escopo)'})
    gl.numerar(caixas)
    # ---------------- cotas
    # as cotas da pluvial (PVP/CA) estão no mesmo layer: as caixas da AP entram na disputa e depois saem
    iscas = gl.pvs_por_bloco(ob, 'zw$12D9', 'PVP')
    rot_ap = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] == 'Simbolos' and d['texto'].strip() in ('CA', 'CS', 'CR', 'CX', 'CAG')]
    gl.caixas_quadradas(ob, iscas, ('AP-Caixa de alvenaria',), ('AP-Caixa de alvenaria',), rot_ap)
    for i, c in enumerate(iscas): c['id'] = f'AP#{i}'
    rot_cx, sobras_rot = gl.cotas_caixas(ob, caixas + iscas, 'TQ-Textos conduto', 'TEXTOS', tipos_fundos=('PVE', 'PVP'))
    sobras_rot = [r for r in sobras_rot]
    # CF com erro de digitação no desenho (CT − CF não bate com a profundidade do próprio rótulo):
    # corrigidas por decisão do usuário em 18/10/2026; vão para o relatório como inconsistência do projeto
    for c in caixas:
        if c['id'] in CORRECOES and c.get('CF') is not None and abs(c['CF'] - CORRECOES[c['id']][0]) < 0.005:
            c['obs'] = [f"CF corrigida: desenho {CORRECOES[c['id']][0]:.2f} → {CORRECOES[c['id']][1]:.2f} (CT {c['CT']:.2f} − profundidade {c['prof']:.2f}); decisão do usuário 18/10/2026"]
            c['CF'] = CORRECOES[c['id']][1]
    # ---------------- eixos e rede
    eixos, sobras = gl.eixos_tubos(ob, L_TUBO, dmin=0.03, dmax=0.25)
    R = Rede(caixas, snap_caixa=0.75, snap_ponta=0.12, snap_te=0.30).monta(eixos)
    n_lig = ligar_pontas(R, gap=0.9, gap_caixa=1.2)
    T = [t for t in R.trechos() if t['L'] > 0.15 and t['nos'][0] != t['nos'][1]]
    for t in T: t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
    cx_por_id = {c['id']: c for c in caixas}
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and d['layer'].startswith('TQ-Sentido')]
    # rótulos dos tubos de esgoto: o projetista pôs boa parte no layer AP-Textos conduto; fica com o texto que está mais perto
    # de uma parede TQ (alinhada) do que de uma parede AP
    tq = [d['pts'][:2, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] in L_TUBO]
    ap = [d['pts'][:2, :2] for d in ob if d['tipo'] == 'LINE' and d['layer'] == 'AP-Condutos']
    def dmin(p, S, rot):
        best = 9.0
        for a, b in S:
            if np.linalg.norm(b - a) < 0.05: continue
            ang = math.degrees(math.atan2(*(b - a)[::-1])) % 180
            if abs(((rot % 180) - ang + 90) % 180 - 90) > 12: continue
            best = min(best, gl.dist_pt_seg(p, a, b)[0])
        return best
    rot_tq = [d for d in tx if d['layer'] in ('TQ-Textos conduto', 'AP-Textos conduto')
              and dmin(d['pts'][0, :2], tq, d['rot']) < min(1.5, dmin(d['pts'][0, :2], ap, d['rot']))]
    gl.rotulos_tubos(rot_tq, T)
    lanc = [d['pts'][0, :2] for d in tx if 'SEGUE PARA' in d['texto'].upper() and 'ETE' in d['texto'].upper()]
    gl.sentido(T, R, setas, cx_por_id, lanc)
    linhas = gl.tabela(T, R, cx_por_id, 'ESG', dn_padrao=dn_desenho)
    for l, t in zip(linhas, T):
        if t['presumido']: l['obs'] = (l['obs'] + ' | ' if l['obs'] else '') + 'ligação presumida (desenho não encosta, < 0,9 m)'
    gl.grau_caixas(caixas, R)
    fn_t = os.path.join(sc.REL, 'SAT_fase2_ESG_trechos.csv'); fn_n = os.path.join(sc.REL, 'SAT_fase2_ESG_caixas.csv')
    gl.salva_csv(linhas, caixas, fn_t, fn_n)
    json.dump({'caixas': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in caixas],
               'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)]},
              open(os.path.join(sc.WRK, 'esg_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---------------- mapa
    fig, ax = plt.subplots(figsize=(17, 17))
    ax.add_collection(LineCollection(arq_sit(), colors='0.82', linewidths=0.3))
    cor = {100: '#8c564b', 150: '#d62728', 75: '#9467bd', 50: '#e377c2', 40: '#e377c2'}
    for l, t in zip(linhas, T):
        p = np.array(t['pts_fluxo']); c = cor.get(int(l['DN_mm'] or 0), 'k') if l['sentido'] != 'indefinido' else 'r'
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=2.2)
        L = np.cumsum(np.r_[0, np.hypot(*np.diff(p, axis=0).T)]); m = L[-1] / 2
        k = max(0, np.searchsorted(L, m) - 1); u = unit(p[k + 1] - p[k]); q = p[k] + u * (m - L[k])
        ax.annotate('', xy=q + u * 0.8, xytext=q - u * 0.8, arrowprops=dict(arrowstyle='-|>', color=c, lw=1.4))
        ax.text(*(q + [0.4, 0.4]), f"{l['trecho']} Ø{int(l['DN_mm'] or 0)} i={l['i_rotulo_pct']}", fontsize=6, color=c)
    for c in caixas:
        ax.plot(*c['c'], 'o' if c['tipo'].startswith('PV') else 's', ms=8, mfc='w', mec='k')
        ax.text(c['c'][0] + 0.5, c['c'][1] - 1.0, f"{c['id']}\nCT {c.get('CT')} CF {c.get('CF')}", fontsize=6, color='navy')
    xs = np.array([c['c'] for c in caixas]); ax.set_xlim(xs[:, 0].min() - 8, xs[:, 0].max() + 8); ax.set_ylim(xs[:, 1].min() - 8, xs[:, 1].max() + 8)
    ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title(f'ETIB Sátiro Dias — ESG-001-HIG-R00 (TQ): esgoto extraído (fase 2) em UTM — {len(linhas)} trechos, '
                 f'{sum(l["L_m"] for l in linhas):.0f} m, {len(caixas)} caixas/PVs; vermelho = sentido indefinido')
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_ESG_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print('caixas', len(caixas), collections.Counter(c['tipo'] for c in caixas))
    print('trechos', len(linhas), f"{sum(l['L_m'] for l in linhas):.1f} m", 'por DN', collections.Counter(l['DN_mm'] for l in linhas))
    print('sentido', collections.Counter(l['sentido'] for l in linhas), '| ligações presumidas', n_lig, '| paredes sem par', len(sobras))
    print('caixas sem cota', [c['id'] for c in caixas if c.get('CF') is None and c['tipo'] != 'TS'], '| rótulos sobrando', [r['txt'] for r in sobras_rot])
    for l in linhas: print(' ', l['trecho'], l['de'], '->', l['para'], l['L_m'], 'Ø', l['DN_mm'], l['material'], 'i', l['i_rotulo_pct'], '| CF', l['CF_montante'], l['CF_jusante'], 'icalc', l['i_pelas_CF_pct'], '|', l['sentido'], '|', l['obs'])


if __name__ == '__main__':
    main()
