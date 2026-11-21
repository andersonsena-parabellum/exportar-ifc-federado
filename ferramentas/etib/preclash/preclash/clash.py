# -*- coding: utf-8 -*-
"""Clash físico e por folga, sem Revit.
Tubo/eletroduto = cápsula (eixo + raio externo). Caixa = prisma (quadrado ou cilindro) do fundo ao tampo.
  tubo × tubo  : distância segmento-segmento − (rA + rB)
  tubo × caixa : distância com sinal (dentro = negativo) dos pontos do eixo (a cada 5 cm) ao prisma − r
Folga = menor valor por par de elementos. CRÍTICA: folga < −2 mm (colisão). ATENÇÃO: folga < regra 'folga' (0,20 m).
Pares da mesma rede não se testam. Entre redes por gravidade, encontro na ponta de um dos trechos = ligação provável
(não é conflito; vai para a lista de ligações para conferência)."""
import numpy as np
from .modelo import comprimento_planta, planta_local

TOL = -0.002


def segmentos(elementos, campo='pts_sol'):
    A, B, R, I = [], [], [], []
    for k, e in enumerate(elementos):
        P = e[campo]
        for a, b in zip(P[:-1], P[1:]):
            if np.linalg.norm(b - a) < 1e-6: continue
            A.append(a); B.append(b); R.append(e['de'] / 2); I.append(k)
    return np.array(A), np.array(B), np.array(R), np.array(I, int)


def dist_seg_seg(P0, P1, Q0, Q1):
    """distância mínima entre pares de segmentos (vetorizado; Ericson, Real-Time Collision Detection 5.1.9)."""
    d1 = P1 - P0; d2 = Q1 - Q0; r = P0 - Q0
    a = np.einsum('ij,ij->i', d1, d1); e = np.einsum('ij,ij->i', d2, d2); f = np.einsum('ij,ij->i', d2, r)
    c = np.einsum('ij,ij->i', d1, r); b = np.einsum('ij,ij->i', d1, d2)
    den = a * e - b * b
    s = np.where(den > 1e-12, np.clip((b * f - c * e) / np.where(den > 1e-12, den, 1), 0, 1), 0.0)
    t = (b * s + f) / np.where(e > 1e-12, e, 1)
    m0 = t < 0; m1 = t > 1
    t = np.clip(t, 0, 1)
    s = np.where(m0, np.clip(-c / np.where(a > 1e-12, a, 1), 0, 1), s)
    s = np.where(m1, np.clip((b - c) / np.where(a > 1e-12, a, 1), 0, 1), s)
    C1 = P0 + d1 * s[:, None]; C2 = Q0 + d2 * t[:, None]
    return np.linalg.norm(C1 - C2, axis=1), C1, C2


def sd_caixa(P, cx):
    """distância com sinal de pontos (n,3) ao prisma da caixa."""
    dz_out = np.maximum(cx['zb'] - P[:, 2], P[:, 2] - cx['zt'])
    if cx['forma'] == 'c':
        dp = np.hypot(P[:, 0] - cx['E'], P[:, 1] - cx['N']) - cx['meia']
        out = np.hypot(np.maximum(dp, 0), np.maximum(dz_out, 0))
        ins = np.maximum(dp, dz_out)
    else:
        qx, qy = planta_local(cx, P[:, 0], P[:, 1])
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(dz_out, 0) ** 2)
        ins = np.maximum(np.maximum(qx, qy), dz_out)
    return np.where(ins > 0, out, ins)


def amostra(P, passo=0.05):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / passo)))
        out.extend(a + (b - a) * (j / k) for j in range(1, k + 1))
    return np.array(out)


def _perto_da_ponta(e, pt, tol):
    P = e['pts']
    return min(np.hypot(*(P[0, :2] - pt[:2])), np.hypot(*(P[-1, :2] - pt[:2]))) < tol


LIGACAO_ENTRE = [{'AP', 'DRE'}]      # disciplinas diferentes que podem se ligar (pluvial e drenagem); a mesma disciplina sempre pode


