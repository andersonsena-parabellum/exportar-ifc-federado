# -*- coding: utf-8 -*-
"""Lista os handles das entidades de topo (espaço do modelo) cuja geometria inteira está a mais de R m de (x0,y0).
INSERT é julgado pela geometria expandida (o ponto de inserção pode estar longe e a geometria cair na obra).
Uso: python -I handles_longe.py <arq.dxf> x0 y0 R  -> imprime handles separados por espaço"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxfgeo
fn, x0, y0, R = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
blocks, model = dxfgeo.parse(fn)
hs, desc = [], []
i = 0
while i < len(model):
    typ, data = model[i]
    j = i + 1
    while j < len(model) and model[j][0] in ('VERTEX', 'SEQEND', 'ATTRIB'):
        j += 1
    d = dxfgeo._first(data)
    if d.get(67, '0').strip() != '1':
        out = {'segs': [], 'circles': [], 'texts': [], 'inserts': [], 'points': []}
        dxfgeo._flatten(blocks, model[i:j], dxfgeo.I, 0.0, '', None, out, 0, set())
        pts = [p for s in out['segs'] for p in s['p']] + [c['c'] for c in out['circles']] + [t['p'] for t in out['texts']] + [p['p'] for p in out['points']]
        if not pts:
            pts = [ins['p'] for ins in out['inserts'][:1]]
        if pts and min(math.hypot(p[0] - x0, p[1] - y0) for p in pts) > R:
            hs.append(d.get(5)); desc.append('%s/%s/%s' % (typ, d.get(8), d.get(2, '')))
    i = j
print(' '.join(hs))
print('# ' + ' | '.join(desc), file=sys.stderr)
