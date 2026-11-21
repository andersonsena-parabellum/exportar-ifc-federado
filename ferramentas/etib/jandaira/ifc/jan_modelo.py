# -*- coding: utf-8 -*-
"""Jandaíra no padrão novo (19/10/2026 noite, Anderson): o modelo para o preclash, montado dos 5 JAN-*.rvt já extraídos
(compat_R01/geo = estado do Daniel; geo_exec = estado atual, com o campo 50x30), sem abrir o Revit.

- Terreno: o do IMP (Revit) levado às cotas da base. Todas as caixas de DRE e ESG das pranchas têm CT 147,50 (platô da SIT);
  o IMP está 0,43 a 0,61 m abaixo. Correção local (IDW dos resíduos nas caixas) somada ao IMP: o terreno passa a 147,50 nas
  caixas e guarda a forma do IMP entre elas. A estrutura as built, os equipamentos e as caixas das pressurizadas sobem junto.
- Gravidade (DRE, ESG): planta e ligação dos tubos do modelo do Daniel; CT/CF/CS/CE das pranchas (rotulos_grav.py).
  Drenagem do campo 50x30 (fase E) e CX-43: cotas do R01 (CX-43 CF 146,49) subidas com o terreno.
- Pressurizadas (AF, HID, SDAI, ELE): só a planta do modelo atual (desvios em planta e caixas da fase B/C, sem os mergulhos);
  a cota sai do estudo da ferramenta (uma por rede na água; uma por trecho entre caixas na elétrica).
- Reservatório inferior de reúso (não modelado no Revit): contorno da prancha AF-001 (5,0 x 2,0 m), 1,80 m de altura (premissa).
Tudo devolvido em UTM (SIRGAS 2000 / 24S) e cota absoluta."""
import os, sys, re, json, math, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import jan_dados as JD
from preclash import modelo as md

BASE = r'D:\Projeto Modelagem\ETIB-JANDAIRA'
C = os.path.join(BASE, r'RELATORIOS\compat_R01'); G0 = os.path.join(C, 'geo'); GX = os.path.join(C, 'geo_exec')
SAIDA = os.path.join(BASE, r'RELATORIOS\IFC_R02')
ROT_JSON = os.path.join(SAIDA, 'rotulos_gravidade.json')
COB0 = {'AF': 0.30, 'HID': 0.60, 'SDAI': 0.60, 'ELE': 0.60}
CX43_CF = 146.49          # R01 (drenagem do campo 50x30 chegando a oeste)
RES_CANTOS = [(37.71, 135.28), (37.90, 137.27), (42.87, 136.79), (42.68, 134.80)]   # interno, prancha AF-001 ("R")
RES_ALTURA = 1.80

_R, _o = JD.tf_compart(JD.meta('ELE', G0))


def utm(P):
    """interno (n,3) ou (3,) -> UTM E, N, cota absoluta."""
    P = np.atleast_2d(np.asarray(P, float))
    if P.shape[1] == 2: P = np.c_[P, np.zeros(len(P))]
    return (P - _o) @ _R


def ang_utm(theta_int):
    """ângulo em planta no interno -> ângulo em UTM."""
    a = utm([[0, 0, 0], [math.cos(theta_int), math.sin(theta_int), 0]])
    return math.atan2(a[1, 1] - a[0, 1], a[1, 0] - a[0, 0])


# ------------------------------------------------------------------ terreno
class Ajuste:
    """deslocamento vertical do IMP até as cotas da base: IDW (potência 2, 8 vizinhos) dos resíduos nas caixas."""
    def __init__(self, T, pontos):
        self.P = np.array([p[:2] for p in pontos]); self.d = np.array([p[2] - (147 + T.z(p[0], p[1])) for p in pontos])
        ok = np.isfinite(self.d); self.P, self.d = self.P[ok], self.d[ok]; self.med = float(np.median(self.d))

    def __call__(self, x, y):
        r = np.hypot(self.P[:, 0] - x, self.P[:, 1] - y); k = np.argsort(r)[:8]
        if r[k[0]] < 0.05: return float(self.d[k[0]])
        w = 1 / r[k] ** 2; return float((w * self.d[k]).sum() / w.sum())


