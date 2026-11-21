# -*- coding: utf-8 -*-
"""Pontos de amostragem do terreno numa faixa larga dos dois lados do muro (offset + = sul)."""
import json, sys
import numpy as np
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
F = json.load(open(W + r"\cnt_face.json", encoding='utf-8'))
OFFS = [float(v) for v in sys.argv[1].split(',')]
passo = float(sys.argv[2]); out = sys.argv[3]
k = 0
with open(W + '\\' + out, 'w', encoding='utf-8') as f:
    for s in F['segmentos']:
        p0 = np.array(s['p0']); u = np.array(s['u']); n = np.array(s['n_sul'])
        for d in np.arange(0, s['L'], passo):
            for o in OFFS:
                q = p0 + u * d + n * o
                f.write(f"{k};{s['secao']};{s['est0'] + d:.3f};{o};{q[0]:.4f};{q[1]:.4f}\n"); k += 1
print(k, out)
