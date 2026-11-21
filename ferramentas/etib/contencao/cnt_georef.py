# -*- coding: utf-8 -*-
"""Georreferencia o DWG da contenção (local) no sistema UTM do SIT_REF.
Casa os CÍRCULOS do layer ARQ_BASE (mesma base nos dois desenhos) por RANSAC (raio + distâncias),
ajusta rígido (rotação + translação, sem escala) por mínimos quadrados e confere nas pontas das LINHAS.
Saída: CAD_GEORREFERENCIADO/transformacao_CNT_local_para_UTM.json
"""
import sys, json, math, re, itertools, random
import numpy as np

CNT = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work\dump_CNT_local.tsv"
SIT = r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\dump_SIT.tsv"
OUT = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\CAD_GEORREFERENCIADO\transformacao_CNT_local_para_UTM.json"
NUM = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def load(fn, layer):
    circ, lines = [], []
    for ln in open(fn, encoding='cp1252', errors='replace'):
        p = ln.rstrip('\n').split('\t')
        if len(p) < 4 or p[1] != layer: continue
        if p[0] == 'CIRCLE':
            m = re.match(r'(-?[\d.]+),(-?[\d.]+) r=([\d.]+)', p[3])
            if m: circ.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
        elif p[0] == 'LINE':
            v = [(float(a), float(b)) for a, b in NUM.findall(p[3])]
            if len(v) == 2: lines.append(v)
    return np.array(circ), lines


def rigid(A, B):
    """B ≈ R·A + t (2D, sem escala)."""
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[1] *= -1; R = Vt.T @ U.T
    return R, cb - R @ ca


cA, lA = load(CNT, 'ARQ_BASE')
cB, lB = load(SIT, 'ARQ_BASE')
# descarta lixo longe da obra (o ARQ_BASE da CNT tem entidades a milhares de km)
cA = cA[(np.abs(cA[:, 0]) < 1000) & (np.abs(cA[:, 1]) < 1000)]
print('círculos CNT', len(cA), 'SIT', len(cB))

random.seed(1)
best = (0, None)
rad_tol = 0.002
for it in range(20000):
    i, j = random.sample(range(len(cA)), 2)
    dA = math.dist(cA[i, :2], cA[j, :2])
    if dA < 5: continue
    ci = np.where(np.abs(cB[:, 2] - cA[i, 2]) < rad_tol)[0]
    cj = np.where(np.abs(cB[:, 2] - cA[j, 2]) < rad_tol)[0]
    if len(ci) == 0 or len(cj) == 0: continue
    k = random.choice(ci); l = random.choice(cj)
    if abs(math.dist(cB[k, :2], cB[l, :2]) - dA) > 0.01: continue
    R, t = rigid(cA[[i, j], :2], cB[[k, l], :2])
    P = (R @ cA[:, :2].T).T + t
    # conta inliers: círculo mais próximo com mesmo raio a < 5 cm
    n = 0
    for q, r in zip(P, cA[:, 2]):
        d = np.hypot(cB[:, 0] - q[0], cB[:, 1] - q[1])
        m = (d < 0.05) & (np.abs(cB[:, 2] - r) < rad_tol)
        n += m.any()
    if n > best[0]:
        best = (n, (R, t))
        if n > 0.8 * len(cA): break
print('RANSAC inliers', best[0])
R, t = best[1]
# refino com todos os pares casados
for _ in range(5):
    P = (R @ cA[:, :2].T).T + t
    A_, B_ = [], []
    for a, q, r in zip(cA, P, cA[:, 2]):
        d = np.hypot(cB[:, 0] - q[0], cB[:, 1] - q[1]); d[np.abs(cB[:, 2] - r) > rad_tol] = 9e9
        k = d.argmin()
        if d[k] < 0.05: A_.append(a[:2]); B_.append(cB[k, :2])
    R, t = rigid(np.array(A_), np.array(B_))
res = np.hypot(*((R @ np.array(A_).T).T + t - np.array(B_)).T)
ang = math.degrees(math.atan2(R[1, 0], R[0, 0]))
print(f'pares {len(A_)}  rot {ang:.10f}°  t {t[0]:.6f} {t[1]:.6f}  resíduo médio {res.mean()*1000:.2f} mm  máx {res.max()*1000:.2f} mm')

# conferência independente nas LINHAS do ARQ_BASE: ponta transformada × ponta mais próxima do SIT
ptsB = np.array([p for l in lB for p in l])
ptsA = np.array([p for l in lA for p in l if abs(p[0]) < 1000 and abs(p[1]) < 1000])
grid = {}
for k, (x, y) in enumerate(ptsB): grid.setdefault((int(x // 1), int(y // 1)), []).append(k)
def nearest(q):
    gx, gy = int(q[0] // 1), int(q[1] // 1); best = 9e9
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for k in grid.get((gx + dx, gy + dy), ()):
                best = min(best, math.hypot(ptsB[k, 0] - q[0], ptsB[k, 1] - q[1]))
    return best
dd = np.array([nearest(q) for q in (R @ ptsA.T).T + t])
print(f'linhas: {len(ptsA)} pontas; mediana {np.median(dd)*1000:.2f} mm; <1 cm {np.mean(dd<0.01)*100:.1f}%; <5 cm {np.mean(dd<0.05)*100:.1f}%')

json.dump({
    'fonte': '24-049-ALH-SLJ-ETIB-IMP-PE-CNT-001-DGE-R00.dwg',
    'metodo': 'RANSAC + mínimos quadrados nos círculos do layer ARQ_BASE (CNT local × SIT_REF UTM, dump_SIT.tsv); conferido nas pontas das linhas do ARQ_BASE',
    'rigid': {'rot_deg': ang, 't': [float(t[0]), float(t[1])], 'regra': 'UTM = R(rot) · p_local + t (rotação em torno de 0,0, depois translação)'},
    'pares_circulos': len(A_), 'residuo_medio_mm': float(res.mean() * 1000), 'residuo_max_mm': float(res.max() * 1000),
    'linhas_mediana_mm': float(np.median(dd) * 1000), 'linhas_pct_1cm': float(np.mean(dd < 0.01) * 100)
}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', OUT)
