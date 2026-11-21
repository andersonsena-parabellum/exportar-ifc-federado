# -*- coding: utf-8 -*-
"""ETIB Catu — fase 2 do incêndio (INC-001-ING-R03_GEO, UTM): rede de hidrantes (PEAD, layer "0. F_PCI - Hidrantes e
Sprinklers", linhas de nível superior) e SDAI (eletrodutos do layer "0. F_PCI - Detecção e Alarme", caixas *U69/*U251,
laços L01–L07 pelo atributo LAÇO). A legenda de laços (tabela no canto noroeste) fica de fora.
Uso: python -I -X utf8 inc_catu.py
"""
import sys, os, re, csv, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from catu_comum import carrega, na_obra, num, REL, WRK
from rede_lib import unit, dist_pt_seg
import linha_lib as ll

DATA = '2026-10-18'
ARQ = ('zw$7D57', 'zw$44A6', 'zw$4B94')
LEGENDA = (567674.0, 8634681.0, 567706.5, 8634711.0)       # tabela de laços desenhada dentro do lote


def fora_legenda(p):
    p = np.atleast_2d(p)
    return ~((p[:, 0] > LEGENDA[0]) & (p[:, 0] < LEGENDA[2]) & (p[:, 1] > LEGENDA[1]) & (p[:, 1] < LEGENDA[3]))


