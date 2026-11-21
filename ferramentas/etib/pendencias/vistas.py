# -*- coding: utf-8 -*-
"""Página de pendências: vistas do modelo de entrega (IFC) em cada ficha — planta (NN_planta.jpg) e perspectiva (NN_3d.jpg), 800 × 514,
ponto no círculo vermelho e os elementos citados na ficha mais grossos e com o código escrito. Generalizado de
exemplo/pendencias/sat_vistas.py. Lê os IFC pela leitura da Revisão de qualidade (revisao/ifc_conf.py) e o terreno do modelo (.npz)."""
import os, sys, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

COR = {'AF': '#1f6fd6', 'ESG': '#8a5a2b', 'AP': '#13a7a7', 'DRE': '#2e8b57', 'ELE': '#e6b800', 'HID': '#e65100', 'SDAI': '#d63fa8'}
NOME = {'AF': 'água fria', 'ESG': 'esgoto', 'AP': 'pluvial', 'DRE': 'drenagem', 'ELE': 'elétrica', 'HID': 'hidrante', 'SDAI': 'alarme'}
COR_NOME = {'AF': 'azul', 'ESG': 'marrom', 'AP': 'ciano', 'DRE': 'verde', 'ELE': 'amarelo', 'HID': 'laranja', 'SDAI': 'rosa'}


def caixa_xy(c):
    mx, my, rot = c.get('mx', c['meia']), c.get('my', c['meia']), c.get('rot', 0.0)
    u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([c['E'], c['N']])
    return np.array([p + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))])


def _nome_cx(c):
    return c['reg']['nome'] if 'reg' in c else c.get('nome', '')


def legenda(discs):
    return ' · '.join(f'{COR_NOME[d]}: {NOME[d]}' for d in COR if d in discs)