def pontos_base(R=None):
    """(x, y, CT) no interno: centro das caixas de DRE e ESG com o CT da prancha."""
    R = R or json.load(open(ROT_JSON, encoding='utf-8'))
    SH, MH = JD.carregar(g=G0, est=None); JD.agrupar_caixas(SH, MH)
    out = []
    for disc in ('DRE', 'ESG'):
        for n, v in R[disc].items():
            if not v.get('CT'): continue
            Mg = [M for M in MH if M.get('grupo') == n and M['disc'] == disc]
            if Mg: c = (Mg[0]['glo'] + Mg[0]['ghi']) / 2; out.append((c[0], c[1], min(x[0] for x in v['CT'])))
    return out


def terreno(npz, passo=1.0):
    T = JD.Terreno(g=G0); pb = pontos_base(); aj = Ajuste(T, pb)
    xs = np.arange(T.lo[0], T.hi[0], passo); ys = np.arange(T.lo[1], T.hi[1], passo)
    P = []
    for x in xs:
        for y in ys:
            z = T.z(x, y)
            if np.isfinite(z): P.append((x, y, 147 + z + aj(x, y) - 147))
    P = np.array(P); U = utm(P)
    U[:, 2] = np.array([147 + p[2] for p in P])          # cota absoluta = 147 + z interno ajustado
    os.makedirs(os.path.dirname(npz), exist_ok=True)
    np.savez(npz, pts=U, fonte='IMP as built (Revit) + correção local às CT das pranchas DRE/ESG (147,50)')
    return T, aj, len(U)


# ------------------------------------------------------------------ utilidades de leitura
def _grupos(M):
    g = collections.defaultdict(list)
    for m in M: g[m.get('grupo')].append(m)
    return g


def _plano(S, disc, excluir=()):
    """segmentos de uma disciplina, sem os trechos verticais (mergulhos e subidas do modelo atual)."""
    out = []
    for s in S:
        if s['disc'] != disc or any(s['trecho'].startswith(x) for x in excluir): continue
        if np.hypot(*(s['b'][:2] - s['a'][:2])) < 0.03: continue
        out.append(s)
    return out


def _cadeias(ss, tol=0.03):
    """segmentos -> polilinhas (pontas encostadas, em planta), sem colinear repetido."""
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
        # tira vértices colineares (pedaços de mergulho na mesma reta)
        Q = [P[0]]
        for k in range(1, len(P) - 1):
            u = P[k][:2] - Q[-1][:2]; v = P[k + 1][:2] - P[k][:2]
            if np.hypot(*u) < 1e-6 or abs(np.cross(u, v)) / (np.hypot(*u) * max(np.hypot(*v), 1e-9)) > 0.02: Q.append(P[k])
        Q.append(P[-1]); out.append(np.array(Q))
    return out


# ------------------------------------------------------------------ gravidade
def _no(desc):
    m = re.search(r'\|\s*([A-Z]+[\w.-]*)\s*->\s*([A-Z]+[\w.-]*)', desc or '')
    return (m.group(1), m.group(2)) if m else (None, None)