def _liga(disc_a, disc_b, regras):
    if disc_a == disc_b: return True
    return any({disc_a, disc_b} <= set(g) for g in regras.get('ligacao_entre', LIGACAO_ENTRE))


def contorno(c, passo=0.05):
    """pontos (n,2) do contorno da caixa em planta."""
    if c['forma'] == 'c':
        a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        return np.column_stack([c['E'] + c['meia'] * np.cos(a), c['N'] + c['meia'] * np.sin(a)])
    mx, my, rot = (c['mx'], c['my'], c['rot']) if c['forma'] == 'r' else (c['meia'], c['meia'], 0.0)
    L = np.array([[-mx, -my], [mx, -my], [mx, my], [-mx, my], [-mx, -my]])
    pts = []
    for a, b in zip(L[:-1], L[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / passo)))
        pts.extend(a + (b - a) * (j / k) for j in range(k))
    P = np.array(pts); cs, sn = np.cos(rot), np.sin(rot)
    return np.column_stack([c['E'] + P[:, 0] * cs - P[:, 1] * sn, c['N'] + P[:, 0] * sn + P[:, 1] * cs])


def _sd_planta(P, c):
    """distância com sinal (dentro = negativo) de pontos 2D ao contorno da caixa em planta."""
    if c['forma'] == 'c':
        return np.hypot(P[:, 0] - c['E'], P[:, 1] - c['N']) - c['meia']
    qx, qy = planta_local(c, P[:, 0], P[:, 1])
    fora = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    return np.where((qx > 0) | (qy > 0), fora, np.maximum(qx, qy))


def folga_caixas(c1, c2):
    """folga entre duas caixas (prismas): negativa quando se sobrepõem; devolve (folga, ponto E, N)."""
    P1, P2 = contorno(c1), contorno(c2)
    s1 = _sd_planta(P1, c2); s2 = _sd_planta(P2, c1)
    i1, i2 = int(np.argmin(s1)), int(np.argmin(s2))
    dp, pt = (s1[i1], P1[i1]) if s1[i1] <= s2[i2] else (s2[i2], P2[i2])
    dz = max(c1['zb'] - c2['zt'], c2['zb'] - c1['zt'])
    folga = float(np.hypot(max(dp, 0), dz)) if dz > 0 else float(dp)
    return folga, pt


def gravidade(folga, regra_folga):
    if folga < TOL: return 'CRÍTICA'
    if folga < regra_folga: return 'ATENÇÃO'
    return None


