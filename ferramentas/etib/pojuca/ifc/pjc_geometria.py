# -*- coding: utf-8 -*-
"""Pojuca — limpeza da geometria antes do estudo de cota (Revisão de qualidade de 26/10, itens C2, C4, C6, D3 e D6):
  - tubo de gravidade repetido ou contido em outro (DRE-014 por cima dos últimos 3,7 m do DRE-003; ramais desenhados em linha dupla que
    só se separam depois do corte na face do prédio): fica o que tem rótulo, depois o de maior Ø, depois o mais longo;
  - eletrodutos de bancos diferentes no mesmo caminho (EL1-029 e EL1-050): o segundo anda para o lado, DE + 0,05 m, com as pontas nas
    caixas e transições a 45°;
  - eletroduto e alarme (PEAD flexível): canto acima de 30° vira curva no próprio tubo, raio 0,30 m, em passos de até 15°; ponta que
    volta sobre si mesma (vértice de mais de 150°) sai;
  - base de poste atravessada por eletroduto que não chega nela (o eletroduto passa pela base): base e poste andam até 1,50 m (aplicar e
    avisar), para o lado livre;
  - perfil das redes de pressão com inclinação máxima de 1:0,8 (perfil_suave): no degrau de piso externo do IMP o perfil subia na
    vertical (degrau em Z de 0,34 m em 0,31 m no EL1-012)."""
import math
import numpy as np
from shapely.geometry import LineString, Point, Polygon


def _comp(P):
    return float(np.sum(np.hypot(*np.diff(np.asarray(P)[:, :2], axis=0).T)))


def sem_repetidos(E, lt, tol=0.25, contido=0.10, log=print):
    G = [e for e in E if e['tipo'] == 'gravidade']
    chave = lambda e: (bool(e['info'].get('material')), lt.fl(e['info'].get('DN_mm')) or 0, _comp(e['pts']))
    fora = set()
    for i, a in enumerate(G):
        for b in G[i + 1:]:
            if a['id'] in fora or b['id'] in fora or a['disc'] != b['disc']: continue
            pa, pb = a['pts'][[0, -1], :2], b['pts'][[0, -1], :2]
            if min(np.abs(pa - pb).max(), np.abs(pa - pb[::-1]).max()) <= tol:
                fora.add(b['id'] if chave(a) >= chave(b) else a['id']); continue
            La, Lb = LineString(a['pts'][:, :2]), LineString(b['pts'][:, :2])
            curto, longo, Lc, Ll = (a, b, La, Lb) if La.length < Lb.length else (b, a, Lb, La)
            if Lc.length > 0.3 and Ll.buffer(contido).contains(Lc): fora.add(curto['id'])
    if fora: log(f"  {len(fora)} tubos repetidos ou contidos em outro saíram: {', '.join(sorted(x.split(':', 1)[1] for x in fora))}")
    return [e for e in E if e['id'] not in fora]


def _deslocar_rota(P, d):
    """rota deslocada d m para a esquerda no miolo, pontas fixas, transições a 45° de comprimento |d|."""
    P = np.asarray(P, float); Z = P[:, 2] if P.shape[1] > 2 else None
    Q2 = P[:, :2]
    S = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(Q2, axis=0).T))]); L = S[-1]
    if L < 2 * abs(d) + 0.5: return P
    s = np.unique(np.concatenate([S, [abs(d), L - abs(d)]])); s = s[(s >= abs(d) - 1e-9) & (s <= L - abs(d) + 1e-9)]
    Q = np.column_stack([np.interp(s, S, Q2[:, 0]), np.interp(s, S, Q2[:, 1])])
    dirs = np.diff(Q, axis=0); dirs /= np.linalg.norm(dirs, axis=1)[:, None] + 1e-12
    nrm = np.column_stack([-dirs[:, 1], dirs[:, 0]])
    nv = np.vstack([nrm[0], (nrm[:-1] + nrm[1:]) / 2, nrm[-1]]) if len(nrm) > 1 else np.vstack([nrm[0], nrm[0]])
    nv /= np.linalg.norm(nv, axis=1)[:, None] + 1e-12
    R = np.vstack([Q2[0], Q + d * nv, Q2[-1]])
    if Z is None: return R
    Sr = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(R, axis=0).T))])
    return np.column_stack([R, np.interp(Sr / Sr[-1] * L, S, Z)])


