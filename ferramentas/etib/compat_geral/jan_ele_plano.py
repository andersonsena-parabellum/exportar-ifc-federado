# -*- coding: utf-8 -*-
"""Jandaíra — Fase B (elétrica), regra "só profundidade" (usuário, 18/10/2026):
 1. cada corrida de eletrodutos (peças encadeadas do mesmo trecho) desce até o topo ficar a 0,70 m do terreno do IMP (NBR 5410, P1);
 2. onde ainda bate em tubo/caixa de outra rede, faz um MERGULHO local por baixo do obstáculo (10 cm de folga, rampas 1:2)
    — muda só o perfil, não o traçado; limite: eixo a 1,60 m do terreno;
 3. caixas de passagem ficam com o fundo 10 cm abaixo do eletroduto mais fundo que chega nelas (topo no terreno);
 4. só o que não se resolve assim muda de traçado: caixa que contém tubo/caixa de outra rede anda 0,5–2,0 m (os eletrodutos acompanham)
    e eletroduto que passaria por baixo de poço/fundação fundo demais (lista para desvio).
Geometria: compat_R01/geo_exec (PCI já revisado). Saída: compat_R01/ele_plano.json + resumo."""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
D = os.path.dirname(JD.G); GX = os.path.join(D, 'geo_exec')
RECOB, FOLGA_V, FOLGA_H, RAMPA, PROF_MAX = float(os.environ.get('JAN_ELE_RECOB', '0.70')), 0.10, 0.15, 2.0, 1.60
SUF = os.environ.get('JAN_SUFIXO', '')
# obstáculos que a corrida CONTORNA em planta (desvio em jan_ele_desvios.py) em vez de mergulhar por baixo
CONTORNAR = {('ELE-I-28', 'CX-SDAI-03'), ('ELE-I-13', 'CX-10'), ('ELE-I-31', 'PVE-10'), ('ELE-I-01', 'PCI-AH-10')}


def raiz(t): return t.rsplit('.', 1)[0] if '.' in t else t


def carregar():
    SEG, MESH = JD.carregar(g=GX, est='daniel'); JD.agrupar_caixas(SEG, MESH)
    return SEG, MESH


def corridas(SEG):
    """corridas = peças ELE horizontais encadeadas (ponta com ponta) do mesmo trecho-raiz."""
    hz = [i for i, s in enumerate(SEG) if s['disc'] == 'ELE' and np.linalg.norm(s['b0'][:2] - s['a0'][:2]) > 0.05
          and abs(s['b0'][2] - s['a0'][2]) < 0.5 * np.linalg.norm(s['b0'][:2] - s['a0'][:2]) and max(s['a0'][2], s['b0'][2]) < -0.15]
    por = collections.defaultdict(list)
    for i in hz: por[raiz(SEG[i]['trecho'])].append(i)
    runs = []
    for r, ids in por.items():
        rest = set(ids)
        while rest:
            i0 = rest.pop(); ch = [(i0, False)]
            for lado in (0, 1):
                cresce = True
                while cresce:
                    cresce = False
                    if lado == 0: i, inv = ch[-1]; fim = SEG[i]['a0'] if inv else SEG[i]['b0']
                    else: i, inv = ch[0]; fim = SEG[i]['b0'] if inv else SEG[i]['a0']
                    for j in list(rest):
                        a, b = SEG[j]['a0'], SEG[j]['b0']
                        if lado == 0:
                            if np.linalg.norm(a - fim) < 0.01: ch.append((j, False)); rest.discard(j); cresce = True; break
                            if np.linalg.norm(b - fim) < 0.01: ch.append((j, True)); rest.discard(j); cresce = True; break
                        else:
                            if np.linalg.norm(b - fim) < 0.01: ch.insert(0, (j, False)); rest.discard(j); cresce = True; break
                            if np.linalg.norm(a - fim) < 0.01: ch.insert(0, (j, True)); rest.discard(j); cresce = True; break
            runs.append(dict(raiz=r, pecas=ch))
    return runs


def poli(SEG, run):
    P = []; corte = [0.0]
    for i, inv in run['pecas']:
        a, b = (SEG[i]['b0'], SEG[i]['a0']) if inv else (SEG[i]['a0'], SEG[i]['b0'])
        if not P: P.append(a.copy())
        P.append(b.copy())
    P = np.array(P); s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1))])
    return P, s


def xy_em(P, s, t):
    k = int(np.clip(np.searchsorted(s, t) - 1, 0, len(s) - 2)); f = (t - s[k]) / max(s[k + 1] - s[k], 1e-9)
    return P[k, :2] + (P[k + 1, :2] - P[k, :2]) * f


