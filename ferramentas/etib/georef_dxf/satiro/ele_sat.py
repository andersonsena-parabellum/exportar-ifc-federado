# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 da elétrica enterrada (eletrodutos de piso) das pranchas EL-001 (iluminação externa),
EL-002 (alimentação) e do campo society (CPS ELE-001/002), todas em UTM.
Nós: caixas de passagem (bloco ou quadrado do layer de caixa/condulete), postes, quadros (pelo texto). Rótulos: Ø do eletroduto
("%%C 1"") e circuitos/quadros do layer de fiação. A cota é premissa (NBR 5410: 0,70 m; 1,00 m sob veículos) -> fase 3.
Uso: python -I -X utf8 ele_sat.py
"""
import sys, os, re, math, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import unit, dist_pt_seg
import linha_lib as ll
from esg_sat import arq_sit

FOLHAS = {   # tag: (nome, prefixo do trecho, caminho da base de arquitetura a ignorar)
    'EL1': ('EL-001 iluminação externa', 'IE', ('zw$46AE', 'zw$6305')),
    'EL2': ('EL-002 alimentação', 'AL', ('zw$46AE',)),
    'CPS_EL1': ('CPS ELE-001 campo 380/220 V', 'CP1', ('YHTY7T',)),
    'CPS_EL2': ('CPS ELE-002 campo 220/127 V', 'CP2', ('YHTY7T',)),
}
L_DUTO = ('02. F_ELETRODUTO PISO', '02. F_ELETRODUTO', 'ELETRODUTO 3 4', 'E-eletrodutopiso')
L_CAIXA = ('0. F_CAIXA-CONDULETE', '0. F_SIMBOL', 'P')
RX_DIAM = re.compile(r'^(%%C|Ø|ø)\s*([\d./ ]+)"?$')
RX_CIRC = re.compile(r'^(IE-\d+|Q[DG][A-Z0-9.\-]*|QDLT[-A-Z.]*|GD-[A-Z.]+|#\d+)$')


def quadrados(ob, layers, lado=(0.15, 1.2)):
    """Centros de quadrados (PL fechada de 4 lados ou laço de 4 LINEs) nos layers dados."""
    out = []
    for d in ob:
        if d['tipo'] == 'PL' and d['layer'] in layers and len(d['pts']) >= 4 and not d['path']:
            P = d['pts'][:, :2]
            if len(P) == 5 or d.get('fechada'):
                P = P[:4]
                s = np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T)
                if lado[0] < s.mean() < lado[1] and s.std() < 0.05 * s.mean():
                    out.append((P.mean(0), float(s.mean())))
    # só entidades soltas (caixas em bloco já vêm pelo INSERT); pontas indexadas numa grade de 1 cm
    segs = [d['pts'][:2, :2] for d in ob if d['tipo'] == 'LINE' and not d['path'] and d['layer'] in layers and lado[0] < np.linalg.norm(d['pts'][1, :2] - d['pts'][0, :2]) < lado[1]]
    usado = set()
    for i, s in enumerate(segs):
        if i in usado: continue
        grupo = [i]; pts = [s[0], s[1]]
        for _ in range(4):
            for j, t in enumerate(segs):
                if j in grupo: continue
                if min(np.linalg.norm(a - b) for a in (t[0], t[1]) for b in pts) < 0.01:
                    grupo.append(j); pts += [t[0], t[1]]
        if len(grupo) == 4:
            usado.update(grupo)
            L = np.mean([np.linalg.norm(segs[k][1] - segs[k][0]) for k in grupo])
            out.append((np.mean(pts, axis=0), float(L)))
    res = []
    for c, l in out:
        if all(np.linalg.norm(c - r[0]) > 0.3 for r in res): res.append((c, l))
    return res


def folha(tag):
    nome, pref, base = FOLHAS[tag]
    E = sc.carrega(tag)
    ob = [d for d in E if sc.na_obra(d['pts']).all() and not d['path'].startswith(base)]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    # ---------------- nós
    nos = []
    for d in ob:
        if d['tipo'] == 'INSERT' and not d['path'] and 'CAIXA' in d['nome'].upper():
            nos.append({'tipo': 'CX', 'c': d['pts'][0, :2].copy(), 'raio': 0.3, 'snap': 0.5, 'corta': False})
    for c, l in quadrados(ob, L_CAIXA):
        if all(np.linalg.norm(c - n['c']) > 0.4 for n in nos):
            nos.append({'tipo': 'CX', 'c': c, 'raio': l / 2, 'snap': 0.5, 'corta': False})
    rot_cx = [d for d in tx if re.match(r'Cx\.?\s*\d+\s*x\s*\d+', d['texto'].strip(), re.I)]
    for n in nos:
        t = min(rot_cx, key=lambda d: np.linalg.norm(d['pts'][0, :2] - n['c']), default=None)
        if t is not None and np.linalg.norm(t['pts'][0, :2] - n['c']) < 3.5:
            n['tipo'] = 'CX ' + re.sub(r'\s+', '', re.match(r'Cx\.?\s*(\d+\s*x\s*\d+)', t['texto'].strip(), re.I).group(1))
    for d in ob:
        if d['tipo'] == 'INSERT' and not d['path'] and 'POSTE' in d['nome'].upper():
            nos.append({'tipo': 'POSTE', 'c': d['pts'][0, :2].copy(), 'raio': 0.2, 'snap': 0.6, 'corta': False})
    # campo society: o poste é o grupo de refletores (blocos do layer EL-LUMINARIAS a < 1,5 m uns dos outros)
    refl = [d['pts'][0, :2] for d in ob if d['tipo'] == 'INSERT' and not d['path'] and d['layer'] == 'EL-LUMINARIAS']
    grupos = []
    for q in refl:
        for g in grupos:
            if np.linalg.norm(np.mean(g, axis=0) - q) < 1.5: g.append(q); break
        else: grupos.append([q])
    for g in grupos:
        nos.append({'tipo': 'POSTE', 'c': np.mean(g, axis=0), 'raio': 0.2, 'snap': 0.6, 'corta': False, 'refletores': len(g)})
    nos.sort(key=lambda n: (-n['c'][1], n['c'][0]))
    cont = collections.Counter()
    for n in nos:
        k = 'POSTE' if n['tipo'] == 'POSTE' else 'CX'
        cont[k] += 1; n['id'] = f"{pref}-{k}-{cont[k]:02d}"
    # ---------------- eixos e rede
    eixos = ll.linhas_da_rede(ob, L_DUTO, so_nivel_superior=True)
    eixos = [e for e in eixos if np.linalg.norm(e['p1'] - e['p0']) > 0.10]
    R, T, nlig = ll.monta(eixos, nos, snap_no=0.5, snap_ponta=0.05, snap_te=0.10, gap=0.40, gap_caixa=0.8)
    cx = {n['id']: n for n in nos}
    # ---------------- rótulos: Ø e circuitos (texto mais próximo do trecho, com a mesma direção quando é rótulo girado)
    for t in T: t['diam'] = []; t['circ'] = []
    # rótulos da fiação: Ø, quadros/circuitos e bitolas ficam em FILEIRAS ao lado do eletroduto (até ~10 m dele);
    # agrupa em fileiras (mesma linha de texto, encadeadas a < 4,5 m) e dá a fileira inteira ao trecho mais próximo da fileira
    rot = []
    for d in tx:
        s_ = d['texto'].strip().replace('\P', ' ')
        if RX_DIAM.match(s_) or (RX_CIRC.match(s_) and d['layer'] in ('01. F_FIAÇÃO-INDICAÇÃO', 'C-TEXTO', 'TEXTO', 'EL-CHAMADAS')):
            rot.append({'p': d['pts'][0, :2], 'rot': d['rot'], 's': s_})
    grupo = list(range(len(rot)))
    def raiz(i):
        while grupo[i] != i: grupo[i] = grupo[grupo[i]]; i = grupo[i]
        return i
    for i, a in enumerate(rot):
        ua = np.array([math.cos(math.radians(a['rot'])), math.sin(math.radians(a['rot']))])
        for j in range(i + 1, len(rot)):
            v = rot[j]['p'] - a['p']
            if abs(v @ ua) < 4.5 and abs(v @ np.array([-ua[1], ua[0]])) < 0.9: grupo[raiz(i)] = raiz(j)
    fil = collections.defaultdict(list)
    for i in range(len(rot)): fil[raiz(i)].append(rot[i])
    for itens in fil.values():
        best = None
        for it in itens:
            b = ll.trecho_mais_proximo(it['p'], T, tol=12.0)
            if b and (best is None or b[0] < best[0]): best = b
        if best is None: continue
        for it in itens:
            m = RX_DIAM.match(it['s'])
            if m: T[best[1]]['diam'].append(m.group(2).strip() + '"')
            elif not it['s'].startswith('#'): T[best[1]]['circ'].append(it['s'])
    destinos = {}
    gr = R.grau()
    for d in tx:
        s = d['texto'].strip()
        if re.match(r'^(Q[DG][A-Z0-9.\-]*|QDLT[-A-Z.]*)$', s) or 'SEGUE PARA' in s.upper():
            cand = [n for n in R.nos if gr[n['id']] == 1]
            if not cand: continue
            n = min(cand, key=lambda n: np.linalg.norm(np.asarray(n['c']) - d['pts'][0, :2]))
            if np.linalg.norm(np.asarray(n['c']) - d['pts'][0, :2]) < 4.0:
                destinos.setdefault(n['id'], set()).add(s)
    for n in nos:
        b = ll.trecho_mais_proximo(n['c'], T, tol=3.0)
        n['trecho_proximo'] = b[1] if b else None; n['dist_eletroduto'] = round(b[0], 2) if b else None
    linhas = []
    for k, t in enumerate(T):
        a, b = t['nos']
        obs = []
        if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
        if not t['diam']: obs.append('sem Ø no desenho')
        pts = t['pts']
        linhas.append({'trecho': f'{pref}-{k+1:03d}', 'folha': nome, 'de': ll.nome_no(R, a, cx), 'para': ll.nome_no(R, b, cx), 'L_m': round(t['L'], 2),
                       'diametro': '/'.join(sorted(set(t['diam']))), 'circuitos': ' '.join(sorted(set(t['circ']))),
                       'destino': ' / '.join(sorted(destinos.get(a, set()) | destinos.get(b, set()))),
                       'E_ini': round(float(pts[0][0]), 3), 'N_ini': round(float(pts[0][1]), 3),
                       'E_fim': round(float(pts[-1][0]), 3), 'N_fim': round(float(pts[-1][1]), 3), 'obs': ' | '.join(obs)})
    return {'tag': tag, 'nome': nome, 'nos': nos, 'R': R, 'T': T, 'linhas': linhas, 'nlig': nlig}


def main():
    res = [folha(tag) for tag in FOLHAS]
    linhas = [l for r in res for l in r['linhas']]
    cols = list(linhas[0].keys())
    with open(os.path.join(sc.REL, 'SAT_fase2_ELE_trechos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows(linhas)
    with open(os.path.join(sc.REL, 'SAT_fase2_ELE_nos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['no', 'folha', 'tipo', 'E', 'N', 'eletrodutos_ligados', 'trecho_mais_proximo', 'distancia_m'])
        for r in res:
            g = r['R'].grau()
            for n in r['nos']:
                nn = next((x['id'] for x in r['R'].nos if x['caixa'] == n['id']), None)
                tp = r['linhas'][n['trecho_proximo']]['trecho'] if n.get('trecho_proximo') is not None else ''
                w.writerow([n['id'], r['nome'], n['tipo'], round(float(n['c'][0]), 3), round(float(n['c'][1]), 3), g[nn] if nn is not None else 0, tp, n.get('dist_eletroduto')])
    json.dump({r['tag']: {'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in r['nos']],
                          'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts']]} for l, t in zip(r['linhas'], r['T'])]} for r in res},
              open(os.path.join(sc.WRK, 'ele_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    fig, ax = plt.subplots(figsize=(17, 17))
    ax.add_collection(LineCollection(arq_sit(), colors='0.84', linewidths=0.3))
    cor = {'EL1': '#2ca02c', 'EL2': '#d62728', 'CPS_EL1': '#9467bd', 'CPS_EL2': '#ff7f0e'}
    for r in res:
        for l, t in zip(r['linhas'], r['T']):
            p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color=cor[r['tag']], lw=1.6 if r['tag'] == 'EL2' else 1.1, alpha=0.9)
        for n in r['nos']:
            ax.plot(*n['c'], 'o' if n['tipo'] == 'POSTE' else 's', ms=4 if n['tipo'] == 'POSTE' else 5, mfc='w', mec=cor[r['tag']])
    for r in res: ax.plot([], [], '-', color=cor[r['tag']], label=f"{r['nome']}: {len(r['linhas'])} trechos, {sum(l['L_m'] for l in r['linhas']):.0f} m, "
                                                                    f"{sum(1 for n in r['nos'] if n['tipo'] != 'POSTE')} caixas, {sum(1 for n in r['nos'] if n['tipo'] == 'POSTE')} postes")
    ax.legend(loc='upper left', fontsize=9)
    ax.set_xlim(545850, 546060); ax.set_ylim(8716085, 8716275); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title('ETIB Sátiro Dias — eletrodutos enterrados extraídos (fase 2), UTM; □ caixa de passagem, ○ poste')
    fig.savefig(os.path.join(sc.REL, 'SAT_fase2_ELE_mapa.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    for r in res:
        print(r['nome'], '| trechos', len(r['linhas']), f"{sum(l['L_m'] for l in r['linhas']):.1f} m", '| nós', collections.Counter(n['tipo'] for n in r['nos']),
              '| sem Ø', sum(1 for l in r['linhas'] if not l['diametro']), '| ligações presumidas', r['nlig'])
        g = r['R'].grau()
        print('   caixas/postes a mais de 2 m de um eletroduto:', [(n['id'], n['dist_eletroduto']) for n in r['nos'] if n['dist_eletroduto'] is None or n['dist_eletroduto'] > 2.0])


if __name__ == '__main__':
    main()