def gravidade(S, M, disc, R, T, aj, log):
    """elementos e caixas de DRE ou ESG com as cotas das pranchas."""
    E, Cx = [], []
    G = _grupos([m for m in M if m['disc'] == disc])
    lab = R.get(disc, {})
    caixas = {}
    for n, ms in G.items():
        if not ms or n is None or str(n).startswith(('AN_', 'PLUV', 'PVC')): continue
        lo = np.min([m['lo'] for m in ms], 0); hi = np.max([m['hi'] for m in ms], 0)
        canal = 'Canaleta' in ' '.join(m['nome'] for m in ms)
        if (hi[0] - lo[0] > 6 or hi[1] - lo[1] > 6) and not canal: continue
        if str(n).startswith(disc + ' caixa') and any(str(k).startswith(('CX', 'PV', 'PI', 'CI', 'CE', 'CG')) and np.hypot(*(((lo + hi) / 2)[:2] - [((m2['glo'] + m2['ghi']) / 2)[:2] for m2 in G[k]][0])) < 0.6 for k in G if k and G[k] and G[k][0].get('glo') is not None): continue
        c = (lo + hi) / 2; v = lab.get(n, {})
        ct = min((x[0] for x in v.get('CT', [])), default=None); cf = min((x[0] for x in v.get('CF', [])), default=None)
        zt_mod = 147 + hi[2]; zb_mod = 147 + lo[2]; d = aj(c[0], c[1])
        if n == 'CX-43': cf = CX43_CF
        if n == 'PI-01': ct, cf = 147.50, 145.26        # rótulo da prancha com a chamada fora do poço do modelo (5,8 m): lido à mão
        # sem rótulo na prancha: topo no terreno (já levado às cotas da base), fundo do modelo + ajuste (CX-18 ficava 8 cm enterrada)
        caixas[n] = dict(c=c, lo=lo, hi=hi, CT=ct if ct is not None else 147 + T.z(c[0], c[1]) + d, CF=cf if cf is not None else zb_mod + d,
                         rot=(ct is not None, cf is not None), CS=v.get('CS', []), CE=v.get('CE', []))
    sem = [n for n, k in caixas.items() if not all(k['rot'])]
    if sem: log(f'  {disc}: {len(sem)} caixas sem rótulo de prancha (cota do modelo + ajuste do terreno): {", ".join(map(str, sem))}')
    def caixa_de(p):
        best = None
        for n, k in caixas.items():
            dx = max(k['lo'][0] - p[0], p[0] - k['hi'][0], 0); dy = max(k['lo'][1] - p[1], p[1] - k['hi'][1], 0)
            d = math.hypot(dx, dy)
            if d < 0.35 and (best is None or d < best[0]): best = (d, n)
        return best[1] if best else None
    def inv(n, p, sai):
        k = caixas[n]; L = k['CS'] if sai else k['CE']
        if L:
            v = min(L, key=lambda x: math.hypot(x[1][0] - p[0], x[1][1] - p[1]))
            if math.hypot(v[1][0] - p[0], v[1][1] - p[1]) < 2.5: return v[0]
        return k['CF']
    # cadeias: segmentos com o mesmo par de nós (A -> B) ou a mesma marca
    ch = collections.defaultdict(list)
    for s in S:
        if s['disc'] != disc: continue
        a, b = _no(s['desc']); ch[(a, b) if a else ('', s['trecho'])].append(s)
    for key, ss in ch.items():
        # ordem do escoamento pelo modelo (do mais alto ao mais baixo), pontas encadeadas
        ss = sorted(ss, key=lambda s: -max(s['a'][2], s['b'][2]))
        pts = []
        for s in ss:
            a, b = (s['a'], s['b']) if s['a'][2] >= s['b'][2] else (s['b'], s['a'])
            if not pts: pts = [a.copy(), b.copy()]
            elif np.linalg.norm(a[:2] - pts[-1][:2]) < 0.05: pts.append(b.copy())
            else: pts += [a.copy(), b.copy()]
        P = np.array(pts); de = ss[0]['de']
        Lc = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
        n0, n1 = caixa_de(P[0]), caixa_de(P[-1])
        z0m, z1m = P[0, 2] - de / 2, P[-1, 2] - de / 2            # GI do modelo
        if n0 and n1: g0, g1 = inv(n0, P[0], True), inv(n1, P[-1], False)
        elif n0: g0 = inv(n0, P[0], True); g1 = g0 - (z0m - z1m)
        elif n1: g1 = inv(n1, P[-1], False); g0 = g1 + (z0m - z1m)
        else: d = aj(P[0, 0], P[0, 1]); g0, g1 = 147 + z0m + d, 147 + z1m + d
        if g1 > g0: g1 = g0 - 0.005 * Lc[-1]                       # nunca sobe
        z = g0 + (g1 - g0) * Lc / max(Lc[-1], 1e-6) + de / 2
        U = utm(P); U[:, 2] = z
        nome = ss[0]['trecho'] if not key[0] else ss[0]['trecho']
        E.append(md.elemento(f'{disc}:{nome}', disc, disc, nome, 'gravidade', de, U, movel=False, de_ate=f'{n0 or "-"} -> {n1 or "-"}',
                             DN_mm=round(de * 1000), cota='GI das pranchas (CS/CE/CF)' if (n0 or n1) else 'modelo + ajuste do terreno'))
    for n, k in caixas.items():
        c, lo, hi = k['c'], k['lo'], k['hi']; U = utm([c])[0]
        lx, ly = hi[0] - lo[0], hi[1] - lo[1]
        if 'Canaleta' in ' '.join(m['nome'] for m in G[n]):
            # canaleta do campo (DirectShape alinhado ao campo): retângulo pelo comprimento
            th = -0.0939; lx, ly = 54.0, 0.5
            Cx.append(md.caixa_retangular(f'{disc}:{n}', disc, disc, U[0], U[1], lx, ly, ang_utm(th), k['CT'] - 0.30, k['CT'], nome=n,
                                          tipo='canaleta semicircular com grelha', cota='topo no terreno'))
            continue
        info = dict(nome=n, CT=round(k['CT'], 2), CF=round(k['CF'], 2), prof=round(k['CT'] - k['CF'], 2),
                    cota='CT/CF das pranchas' if all(k['rot']) else 'modelo + ajuste do terreno')
        if any('Anel' in m['nome'] for m in G[n]):          # poço de visita / poço de infiltração em anéis de concreto: circular
            Cx.append(md.caixa(f'{disc}:{n}', disc, disc, 'c', U[0], U[1], max(lx, ly) / 2, k['CF'] - 0.10, k['CT'], tipo='poço (anéis)', **info))
        else:
            Cx.append(md.caixa_retangular(f'{disc}:{n}', disc, disc, U[0], U[1], lx, ly, ang_utm(0.0), k['CF'] - 0.10, k['CT'], tipo='caixa', **info))
    return E, Cx