def separar_bancos(E, log=print, min_sobre=0.30):
    """eletroduto de outro banco no mesmo caminho: anda para o lado (o mais curto dos dois)."""
    els = [e for e in E if e['tipo'] == 'pressao' and e['disc'] == 'ELE']
    feitos = []
    for i, a in enumerate(els):
        for b in els[i + 1:]:
            La, Lb = LineString(a['pts'][:, :2]), LineString(b['pts'][:, :2])
            dist = (a['de'] + b['de']) / 2 + 0.02
            if La.distance(Lb) > dist: continue
            sob = La.intersection(Lb.buffer(dist)).length
            if sob < min_sobre: continue
            m = b if Lb.length <= La.length else a; o = a if m is b else b
            d = (a['de'] + b['de']) / 2 + 0.05
            esq = LineString(_deslocar_rota(m['pts'][:, :2], d)); dir_ = LineString(_deslocar_rota(m['pts'][:, :2], -d))
            Lo = LineString(o['pts'][:, :2])
            novo = _deslocar_rota(m['pts'], d if esq.distance(Lo) >= dir_.distance(Lo) else -d)
            m.setdefault('pts_planta0', m['pts'].copy()); m['pts'] = novo; m['pts_sol'] = novo.copy(); m.pop('S', None)
            feitos.append(f"{m['trecho']} (ao lado do {o['trecho']}, {sob:.1f} m juntos)")
    if feitos: log(f"  {len(feitos)} eletrodutos no mesmo caminho de outro banco foram para o lado: {', '.join(feitos)}")


def curvas_no_tubo(E, log=print, lim=30.0, raio=0.30, passo=15.0):
    """PEAD flexível (elétrica e alarme): canto acima de 'lim' vira arco no próprio tubo; vértice que volta sobre si sai."""
    n_c = n_v = 0
    for e in E:
        if e['tipo'] != 'pressao' or e['disc'] not in ('ELE', 'SDAI') or len(e['pts']) < 3: continue
        P = np.asarray(e['pts'], float)
        mud = True
        while mud and len(P) >= 3:                  # vértice com volta (> 150°) sai
            mud = False
            for k in range(1, len(P) - 1):
                u, v = P[k, :2] - P[k - 1, :2], P[k + 1, :2] - P[k, :2]
                if np.hypot(*u) < 1e-6 or np.hypot(*v) < 1e-6: P = np.delete(P, k, 0); mud = True; break
                ang = math.degrees(math.acos(np.clip(u @ v / np.hypot(*u) / np.hypot(*v), -1, 1)))
                if ang > 150: P = np.delete(P, k, 0); mud = True; n_v += 1; break
        out = [P[0]]
        for k in range(1, len(P) - 1):
            a, b, c = P[k - 1], P[k], P[k + 1]
            u, v = b[:2] - a[:2], c[:2] - b[:2]; lu, lv = np.hypot(*u), np.hypot(*v)
            ang = math.degrees(math.acos(np.clip(u @ v / lu / lv, -1, 1)))
            if ang <= lim + 0.5: out.append(b); continue
            r = min(raio, 0.45 * lu / math.tan(math.radians(ang) / 2), 0.45 * lv / math.tan(math.radians(ang) / 2))
            t = r * math.tan(math.radians(ang) / 2)
            p0 = b[:2] - u / lu * t; p1 = b[:2] + v / lv * t
            n = max(2, int(math.ceil(ang / passo)))
            # arco tangente nos dois lados (centro na bissetriz)
            nu = np.array([-u[1], u[0]]) / lu
            if (nu @ (v / lv)) < 0: nu = -nu
            cen = p0 + nu * r
            a0 = math.atan2(*(p0 - cen)[::-1]); a1 = math.atan2(*(p1 - cen)[::-1])
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            for j in range(n + 1):
                q = cen + r * np.array([math.cos(a0 + da * j / n), math.sin(a0 + da * j / n)])
                out.append(np.array([q[0], q[1], b[2]]))
            n_c += 1
        out.append(P[-1])
        Q = np.array(out)
        if len(Q) != len(e['pts']) or np.abs(Q - e['pts']).max() > 1e-6:
            e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = Q; e['pts_sol'] = Q.copy(); e.pop('S', None)
    if n_c or n_v: log(f'  elétrica e alarme: {n_c} cantos viraram curva no próprio tubo (raio 0,30 m), {n_v} vértices de volta saíram')


