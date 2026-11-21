# -*- coding: utf-8 -*-
"""Corrige as sobreposições internas da elétrica (decisão do usuário, 16/10/2026):
  - cruzamento: o eletroduto que CRUZA (o que tem mais parceiros no local; empate -> o de menor DE) passa por baixo,
    com 5 cm de folga, num "mergulho" local (rampas de no máx. 1:2, mín. 0,30 m de projeção);
  - paralelo (banco/mesma vala, ângulo < 20°): afasta lateralmente o de menor DE (ou o que não cria conflito novo).
Trabalha por CORRIDA (segmentos consecutivos do mesmo trecho), para que o mergulho atravesse juntas sem descontinuidade.
Entrada: work/revit_conduits_atual_2026-10-16.tsv (lido do Revit). Saída: work/fix_sobreposicoes_plano.tsv + resumo.
"""
import math, collections, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work" + "\\"
FOLGA = 0.05

# ---------------- leitura
C = {}
for l in open(W + 'revit_conduits_atual_2026-10-16.tsv', encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) < 11: continue
    C[r[0]] = dict(id=r[0], tipo=r[1], trecho=r[2], de=float(r[3]) / 1000, a=np.array(list(map(float, r[4:7]))), b=np.array(list(map(float, r[7:10]))))
print('eletrodutos', len(C))


def root(t): return t.split('.')[0]


# corridas: segmentos do mesmo root encadeados ponta a ponta
runs = collections.defaultdict(list)
for c in C.values(): runs[root(c['trecho'])].append(c['id'])
RUN = {}   # run_id -> lista ordenada de (id, invertido)
for rt, ids in runs.items():
    segs = {i: (C[i]['a'], C[i]['b']) for i in ids}
    rest = set(ids); chains = []
    while rest:
        i0 = rest.pop(); chain = [(i0, False)]
        for side in (0, 1):
            grow = True
            while grow:
                grow = False
                end = (segs[chain[-1][0]][1] if not chain[-1][1] else segs[chain[-1][0]][0]) if side == 0 else (segs[chain[0][0]][0] if not chain[0][1] else segs[chain[0][0]][1])
                for j in list(rest):
                    a, b = segs[j]
                    if side == 0:
                        if np.linalg.norm(a - end) < 0.002: chain.append((j, False)); rest.discard(j); grow = True; break
                        if np.linalg.norm(b - end) < 0.002: chain.append((j, True)); rest.discard(j); grow = True; break
                    else:
                        if np.linalg.norm(b - end) < 0.002: chain.insert(0, (j, False)); rest.discard(j); grow = True; break
                        if np.linalg.norm(a - end) < 0.002: chain.insert(0, (j, True)); rest.discard(j); grow = True; break
        chains.append(chain)
    for k, ch in enumerate(chains): RUN[f'{rt}#{k}'] = ch


def run_poly(rid):
    pts = []; owners = []
    for i, inv in RUN[rid]:
        a, b = C[i]['a'], C[i]['b']
        if inv: a, b = b, a
        if not pts: pts.append(a.copy())
        pts.append(b.copy()); owners.append(i)
    return np.array(pts), owners

P = {}; OWN = {}; DE = {}
for rid in RUN:
    P[rid], OWN[rid] = run_poly(rid); DE[rid] = C[OWN[rid][0]]['de']
# vértices originais (juntas) de cada corrida, por comprimento acumulado -> para re-separar por elemento
def cum(p): return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1))])
JOINT = {rid: cum(P[rid]) for rid in RUN}
print('corridas', len(RUN))


def segdist(p1, q1, p2, q2):
    d1 = q1 - p1; d2 = q2 - p2; r = p1 - p2; a = d1 @ d1; e = d2 @ d2; f = d2 @ r; c = d1 @ r; b = d1 @ d2; den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-12 else 0.0
    t = (b * s + f) / e if e > 1e-12 else 0
    if t < 0: t = 0; s = np.clip(-c / a, 0, 1)
    elif t > 1: t = 1; s = np.clip((b - c) / a, 0, 1)
    return float(np.linalg.norm(p1 + d1 * s - p2 - d2 * t)), float(s), float(t)


# caixas (para isentar pontas que se encontram DENTRO da caixa)
CX = []
for l in open(W + 'revit_caixas.tsv', encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) < 9: continue
    CX.append((float(r[2]), float(r[3]), float(r[4]) / 100, float(r[5]) / 100, float(r[6]), float(r[7]), float(r[8])))


def em_caixa(q, tol=0.06):
    for x, y, w, d, rot, zt, zb in CX:
        dx, dy = q[0] - x, q[1] - y
        c, s = math.cos(-rot), math.sin(-rot)
        lx, ly = dx * c - dy * s, dx * s + dy * c
        if abs(lx) <= w / 2 + tol and abs(ly) <= d / 2 + tol and zb - 0.05 <= q[2] <= zt + 0.05: return True
    return False