# ------------------------------------------------------------------ pressurizadas
SIST_AF = {'Alimentação': 'AL', 'Água Fria Potável': 'AFP', 'Água fria - Reuso': 'AR'}
BARRILETE = ('PCI-AF',)        # casa de bombas do incêndio: tubos acima do piso, com válvulas e conexões (não é rede enterrada)
# peças do barrilete (Revit: Conexões de tubo / Acessórios do tubo) -> (classe IFC, PredefinedType, tipo)
PECAS = [('Cotovelo', 'IfcPipeFitting', 'BEND', 'conexão'), ('Tê', 'IfcPipeFitting', 'JUNCTION', 'conexão'),
         ('Luva de redução', 'IfcPipeFitting', 'TRANSITION', 'conexão'), ('Retenção', 'IfcValve', 'CHECK', 'válvula'),
         ('Registro', 'IfcValve', 'ISOLATING', 'válvula'), ('Valvula', 'IfcValve', 'ISOLATING', 'válvula'),
         ('Pressostato', 'IfcSensor', 'PRESSURESENSOR', 'instrumento'), ('Manômetro', 'IfcFlowInstrument', 'PRESSUREGAUGE', 'instrumento')]


def barrilete(S, M, aj, log):
    """barrilete da casa de bombas do incêndio (20/10/2026, verificação da ferramenta: 9 pedaços de 4 a 10 cm soltos): os tubos
    PCI-AF-* ficam na cota do modelo do Daniel (sucção a 0,34 m e recalque a 1,09 m do piso, descida até a rede enterrada), um
    elemento por tubo, com as verticais, fora do estudo de cota; as válvulas (IfcValve), tês, curvas e reduções (IfcPipeFitting) e os
    instrumentos entram como peças no lugar delas, fechando os vãos entre os tubos. As conexões da rede enterrada (abaixo de
    −0,50 m) ficam com a ferramenta, que as põe na cota do estudo."""
    E, Cx = [], []
    for s in S:
        if s['disc'] != 'INC' or not s['trecho'].startswith(BARRILETE): continue
        P = np.array([s['a'], s['b']], float)
        if np.linalg.norm(P[1] - P[0]) < 0.005: continue
        U = utm(P); U[:, 2] = [147 + p[2] + aj(p[0], p[1]) for p in P]
        E.append(md.elemento(f'HID:{s["trecho"]}:{s["id"]}', 'HID', 'HID', s['trecho'], 'pressao', s['de'], U, cob_min=None, movel=False,
                             estudo=False, DN_mm=s['dn'], material=s['tipo'], sistema=s['sis'],
                             cota='modelo do Daniel (barrilete da casa de bombas, acima do piso)'))
    n = collections.Counter()
    for m in M:
        if m['disc'] != 'INC' or m['cat'] not in ('Conexões de tubo', 'Acessórios do tubo'): continue
        nome = m['nome'].split(' : ')[0]
        if any(kk.lower() in nome.lower() for kk, _ in CLASSE): continue   # equipamento (vaso de expansão, registro de recalque): equipamentos()
        lo, hi = m['lo'], m['hi']; c = (lo + hi) / 2
        if c[2] < -0.50: continue                                   # conexão da rede enterrada: a ferramenta põe na cota do estudo
        k = next((x for x in PECAS if x[0].lower() in nome.lower()), None)
        if not k: continue
        d = aj(c[0], c[1]); U = utm([c])[0]
        Cx.append(md.caixa_retangular(f'HID:{m["id"]}', 'HID', 'HID', U[0], U[1], max(hi[0] - lo[0], 0.05), max(hi[1] - lo[1], 0.05),
                                      ang_utm(0.0), 147 + lo[2] + d, 147 + hi[2] + d, nome=(m.get('trecho') or nome), classe_ifc=k[1], pred=k[2],
                                      tipo=k[3], familia=nome, equipamento='sim', cota='modelo do Daniel (casa de bombas)'))
        n[k[3]] += 1
    log(f'  barrilete do incêndio: {len(E)} tubos na cota do modelo, peças {dict(n)}')
    return E, Cx


