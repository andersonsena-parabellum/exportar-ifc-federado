# -*- coding: utf-8 -*-
"""Fase C: deslocamento em GRUPO das linhas de água potável que passam por caixas/poços (os tubos ligados andam juntos no Revit).
Linha E (x≈63,4): AL-20 + AL-04 + toco AL-19.t; linha S (y≈6,7): AL-21 + AL-22; reúso AR-16 (y≈5,8) sozinho. Testa um deslocamento único por linha."""
import sys, os, math, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
D = os.path.dirname(JD.G); GX = os.path.join(D, 'geo_exec')
SEG, MESH = JD.carregar(g=GX, est='daniel'); JD.agrupar_caixas(SEG, MESH)
IGN = {j for j, M in enumerate(MESH) if M['disc'] == 'AF' and M['cat'].startswith(('Conex', 'Acess'))}
IDX = mt.Indice(SEG, MESH)
GR = {'E': ({'AL-20', 'AL-04', 'AL-19.t'}, 'x'), 'S': ({'AL-21', 'AL-22'}, 'y'), 'R': ({'AR-16'}, 'y')}
def pot(s): return 'Alimenta' in s['sis'] or 'Pot' in s['sis']
def custo(ids):
    c = 0
    for i in ids:
        s = SEG[i]
        for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
            if t == 'M' and j in IGN: continue
            B = SEG[j] if t == 'S' else MESH[j]
            if B['disc'] in ('AF',) or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes', 'Quadro estrutural')): continue
            # colisão com elétrica/alarme resolve-se depois com mergulho: pesa pouco
            if B['disc'] in ('ELE', 'SDAI') and pot(s): c += 5 if g < mt.TOL else 1; continue
            if B['disc'] in ('ELE', 'SDAI') and not pot(s): c += 5 if g < mt.TOL else 1; continue
            c += 100 if g < mt.TOL else (3 if g < 0.10 else 1)
    return c
res = {}
for nome, (tr, eixo) in GR.items():
    ids = [i for i, s in enumerate(SEG) if s['disc'] == 'AF' and s['trecho'] in tr]
    best = None
    for o in np.round(np.arange(-2.5, 2.51, 0.25), 2):
        d = (float(o), 0.0) if eixo == 'x' else (0.0, float(o))
        for i in ids: mt.mover(i, 0.0, IDX, d)
        c = custo(ids) + 3 * abs(o)
        if best is None or c < best[0]: best = (c, d)
    for i in ids: mt.mover(i, 0.0, IDX, best[1])
    res[nome] = dict(trechos=sorted(tr), ids=[SEG[i]['id'] for i in ids], dxy=best[1], custo=best[0])
    print(nome, sorted(tr), 'deslocamento', best[1], 'custo', round(best[0], 1))
json.dump(res, open(os.path.join(D, 'af_grupos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
