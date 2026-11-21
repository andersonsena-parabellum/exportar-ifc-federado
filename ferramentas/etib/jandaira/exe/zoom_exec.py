# -*- coding: utf-8 -*-
"""Recorte de conferência de uma prancha revisada em volta de pontos UTM: original em cinza, revisada em vermelho por cima.
Uso: python -X utf8 zoom_exec.py <FOLHA (chave do adaptador, ex. DRE-001)> <raio m> E,N[,rótulo] ...
Grava <JAN_EXEC_OUT>/conferencia/zoom_<FOLHA>.png"""
import os, sys, math, json
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC'
folha, raio = sys.argv[1], float(sys.argv[2]); pts = [a.split(',') for a in sys.argv[3:]]
dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
loc = lambda p: R.T @ (np.asarray(p, float) - np.array(t))
rv = os.path.join(OUT, base + '_REVISADO.dwg')
if not os.path.exists(rv[:-4] + '.dxf') or os.path.getmtime(rv[:-4] + '.dxf') < os.path.getmtime(rv):
    import rever
    rever.console(rv, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                  rv + '.dxf.log', {'DXF_OUT': rv[:-4].replace(chr(92), '/') + '.dxf'})
O = ab.entidades(os.path.join(OUT, '_copias', base + '.dxf')); N = ab.entidades(rv[:-4] + '.dxf')
fig, axs = plt.subplots(1, len(pts), figsize=(7 * len(pts), 7), squeeze=False)
for ax, p in zip(axs[0], pts):
    c = loc((float(p[0]), float(p[1])))
    for E_, cor, lw in ((O, '#999999', 1.6), (N, '#d62728', 0.6)):
        for e in E_:
            P = e['pts'] if 'pts' in e else np.array([e['p']])
            if np.min(np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])) > raio * 1.5 and not ('pts' in e and len(P) > 1 and np.min(np.abs(P - c).max(1)) < raio * 3): continue
            if 'txt' in e and e.get('txt'):
                ax.text(e['p'][0], e['p'][1], e['txt'][:30], fontsize=5, color=cor, rotation=math.degrees(e.get('rot', 0)))
            elif len(P) > 1: ax.plot(P[:, 0], P[:, 1], color=cor, lw=lw)
    ax.set_xlim(c[0] - raio, c[0] + raio); ax.set_ylim(c[1] - raio, c[1] + raio); ax.set_aspect('equal')
    ax.set_title(p[2] if len(p) > 2 else f'{p[0]}, {p[1]}', fontsize=9)
os.makedirs(os.path.join(OUT, 'conferencia'), exist_ok=True)
fn = os.path.join(OUT, 'conferencia', f'zoom_{folha}.png'); plt.tight_layout(); plt.savefig(fn, dpi=110); print(fn)
