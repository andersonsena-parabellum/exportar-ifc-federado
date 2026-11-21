# -*- coding: utf-8 -*-
"""Confere os executivos revisados (COMPAT-R01): exporta cada cópia para DXF (accoreconsole, um por vez), lê e desenha
PNG da planta com os layers COMPAT-R01-* por cima do desenho original (visão geral + recorte de cada nuvem).
Saída: ETIB-CATU/EXECUTIVO_REVISADO/conferencia/<prancha>_*.png
Uso: .venv/Scripts/python.exe -X utf8 georef/exec_conferir.py"""
import os, sys, glob, subprocess
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from dxf_ler import ler          # noqa: E402
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

SAI = r'D:\Projeto Modelagem\ETIB-CATU\EXECUTIVO_REVISADO'
WRK = os.path.join(AQUI, 'work', 'CATU', 'exec')
CONF = os.path.join(SAI, 'conferencia')
COR = {'COMPAT-R01-REMOVIDO': ('#777777', (0, (4, 2)), 1.6), 'COMPAT-R01-NOVO': ('#e00000', '-', 1.6), 'COMPAT-R01-NUVEM': ('#ff4d4d', '-', 0.8),
       'COMPAT-R01-MERGULHO': ('#0099cc', '-', 0.8), 'COMPAT-R01-NOTAS': ('#e00000', '-', 0.5)}


def dxfout(dwg):
    out = os.path.join(WRK, os.path.basename(dwg)[:-4] + '.dxf')
    scr = os.path.join(AQUI, 'dxfout.scr'); log = out + '.log'
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                        f"& '{os.path.join(AQUI, 'run_acc.ps1')}' -Dwg '{dwg}' -Scr '{scr}' -Log '{log}' -TimeoutSec 600 -EnvVars @{{DXF_OUT='{out.replace(chr(92), '/')}'}}"],
                       capture_output=True, text=True)
    print(r.stdout.strip(), flush=True)
    return out


def desenhar(D, ax, lim=None, base_alpha=0.35):
    for d in D:
        if d['tipo'] not in ('LINE', 'PL', 'CIRCLE', 'ARC', 'TEXT'): continue
        p = d['pts']
        if lim and (p[:, 0].max() < lim[0] or p[:, 0].min() > lim[2] or p[:, 1].max() < lim[1] or p[:, 1].min() > lim[3]): continue
        if d['layer'] in COR:
            c, ls, lw = COR[d['layer']]
            if d['tipo'] == 'TEXT': ax.text(p[0, 0], p[0, 1], d.get('texto', ''), color=c, fontsize=7, clip_on=True)
            elif d['tipo'] == 'CIRCLE': ax.add_patch(plt.Circle(p[0, :2], d['r'], fill=False, ec=c, lw=lw))
            else: ax.plot(p[:, 0], p[:, 1], color=c, ls=ls, lw=lw)
        elif d['tipo'] in ('LINE', 'PL') and lim is not None:
            ax.plot(p[:, 0], p[:, 1], color='k', lw=0.3, alpha=base_alpha)


def main():
    os.makedirs(CONF, exist_ok=True)
    for dwg in sorted(glob.glob(os.path.join(SAI, '*_COMPAT-R01.dwg'))):
        nome = os.path.basename(dwg)[:-4]
        D = ler(dxfout(dwg), cache=False)
        nv = [d for d in D if d['layer'] == 'COMPAT-R01-NUVEM' and d['tipo'] == 'PL']
        rot = [d for d in D if d['layer'] == 'COMPAT-R01-NUVEM' and d['tipo'] == 'TEXT']
        P = np.vstack([d['pts'][:, :2] for d in D if d['layer'].startswith('COMPAT-R01') and d['layer'] != 'COMPAT-R01-NOTAS'] or [np.zeros((1, 2))])
        lo, hi = P.min(0) - 10, P.max(0) + 10
        fig, ax = plt.subplots(figsize=(16, 16)); desenhar(D, ax, (lo[0], lo[1], hi[0], hi[1]), 0.15)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_aspect('equal'); ax.set_title(nome + ' — visão geral das alterações')
        fig.savefig(os.path.join(CONF, nome + '_geral.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
        for k, c in enumerate(nv[:12], 1):
            q0, q1 = c['pts'][:, :2].min(0) - 3, c['pts'][:, :2].max(0) + 3
            fig, ax = plt.subplots(figsize=(9, 9)); desenhar(D, ax, (q0[0], q0[1], q1[0], q1[1]))
            ax.set_xlim(q0[0], q1[0]); ax.set_ylim(q0[1], q1[1]); ax.set_aspect('equal')
            r = min(rot, key=lambda t: np.hypot(*(t['pts'][0, :2] - c['pts'][:, :2].max(0)))) if rot else None
            ax.set_title(f"{nome} — {r['texto'] if r else k}")
            fig.savefig(os.path.join(CONF, f"{nome}_{r['texto'] if r else k}.png"), dpi=100, bbox_inches='tight'); plt.close(fig)
        print(nome, len(nv), 'nuvens', flush=True)


if __name__ == '__main__':
    main()
