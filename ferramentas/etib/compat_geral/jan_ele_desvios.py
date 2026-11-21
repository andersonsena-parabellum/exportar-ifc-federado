# -*- coding: utf-8 -*-
"""Fase B (cota atual, "mexer o mínimo"): os 3 desvios em planta que profundidade não resolve, por cima do plano ele_plano_atual.
  ELE-I-01  (guarita): passa a 22 cm da subida do hidrante AH-10 (era 3 cm) com um vértice a leste;
  ELE-I-13  (CX-10 da drenagem): contorna a caixa pelo oeste;
  ELE-I-31.8–.11 (PVE-10 do esgoto): contorna o poço pelo oeste (0,9 m).
Avalia o clash da elétrica e regrava compat_R01/ele_instrucoes.tsv (plano + desvios)."""
import sys, os, json, pickle, collections, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
D = os.path.dirname(JD.G); GX = os.path.join(D, 'geo_exec'); SUF = '_atual'
plano = json.load(open(os.path.join(D, 'ele_plano' + SUF + '.json'), encoding='utf-8'))
S2, M2 = pickle.load(open(os.path.join(D, 'ele_plano' + SUF + '_geo.pkl'), 'rb'))
SEG0, _ = JD.carregar(g=GX, est=None, discs=('ELE',)); orig = {s['id']: s for s in SEG0}
# id original -> lista de vértices em planta (x, y); None = ponta do plano (S2) naquele lado
DESV = {'5247455': [None, (44.80, 3.00), None],
        '5247479': [None, (45.50, 96.60), None],
        '5247681': [(64.79, 86.45), (63.51, 87.51)], '5247683': [(63.51, 87.51), (63.04, 88.85)],
        '5247685': [(63.04, 88.85), (62.52, 90.17)], '5247687': [(62.52, 90.17), (62.80, 91.78)],
        '5247583': [None, (66.75, 35.25), None]}   # ELE-I-28.1 contorna a CX-SDAI-03 pelo leste
# localizar, em S2, os sub-segmentos de cada peça desviada (pela corrida e pelo trecho ao longo dela)
rem = set(); novos = []
for k, r in enumerate(plano['corridas']):
    pecas = r['pecas']; V = np.array(r['vertices'])
    sv = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(V[:, :2], axis=0), axis=1))])
    lim = [0.0]
    for pid, inv in pecas: lim.append(lim[-1] + np.linalg.norm(orig[pid]['b0'][:2] - orig[pid]['a0'][:2]))
    subs = sorted([s for s in S2 if s.get('run') == k and '~' in s['id']], key=lambda s: int(s['id'].split('.')[-1]))
    for p, (pid, inv) in enumerate(pecas):
        if pid not in DESV: continue
        meus = [s for m, s in enumerate(subs) if lim[p] <= (sv[m] + sv[m + 1]) / 2 < lim[p + 1]]
        for s in meus: rem.add(s['id'])
        z = min(min(s['a'][2], s['b'][2]) for s in meus)   # cota mais funda que o plano dava à peça
        pa = meus[0]['a'] if not inv else meus[-1]['b']; pb = meus[-1]['b'] if not inv else meus[0]['a']
        if inv: pa, pb = pb, pa
        xy = [tuple(pa[:2]) if v is None and n == 0 else (tuple(pb[:2]) if v is None else v) for n, v in enumerate(DESV[pid])]
        if len(DESV[pid]) == 2 and all(v is not None for v in DESV[pid]): xy = DESV[pid]
        pts = [np.array([x, y, z]) for x, y in xy]
        for n in range(len(pts) - 1):
            d = dict(meus[0]); d.update(id=f'DESV-{pid}-{n}', orig=pid, n=n, a=pts[n].copy(), b=pts[n + 1].copy(), a0=pts[n].copy(), b0=pts[n + 1].copy(), de=orig[pid]['de'])
            novos.append(d)
S3 = [s for s in S2 if s['id'] not in rem] + novos
print(f'desvios: {len(DESV)} peças, {len(rem)} sub-segmentos trocados por {len(novos)}')
IDX = mt.Indice(S3, M2); conf = []
for i, s in enumerate(S3):
    if s['disc'] != 'ELE': continue
    for t, j, g, pt in mt.avaliar_seg(i, IDX):
        B = S3[j] if t == 'S' else M2[j]
        if B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes'): continue
        if g < mt.TOL: conf.append((s.get('trecho'), s['id'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt, 2))))
