# -*- coding: utf-8 -*-
"""Terreno ORIGINAL (levantamento TOP-001, UTM) ao longo do muro: cotas pontuais (TOP-COTAS) interpoladas
por IDW nos dois lados da face, para comparar com o H das seções e com o IMP as built.
Saída: work/top_ao_longo_muro.csv + resumo no console."""
import json, re, sys, collections, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
NUM = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')
pts = []; tipos = collections.Counter()
P3 = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*),(-?\d+\.?\d*)')
for ln in open(W + r"\dumpz_TOP.tsv", encoding='cp1252', errors='replace'):
    p = ln.rstrip('\n').split('\t')
    if len(p) < 3: continue
    tipos[(p[0], p[1])] += 1
    if p[0] == 'INSERT' and p[1] in ('TOP-COTAS', '_TG', 'TG'):
        m = P3.match(p[2])
        if m and float(m.group(3)) > 100: pts.append(tuple(map(float, m.groups())))
    elif p[0] == 'POLYLINE' and p[1] == 'CURVAS':
        for x, y, z in P3.findall(p[2])[::3]: pts.append((float(x), float(y), float(z)))
print('tipos', [(k, n) for k, n in tipos.most_common(12)])
print('pontos com cota', len(pts))
P = np.array(pts)
print('faixa de cotas', P[:, 2].min(), P[:, 2].max())
F = json.load(open(W + r"\cnt_face.json", encoding='utf-8'))
ORIG = np.array(F['origem_interna_utm'])


def idw(q, r=8.0, k=6):
    d = np.hypot(P[:, 0] - q[0], P[:, 1] - q[1]); idx = np.argsort(d)[:k]
    if d[idx[0]] > r: return float('nan'), d[idx[0]]
    w = 1 / np.maximum(d[idx], 0.05) ** 2
    return float((P[idx, 2] * w).sum() / w.sum()), float(d[idx[0]])

out = open(W + r"\top_ao_longo_muro.csv", 'w', encoding='utf-8')
out.write('secao;estaca;off;x_int;y_int;z_top;dist_cota_mais_prox\n')
print('sec   est   z(-4)  z(-1)  z(+1.5) z(+4)   dif(+4 − −4)   H proj')
for s in F['segmentos']:
    p0 = np.array(s['p0']) + ORIG; u = np.array(s['u']); n = np.array(s['n_sul'])
    for d in np.arange(0, s['L'] + 0.01, 2.0):
        zz = {}
        for o in (-8, -4, -1, 1.5, 4, 8):
            q = p0 + u * d + n * o; z, dm = idw(q); zz[o] = z
            out.write(f"{s['secao']};{s['est0']+d:.2f};{o};{q[0]-ORIG[0]:.3f};{q[1]-ORIG[1]:.3f};{z:.3f};{dm:.2f}\n")
        if int(d) % 6 == 0:
            print(s['secao'], f"{s['est0']+d:6.1f} {zz[-4]:7.2f} {zz[-1]:7.2f} {zz[1.5]:7.2f} {zz[4]:7.2f}   {zz[4]-zz[-4]:6.2f}        {s['H']:.2f}")
out.close()