def gerar(F, R, T, pasta, log=print):
    """F = fichas (com 'codigos' já resolvidos em nomes); R = leitura dos IFC (ifc_conf.ler); T = Terreno. Grava as imagens em pasta."""
    from preclash import clash as CL
    seg = [s for s in R['seg'] if s['disc'] in COR]; cx = [c for c in R['cx'] if c['disc'] in COR]
    discs = {s['disc'] for s in seg} | {c['disc'] for c in cx}
    for k, f in enumerate(F):
        E0, N0 = f['E'], f['N']; nomes = set(f.get('codigos_nomes', []))
        # planta
        fig, ax = plt.subplots(figsize=(8, 5.14), dpi=100); r = f.get('raio', 12.0)
        for c in cx:
            if abs(c['E'] - E0) > 2 * r or abs(c['N'] - N0) > 2 * r: continue
            Q = caixa_xy(c); dest = _nome_cx(c) in nomes
            ax.fill(Q[:, 0], Q[:, 1], color=COR[c['disc']], alpha=0.6 if dest else 0.25, lw=0)
            ax.plot(Q[:, 0], Q[:, 1], color=COR[c['disc']], lw=1.6 if dest else 0.8)
            ax.text(c['E'], c['N'], _nome_cx(c), fontsize=7.5 if dest else 6.5, ha='center', va='center', clip_on=True, fontweight='bold' if dest else 'normal')
        for s in seg:
            P = s['P']
            if np.min(np.hypot(P[:, 0] - E0, P[:, 1] - N0)) > 2 * r: continue
            dest = s['nome'] in nomes
            ax.plot(P[:, 0], P[:, 1], color=COR[s['disc']], lw=3.2 if dest else 1.6, solid_capstyle='round')
            m = P[len(P) // 2]
            if np.hypot(m[0] - E0, m[1] - N0) < r: ax.text(m[0], m[1], s['nome'], fontsize=7, color=COR[s['disc']], clip_on=True,
                                                         fontweight='bold' if dest else 'normal')
        ax.add_patch(plt.Circle((E0, N0), r * 0.12, fill=False, color='#d32f2f', lw=2.2))
        ax.set_xlim(E0 - r * 1.556, E0 + r * 1.556); ax.set_ylim(N0 - r, N0 + r); ax.set_aspect('equal'); ax.axis('off')
        ax.text(0.01, 0.01, 'Planta do modelo (IFC de entrega) · ' + legenda(discs), transform=ax.transAxes, fontsize=6.5, color='0.35')
        fig.subplots_adjust(0, 0, 1, 1); fig.savefig(os.path.join(pasta, f'{k:02d}_planta.jpg'), dpi=100, pil_kwargs={'quality': 88}); plt.close(fig)
        # 3D
        r3 = f.get('raio3d', 4.5)
        fig = plt.figure(figsize=(8, 5.14), dpi=100); ax = fig.add_subplot(111, projection='3d')
        xs = np.linspace(E0 - r3, E0 + r3, 29); ys = np.linspace(N0 - r3, N0 + r3, 29); X, Y = np.meshgrid(xs, ys)
        Z = T.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape) if T is not None else np.full(X.shape, np.nan)
        z0 = np.nanmean(Z) if np.isfinite(Z).any() else f.get('z', 0.0)
        zc = f.get('z', z0); zlo, zhi = zc - 2.5, zc + 2.5
        if np.isfinite(Z).any(): ax.plot_wireframe(X, Y, np.clip(Z, zlo, zhi), color='0.78', lw=0.4, rstride=2, cstride=2)
        dentro = lambda Q: (np.abs(Q[:, 0] - E0) <= r3) & (np.abs(Q[:, 1] - N0) <= r3) & (Q[:, 2] >= zlo) & (Q[:, 2] <= zhi)
        for c in cx:
            if abs(c['E'] - E0) > r3 or abs(c['N'] - N0) > r3: continue
            Q = caixa_xy(c); zb, zt = max(c['zb'], zlo), min(c['zt'], zhi)
            if zb >= zt: continue
            lw = 2 if _nome_cx(c) in nomes else 1
            for z in (zb, zt): ax.plot(Q[:, 0], Q[:, 1], z, color=COR[c['disc']], lw=lw)
            for q in Q[:4]: ax.plot([q[0], q[0]], [q[1], q[1]], [zb, zt], color=COR[c['disc']], lw=lw)
            if _nome_cx(c) in nomes: ax.text(c['E'], c['N'], zt + 0.3, _nome_cx(c), fontsize=8, fontweight='bold')
        for s in seg:
            P = s['P']
            if np.min(np.hypot(P[:, 0] - E0, P[:, 1] - N0)) > 2 * r3: continue
            Q = CL.amostra(P, 0.1); ok = dentro(Q); Q = np.where(ok[:, None], Q, np.nan)
            dest = s['nome'] in nomes
            ax.plot(Q[:, 0], Q[:, 1], Q[:, 2], color=COR[s['disc']], lw=max(2.0, s['de'] * 30) if dest else max(1.0, s['de'] * 16))
            if dest and ok.any():
                m = Q[np.nonzero(ok)[0][ok.sum() // 2]]; ax.text(m[0], m[1], m[2] + 0.25, s['nome'], fontsize=8, fontweight='bold', color=COR[s['disc']])
        ax.scatter([E0], [N0], [zc], s=200, facecolors='none', edgecolors='#d32f2f', linewidths=2.4)
        ax.set_xlim(E0 - r3, E0 + r3); ax.set_ylim(N0 - r3, N0 + r3); ax.set_zlim(zlo, zhi); ax.set_box_aspect((1, 1, 0.42))
        ax.view_init(elev=30, azim=-60); ax.set_axis_off()
        fig.subplots_adjust(0, 0, 1, 1); fig.savefig(os.path.join(pasta, f'{k:02d}_3d.jpg'), dpi=100, pil_kwargs={'quality': 88}); plt.close(fig)
        log(f'  vistas da ficha {f["n"]}')