def detectar(elementos, caixas, regras, campo='pts_sol', tol_ligacao=0.8):
    folga_min = regras['folga']
    A, B, R, I = segmentos(elementos, campo)
    lo = np.minimum(A, B) - R[:, None]; hi = np.maximum(A, B) + R[:, None]
    n = len(A); res = {}
    rede = np.array([e['rede'] for e in elementos])
    for i in range(n - 1):
        j = np.arange(i + 1, n)
        j = j[(rede[I[j]] != rede[I[i]])]
        if not len(j): continue
        ov = np.all((lo[j] - folga_min <= hi[i]) & (hi[j] + folga_min >= lo[i]), axis=1)
        j = j[ov]
        if not len(j): continue
        d, C1, C2 = dist_seg_seg(np.repeat(A[i:i + 1], len(j), 0), np.repeat(B[i:i + 1], len(j), 0), A[j], B[j])
        g = d - R[i] - R[j]
        for k in np.nonzero(g < folga_min)[0]:
            ka, kb = I[i], I[j[k]]
            key = (min(ka, kb), max(ka, kb))
            if key not in res or g[k] < res[key]['folga']:
                ca, cb = (C1[k], C2[k]) if ka < kb else (C2[k], C1[k])
                res[key] = {'folga': float(g[k]), 'pa': ca, 'pb': cb}
    out = []
    for (ka, kb), r in res.items():
        ea, eb = elementos[ka], elementos[kb]
        pt = (r['pa'] + r['pb']) / 2
        lig = (ea['tipo'] == 'gravidade' and eb['tipo'] == 'gravidade' and
               (_perto_da_ponta(ea, pt, tol_ligacao) or _perto_da_ponta(eb, pt, tol_ligacao)))
        out.append({'tipo': 'tubo×tubo', 'a': ea['id'], 'b': eb['id'], 'ka': ka, 'kb': kb, 'folga': r['folga'],
                    'E': float(pt[0]), 'N': float(pt[1]), 'z': float(pt[2]), 'zA': float(r['pa'][2]), 'zB': float(r['pb'][2]),
                    'ligacao': lig, 'gravidade': gravidade(r['folga'], folga_min)})
    # tubos × caixas
    for k, e in enumerate(elementos):
        P = amostra(e[campo]); r = e['de'] / 2
        plo, phi = P.min(0) - r, P.max(0) + r
        for c in caixas:
            if c['rede'] == e['rede']: continue
            m = c['meia'] + folga_min
            if plo[0] > c['E'] + m or phi[0] < c['E'] - m or plo[1] > c['N'] + m or phi[1] < c['N'] - m or plo[2] > c['zt'] + folga_min or phi[2] < c['zb'] - folga_min:
                continue
            sd = sd_caixa(P, c) - r
            q = int(np.argmin(sd))
            if sd[q] >= folga_min: continue
            # trecho por gravidade de outra rede que termina dentro/encostado na caixa = ligação (ex.: dreno do campo na CA da pluvial)
            lig = (e['tipo'] == 'gravidade' and _liga(e['disc'], c['disc'], regras) and
                   _perto_da_ponta(e, np.array([c['E'], c['N']]), c['meia'] + tol_ligacao))
            out.append({'tipo': 'tubo×caixa', 'a': e['id'], 'b': c['id'], 'ka': k, 'kb': None, 'folga': float(sd[q]),
                        'E': float(P[q, 0]), 'N': float(P[q, 1]), 'z': float(P[q, 2]), 'zA': float(P[q, 2]), 'zB': None,
                        'ligacao': lig, 'gravidade': gravidade(float(sd[q]), folga_min)})
    # caixas × caixas (de redes diferentes): caixa de passagem ou equipamento em cima de PV/CA etc.
    if caixas:
        cE = np.array([c['E'] for c in caixas]); cN = np.array([c['N'] for c in caixas]); cM = np.array([c['meia'] for c in caixas])
        for i, c1 in enumerate(caixas[:-1]):
            j = np.arange(i + 1, len(caixas))
            j = j[np.hypot(cE[j] - c1['E'], cN[j] - c1['N']) < cM[j] + c1['meia'] + folga_min]
            for k in j:
                c2 = caixas[k]
                if c2['rede'] == c1['rede'] or c2['disc'] == c1['disc']: continue   # mesma disciplina: caixa compartilhada entre pranchas
                f, pt = folga_caixas(c1, c2)
                if f >= folga_min: continue
                z = (max(c1['zb'], c2['zb']) + min(c1['zt'], c2['zt'])) / 2
                out.append({'tipo': 'caixa×caixa', 'a': c1['id'], 'b': c2['id'], 'ka': None, 'kb': None, 'folga': f,
                            'E': float(pt[0]), 'N': float(pt[1]), 'z': float(z), 'zA': None, 'zB': None,
                            'ligacao': False, 'gravidade': gravidade(f, folga_min)})
    out.sort(key=lambda c: c['folga'])
    return out


def resumo(conf):
    tot = {'CRÍTICA': 0, 'ATENÇÃO': 0, 'ligações': 0}
    for c in conf:
        if c['ligacao']: tot['ligações'] += 1
        else: tot[c['gravidade']] += 1
    return tot


# ------------------------------------------------------------------ forma real (malha) das peças de estrutura/equipamento
def _casco(P):
    P = np.unique(np.round(P, 4), axis=0)
    if len(P) < 3: return P
    P = P[np.lexsort((P[:, 1], P[:, 0]))]
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in P[::-1]:
        while len(hi) >= 2 and cr(hi[-2], hi[-1], q) <= 0: hi.pop()
        hi.append(q)
    return np.array(lo[:-1] + hi[:-1])


