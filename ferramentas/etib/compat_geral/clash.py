# -*- coding: utf-8 -*-
"""Clash geral R02 (todas × todas) sobre a geometria exportada do Revit (RELATORIOS/compat_R02/geo).
Tubo/eletroduto = cápsula (eixo + raio externo); demais = malha triangulada fechada.
  tubo×tubo   : distância segmento-segmento − (r1 + r2)
  tubo×sólido : distância com sinal (dentro = negativo) dos pontos do eixo (a cada 5 cm) à malha − r
  sólido×sólido: distância com sinal de pontos amostrados nas faces de A em B e vice-versa
Folga = menor valor por PAR DE ELEMENTOS. Colisão: folga < −2 mm; folga curta: < 0,20 m.
Uso: clash.py [pasta_geo] [saida.csv] [deslocamentos.json opcional p/ testar soluções]
"""
import sys, os, re, json, math, collections, time
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
G = sys.argv[1] if len(sys.argv) > 1 else r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash.csv"
MODS = json.load(open(sys.argv[3], encoding='utf-8')) if len(sys.argv) > 3 else None
FOLGA = 0.20; TOL = -0.002
t0 = time.time()

# ------------------------------------------------------------------ leitura
def disc_seg(f, r):
    if f == 'HS': return 'AF' if r[4].startswith('Água') else 'ESG'
    if f == 'INC': return 'SDAI' if (r[2] == 'Conduites' or 'SDAI' in r[3]) else 'INC'
    if f == 'ELE': return 'TEL' if r[3].startswith('TEL') else 'ELE'
    return f

def disc_mesh(f, r):
    nome, trecho = r[3], r[4]
    if f == 'HS': return 'AF' if (nome.startswith('AF') ) else 'ESG'
    if f == 'INC': return 'SDAI' if 'SDAI' in nome else 'INC'
    if f == 'ELE': return 'TEL' if trecho.startswith('CF') else 'ELE'
    if f == 'EST': return 'IMP' if '-IMP_' in r[4] else 'EST'
    return f

