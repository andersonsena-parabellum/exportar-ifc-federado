# -*- coding: utf-8 -*-
"""Gera compat_R01/ele_instrucoes.tsv (lido por FERRAMENTAS/jandaira/faseB_ele_aplicar.cs) a partir do plano da elétrica.
Uso: jan_ele_instrucoes.py [sufixo do plano, ex.: _atual]"""
import sys, os, json, pickle, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
D = os.path.dirname(JD.G); GX = os.path.join(D, 'geo_exec'); SUF = sys.argv[1] if len(sys.argv) > 1 else ''
plano = json.load(open(os.path.join(D, 'ele_plano' + SUF + '.json'), encoding='utf-8'))
S2, M2 = pickle.load(open(os.path.join(D, 'ele_plano' + SUF + '_geo.pkl'), 'rb'))
SEG0, _ = JD.carregar(g=GX, est=None, discs=('ELE',)); orig = {s['id']: s for s in SEG0}
F = lambda v: '%.4f' % v
lin = []; nmod = ncop = 0
sub = {}
for s in S2:
    if s.get('run') is not None and '~' in s['id']: sub.setdefault(s['run'], []).append(s)
for k, r in enumerate(plano['corridas']):
    pecas = r['pecas']; V = np.array(r['vertices'])
    sv = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(V[:, :2], axis=0), axis=1))])
    # limites das peças originais ao longo da corrida
    lim = [0.0]
    for pid, inv in pecas: lim.append(lim[-1] + np.linalg.norm(orig[pid]['b0'][:2] - orig[pid]['a0'][:2]))
    segs = sorted(sub.get(k, []), key=lambda s: int(s['id'].split('.')[-1]))
    if len(segs) != len(V) - 1: print('corrida', k, 'sub-segmentos', len(segs), 'vertices', len(V)); continue
    mudou = any(abs(s['a'][2] - orig[pecas[0][0]]['a0'][2]) > 0.003 for s in segs) or len(segs) > len(pecas)
    if not mudou and all(np.allclose(s['a'], s['a0']) for s in segs): pass
    cont = {}
    for m, s in enumerate(segs):
        smid = (sv[m] + sv[m + 1]) / 2; p = min(int(np.searchsorted(lim, smid) - 1), len(pecas) - 1); pid = pecas[max(p, 0)][0]
        n = cont.get(pid, 0); cont[pid] = n + 1
        o = orig[pid]
        if n == 0 and np.allclose(s['a'], o['a0'], atol=0.002) and np.allclose(s['b'], o['b0'], atol=0.002) and sum(1 for x in segs if True) == len(pecas): continue
        dz = min(s['a'][2], s['b'][2]) - min(o['a0'][2], o['b0'][2])
        nota = 'R01 18/10: eixo ' + ('%.2f' % (147 + min(s['a'][2], s['b'][2]))).replace('.', ',') + (' (mergulho local)' if len(segs) > len(pecas) else '')
        lin.append('\t'.join(['SEG', pid, F(s['a'][0]), F(s['a'][1]), F(s['a'][2]), F(s['b'][0]), F(s['b'][1]), F(s['b'][2]), '' if n == 0 else '.m%d' % n, nota]))
        if n == 0: nmod += 1
        else: ncop += 1
# eletrodutos fora das corridas cuja ponta acompanhou uma caixa movida
for s in S2:
    if s['disc'] == 'ELE' and '~' not in s['id'] and s['id'] in orig:
        o = orig[s['id']]
        if not (np.allclose(s['a'], o['a0'], atol=0.002) and np.allclose(s['b'], o['b0'], atol=0.002)):
            lin.append('\t'.join(['SEG', s['id'], F(s['a'][0]), F(s['a'][1]), F(s['a'][2]), F(s['b'][0]), F(s['b'][1]), F(s['b'][2]), '', 'R01 18/10: ponta acompanha caixa movida'])); nmod += 1
ncx = 0
for g, c in plano['caixas'].items():
    dx, dy = c['dxy']; mov = math.hypot(dx, dy) > 1e-6
    if c['prof'] is None: continue
    if not mov and abs(c['prof'] - c['prof_hoje']) < 0.005: continue
    nota = 'R01 18/10: ' + ('posicao nova (%.1f m); ' % math.hypot(dx, dy) if mov else '') + ('profundidade %.2f' % c['prof']).replace('.', ',')
    lin.append('\t'.join(['CX', g, F(dx), F(dy), F(c['prof']), nota])); ncx += 1
open(os.path.join(D, 'ele_instrucoes.tsv'), 'w', encoding='utf-8').write('\n'.join(lin) + '\n')
print(f'instruções: eletrodutos redesenhados {nmod} | pedaços novos {ncop} | caixas {ncx}')