def _sd_casco(H, q):
    """distância com sinal (dentro < 0) do ponto 2D q ao polígono convexo H (anti-horário)."""
    if len(H) < 3: return float(np.min(np.hypot(H[:, 0] - q[0], H[:, 1] - q[1]))) if len(H) else np.inf
    dmin = np.inf; dentro = True
    for a, b in zip(H, np.roll(H, -1, 0)):
        ab = b - a; L2 = float(ab @ ab)
        t = 0.0 if L2 < 1e-12 else float(np.clip((q - a) @ ab / L2, 0, 1))
        dmin = min(dmin, float(np.hypot(*(a + ab * t - q))))
        if ab[0] * (q[1] - a[1]) - ab[1] * (q[0] - a[0]) < 0: dentro = False
    return -dmin if dentro else dmin


def _secao(T, z):
    pts = []
    for a, b in ((T[:, 0], T[:, 1]), (T[:, 1], T[:, 2]), (T[:, 2], T[:, 0])):
        m = ((a[:, 2] - z) * (b[:, 2] - z) <= 0) & (np.abs(a[:, 2] - b[:, 2]) > 1e-9)
        s = (z - a[m, 2]) / (b[m, 2] - a[m, 2])
        pts.append(a[m, :2] + (b[m, :2] - a[m, :2]) * s[:, None])
    P = np.vstack(pts) if pts else np.zeros((0, 2))
    return _casco(P) if len(P) else None


def folga_malha(P, r, T, passo=0.02):
    """folga do tubo (eixo P, raio r) contra a FORMA REAL da peça (triângulos T (n,3,3), UTM): em cada ponto do eixo e em 5 alturas
    da seção do tubo, corta a malha nessa altura (fecho convexo) e mede em planta (método da Jandaíra, folga_forma_real.py).
    A sapata cônica afina para cima: a caixa envolvente acusa colisão que não existe."""
    zlo, zhi = float(T[:, :, 2].min()), float(T[:, :, 2].max())
    Q = amostra(P, passo); lo = T.reshape(-1, 3)[:, :2].min(0) - 1.0 - r; hi = T.reshape(-1, 3)[:, :2].max(0) + 1.0 + r
    Q = Q[np.all((Q[:, :2] >= lo) & (Q[:, :2] <= hi), axis=1)]
    if not len(Q): return np.inf
    melhor = np.inf; cache = {}
    for q in Q:
        if q[2] - r > zhi: melhor = min(melhor, q[2] - r - zhi); continue
        if q[2] + r < zlo: melhor = min(melhor, zlo - q[2] - r); continue
        for f in (-1.0, -0.5, 0.0, 0.5, 1.0):
            z = q[2] + f * r * 0.999
            if z < zlo or z > zhi: continue
            k = round(z, 2)
            if k not in cache: cache[k] = _secao(T, k)
            H = cache[k]
            if H is None or not len(H): continue
            melhor = min(melhor, _sd_casco(H, q[:2]) - r * np.sqrt(max(0.0, 1 - f * f)))
    return melhor


def refinar_forma(conf, elementos, caixas, regras):
    """recalcula pela forma real os conflitos tubo × caixa cuja caixa traz info['malha'] (triângulos UTM); o que fica livre sai."""
    ids = {e['id']: e for e in elementos}; cx = {c['id']: c for c in caixas}; out = []
    for c in conf:
        C = cx.get(c['b']) if c['tipo'] == 'tubo×caixa' else None
        if C is None or C['info'].get('malha') is None or c['a'] not in ids:
            out.append(c); continue
        e = ids[c['a']]
        f = folga_malha(e['pts_sol'], e['de'] / 2, np.asarray(C['info']['malha'], float))
        if not np.isfinite(f): f = c['folga']
        g = gravidade(f, regras['folga'])
        if g is None: continue
        out.append(dict(c, folga=float(f), gravidade=g, forma_real=True))
    return out
