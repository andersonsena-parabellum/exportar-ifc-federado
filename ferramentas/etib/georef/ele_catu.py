# -*- coding: utf-8 -*-
"""ETIB Catu — fase 2 da elétrica: EL-001 (alimentação BT, bancos de eletrodutos, caixas 80x80) e EL-002 (iluminação externa,
circuitos IE-xx, caixas e postes). Cada linha do layer "02. F_ELETRODUTO PISO" é um eletroduto. Rotas = eletrodutos entre o mesmo
par de caixas (banco). Rótulos (circuito + Ø) do layer "01. F_FIAÇÃO-INDICAÇÃO" vão para a rota mais próxima.
Uso: python -I -X utf8 ele_catu.py
"""
import sys, os, re, csv, json, math, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from catu_comum import carrega, na_obra, num, REL, WRK
from rede_lib import unit, dist_pt_seg
import linha_lib as ll

DATA = '2026-10-18'
L_ELE = ('02. F_ELETRODUTO PISO',)


def bitola(s):
    s = s.replace('%%C', 'Ø').replace('%%c', 'Ø').strip()
    m = re.match(r'Ø\s*([\d. /]+)"?', s)
    return ('Ø' + m.group(1).strip().replace(' ', '') + '"') if m else None


def extrai(tag, cfg):
    E = carrega(tag)
    ob = [d for d in E if not d['path'].startswith('ARQ BASE IMP') and na_obra(d['pts']).all()]
    tx = [d for d in ob if d['tipo'] == 'TEXT' and d['layer'] in ('01. F_FIAÇÃO-INDICAÇÃO', 'C-TEXTO')]
    # caixas (e postes, no EL-002) — posição: centro da geometria do bloco (o ponto base pode estar fora)
    por_raiz = collections.defaultdict(list)
    for d in ob:
        if d['path'] and d['tipo'] != 'INSERT': por_raiz[d['raiz']].append(d['pts'][:, :2])
    nos = []
    for d in ob:
        if d['tipo'] == 'INSERT' and d['path'] == '' and (d['nome'] in cfg['caixas'] or d['nome'] in cfg.get('postes', ())):
            P = np.vstack(por_raiz.get(d['raiz'], [d['pts'][:, :2]]))
            c = (P.min(0) + P.max(0)) / 2
            tipo = 'POSTE' if d['nome'] in cfg.get('postes', ()) else 'CX'
            lado = float(np.ptp(P, axis=0).max())
            if all(np.linalg.norm(c - n['c']) > 0.2 for n in nos):
                nos.append({'tipo': tipo, 'c': c, 'raio': min(lado / 2, 0.5) if tipo == 'CX' else 0.15, 'snap': 0.45 if tipo == 'CX' else 0.6,
                            'corta': tipo == 'CX', 'bloco': d['nome']})
    # rótulo de dimensão da caixa ("CX. 80x80 cm"): o mais próximo
    dims = [d for d in tx if re.match(r'(?i)cx\.?\s*\d+x\d+', d['texto'].strip())]
    for n in nos:
        if n['tipo'] != 'CX': continue
        b = min(dims, key=lambda d: np.linalg.norm(d['pts'][0, :2] - n['c']), default=None)
        n['dim'] = b['texto'].strip() if b is not None and np.linalg.norm(b['pts'][0, :2] - n['c']) < 3 else ''
    cont = collections.Counter()
    for n in sorted(nos, key=lambda n: (-n['c'][1], n['c'][0])):
        cont[n['tipo']] += 1; n['id'] = f"{cfg['pref']}-{n['tipo']}{cont[n['tipo']]:02d}"
    # QGBT (origem) e quadros dos blocos (pontas): nós próprios, nomeados pelo texto mais próximo
    qtx = [d for d in tx if re.match(r'^QD', d['texto'].strip())]
    for d in (E if cfg.get('qgbt') else []):   # o texto QGBT pode estar dentro da arquitetura de base
        if d['tipo'] == 'TEXT' and d['texto'].strip() == 'QGBT' and na_obra(d['pts'][:1]).all():
            nos.append({'tipo': 'QGBT', 'id': 'QGBT', 'c': d['pts'][0, :2].copy() + [0, -0.4], 'raio': 0.6, 'snap': 0.5, 'corta': True, 'bloco': 'texto QGBT'}); break
    for d in ob:
        if d['tipo'] == 'INSERT' and d['path'] == '' and d['nome'] in cfg.get('quadros', ()):
            P = np.vstack(por_raiz.get(d['raiz'], [d['pts'][:, :2]])); c = P.mean(0)
            if any(np.linalg.norm(c - n['c']) < 0.3 for n in nos): continue
            t = min(qtx, key=lambda q: np.linalg.norm(q['pts'][0, :2] - c), default=None)
            nome = re.sub(r'\s*-\s*', '-', t['texto'].strip()) if t is not None and np.linalg.norm(t['pts'][0, :2] - c) < 3 else 'QD'
            nid = nome; k = 2
            while any(n['id'] == nid for n in nos): nid = f'{nome}#{k}'; k += 1
            nos.append({'tipo': 'QD', 'id': nid, 'c': c, 'raio': 0.1, 'snap': 0.6, 'corta': False, 'bloco': d['nome']})
    # quadros (pontas nos blocos)
    quadros = [d for d in tx if re.match(r'^QD', d['texto'].strip()) and 'mm' not in d['texto']]
    eix = ll.linhas_da_rede(ob, L_ELE, so_nivel_superior=True)
    R, T, nlig = ll.monta(eix, nos, snap_no=0.45, snap_ponta=0.03, snap_te=0.03, gap=0.2, gap_caixa=0.6)
    cx = {n['id']: n for n in nos}
    # rotas = mesmo par de nós de projeto nas pontas (feixe); pontas soltas viram o nó mais próximo
    def chave(t):
        a, b = (ll.nome_no(R, t['nos'][0], cx), ll.nome_no(R, t['nos'][1], cx))
        return tuple(sorted((a, b)))
    rotas = collections.defaultdict(list)
    for k, t in enumerate(T): rotas[chave(t)].append(k)
    # rótulos: circuito + Ø (+ fiação #) agrupados por proximidade; vão para a rota mais próxima
    circ = [d for d in tx if re.match(cfg['circuito'], d['texto'].strip())]
    diam = [d for d in tx if bitola(d['texto'])]
    grupos = []
    for c in circ:
        p = c['pts'][0, :2]
        dm = min(diam, key=lambda d: np.linalg.norm(d['pts'][0, :2] - p), default=None)
        dd = np.linalg.norm(dm['pts'][0, :2] - p) if dm is not None else 9
        grupos.append({'circuito': re.sub(r'\s*-\s*', '-', c['texto'].strip()), 'diam': bitola(dm['texto']) if dd < 1.6 else '', 'p': p})
    rot_por_rota = collections.defaultdict(list)
    for g in grupos:
        b = ll.trecho_mais_proximo(g['p'], T, tol=cfg.get('tol_rot', 3.0))
        if b: rot_por_rota[chave(T[b[1]])].append(g)
    linhas, lin_rotas = [], []
    for i, (k, idx) in enumerate(sorted(rotas.items(), key=lambda kv: kv[0])):
        Ls = [T[j]['L'] for j in idx]
        gs = rot_por_rota.get(k, [])
        ids = collections.Counter((g['circuito'], g['diam']) for g in gs)
        obs = []
        if not gs: obs.append('sem rótulo de circuito: Ø pela nota do projeto')
        if any(T[j]['presumido'] for j in idx): obs.append('ligação presumida (desenho não encosta)')
        if k[0].startswith('PONTA') or k[1].startswith('PONTA'): obs.append('ponta sem caixa (entrada em bloco/quadro?)')
        lin_rotas.append({'rota': f"{cfg['pref']}-R{i+1:02d}", 'de': k[0], 'para': k[1], 'eletrodutos': len(idx), 'L_medio_m': round(float(np.mean(Ls)), 2),
                          'L_total_m': round(float(np.sum(Ls)), 2),
                          'circuitos_rotulo': '; '.join(f'{c} {d}'.strip() + (f' (×{n})' if n > 1 else '') for (c, d), n in sorted(ids.items())),
                          'obs': ' | '.join(obs)})
        for j in idx:
            t = T[j]; p = t['pts']
            linhas.append({'eletroduto': f"{cfg['pref']}-{j+1:03d}", 'rota': lin_rotas[-1]['rota'], 'de': ll.nome_no(R, t['nos'][0], cx), 'para': ll.nome_no(R, t['nos'][1], cx),
                           'L_m': round(t['L'], 2), 'E_ini': round(float(p[0][0]), 3), 'N_ini': round(float(p[0][1]), 3),
                           'E_fim': round(float(p[-1][0]), 3), 'N_fim': round(float(p[-1][1]), 3), '_pts': p})
    gr = R.grau()
    nos_csv = []
    for n in nos:
        nn = next((x['id'] for x in R.nos if x['caixa'] == n['id']), None)
        nos_csv.append({'no': n['id'], 'tipo': {'CX': 'caixa de passagem', 'POSTE': 'poste', 'QGBT': 'QGBT (origem)', 'QD': 'quadro do bloco'}[n['tipo']], 'dimensao_rotulo': n.get('dim', ''),
                        'bloco': n['bloco'], 'E': round(float(n['c'][0]), 3), 'N': round(float(n['c'][1]), 3),
                        'eletrodutos_ligados': gr[nn] if nn is not None else 0})
    return {'linhas': linhas, 'rotas': lin_rotas, 'nos': nos_csv, 'nos_raw': nos, 'nlig': nlig, 'quadros': [(q['texto'], q['pts'][0, :2]) for q in quadros]}


