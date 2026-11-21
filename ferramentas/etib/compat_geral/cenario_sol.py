# -*- coding: utf-8 -*-
"""Cenário de solução (geo_sol): cópia da geometria exportada com
 1) CONTENÇÃO: sapatas sem ponta (lado do lote); o talão (lado do aterro) recebe a mesma largura -> sapata de [0 ; 0,90+0,25+ponta];
 2) IMP: muros existentes (Paredes) a menos de 1,5 m da face do muro novo removidos (demolição prévia).
Os demais arquivos são copiados sem mudança."""
import os, shutil, json, math
import numpy as np
G = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo"; S = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo_sol"
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
os.makedirs(S, exist_ok=True)
for f in os.listdir(G):
    if f not in ('CNT_mesh.tsv', 'EST_mesh.tsv'): shutil.copy(os.path.join(G, f), os.path.join(S, f))
# 1) sapatas alternativas
alt = {}
for l in open(os.path.join(W, 'cnt_pecas.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    if c[0] != 'SAPATA': continue
    g = list(map(float, c[8].split(';'))); p0 = np.array(g[0:2]); u = np.array(g[2:4]); n = np.array(g[4:6])
    u /= np.linalg.norm(u); n /= np.linalg.norm(n)
    d0, d1, z0 = float(c[3]), float(c[4]), float(c[5])
    prof = [tuple(map(float, q.split(','))) for q in c[7].split(';')]
    a0 = min(p[0] for p in prof); a1 = max(p[0] for p in prof); h = -min(p[1] for p in prof)
    s0, s1 = 0.0, a1 + (-a0)            # sem ponta; talão absorve a largura
    V = []
    for d in (d0, d1):
        for s in (s0, s1):
            for z in (z0 - h, z0):
                q = p0 + u * d + n * s; V.append((q[0], q[1], z))
    V = np.array(V).reshape(2, 2, 2, 3)   # [d][s][z]
    def quad(a, b, c_, d_): return [a, b, c_, a, c_, d_]
    P = lambda i, j, k: V[i, j, k]
    tris = []
    tris += quad(P(0,0,0), P(0,1,0), P(0,1,1), P(0,0,1)); tris += quad(P(1,0,0), P(1,0,1), P(1,1,1), P(1,1,0))
    tris += quad(P(0,0,0), P(0,0,1), P(1,0,1), P(1,0,0)); tris += quad(P(0,1,0), P(1,1,0), P(1,1,1), P(0,1,1))
    tris += quad(P(0,0,0), P(1,0,0), P(1,1,0), P(0,1,0)); tris += quad(P(0,0,1), P(0,1,1), P(1,1,1), P(1,0,1))
    alt[c[2]] = (len(tris) // 3, ','.join(f'{v:.3f}' for t in tris for v in t), f'{s1:.2f}')
nalt = 0
with open(os.path.join(S, 'CNT_mesh.tsv'), 'w', encoding='utf-8') as f:
    for l in open(os.path.join(G, 'CNT_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if r[2].startswith('Funda') and r[4] in alt:
            nt, v, s1 = alt[r[4]]; r[6] = str(nt); r[7] = v; r[5] = r[5] + f' | SOLUÇÃO: sem ponta, talão até {s1} m'; nalt += 1
        f.write('\t'.join(r) + '\n')
# 2) muros existentes do IMP junto ao muro novo
F = json.load(open(os.path.join(W, 'cnt_face.json'), encoding='utf-8'))
def dist_face(x, y):
    best = 9e9
    for sg in F['segmentos']:
        a = np.array(sg['p0']); b = np.array(sg['p1']); p = np.array([x, y]); d = b - a
        t = np.clip((p - a) @ d / (d @ d), 0, 1); best = min(best, float(np.linalg.norm(p - a - d * t)))
    return best
nrem = 0
with open(os.path.join(S, 'EST_mesh.tsv'), 'w', encoding='utf-8') as f:
    for l in open(os.path.join(G, 'EST_mesh.tsv'), encoding='utf-8'):
        r = l.split('\t', 7)
        if '-IMP_' in r[4] and r[2] == 'Paredes':
            v = np.array(r[7].split(','), dtype=float).reshape(-1, 3)
            if np.median([dist_face(x, y) for x, y in v[:, :2]]) < 1.5: nrem += 1; continue
        f.write(l)
print('sapatas alteradas', nalt, '| muros existentes removidos', nrem, '| ok', S)