def bases_de_poste(E, C, ter, md, log=print, passo_max=1.50, folga=0.10):
    """base de poste atravessada por eletroduto que não termina nela: base + poste andam para o lado livre (até 1,50 m)."""
    def poli(c, E_=None, N_=None, b=0.0):
        E_ = c['E'] if E_ is None else E_; N_ = c['N'] if N_ is None else N_
        if c['forma'] == 'c': return Point(E_, N_).buffer(c['meia'] + b)
        mx, my, rot = c.get('mx', c['meia']), c.get('my', c['meia']), c.get('rot', 0.0)
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([E_, N_])
        return Polygon([p + s * (mx + b) * u + t * (my + b) * v for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    redes = [(e, LineString(e['pts'][:, :2])) for e in E if len(e['pts']) > 1]
    fixos = [c for c in C if not c['id'].endswith(':base') and c['disc'] != 'EST' or c['disc'] == 'EST']
    reg = []
    for b in [c for c in C if c['id'].endswith(':base') and c['info'].get('equipamento')]:
        pg = poli(b)
        def passa(e, Ls, pg_):
            if e['disc'] != 'ELE' or not Ls.intersects(pg_): return False
            return not any(pg_.buffer(0.05).contains(Point(*e['pts'][k, :2])) for k in (0, -1))
        cruz = [(e, Ls) for e, Ls in redes if passa(e, Ls, pg)]
        if not cruz: continue
        cx_ele = [c for c in C if c['disc'] == 'ELE' and not c['info'].get('equipamento')]
        na_cx = lambda q: any(abs(c['E'] - q[0]) < 2 and abs(c['N'] - q[1]) < 2 and max(md.planta_local(c, q[0], q[1])) < 0.10 for c in cx_ele)
        # pontas do poste: as que estão na base e não numa caixa de passagem (a caixa ao lado da base fica onde está)
        meus = [e for e, Ls in redes if e['disc'] == 'ELE' and any(pg.buffer(0.10).contains(Point(*e['pts'][k, :2])) and not na_cx(e['pts'][k])
                                                                   for k in (0, -1))]
        def livre(E_, N_):
            p2 = poli(b, E_, N_, folga)
            if any(Ls.intersects(p2) for e, Ls in redes if e not in meus): return False
            return not any(poli(c).intersects(p2) for c in C if c is not b and c['id'] != b['id'][:-5]
                           and abs(c['E'] - E_) < 6 and abs(c['N'] - N_) < 6)
        e0, L0 = cruz[0]; q = L0.interpolate(L0.project(Point(b['E'], b['N']))); n = np.array([b['E'] - q.x, b['N'] - q.y])
        n = n / np.hypot(*n) if np.hypot(*n) > 1e-6 else np.array([1.0, 0.0])
        dirs = [n, -n] + [np.array([math.cos(a), math.sin(a)]) for a in np.radians(np.arange(0, 360, 15))]
        achou = None
        for p in np.arange(0.10, passo_max + 1e-6, 0.10):
            for u in dirs:
                if livre(b['E'] + u[0] * p, b['N'] + u[1] * p): achou = u * p; break
            if achou is not None: break
        if achou is None: reg.append(f"{b['info']['nome']} (sem lugar livre até {passo_max:.2f} m)"); continue
        haste = next((c for c in C if c['id'] == b['id'][:-5]), None)
        for c in (b, haste):
            if c is None: continue
            z0 = float(ter.z([[c['E'], c['N']]])[0]); c['E0'], c['N0'] = c['E'], c['N']; c['E'] += achou[0]; c['N'] += achou[1]
            dz = float(ter.z([[c['E'], c['N']]])[0]) - z0
            if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
        for e in meus:
            for k in (0, -1):
                if pg.buffer(0.10).contains(Point(*e['pts'][k, :2])) and not na_cx(e['pts'][k]):
                    e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = e['pts'].copy(); e['pts'][k, :2] += achou; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
        reg.append(f"{b['info']['nome']} {np.hypot(*achou):.2f} m (o {', '.join(e['trecho'] for e, _ in cruz)} passava por ela)")
    if reg: log(f"  bases de poste atravessadas por eletroduto: {'; '.join(reg)}")
    return reg


def perfil_suave(P, ter, cob, de, k=0.80):
    """inclinação máxima de 1:k: o perfil só desce (o recobrimento nunca fica abaixo do mínimo) até a rampa caber."""
    P = np.asarray(P, float).copy()
    if len(P) < 3: return P
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
    z = P[:, 2].copy()
    for i in range(1, len(z)): z[i] = min(z[i], z[i - 1] + k * (s[i] - s[i - 1]))
    for i in range(len(z) - 2, -1, -1): z[i] = min(z[i], z[i + 1] + k * (s[i + 1] - s[i]))
    P[:, 2] = z
    return _limitar(P, ter, de, 1.95)          # e nunca abaixo de 1,95 m do terreno ao topo (o máximo é 2,00 m)


def separar_trechos(E, discs=('ELE', 'SDAI', 'HID', 'AF'), log=print, min_sobre=0.30):
    """depois dos contornos: dois trechos da mesma disciplina no mesmo caminho num pedaço (os eletrodutos do banco contornando a mesma
    caixa, HI-05 e HI-12 desenhados um sobre o outro): só o pedaço junto do outro anda para o lado (DE + 0,05 m), com rampas a 45°."""
    from preclash.desvio import _deslocar
    els = [e for e in E if e['tipo'] == 'pressao' and e['disc'] in discs and len(e['pts']) > 1]
    feitos = []
    for i, a in enumerate(els):
        for b in els[i + 1:]:
            if a['disc'] != b['disc']: continue
            La, Lb = LineString(a['pts'][:, :2]), LineString(b['pts'][:, :2])
            dist = (a['de'] + b['de']) / 2 + 0.02
            if La.distance(Lb) > dist: continue
            m, o = (b, a) if Lb.length <= La.length else (a, b)
            Lm, Lo = LineString(m['pts'][:, :2]), LineString(o['pts'][:, :2])
            sob = Lm.intersection(Lo.buffer(dist))
            if sob.is_empty or sob.length < min_sobre: continue
            gs = list(getattr(sob, 'geoms', [sob]))
            ss = [Lm.project(Point(q)) for g in gs for q in g.coords]
            s0, s1 = max(min(ss), 0.05), min(max(ss), Lm.length - 0.05)
            if s1 - s0 < min_sobre: continue
            d = (a['de'] + b['de']) / 2 + 0.05
            P2 = m['pts'][:, :2]
            cand = [(_deslocar(P2, s0, s1, sg * d), sg) for sg in (1, -1)]
            Q, sg = min(cand, key=lambda c: LineString(c[0]).intersection(Lo.buffer(dist)).length)   # o lado que sai de junto do outro
            S0 = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P2, axis=0).T))]); S1 = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
            z = np.interp(S1 / S1[-1] * S0[-1], S0, m['pts'][:, 2])
            novo = np.column_stack([Q, z])
            m.setdefault('pts_planta0', m['pts'].copy()); m['pts'] = novo; m['pts_sol'] = novo.copy(); m.pop('S', None)
            feitos.append(f"{m['trecho']} ({sob.length:.1f} m junto do {o['trecho']})")
    if feitos: log(f"  {len(feitos)} pedaços no mesmo caminho de outro trecho foram para o lado: {', '.join(feitos)}")