SEG = []
for f in ('HS', 'DRN', 'INC', 'ELE'):
    for l in open(os.path.join(G, f + '_segs.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 13: continue
        a = np.array(list(map(float, r[7:10]))); b = np.array(list(map(float, r[10:13])))
        if np.linalg.norm(b - a) < 1e-4: continue
        SEG.append(dict(disc=disc_seg(f, r), id=r[1], cat=r[2], tipo=r[3], sis=r[4], trecho=r[5] or r[4], de=float(r[6]), a=a, b=b, desc=r[13] if len(r) > 13 else ''))
MESH = []
for f in ('HS', 'DRN', 'INC', 'ELE', 'CNT', 'EST'):
    for l in open(os.path.join(G, f + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 8: continue
        if f == 'EST' and 'PISO-TÁTIL' in r[3]: continue        # revestimento de superfície (IMP)
        v = np.array(r[7].split(','), dtype=float).reshape(-1, 3, 3)
        d = disc_mesh(f, r)
        sub = r[2]
        bloco = r[1].split(':')[0] if f == 'EST' else ''
        MESH.append(dict(disc=d, id=r[1], cat=r[2], nome=r[3], trecho=r[4] if f != 'EST' else (bloco + ' ' + r[3].split(' : ')[0]), desc=r[5] if f != 'EST' else r[4], tri=v,
                         lo=v.reshape(-1, 3).min(0), hi=v.reshape(-1, 3).max(0), bloco=bloco))
print(f'segmentos {len(SEG)} | sólidos {len(MESH)} | leitura {time.time()-t0:.1f}s')

# deslocamentos de teste (soluções): {"seg": {id: {"dz": m, "dxy": [dx,dy]}} , "trecho_prefixo": {...}}
if MODS:
    for s in SEG:
        m = MODS.get('seg', {}).get(s['id'])
        if m is None:
            for pref, mm in MODS.get('prefixo', {}).items():
                if s['trecho'].startswith(pref) or s['id'] == pref: m = mm; break
        if m:
            dz = m.get('dz', 0.0); dxy = m.get('dxy', [0, 0])
            s['a'] = s['a'] + np.array([dxy[0], dxy[1], -dz]); s['b'] = s['b'] + np.array([dxy[0], dxy[1], -dz])
    for M in MESH:
        m = MODS.get('mesh', {}).get(M['id'])
        if m:
            off = np.array([m['dxy'][0], m['dxy'][1], -m.get('dz', 0.0)])
            M['tri'] = M['tri'] + off; M['lo'] = M['lo'] + off; M['hi'] = M['hi'] + off
    print('soluções aplicadas para teste')

# ------------------------------------------------------------------ geometria
def segdist(p1, q1, p2, q2):
    d1 = q1 - p1; d2 = q2 - p2; r = p1 - p2; a = d1 @ d1; e = d2 @ d2; f = d2 @ r; c = d1 @ r; b = d1 @ d2; den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-12 else 0.0
    t = (b * s + f) / e if e > 1e-12 else 0
    if t < 0: t = 0; s = np.clip(-c / a, 0, 1)
    elif t > 1: t = 1; s = np.clip((b - c) / a, 0, 1)
    P = p1 + d1 * s; Q = p2 + d2 * t
    return float(np.linalg.norm(P - Q)), (P + Q) / 2


def pt_tri_dist(P, T):
    """distância de cada ponto (n,3) a cada triângulo (m,3,3) -> (n,m). Ericson, vetorizado."""
    A = T[:, 0][None]; B = T[:, 1][None]; C = T[:, 2][None]; p = P[:, None, :]
    ab = B - A; ac = C - A; ap = p - A
    d1 = (ab * ap).sum(-1); d2 = (ac * ap).sum(-1)
    bp = p - B; d3 = (ab * bp).sum(-1); d4 = (ac * bp).sum(-1)
    cp = p - C; d5 = (ab * cp).sum(-1); d6 = (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-18, 1e-18, den)
    v = vb / den; w = vc / den
    res = A + ab * v[..., None] + ac * w[..., None]                       # interior
    # regiões de vértice/aresta
    def setr(mask, val):
        nonlocal res
        res = np.where(mask[..., None], val, res)
    m = (d1 <= 0) & (d2 <= 0); setr(m, np.broadcast_to(A, res.shape))
    m = (d3 >= 0) & (d4 <= d3); setr(m, np.broadcast_to(B, res.shape))
    m = (d6 >= 0) & (d5 <= d6); setr(m, np.broadcast_to(C, res.shape))
    with np.errstate(divide='ignore', invalid='ignore'):
        vv = d1 / (d1 - d3); m = (vc <= 0) & (d1 >= 0) & (d3 <= 0); setr(m, A + ab * np.nan_to_num(vv)[..., None])
        ww = d2 / (d2 - d6); m = (vb <= 0) & (d2 >= 0) & (d6 <= 0); setr(m, A + ac * np.nan_to_num(ww)[..., None])
        uu = (d4 - d3) / ((d4 - d3) + (d5 - d6)); m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); setr(m, B + (C - B) * np.nan_to_num(uu)[..., None])
    return np.linalg.norm(p - res, axis=-1)


RAY = np.array([0.8726, 0.3864, 0.2987]); RAY /= np.linalg.norm(RAY)
def inside(P, T):
    """paridade de interseções de um raio a partir de cada ponto -> bool (n,)"""
    v0 = T[:, 0][None]; e1 = (T[:, 1] - T[:, 0])[None]; e2 = (T[:, 2] - T[:, 0])[None]
    h = np.cross(RAY, e2); a = (e1 * h).sum(-1)
    ok = np.abs(a) > 1e-12; f = np.where(ok, 1.0 / np.where(ok, a, 1), 0)
    s = P[:, None, :] - v0; u = f * (s * h).sum(-1)
    q = np.cross(s, e1); v = f * (q * RAY).sum(-1); t = f * (e2 * q).sum(-1)
    hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > 1e-9)
    return (hit.sum(1) % 2) == 1


def signed(P, M):
    T = M['tri']
    d = pt_tri_dist(P, T).min(1)
    ins = inside(P, T)
    return np.where(ins, -d, d)


def samples_seg(s, step=0.05):
    L = np.linalg.norm(s['b'] - s['a']); n = max(2, int(math.ceil(L / step)) + 1)
    return s['a'] + (s['b'] - s['a']) * np.linspace(0, 1, n)[:, None]


def samples_mesh(M, step=0.15):
    T = M['tri']; pts = [T.reshape(-1, 3), T.mean(1)]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    for i in np.where(area > step * step)[0]:
        k = int(min(12, math.ceil(math.sqrt(area[i]) / step)))
        g = [(a / k, b / k) for a in range(k + 1) for b in range(k + 1 - a)]
        A, B, C = T[i]; pts.append(np.array([A + (B - A) * x + (C - A) * y for x, y in g]))
    return np.unique(np.round(np.vstack(pts), 4), axis=0)

# ------------------------------------------------------------------ pares
NAO = {('EST', 'IMP'), ('IMP', 'EST'), ('EST', 'EST'), ('IMP', 'IMP')}
SO_COLISAO = {frozenset(('ELE', 'TEL'))}       # mesmo RVT, valas compartilhadas: folga não é item
def par_ok(d1, d2): return d1 != d2 and (d1, d2) not in NAO

res = []
def add(tipo, A, B, folga, pt, ka, kb):
    res.append(dict(tipo=tipo, dA=A['disc'], dB=B['disc'], idA=A['id'], idB=B['id'], kA=ka, kB=kb, folga=folga, x=pt[0], y=pt[1], z=pt[2]))

# grade para pré-filtro
def bb_seg(s, m):
    lo = np.minimum(s['a'], s['b']) - (s['de'] / 2 + m); hi = np.maximum(s['a'], s['b']) + (s['de'] / 2 + m); return lo, hi
CELL = 5.0
def cells(lo, hi):
    return [(i, j) for i in range(int(lo[0] // CELL), int(hi[0] // CELL) + 1) for j in range(int(lo[1] // CELL), int(hi[1] // CELL) + 1)]
gS = collections.defaultdict(list); gM = collections.defaultdict(list)
for i, s in enumerate(SEG):
    lo, hi = bb_seg(s, FOLGA); s['lo'], s['hi'] = lo, hi
    for c in cells(lo, hi): gS[c].append(i)
for i, M in enumerate(MESH):
    for c in cells(M['lo'] - FOLGA, M['hi'] + FOLGA): gM[c].append(i)
def ov(lo1, hi1, lo2, hi2, m=0.0): return np.all(lo1 - m <= hi2) and np.all(lo2 - m <= hi1)

# tubo × tubo
vis = set()
for c, idx in gS.items():
    for ii in range(len(idx)):
        for jj in range(ii + 1, len(idx)):
            i, j = idx[ii], idx[jj]
            if (i, j) in vis: continue
            vis.add((i, j)); A, B = SEG[i], SEG[j]
            if not par_ok(A['disc'], B['disc']) or not ov(A['lo'], A['hi'], B['lo'], B['hi']): continue
            d, pt = segdist(A['a'], A['b'], B['a'], B['b']); g = d - (A['de'] + B['de']) / 2
            if g < FOLGA:
                if frozenset((A['disc'], B['disc'])) in SO_COLISAO and g >= TOL: continue
                add('tubo×tubo', A, B, g, pt, 'S', 'S')
print(f'tubo×tubo: {len(res)} pares | {time.time()-t0:.1f}s')

# tubo × sólido
vis = set(); n0 = len(res)
for c, idx in gS.items():
    for i in idx:
        for j in gM.get(c, ()):
            if (i, j) in vis: continue
            vis.add((i, j)); A, M = SEG[i], MESH[j]
            if not par_ok(A['disc'], M['disc']) or not ov(A['lo'], A['hi'], M['lo'], M['hi']): continue
            P = samples_seg(A)
            m = np.all((P >= M['lo'] - A['de'] / 2 - FOLGA) & (P <= M['hi'] + A['de'] / 2 + FOLGA), axis=1)
            if not m.any(): continue
            P = P[m]; sd = signed(P, M) - A['de'] / 2; k = int(sd.argmin())
            if sd[k] < FOLGA:
                if frozenset((A['disc'], M['disc'])) in SO_COLISAO and sd[k] >= TOL: continue
                add('tubo×sólido', A, M, float(sd[k]), P[k], 'S', 'M')
print(f'tubo×sólido: {len(res)-n0} pares | {time.time()-t0:.1f}s')

# sólido × sólido (não estrutura × estrutura)
vis = set(); n0 = len(res); SAMP = {}
for c, idx in gM.items():
    for ii in range(len(idx)):
        for jj in range(ii + 1, len(idx)):
            i, j = idx[ii], idx[jj]
            if (i, j) in vis: continue
            vis.add((i, j)); A, B = MESH[i], MESH[j]
            if not par_ok(A['disc'], B['disc']) or not ov(A['lo'], A['hi'], B['lo'], B['hi'], FOLGA): continue
            best = (9e9, None)
            for X, Y, key in ((A, B, i), (B, A, j)):
                if key not in SAMP: SAMP[key] = samples_mesh(X)
                P = SAMP[key]; m = np.all((P >= Y['lo'] - FOLGA) & (P <= Y['hi'] + FOLGA), axis=1)
                if not m.any(): continue
                sd = signed(P[m], Y); k = int(sd.argmin())
                if sd[k] < best[0]: best = (float(sd[k]), P[m][k])
            if best[0] < FOLGA:
                if frozenset((A['disc'], B['disc'])) in SO_COLISAO and best[0] >= TOL: continue
                add('sólido×sólido', A, B, best[0], best[1], 'M', 'M')
print(f'sólido×sólido: {len(res)-n0} pares | {time.time()-t0:.1f}s')

# ------------------------------------------------------------------ gravidade e saída
def info(k, idx):
    E = (SEG if k == 'S' else MESH)
    return E

IDX = {('S', s['id']): s for s in SEG}; IDX.update({('M', m['id']): m for m in MESH})
def grav(r):
    A = IDX[(r['kA'], r['idA'])]; B = IDX[(r['kB'], r['idB'])]
    col = r['folga'] < TOL
    ds = {r['dA'], r['dB']}
    if 'EST' in ds:
        E = A if A['disc'] == 'EST' else B
        if E['cat'] in ('Pisos',) or (E['cat'] == 'Paredes'):
            return ('INFORMAÇÃO' if col else None), ('passagem por laje/parede estrutural' if col else '')
        if E['cat'] == 'Quadro estrutural':
            return ('ATENÇÃO' if col else ('ATENÇÃO' if r['folga'] < 0.10 else None)), ('travessia de viga baldrame' if col else 'muito próximo de viga baldrame')
        return ('CRÍTICA' if col else ('ATENÇÃO' if r['folga'] < 0.10 else None)), ('colisão com fundação/pilar' if col else 'muito próximo de fundação/pilar')
    if 'IMP' in ds:
        if 'CNT' in ds: return ('ATENÇÃO' if col else None), 'muro existente do IMP dentro/junto do muro novo'
        return ('INFORMAÇÃO' if col else None), ('passagem pelo muro existente (IMP)' if col else '')
    return ('CRÍTICA' if col else 'ATENÇÃO'), ('colisão' if col else 'folga menor que 20 cm')

rows = []
for r in res:
    g, motivo = grav(r)
    if g is None: continue
    A = IDX[(r['kA'], r['idA'])]; B = IDX[(r['kB'], r['idB'])]
    # ordena o par para estabilidade (disciplina alfabética)
    if A['disc'] > B['disc']: A, B = B, A
    rows.append([g, motivo, f"{A['disc']}×{B['disc']}", A['disc'], A['id'], A.get('trecho', ''), A.get('cat', ''), A.get('nome', A.get('tipo', ''))[:60], f"{A.get('de', 0)*1000:.0f}" if 'de' in A else '',
                 B['disc'], B['id'], B.get('trecho', ''), B.get('cat', ''), B.get('nome', B.get('tipo', ''))[:60], f"{B.get('de', 0)*1000:.0f}" if 'de' in B else '',
                 f"{r['folga']:.3f}", f"{r['x']:.2f}", f"{r['y']:.2f}", f"{r['z']:.2f}", r['tipo']])
rows.sort(key=lambda x: ({'CRÍTICA': 0, 'ATENÇÃO': 1, 'INFORMAÇÃO': 2}[x[0]], x[2], float(x[15])))
with open(OUT, 'w', encoding='utf-8-sig') as f:
    f.write('gravidade;motivo;par;discA;idA;trechoA;catA;nomeA;DE_A_mm;discB;idB;trechoB;catB;nomeB;DE_B_mm;folga_m;x;y;z;tipo\n')
    for r in rows: f.write(';'.join(str(v).replace(';', ',') for v in r) + '\n')
cnt = collections.Counter((r[0], r[2]) for r in rows)
print(f'pontos: {len(rows)} | {collections.Counter(r[0] for r in rows)} | {time.time()-t0:.1f}s')
for k, v in sorted(cnt.items()): print('  ', k, v)
print('ok', OUT)
