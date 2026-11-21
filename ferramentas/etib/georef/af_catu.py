# -*- coding: utf-8 -*-
"""ETIB Catu — fase 2 da água fria (AGF-001-R02_GEO, UTM): rede em linha única do reservatório existente até os blocos,
com Ø/material do rótulo, registros (RG) e destinos ("ALIMENTAÇÃO ..."). A cota é premissa (o projeto não traz):
fica para a fase 3, sobre o terreno do IMP.
Uso: python -I -X utf8 af_catu.py
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
ARQ = ('zw$7D57', 'zw$44A6', 'ARQ_IMP')


def main():
    E = carrega('AF')
    ob = [d for d in E if not d['path'].startswith(ARQ) and not d['layer'].upper().startswith('ARQ') and na_obra(d['pts']).all()]
    tx = [d for d in ob if d['tipo'] == 'TEXT']
    chamadas = [d['pts'][:, :2] for d in ob if d['tipo'] == 'PL' and d['layer'] == '0' and d['path'] == '']
    # nós: registros (bloco zw$EE94 ou símbolo solto com texto "RG"), reservatório, destinos
    nos = []
    rgs = [d for d in tx if d['texto'].strip() == 'RG']
    for t in rgs:
        p = t['pts'][0, :2]
        bit = min((d for d in tx if re.fullmatch(r'[\d./ ]+"', d['texto'].strip())), key=lambda d: np.linalg.norm(d['pts'][0, :2] - p))
        ins = [d for d in ob if d['tipo'] == 'INSERT' and d['nome'] == 'zw$EE94' and np.linalg.norm(d['pts'][0, :2] - p) < 1.2]
        circ = [d for d in ob if d['tipo'] == 'CIRCLE' and d['layer'] == 'TEXTOS' and np.linalg.norm(d['pts'][0, :2] - p) < 1.5]
        c = ins[0]['pts'][0, :2] if ins else (circ[0]['pts'][0, :2] if circ else p)
        nos.append({'tipo': 'RG', 'c': c.copy(), 'raio': 0.05, 'snap': 0.3, 'corta': False, 'bitola': bit['texto'].strip(), 'id': ''})
    for i, n in enumerate(sorted(nos, key=lambda n: (-n['c'][1], n['c'][0]))): n['id'] = f'RG-{i+1:02d}'
    eixos = ll.linhas_da_rede(ob, ('AF-Condutos', 'AF-Condutos Reúso', 'AL-Condutos'), so_nivel_superior=False)
    R, T, nlig = ll.monta(eixos, nos, snap_no=0.3, snap_ponta=0.05, snap_te=0.06, gap=0.3, gap_caixa=0.4)
    cx = {n['id']: n for n in nos}
    # rótulos "PVC" + "NN mm" (girados com o tubo)
    for t in T: t['rot'] = []
    for m in tx:
        if not re.fullmatch(r'\d+\s*mm', m['texto'].strip()): continue
        p = m['pts'][0, :2]
        mat = next((d['texto'].strip() for d in tx if d['texto'].strip().startswith('PVC') and np.linalg.norm(d['pts'][0, :2] - p) < 0.8), '')
        b = ll.trecho_mais_proximo(p, T, rot=m['rot'], tol=1.5)
        if b:
            t = T[b[1]]
            def custo(i, rot=m['rot']):
                a_, b_ = np.asarray(t['pts'][i]), np.asarray(t['pts'][i + 1])
                ang = np.degrees(np.arctan2(*(b_ - a_)[::-1])) % 180
                da = abs(((rot % 180) - ang + 90) % 180 - 90)
                return dist_pt_seg(p, a_, b_)[0] + (0 if da < 15 else 100)
            seg = min(range(len(t['pts']) - 1), key=custo)
            t['rot'].append({'dn': num(m['texto']), 'mat': mat, 'seg': seg, 'L_seg': float(np.linalg.norm(np.subtract(t['pts'][seg + 1], t['pts'][seg])))})
    for t in T:
        t['rot'].sort(key=lambda r: -r['L_seg'])   # o Ø do trecho é o do maior segmento rotulado
    # destinos e origem pelas chamadas
    # a chamada tem uma ponta junto do texto e a outra no tubo: vale a ponta mais perto de um nó da rede
    dest = {}
    g = R.grau()
    cand = [n for n in R.nos if g[n['id']] >= 1 and (g[n['id']] == 1 or n['caixa'] is not None)]
    for d in tx:
        if 'ALIMENTA' in d['texto'].upper() or 'RESERVAT' in d['texto'].upper():
            p = d['pts'][0, :2]
            best = None
            for ch in chamadas:
                if min(np.linalg.norm(v - p) for v in ch) > 2.5: continue
                for ponta in (ch[0], ch[-1]):
                    n = min(cand, key=lambda n: np.linalg.norm(np.asarray(n['c']) - ponta))
                    dd = np.linalg.norm(np.asarray(n['c']) - ponta)
                    if dd < 1.5 and (best is None or dd < best[0]): best = (dd, n['id'])
            if best: dest[best[1]] = d['texto'].replace('^J', ' ').replace('\n', ' ').strip()
    origem = [n for n, v in dest.items() if 'RESERVAT' in v.upper()]
    # sentido: do reservatório para fora (BFS); trechos que não alcançam o reservatório ficam "sem ligação"
    adj = collections.defaultdict(list)
    for k, t in enumerate(T): adj[t['nos'][0]].append((t['nos'][1], k)); adj[t['nos'][1]].append((t['nos'][0], k))
    # o ramal do bloco administrativo sai do reservatório numa ponta própria: todas as pontas a < 3 m do texto contam como origem
    res_txt = next((d for d in tx if 'RESERVAT' in d['texto'].upper()), None)
    g = R.grau()
    if res_txt is not None:
        for n in R.nos:
            if g[n['id']] == 1 and np.linalg.norm(np.asarray(n['c']) - res_txt['pts'][0, :2]) < 4.0 and n['id'] not in origem:
                origem.append(n['id']); dest.setdefault(n['id'], 'RESERVATÓRIO EXISTENTE')
    vis = set(origem); fila = list(origem); ordem = {}
    while fila:
        n = fila.pop(0)
        for m, k in adj[n]:
            if k in ordem: continue
            ordem[k] = (n, m)
            if m not in vis: vis.add(m); fila.append(m)
    linhas = []
    for k, t in enumerate(T):
        a, b = ordem.get(k, t['nos'])
        pts = t['pts'] if a == t['nos'][0] else t['pts'][::-1]
        t['pts_fluxo'] = [np.asarray(p) for p in pts]
        rot = t['rot'][0] if t['rot'] else {}
        inv = a != t['nos'][0]
        dnj = max(t['rot'], key=lambda r: (len(t['pts']) - 2 - r['seg']) if inv else r['seg'])['dn'] if t['rot'] else None
        obs = []
        if not t['rot']: obs.append('sem rótulo próprio (Ø do trecho vizinho, ver coluna DN_adotado)')
        if len({r['dn'] for r in t['rot']}) > 1: obs.append('redução no trecho: ' + ' / '.join(f"Ø{r['dn']:.0f} no segmento de {r['L_seg']:.1f} m" for r in t['rot']))
        if k not in ordem: obs.append('não liga ao reservatório')
        if t['presumido']: obs.append('ligação presumida (desenho não encosta)')
        linhas.append({'trecho': f'AF-{k+1:02d}', 'de': ll.nome_no(R, a, cx), 'para': ll.nome_no(R, b, cx), 'L_m': round(t['L'], 2),
                       'DN_mm': rot.get('dn'), 'material': rot.get('mat', ''), 'destino_jusante': dest.get(b, ''),
                       'E_ini': round(float(pts[0][0]), 3), 'N_ini': round(float(pts[0][1]), 3),
                       'E_fim': round(float(pts[-1][0]), 3), 'N_fim': round(float(pts[-1][1]), 3), 'obs': ' | '.join(obs), '_dnj': dnj})
    # Ø sem rótulo: herda do trecho de montante (mesma linha), senão do de jusante
    por_no_sai = collections.defaultdict(list); por_no_chega = collections.defaultdict(list)
    for l, t in zip(linhas, T):
        a, b = ordem.get(T.index(t), t['nos'])
        por_no_sai[a].append(l); por_no_chega[b].append(l); l['_a'], l['_b'] = a, b
    for _ in range(5):
        for l in linhas:
            if l['DN_mm'] is None:
                v = [x.get('_dnj') or x.get('DN_adotado') for x in por_no_chega[l['_a']] if x.get('_dnj') or x.get('DN_adotado')]                     or [x['DN_mm'] for x in por_no_sai[l['_b']] if x['DN_mm']]
                if v: l['DN_adotado'] = v[0]; l['_dnj'] = v[0]
    for l in linhas:
        l.setdefault('DN_adotado', l['DN_mm'])
        if l['_b'] in dest and 'RESERV' not in dest[l['_b']].upper():
            l['destino_jusante'] = dest[l['_b']]
        del l['_a'], l['_b'], l['_dnj']
    cols = ['trecho', 'de', 'para', 'L_m', 'DN_mm', 'DN_adotado', 'material', 'destino_jusante', 'E_ini', 'N_ini', 'E_fim', 'N_fim', 'obs']
    with open(os.path.join(REL, f'AF_fase2_trechos_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows([{c: l[c] for c in cols} for l in linhas])
    gr = R.grau()
    with open(os.path.join(REL, f'AF_fase2_nos_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['no', 'tipo', 'E', 'N', 'bitola', 'tubos_ligados', 'obs'])
        for n in nos:
            nn = next((x['id'] for x in R.nos if x['caixa'] == n['id']), None)
            w.writerow([n['id'], 'registro de gaveta', round(float(n['c'][0]), 3), round(float(n['c'][1]), 3), n['bitola'], gr[nn] if nn is not None else 0, ''])
        for k, v in dest.items():
            c = R.nos[k]['c']
            w.writerow([ll.nome_no(R, k, cx), 'origem' if 'RESERV' in v.upper() else 'entrada no bloco', round(float(c[0]), 3), round(float(c[1]), 3), '', gr[k], v])
    json.dump({'trechos': [{**l, 'pts': [list(map(float, p)) for p in t['pts_fluxo']]} for l, t in zip(linhas, T)],
               'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in nos]},
              open(os.path.join(WRK, 'af_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # mapa
    S = carrega('SIT'); arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO', 'PAGINA')):
            p = d['pts'][:, :2]
            if p[:, 0].min() > 567640 and p[:, 1].min() > 8634590 and p[:, 0].max() < 567800: arq.extend(zip(p[:-1], p[1:]))
    fig, ax = plt.subplots(figsize=(15, 15))
    ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
    cor = {75: '#08306b', 60: '#2171b5', 50: '#4292c6', 32: '#6baed6', 25: '#9ecae1'}
    for l, t in zip(linhas, T):
        p = np.array(t['pts_fluxo']); dn = int(l['DN_adotado'] or 0)
        ax.plot(p[:, 0], p[:, 1], '-', color=cor.get(dn, 'r'), lw=1 + dn / 20)
        m = p.mean(0) if len(p) == 2 else p[len(p) // 2]
        u = unit(p[-1] - p[0])
        ax.annotate('', xy=m + u * 0.8, xytext=m - u * 0.8, arrowprops=dict(arrowstyle='-|>', color=cor.get(dn, 'r')))
        ax.text(*(m + [0.6, 0.6]), f"{l['trecho']} Ø{dn}", fontsize=7, color=cor.get(dn, 'r'))
    for n in nos:
        ax.plot(*n['c'], 's', ms=7, mfc='w', mec='k'); ax.text(n['c'][0] + 0.6, n['c'][1] - 0.9, f"{n['id']} {n['bitola']}", fontsize=7)
    for k, v in dest.items():
        c = R.nos[k]['c']; ax.plot(*c, '*', ms=12, color='orange' if 'RESERV' in v.upper() else 'g'); ax.text(c[0] + 0.6, c[1] + 0.4, v, fontsize=7, color='darkgreen')
    ax.set_xlim(567675, 567760); ax.set_ylim(8634600, 8634712); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title(f'ETIB Catu — AGF-001-R02: água fria extraída (fase 2) — {len(linhas)} trechos, {sum(l["L_m"] for l in linhas):.0f} m; ★ laranja = reservatório, ★ verde = entrada nos blocos')
    fig.savefig(os.path.join(REL, f'AF_fase2_mapa_{DATA}.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print(f'trechos {len(linhas)}  {sum(l["L_m"] for l in linhas):.1f} m  por DN', collections.Counter(l['DN_adotado'] for l in linhas), '| ligações presumidas', nlig)
    for l in linhas: print(' ', l['trecho'], l['de'], '->', l['para'], l['L_m'], 'Ø', l['DN_mm'], l['DN_adotado'], l['destino_jusante'], '|', l['obs'])
    print('destinos', dest)


if __name__ == '__main__':
    main()
