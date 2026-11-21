# -*- coding: utf-8 -*-
"""Diagnóstico: por que as linhas do ARQ_BASE não casam (os círculos casam)?
Mede o vetor (dx,dy) até a ponta mais próxima do SIT e procura deslocamento em bloco por região."""
import json, math, re, collections
import numpy as np
exec(open(r"D:\Projeto Modelagem\FERRAMENTAS\contencao\cnt_georef.py", encoding='utf-8').read().split("random.seed(1)")[0])
T = json.load(open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\CAD_GEORREFERENCIADO\transformacao_CNT_local_para_UTM.json", encoding='utf-8'))
a = math.radians(T['rigid']['rot_deg']); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]); t = np.array(T['rigid']['t'])
ptsB = np.array([p for l in lB for p in l])
ptsA = np.array([p for l in lA for p in l if abs(p[0]) < 1000 and abs(p[1]) < 1000])
PA = (R @ ptsA.T).T + t
print('CNT pontas (local) bbox', ptsA.min(0).round(1), ptsA.max(0).round(1))
print('CNT pontas (UTM)   bbox', PA.min(0).round(1), PA.max(0).round(1))
print('SIT pontas  bbox', ptsB.min(0).round(1), ptsB.max(0).round(1))
print('círculos CNT local bbox', cA[:, :2].min(0).round(1), cA[:, :2].max(0).round(1))
grid = {}
for k, (x, y) in enumerate(ptsB): grid.setdefault((int(x // 2), int(y // 2)), []).append(k)
vec = []
for q in PA[::7]:
    gx, gy = int(q[0] // 2), int(q[1] // 2); best = (9e9, None)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for k in grid.get((gx + dx, gy + dy), ()):
                d = math.hypot(ptsB[k, 0] - q[0], ptsB[k, 1] - q[1])
                if d < best[0]: best = (d, ptsB[k] - q)
    if best[1] is not None: vec.append((q[0], q[1], best[0], best[1][0], best[1][1]))
V = np.array(vec)
print('amostras', len(V), 'sem vizinho em 2-4 m:', (len(PA[::7]) - len(V)))
h = collections.Counter((round(v[3], 2), round(v[4], 2)) for v in V)
print('vetores mais comuns (dx,dy) cm:', [(k, n) for k, n in h.most_common(8)])
# por faixa de y (local) -> mediana da distância
for y0 in range(-30, 180, 20):
    m = (ptsA[::7][:len(V), 1] >= y0) & (ptsA[::7][:len(V), 1] < y0 + 20)
    if m.sum(): print(f'y local {y0:4d}..{y0+20:4d}: n={m.sum():5d} mediana {np.median(V[m,2])*1000:8.1f} mm  <1cm {np.mean(V[m,2]<0.01)*100:5.1f}%')