for j, M in enumerate(M2):
    if M['disc'] != 'ELE' or not str(M.get('grupo', '')).startswith('CX-'): continue
    for t, k2, g, pt in mt.avaliar_mesh(j, IDX):
        B = S3[k2] if t == 'S' else M2[k2]
        if B['disc'] == 'ELE' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        if g < mt.TOL: conf.append((M['grupo'], 'caixa', B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt, 2))))
print('colisões da elétrica que sobram:', len(conf))
for c in sorted(set(conf), key=lambda c: c[4]): print('  ', c)
# caixas: só muda a profundidade se precisar (eletroduto mais fundo que o fundo de hoje, ou a caixa de hoje bate em outra rede)
manter = set()
grupos = collections.defaultdict(list)
for j, M in enumerate(M2):
    if M['disc'] == 'ELE' and str(M.get('grupo', '')).startswith('CX-') and M['cat'].startswith('Equip'): grupos[M['grupo']].append(j)
for g, js in grupos.items():
    c = plano['caixas'].get(g)
    if not c or c['prof'] is None or abs(c['prof'] - c['prof_hoje']) < 0.005: continue
    lo = np.min([M2[j]['lo'] for j in js], 0); hi = np.max([M2[j]['hi'] for j in js], 0); top = hi[2]
    fundo_hoje = top - c['prof_hoje']
    fundos = [p[2] - s['de'] / 2 for s in S3 if s['disc'] == 'ELE' for p in (s['a'], s['b']) if lo[0] - .15 <= p[0] <= hi[0] + .15 and lo[1] - .15 <= p[1] <= hi[1] + .15]
    if fundos and min(fundos) - 0.10 < fundo_hoje - 0.005: continue          # precisa aprofundar
    bak = {j: (M2[j]['tri'].copy(), M2[j]['lo'].copy(), M2[j]['hi'].copy()) for j in js}
    k = c['prof_hoje'] / c['prof']
    for j in js:
        Tt = M2[j]['tri'].copy(); Tt[..., 2] = top - (top - Tt[..., 2]) * k; M2[j]['tri'] = Tt; M2[j]['lo'] = Tt.reshape(-1, 3).min(0); M2[j]['hi'] = Tt.reshape(-1, 3).max(0); M2[j].pop('samp', None)
    IDX2 = mt.Indice(S3, M2); bate = False
    for j in js:
        for t2, k2, g2, p2 in mt.avaliar_mesh(j, IDX2):
            B = S3[k2] if t2 == 'S' else M2[k2]
            if B['disc'] != 'ELE' and not (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')) and g2 < mt.TOL: bate = True
    if bate:
        for j in js: M2[j]['tri'], M2[j]['lo'], M2[j]['hi'] = bak[j]; M2[j].pop('samp', None)
    else: manter.add(g)
print('caixas que mantêm a profundidade de hoje (0,80 m):', len(manter))
pickle.dump((S3, M2), open(os.path.join(D, 'ele_plano_final_geo.pkl'), 'wb'))
# instruções = plano (sem as peças desviadas) + desvios
subprocess.run([sys.executable, '-W', 'ignore', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jan_ele_instrucoes.py'), SUF], check=True)
arq = os.path.join(D, 'ele_instrucoes.tsv'); L = [l for l in open(arq, encoding='utf-8').read().splitlines() if l and not (l.startswith('SEG\t') and l.split('\t')[1] in DESV)]
F = lambda v: '%.4f' % v
L2 = []
for l in L:
    r = l.split('	')
    if r[0] == 'CX' and r[1] in manter:
        c = plano['caixas'][r[1]]
        if abs(c['dxy'][0]) + abs(c['dxy'][1]) < 1e-6: continue
        r[4] = '%.4f' % c['prof_hoje']; r[5] = 'R01 18/10: posicao nova (%.1f m)' % np.hypot(*c['dxy']); l = '	'.join(r)
    L2.append(l)
L = L2
for d in sorted(novos, key=lambda d: (d['orig'], d['n'])):
    L.append('\t'.join(['SEG', d['orig'], F(d['a'][0]), F(d['a'][1]), F(d['a'][2]), F(d['b'][0]), F(d['b'][1]), F(d['b'][2]), '' if d['n'] == 0 else '.d%d' % d['n'],
                        'R01 18/10: desvio em planta (' + ('subida do hidrante AH-10' if d['orig'] == '5247455' else 'caixa CX-10 da drenagem' if d['orig'] == '5247479' else 'caixa CX-SDAI-03 do alarme' if d['orig'] == '5247583' else 'poco PVE-10 do esgoto') + ')']))
open(arq, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('instruções finais:', len(L), 'linhas')