def salva(nome, linhas, cols):
    with open(os.path.join(REL, f'{nome}_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows([{c: l.get(c, '') for c in cols} for l in linhas])


def main():
    E = carrega('INC')
    ob = [d for d in E if not d['path'].startswith(ARQ) and not d['layer'].upper().startswith('ARQ') and na_obra(d['pts']).all()
          and fora_legenda(d['pts']).all()]
    tx = [d for d in ob if d['tipo'] == 'TEXT']

    # ======================= HIDRANTES
    # o hidrante é o símbolo do layer de hidrantes dentro do bloco *U34/*U41 (o ponto de inserção do bloco fica no abrigo, 2-3 m ao lado)
    hid = []
    por_raiz = collections.defaultdict(list)
    for d in ob:
        if d['path'].split('|')[0] in ('*U34', '*U41') and d['layer'] == '0. F_PCI - Hidrantes e Sprinklers' and d['tipo'] != 'INSERT':
            por_raiz[d['raiz']].append(d['pts'][:, :2])
    for d in ob:
        if d['tipo'] == 'INSERT' and d['path'] == '' and d['layer'] == '0. F_PCI - Parede TRRF' and d['nome'] in ('*U34', '*U41'):
            P = np.vstack(por_raiz.get(d['raiz'], [d['pts'][:, :2]]))
            c = np.median(P, axis=0)
            if all(np.linalg.norm(c - h['c']) > 0.3 for h in hid):
                hid.append({'tipo': 'HID', 'c': c, 'raio': 0.3, 'snap': 1.2, 'corta': False, 'abrigo': d['pts'][0, :2].copy()})
    for i, h in enumerate(sorted(hid, key=lambda h: (-h['c'][1], h['c'][0]))): h['id'] = f'H-{i+1:02d}'
    rec = [d for d in ob if d['tipo'] == 'INSERT' and d['nome'] == '*U17']
    especiais = [{'tipo': 'RECALQUE', 'id': 'RECALQUE', 'c': r['pts'][0, :2].copy(), 'raio': 0.2, 'snap': 1.0, 'corta': False} for r in rec[:1]]
    trrf = [d['pts'][:, :2] for d in ob if d['layer'] == '0. F_PCI - Parede TRRF' and d['tipo'] in ('LINE', 'PL') and d['path'] == '']
    if trrf:
        P = np.vstack(trrf); cb = P.mean(0)
        especiais.append({'tipo': 'CASA DE BOMBAS', 'id': 'CB', 'c': cb, 'raio': float(np.ptp(P, axis=0).max() / 2), 'snap': 0.8, 'corta': False,
                          'contorno': [p.tolist() for p in trrf]})
    nos_h = hid + especiais
    eix = ll.linhas_da_rede(ob, ('0. F_PCI - Hidrantes e Sprinklers',), so_nivel_superior=True)
    eix = [e for e in eix if np.linalg.norm(e['p1'] - e['p0']) > 0.03]
    # eletroduto do SDAI desenhado no layer de hidrantes: linha com as duas pontas em caixas de passagem *U69/*U251
    cpos = np.array([d['pts'][0, :2] for d in ob if d['tipo'] == 'INSERT' and d['path'] == '' and d['nome'] in ('*U69', '*U251')])
    def em_caixa(q): return np.min(np.hypot(*(cpos - q).T)) < 0.25
    global SDAI_INCLUIR
    SDAI_INCLUIR = [e for e in eix if em_caixa(e['p0']) and em_caixa(e['p1'])]
    eix = [e for e in eix if not (em_caixa(e['p0']) and em_caixa(e['p1']))]
    # trechos de hidrante desenhados no layer do SDAI: linhas com as DUAS pontas em conexões PEAD (blocos do layer 0, escala 45,5/34,1)
    fit = np.array([d['pts'][0, :2] for d in ob if d['tipo'] == 'INSERT' and d['path'] == '' and d['layer'] == '0' and (abs(d['s'] - 45.5) < 1 or abs(d['s'] - 34.12) < 1)])
    def em_conexao(q): return len(fit) and np.min(np.hypot(*(fit - q).T)) < 0.12
    trocados = []
    for e in ll.linhas_da_rede(ob, ('0. F_PCI - Detecção e Alarme',), so_nivel_superior=True):
        if em_conexao(e['p0']) and em_conexao(e['p1']):
            e['origem'] = 'linha no layer do SDAI'; eix.append(e); trocados.append(e)
    global SDAI_EXCLUIR
    SDAI_EXCLUIR = trocados
    Rh, Th, nl_h = ll.monta(eix, nos_h, snap_no=1.0, snap_ponta=0.06, snap_te=0.06, gap=0.6, gap_caixa=1.5)
    cxh = {n['id']: n for n in nos_h}
    rot_h = [d for d in tx if d['layer'] == 'HI-Textos conduto' and re.fullmatch(r'[\d./]+"', d['texto'].strip())]
    for t in Th: t['rot'] = []
    for r in rot_h:
        b = ll.trecho_mais_proximo(r['pts'][0, :2], Th, rot=r['rot'], tol=1.5)
        if b: Th[b[1]]['rot'].append(r['texto'].strip())
    # sentido: da casa de bombas para os hidrantes (BFS)
    origem = [n['id'] for n in Rh.nos if n['caixa'] == 'CB']
    ordem = bfs(Th, origem)
    lin_h = []
    for k, t in enumerate(Th):
        a, b = ordem.get(k, t['nos']); pts = t['pts'] if a == t['nos'][0] else t['pts'][::-1]; t['pts_fluxo'] = [np.asarray(p) for p in pts]
        obs = []
        if k not in ordem: obs.append('não liga à casa de bombas')
        if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
        if not t['rot']: obs.append('sem rótulo (Ø do projeto: PEAD 2.1/2" em toda a rede)')
        if any(Rh.arestas[m]['origem'] == 'linha no layer do SDAI' for m in t['arestas']): obs.append('desenhado no layer do SDAI (0. F_PCI - Detecção e Alarme), com conexões PEAD nas pontas')
        lin_h.append({'trecho': f'HID-{k+1:02d}', 'de': ll.nome_no(Rh, a, cxh), 'para': ll.nome_no(Rh, b, cxh), 'L_m': round(t['L'], 2),
                      'rotulo': (t['rot'][0] if t['rot'] else ''), 'material': 'PEAD', 'DN': '2.1/2"',
                      'E_ini': round(float(pts[0][0]), 3), 'N_ini': round(float(pts[0][1]), 3), 'E_fim': round(float(pts[-1][0]), 3), 'N_fim': round(float(pts[-1][1]), 3),
                      'obs': ' | '.join(obs)})
    salva('INC_fase2_hidrantes_trechos', lin_h, list(lin_h[0].keys()))
    gh = Rh.grau()
    nos_csv = []
    for n in nos_h:
        nn = next((x['id'] for x in Rh.nos if x['caixa'] == n['id']), None)
        nos_csv.append({'no': n['id'], 'tipo': {'HID': 'hidrante (abrigo tipo 02)', 'RECALQUE': 'hidrante de recalque', 'CB': 'casa de bombas'}.get(n['tipo'], n['tipo']),
                        'E': round(float(n['c'][0]), 3), 'N': round(float(n['c'][1]), 3), 'tubos_ligados': gh[nn] if nn is not None else 0,
                        'obs': '' if (nn is not None and gh[nn]) else dist_obs(n['c'], Th)})
    salva('INC_fase2_hidrantes_nos', nos_csv, ['no', 'tipo', 'E', 'N', 'tubos_ligados', 'obs'])

    # ======================= SDAI
    cxs = []
    for d in ob:
        if d['tipo'] == 'INSERT' and d['path'] == '' and d['nome'] in ('*U69', '*U251'):
            if all(np.linalg.norm(d['pts'][0, :2] - c['c']) > 0.2 for c in cxs):
                cxs.append({'tipo': 'CX', 'c': d['pts'][0, :2].copy(), 'raio': 0.15, 'snap': 0.5, 'corta': True, 'bloco': d['nome']})
    for i, c in enumerate(sorted(cxs, key=lambda c: (-c['c'][1], c['c'][0]))): c['id'] = f'CX-{i+1:02d}'
    bat = [d['pts'][:, :2] for d in ob if d['path'].split('|')[0] == 'bat' and d['tipo'] != 'INSERT']   # ponto base do bloco fica longe: usa a geometria
    if bat:
        cc = np.vstack(bat).mean(0)
        perto = [c for c in cxs if np.linalg.norm(c['c'] - cc) < 0.8]
        if perto:   # a central fica colada a uma caixa de passagem: a caixa vira o nó da central
            perto[0]['tipo'] = 'CENTRAL'; perto[0]['id'] = 'CENTRAL'
        else:
            cxs.append({'tipo': 'CENTRAL', 'id': 'CENTRAL', 'c': cc, 'raio': 0.3, 'snap': 1.0, 'corta': False})
    eix = ll.linhas_da_rede(ob, ('0. F_PCI - Detecção e Alarme',), so_nivel_superior=True)
    eix = [e for e in eix if not any(np.allclose(e['p0'], x['p0']) and np.allclose(e['p1'], x['p1']) for x in SDAI_EXCLUIR)]
    for e in SDAI_INCLUIR: eix.append({**e, 'origem': 'linha no layer de hidrantes'})
    Rs, Ts, nl_s = ll.monta(eix, cxs, snap_no=0.5, snap_ponta=0.06, snap_te=0.06, gap=0.4, gap_caixa=0.8)
    cxd = {c['id']: c for c in cxs}
    lacos = [d for d in tx if d.get('tag') == 'LAÇO' or re.fullmatch(r'L0\d', d['texto'].strip())]
    for t in Ts: t['lacos'] = set()
    for l in lacos:
        b = ll.trecho_mais_proximo(l['pts'][0, :2], Ts, tol=2.5)
        if b: Ts[b[1]]['lacos'].add(l['texto'].strip())
    origem = [n['id'] for n in Rs.nos if n['caixa'] == 'CENTRAL']
    ordem = bfs(Ts, origem)
    lin_s = []
    for k, t in enumerate(Ts):
        a, b = ordem.get(k, t['nos']); pts = t['pts'] if a == t['nos'][0] else t['pts'][::-1]; t['pts_fluxo'] = [np.asarray(p) for p in pts]
        obs = []
        if k not in ordem: obs.append('não liga à central (o trecho de ligação pode estar no mesmo caminho da rede de hidrantes, sem desenho próprio)')
        if any(Rs.arestas[m]['origem'] == 'linha no layer de hidrantes' for m in t['arestas']): obs.append('desenhado no layer de hidrantes, entre duas caixas do SDAI')
        if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
        lin_s.append({'trecho': f'SDAI-{k+1:02d}', 'de': ll.nome_no(Rs, a, cxd), 'para': ll.nome_no(Rs, b, cxd), 'L_m': round(t['L'], 2),
                      'lacos_rotulo': ', '.join(sorted(t['lacos'])),
                      'E_ini': round(float(pts[0][0]), 3), 'N_ini': round(float(pts[0][1]), 3), 'E_fim': round(float(pts[-1][0]), 3), 'N_fim': round(float(pts[-1][1]), 3),
                      'obs': ' | '.join(obs), '_a': a, '_b': b})
    # laço sem rótulo: herda do vizinho de jusante (o que sai da central leva todos os de jusante) — marcado como inferido
    filhos = collections.defaultdict(list)
    for l in lin_s: filhos[l['_a']].append(l)
    def lacos_de(l, vis=()):
        s = set(x for x in l['lacos_rotulo'].split(', ') if x)
        for f in filhos[l['_b']]:
            if id(f) not in vis: s |= lacos_de(f, vis + (id(l),))
        return s
    for l in lin_s:
        tot = lacos_de(l)
        l['lacos_inferidos'] = ', '.join(sorted(tot - set(x for x in l['lacos_rotulo'].split(', ') if x)))
    for l in lin_s:
        del l['_a'], l['_b']
    salva('INC_fase2_sdai_trechos', lin_s, ['trecho', 'de', 'para', 'L_m', 'lacos_rotulo', 'lacos_inferidos', 'E_ini', 'N_ini', 'E_fim', 'N_fim', 'obs'])
    gs = Rs.grau()
    salva('INC_fase2_sdai_caixas', [{'caixa': c['id'], 'tipo': 'central de alarme' if c['tipo'] == 'CENTRAL' else 'caixa de passagem',
                                     'E': round(float(c['c'][0]), 3), 'N': round(float(c['c'][1]), 3),
                                     'eletrodutos_ligados': gs[next((x['id'] for x in Rs.nos if x['caixa'] == c['id']), -1)]} for c in cxs],
          ['caixa', 'tipo', 'E', 'N', 'eletrodutos_ligados'])
    json.dump({'hidrantes': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(lin_h, Th)],
               'sdai': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(lin_s, Ts)],
               'nos_h': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in nos_h],
               'caixas_sdai': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in c.items()} for c in cxs]},
              open(os.path.join(WRK, 'inc_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    mapa(lin_h, Th, nos_h, lin_s, Ts, cxs)
    print(f'HIDRANTES: {len(lin_h)} trechos, {sum(l["L_m"] for l in lin_h):.1f} m; {len(hid)} hidrantes; ligações presumidas {nl_h}')
    print('  sem ligação à CB:', [l['trecho'] for l in lin_h if 'não liga' in l['obs']], '| nós:', [(n['no'], n['obs']) for n in nos_csv if n['obs']])
    print(f'SDAI: {len(lin_s)} trechos, {sum(l["L_m"] for l in lin_s):.1f} m; {len(cxs)} caixas; ligações presumidas {nl_s}')
    print('  sem ligação à central:', [l['trecho'] for l in lin_s if 'não liga' in l['obs']])
    print('  laços por trecho:', collections.Counter(l['lacos_rotulo'] for l in lin_s).most_common(12))


def dist_obs(c, T):
    d = min(dist_pt_seg(np.asarray(c), np.asarray(a), np.asarray(b))[0] for t in T for a, b in zip(t['pts'][:-1], t['pts'][1:]))
    return (f'sobre o tubo (a {d:.2f} m do eixo): tê presumido' if d < 0.5 else f'sem tubo ligado: tubo mais próximo a {d:.2f} m (ramal não desenhado?)')


def bfs(T, origem):
    adj = collections.defaultdict(list)
    for k, t in enumerate(T): adj[t['nos'][0]].append((t['nos'][1], k)); adj[t['nos'][1]].append((t['nos'][0], k))
    vis = set(origem); fila = list(origem); ordem = {}
    while fila:
        n = fila.pop(0)
        for m, k in adj[n]:
            if k in ordem: continue
            ordem[k] = (n, m)
            if m not in vis: vis.add(m); fila.append(m)
    return ordem


def mapa(lin_h, Th, nos_h, lin_s, Ts, cxs):
    S = carrega('SIT'); arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO', 'PAGINA')):
            p = d['pts'][:, :2]
            if p[:, 0].min() > 567640 and p[:, 1].min() > 8634560 and p[:, 0].max() < 567800: arq.extend(zip(p[:-1], p[1:]))
    for nome, L, T, cor in (('hidrantes', lin_h, Th, '#d62728'), ('sdai', lin_s, Ts, '#9467bd')):
        fig, ax = plt.subplots(figsize=(16, 15))
        ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
        for l, t in zip(L, T):
            p = np.array(t['pts_fluxo']); c = cor if 'não liga' not in l['obs'] else 'orange'
            ax.plot(p[:, 0], p[:, 1], '-', color=c, lw=2)
            m = p[len(p) // 2] if len(p) > 2 else p.mean(0); u = unit(p[-1] - p[0])
            if l['L_m'] > 3: ax.annotate('', xy=m + u * 0.7, xytext=m - u * 0.7, arrowprops=dict(arrowstyle='-|>', color=c))
            if nome == 'sdai' and (l.get('lacos_rotulo') or l.get('lacos_inferidos')) and l['L_m'] > 4:
                ax.text(*(m + [0.4, 0.4]), (l['lacos_rotulo'] or '(' + l['lacos_inferidos'] + ')'), fontsize=6, color='indigo', clip_on=True)
        if nome == 'hidrantes':
            for n in nos_h:
                ax.plot(*n['c'], 'P' if n['tipo'] == 'HID' else 's', ms=10, mfc='w', mec='k'); ax.text(n['c'][0] + 0.6, n['c'][1] + 0.6, n['id'], fontsize=8)
                if n.get('contorno'):
                    for q in n['contorno']: q = np.array(q); ax.plot(q[:, 0], q[:, 1], 'k-', lw=1)
        else:
            for c in cxs:
                ax.plot(*c['c'], 'D' if c['tipo'] == 'CX' else '*', ms=6 if c['tipo'] == 'CX' else 14, mfc='w' if c['tipo'] == 'CX' else 'gold', mec='k')
                ax.text(c['c'][0] + 0.5, c['c'][1] - 0.9, c['id'], fontsize=6, clip_on=True)
        ax.set_xlim(567645, 567795); ax.set_ylim(8634570, 8634710); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
        ax.set_title(f'ETIB Catu — INC-001-ING-R03: {"rede de hidrantes (PEAD 2½″)" if nome == "hidrantes" else "SDAI (eletrodutos e caixas; laços do rótulo, entre parênteses inferidos)"} — {len(L)} trechos, {sum(l["L_m"] for l in L):.0f} m; laranja = não liga à origem')
        fig.savefig(os.path.join(REL, f'INC_fase2_mapa_{nome}_{DATA}.png'), dpi=110, bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    main()
