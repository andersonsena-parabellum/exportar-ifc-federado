# -*- coding: utf-8 -*-
"""Estudo de cota das redes pressurizadas, ANTES do clash de soluções (parâmetros do dono do projeto, 19/10/2026).
Em vez de mergulhos pontuais (rede que desce só no cruzamento e volta), cada rede pressurizada ganha UMA cota de
implantação escolhida para dar o menor número de colisões:
  - água fria e hidrantes ('por_rede'): um recobrimento só para a rede inteira (campo 'rede' do elemento);
  - elétrica, SDAI, CFTV ('por_trecho'): um recobrimento por trecho entre caixas (a troca de cota acontece dentro da caixa);
  - o perfil segue o terreno com o recobrimento escolhido (leitura.perfil_por_recobrimento), topo no máximo a 'prof_max';
  - a elétrica fica sempre ACIMA da água onde se cruzam ('acima': pares (de cima, de baixo)): ficar por baixo conta como colisão;
  - custo = 10 por colisão + 1 por folga curta (< REGRAS['folga']) com o que já está fixo (gravidade, estrutura, caixas,
    redes já estudadas); empate: a mais rasa. Redes que ainda vão ser estudadas não entram no custo de quem vem antes.
Ordem: primeiro a água (AF, HID), depois a elétrica (ELE, SDAI, CFTV); dentro de cada uma, os grupos maiores primeiro.
REGRAS['estudo'] = {'por_rede': [...], 'por_trecho': [...], 'cob_min': {disc: m}, 'prof_max': 1.5, 'passo': 0.05, 'acima': [(cima, baixo), ...]}
O elemento estudado guarda 'pts_projeto' (cota antes do estudo) e 'estudo' = {'cob', 'grupo', 'custo', 'colisoes'}; 'pts' passa a ser a cota estudada.
Ajustes da escola A (19/10/2026, noite), que valem para todas:
  - 'desvio_perfil' 0,05 m (Douglas-Peucker do perfil): com 0,20 a rede afundava até 20 cm no meio do vão e encostava na outra;
  - 'preencher_rebaixo' (m, desligado por padrão; escola A usa 5): o perfil usa o terreno com os rebaixos estreitos preenchidos
    (fechamento de ~2r+1 m), para um rebaixo de piso (0,6 m abaixo do entorno) não puxar a rede inteira para baixo; a profundidade
    máxima continua medida no terreno real. Na escola H piorou (104 -> 110 -> 119 críticos), por isso fica por escola;
  - 'caixa_acompanha': o fundo da caixa de passagem/registro desce até 10 cm abaixo do tubo mais fundo que chega nela, e o custo da
    elétrica conta o que essa caixa mais funda passa a pegar (equipamento e reservatório não mudam)."""
import collections
import numpy as np
from . import clash as cl
from .leitura import perfil_por_recobrimento

PADRAO = {'por_rede': ['AF', 'HID'], 'por_trecho': ['ELE', 'SDAI', 'CFTV'],
          'cob_min': {'AF': 0.30, 'HID': 0.60, 'ELE': 0.60, 'SDAI': 0.60, 'CFTV': 0.60},
          'prof_max': 2.00, 'passo': 0.05,          # prof_max: parâmetro do projeto por escola (parametros.py: EXE 1,5; demais 2,0)
          'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID'), ('CFTV', 'AF'), ('CFTV', 'HID')],
          'desvio_perfil': 0.05, 'preencher_rebaixo': 0, 'caixa_acompanha': True,
          # tubulação de casa de bombas/abrigo não é rede enterrada: perto de bomba/tanque fica na cota do modelo (escola A R03:
          # o barrilete das bombas de incêndio foi levado a 1,10 m de recobrimento, 2 m abaixo das bombas, e saiu picotado)
          'fixar_perto_de': ['IfcPump', 'IfcTank'], 'raio_fixo': 3.0,
          # eixo do grupo pelo maior diâmetro (redução sem degrau); False repete o critério antigo (eixo por diâmetro do trecho)
          'eixo_maior_diametro': True,
          # cotas congeladas de uma entrega anterior: {id do elemento: recobrimento} (cobs_de_ifc); o grupo só testa esse valor
          'cob_fixo': None}