def douglas(pts, tol=0.004):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; d = b - a; L = np.linalg.norm(d)
    dist = [abs(np.cross(d, p - a)) / L if L > 1e-9 else np.linalg.norm(p - a) for p in pts[1:-1]]
    k = int(np.argmax(dist)) + 1
    if dist[k - 1] > tol: return douglas(pts[:k + 1], tol)[:-1] + douglas(pts[k:], tol)
    return [a, b]


class Plano:
    def __init__(self):
        self.SEG, self.MESH = carregar(); self.T = JD.Terreno(g=GX)
        self.runs = corridas(self.SEG); self.dips = collections.defaultdict(list)   # run idx -> [(s1, s2, zreq, obstáculo)]
        self.base = {}; self.caixa_dxy = {}; self.sem_solucao = []
        for k, r in enumerate(self.runs):
            P, s = poli(self.SEG, r); r['P'], r['s'] = P, s
            de = max(self.SEG[i]['de'] for i, _ in r['pecas']); r['de'] = de
            zr = []
            for t in np.arange(0, s[-1] + 1e-9, 0.5):
                x, y = xy_em(P, s, t); zt = self.T.z(x, y)
                if not np.isnan(zt): zr.append(zt - RECOB - de / 2)
            z0 = min(P[:, 2].min(), min(zr) if zr else P[:, 2].min())
            self.base[k] = z0

    def perfil(self, k):
        r = self.runs[k]; s = r['s']; L = s[-1]; z0 = self.base[k]
        ts = np.unique(np.concatenate([np.arange(0, L, 0.05), [L], s]))
        # sem recobrimento mínimo (cota atual): mantém o perfil original de cada peça; com recobrimento: corrida horizontal na cota-base
        z = np.interp(ts, s, r['P'][:, 2]) if RECOB <= 0 else np.full(len(ts), z0)
        for s1, s2, zq, _ in self.dips[k]:
            zz = zq + np.maximum(0, np.maximum(s1 - ts, ts - s2)) / RAMPA
            z = np.minimum(z, zz)
        return ts, z

    def geometria(self):
        """SEG/MESH novos: corridas viram sub-segmentos com o perfil; caixas movidas/aprofundadas."""
        S2 = [s for s in self.SEG if not any(self.SEG.index(s) == i for r in self.runs for i, _ in r['pecas'])] if False else None
        ids_run = {i for r in self.runs for i, _ in r['pecas']}
        S2 = [dict(s) for j, s in enumerate(self.SEG) if j not in ids_run]
        self.sub = {}
        for k, r in enumerate(self.runs):
            ts, z = self.perfil(k); P, s = r['P'], r['s']
            pts = [np.array([*xy_em(P, s, t), zz]) for t, zz in zip(ts, z)]
            # mantém os vértices originais (juntas das peças) e simplifica o resto
            pts2 = [np.array([t, zz]) for t, zz in zip(ts, z)]
            keep = douglas(pts2)
            tk = sorted(set([round(p[0], 4) for p in keep] + [round(x, 4) for x in s]))
            zk = np.interp(tk, ts, z)
            V = [np.array([*xy_em(P, s, t), zz]) for t, zz in zip(tk, zk)]
            self.sub[k] = V
            base = self.SEG[r['pecas'][0][0]]
            for m in range(len(V) - 1):
                d = dict(base); d.update(id=f"{base['id']}~{k}.{m}", a=V[m].copy(), b=V[m + 1].copy(), a0=V[m].copy(), b0=V[m + 1].copy(), dz=0.0, de=r['de'], trecho=r['raiz'], run=k)
                S2.append(d)
        M2 = [dict(M) for M in self.MESH]
        for M in M2:
            off = self.caixa_dxy.get((M['fonte'], M.get('grupo')))
            if off is not None and M['disc'] == 'ELE':
                o = np.array([off[0], off[1], 0.0]); M['tri'] = M['tri'] + o; M['lo'] = M['lo'] + o; M['hi'] = M['hi'] + o
                if 'glo' in M: M['glo'] = M['glo'] + o; M['ghi'] = M['ghi'] + o
        # eletrodutos que chegam numa caixa movida acompanham a ponta
        for (f, g), off in self.caixa_dxy.items():
            ref = next((M for M in M2 if M['fonte'] == f and M.get('grupo') == g and 'glo' in M), None)
            if ref is None: continue
            lo, hi = ref['glo'] - np.array([off[0], off[1], 0]), ref['ghi'] - np.array([off[0], off[1], 0])
            for s in S2:
                if s['disc'] != 'ELE': continue
                for e in ('a', 'b'):
                    p = s[e]
                    if lo[0] - 0.15 <= p[0] <= hi[0] + 0.15 and lo[1] - 0.15 <= p[1] <= hi[1] + 0.15:
                        s[e] = p + np.array([off[0], off[1], 0]); s[e + '0'] = s[e].copy()
        self.ajustar_caixas(S2, M2)
        return S2, M2

    def ajustar_caixas(self, S2, M2):
        grupos = collections.defaultdict(list)
        for M in M2:
            if M['disc'] == 'ELE' and 'glo' in M and M['cat'].startswith('Equip') and M['grupo'].startswith('CX-'): grupos[M['grupo']].append(M)
        self.prof_caixa = {}
        for g, L in grupos.items():
            lo = np.min([M['lo'] for M in L], 0); hi = np.max([M['hi'] for M in L], 0); fundos = []
            for s in S2:
                if s['disc'] != 'ELE': continue
                for p in (s['a'], s['b']):
                    if lo[0] - 0.15 <= p[0] <= hi[0] + 0.15 and lo[1] - 0.15 <= p[1] <= hi[1] + 0.15: fundos.append(p[2] - s['de'] / 2)
            if not fundos: continue
            novo = min(fundos) - 0.10; top = hi[2]; velho = lo[2]
            self.prof_caixa[g] = (top - novo, top - velho)
            if abs(novo - velho) < 0.005: continue
            k = (top - novo) / (top - velho)
            for M in L:
                Tt = M['tri'].copy(); Tt[..., 2] = top - (top - Tt[..., 2]) * k
                M['tri'] = Tt; M['lo'] = Tt.reshape(-1, 3).min(0); M['hi'] = Tt.reshape(-1, 3).max(0); M.pop('samp', None)
                M['glo'] = np.array([*M['glo'][:2], novo]) if 'glo' in M else None

    def conflitos(self, S2, M2):
        IDX = mt.Indice(S2, M2); out = []
        for i, s in enumerate(S2):
            if s['disc'] != 'ELE': continue
            for t, j, g, pt in mt.avaliar_seg(i, IDX):
                B = S2[j] if t == 'S' else M2[j]
                if B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes'): continue
                if g < mt.TOL: out.append(('S', i, t, j, g, pt))
        for j, M in enumerate(M2):
            if M['disc'] != 'ELE' or 'glo' not in M or not str(M.get('grupo', '')).startswith('CX-'): continue
            for t, k, g, pt in mt.avaliar_mesh(j, IDX):
                B = S2[k] if t == 'S' else M2[k]
                if B['disc'] == 'ELE' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
                if g < mt.TOL: out.append(('M', j, t, k, g, pt))
        return out


