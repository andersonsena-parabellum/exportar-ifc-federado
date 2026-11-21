# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — imagens das colisões que sobram, para ver no tablet: para cada uma, planta, corte ao longo do tubo e 3D,
com a forma REAL da estrutura as built (malha do RVT) e os tubos do cenário de entrega (PRECLASH_R02/JAN.json, AD).
Grava RELATORIOS/EXECUTIVO_R03_IFC/conferencia/colisao_<trecho>.png (JAN_PRE = pasta da rodada, JAN_IMG_OUT = saída). Uso: python imagens_colisoes.py"""
import os, sys, json, math
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\ifc'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
sys.stdout.reconfigure(encoding='utf-8')
import jan_modelo as JM, jan_dados as JD
from preclash.terreno import Terreno
PRE = os.environ.get('JAN_PRE', r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02')
OUT = os.environ.get('JAN_IMG_OUT', r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\conferencia'); os.makedirs(OUT, exist_ok=True)
G0 = JM.G0; O = (631578.10, 8721003.57)
T = JD.Terreno(g=G0); aj = JM.Ajuste(T, JM.pontos_base(json.load(open(JM.ROT_JSON, encoding='utf-8'))))
TER = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\jandaira_terreno.npz')
links = JD.mapa_links('ELE', G0)
J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8')); zr = J['zref']


def malha(eid):
    _, tag, rid = eid.split(':')
    m = JD.meta(tag, G0); nome = m['titulo'].split('__', 1)[-1]
    R, o = links.get(nome) or links.get(nome.replace('-ECC-', '-FUN-').replace('-EMT-', '-FUN-'))
    for l in open(os.path.join(G0, tag + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 9 or r[1] != rid: continue
        v = np.array(r[8].split(','), dtype=float).reshape(-1, 3)
        lo, hi = v.min(0), v.max(0); c = R @ ((lo + hi) / 2) + o; d = aj(c[0], c[1])
        W = np.array([R @ p + o for p in v]); U = JM.utm(W); U[:, 2] = 147 + W[:, 2] + d
        return U.reshape(-1, 3, 3), r[2], r[3].split(' : ')[0]
    return None, None, None


def hull(P):
    P = np.unique(np.round(np.asarray(P, float), 5), axis=0)
    if len(P) < 3: return P
    P = P[np.lexsort((P[:, 1], P[:, 0]))]; cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in P[::-1]:
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def corte_vertical(TRI, a, u):
    """seção da malha pelo plano vertical que passa em a com direção u (planta): pontos (s, z)."""
    n = np.array([-u[1], u[0]]); pts = []
    for t in TRI:
        d = [(p[:2] - a) @ n for p in t]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if d[i] * d[j] <= 0 and abs(d[i] - d[j]) > 1e-12:
                s = d[i] / (d[i] - d[j]); p = t[i] + (t[j] - t[i]) * s
                pts.append([(p[:2] - a) @ u, p[2]])
    return hull(pts) if len(pts) >= 3 else None


def pecas_perto(c0, raio=3.5):
    out = []
    for c in J['caixas']:
        if not c['id'].startswith('EST:'): continue
        if math.hypot(c['x'] + O[0] - c0[0], c['y'] + O[1] - c0[1]) > raio + c['m']: continue
        TRI, cat, nome = malha(c['id'])
        if TRI is not None and TRI[:, :, 2].min() < 147.6: out.append((c['id'], TRI, cat, nome))
    return out


def tubos_perto(c0, raio=6.0):
    out = []
    for e in J['elementos']:
        if 'AD' not in e['cen']: continue
        P = np.array((e['sol'] or {}).get('AD') or e['p'], float); P[:, 0] += O[0]; P[:, 1] += O[1]; P[:, 2] += zr
        if np.min(np.hypot(P[:, 0] - c0[0], P[:, 1] - c0[1])) < raio: out.append((e, P))
    return out


COR = {'DRE': '#1f77b4', 'ESG': '#8c564b', 'AF': '#17becf', 'HID': '#d62728', 'SDAI': '#e377c2', 'ELE': '#ff7f0e'}


def figura(titulo, alvo, ponto, texto, fn, foco=None):
    c0 = np.array(ponto[:2], float)
    pecas = pecas_perto(c0); tubos = tubos_perto(c0)
    e_alvo, P_alvo = next((e, P) for e, P in tubos if e['trecho'] == alvo)
    fig = plt.figure(figsize=(18, 7.4), dpi=110)
    fig.suptitle(titulo, fontsize=15, fontweight='bold', x=0.01, y=0.985, ha='left')
    fig.text(0.01, 0.935, texto, fontsize=10.5, ha='left', va='top')
    # ------------------------------------------------ planta
    ax = fig.add_axes([0.03, 0.05, 0.30, 0.74]); ax.set_title('Planta (m, em volta da colisão)', fontsize=11)
    loc = lambda P: np.asarray(P)[..., :2] - c0
    for eid, TRI, cat, nome in pecas:
        H = hull(TRI.reshape(-1, 3)[:, :2]) - c0
        cor = '#f4a261' if 'Funda' in cat else ('#6c757d' if 'Pilar' in cat else '#adb5bd')
        ax.fill(H[:, 0], H[:, 1], color=cor, alpha=0.55 if 'Funda' in cat else 0.85, lw=0.8, ec='#555')
    for e, P in tubos:
        Q = loc(P); lw = max(2.0, e['de'] * 40); cor = COR.get(e['disc'], '#333')
        ax.plot(Q[:, 0], Q[:, 1], color=cor, lw=lw * (1.6 if e['trecho'] == alvo else 1.0), alpha=1.0 if e['disc'] in ('DRE', 'ESG') else 0.55, solid_capstyle='round')
        m = Q[len(Q) // 2]
        if e['disc'] in ('DRE', 'ESG') and np.hypot(*m) < 5: ax.text(m[0], m[1], e['trecho'], fontsize=8, color=cor, fontweight='bold')
    for c in J['caixas']:
        if c['disc'] in ('DRE', 'ESG') and math.hypot(c['x'] + O[0] - c0[0], c['y'] + O[1] - c0[1]) < 6:
            ax.plot(c['x'] + O[0] - c0[0], c['y'] + O[1] - c0[1], 's', ms=11, mfc='white', mec=COR[c['disc']], mew=2)
            ax.text(c['x'] + O[0] - c0[0] + 0.25, c['y'] + O[1] - c0[1] + 0.25, c['id'].split(':')[1], fontsize=8)
    ax.add_patch(plt.Circle((0, 0), 0.35, fill=False, ec='red', lw=2.2))
    ax.set_xlim(-4, 4); ax.set_ylim(-4, 4); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.text(-3.8, -3.8, 'laranja = sapata (forma real)   cinza = pilar/viga   círculo vermelho = colisão', fontsize=8)
    # ------------------------------------------------ corte ao longo do tubo
    ax2 = fig.add_axes([0.38, 0.10, 0.29, 0.66]); ax2.set_title(f'Corte ao longo do {alvo}', fontsize=11)
    a = P_alvo[0, :2]; u = P_alvo[-1, :2] - a; L = np.hypot(*u); u = u / L
    s = np.array([(p[:2] - a) @ u for p in P_alvo]); r = e_alvo['de'] / 2
    for eid, TRI, cat, nome in pecas:
        S = corte_vertical(TRI, a, u)
        if S is not None and len(S) >= 3:
            cor = '#f4a261' if 'Funda' in cat else '#6c757d'
            ax2.fill(S[:, 0], S[:, 1], color=cor, alpha=0.7, ec='#555', lw=0.8)
            ax2.text(S[:, 0].mean(), S[:, 1].min() + 0.05, 'sapata' if 'Funda' in cat else ('pilar' if 'Pilar' in cat else 'viga'), fontsize=9, ha='center')
    ss = np.linspace(min(s.min(), -1) - 1, max(s.max(), L) + 1, 120)
    zt = np.array(TER.z(np.array([a + u * x for x in ss])), float)
    ax2.plot(ss, zt, color='#2a9d8f', lw=2, label='terreno'); ax2.fill_between(ss, zt, zt + 0.15, color='#2a9d8f', alpha=0.15)
    ax2.fill_between(s, P_alvo[:, 2] - r, P_alvo[:, 2] + r, color=COR[e_alvo['disc']], alpha=0.9, label=f'{alvo} (Ø {e_alvo["de"] * 1000:.0f} mm)')
    if foco is not None:
        sf = (np.array(foco[:2]) - a) @ u; ax2.axvline(sf, color='red', ls='--', lw=1.2); ax2.text(sf, zt.max() + 0.05, 'colisão', color='red', ha='center', fontsize=9)
    ax2.set_xlabel('distância ao longo do tubo (m)'); ax2.set_ylabel('cota (m)'); ax2.grid(alpha=0.3); ax2.legend(fontsize=8, loc='lower left')
    ax2.set_xlim(-1.5, L + 1.5); ax2.set_ylim(float(np.nanmin(zt)) - 2.2, float(np.nanmax(zt)) + 0.5)
    ex = 1.0 if L < 6 else 2.5
    ax2.set_aspect(ex, adjustable='box')
    if ex > 1: ax2.set_title(f'Corte ao longo do {alvo} (escala vertical {ex:.1f}x)'.replace('.', ','), fontsize=11)
    # ------------------------------------------------ 3D
    ax3 = fig.add_axes([0.68, 0.02, 0.32, 0.78], projection='3d'); ax3.set_title('3D', fontsize=11)
    for eid, TRI, cat, nome in pecas:
        V = TRI - np.array([c0[0], c0[1], 0])
        cor = '#f4a261' if 'Funda' in cat else ('#6c757d' if 'Pilar' in cat else '#adb5bd')
        ax3.add_collection3d(Poly3DCollection(V, facecolor=cor, edgecolor='none', alpha=0.45 if 'Funda' in cat else 0.7))
    for e, P in tubos:
        if e['disc'] not in ('DRE', 'ESG'): continue
        Q = P - np.array([c0[0], c0[1], 0])
        ax3.plot(Q[:, 0], Q[:, 1], Q[:, 2], color=COR[e['disc']], lw=max(3, e['de'] * 45) * (1.5 if e['trecho'] == alvo else 1))
    zc = P_alvo[:, 2].mean()
    ax3.set_xlim(-3, 3); ax3.set_ylim(-3, 3); ax3.set_zlim(zc - 1.6, zc + 1.4); ax3.view_init(elev=22, azim=-60)
    ax3.set_box_aspect((1, 1, 0.5)); ax3.set_xticks([]); ax3.set_yticks([])
    fig.savefig(fn, dpi=110); plt.close(fig); print(fn)


figura('DRE-133 × sapata do BP4 (sob o bloco, a ~9 m da CX-33)', 'DRE-133', (631582.577, 8721101.369),
       'A junção do DRE-133 com o DRE-126 fica sobre a sapata e o DRE-133 passa em cima do cone, entrando 16,7 cm no cone (junto do pilar). O DRE-126 chega na mesma junção, mas passa\n'
       'fora da sapata real (0,66 m). Não há posição livre até 2,5 m nem cota livre até ±0,40 m: o projetista precisa levar a junção para fora da sapata.',
       os.path.join(OUT, 'colisao_DRE-133.png'))
figura('DRE-061.1 × pilar do BP4 (a 1,8 m da CES-01)', 'DRE-061.1', (631578.050, 8721050.293),
       'O DRE-061.1 atravessa um pilar (6,5 cm). O pilar vai da sapata até o piso, então mudar a cota não resolve: o tubo precisa desviar do pilar em planta.\n'
       'A junção da ponta (DRE-078/DRE-080) não tem posição livre até 2,5 m.',
       os.path.join(OUT, 'colisao_DRE-061.1.png'), foco=(631578.050, 8721050.293))
