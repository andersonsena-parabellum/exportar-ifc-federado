# -*- coding: utf-8 -*-
"""Extrai a rede elétrica do campo (CPS EL-001 R01) já no interno dos modelos JAN: eletrodutos (layer 02. F_ELETRODUTO PISO),
caixas, postes/quadro (blocos) e textos de bitola. Uso: python -I ele_cps.py [--csv saida]"""
import sys, json, math, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); import dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
DXF = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R01.dxf"
T = json.load(open(r"D:\Projeto Modelagem\ETIB-JANDAIRA\CAD_GEORREFERENCIADO\transformacao_CPS_EL-001-ELG-R01_local_para_UTM.json", encoding='utf-8'))
t = math.radians(T['rot_int_graus']); R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]]); tt = np.array(T['t_int'])
I = lambda p: R @ np.asarray(p[:2]) + tt
g = dxfgeo.load(DXF)
lay = collections.Counter(s['lay'] for s in g['segs']); print('layers:', dict(lay))
print('blocos:', collections.Counter((i['name'], i['lay']) for i in g['inserts']).most_common(20))
txt = collections.Counter(x['t'][:25] for x in g['texts']); print('textos:', txt.most_common(40))
el = [s for s in g['segs'] if 'ELETRODUTO' in s['lay'].upper()]
L = sum(np.linalg.norm(np.diff(np.array([q[:2] for q in s['p']]), axis=0), axis=1).sum() for s in el)
print('eletrodutos: %d polilinhas, %.1f m' % (len(el), L))
for s in el: P = np.array([I(q) for q in s['p']]); print('   ', s['path'][:30], len(P), P[0].round(2), P[-1].round(2))
for s in el: print('vértices:', [tuple(I(q).round(2)) for q in s['p']])
for i in g['inserts']: print('bloco', i['name'], tuple(I(i['p']).round(2)), 'rot %.1f' % i['rot'])
for x in g['texts']:
    if 'CX' in x['t'] or 'QDLT' in x['t'] or '%%C' in x['t']: print('texto', x['t'][-20:], tuple(I(x['p']).round(2)))