def salva(nome, linhas, cols):
    with open(os.path.join(REL, f'{nome}_{DATA}.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows([{c: l.get(c, '') for c in cols} for l in linhas])


def mapa(res):
    S = carrega('SIT'); arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO', 'PAGINA')):
            p = d['pts'][:, :2]
            if p[:, 0].min() > 567640 and p[:, 1].min() > 8634560 and p[:, 0].max() < 567800: arq.extend(zip(p[:-1], p[1:]))
    fig, ax = plt.subplots(figsize=(17, 16))
    ax.add_collection(LineCollection(arq, colors='0.82', linewidths=0.3))
    for tag, cor in (('EL1', '#ff7f0e'), ('EL2', '#2ca02c')):
        r = res[tag]
        for l in r['linhas']:
            p = np.array(l['_pts']); ax.plot(p[:, 0], p[:, 1], '-', color=cor, lw=1.0)
        for ro in r['rotas']:
            ls = [l for l in r['linhas'] if l['rota'] == ro['rota']]
            p = np.array(ls[0]['_pts']); m = p[len(p) // 2] if len(p) > 2 else p.mean(0)
            if ro['L_medio_m'] > 3:
                ax.text(*(m + [0.4, 0.4]), f"{ro['rota']} ({ro['eletrodutos']})", fontsize=6, color=cor, clip_on=True)
        for n in r['nos_raw']:
            ax.plot(*n['c'], 's' if n['tipo'] == 'CX' else 'o', ms=6 if n['tipo'] == 'CX' else 4, mfc='w', mec=cor)
    ax.plot([], [], '-', color='#ff7f0e', label='EL-001 alimentação BT (cada linha = 1 eletroduto)')
    ax.plot([], [], '-', color='#2ca02c', label='EL-002 iluminação externa')
    ax.legend(loc='lower left'); ax.set_xlim(567650, 567795); ax.set_ylim(8634570, 8634705); ax.set_aspect('equal')
    ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
    ax.set_title('ETIB Catu — elétrica extraída (fase 2): rotas entre caixas, (n) = eletrodutos no banco; □ caixa, ○ poste')
    fig.savefig(os.path.join(REL, f'ELE_fase2_mapa_{DATA}.png'), dpi=110, bbox_inches='tight'); plt.close(fig)


def main():
    cfg = {'EL1': {'pref': 'EL1', 'qgbt': True, 'caixas': ('*U8', '*U50'), 'quadros': ('*U7', 'QUADRO ELE', 'zw$81C8', 'zw$333D'), 'circuito': r'^QD'},
           'EL2': {'pref': 'EL2', 'caixas': ('Cx60x60',), 'postes': ('POSTE UMA PETALA',), 'circuito': r'^IE\s*-?\s*\d+'}}
    res = {}
    for tag, c in cfg.items():
        r = extrai(tag, c); res[tag] = r
        salva(f'ELE_fase2_{tag}_eletrodutos', r['linhas'], ['eletroduto', 'rota', 'de', 'para', 'L_m', 'E_ini', 'N_ini', 'E_fim', 'N_fim'])
        salva(f'ELE_fase2_{tag}_rotas', r['rotas'], ['rota', 'de', 'para', 'eletrodutos', 'L_medio_m', 'L_total_m', 'circuitos_rotulo', 'obs'])
        salva(f'ELE_fase2_{tag}_caixas', r['nos'], ['no', 'tipo', 'dimensao_rotulo', 'bloco', 'E', 'N', 'eletrodutos_ligados'])
        print(f"{tag}: {len(r['linhas'])} eletrodutos, {sum(l['L_m'] for l in r['linhas']):.1f} m, {len(r['rotas'])} rotas, "
              f"{sum(1 for n in r['nos'] if n['tipo'] == 'caixa de passagem')} caixas, {sum(1 for n in r['nos'] if n['tipo'] == 'quadro do bloco')} quadros, {sum(1 for n in r['nos'] if n['tipo'] == 'poste')} postes, ligações presumidas {r['nlig']}")
        print('   nós sem eletroduto:', [n['no'] for n in r['nos'] if not n['eletrodutos_ligados'] and n['tipo'] != 'poste'],
              '| postes sem eletroduto:', sum(1 for n in r['nos'] if not n['eletrodutos_ligados'] and n['tipo'] == 'poste'))
        print('   rotas sem rótulo:', sum(1 for ro in r['rotas'] if not ro['circuitos_rotulo']), '| pontas:', sum(1 for ro in r['rotas'] if 'ponta' in ro['obs']))
        for ro in r['rotas'][:60]: print('     ', ro['rota'], ro['de'], ro['para'], ro['eletrodutos'], ro['L_medio_m'], '|', ro['circuitos_rotulo'][:120])
    json.dump({t: {'eletrodutos': [{**{k: v for k, v in l.items() if k != '_pts'}, 'pts': [list(map(float, p)) for p in l['_pts']]} for l in r['linhas']],
                   'rotas': r['rotas'], 'nos': [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in n.items()} for n in r['nos_raw']]}
               for t, r in res.items()}, open(os.path.join(WRK, 'ele_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    mapa(res)


if __name__ == '__main__':
    main()
