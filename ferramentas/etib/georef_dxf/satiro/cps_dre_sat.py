# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 da drenagem do campo society (CPS-PE-DRE-001-DRG-R01_GEO, UTM, posicionado pelo centro do campo,
precisão ~0,75 m): drenos PVC-DR 100 mm em espinha de peixe, coletores PVCR 150 mm, CAs nas saídas "INTERLIGAR A REDE EXTERNA"
e canaletas semicirculares com grelha. Não há cotas de caixa no desenho (só i=1 %).
Uso: python -I -X utf8 cps_dre_sat.py
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
from ap_sat import limpa_eixos, dn_desenho
from esg_sat import arq_sit

BASE = ('zw$6316',)


def main():
    E = sc.carrega('CPS_DRE')
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(BASE)]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    caixas = []
    rot = [d for d in tx if d['layer'] == 'Simbolos' and d['texto'].strip() in ('CA', 'CAG', 'CS')]
    gl.caixas_quadradas(ob, caixas, ('AP-Caixa de alvenaria',), ('AP-Caixa de alvenaria', 'Simbolos', 'Simbolos_int'), rot)
    # o mesmo símbolo de caixa aparece duas vezes num canto: deduplica por centro
    cx2 = []
    for c in caixas:
        if all(np.linalg.norm(c['c'] - x['c']) > 0.3 for x in cx2): cx2.append(c)
    caixas = gl.numerar(cx2, prefixo='CPS-')
    lanc_txt = [d for d in tx if 'INTERLIGAR' in d['texto'].upper()]
    lanc = [d['pts'][0, :2] for d in lanc_txt]
    eixos, sobras = gl.eixos_tubos(ob, ('AP-Condutos',), dmin=0.02, dmax=0.45)
    eixos, n_tiq = limpa_eixos(eixos, caixas)
    canaletas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] in ('AP-Condutos', '0', 'Nível 1') and d['path'] and np.hypot(*np.diff(d['pts'][:, :2], axis=0).T).sum() > 5]
    R = Rede(caixas, snap_caixa=0.75, snap_ponta=0.10, snap_te=0.25).monta(eixos)
    n_lig = ligar_pontas(R, gap=0.9, gap_caixa=1.2)
    T = [t for t in R.trechos() if t['L'] > 0.15 and t['nos'][0] != t['nos'][1]]
    for t in T: t['presumido'] = any(R.arestas[m]['origem'].startswith('ligação') for m in t['arestas'])
    cx_por_id = {c['id']: c for c in caixas}
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and d['layer'] == 'AP-Sentido conduto']
    gl.rotulos_tubos([d for d in tx if d['layer'] == 'AP-Textos conduto'], T, mats=('PVC', 'PVCR', 'PVC-V', 'PVC-DR'))
    gl.sentido(T, R, setas, cx_por_id, lanc)
    for t in T:
        mat = t['rot'][0]['mat'] if t['rot'] else ''
        t['classe'] = 'dreno (PVC-DR)' if mat == 'PVC-DR' else 'coletor'
    linhas = gl.tabela(T, R, cx_por_id, 'CPS-DRE', dn_padrao=dn_desenho)
    for l, t in zip(linhas, T):
        if t['presumido']: l['obs'] = (l['obs'] + ' | ' if l['obs'] else '') + 'ligação presumida (desenho não encosta, < 0,9 m)'
        l['obs'] = (l['obs'] + ' | ' if l['obs'] else '') + 'posição aproximada (campo posicionado pelo centro, ~0,75 m)'
    gl.grau_caixas(caixas, R)
    gl.salva_csv(linhas, caixas, os.path.join(sc.REL, 'SAT_fase2_CPS-DRE_trechos.csv'), os.path.join(sc.REL, 'SAT_fase2_CPS-DRE_caixas.csv'))
    json.dump({'caixas': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in caixas],
               'canaletas': [c.tolist() for c in canaletas], 'lancamentos': [q.tolist() for q in lanc],
               'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)]},
              open(os.path.join(sc.WRK, 'cps_dre_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # mapa: rede do CPS sobre a SIT e sobre a drenagem do campo que já existe no ESG-001 (AP)
    ap = json.load(open(os.path.join(sc.WRK, 'ap_rede.json'), encoding='utf-8'))
    fig, ax = plt.subplots(figsize=(15, 15))
    ax.add_collection(LineCollection(arq_sit(), colors='0.82', linewidths=0.3))
    for t in ap['trechos']:
        p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color='#ff9896', lw=1.2, alpha=0.8)
    for c in canaletas: ax.plot(c[:, 0], c[:, 1], '-', color='#bcbd22', lw=3, alpha=0.6)
    cor = {'coletor': '#1f77b4', 'dreno (PVC-DR)': '#2ca02c'}
    for l, t in zip(linhas, T):
        p = np.array(t['pts_fluxo']); c = cor.get(l['classe'], 'k') if l['sentido'] != 'indefinido' else 'r'
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=2.0)
        L = np.cumsum(np.r_[0, np.hypot(*np.diff(p, axis=0).T)]); m = L[-1] / 2
        k = max(0, np.searchsorted(L, m) - 1); u = unit(p[k + 1] - p[k]); q = p[k] + u * (m - L[k])
        ax.annotate('', xy=q + u * 0.6, xytext=q - u * 0.6, arrowprops=dict(arrowstyle='-|>', color=c, lw=1))
        ax.text(*(q + [0.3, 0.3]), f"Ø{int(l['DN_mm'] or 0)}", fontsize=6, color=c)
    for c in caixas: ax.plot(*c['c'], 'D', ms=7, mfc='w', mec='k'); ax.text(c['c'][0] + 0.5, c['c'][1] - 0.8, c['id'], fontsize=7)
    for q in lanc: ax.plot(*q, 'r*', ms=12)
    ax.set_xlim(545855, 545955); ax.set_ylim(8716115, 8716215); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title('ETIB Sátiro Dias — drenagem do campo society (CPS-DRE-001 R01) extraída: azul = coletor PVCR, verde = dreno PVC-DR, amarelo = canaleta;\n'
                 'rosa = pluvial do ESG-001 (AP), já sem a espinha do campo (retirada: vale este CPS DRE-001, decisão de 18/10/2026)', fontsize=10)
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_CPS-DRE_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print('caixas', len(caixas), '| trechos', len(linhas), f"{sum(l['L_m'] for l in linhas):.1f} m", collections.Counter(l['classe'] for l in linhas))
    print('por DN', collections.Counter(l['DN_mm'] for l in linhas), '| sentido', collections.Counter(l['sentido'] for l in linhas))
    print('tiques', n_tiq, '| ligações presumidas', n_lig, '| canaletas', len(canaletas), [round(float(np.hypot(*np.diff(c, axis=0).T).sum()), 1) for c in canaletas])


if __name__ == '__main__':
    main()