def pressurizadas(S, M, T, aj, log):
    E, Cx = [], []
    def z0(p, disc, de):
        return 147 + T.z(p[0], p[1]) + aj(p[0], p[1]) - COB0[disc] - de / 2
    for disc, src, fonte in (('AF', 'AF', 'AF'), ('HID', 'INC', 'PCI'), ('SDAI', 'SDAI', 'PCI'), ('ELE', 'ELE', 'ELE')):
        segs = _plano(S, src, excluir=BARRILETE if disc == 'HID' else ())
        # pedaços do mesmo trecho (mergulhos e desvios do modelo atual) encadeados numa polilinha só, em planta
        por = collections.defaultdict(list)
        for s in segs: por[(re.sub(r'\.(m|d|g|R|t)\d*$', '', s['trecho']), round(s['de'], 4))].append(s)
        for (raiz, de), ss in por.items():
            for nc, P in enumerate(_cadeias(ss)):
                s = ss[0]; rede = disc; sub = ''
                if disc == 'AF':
                    rede = next((v for kk, v in SIST_AF.items() if s['sis'].startswith(kk)), 'AF')
                if disc == 'ELE':
                    # uma rede só para a elétrica (BT, iluminação e campo dividem caixas: CX-I01 recebe ELE-F-06, CX-F07 recebe ELE-CPS-05)
                    d = s.get('desc') or ''
                    sub = 'campo (CPS)' if s['trecho'].startswith('ELE-CPS') else ('iluminação externa (EL-002)' if 'EL-002' in d else 'BT (EL-001)')
                P = np.array([p for k, p in enumerate(P) if k == 0 or np.hypot(*(p[:2] - P[k - 1][:2])) > 0.02])
                if len(P) < 2: continue
                # nó a cada 4 m no máximo (colinear, planta igual): o perfil do estudo segue o terreno em vez de cortar reto entre
                # vértices distantes (AR-06 de 27 m ficava 0,13 m mais fundo no meio; lição da Pojuca)
                Q = [P[0]]
                for a, b in zip(P[:-1], P[1:]):
                    n = int(np.ceil(np.hypot(*(b[:2] - a[:2])) / 4.0))
                    Q += [a + (b - a) * j / n for j in range(1, n + 1)]
                P = np.array(Q)
                U = utm(P); U[:, 2] = [z0(p, disc, de) for p in P]
                # id único: o mesmo trecho pode sair em duas cadeias (PCI-AH-05 de 8,5 m e o pedaço de 0,27 m até o hidrante) — com o
                # mesmo id o congelamento copiava uma por cima da outra e o IFC saía com o pedaço em dobro e sem o trecho longo
                E.append(md.elemento(f'{disc}:{raiz}:{s["id"]}' + (f'#{nc + 1}' if nc else ''), disc, rede, raiz, 'pressao', de, U, cob_min=COB0[disc], movel=True,
                                     DN_mm=s['dn'], material=s['tipo'], sistema=s['sis'], cota='estudo de cota da rede', **({'circuito': sub} if sub else {})))
    e, c = barrilete(S, M, aj, log); E += e; Cx += c
    # caixas das pressurizadas (ELE, SDAI) e caixas de registro da AF
    G = _grupos([m for m in M if m['disc'] in ('ELE', 'SDAI', 'AF')])
    for n, ms in G.items():
        if not n or not ms: continue
        cats = {m['cat'] for m in ms}; nomes = ' '.join(m['nome'] for m in ms)
        disc = ms[0]['disc']
        lo = np.min([m['lo'] for m in ms], 0); hi = np.max([m['hi'] for m in ms], 0); c = (lo + hi) / 2
        lx, ly = hi[0] - lo[0], hi[1] - lo[1]
        if lx > 3 or ly > 3: continue
        d = aj(c[0], c[1]); zt = 147 + T.z(c[0], c[1]) + d; U = utm([c])[0]
        if 'Caixa de Passagem' in nomes:
            Cx.append(md.caixa_retangular(f'{disc}:{n}', disc, disc, U[0], U[1], lx, ly, ang_utm(0.0), zt - 0.60, zt, nome=n,
                                          tipo=re.search(r'Caixa de Passagem ([\dx]+)', nomes).group(1) if re.search(r'Caixa de Passagem ([\dx]+)', nomes) else '',
                                          cota='topo no terreno; fundo pelo estudo'))
        elif disc == 'AF' and 'CR-' in nomes:
            Cx.append(md.caixa_retangular(f'AF:{n}', 'AF', 'AF', U[0], U[1], lx, ly, ang_utm(0.0), zt - 0.45, zt, nome=n, tipo='caixa de registro',
                                          cota='topo no terreno; 0,45 m (premissa)'))
    # reservatório inferior de reúso
    R = np.array(RES_CANTOS); c = R.mean(0); u = R[2] - R[1]; th = math.atan2(u[1], u[0])
    lx = float(np.linalg.norm(R[2] - R[1])); ly = float(np.linalg.norm(R[1] - R[0]))
    zt = 147 + T.z(c[0], c[1]) + aj(c[0], c[1]); U = utm([c])[0]
    Cx.append(md.caixa_retangular('AF:RES-REUSO', 'AF', 'AL', U[0], U[1], lx, ly, ang_utm(th), zt - RES_ALTURA, zt, nome='Reservatório inferior de reúso',
                                  classe_ifc='IfcTank', tipo='reservatório enterrado', dimensoes=f'{lx:.2f} x {ly:.2f} x {RES_ALTURA:.2f} m',
                                  cota=f'topo no terreno; {RES_ALTURA:.2f} m de altura (premissa: a prancha só traz o contorno)'))
    log(f'  reservatório de reúso: {lx:.2f} x {ly:.2f} m, topo {zt:.2f}, fundo {zt - RES_ALTURA:.2f}')
    return E, Cx


