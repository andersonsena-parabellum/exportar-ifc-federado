# -*- coding: utf-8 -*-
"""Pré-clash da iluminação do campo (CPS EL-001 R01) contra os modelos JAN revisados (geo_exec), no interno.
Premissa de cota: eixo do eletroduto Ø1" na cota 146,57 (mesma da elétrica do Daniel, "mexer o mínimo"); caixas 30x30 com 0,55 m.
Grava compat_R01/cps_ele.json (segmentos e caixas no interno) e imprime os conflitos."""
import sys, os, json, math, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"
Z, DE, CX, HCX = 146.57 - 147.0, 0.033, 0.30, 0.55
V1 = [(104.99, 130.63), (65.13, 134.39), (61.79, 98.99), (101.65, 95.23)]
ROT = {'CX-C01': (101.87, 95.11), 'CX-C02': (75.95, 97.25), 'CX-C03': (60.88, 98.67), 'CX-C04': (61.42, 116.82), 'CX-C05': (64.31, 134.69), 'CX-C06': (79.38, 133.27), 'CX-C07': (104.23, 130.95)}
segs = [(np.array(V1[k]), np.array(V1[k + 1])) for k in range(3)]
def no_tubo(p):
    best = None
    for a, b in segs:
        u = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1); q = a + (b - a) * u; d = np.linalg.norm(p - q)
        if best is None or d < best[0]: best = (d, q, (b - a) / np.linalg.norm(b - a))
    return best
caixas = {}
for k, p in ROT.items():
    d, q, u = no_tubo(np.array(p)); caixas[k] = dict(c=q.tolist(), u=u.tolist(), dist_rotulo=round(float(d), 2))
# eletroduto partido nas caixas
pts = sorted([(k, np.array(v['c'])) for k, v in caixas.items()], key=lambda kv: 0)
seq = [np.array(V1[0])]
for a, b in segs:
    on = [np.array(v['c']) for v in caixas.values() if no_tubo(np.array(v['c']))[0] < 1e-6 and np.linalg.norm(np.cross(np.append(b - a, 0), np.append(np.array(v['c']) - a, 0))) < 1e-3 and 0 <= np.dot(np.array(v['c']) - a, b - a) <= np.dot(b - a, b - a)]
    for q in sorted(on, key=lambda q: np.dot(q - a, b - a)): seq.append(q)
    seq.append(b)
seq2 = [seq[0]] + [q for k, q in enumerate(seq[1:]) if np.linalg.norm(q - seq[k]) > 0.05]
SEG, MESH = JD.carregar(g=os.path.join(C, 'geo_exec'), est='daniel'); JD.agrupar_caixas(SEG, MESH)
n0 = len(SEG)
for k in range(len(seq2) - 1):
    a = np.array([*seq2[k], Z]); b = np.array([*seq2[k + 1], Z])
    SEG.append(dict(k='S', disc='ELE', fonte='CPS', id='CPS-%d' % k, cat='Conduites', tipo='Eletroduto Ø1"', sis='', trecho='ELE-CPS-%02d' % (k + 1), de=DE, dn='25', desc='CPS EL-001 R01', a=a, b=b, a0=a.copy(), b0=b.copy(), dz=0.0, grupo='ELE-CPS-%02d' % (k + 1)))
def caixa_mesh(c, u, l, h, ztop):
    u = np.array(u); n = np.array([-u[1], u[0]]); c = np.array(c); P = [c + su * u * l / 2 + sn * n * l / 2 for su, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    V = [np.array([*p, ztop - h]) for p in P] + [np.array([*p, ztop]) for p in P]
    F = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[V[i] for i in f] for f in F])
m0 = len(MESH)
for k, v in caixas.items():
    tri = caixa_mesh(v['c'], v['u'], CX, HCX, 0.0)
    MESH.append(dict(k='M', disc='ELE', fonte='CPS', id='CPS-' + k, cat='Equipamento elétrico', nome=k, trecho=k, desc='CPS', tri=tri, lo=tri.reshape(-1, 3).min(0), hi=tri.reshape(-1, 3).max(0), bloco='', grupo=k, glo=tri.reshape(-1, 3).min(0), ghi=tri.reshape(-1, 3).max(0)))
IDX = mt.Indice(SEG, MESH); res = []
for i in range(n0, len(SEG)):
    for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
        B = SEG[j] if t == 'S' else MESH[j]
        if B.get('fonte') == 'CPS' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        res.append((SEG[i]['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt, 2))))
for j in range(m0, len(MESH)):
    for t, k2, g, pt in mt.avaliar_mesh(j, IDX, 0.20):
        B = SEG[k2] if t == 'S' else MESH[k2]
        if B.get('fonte') == 'CPS' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        res.append((MESH[j]['grupo'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt, 2))))
res = sorted(set(res), key=lambda r: r[3])
print('eletroduto do campo: %d trechos, %.1f m; caixas: %d (rótulo a até %.1f m do tubo)' % (len(SEG) - n0, sum(np.linalg.norm(s['b'] - s['a']) for s in SEG[n0:]), len(caixas), max(v['dist_rotulo'] for v in caixas.values())))
print('colisões:', sum(1 for r in res if r[3] < -0.2), '| folgas < 20 cm:', sum(1 for r in res if r[3] >= -0.2))
for r in res: print('  ', r)
json.dump(dict(premissa='eixo 146,57; caixas 30x30x0,55; CPS centrado no piso do IMP (±1 m)', segs=[dict(trecho=s['trecho'], a=s['a'].tolist(), b=s['b'].tolist(), de=DE) for s in SEG[n0:]], caixas=caixas),
          open(os.path.join(C, 'cps_ele.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
