# -*- coding: utf-8 -*-
"""Alagoinhas (implantação) no padrão novo (21/10/2026): o modelo para o preclash montado dos RVT da escola, sem abrir o Revit.
Fonte: a geometria extraída dos RVT (RELATORIOS/compat_R02/geo/*_segs.tsv e *_mesh.tsv, export_geo.cs de 16/10, posterior ao
último salvamento das redes): HS (AF + ESG), DRN, ELE, INC (hidrantes + SDAI) e EST (fundações, pilares e vigas as built de todos
os blocos, com a malha real). Coordenadas internas = UTM − (561500; 8658000), cota absoluta.
- Terreno: amostras do IMP as built (compat_geral/terreno.py) levadas às CT das caixas de ESG e DRN do modelo (= das pranchas)
  pela correção local da ferramenta (terreno.ajustar): quando o IMP e a base divergem, vale a base.
- Gravidade (ESG, DRE): eixo 3D do modelo (cotas das pranchas, já conferidas na auditoria de 14/10 e na drenagem validada),
  com as verticais (pé de prumada, entradas, quedas). Caixas e PV pela malha (retângulo mínimo ou círculo).
- Pressurizadas (AF, HID, SDAI, ELE): só a planta do modelo; a cota sai do estudo (uma por rede na água; uma por trecho entre caixas
  na elétrica, sempre acima da água). Barrilete das bombas e ligações do reservatório: na cota do modelo, fora do estudo.
- Material pela legenda das pranchas e pelo memorial (não pelo tipo do Revit): AF PVC soldável marrom; ESG PVC Série Normal
  (Vinilfort a partir de 200 mm); DRE PVC Série Reforçada até 150 mm, Série Normal em 200 mm e Vinilfort a partir de 250 mm;
  ELE eletroduto PVC corrugado flexível; SDAI eletroduto PEAD; hidrantes PEAD SDR 11.
- Reservatório existente (contorno da SIT R04) como IfcTank. CFTV/dados e contenção ficam fora (escopo)."""
import os, re, sys, math, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
from preclash import modelo as md, terreno as tr
from preclash.leitura_ifc import retangulo_minimo

BASE = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS'
G = os.path.join(BASE, r'RELATORIOS\compat_R02\geo')
O = np.array([561500.0, 8658000.0, 0.0])
DADOS = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados'
TER_IMP = os.path.join(DADOS, 'alagoinhas_terreno_imp.npz')
TER = os.path.join(DADOS, 'alagoinhas_terreno.npz')
COB0 = {'AF': 0.30, 'HID': 0.60, 'SDAI': 0.60, 'ELE': 0.70}
# reservatório existente: círculo r = 2,70 m da SIT R04 (layer "01 - LINHAS EDIFICAÇÕES", junto ao texto RES)
RES_C, RES_R = (561596.72, 8658001.02), 2.70
MAT = {'AF': 'Tubo PVC soldável marrom', 'HID': 'Tubo PEAD SDR 11', 'SDAI': 'Eletroduto PEAD flexível', 'ELE': 'Eletroduto PVC corrugado flexível'}


def utm(P):
    P = np.atleast_2d(np.asarray(P, float))
    return P + O