TOL_NO = 0.02     # pontas a menos disso (planta) são o mesmo nó


def _no(p):
    return (round(float(p[0]) / TOL_NO), round(float(p[1]) / TOL_NO))


def _na_caixa(p, caixas, disc):
    for c in caixas:
        if c['disc'] != disc: continue
        if abs(p[0] - c['E']) > c['meia'] + 0.05 or abs(p[1] - c['N']) > c['meia'] + 0.05: continue
        if cl._sd_planta(np.array([p[:2]]), c)[0] < 0.05: return True
    return False


def fixos_internos(E, caixas, cfg):
    """ids das pressurizadas que ficam na cota do modelo: info['estudo'] = False no adaptador, ou o trecho inteiro a menos de
    'raio_fixo' m de equipamento das classes 'fixar_perto_de' (bomba, tanque: barrilete de casa de bombas, reservatório)."""
    eq = [c for c in caixas if c['info'].get('classe_ifc') in cfg.get('fixar_perto_de', ())]
    out = set()
    for e in E:
        if e['tipo'] != 'pressao': continue
        if e['info'].get('estudo') is False: out.add(e['id']); continue
        if not eq: continue
        P = e['pts'][:, :2]
        if all(min(np.hypot(*(q - np.array([c['E'], c['N']]))) for c in eq) < cfg.get('raio_fixo', 3.0) for q in P): out.add(e['id'])
    return out


def grupos(E, caixas, cfg):
    """grupos de elementos que recebem o mesmo recobrimento."""
    fix = fixos_internos(E, caixas, cfg)
    E = [e for e in E if e['id'] not in fix]
    out = []
    por_rede = collections.defaultdict(list)
    for e in E:
        if e['tipo'] == 'pressao' and e['disc'] in cfg['por_rede']: por_rede[(e['disc'], e['rede'])].append(e)
    for (d, r), es in por_rede.items(): out.append({'disc': d, 'nome': f'{d} rede {r}', 'els': es})
    # por trecho entre caixas: componentes ligados por nós que NÃO estão dentro de caixa da disciplina
    for d in cfg['por_trecho']:
        es = [e for e in E if e['tipo'] == 'pressao' and e['disc'] == d]
        if not es: continue
        pai = list(range(len(es)))
        def raiz(i):
            while pai[i] != i: pai[i] = pai[pai[i]]; i = pai[i]
            return i
        nos = collections.defaultdict(list)
        for i, e in enumerate(es):
            for p in (e['pts'][0], e['pts'][-1]): nos[(e['rede'], _no(p))].append((i, p))
        for (rede, _), lst in nos.items():
            if len(lst) < 2 or _na_caixa(lst[0][1], caixas, d): continue
            for (i, _), (j, _) in zip(lst[:-1], lst[1:]): pai[raiz(i)] = raiz(j)
        comp = collections.defaultdict(list)
        for i, e in enumerate(es): comp[raiz(i)].append(e)
        for k, g in comp.items():
            out.append({'disc': d, 'nome': f"{d} trecho {g[0]['trecho']}" + (f' (+{len(g) - 1})' if len(g) > 1 else ''), 'els': g})
    agua = set(cfg['por_rede'])
    out.sort(key=lambda g: (g['disc'] not in agua, -sum(len(e['pts']) for e in g['els'])))
    return out


def _segs(els, campo):
    A, B, R, D = [], [], [], []
    for e in els:
        P = e[campo]
        for a, b in zip(P[:-1], P[1:]):
            if np.linalg.norm(b - a) < 1e-6: continue
            A.append(a); B.append(b); R.append(e['de'] / 2); D.append(e['disc'])
    return np.array(A).reshape(-1, 3), np.array(B).reshape(-1, 3), np.array(R), np.array(D)


