# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 do PCI (IN-001-ING-R03_GEO, UTM): rede de hidrantes (HI-Condutos, PEAD 2.1/2" / ø80) e
eletrodutos do SDAI (layer "0. F_PCI - Detecção e Alarme"), com caixas de passagem (*U21), hidrantes/recalque, casa de bombas e destinos.
Atenção: a base de arquitetura do PCI tem as edificações giradas 0,57° em relação ao terreno; o _GEO alinha pelas edificações.
A cota é premissa (hidrante: nota do projeto; SDAI: como a elétrica) -> fase 3.
Uso: python -I -X utf8 pci_sat.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import unit
import linha_lib as ll
from esg_sat import arq_sit

IGN = ('zw$5548', 'zw$4B94', '*U74', '*U75', '*U81', '*U82', '*U83', '*U84', '*U85')
SIS = {'HID': ('HI-Condutos (Alimentador e Sub-Ramal)',), 'SDAI': ('0. F_PCI - Detecção e Alarme',)}
CASA_BOMBAS = np.array([546033.98, 8716174.25])


def main():
    E = sc.carrega('IN')
    # fora: legenda de laço (caixa a NE, E 546033–546041 / N 8716235–8716250) e o isométrico das bombas (E > 546045)
    leg = lambda p: ((p[:, 0] > 546033) & (p[:, 0] < 546041) & (p[:, 1] > 8716235) & (p[:, 1] < 8716250)).any() or (p[:, 0] > 546045).any()
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(IGN) and not leg(d['pts'][:, :2])]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    ins = [d for d in ob if d['tipo'] == 'INSERT' and not d['path']]
    res = {}
    for sis, layers in SIS.items():
        nos = []
        if sis == 'HID':
            nos.append({'id': 'CASA-BOMBAS', 'tipo': 'casa de bombas / reservatório (taça)', 'c': CASA_BOMBAS.copy(), 'raio': 2.7, 'snap': 0.4, 'corta': False})
            for d in ins:
                if d['layer'].startswith('0. F_PCI - Hidrantes') and d['nome'].startswith('*U') and d['nome'] not in ('*U74',):
                    if np.linalg.norm(d['pts'][0, :2] - CASA_BOMBAS) < 7: continue   # símbolos dentro da casa de bombas
                    nos.append({'id': '', 'tipo': 'hidrante / recalque (símbolo)', 'c': d['pts'][0, :2].copy(), 'raio': 0.3, 'snap': 1.2, 'corta': False})
        else:
            for d in ins:
                if d['nome'] == '*U21':
                    nos.append({'id': '', 'tipo': 'caixa de passagem SDAI', 'c': d['pts'][0, :2].copy(), 'raio': 0.25, 'snap': 0.5, 'corta': False})
        k = 0
        for n in sorted(nos, key=lambda n: (-n['c'][1], n['c'][0])):
            if not n['id']: k += 1; n['id'] = f"{sis}-{'CX' if sis == 'SDAI' else 'H'}-{k:02d}"
        eixos = ll.linhas_da_rede(ob, layers, so_nivel_superior=True)
        eixos = [e for e in eixos if np.linalg.norm(e['p1'] - e['p0']) > 0.10]
        R, T, nlig = ll.monta(eixos, nos, snap_no=0.5, snap_ponta=0.05, snap_te=0.10, gap=0.6, gap_caixa=1.0)
        # rótulos
        for t in T: t['rot'] = []
        for d in tx:
            s = d['texto'].strip()
            if d['layer'] == 'HI-Textos conduto' and sis == 'HID' and (re.fullmatch(r'[\d./]+"', s) or s.startswith('ø')):
                b = ll.trecho_mais_proximo(d['pts'][0, :2], T, rot=d['rot'], tol=1.5)
                if b: T[b[1]]['rot'].append(s)
            if sis == 'SDAI' and re.fullmatch(r'L\d\d', s):
                b = ll.trecho_mais_proximo(d['pts'][0, :2], T, tol=3.0)
                if b: T[b[1]]['rot'].append(s)
        # destinos
        dest = {}; g = R.grau()
        for d in tx:
            s = d['texto'].replace('^J', ' ').strip()
            if any(k in s.upper() for k in ('SEGUE PARA', 'HIDRANTE DE RECALQUE', 'CENTRAL DE ALARME', 'VEM DOS')):
                cand = [n for n in R.nos if g[n['id']] == 1]
                if not cand: continue
                n = min(cand, key=lambda n: np.linalg.norm(np.asarray(n['c']) - d['pts'][0, :2]))
                if np.linalg.norm(np.asarray(n['c']) - d['pts'][0, :2]) < 8.0: dest.setdefault(n['id'], set()).add(s[:60])
        cx = {n['id']: n for n in nos}
        linhas = []
        for i, t in enumerate(T):
            a, b = t['nos']
            obs = []
            if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
            mat = 'PEAD' if sis == 'HID' else 'eletroduto PEAD (SDAI)'
            linhas.append({'trecho': f'{sis}-{i+1:02d}', 'sistema': sis, 'de': ll.nome_no(R, a, cx), 'para': ll.nome_no(R, b, cx), 'L_m': round(t['L'], 2),
                           'rotulo': ' '.join(sorted(set(t['rot']))), 'material': mat,
                           'destino': ' / '.join(sorted(dest.get(a, set()) | dest.get(b, set()))),
                           'E_ini': round(float(t['pts'][0][0]), 3), 'N_ini': round(float(t['pts'][0][1]), 3),
                           'E_fim': round(float(t['pts'][-1][0]), 3), 'N_fim': round(float(t['pts'][-1][1]), 3), 'obs': ' | '.join(obs)})
        res[sis] = {'nos': nos, 'R': R, 'T': T, 'linhas': linhas, 'nlig': nlig}
    linhas = res['HID']['linhas'] + res['SDAI']['linhas']
    with open(os.path.join(sc.REL, 'SAT_fase2_PCI_trechos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=';'); w.writeheader(); w.writerows(linhas)
    with open(os.path.join(sc.REL, 'SAT_fase2_PCI_nos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['no', 'tipo', 'E', 'N', 'ligacoes'])
        for sis, r in res.items():
            g = r['R'].grau()
            for n in r['nos']:
                nn = next((x['id'] for x in r['R'].nos if x['caixa'] == n['id']), None)
                w.writerow([n['id'], n['tipo'], round(float(n['c'][0]), 3), round(float(n['c'][1]), 3), g[nn] if nn is not None else 0])
    json.dump({sis: {'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in r['nos']],
                     'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts']]} for l, t in zip(r['linhas'], r['T'])]} for sis, r in res.items()},
              open(os.path.join(sc.WRK, 'pci_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    fig, ax = plt.subplots(figsize=(15, 15))
    ax.add_collection(LineCollection(arq_sit(), colors='0.84', linewidths=0.3))
    cor = {'HID': '#d62728', 'SDAI': '#ff7f0e'}
    for sis, r in res.items():
        for l, t in zip(r['linhas'], r['T']):
            p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-' if sis == 'HID' else '--', color=cor[sis], lw=2 if sis == 'HID' else 1.4)
            m = p[len(p) // 2]; ax.text(m[0] + 0.4, m[1] + 0.4, f"{l['trecho']} {l['rotulo']}", fontsize=6.5, color=cor[sis])
        for n in r['nos']:
            ax.plot(*n['c'], 's' if sis == 'SDAI' else 'o', ms=6, mfc='w', mec=cor[sis]); ax.text(n['c'][0] + 0.5, n['c'][1] - 1.0, n['id'], fontsize=6)
        ax.plot([], [], '-' if sis == 'HID' else '--', color=cor[sis], label=f"{sis}: {len(r['linhas'])} trechos, {sum(l['L_m'] for l in r['linhas']):.0f} m")
    ax.legend(loc='upper left')
    ax.set_xlim(545930, 546050); ax.set_ylim(8716115, 8716272); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title('ETIB Sátiro Dias — PCI (IN-001-ING-R03) extraído (fase 2): hidrantes (vermelho) e eletrodutos do SDAI (laranja tracejado), UTM')
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_PCI_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    for sis, r in res.items():
        print(sis, 'trechos', len(r['linhas']), f"{sum(l['L_m'] for l in r['linhas']):.1f} m", '| nós', len(r['nos']), '| ligações presumidas', r['nlig'])
        for l in r['linhas']: print('  ', l['trecho'], l['de'], '->', l['para'], l['L_m'], l['rotulo'], '|', l['destino'], '|', l['obs'])


if __name__ == '__main__':
    main()
