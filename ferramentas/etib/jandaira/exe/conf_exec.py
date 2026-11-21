# -*- coding: utf-8 -*-
"""Conferência das pranchas no padrão de executivo final: compara o DXF da cópia original com o DXF do *_REVISADO.dwg (por handle)
e desenha, para cada grupo de mudanças, um recorte: prancha em cinza, o que saiu em azul tracejado, o que entrou ou andou em vermelho
(textos novos escritos). Gera EXECUTIVO_R02/conferencia/<prancha>_conferencia.png e um resumo por prancha.
Uso: python -X utf8 conf_exec.py [prancha ...]   (sem argumento: todas as *_REVISADO.dwg)"""
import os, sys, glob, math, json, collections
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import asbuilt as ab, rever
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02'; CONF = os.path.join(OUT, 'conferencia'); os.makedirs(CONF, exist_ok=True)


def dxf(dwg):
    fn = dwg[:-4] + '.dxf'
    if not os.path.exists(fn) or os.path.getmtime(fn) < os.path.getmtime(dwg):
        rever.console(dwg, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                      dwg + '.dxf.log', {'DXF_OUT': fn.replace('\\', '/')})
    return ab.entidades(fn)


def geo(e): return e['pts'] if 'pts' in e else np.array([e['p']])


def mudou(a, b):
    if a['typ'] != b['typ']: return True
    A, B = geo(a), geo(b)
    if A.shape != B.shape: return True
    return np.abs(A - B).max() > 1e-3 or a.get('txt') != b.get('txt') or abs(a.get('rot', 0) - b.get('rot', 0)) > 1e-3


def grupos(P, r=10.0):
    lab = -np.ones(len(P), int); k = 0
    for i in range(len(P)):
        if lab[i] >= 0: continue
        fila = [i]; lab[i] = k
        while fila:
            j = fila.pop(); d = np.hypot(*(P - P[j]).T)
            for m in np.where((d < r) & (lab < 0))[0]: lab[m] = k; fila.append(m)
        k += 1
    return lab


def conferir(rev):
    base = os.path.basename(rev)[:-len('_REVISADO.dwg')]
    O = ab.entidades(os.path.join(OUT, '_copias', base + '.dxf')); N = dxf(rev)
    o = {e['h']: e for e in O}; n = {e['h']: e for e in N}
    sai = [o[h] for h in o if h not in n]; novo = [n[h] for h in n if h not in o]; mov = [n[h] for h in n if h in o and mudou(o[h], n[h])]
    alt = sai + novo + mov
    res = dict(prancha=base, saem=len(sai), entram=len(novo), mudam=len(mov))
    if not alt: print(base, res); return res
    C = np.array([geo(e).mean(0) for e in alt]); lab = grupos(C)
    ng = lab.max() + 1; cols = min(4, ng); rows = math.ceil(ng / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(6 * cols, 6 * rows), squeeze=False)
    for k in range(ng):
        ax = axs[k // cols][k % cols]; idx = np.where(lab == k)[0]
        lo, hi = C[idx].min(0) - 4, C[idx].max(0) + 4; w = max(hi - lo); c = (lo + hi) / 2; lo, hi = c - w / 2, c + w / 2
        dentro = lambda P: (P[:, 0].max() > lo[0]) & (P[:, 0].min() < hi[0]) & (P[:, 1].max() > lo[1]) & (P[:, 1].min() < hi[1])
        for e in N:
            if 'pts' in e and dentro(e['pts']): ax.plot(e['pts'][:, 0], e['pts'][:, 1], color='#bdbdbd', lw=0.4)
            elif 'p' in e and e['typ'] != 'INSERT' and lo[0] < e['p'][0] < hi[0] and lo[1] < e['p'][1] < hi[1]:
                ax.text(e['p'][0], e['p'][1], str(e.get('txt', ''))[:24], fontsize=4, color='#9e9e9e')
        for e in sai:
            if 'pts' in e and dentro(e['pts']): ax.plot(e['pts'][:, 0], e['pts'][:, 1], color='#1e88e5', lw=0.9, ls='--')
            elif 'p' in e and lo[0] < e['p'][0] < hi[0] and lo[1] < e['p'][1] < hi[1]: ax.plot(*e['p'], 'x', color='#1e88e5', ms=4)
        for e in novo + mov:
            if 'pts' in e and dentro(e['pts']): ax.plot(e['pts'][:, 0], e['pts'][:, 1], color='#d32f2f', lw=1.1)
            elif 'p' in e and lo[0] < e['p'][0] < hi[0] and lo[1] < e['p'][1] < hi[1]:
                ax.plot(*e['p'], 'o', color='#d32f2f', ms=2)
                if e['typ'] != 'INSERT': ax.text(e['p'][0], e['p'][1], str(e.get('txt', ''))[:40], fontsize=5.5, color='#b71c1c', fontweight='bold')
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title('%d: %d saem, %d entram/andam' % (k + 1, sum(1 for i in idx if alt[i] in sai), sum(1 for i in idx if alt[i] not in sai)), fontsize=8)
    for k in range(ng, rows * cols): axs[k // cols][k % cols].axis('off')
    fig.suptitle(base + ' — azul tracejado: sai; vermelho: entra ou anda', fontsize=10); fig.tight_layout()
    png = os.path.join(CONF, base + '_conferencia.png'); fig.savefig(png, dpi=95); plt.close(fig)
    res.update(grupos=int(ng), png=png); print(base, res); return res


if __name__ == '__main__':
    alvos = sys.argv[1:] or [os.path.basename(f)[:-len('_REVISADO.dwg')] for f in glob.glob(os.path.join(OUT, '*_REVISADO.dwg'))]
    R = [conferir(os.path.join(OUT, a + '_REVISADO.dwg')) for a in alvos]
    json.dump(R, open(os.path.join(CONF, 'resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