def fundo_obstaculo(B, pt):
    if 'a' in B:   # tubo
        d = B['b'] - B['a']; L2 = d[0] ** 2 + d[1] ** 2
        t = 0.5 if L2 < 1e-9 else float(np.clip(((pt[0] - B['a'][0]) * d[0] + (pt[1] - B['a'][1]) * d[1]) / L2, 0, 1))
        return B['a'][2] + d[2] * t - B['de'] / 2, (B['a'], B['b'], B['de'] / 2)
    lo = B.get('glo') if B.get('glo') is not None else B['lo']; hi = B.get('ghi') if B.get('ghi') is not None else B['hi']
    return lo[2], (lo, hi, 0)


def intervalo(run, geo, de):
    """trecho (s1, s2) da corrida cujo eixo passa a menos de FOLGA_H do obstáculo em planta."""
    P, s = run['P'], run['s']; ts = np.arange(0, s[-1] + 1e-9, 0.05); dentro = []
    for t in ts:
        x, y = xy_em(P, s, t)
        if len(geo[0]) == 3 and geo[2] > 0:   # tubo
            a, b, r = geo; d = b[:2] - a[:2]; L2 = d @ d
            u = 0 if L2 < 1e-12 else np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / L2, 0, 1)
            dist = math.hypot(x - a[0] - d[0] * u, y - a[1] - d[1] * u)
            if dist < r + de / 2 + FOLGA_H: dentro.append(t)
        else:
            lo, hi, _ = geo
            if lo[0] - de / 2 - FOLGA_H <= x <= hi[0] + de / 2 + FOLGA_H and lo[1] - de / 2 - FOLGA_H <= y <= hi[1] + de / 2 + FOLGA_H: dentro.append(t)
    return (min(dentro), max(dentro)) if dentro else None