# ------------------------------------------------------------------ equipamentos e estrutura
CLASSE = [('Quadro de Distribui', 'IfcElectricDistributionBoard'), ('Poste', 'IfcLightFixture'), ('Central de Alarme', 'IfcAlarm'),
          ('Abrigo para Hidrante', 'IfcFireSuppressionTerminal'), ('Bomba', 'IfcPump'), ('Motobomba', 'IfcPump'), ('Pressurizador', 'IfcPump'),
          ('Registro de Recalque', 'IfcFireSuppressionTerminal'), ('Hidrometro', 'IfcFlowMeter'), ('Vaso de Expans', 'IfcTank')]


def equipamentos(M, T, aj):
    Cx = []
    for m in M:
        if m['disc'] == 'EST': continue
        cl = next((c for k, c in CLASSE if k.lower() in m['nome'].lower()), None)
        if not cl: continue
        lo, hi = m['lo'], m['hi']; c = (lo + hi) / 2
        lx, ly = max(hi[0] - lo[0], 0.05), max(hi[1] - lo[1], 0.05)
        if cl == 'IfcLightFixture':
            # poste: o que encosta no chão é a base (o braço e a luminária abrem a caixa envolvente em ~2 m)
            V = m['tri'].reshape(-1, 3); b = V[V[:, 2] < lo[2] + 0.30]
            if len(b): c = np.r_[b[:, :2].mean(0), c[2]]
            lx = ly = 0.40
            hi = np.r_[hi[:2], hi[2]]; lo = np.r_[lo[:2], lo[2] - 0.80]          # base enterrada 0,80 m (premissa)
        d = aj(c[0], c[1]); U = utm([c])[0]
        disc = {'AF': 'AF', 'INC': 'HID', 'SDAI': 'SDAI', 'ELE': 'ELE'}.get(m['disc'], m['disc'])
        Cx.append(md.caixa_retangular(f'EQ:{m["id"]}', disc, 'EQ', U[0], U[1], lx, ly, ang_utm(0.0),
                                      147 + lo[2] + d, 147 + hi[2] + d, nome=m['nome'].split(' : ')[0], classe_ifc=cl, equipamento='sim',
                                      cota='modelo do Daniel + ajuste do terreno' + ('; base 0,40 x 0,40 x 0,80 m (premissa)' if cl == 'IfcLightFixture' else '')))
    return Cx


