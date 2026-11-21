# -*- coding: utf-8 -*-
"""Onde está o campo: SIT R03 (UTM) -> interno dos modelos JAN; e o que o IMP as built tem nessa região."""
import sys, os, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"
R, o = JD.tf_compart(JD.meta('ELE', G))
def utm_para_interno(E, N, z=0.0): return np.array([E, N, z]) @ R.T + o
c = utm_para_interno(631596.346, 8721147.338); print('centro do campo da SIT (45x25) no interno:', c.round(3))
p2 = utm_para_interno(631596.346 + np.cos(np.radians(25.7107)), 8721147.338 + np.sin(np.radians(25.7107)))
print('ângulo do eixo longo no interno: %.4f°' % np.degrees(np.arctan2(p2[1] - c[1], p2[0] - c[0])))
# IMP: o que tem perto do campo
for f in os.listdir(G):
    if f.startswith('IMP') and f.endswith('_mesh.tsv'): imp = os.path.join(G, f)
cats = collections.Counter(); perto = []
for l in open(imp, encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) < 9 or not r[8]: continue
    v = np.array(r[8].split(','), dtype=float).reshape(-1, 3); lo, hi = v.min(0), v.max(0); cc = (lo + hi) / 2
    cats[r[2]] += 1
    if np.linalg.norm(cc[:2] - c[:2]) < 45: perto.append((r[2], r[3][:50], (hi - lo).round(2), cc.round(2)))
print('categorias do IMP:', dict(cats))
for p in sorted(perto, key=lambda p: -p[2][0] * p[2][1])[:25]: print('  ', p)
