# -*- coding: utf-8 -*-
"""Lista os textos de um dump (UTM) numa faixa em volta do muro: offset (sul +) e estaca.
Uso: cnt_textos_faixa.py dump.tsv [offmin] [offmax]"""
import sys, json, re
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
F = json.load(open(W + r"\cnt_face.json", encoding='utf-8')); O = np.array(F['origem_interna_utm'])
a = np.array(F['segmentos'][0]['p0']) + O; b = np.array(F['segmentos'][-1]['p1']) + O
u = (b - a) / np.linalg.norm(b - a); n = np.array([u[1], -u[0]]); L = np.linalg.norm(b - a)
omin = float(sys.argv[2]) if len(sys.argv) > 2 else -15; omax = float(sys.argv[3]) if len(sys.argv) > 3 else 40
res = []
for ln in open(sys.argv[1], encoding='cp1252', errors='replace'):
    p = ln.rstrip('\n').split('\t')
    if len(p) < 4 or p[0] not in ('TEXT', 'MTEXT'): continue
    m = re.match(r'(-?[\d.]+),(-?[\d.]+) h=\S+ rot=\S+ (.*)$', p[3])
    if not m: continue
    q = np.array([float(m.group(1)), float(m.group(2))])
    if abs(q[0]) < 1e5: continue        # dump em coordenadas locais: ignore
    e = float((q - a) @ u); o = float((q - a) @ n)
    if -20 < e < L + 20 and omin < o < omax: res.append((o, e, p[1], m.group(3)[:70]))
for o, e, lay, t in sorted(res): print(f'off {o:6.1f}  est {e:6.1f}  {lay:22s} {t}')
print(len(res), 'textos')
