# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — folga dos tubos que sobraram contra a FORMA REAL da peça da estrutura (malha do RVT as built), em vez da
caixa envolvente usada no clash: a sapata cônica afina para cima, então a caixa envolvente acusa colisão que pode não existir.
Para cada ponto do eixo do tubo (a cada 2 cm) e cada altura da seção do tubo, corta a malha da peça na mesma altura (fecho convexo da
seção) e mede a distância em planta. Uso: python folga_forma_real.py"""
import os, sys, csv, json, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\ifc'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
sys.stdout.reconfigure(encoding='utf-8')
import jan_modelo as JM, jan_dados as JD
from preclash import clash as cl
PRE = os.environ.get('JAN_PRE') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02'
G0 = JM.G0
T = JD.Terreno(g=G0); aj = JM.Ajuste(T, JM.pontos_base(json.load(open(JM.ROT_JSON, encoding='utf-8'))))
links = JD.mapa_links('ELE', G0)


def malha(eid):
    """triângulos (n,3,3) em UTM da peça EST:<tag>:<id>, como no jan_modelo.estrutura (mesmo ajuste do terreno)."""
    _, tag, rid = eid.split(':')
    m = JD.meta(tag, G0); nome = m['titulo'].split('__', 1)[-1]
    irmao = nome.replace('-ECC-', '-FUN-').replace('-EMT-', '-FUN-')
    R, o = links.get(nome) or links.get(irmao)
    for l in open(os.path.join(G0, tag + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 9 or r[1] != rid: continue
        v = np.array(r[8].split(','), dtype=float).reshape(-1, 3)
        lo, hi = v.min(0), v.max(0); c = R @ ((lo + hi) / 2) + o; d = aj(c[0], c[1])
        W = np.array([R @ p + o for p in v]); U = JM.utm(W); U[:, 2] = 147 + W[:, 2] + d
        return U.reshape(-1, 3, 3), r[3].split(' : ')[0]
    return None, None


def secao(TRI, z):
    pts = []
    for t in TRI:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (a[2] - z) * (b[2] - z) <= 0 and abs(a[2] - b[2]) > 1e-9:
                s = (z - a[2]) / (b[2] - a[2]); pts.append(a[:2] + (b[:2] - a[:2]) * s)
            elif abs(a[2] - z) < 1e-9: pts.append(a[:2])
    if len(pts) < 3: return None
    P = np.unique(np.round(np.array(pts), 5), axis=0)
    if len(P) < 3: return None
    # fecho convexo (cadeia monótona)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in P[::-1]:
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def dist_poligono(q, H):
    """distância com sinal do ponto q ao polígono convexo H (negativa dentro)."""
    d = []; dentro = True
    for a, b in zip(H, np.roll(H, -1, 0)):
        e = b - a; L = np.hypot(*e); n = np.array([e[1], -e[0]]) / max(L, 1e-12)
        if np.dot(q - a, n) > 0: dentro = False
        u = np.clip(np.dot(q - a, e) / max(L * L, 1e-12), 0, 1); d.append(np.hypot(*(q - (a + e * u))))
    return -min(d) if dentro else min(d)


J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8')); O = (631578.10, 8721003.57); zr = J['zref']
ELS = {e['id']: e for e in J['elementos']}
for r in csv.DictReader(open(os.path.join(PRE, 'JAN_preclash_AD_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
    if r['gravidade'] != 'CRÍTICA' or r['disc_B'] != 'EST': continue
    # o CSV traz o nome da peça; o id vem da conferência pelo clash no ponto
    e = next(x for x in J['elementos'] if x['trecho'] == r['trecho_A'] and 'AD' in x['cen'])
    P = np.array((e['sol'] or {}).get('AD') or e['p'], float); P[:, 0] += O[0]; P[:, 1] += O[1]; P[:, 2] += zr
    pc = np.array([float(r['E'].replace(',', '.')), float(r['N'].replace(',', '.'))])
    cands = [c for c in J['caixas'] if c['id'].startswith('EST:') and math.hypot(c['x'] + O[0] - pc[0], c['y'] + O[1] - pc[1]) < c['m'] + 0.3]
    rr = e['de'] / 2; melhor = None
    for c in cands:
        TRI, nome = malha(c['id'])
        if TRI is None or nome.split(':')[0] not in r['trecho_B'] and r['trecho_B'] not in nome: continue
        zlo, zhi = TRI[:, :, 2].min(), TRI[:, :, 2].max(); f = 9.0
        for q in cl.amostra(P, 0.02):
            for dzv in np.linspace(-rr, rr, 7):
                h = q[2] + dzv
                if h < zlo or h > zhi: continue
                H = secao(TRI, h)
                if H is None: continue
                f = min(f, dist_poligono(q[:2], H) - math.sqrt(max(rr * rr - dzv * dzv, 0)))
            if f < -0.3: break
        if melhor is None or f < melhor[0]: melhor = (f, nome, c['id'])
    caixa = float(r['folga_m'].replace(',', '.'))
    if melhor: print(f"{r['trecho_A']:10s} × {melhor[1][:40]:40s} caixa envolvente {caixa:+.3f} m | forma real {melhor[0]:+.3f} m")
    else: print(r['trecho_A'], r['trecho_B'][:40], 'peça não achada')
