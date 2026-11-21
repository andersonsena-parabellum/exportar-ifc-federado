# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 da água fria (AF-001-HIG-R00_GEO, UTM): alimentação (hidrômetro -> reservatório/pressurizador),
AF (pressurizador -> edificações) e reúso/irrigação (torneiras de jardim, "água não potável").
A cota é premissa (o projeto não traz): fica para a fase 3.
Uso: python -I -X utf8 af_sat.py
"""
import sys, os, re, csv, json, collections, math
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import unit, dist_pt_seg
import linha_lib as ll

ARQ = ('ARQ_BASE', 'ARQ_LETRAS')
CLASSE = {'AL-Condutos': 'alimentação', 'AF-Condutos': 'AF', 'AF-Condutos Reúso': 'reúso', 'AF-Sentido conduto Reúso': 'reúso'}


def main():
    E = sc.carrega('AF')
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(ARQ)]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    # eixos: condutos + as linhas longas do layer "AF-Sentido conduto Reúso" (o projetista desenhou a rede de reúso nele;
    # as setas desse layer são polilinhas de 0,80 m)
    eixos = ll.linhas_da_rede(ob, ('AF-Condutos', 'AF-Condutos Reúso', 'AL-Condutos'), so_nivel_superior=True)
    for d in ob:
        if d['tipo'] == 'LINE' and d['layer'] == 'AF-Sentido conduto Reúso':
            p = d['pts'][:, :2]
            if np.linalg.norm(p[1] - p[0]) > 1.0:
                eixos.append({'p0': p[0].copy(), 'p1': p[1].copy(), 'd': 0.0, 'origem': 'LINE', 'layer': 'AF-Sentido conduto Reúso'})
    eixos = [e for e in eixos if np.linalg.norm(e['p1'] - e['p0']) > 0.10]   # tiquinhos de 5–8 cm são símbolos de conexão
    setas = [(d['pts'][0, :2], d['pts'][-1, :2]) for d in ob if d['tipo'] == 'PL' and 'Sentido' in d['layer'] and len(d['pts']) == 2
             and abs(np.linalg.norm(d['pts'][1, :2] - d['pts'][0, :2]) - 0.8) < 0.05]
    # nós de projeto
    nos = []
    # ligação na rede pública (círculo do layer Simbolos junto ao texto ALIMENTAÇÃO) e hidrômetro/cavalete (entre as duas pontas)
    hid = next(d for d in tx if 'HIDR' in d['texto'].upper())
    c_lig = min((d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'Simbolos'), key=lambda d: np.linalg.norm(d['pts'][0, :2] - hid['pts'][0, :2]))
    nos.append({'id': 'LIGACAO-REDE', 'tipo': 'ligação na rede pública (ALIMENTAÇÃO)', 'c': c_lig['pts'][0, :2].copy(), 'raio': 0.05, 'snap': 0.3, 'corta': False})
    al_pts = [d['pts'][:, :2] for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'AL-Conexões' and np.linalg.norm(d['pts'][0, :2] - hid['pts'][0, :2]) < 1.0]
    c_hid = np.mean([p[0] for p in al_pts], axis=0) if al_pts else hid['pts'][0, :2]
    nos.append({'id': 'HIDROMETRO', 'tipo': 'hidrômetro / cavalete 1"', 'c': c_hid, 'raio': 0.26, 'snap': 0.1, 'corta': False})
    # casa de bombas (círculo de 2,70 m da base) e os 3 reservatórios inferiores (tanques de 15 m³, círculos de 1,58 m)
    base = [d for d in E if d['path'].startswith('ARQ_BASE') and d['tipo'] == 'CIRCLE' and sc.na_obra(d['pts']).all()]
    cb = next(d for d in base if abs(d['r'] - 2.70) < 0.02)
    nos.append({'id': 'CASA-BOMBAS', 'tipo': 'casa de bombas / base do reservatório elevado (taça)', 'c': cb['pts'][0, :2].copy(), 'raio': 2.7, 'snap': 0.3, 'corta': False})
    Ein = sc.carrega('IN')
    tanques = sorted({tuple(np.round(d['pts'][0, :2], 2)) for d in Ein if d['tipo'] == 'CIRCLE' and d['path'].endswith('TANQUE PB - 15.000') and abs(d['r'] - 1.59) < 0.02})
    for i, c in enumerate(tanques):
        nos.append({'id': f'RES-INF-{i+1}', 'tipo': 'reservatório inferior 15 m³ (posição do PCI)', 'c': np.array(c), 'raio': 1.6, 'snap': 0.3, 'corta': False})
    tjs = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'AF-Peça de utilização']
    for i, d in enumerate(sorted(tjs, key=lambda d: (-d['pts'][0, 1], d['pts'][0, 0]))):
        nos.append({'id': f'TJ-{i+1:02d}', 'tipo': 'torneira de jardim 25 x 1/2" (água não potável)', 'c': d['pts'][0, :2].copy(), 'raio': 0.03, 'snap': 0.3, 'corta': False})
    # área do reservatório/pressurizador = caixa do desenho "AF-Pressurizador"
    pr = np.array([p for d in ob if d['layer'] == 'AF-Pressurizador' for p in d['pts'][:, :2]])
    lo, hi = pr.min(0), pr.max(0)
    print('pressurizador: E %.2f–%.2f  N %.2f–%.2f' % (lo[0], hi[0], lo[1], hi[1]))
    R, T, nlig = ll.monta(eixos, nos, snap_no=0.3, snap_ponta=0.05, snap_te=0.06, gap=0.3, gap_caixa=0.4)
    cx = {n['id']: n for n in nos}
    # rótulos "PVC" + "NN mm"
    for t in T: t['rot'] = []
    for m in tx:
        if not re.fullmatch(r'\d+\s*mm', m['texto'].strip()): continue
        p = m['pts'][0, :2]
        mat = next((d['texto'].strip() for d in tx if d['texto'].strip().startswith('PVC') and np.linalg.norm(d['pts'][0, :2] - p) < 0.8), '')
        b = ll.trecho_mais_proximo(p, T, rot=m['rot'], tol=1.2)
        if b: T[b[1]]['rot'].append({'dn': sc.num(m['texto']), 'mat': mat})
    # origens: hidrômetro (alimentação) e o lado do pressurizador (AF e reúso)
    g = R.grau()
    dentro_pr = lambda c: lo[0] - 0.8 < c[0] < hi[0] + 0.8 and lo[1] - 0.8 < c[1] < hi[1] + 0.8
    origem = [n['id'] for n in R.nos if n['caixa'] in ('LIGACAO-REDE', 'CASA-BOMBAS')]
    for n in R.nos:
        if g[n['id']] == 1 and n['caixa'] is None and dentro_pr(n['c']):
            origem.append(n['id'])
    # a alimentação termina nos reservatórios inferiores: não sai deles
    fim_al = {n['id'] for n in R.nos if (n['caixa'] or '').startswith('RES-INF')}
    adj = collections.defaultdict(list)
    for k, t in enumerate(T): adj[t['nos'][0]].append((t['nos'][1], k)); adj[t['nos'][1]].append((t['nos'][0], k))
    vis = set(origem); fila = list(origem); ordem = {}
    while fila:
        n = fila.pop(0)
        for m, k in adj[n]:
            if k in ordem: continue
            ordem[k] = (n, m)
            if m not in vis and m not in fim_al: vis.add(m); fila.append(m)
    linhas = []
    for k, t in enumerate(T):
        a, b = ordem.get(k, t['nos'])
        pts = t['pts'] if a == t['nos'][0] else t['pts'][::-1]
        t['pts_fluxo'] = [np.asarray(p) for p in pts]
        # sentido pela seta do projeto, quando houver, para conferir o BFS
        s_seta, _ = __import__('rede_lib').sentido_por_setas(t['pts'], setas)
        seta_ok = '' if s_seta == 0 else ('confere' if (s_seta > 0) == (a == t['nos'][0]) else 'CONTRÁRIA')
        rot = t['rot'][0] if t['rot'] else {}
        classe = sorted({CLASSE.get(l, l) for l in t['layers']})
        obs = []
        if not t['rot']: obs.append('sem rótulo próprio (Ø herdado)')
        if len({r['dn'] for r in t['rot']}) > 1: obs.append('rótulos diferentes: ' + ', '.join(f"{r['dn']:.0f}" for r in t['rot']))
        if k not in ordem: obs.append('não liga a uma origem')
        if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
        if seta_ok == 'CONTRÁRIA': obs.append('seta do projeto no sentido contrário')
        fim = ''
        if dentro_pr(pts[-1]) and k in ordem and R.nos[b]['caixa'] is None and g[b] == 1: fim = 'reservatório / pressurizador'
        if R.nos[b]['caixa']: fim = cx[R.nos[b]['caixa']]['tipo']
        linhas.append({'trecho': f'AF-{k+1:02d}', 'rede': '/'.join(classe), 'de': ll.nome_no(R, a, cx), 'para': ll.nome_no(R, b, cx),
                       'L_m': round(t['L'], 2), 'DN_mm': rot.get('dn'), 'material': rot.get('mat', ''), 'seta': seta_ok, 'chega_em': fim,
                       'E_ini': round(float(pts[0][0]), 3), 'N_ini': round(float(pts[0][1]), 3),
                       'E_fim': round(float(pts[-1][0]), 3), 'N_fim': round(float(pts[-1][1]), 3), 'obs': ' | '.join(obs),
                       '_a': a, '_b': b})
    # Ø sem rótulo: herda do trecho de montante, senão do de jusante (mesma rede)
    chega = collections.defaultdict(list); sai = collections.defaultdict(list)
    for l in linhas: sai[l['_a']].append(l); chega[l['_b']].append(l)
    for l in linhas: l['DN_adotado'] = l['DN_mm']
    for _ in range(6):
        for l in linhas:
            if l['DN_adotado'] is None:
                v = [x['DN_adotado'] for x in chega[l['_a']] if x['DN_adotado'] and x['rede'] == l['rede']] or \
                    [x['DN_adotado'] for x in sai[l['_b']] if x['DN_adotado'] and x['rede'] == l['rede']]
                if v: l['DN_adotado'] = v[0]
    cols = ['trecho', 'rede', 'de', 'para', 'L_m', 'DN_mm', 'DN_adotado', 'material', 'seta', 'chega_em', 'E_ini', 'N_ini', 'E_fim', 'N_fim', 'obs']
    with open(os.path.join(sc.REL, 'SAT_fase2_AF_trechos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows([{c: l[c] for c in cols} for l in linhas])
    with open(os.path.join(sc.REL, 'SAT_fase2_AF_nos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['no', 'tipo', 'E', 'N', 'tubos_ligados'])
        for n in nos:
            nn = next((x['id'] for x in R.nos if x['caixa'] == n['id']), None)
            w.writerow([n['id'], n['tipo'], round(float(n['c'][0]), 3), round(float(n['c'][1]), 3), g[nn] if nn is not None else 0])
        for n in R.nos:
            if n['caixa'] is None and g[n['id']] != 2:
                w.writerow([ll.nome_no(R, n['id'], cx), 'reservatório/pressurizador' if dentro_pr(n['c']) else ('ponta' if g[n['id']] == 1 else 'tê/cruzeta'),
                            round(float(n['c'][0]), 3), round(float(n['c'][1]), 3), g[n['id']]])
    json.dump({'trechos': [{**{k: v for k, v in l.items() if not k.startswith('_')}, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)],
               'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in nos],
               'pressurizador_bbox': [lo.tolist(), hi.tolist()]},
              open(os.path.join(sc.WRK, 'af_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # mapa sobre a SIT (UTM)
    S = sc.carrega('SIT'); arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and sc.na_obra(d['pts']).all() and 'PISO' not in d['layer'] and 'HATCH' not in d['layer']:
            p = d['pts'][:, :2]; arq.extend(zip(p[:-1], p[1:]))
    fig, ax = plt.subplots(figsize=(16, 16))
    ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
    cor = {'alimentação': '#08519c', 'AF': '#3182bd', 'reúso': '#31a354'}
    for l, t in zip(linhas, T):
        p = np.array(t['pts_fluxo']); c = cor.get(l['rede'], 'r'); dn = l['DN_adotado'] or 25
        ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=0.8 + dn / 25)
        m = p.mean(0) if len(p) == 2 else p[len(p) // 2]; u = unit(p[-1] - p[0])
        ax.annotate('', xy=m + u * 1.0, xytext=m - u * 1.0, arrowprops=dict(arrowstyle='-|>', color=c))
        ax.text(*(m + [0.7, 0.7]), f"{l['trecho']} Ø{l['DN_adotado']}", fontsize=6.5, color=c)
    for n in nos:
        ax.plot(*n['c'], 'o' if n['id'].startswith('TJ') else 's', ms=7, mfc='w', mec='k'); ax.text(n['c'][0] + 0.6, n['c'][1] - 1.2, n['id'], fontsize=7)
    ax.add_patch(plt.Rectangle(lo, *(hi - lo), fill=False, ec='orange', lw=1.5)); ax.text(lo[0], hi[1] + 0.8, 'reservatório / pressurizador', color='orange', fontsize=8)
    ax.set_xlim(545895, 546050); ax.set_ylim(8716090, 8716262); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    tot = collections.defaultdict(float)
    for l in linhas: tot[l['rede']] += l['L_m']
    ax.set_title('ETIB Sátiro Dias — AF-001-HIG-R00: água fria extraída (fase 2), UTM — ' + ', '.join(f'{k} {v:.0f} m' for k, v in tot.items()))
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_AF_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print(f'trechos {len(linhas)}', dict(tot), '| ligações presumidas', nlig)
    for l in linhas: print(' ', l['trecho'], l['rede'], l['de'], '->', l['para'], l['L_m'], 'Ø', l['DN_mm'], l['DN_adotado'], l['seta'], l['chega_em'], '|', l['obs'])


if __name__ == '__main__':
    main()