if __name__ == '__main__':
    PL = Plano()
    print(f"corridas ELE: {len(PL.runs)} | descida até 0,70 m: média {np.mean([PL.runs[k]['P'][:,2].min() - PL.base[k] for k in PL.base]):.2f} m")
    for it in range(6):
        S2, M2 = PL.geometria(); C = PL.conflitos(S2, M2)
        novos = 0; caixas = collections.defaultdict(list)
        for tipo, i, t, j, g, pt in C:
            if tipo == 'S':
                s = S2[i]; k = s['run']; B = S2[j] if t == 'S' else M2[j]
                if (PL.runs[k]['raiz'], B.get('grupo', B.get('trecho'))) in CONTORNAR: continue
                fb, geo = fundo_obstaculo(B, pt); zq = fb - FOLGA_V - PL.runs[k]['de'] / 2
                iv = intervalo(PL.runs[k], geo, PL.runs[k]['de'])
                if iv is None: continue
                zt = PL.T.z(pt[0], pt[1])
                if not np.isnan(zt) and zq < zt - PROF_MAX:
                    key = (PL.runs[k]['raiz'], B.get('grupo', B.get('trecho')))
                    if key not in [x[:2] for x in PL.sem_solucao]: PL.sem_solucao.append(key + (round(zt - zq, 2),))
                    continue
                if any(abs(d[0] - iv[0]) < 0.05 and abs(d[1] - iv[1]) < 0.05 and d[2] <= zq + 1e-3 for d in PL.dips[k]): continue
                PL.dips[k].append((iv[0], iv[1], zq, B.get('grupo', B.get('trecho')))); novos += 1
            else:
                M = M2[i]; caixas[M['grupo']].append((t, j, g))
        # caixas que contêm tubo/caixa de outra rede: tenta posição nova (0,5–2,0 m), uma vez por caixa; avalia só a caixa no índice atual
        movidas = 0
        IDX = mt.Indice(S2, M2)
        for g, lst in caixas.items():
            if ('ELE', g) in PL.caixa_dxy: continue
            js = [jj for jj, M in enumerate(M2) if M['disc'] == 'ELE' and M.get('grupo') == g]
            if not js: continue
            def custo_cx():
                c = 0
                for jj in js:
                    for t2, k2, g2, p2 in mt.avaliar_mesh(jj, IDX):
                        B2 = S2[k2] if t2 == 'S' else M2[k2]
                        if B2['disc'] == 'ELE' or (B2['disc'] == 'EST' and B2['cat'] in ('Pisos', 'Paredes')): continue
                        c += 100 if g2 < mt.TOL else (3 if g2 < 0.10 else 1)
                return c
            best = None
            for o in (0.5, 1.0, 1.5, 2.0):
                for ang in range(0, 360, 45):
                    d = (o * math.cos(math.radians(ang)), o * math.sin(math.radians(ang)))
                    for jj in js: mt.mover_mesh(jj, d, IDX)
                    c = custo_cx() + 2 * o
                    if best is None or c < best[0]: best = (c, d)
            for jj in js: mt.mover_mesh(jj, (0.0, 0.0), IDX)
            PL.caixa_dxy[('ELE', g)] = best[1]; movidas += 1
            print(f'   caixa {g}: {math.hypot(*best[1]):.1f} m (custo {best[0]:.0f})', flush=True)
        print(f'iteração {it+1}: conflitos {len(C)} | mergulhos novos {novos} | caixas movidas {movidas}', flush=True)
        if not novos and not movidas: break
    S2, M2 = PL.geometria(); C = PL.conflitos(S2, M2)
    nd = sum(len(v) for v in PL.dips.values())
    print(f'mergulhos: {nd} em {sum(1 for v in PL.dips.values() if v)} corridas | caixas com posição nova: {len(PL.caixa_dxy)} | sem solução por profundidade: {len(PL.sem_solucao)}')
    for x in PL.sem_solucao: print('   desvio necessário:', x)
    for (f, g), d in PL.caixa_dxy.items(): print(f'   caixa {g}: mover {math.hypot(*d):.1f} m')
    print('conflitos ELE restantes:', len(C))
    for tipo, i, t, j, g, pt in C:
        A = S2[i] if tipo == 'S' else M2[i]; B = S2[j] if t == 'S' else M2[j]
        print(f"   {A.get('trecho') if tipo=='S' else A['grupo']} × {B['disc']} {B.get('grupo', B.get('trecho'))} {g*100:.0f} cm ({pt[0]:.1f};{pt[1]:.1f}) z={pt[2]:.2f}")
    out = dict(base={PL.runs[k]['raiz'] + '#' + str(k): PL.base[k] for k in PL.base},
               corridas=[dict(raiz=r['raiz'], pecas=[[SEG_id, inv] for SEG_id, inv in [(PL.SEG[i]['id'], inv) for i, inv in r['pecas']]],
                              vertices=[list(map(float, v)) for v in PL.sub[k]]) for k, r in enumerate(PL.runs)],
               caixas={g: dict(dxy=list(PL.caixa_dxy.get(('ELE', g), (0.0, 0.0))), prof=PL.prof_caixa.get(g, (None, None))[0], prof_hoje=PL.prof_caixa.get(g, (None, None))[1]) for g in PL.prof_caixa},
               sem_solucao=PL.sem_solucao)
    json.dump(out, open(os.path.join(D, 'ele_plano' + SUF + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    import pickle; pickle.dump((S2, M2), open(os.path.join(D, 'ele_plano' + SUF + '_geo.pkl'), 'wb'))