def pontas_nas_bases(E, C, md=None, log=print):
    """eletroduto que termina dentro da base do poste: a ponta fica na face da base (o eletroduto sobe pela base até o poste)."""
    n = 0
    for b in [c for c in C if c['id'].endswith(':base') and c['info'].get('equipamento')]:
        mx, my, rot = b.get('mx', b['meia']), b.get('my', b['meia']), b.get('rot', 0.0)
        cs, sn = math.cos(rot), math.sin(rot)
        loc = lambda p: ((p[0] - b['E']) * cs + (p[1] - b['N']) * sn, -(p[0] - b['E']) * sn + (p[1] - b['N']) * cs)
        dentro = lambda p: (abs(loc(p)[0]) <= mx + 0.01 and abs(loc(p)[1]) <= my + 0.01) if b['forma'] != 'c' else np.hypot(p[0] - b['E'], p[1] - b['N']) <= b['meia'] + 0.01
        cx_ele = [c for c in C if c['disc'] == 'ELE' and not c['info'].get('equipamento')]
        for e in E:
            if e['tipo'] != 'pressao' or e['disc'] != 'ELE' or len(e['pts']) < 2: continue
            for k in (0, -1):
                if not dentro(e['pts'][k]): continue
                q0 = e['pts'][k]
                if md is not None and any(abs(c['E'] - q0[0]) < 2 and abs(c['N'] - q0[1]) < 2 and max(md.planta_local(c, q0[0], q0[1])) < 0.10 for c in cx_ele):
                    continue                                   # a ponta está na caixa de passagem ao lado da base
                j = 1 if k == 0 else -2
                a, q = e['pts'][k].copy(), e['pts'][j]
                if dentro(q): continue
                for t in np.linspace(0, 1, 201):
                    p = a + (q - a) * t
                    if not dentro(p): break
                P = e['pts'].copy(); P[k] = a + (q - a) * min(1.0, t + 0.01)
                e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None); n += 1
    if n: log(f'  {n} pontas de eletroduto ficaram na face da base do poste')


