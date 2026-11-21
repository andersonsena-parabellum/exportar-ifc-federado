# -*- coding: utf-8 -*-
"""Figura de conferência do campo no interno dos modelos JAN: piso do IMP as built, campo da SIT (45x25), base do CPS (50x30)
centrada no piso do IMP a -5,38°, drenagem do JAN-DRE e QDLT-CAMPO do JAN-ELE."""
import sys, os, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral")
import dxfgeo, jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
D = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-"
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"
OUT = sys.argv[1]
Rc, oc = JD.tf_compart(JD.meta('ELE', G))
u2i = lambda P: np.c_[P, np.zeros(len(P))] @ Rc.T + oc
C = np.array([90.952, 114.112]); t = np.radians(-5.3818); R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
fig, ax = plt.subplots(figsize=(11, 7.5), dpi=150)
# piso IMP
imp = [os.path.join(G, f) for f in os.listdir(G) if f.startswith('IMP') and f.endswith('_mesh.tsv')][0]
for l in open(imp, encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) > 8 and r[1] == '458119':
        v = np.array(r[8].split(','), dtype=float).reshape(-1, 3, 3)
        for tri in v: ax.fill(tri[:, 0], tri[:, 1], color='#e6e6e6', lw=0)
ax.plot([], [], color='#cfcfcf', lw=6, label='Piso do campo no IMP as built')
# SIT
g = dxfgeo.load(D + 'IMP-PE-URB-001-SIT-R03.dxf'); k = 0
for s in g['segs']:
    P = np.array([q[:2] for q in s['p']])
    if np.linalg.norm(P.mean(0) - np.array([631596.346, 8721147.338])) > 45: continue
    Q = u2i(P); ax.plot(Q[:, 0], Q[:, 1], color='#7b61ff', lw=0.5, label='SIT R03 (campo 45x25)' if k == 0 else None); k = 1
# CPS
g = dxfgeo.load(D + 'CPS-PE-DRE-001-DRG-R01.dxf'); c0 = np.array([27.15, 17.15]); k = 0; kd = 0
for s in g['segs']:
    P = np.array([q[:2] for q in s['p']]); Q = (P - c0) @ R.T + C
    if s['lay'].startswith('ARQ_BASE'): ax.plot(Q[:, 0], Q[:, 1], color='#e65100', lw=0.6, label='CPS R01 (campo 50x30), centrado no IMP' if k == 0 else None); k = 1
    elif s['lay'] == 'AP-Condutos': ax.plot(Q[:, 0], Q[:, 1], color='#00897b', lw=1.2, ls='--', label='Drenagem do CPS R01' if kd == 0 else None); kd = 1
S, M = JD.carregar(g=G, est=None, discs=('DRE', 'ELE')); JD.agrupar_caixas(S, M); k = 0
for s in S:
    if s['disc'] != 'DRE': continue
    if np.linalg.norm((s['a'][:2] + s['b'][:2]) / 2 - C) > 50: continue
    ax.plot([s['a'][0], s['b'][0]], [s['a'][1], s['b'][1]], color='#2e9e5b', lw=1.6, label='Drenagem no JAN-DRE (Daniel)' if k == 0 else None); k = 1
q = [m for m in M if m.get('grupo') == 'QDLT-CAMPO'][0]; c = (q['glo'] + q['ghi']) / 2
ax.plot(c[0], c[1], 's', color='#e0a400', ms=8, label='QDLT-CAMPO no JAN-ELE')
qc = R @ (np.array([12.7, 74.46]) - np.array([43.983, 58.077])) + C; ax.plot(qc[0], qc[1], 'x', color='#e0a400', ms=9, mew=2, label='QDLT-CAMPO do CPS')
ax.set_aspect('equal'); ax.set_xlim(C[0] - 48, C[0] + 48); ax.set_ylim(C[1] - 30, C[1] + 30); ax.legend(fontsize=7, loc='lower left'); ax.grid(alpha=0.2)
ax.set_title('Campo society — Jandaíra (coordenadas internas dos modelos JAN)', fontsize=9)
fig.tight_layout(); fig.savefig(OUT); print('ok', OUT)