def estrutura(T, aj, cats=('Fundações estruturais', 'Pilares estruturais', 'Quadro estrutural')):
    """peças as built (fundação, pilar, viga) como prismas orientados pelo bloco; sobem com o ajuste do terreno do bloco."""
    Rh, oh = JD.tf_compart(JD.meta('ELE', G0)); links = JD.mapa_links('ELE', G0); Cx = []
    for f in sorted(os.listdir(G0)):
        if not (f.startswith('EST_') and f.endswith('_mesh.tsv')): continue
        tag = f[:-9]; m = JD.meta(tag, G0); nome = m['titulo'].split('__', 1)[-1]
        irmao = nome.replace('-ECC-', '-FUN-').replace('-EMT-', '-FUN-')
        if nome in links: R, o = links[nome]
        elif irmao in links: R, o = links[irmao]
        else: continue
        th = math.atan2(R[1, 0], R[0, 0]); bloco = tag.split('_')[1]
        for l in open(os.path.join(G0, f), encoding='utf-8'):
            r = l.rstrip('\n').split('\t')
            if len(r) < 9 or not r[8] or r[2] not in cats: continue
            v = np.array(r[8].split(','), dtype=float).reshape(-1, 3)      # coordenadas do arquivo do bloco (já no eixo do bloco)
            lo, hi = v.min(0), v.max(0); cl = (lo + hi) / 2
            if lo[2] + o[2] > 0.5: continue                                 # só o que está abaixo ou rente ao térreo
            c = R @ cl + o; d = aj(c[0], c[1]); U = utm([c])[0]
            tipo = 'pilar' if 'Pilar' in r[2] else ('viga' if 'Quadro' in r[2] else 'fundação')
            # forma real da peça (triângulos em UTM, mesmo ajuste do terreno): a ferramenta faz o clash por ela (clash.folga_malha /
            # refinar_forma) em vez da caixa envolvente — a sapata cônica afina para cima (DRE-126: caixa -0,05 m, forma real +0,66 m)
            W = np.array([R @ p + o for p in v]); M_ = utm(W); M_[:, 2] = 147 + W[:, 2] + d
            Cx.append(md.caixa_retangular(f'EST:{tag}:{r[1]}', 'EST', 'EST-' + bloco, U[0], U[1], hi[0] - lo[0], hi[1] - lo[1], ang_utm(th),
                                          147 + (R @ lo + o)[2] + d, 147 + (R @ hi + o)[2] + d, nome=r[3].split(' : ')[0], tipo=tipo, bloco=bloco,
                                          cota='as built + ajuste do terreno',
                                          **({'malha': M_.reshape(-1, 3, 3)} if len(M_) % 3 == 0 and len(M_) >= 3 else {})))
    return Cx