def overlaps(P):
    """Lista de (gap, ri, ki, si, rj, kj, tj, ang) para pares de corridas diferentes com sobreposição (gap<0)."""
    segs = []
    for rid, p in P.items():
        for k in range(len(p) - 1): segs.append((rid, k, p[k], p[k + 1]))
    S = np.array([[min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])] for _, _, a, b in segs])
    out = []
    for i in range(len(segs)):
        ri, ki, ai, bi = segs[i]
        m = (S[:, 0] <= S[i, 1] + 0.3) & (S[:, 1] >= S[i, 0] - 0.3) & (S[:, 2] <= S[i, 3] + 0.3) & (S[:, 3] >= S[i, 2] - 0.3)
        for j in np.where(m)[0]:
            if j <= i: continue
            rj, kj, aj, bj = segs[j]
            if rj == ri or root(rj.split('#')[0]) == root(ri.split('#')[0]): continue
            if np.linalg.norm(bi - ai) < 1e-4 or np.linalg.norm(bj - aj) < 1e-4: continue
            d, s, t = segdist(ai, bi, aj, bj); g = d - (DE[ri] + DE[rj]) / 2
            if g < -0.0005:
                qi = ai + (bi - ai) * s; qj = aj + (bj - aj) * t
                if em_caixa(qi) and em_caixa(qj): continue      # encontro dentro da caixa: não é conflito
                u = (bi - ai)[:2]; v = (bj - aj)[:2]
                nu, nv = np.linalg.norm(u), np.linalg.norm(v)
                ang = 0.0 if nu < 1e-6 or nv < 1e-6 else math.degrees(math.acos(min(1, abs(u @ v) / nu / nv)))
                out.append((g, ri, ki, s, rj, kj, t, ang))
    return out


def z_at(p, k, s): return p[k][2] + (p[k + 1][2] - p[k][2]) * s


def insert_dip(p, s0, s1, dz, t_ramp):
    """Rebaixa a corrida p (polilinha 3D) de dz entre os comprimentos s0..s1 (em planta), com rampas de t_ramp.
    Devolve nova polilinha (com vértices inseridos)."""
    L = cum(p); tot = L[-1]
    a0 = max(0.0, s0 - t_ramp); a1 = s0; b0 = s1; b1 = min(tot, s1 + t_ramp)
    def lerp(sv):
        k = int(np.clip(np.searchsorted(L, sv) - 1, 0, len(p) - 2))
        f = 0 if L[k + 1] == L[k] else (sv - L[k]) / (L[k + 1] - L[k])
        return p[k] + (p[k + 1] - p[k]) * f
    keys = sorted(set([0.0, tot, a0, a1, b0, b1] + list(L)))
    new = []
    for sv in keys:
        q = lerp(sv).copy()
        if a1 <= sv <= b0: off = dz
        elif a0 < sv < a1: off = dz * (sv - a0) / (a1 - a0)
        elif b0 < sv < b1: off = dz * (b1 - sv) / (b1 - b0)
        else: off = 0.0
        q[2] -= off; new.append(q)
    out = [new[0]]
    for q in new[1:]:
        if np.linalg.norm(q - out[-1]) > 1e-4: out.append(q)
    return np.array(out)


log = []
P0 = {k: v.copy() for k, v in P.items()}
for it in range(80):
    ov = overlaps(P)
    cr = [o for o in ov if o[7] >= 20]; pa = [o for o in ov if o[7] < 20]
    print(f'iteração {it}: {len(ov)} sobreposições ({len(cr)} cruzamentos, {len(pa)} paralelos)')
    if not ov: break
    if pa and (not cr or it % 2 == 1):
        cr = []
    if cr:
        # local de cada cruzamento (xy) e parceiros por corrida, agrupando cruzamentos a < 1,5 m
        partners = collections.defaultdict(set)
        for g, ri, ki, s, rj, kj, t, ang in cr: partners[ri].add(rj); partners[rj].add(ri)
        # escolhe a corrida que mais cruza; empate -> menor DE
        c = sorted(partners, key=lambda r: (-len(partners[r]), DE[r]))[0]
        p = P[c]; L = cum(p)
        ivs = []
        for g, ri, ki, s, rj, kj, t, ang in cr:
            if c not in (ri, rj): continue
            if ri == c: k, sv, o, ko, tv = ki, s, rj, kj, t
            else: k, sv, o, ko, tv = kj, t, ri, ki, s
            pos = L[k] + (L[k + 1] - L[k]) * sv
            zc = z_at(p, k, sv); zo = z_at(P[o], ko, tv)
            need = (zc - zo) + (DE[c] + DE[o]) / 2 + FOLGA
            hw = ((DE[c] + DE[o]) / 2 + FOLGA) / max(math.sin(math.radians(ang)), 0.34) + 0.05
            ivs.append([pos - hw, pos + hw, need, o])
        ivs.sort()
        merged = []
        for iv in ivs:
            if merged and iv[0] <= merged[-1][1] + 0.6:
                merged[-1][1] = max(merged[-1][1], iv[1]); merged[-1][2] = max(merged[-1][2], iv[2]); merged[-1][3] += ',' + iv[3]
            else: merged.append(list(iv))
        for s0, s1, dz, quem in merged:
            dz = round(max(dz, 0.0) + 0.005, 3)
            t_ramp = max(0.30, 2 * dz)
            P[c] = insert_dip(P[c], max(s0, 0), min(s1, cum(P[c])[-1]), dz, t_ramp)
            log.append(('mergulho', c, f'{s0:.2f}-{s1:.2f}', f'{dz:.3f}', quem))
    else:
        g, ri, ki, s, rj, kj, t, ang = sorted(pa)[0]
        # afasta lateralmente: tenta mover a de menor DE (depois a outra), na direção que se afasta da parceira
        best = None
        for mov, fixa, km, sm, kf, sf in ((ri, rj, ki, s, kj, t), (rj, ri, kj, t, ki, s)) if DE[ri] <= DE[rj] else ((rj, ri, kj, t, ki, s), (ri, rj, ki, s, kj, t)):
            pm = P[mov]; pf = P[fixa]
            qm = pm[km] + (pm[km + 1] - pm[km]) * sm; qf = pf[kf] + (pf[kf + 1] - pf[kf]) * sf
            u = (pm[-1] - pm[0])[:2]; u = u / np.linalg.norm(u); n = np.array([-u[1], u[0]])
            sgn = 1 if (qm - qf)[:2] @ n >= 0 else -1
            desl = -g + FOLGA + 0.002
            trial = pm.copy(); trial[:, 0] += sgn * n[0] * desl; trial[:, 1] += sgn * n[1] * desl
            Pt = dict(P); Pt[mov] = trial
            nconf = sum(1 for o in overlaps({k: Pt[k] for k in Pt}) if mov in (o[1], o[4]))
            if best is None or nconf < best[0]: best = (nconf, mov, trial, desl, fixa)
            if nconf == 0: break
        P[best[1]] = best[2]; log.append(('afastamento', best[1], '-', f'{best[3]:.3f}', best[4]))