def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
    """cand: lista de (elemento, pts). outros: (A, B, R, D) dos elementos fixos. futuros: (A, B, R, D) das redes que ainda vão ser
    estudadas e têm de passar POR CIMA desta (a água tem de deixar lugar para a elétrica no recobrimento mínimo dela).
    Devolve (custo, colisões, curtas)."""
    folga = regras['folga']
    A = np.array([a for _, P in cand for a in P[:-1]]); B = np.array([b for _, P in cand for b in P[1:]])
    R = np.array([e['de'] / 2 for e, P in cand for _ in P[:-1]])
    ok = np.linalg.norm(B - A, axis=1) > 1e-6; A, B, R = A[ok], B[ok], R[ok]
    oA, oB, oR, oD = outros
    crit = curt = 0
    abaixo = {b for c, b in cfg['acima'] if c == disc}; acima_de = {c for c, b in cfg['acima'] if b == disc}
    if len(oA) and len(A):
        lo = np.minimum(A, B) - R[:, None] - folga; hi = np.maximum(A, B) + R[:, None] + folga
        olo = np.minimum(oA, oB) - oR[:, None]; ohi = np.maximum(oA, oB) + oR[:, None]
        for i in range(len(A)):
            j = np.nonzero(np.all((olo <= hi[i]) & (ohi >= lo[i]), axis=1))[0]
            if not len(j): continue
            d, C1, C2 = cl.dist_seg_seg(np.repeat(A[i:i + 1], len(j), 0), np.repeat(B[i:i + 1], len(j), 0), oA[j], oB[j])
            g = d - R[i] - oR[j]
            crit += int(np.sum(g < cl.TOL)); curt += int(np.sum((g >= cl.TOL) & (g < folga)))
            # regra de posição: elétrica por cima da água onde se cruzam em planta
            dp = np.hypot(C1[:, 0] - C2[:, 0], C1[:, 1] - C2[:, 1])
            cruza = dp < R[i] + oR[j] + 0.05
            for k in np.nonzero(cruza & (g >= cl.TOL))[0]:
                od = oD[j[k]]
                if od in abaixo and C1[k, 2] - R[i] < C2[k, 2] + oR[j[k]] + folga - 1e-6: crit += 1
                if od in acima_de and C2[k, 2] - oR[j[k]] < C1[k, 2] + R[i] + folga - 1e-6: crit += 1
    if futuros is not None and len(futuros[0]) and len(A):
        fA, fB, fR, fD = futuros
        flo = np.minimum(fA, fB)[:, :2] - fR[:, None]; fhi = np.maximum(fA, fB)[:, :2] + fR[:, None]
        for i in range(len(A)):
            lo2 = np.minimum(A[i], B[i])[:2] - R[i]; hi2 = np.maximum(A[i], B[i])[:2] + R[i]
            j = np.nonzero(np.all((flo <= hi2) & (fhi >= lo2), axis=1))[0]
            if not len(j): continue
            a2 = np.column_stack([np.repeat(A[i:i + 1, :2], len(j), 0), np.zeros(len(j))]); b2 = np.column_stack([np.repeat(B[i:i + 1, :2], len(j), 0), np.zeros(len(j))])
            d, C1, _ = cl.dist_seg_seg(a2, b2, np.column_stack([fA[j, :2], np.zeros(len(j))]), np.column_stack([fB[j, :2], np.zeros(len(j))]))
            for k in np.nonzero(d < R[i] + fR[j] + 0.05)[0]:
                q = C1[k, :2]; zt = float(ter.z([q])[0])
                if not np.isfinite(zt): continue
                L = np.linalg.norm(B[i, :2] - A[i, :2]); s = 0.0 if L < 1e-9 else float(np.clip(np.dot(q - A[i, :2], B[i, :2] - A[i, :2]) / L ** 2, 0, 1))
                z = A[i, 2] + (B[i, 2] - A[i, 2]) * s
                if z + R[i] > zt - (cfg['cob_min'].get(fD[j[k]], 0.6) + 2 * fR[j[k]] + folga) + 1e-6: crit += 1
    for e, P in cand:
        Q = cl.amostra(P, 0.10); r = e['de'] / 2
        plo, phi = Q.min(0) - r - folga, Q.max(0) + r + folga
        for c in caixas:
            if c['rede'] == e['rede'] or c['disc'] == e['disc']: continue
            m = c['meia']
            if plo[0] > c['E'] + m or phi[0] < c['E'] - m or plo[1] > c['N'] + m or phi[1] < c['N'] - m or plo[2] > c['zt'] or phi[2] < c['zb']: continue
            sd = float(np.min(cl.sd_caixa(Q, c))) - r
            if sd < cl.TOL: crit += 1
            elif sd < folga: curt += 1
    return 10 * crit + curt, crit, curt