def ligados(c, E, tol=0.10):
    """(elemento, ponta) das pressurizadas da disciplina da caixa que terminam dentro dela (planta, tolerância tol)."""
    out = []
    for e in E:
        if e['tipo'] != 'pressao' or e['disc'] != c['disc']: continue
        for k in (0, -1):
            qx, qy = md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])
            if qx < tol and qy < tol: out.append((e, k))
    return out


def redes_das_caixas(E, Cx):
    """caixa de passagem, caixa de registro e equipamento (poste, quadro, abrigo) ficam na rede dos trechos que chegam neles:
    o clash não acusa o eletroduto que entra na própria caixa/poste e, se a caixa andar, os trechos acompanham."""
    for c in Cx:
        if c['disc'] not in ('ELE', 'SDAI', 'AF', 'HID') or c['info'].get('tipo') == 'reservatório enterrado': continue
        L = ligados(c, E, 0.30 if c['info'].get('equipamento') else 0.10)
        if L: c['rede'] = collections.Counter(e['rede'] for e, _ in L).most_common(1)[0][0]


def montar(log=print):
    R = json.load(open(ROT_JSON, encoding='utf-8'))
    T = JD.Terreno(g=G0); aj = Ajuste(T, pontos_base(R))
    log(f'  ajuste do terreno às CT das pranchas: mediana {aj.med:+.2f} m ({len(aj.d)} caixas)')
    SX, MX = JD.carregar(g=GX, est=None); JD.agrupar_caixas(SX, MX)
    SH, MH = JD.carregar(g=G0, est=None); JD.agrupar_caixas(SH, MH)
    E, Cx = [], []
    e, c = gravidade(SX, MX + [m for m in MH if m['disc'] == 'DRE' and m.get('grupo') in ('CX-18', 'CX-19', 'CX-20', 'CX-40')], 'DRE', R, T, aj, log); E += e; Cx += c
    e, c = gravidade(SH, MH, 'ESG', R, T, aj, log); E += e; Cx += c
    e, c = pressurizadas(SX, MX, T, aj, log); E += e; Cx += c
    Cx += equipamentos(MX, T, aj)
    redes_das_caixas(E, Cx)
    Cx += estrutura(T, aj)
    cnt = collections.Counter(x['disc'] for x in E); cc = collections.Counter(x['disc'] for x in Cx)
    log(f'  elementos {dict(cnt)} | caixas/peças {dict(cc)}')
    return E, Cx, aj