ov = overlaps(P)
print('sobreposições restantes:', len(ov))
for o in ov[:10]: print('  resta', o)

# ---------------- re-separar cada corrida modificada pelos elementos originais
plano = []
mods = [rid for rid in P if P[rid].shape != P0[rid].shape or not np.allclose(P[rid], P0[rid])]
for rid in mods:
    p = P[rid]; L = cum(p); J = JOINT[rid]
    # juntas originais: J[k]..J[k+1] pertence ao elemento OWN[rid][k]
    for k, eid in enumerate(OWN[rid]):
        s0, s1 = J[k], J[k + 1]
        pts = [q for q, sv in zip(p, L) if s0 - 1e-6 <= sv <= s1 + 1e-6]
        inv = dict(RUN[rid])[eid]
        segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if np.linalg.norm(pts[i + 1] - pts[i]) > 1e-4]
        if inv: segs = [(b, a) for a, b in reversed(segs)]
        orig = (C[eid]['a'], C[eid]['b'])
        if len(segs) == 1 and np.allclose(segs[0][0], orig[0], atol=1e-4) and np.allclose(segs[0][1], orig[1], atol=1e-4): continue
        for n_, (a, b) in enumerate(segs):
            plano.append((eid, n_, *a, *b))
with open(W + 'fix_sobreposicoes_plano.tsv', 'w', encoding='utf-8') as f:
    for r in plano: f.write('\t'.join([r[0], str(r[1])] + [f'{v:.4f}' for v in r[2:]]) + '\n')
with open(W + 'fix_sobreposicoes_log.tsv', 'w', encoding='utf-8') as f:
    for r in log: f.write('\t'.join(map(str, r)) + '\n')
print('corridas modificadas', len(mods), '| elementos afetados', len(set(r[0] for r in plano)), '| peças no plano', len(plano))
dzs = [float(r[3]) for r in log if r[0] == 'mergulho']; ds = [float(r[3]) for r in log if r[0] == 'afastamento']
print('mergulhos', len(dzs), 'rebaixo máx', max(dzs) if dzs else 0, '| afastamentos', len(ds), 'máx', max(ds) if ds else 0)
for r in log: print('  ', r)
print('--- pontas das corridas modificadas')
for rid in mods:
    for e0, e1 in ((P0[rid][0], P[rid][0]), (P0[rid][-1], P[rid][-1])):
        mv = np.linalg.norm(e1 - e0)
        if mv > 1e-4:
            best = None
            for x, y, w, d, rot, zt, zb in CX:
                dist = math.hypot(e0[0] - x, e0[1] - y)
                if best is None or dist < best[0]: best = (dist, x, y, w, d, rot, zt, zb)
            dist, x, y, w, d, rot, zt, zb = best
            def loc(q):
                dx, dy = q[0] - x, q[1] - y; c, s = math.cos(-rot), math.sin(-rot)
                return dx * c - dy * s, dx * s + dy * c
            l0 = loc(e0); l1 = loc(e1)
            print(f'  {rid}: ponta movida {mv*1000:.0f} mm | caixa a {dist:.2f} m ({w*100:.0f}x{d*100:.0f}) | local antes ({l0[0]:+.3f},{l0[1]:+.3f}) depois ({l1[0]:+.3f},{l1[1]:+.3f}) | meia face {w/2:.2f}/{d/2:.2f}')