class TerrenoPreenchido:
    """terreno para o PERFIL das pressurizadas: rebaixos estreitos preenchidos (fechamento morfológico numa grade de 1 m, raio r).
    Degrau entre platôs não muda (o fechamento só enche vale)."""
    def __init__(self, ter, box, r=5):
        self.ter = ter; x0, y0, x1, y1 = box
        xs = np.arange(x0, x1 + 0.5, 1.0); ys = np.arange(y0, y1 + 0.5, 1.0)
        X, Y = np.meshgrid(xs, ys); Z = np.array(ter.z(np.c_[X.ravel(), Y.ravel()]), float).reshape(X.shape)
        ok = np.isfinite(Z); Zf = np.where(ok, Z, np.nanmin(Z) if ok.any() else 0.0)
        def filtro(A, f):
            P = np.pad(A, r, mode='edge'); out = A.copy()
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    out = f(out, P[r + dy:r + dy + A.shape[0], r + dx:r + dx + A.shape[1]])
            return out
        C = filtro(filtro(Zf, np.maximum), np.minimum)
        self.xs, self.ys, self.D = xs, ys, np.where(ok, np.maximum(C - Zf, 0.0), 0.0)

    def z(self, Q):
        Q = np.atleast_2d(np.asarray(Q, float)); z = np.array(self.ter.z(Q), float)
        xs, ys, D = self.xs, self.ys, self.D
        fx = np.clip(Q[:, 0] - xs[0], 0, len(xs) - 1.001); fy = np.clip(Q[:, 1] - ys[0], 0, len(ys) - 1.001)
        i, j = fx.astype(int), fy.astype(int); u, v = fx - i, fy - j
        return z + D[j, i] * (1 - u) * (1 - v) + D[j, i + 1] * u * (1 - v) + D[j + 1, i] * (1 - u) * v + D[j + 1, i + 1] * u * v

    def __getattr__(self, k):
        return getattr(self.ter, k)


DESVIO_PERFIL = 0.05


def _perfil(e, cob, ter):
    return perfil_por_recobrimento(e['pts'][:, :2], e['de'], cob, ter, desvio=DESVIO_PERFIL)


def _ligados(c, E):
    """(elemento, índice da ponta) da mesma disciplina que chegam na caixa c."""
    from .modelo import planta_local
    out = []
    for e in E:
        if e['disc'] != c['disc']: continue
        for k in (0, len(e['pts']) - 1):
            p = e['pts'][k]
            if c['forma'] == 'c': dentro = np.hypot(p[0] - c['E'], p[1] - c['N']) < c['meia'] + 0.10
            else:
                qx, qy = planta_local(c, p[0], p[1]); dentro = qx < 0.10 and qy < 0.10
            if dentro: out.append((e, k))
    return out


def _desce_caixa(c):
    return not c['info'].get('equipamento') and 'reservat' not in str(c['info'].get('tipo', '')).lower() and c['info'].get('classe_ifc') != 'IfcTank'