def _limitar(P, ter, de, prof):
    zt = ter.z(P[:, :2]); zt = np.where(np.isnan(zt), np.nanmin(zt), zt)
    P[:, 2] = np.maximum(P[:, 2], zt - prof - de / 2)
    return P


def _em_caixa(p, C, md, folga=0.05):
    return any(c['disc'] in ('DRE', 'ESG') and abs(c['E'] - p[0]) < 3 and abs(c['N'] - p[1]) < 3 and max(md.planta_local(c, p[0], p[1])) < folga for c in C)


def soldar_gravidade(E, C, md, tol=0.30, log=print):
    """ponta de tubo de gravidade fora de caixa a menos de 'tol' de outra ponta ou de um vértice de outro tubo da mesma rede (ligação
    presumida da extração: o desenho não encosta): as duas pontas vão para o mesmo ponto (C2/C6 da Revisão)."""
    G = [e for e in E if e['tipo'] == 'gravidade']
    pts = [(e, k) for e in G for k in (0, -1) if not _em_caixa(e['pts'][k], C, md)]
    n = 0; feitos = set()
    for i, (e, k) in enumerate(pts):
        if (id(e), k) in feitos: continue
        p = e['pts'][k, :2]
        melhor = None
        for f, j in pts[i + 1:]:
            if f is e or f['rede'] != e['rede'] or (id(f), j) in feitos: continue
            d = float(np.hypot(*(f['pts'][j, :2] - p)))
            if 0.005 < d < tol and (melhor is None or d < melhor[0]): melhor = (d, f, j, None)
        for f in G:
            if f is e or f['rede'] != e['rede']: continue
            for v in range(1, len(f['pts']) - 1):
                d = float(np.hypot(*(f['pts'][v, :2] - p)))
                if 0.005 < d < 0.20 and (melhor is None or d < melhor[0]): melhor = (d, f, None, v)
        if melhor is None: continue
        d, f, j, v = melhor
        if j is not None:
            m = (p + f['pts'][j, :2]) / 2
            for x, kk in ((e, k), (f, j)):
                x['pts'] = x['pts'].copy(); x['pts'][kk, :2] = m; x['pts_sol'] = x['pts'].copy(); x.pop('S', None); feitos.add((id(x), kk))
        else:
            e['pts'] = e['pts'].copy(); e['pts'][k, :2] = f['pts'][v, :2]; e['pts_sol'] = e['pts'].copy(); e.pop('S', None); feitos.add((id(e), k))
        n += 1
    if n: log(f'  {n} pontas de gravidade fora de caixa ligadas à peça vizinha (até {tol * 100:.0f} cm)')


def juntar_curtos(E, lim=0.50, log=print):
    """pedaço de gravidade menor que a conexão (CPS-DRE-038, 0,41 m entre dois nós) some e o trecho seguinte começa no lugar dele;
    pedaço de pressão menor que 0,25 m com uma ponta solta (HI-18 no barrilete) sai."""
    fora = set(); log_ = []
    G = [e for e in E if e['tipo'] == 'gravidade']
    for e in G:
        if _comp(e['pts']) >= lim: continue
        prox = next((f for f in G if f is not e and f['info'].get('de_no') == e['info'].get('para_no')), None)
        ant = next((f for f in G if f is not e and f['info'].get('para_no') == e['info'].get('de_no')), None)
        if prox is None or ant is None: continue
        prox['pts'] = prox['pts'].copy(); prox['pts'][0] = e['pts'][0]; prox['pts_sol'] = prox['pts'].copy(); prox.pop('S', None)
        prox['info']['de_no'] = e['info'].get('de_no'); fora.add(e['id']); log_.append(e['trecho'])
    P = [e for e in E if e['tipo'] == 'pressao']
    for e in P:
        if _comp(e['pts']) >= 0.25: continue
        livre = [k for k in (0, -1) if not any(f is not e and f['disc'] == e['disc'] and
                                                min(np.hypot(*(f['pts'][j, :2] - e['pts'][k, :2])) for j in (0, -1)) < 0.02 for f in P)]
        if livre: fora.add(e['id']); log_.append(e['trecho'])
    if fora: log(f"  {len(fora)} pedaços curtos saíram (o vizinho cobre): {', '.join(log_)}")
    return [e for e in E if e['id'] not in fora]