# ------------------------------------------------------------------ leitura
def ler_segs(f):
    out = []
    for l in open(os.path.join(G, f + '_segs.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 13: continue
        a = np.array([float(r[7]), float(r[8]), float(r[9])]); b = np.array([float(r[10]), float(r[11]), float(r[12])])
        if np.linalg.norm(b - a) < 1e-4: continue
        out.append({'src': f, 'id': r[1], 'cat': r[2], 'tipo': r[3], 'sis': r[4], 'trecho': r[5] or r[4], 'de': float(r[6] or 0) or 0.05,
                    'a': a, 'b': b, 'desc': r[13] if len(r) > 13 else ''})
    return out


def ler_mesh(f):
    out = []
    for l in open(os.path.join(G, f + '_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t', 7)
        if len(r) < 8 or not r[7]: continue
        V = np.array(r[7].split(','), dtype=float)
        if len(V) % 9: continue
        V = V.reshape(-1, 3)
        out.append({'src': f, 'id': r[1], 'cat': r[2], 'nome': r[3], 'trecho': r[4], 'desc': r[5], 'V': V, 'lo': V.min(0), 'hi': V.max(0)})
    return out


# ------------------------------------------------------------------ terreno
def terreno(log=print):
    """IMP as built (amostras do Revit) -> npz; depois a correção local às CT das caixas de ESG/DRE (base)."""
    import terreno as TIMP
    P = utm(TIMP.P)
    _, k = np.unique(np.round(P[:, :2], 2), axis=0, return_index=True); P = P[np.sort(k)]
    # redes na borda do levantamento (T05 junto ao reservatório, ponta norte da EL2-029): o ponto da rede fora do casco das
    # amostras recebe a cota da amostra mais próxima (terreno estendido na horizontal, até 60 m)
    import matplotlib.tri as mtri
    Tr = mtri.Triangulation(P[:, 0], P[:, 1]); acha = Tr.get_trifinder()
    Q = np.array([s['a'][:2] + (s['b'][:2] - s['a'][:2]) * t for f in ('HS', 'DRN', 'ELE', 'INC') for s in ler_segs(f)
                  for t in np.linspace(0, 1, max(2, int(np.hypot(*(s['b'][:2] - s['a'][:2])) / 2.0) + 1))]) + O[:2]
    fora = Q[acha(Q[:, 0], Q[:, 1]) < 0]
    if len(fora):
        ext = []
        for q in np.unique(np.round(fora, 1), axis=0):
            d = np.hypot(P[:, 0] - q[0], P[:, 1] - q[1]); i = int(np.argmin(d))
            if d[i] < 60: ext.append((q[0], q[1], P[i, 2]))
        if ext: P = np.vstack([P, np.array(ext)]); log(f'  terreno: {len(ext)} pontos de rede fora do levantamento com a cota da amostra mais próxima')
    os.makedirs(DADOS, exist_ok=True)
    np.savez_compressed(TER_IMP, pts=P, fonte='IMP as built (amostras lidas do Revit)')
    base = []
    for m in ler_mesh('HS') + ler_mesh('DRN'):
        if _tipo_grav(m):
            lo, hi = m['lo'], m['hi']
            for x, y in (((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2), (lo[0], lo[1]), (lo[0], hi[1]), (hi[0], lo[1]), (hi[0], hi[1])):
                c = utm([[x, y, 0]])[0]; base.append((c[0], c[1], hi[2]))
    rel = tr.ajustar(TER_IMP, base, TER, modo='local', raio=6.0, fonte='CT das caixas de esgoto e drenagem das pranchas')
    log(f"  terreno: {len(P)} amostras do IMP; caixas ESG/DRE: resíduo mediano {rel['antes_mediana']:+.2f} m (p95 {rel['antes_p95_abs']:.2f}) -> "
        f"{rel['depois_mediana']:+.3f} (p95 {rel['depois_p95_abs']:.3f})")
    return rel


# ------------------------------------------------------------------ gravidade
def _tipo_grav(m):
    n = m['nome']; t = m['trecho'] or ''
    if m['src'] == 'HS':
        if 'Poço de visita' in n: return 'poço de visita'
        if 'Gordura' in n: return 'caixa retentora (CG)'
        if 'Caixa de Inspeção' in n: return 'caixa sifonada' if t.startswith('CES') else 'caixa de inspeção'
    if m['src'] == 'DRN':
        if 'Poço de visita' in n: return 'poço de visita'
        if 'Caixa de areia' in n: return 'caixa de areia'
    return None


def _cadeias3d(ss, tol=0.03):
    """segmentos -> polilinhas 3D (pontas encostadas em 3D), na ordem."""
    livres = list(ss); out = []
    while livres:
        s = livres.pop(0); P = [s['a'].copy(), s['b'].copy()]
        mudou = True
        while mudou:
            mudou = False
            for x in list(livres):
                for a, b in ((x['a'], x['b']), (x['b'], x['a'])):
                    if np.linalg.norm(a - P[-1]) < tol: P.append(b.copy()); livres.remove(x); mudou = True; break
                    if np.linalg.norm(b - P[0]) < tol: P.insert(0, a.copy()); livres.remove(x); mudou = True; break
                if mudou: break
        out.append(np.array(P))
    return out


def _dn(s):
    m = re.search(r'DN\s*(\d+)', s['desc'])
    return int(m.group(1)) if m else int(round(s['de'] * 1000))


def mat_dre(dn, tipo):
    if dn < 40 or (dn <= 40 and 'Sold' in tipo): return 'Tubo PVC soldável'
    if dn <= 150: return 'Tubo PVC Série Reforçada'
    if dn < 250: return 'Tubo PVC Série Normal'
    return 'Tubo PVC Vinilfort'


def _na_caixa(p, C, disc, folga=0.05):
    for c in C:
        if c['disc'] != disc or abs(c['E'] - p[0]) > 3 or abs(c['N'] - p[1]) > 3: continue
        qx, qy = md.planta_local(c, p[0], p[1])
        if qx < folga and qy < folga: return True
    return False


def _levar(e, k, q, E):
    """leva a ponta k do tubo de gravidade e para q (eixo do tubo onde ele chega) sem inverter o escoamento: se a ponta do outro
    lado ficaria mais baixa e estiver solta (ralo), o tubo inteiro sobe junto, com a mesma declividade; senão não mexe."""
    P = e['pts']; j = -1 if k == 0 else 0; p0 = P[k].copy()
    L = float(np.sum(np.hypot(*np.diff(P[:, :2], axis=0).T)))
    i0 = float(P[j][2] - p0[2])                                       # >0: a ponta k é a de jusante
    nova = float(q[2] - p0[2])
    if i0 > 0 and P[j][2] - q[2] < 0.005 * L:                          # jusante subiria acima do que a declividade aceita
        livre = len(P) == 2 and not any(np.hypot(*(o['pts'][m][:2] - P[j][:2])) < 0.03 for o in E if o is not e for m in (0, -1))
        if not livre: return False
        P[j][2] += nova
    elif i0 < 0 and q[2] - P[j][2] < 0.005 * L:                        # montante desceria abaixo da jusante
        return False
    P[k] = q; e['pts_sol'] = P.copy()
    return True


def _arrumar_nos(E, C, log=print):
    """detalhes do modelo da drenagem/esgoto que a Revisão de qualidade (21/10) apontou como peças soltas ou sobrepostas:
    1) degrau de menos de 5 cm no meio do tubo (DRN-399: vertical de 2,9 cm entre dois horizontais) sai: vira declividade;
    2) duas verticais no mesmo ponto (DRN-332 e DRN-333 descendo do mesmo ralo): fica a do maior, o menor nasce nela (junção);
    3) ramal menor que corre por cima de um maior até a mesma caixa (DRN-342 sobre DRN-328 nos últimos metros, CA43): o menor
       chega ao lado do maior;
    4) no nó, a ponta do ramal menor que chega dentro do diâmetro do maior vai para o eixo dele (DRN-148 10 cm abaixo do
       eixo do DRN-146: a junção ficava sem a perna dele)."""
    n = [0, 0, 0, 0]
    for e in E:
        P = e['pts']; Q = [P[0]]
        for k in range(1, len(P)):
            a, b = Q[-1], P[k]
            if np.hypot(*(b[:2] - a[:2])) < 0.01 and abs(b[2] - a[2]) < 0.05 and 0 < k < len(P) - 1 and len(Q) > 1:
                n[0] += 1; continue                                   # o degrau some: do ponto de antes segue direto ao seguinte
            Q.append(b)
        if len(Q) != len(P): e['pts'] = np.array(Q); e['pts_sol'] = e['pts'].copy()
    for e in E:
        for o in E:
            if o is e or o['disc'] != e['disc'] or o['de'] <= e['de'] + 1e-6: continue
            P, Q = e['pts'], o['pts']
            for k, j in ((0, 1), (-1, -2)):
                if len(P) < 3 or np.hypot(*(P[j][:2] - P[k][:2])) > 0.01: continue        # vertical na ponta de e
                for kk, jj in ((0, 1), (-1, -2)):
                    if np.hypot(*(Q[jj][:2] - Q[kk][:2])) > 0.01 or np.hypot(*(Q[kk][:2] - P[k][:2])) > 0.03: continue
                    zl, zh = sorted((Q[kk][2], Q[jj][2]))
                    if zl - 0.01 <= P[j][2] <= zh + 0.01:
                        e['pts'] = np.delete(P, k, axis=0); e['pts_sol'] = e['pts'].copy(); n[1] += 1; break
                P = e['pts']
    def _proj(Q, p):
        best = None
        for a, b in zip(Q[:-1], Q[1:]):
            ab = b[:2] - a[:2]; L2 = float(ab @ ab)
            if L2 < 1e-8: continue
            t = float(np.clip((p[:2] - a[:2]) @ ab / L2, 0, 1)); q = a + (b - a) * t
            d = float(np.hypot(*(q[:2] - p[:2])))
            if best is None or d < best[0]: best = (d, q, ab / np.sqrt(L2))
        return best
    for e in E:
        for o in E:
            if o is e or o['disc'] != e['disc'] or o['de'] <= e['de'] + 1e-6: continue
            P = e['pts']
            if len(P) != 2: continue
            for k in (0, -1):
                if np.hypot(*(o['pts'][0][:2] - P[k][:2])) > 0.03 and np.hypot(*(o['pts'][-1][:2] - P[k][:2])) > 0.03: continue
                u = P[k][:2] - P[1 + k if k == 0 else -2][:2]; L = float(np.hypot(*u))
                if L < 2.0: continue
                lim = (o['de'] + e['de']) / 2 + 0.02; s0 = None
                for t in np.linspace(0, 1, int(L / 0.10) + 1):
                    p = P[k] - np.r_[u * t, 0]
                    b = _proj(o['pts'], p)
                    if b is None or b[0] > lim: break
                    s0 = (t, b)
                if s0 is None or s0[0] * L < 0.5: continue
                b = s0[1]
                ang = np.degrees(np.arccos(min(1.0, abs(float(b[2] @ (u / L))))))
                if ang > 10 or not _na_caixa(P[k], C, e['disc']): continue
                # os dois chegam na mesma caixa (CA43): o menor chega ao lado do maior, afastado eixo a eixo (de1 + de2)/2 + 5 cm
                nrm = np.array([-b[2][1], b[2][0]]); lado = 1.0 if float((P[1 + k if k == 0 else -2][:2] - b[1][:2]) @ nrm) >= 0 else -1.0
                P[k][:2] = P[k][:2] + nrm * lado * ((o['de'] + e['de']) / 2 + 0.05); e['pts_sol'] = P.copy(); n[2] += 1
    nos = collections.defaultdict(list)
    for e in E:
        for k in (0, -1): nos[(e['disc'], round(float(e['pts'][k][0]) / 0.03), round(float(e['pts'][k][1]) / 0.03))].append((e, k))
    for lst in nos.values():
        if len(lst) < 2: continue
        m, km = max(lst, key=lambda x: x[0]['de']); zc = m['pts'][km][2]
        if _na_caixa(m['pts'][km], C, m['disc']): continue           # dentro da caixa cada tubo chega na sua cota (pranchas)
        for e, k in lst:
            if e is m: continue
            dz = e['pts'][k][2] - zc
            if 0.005 < abs(dz) <= m['de'] / 2 + 0.02 and e['de'] < m['de'] and _levar(e, k, m['pts'][km].copy(), E): n[3] += 1
    log(f'  gravidade: {n[0]} degraus < 5 cm tirados, {n[1]} verticais repetidas, {n[2]} ramais sobrepostos afastados na chegada da caixa, '
        f'{n[3]} pontas de ramal levadas ao eixo do tubo maior no nó')


def gravidade(log=print):
    E, C = [], []
    S = [s for s in ler_segs('HS') if s['sis'].startswith('Esgoto')] + ler_segs('DRN')
    por = collections.defaultdict(list)
    for s in S:
        disc = 'ESG' if s['src'] == 'HS' else 'DRE'
        raiz = re.sub(r'-(VP|VM|E)$', '', s['trecho'])
        por[(disc, raiz)].append(s)
    for (disc, raiz), ss in por.items():
        for nc, P in enumerate(_cadeias3d(ss)):
            # escoamento do mais alto para o mais baixo
            if P[0, 2] < P[-1, 2]: P = P[::-1]
            s0 = ss[0]; dn = _dn(s0) if disc == 'DRE' else int(round(s0['de'] * 1000))
            de = md.de_gravidade(dn) if dn >= 75 else dn / 1000.0
            mat = ('Tubo PVC Vinilfort' if dn >= 200 else 'Tubo PVC Série Normal') if disc == 'ESG' else mat_dre(dn, s0['tipo'])
            info = dict(DN_mm=dn, material=mat, cota='cotas das pranchas (modelo)', de_ate=s0['desc'][:80] if disc == 'ESG' else '',
                        GI_mont=round(float(P[0, 2] - de / 2), 3), GI_jus=round(float(P[-1, 2] - de / 2), 3))
            E.append(md.elemento(f'{disc}:{raiz}' + (f'#{nc + 1}' if nc else ''), disc, disc, raiz, 'gravidade', de, utm(P), movel=False, **info))
    # queda sem a peça vertical no modelo (ramais internos DN32/40 da drenagem, DRN-009 -> DRN-008 a 1,5 m): a ponta de cima
    # ganha o tubo de queda até a cota da ponta de baixo (mesmo ponto em planta)
    # ramal desenhado duas vezes no modelo (DRN-012 DN40 e DRN-013 DN32 no mesmo caminho): fica o de maior diâmetro
    def _dist(Q, P):
        d = np.full(len(Q), 1e9)
        for a, b in zip(P[:-1], P[1:]):
            ab = b - a; L2 = float(ab @ ab)
            t = np.clip(((Q - a) @ ab) / L2, 0, 1) if L2 > 1e-12 else np.zeros(len(Q))
            d = np.minimum(d, np.hypot(*(a + t[:, None] * ab - Q).T))
        return d

    def _amostra2(P, passo=0.25):
        out = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            n = max(1, int(np.hypot(*(b - a)) / passo)); out += [a + (b - a) * k / n for k in range(1, n + 1)]
        return np.array(out)
    dup = set()
    for i, e in enumerate(E):
        for o in E[i + 1:]:
            if o['disc'] != e['disc'] or id(o) in dup or id(e) in dup: continue
            A_, B_ = (e, o) if np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)) <= np.sum(np.hypot(*np.diff(o['pts'][:, :2], axis=0).T)) else (o, e)
            Q = _amostra2(A_['pts'][:, :2])
            if len(Q) >= 2 and np.mean(_dist(Q, B_['pts'][:, :2]) < 0.10) > 0.85:
                dup.add(id(o) if o['de'] <= e['de'] else id(e))
    if dup: log(f"  gravidade: {len(dup)} ramais duplicados no modelo (mesmo caminho) — fica o de maior diâmetro: " + ', '.join(x['trecho'] for x in E if id(x) in dup))
    E[:] = [x for x in E if id(x) not in dup]
    for m in ler_mesh('HS') + ler_mesh('DRN'):
        t = _tipo_grav(m)
        if not t: continue
        disc = 'ESG' if m['src'] == 'HS' else 'DRE'
        c = utm([(m['lo'] + m['hi']) / 2])[0]; lo, hi = m['lo'], m['hi']
        nome = m['trecho'] or m['id']
        info = dict(nome=nome, tipo=t, CT=round(float(hi[2]), 2), fundo=round(float(lo[2]), 2), cota='CT/CF das pranchas (modelo)')
        if t == 'poço de visita':
            info['material'] = 'Concreto armado; tampão de ferro fundido'
            C.append(md.caixa(f'{disc}:{nome}', disc, disc, 'c', c[0], c[1], max(hi[0] - lo[0], hi[1] - lo[1]) / 2, lo[2], hi[2], **info))
        else:
            cx, cy, lx, ly, rot, _ = retangulo_minimo(m['V'][:, :2])
            info['material'] = 'Concreto armado; grelha de ferro fundido' if t == 'caixa de areia' else 'Alvenaria de blocos; tampa de concreto pré-moldado'
            u = utm([[cx, cy, 0]])[0]
            C.append(md.caixa_retangular(f'{disc}:{nome}', disc, disc, u[0], u[1], lx, ly, rot, lo[2], hi[2], **info))
    ns = 0
    for e in E:
        for k in (0, -1):
            p = e['pts'][k]
            if any(np.linalg.norm(o['pts'][j] - p) < 0.03 for o in E if o is not e and o['disc'] == e['disc'] for j in (0, -1)): continue
            for o in E:
                if o is e or o['disc'] != e['disc']: continue
                P = o['pts']; feito = False
                for a, b in zip(P[:-1], P[1:]):
                    ab = b - a; L2 = float(ab @ ab)
                    if L2 < 1e-6: continue
                    t = float(np.clip((p - a) @ ab / L2, 0, 1)); q = a + ab * t
                    # também na ponta do tubo maior (DRN-190 chegando 12 cm antes do início do DRN-187), fora de caixa
                    meio = 0.02 < t < 0.98 or (o['de'] > e['de'] + 1e-6 and not _na_caixa(p, C, e['disc']))
                    if meio and 0.005 < np.linalg.norm(q - p) < 0.10 + (o['de'] + e['de']) / 2 and _levar(e, k, q, E):
                        ns += 1; feito = True; break
                if feito: break
    if ns: log(f'  gravidade: {ns} pontas de ramal levadas para cima do tubo onde chegam (vão de modelo até 10 cm)')
    nq = 0; feitas = []
    for e in E:
        if e['de'] > 0.051: continue                         # só os ramais internos DN32/40 (os outros têm a vertical no modelo)
        for k in (0, -1):
            p = e['pts'][k]; viz = e['pts'][1 if k == 0 else -2]
            if np.hypot(*(viz[:2] - p[:2])) < 0.01: continue    # a ponta já é de uma vertical
            for o in E:
                if o is e or o['disc'] != e['disc'] or o['de'] > 0.051: continue
                for j in (0, -1):
                    q = o['pts'][j]
                    if np.hypot(*(q[:2] - p[:2])) < 0.03 and p[2] - q[2] > 0.02 and not any(np.hypot(*(f - p[:2])) < 0.03 for f in feitas):
                        feitas.append(p[:2].copy())
                        # a vertical vai no tubo de BAIXO (sobe até a ponta de cima): no nó de cima todas as pontas ficam na mesma cota
                        # (a ferramenta agrupa os nós só em planta; com a vertical no de cima, o nó misturava as duas cotas)
                        P = o['pts']; v = np.array([[p[0], p[1], p[2]]])
                        o['pts'] = np.vstack([v, P]) if j == 0 else np.vstack([P, v]); o['pts_sol'] = o['pts'].copy(); nq += 1
                        break
                else: continue
                break
    if nq: log(f'  gravidade: {nq} tubos de queda que faltavam no modelo (ramais internos)')
    _arrumar_nos(E, C, log)
    log(f"  gravidade: {collections.Counter(e['disc'] for e in E)} trechos, {collections.Counter(c['disc'] for c in C)} caixas")
    return E, C


# ------------------------------------------------------------------ pressurizadas
def _cadeias(ss, tol=0.03):
    livres = list(ss); out = []
    while livres:
        s = livres.pop(0); P = [s['a'].copy(), s['b'].copy()]
        mudou = True
        while mudou:
            mudou = False
            for x in list(livres):
                for a, b in ((x['a'], x['b']), (x['b'], x['a'])):
                    if np.hypot(*(a[:2] - P[-1][:2])) < tol: P.append(b.copy()); livres.remove(x); mudou = True; break
                    if np.hypot(*(b[:2] - P[0][:2])) < tol: P.insert(0, a.copy()); livres.remove(x); mudou = True; break
                if mudou: break
        Q = [P[0]]
        for k in range(1, len(P) - 1):
            u = P[k][:2] - Q[-1][:2]; v = P[k + 1][:2] - P[k][:2]
            if np.hypot(*u) < 1e-6: continue
            if abs(np.cross(u, v)) / (np.hypot(*u) * max(np.hypot(*v), 1e-9)) > 0.02: Q.append(P[k])
        Q.append(P[-1]); out.append(np.array(Q))
    return out


def _disc_press(s):
    if s['src'] == 'HS': return 'AF'
    if s['src'] == 'INC': return 'SDAI' if s['cat'] == 'Conduites' else 'HID'
    if s['src'] == 'ELE': return None if s['tipo'].startswith('TEL') else 'ELE'
    return None


def _fixo(s, disc):
    """barrilete das bombas e ligações junto aos reservatórios: tubulação de casa de bombas, na cota do modelo."""
    d = s['desc']
    if disc == 'AF': return d.startswith(('Barrilete: sucção', 'Ligação bomba'))
    # hidrantes: a alimentação reservatório -> bombas (T05) é rede enterrada e entra no estudo; perto das bombas/tanque a
    # ferramenta fixa sozinha (fixar_perto_de); só a subida do hidrante de recalque fica na cota do modelo
    if disc == 'HID': return False
    return False


def _dn_pol(desc):
    m = re.search(r'Ø\s*([\d/ ]+)"', desc)
    if not m: return None
    t = m.group(1).strip(); tot = 0.0
    for x in t.split():
        if '/' in x: a, b = x.split('/'); tot += float(a) / float(b)
        else: tot += float(x)
    return round(tot * 25.4, 1)


def pressurizadas(T, log=print):
    E = []
    segs = [(s, _disc_press(s)) for s in ler_segs('HS') + ler_segs('INC') + ler_segs('ELE')]
    segs = [(s, d) for s, d in segs if d and not (s['src'] == 'HS' and s['sis'].startswith('Esgoto'))]
    # barrilete: um elemento por tubo, 3D do modelo
    nfix = 0
    for s, d in segs:
        if not _fixo(s, d): continue
        P = utm([s['a'], s['b']])
        rede = 'AL' if (d == 'AF' and s['sis'].startswith('Água fria - Abast')) else d
        E.append(md.elemento(f'{d}:{s["trecho"]}:{s["id"]}', d, rede, s['trecho'], 'pressao', s['de'], P, cob_min=None, movel=False, estudo=False,
                             DN_mm=round(s['de'] * 1000), material=MAT[d], sistema=s['sis'] or d, descricao=s['desc'][:80],
                             cota='cota do modelo (casa de bombas / reservatório)'))
        nfix += 1
    por = collections.defaultdict(list)
    for s, d in segs:
        if _fixo(s, d): continue
        if np.hypot(*(s['b'][:2] - s['a'][:2])) < 0.03: continue        # verticais do modelo (subida do recalque etc.): a cota sai do estudo
        raiz = re.sub(r'\.\d+$', '', s['trecho'])
        por[(d, raiz, round(s['de'], 4))].append(s)
    cad = []
    for (d, raiz, de), ss in por.items():
        for nc, P in enumerate(_cadeias(ss)):
            P = np.array([p for k, p in enumerate(P) if k == 0 or np.hypot(*(p[:2] - P[k - 1][:2])) > 0.02])
            if len(P) >= 2: cad.append([d, raiz, de, ss, nc, P])
    # pontas de cadeias de água (AF/HID) a menos de 8 cm viram um ponto só: no modelo do Revit os tubos ficam até 5 cm
    # afastados e, num pé de platô, o terreno de cada ponta dava cotas 9 a 25 cm diferentes (AF-07 × AF-07.5, revisão de 21/10)
    pts = [(i, k) for i, c in enumerate(cad) for k in (0, -1)]
    for a in range(len(pts)):
        i, k = pts[a]; p = cad[i][5][k]
        if cad[i][0] not in ('AF', 'HID'): continue                 # banco de eletrodutos: pontas paralelas a 10 cm são outros dutos
        grupo = [(j, m) for j, m in pts if cad[j][0] == cad[i][0] and np.hypot(*(cad[j][5][m][:2] - p[:2])) < 0.08]
        if len(grupo) > 1:
            q = np.mean([cad[j][5][m][:2] for j, m in grupo], axis=0)
            for j, m in grupo: cad[j][5][m][:2] = q
    for d, raiz, de, ss, nc, P in cad:
        P = np.array([p for k, p in enumerate(P) if k == 0 or np.hypot(*(p[:2] - P[k - 1][:2])) > 0.02])
        if len(P) < 2: continue                                       # pedaço de poucos cm que sumiu na costura das pontas
        s = ss[0]
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            n = int(np.ceil(np.hypot(*(b[:2] - a[:2])) / 4.0))
            Q += [a + (b - a) * j / n for j in range(1, n + 1)]
        U = utm(np.array(Q)); zt = T.z(U[:, :2])
        if np.isfinite(zt).any():
            zt = np.where(np.isfinite(zt), zt, np.nanmedian(zt)); U[:, 2] = zt - COB0[d] - de / 2
        # fora das amostras do terreno (EL2-029, ponta norte): fica na cota do modelo
        info = dict(material=MAT[d], sistema=s['sis'] or s['tipo'], descricao=s['desc'][:80], cota='estudo de cota da rede')
        if d == 'ELE':
            rede = 'ELE'; info['circuito'] = 'BT (EL-001)' if 'Alimentação' in s['tipo'] else 'iluminação externa (EL-002)'
            info['DN_mm'] = _dn_pol(s['desc']) or round(de * 1000)
        elif d == 'SDAI':
            rede = 'SDAI'; info['DN_mm'] = 50.8; info['laco'] = re.sub(r'^.*Laço\s*', '', s['desc'])[:60]
        elif d == 'HID':
            # T05 (reservatório -> bombas) é a sucção das bombas, antes delas: rede própria, com a sua cota
            rede = 'HID-SUC' if s['desc'].startswith(('Alimentação reservatório/bombas', 'Saída do reservatório taça')) else 'HID'
            info['DN_mm'] = round(de * 1000)
        else:
            rede = 'AL' if s['sis'].startswith('Água fria - Abast') else 'AF'; info['DN_mm'] = round(de * 1000)
        E.append(md.elemento(f'{d}:{raiz}:{s["id"]}' + (f'#{nc + 1}' if nc else ''), d, rede, raiz, 'pressao', de, U, cob_min=COB0[d], movel=True, **info))
    log(f"  pressurizadas: {collections.Counter(e['disc'] for e in E)} ({nfix} tubos de barrilete na cota do modelo)")
    return E


def caixas_press(T, log=print):
    C = []
    for m in ler_mesh('ELE') + ler_mesh('INC') + ler_mesh('HS'):
        n, t = m['nome'], m['trecho'] or ''
        lo, hi = m['lo'], m['hi']; c3 = (lo + hi) / 2
        cx, cy, lx, ly, rot, _ = retangulo_minimo(m['V'][:, :2]); u = utm([[cx, cy, 0]])[0]
        zt = float(T.z([u[:2]])[0]); zt = zt if np.isfinite(zt) else float(hi[2])
        h = float(hi[2] - lo[2])
        if m['src'] == 'ELE' and 'ELE-CX' in n:
            if t.startswith('CF'): continue                                    # CFTV/dados: fora do escopo
            C.append(md.caixa_retangular(f'ELE:{t}', 'ELE', 'ELE', u[0], u[1], lx, ly, rot, zt - h, zt, nome=t,
                                         tipo='caixa de passagem ' + (re.search(r'(\d+x\d+)', n).group(1) if re.search(r'(\d+x\d+)', n) else ''),
                                         material='Alvenaria / concreto', cota='tampa no terreno; fundo pelo eletroduto mais fundo'))
        elif m['src'] == 'INC' and 'SDAI - Caixa de passagem' in n:
            C.append(md.caixa_retangular(f'SDAI:{t}', 'SDAI', 'SDAI', u[0], u[1], lx, ly, rot, zt - h, zt, nome=t, tipo='caixa de passagem 68x68',
                                         material='Alvenaria / concreto', cota='tampa no terreno; fundo pelo eletroduto mais fundo'))
        elif m['src'] == 'INC' and 'hidrante de recalque' in n.lower():
            C.append(md.caixa_retangular(f'HID:{t or m["id"]}', 'HID', 'HID', u[0], u[1], lx, ly, rot, zt - h, zt, nome='Caixa do hidrante de recalque',
                                         tipo='caixa de registro 40x40', material='Alvenaria / concreto', cota='tampa no terreno'))
        elif m['src'] == 'INC' and ('Bomba' in n or 'Jockey' in n):
            C.append(md.caixa_retangular(f'EQ:{m["id"]}', 'HID', 'HID', u[0], u[1], lx, ly, rot, lo[2], hi[2], nome=n.split(' : ')[0],
                                         classe_ifc='IfcPump', equipamento='sim', cota='modelo'))
        elif m['src'] == 'INC' and 'Registro de Recalque' in n:
            C.append(md.caixa_retangular(f'EQ:{m["id"]}', 'HID', 'HID', u[0], u[1], max(lx, 0.05), max(ly, 0.05), rot, lo[2], hi[2],
                                         nome='Registro de recalque com válvula de retenção', classe_ifc='IfcValve', pred='CHECK', equipamento='sim', cota='modelo'))
        elif m['src'] == 'HS' and 'Bomba pressurizadora' in n:
            C.append(md.caixa_retangular(f'EQ:{m["id"]}', 'AF', 'AF', u[0], u[1], lx, ly, rot, lo[2], hi[2], nome='Bomba pressurizadora',
                                         classe_ifc='IfcPump', equipamento='sim', cota='modelo'))
        elif m['src'] == 'HS' and 'Alçapão' in n:
            C.append(md.caixa_retangular(f'AF:{m["id"]}', 'AF', 'AF', u[0], u[1], lx, ly, rot, zt - h, zt, nome=t or 'Alçapão', tipo='caixa de registro (alçapão enterrado)',
                                         material='Alvenaria / concreto', cota='tampa no terreno'))
        elif m['src'] == 'HS' and 'Registro (volume)' in n:
            C.append(md.caixa_retangular(f'EQ:{m["id"]}', 'AF', 'AF', u[0], u[1], max(lx, 0.05), max(ly, 0.05), rot, lo[2], hi[2], nome=t or 'Registro de gaveta',
                                         classe_ifc='IfcValve', pred='ISOLATING', equipamento='sim', tipo='registro', cota='modelo'))
        elif m['src'] == 'HS' and 'hidrômetro' in n.lower():
            C.append(md.caixa_retangular(f'AF:{m["id"]}', 'AF', 'AL', u[0], u[1], lx, ly, rot, lo[2], hi[2], nome='Abrigo do hidrômetro',
                                         classe_ifc='IfcFlowMeter', pred='WATERMETER', equipamento='sim', tipo='hidrômetro', cota='modelo'))
    # reservatório existente
    zt = float(T.z([RES_C])[0])
    C.append(md.caixa('AF:RES', 'AF', 'AF', 'c', RES_C[0], RES_C[1], RES_R, zt, zt + 3.00, nome='Reservatório existente', classe_ifc='IfcTank',
                      tipo='reservatório existente', dimensoes=f'Ø{2 * RES_R:.2f} m (contorno da implantação)', cota='base no terreno'))
    log(f"  caixas e equipamentos das pressurizadas: {collections.Counter(c['disc'] for c in C)}")
    return C


# ------------------------------------------------------------------ estrutura (forma real)
CATS_EST = ('Fundações estruturais', 'Pilares estruturais', 'Quadro estrutural')


def estrutura(T, log=print):
    C = []; n = collections.Counter()
    for m in ler_mesh('EST'):
        if m['cat'] not in CATS_EST or '-IMP_' in (m['trecho'] or ''): continue
        lo, hi = m['lo'], m['hi']; c = utm([(lo + hi) / 2])[0]
        zt = float(T.z([c[:2]])[0])
        if np.isfinite(zt) and lo[2] > zt + 0.50: continue                 # só o que fica abaixo ou rente ao terreno
        cx, cy, lx, ly, rot, _ = retangulo_minimo(m['V'][:, :2]); u = utm([[cx, cy, 0]])[0]
        bloco = re.search(r'ETIB-([A-Z0-9]+)-PE', m['trecho']).group(1) if re.search(r'ETIB-([A-Z0-9]+)-PE', m['trecho']) else 'EST'
        tipo = 'pilar' if m['cat'].startswith('Pilar') else ('viga' if m['cat'].startswith('Quadro') else 'fundação')
        M = utm(m['V']).reshape(-1, 3, 3)
        C.append(md.caixa_retangular(f'EST:{bloco}:{m["id"]}', 'EST', 'EST-' + bloco, u[0], u[1], lx, ly, rot, lo[2], hi[2],
                                     nome=m['nome'].split(' : ')[-1][:60], tipo=tipo, bloco=bloco, familia=m['nome'][:80], malha=M, cota='as built'))
        n[bloco] += 1
    log(f'  estrutura as built (forma real): {sum(n.values())} peças {dict(n)}')
    return C


# ------------------------------------------------------------------ montagem
def ligados(c, E, tol=0.10):
    out = []
    for e in E:
        if e['tipo'] != 'pressao' or e['disc'] != c['disc']: continue
        for k in (0, -1):
            qx, qy = md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])
            if c['forma'] == 'c': dentro = np.hypot(e['pts'][k, 0] - c['E'], e['pts'][k, 1] - c['N']) < c['meia'] + tol
            else: dentro = qx < tol and qy < tol
            if dentro: out.append((e, k))
    return out


def redes_das_caixas(E, C):
    for c in C:
        if c['disc'] not in ('ELE', 'SDAI', 'AF', 'HID') or c['info'].get('classe_ifc') == 'IfcTank': continue
        L = ligados(c, E, 0.30 if c['info'].get('equipamento') else 0.10)
        if L: c['rede'] = collections.Counter(e['rede'] for e, _ in L).most_common(1)[0][0]


def montar(log=print):
    if not os.path.exists(TER) or os.path.getmtime(TER) < os.path.getmtime(__file__): terreno(log)
    T = tr.Terreno(TER)
    E, C = gravidade(log)
    E += pressurizadas(T, log)
    C += caixas_press(T, log)
    redes_das_caixas(E, C)
    C += estrutura(T, log)
    return E, C, T


if __name__ == '__main__':
    E, C, T = montar()
    print(len(E), 'elementos', len(C), 'caixas')