def custo_caixas(cand, outros, caixas, regras, disc):
    """o que as caixas das pontas (fundo descendo com o trecho) passam a pegar: (colisões, curtas) novas."""
    from .modelo import planta_local
    folga = regras['folga']; oA, oB, oR, oD = outros; novo = {}
    for e, P in cand:
        for k in (0, -1):
            for b in caixas:
                if b['disc'] != disc or not _desce_caixa(b): continue
                qx, qy = planta_local(b, P[k, 0], P[k, 1])
                if qx < 0.10 and qy < 0.10: novo[b['id']] = min(novo.get(b['id'], b['zb']), float(P[k, 2]) - e['de'] / 2 - 0.10)
    cr = ct = 0
    for b in caixas:
        if b['id'] not in novo or novo[b['id']] >= b['zb'] - 1e-6: continue
        b2 = dict(b, zb=novo[b['id']]); m = b['meia'] + folga
        if len(oA):
            sel = ((np.minimum(oA[:, 0], oB[:, 0]) - oR <= b['E'] + m) & (np.maximum(oA[:, 0], oB[:, 0]) + oR >= b['E'] - m) &
                   (np.minimum(oA[:, 1], oB[:, 1]) - oR <= b['N'] + m) & (np.maximum(oA[:, 1], oB[:, 1]) + oR >= b['N'] - m) &
                   (np.minimum(oA[:, 2], oB[:, 2]) - oR <= b['zt']) & (np.maximum(oA[:, 2], oB[:, 2]) + oR >= b2['zb'] - folga) & (oD != disc))
            for i in np.nonzero(sel)[0]:
                Q = cl.amostra(np.array([oA[i], oB[i]]), 0.05)
                s1 = float(np.min(cl.sd_caixa(Q, b2))) - oR[i]; s0 = float(np.min(cl.sd_caixa(Q, b))) - oR[i]
                if s1 < cl.TOL <= s0: cr += 1
                elif s1 < folga <= s0: ct += 1
        for o in caixas:
            if o['disc'] == disc or abs(o['E'] - b['E']) > 4 or abs(o['N'] - b['N']) > 4: continue
            f1 = cl.folga_caixas(b2, o)[0]; f0 = cl.folga_caixas(b, o)[0]
            if f1 < cl.TOL <= f0: cr += 1
            elif f1 < folga <= f0: ct += 1
    return cr, ct


def estudar(E, caixas, regras, ter, log=print):
    global DESVIO_PERFIL
    cfg = dict(PADRAO, **(regras.get('estudo') or {}))
    legado = globals().get('_jan', False)          # adaptador antigo da escola A já faz os ajustes abaixo por conta própria
    DESVIO_PERFIL = cfg['desvio_perfil']
    G = grupos(E, caixas, cfg)
    ter_real = ter
    if cfg['preencher_rebaixo'] and not legado and G:
        lo = np.min([e['pts'][:, :2].min(0) for g in G for e in g['els']], 0) - 10; hi = np.max([e['pts'][:, :2].max(0) for g in G for e in g['els']], 0) + 10
        ter = TerrenoPreenchido(ter_real, (lo[0], lo[1], hi[0], hi[1]), int(round(cfg['preencher_rebaixo'])))
    acompanha = cfg['caixa_acompanha'] and not legado
    estudar_discs = {g['disc'] for g in G}
    feitos = set()                      # ids já com a cota escolhida
    rel = []
    for gi, g in enumerate(G):
        ids = {e['id'] for e in g['els']}
        fixos = [e for e in E if e['id'] not in ids and (e['disc'] not in estudar_discs or e['id'] in feitos)]
        lo = np.min([e['pts'][:, :2].min(0) for e in g['els']], 0) - 3; hi = np.max([e['pts'][:, :2].max(0) for e in g['els']], 0) + 3
        fixos = [e for e in fixos if np.all(e['pts_sol'][:, :2].max(0) >= lo) and np.all(e['pts_sol'][:, :2].min(0) <= hi)]
        cxs = [c for c in caixas if lo[0] - 1 <= c['E'] <= hi[0] + 1 and lo[1] - 1 <= c['N'] <= hi[1] + 1]
        outros = _segs(fixos, 'pts_sol')
        sobem = {c for c, b in cfg['acima'] if b == g['disc']}
        futuros = _segs([e for e in E if e['disc'] in sobem and e['id'] not in feitos and e['tipo'] == 'pressao'
                         and np.all(e['pts'][:, :2].max(0) >= lo) and np.all(e['pts'][:, :2].min(0) <= hi)], 'pts')
        cmin = max([cfg['cob_min'].get(g['disc'], 0.30)] + [e['cob_min'] or 0 for e in g['els']])
        melhor = None
        congelado = [cfg['cob_fixo'][e['id']] for e in g['els'] if cfg.get('cob_fixo') and e['id'] in cfg['cob_fixo']]
        faixa = [max(congelado, key=congelado.count)] if congelado else np.arange(cmin, cfg['prof_max'] + 1e-6, cfg['passo'])
        de_g = max(e['de'] for e in g['els']) if (cfg['eixo_maior_diametro'] and not legado) else 0.0
        for cob in faixa:
            cand = []; fundo = 0.0
            try:
                for e in g['els']:
                    # eixo do grupo pelo maior diâmetro: trechos de diâmetros diferentes ficam no mesmo eixo (sem degrau na redução)
                    P = perfil_por_recobrimento(e['pts'][:, :2], de_g, float(cob), ter, desvio=DESVIO_PERFIL) if de_g > e['de'] + 1e-6 else _perfil(e, float(cob), ter)
                    cand.append((e, P))
                    zt = ter_real.z(cl.amostra(P, 0.5)); topo = cl.amostra(P, 0.5)[:, 2] + e['de'] / 2
                    fundo = max(fundo, float(np.nanmax(zt - topo)) if np.isfinite(zt).any() else 0.0)
            except ValueError:
                continue
            excede = fundo > cfg['prof_max'] + 0.01
            c, nc, nk = custo(cand, outros, cxs, regras, cfg, g['disc'], futuros, ter)
            if acompanha and g['disc'] in cfg['por_trecho']:
                cr, ct = custo_caixas(cand, outros, cxs, regras, g['disc']); c += 10 * cr + ct; nc += cr; nk += ct
            chave = (excede, c, cob)
            if melhor is None or chave < melhor[0]: melhor = (chave, float(cob), cand, nc, nk, fundo)
            if c == 0 and not excede: break            # o mais raso sem nenhum conflito
        if melhor is None:
            log(f"  estudo {g['nome']}: fora do terreno, fica como no projeto"); continue
        _, cob, cand, nc, nk, fundo = melhor
        for e, P in cand:
            e['pts_projeto'] = e.get('pts_projeto', e['pts'].copy())
            e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None)
            e['estudo'] = {'cob': cob, 'grupo': g['nome'], 'custo': melhor[0][1], 'colisoes': nc, 'curtas': nk}
            feitos.add(e['id'])
        rel.append({'grupo': g['nome'], 'disc': g['disc'], 'n': len(g['els']), 'cob': cob, 'colisoes': nc, 'curtas': nk, 'prof_max_topo': fundo})
        log(f"  estudo {g['nome']}: recobrimento {cob:.2f} m ({len(g['els'])} trechos) -> {nc} colisões, {nk} folgas curtas")
    # nó entre peças do mesmo grupo: o perfil de cada peça abaixa as pontas por conta própria (recobrimento mínimo no meio dela) e
    # duas peças no mesmo ponto ficavam até 24 cm desencontradas (AF-07 × AF-07.5 em escola B, 21/10): todas vão para a mais funda
    if not legado:
        pontas = [(e, k) for e in E if e.get('estudo') for k in (0, len(e['pts']) - 1)]
        nos = collections.defaultdict(list)
        for e, k in pontas: nos[(e['estudo']['grupo'], round(float(e['pts'][k, 0]) / 0.03), round(float(e['pts'][k, 1]) / 0.03))].append((e, k))
        n_ = 0
        for lst in nos.values():
            if len(lst) < 2: continue
            z = min(float(e['pts'][k, 2]) for e, k in lst)          # mesmo eixo (como no grupo de diâmetros diferentes)
            for e, k in lst:
                if abs(e['pts'][k, 2] - z) > 0.005: e['pts'][k, 2] = z; e['pts_sol'] = e['pts'].copy(); e.pop('S', None); n_ += 1
        if n_: log(f'  estudo: {n_} pontas levadas à cota da peça mais funda do mesmo nó')
    # trecho que ficou na cota do modelo (casa de bombas, reservatório) e encosta num trecho estudado: subida/descida vertical na
    # ponta dele até a cota do estudado (senão a rede fica com um degrau sem peça — escola A R03, 20/10/2026)
    fix = fixos_internos(E, caixas, cfg) if not legado else set(); est_ = [e for e in E if e.get('estudo')]   # adaptador antigo da escola A liga por conta própria
    for e in E:
        if e['id'] not in fix: continue
        for k in (0, -1):
            p = e['pts'][k]
            # ponta que já encosta (3D) em outro trecho da rede (ex.: descida do barrilete em vários pedaços) não ganha subida
            if any(np.linalg.norm(o['pts'][j] - p) < 0.30 for o in E if o is not e and o['rede'] == e['rede'] and o['id'] in fix for j in (0, -1)): continue
            alvo = [(np.hypot(*(o['pts'][j][:2] - p[:2])), o['pts'][j]) for o in est_ if o['rede'] == e['rede'] for j in (0, -1)]
            alvo = [a_ for a_ in alvo if a_[0] < 0.10 and abs(a_[1][2] - p[2]) > 0.02]
            if not alvo: continue
            q_ = min(alvo, key=lambda a_: a_[0] + abs(a_[1][2] - p[2]))[1]     # a ponta estudada mais próxima em planta e em nível
            novo = np.array([q_[0], q_[1], q_[2]])
            e['pts_projeto'] = e.get('pts_projeto', e['pts'].copy())
            e['pts'] = np.vstack([novo, [p[0], p[1], q_[2]], e['pts']]) if k == 0 else np.vstack([e['pts'], [p[0], p[1], q_[2]], novo])
            e['pts_sol'] = e['pts'].copy(); e.pop('S', None); e['info']['subida_estudo'] = 'sim'
            log(f"  {e['trecho']}: fica na cota do modelo; subida/descida de {abs(q_[2] - p[2]):.2f} m até o trecho estudado")
    if acompanha:                     # fundo da caixa de passagem/registro até 10 cm abaixo do tubo mais fundo que chega nela
        discs = set(cfg['por_rede']) | set(cfg['por_trecho'])
        estud = [e for e in E if e.get('estudo')]
        for c in caixas:
            if c['disc'] not in discs or not _desce_caixa(c): continue
            L = _ligados(c, estud)
            if L:
                zb = min(float(e['pts'][k, 2]) - e['de'] / 2 for e, k in L) - 0.10
                if zb < c['zb']: c['zb_projeto'] = c.get('zb_projeto', c['zb']); c['zb'] = zb
    return rel


def cobs_de_ifc(arquivos):
    """{id do elemento: recobrimento do estudo} lidos do Pset PRECLASH de IFC já entregues (Name ou Description = id),
    para REGRAS['estudo']['cob_fixo']: refazer o IFC (classes, conexões) sem mover nenhuma rede enterrada."""
    import ifcopenshell, ifcopenshell.util.element as ue
    if isinstance(arquivos, str): arquivos = [arquivos]
    out = {}
    for fn in arquivos:
        f = ifcopenshell.open(fn)
        for p in f.by_type('IfcProduct'):
            pp = ue.get_psets(p); ps = pp.get('PRECLASH') or pp.get('Dados_ETIB') or {}
            cob = ps.get('recobrimento_estudo', ps.get('recobrimento_m'))
            if cob is None: continue
            for k in (p.Name, p.Description):
                if k and ':' in str(k): out[str(k)] = float(cob)
    return out
