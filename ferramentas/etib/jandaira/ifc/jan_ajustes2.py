# -*- coding: utf-8 -*-
"""Jandaíra — segunda leva de ajustes para zerar o que sobrou (Anderson, 20/10/2026: "Sim. Tudo"; "se precisar pode aumentar
profundidade também além do 1,5 m"). Roda no adaptador depois de jan_ajustes.ajustar / mover_ele e antes do contornar:
  - cota_grav: sobe ou desce em bloco um pedaço da rede por gravidade (caixas/junções e os tubos entre elas) para passar por
    cima/baixo de sapata, viga, tubo pressurizado (na cota da rodada anterior) ou da outra rede por gravidade; o bloco cresce até
    nenhum tubo da borda ficar abaixo da declividade de projeto (ou 1% / 2% no DN 75); recobrimento mínimo 0,30 m;
  - mover_postes: poste cuja base (premissa 0,40 x 0,40 x 0,80 m) ficou crítica anda 0,2 a 1,0 m; o eletroduto que chega acompanha.
Os alvos saem dos críticos da rodada anterior (PRECLASH_R02/JAN_preclash_AD_conflitos_depois.csv); as decisões ficam acumuladas em
RELATORIOS/IFC_R02/JAN_cota_grav.json e JAN_postes.json, e são reaplicadas a cada rodada."""
import os, json, csv
import numpy as np
from preclash import clash as cl, modelo as md
from jan_ajustes import _nos, SAIDA

PRE = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02'
ORIG = (631578.10, 8721003.57)
_REF = None


def ref_press():
    """pressurizadas na cota da rodada anterior (cenário AD do JAN.json, em UTM)."""
    global _REF
    if _REF is None:
        J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8')); zr = J['zref']; _REF = []
        for e in J['elementos']:
            if e['disc'] not in ('AF', 'HID', 'SDAI', 'ELE') or 'AD' not in e['cen']: continue
            P = np.array((e['sol'] or {}).get('AD') or e['p'], float); P[:, 0] += ORIG[0]; P[:, 1] += ORIG[1]; P[:, 2] += zr
            _REF.append(md.elemento('REF:' + e['id'], e['disc'], e['rede'], e['trecho'], 'pressao', e['de'], P))
    return _REF


_REFZB = None


def ref_zb():
    """fundo das caixas na rodada anterior (as de passagem descem até o eletroduto mais fundo no estudo)."""
    global _REFZB
    if _REFZB is None:
        J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8')); zr = J['zref']
        _REFZB = {c['id']: c['zb'] + zr for c in J['caixas']}
    return _REFZB


def criticos_anteriores():
    fn = os.path.join(PRE, 'JAN_preclash_AD_conflitos_depois.csv')
    if not os.path.exists(fn): return []
    return [r for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';') if r['gravidade'] == 'CRÍTICA']


def _perto(objs, lo, hi, m=3.0):
    out = []
    for o in objs:
        if 'pts' in o:
            P = o.get('pts_sol', o['pts'])
            if np.all(P[:, :2].max(0) >= lo - m) and np.all(P[:, :2].min(0) <= hi + m): out.append(o)
        elif lo[0] - m - o['meia'] <= o['E'] <= hi[0] + m + o['meia'] and lo[1] - m - o['meia'] <= o['N'] <= hi[1] + m + o['meia']: out.append(o)
    return out


def cota_grav(E, C, regras, ter, log=print):
    G = [e for e in E if e['tipo'] == 'gravidade']
    CXG = {c['info'].get('nome'): c for c in C if c['disc'] in ('DRE', 'ESG') and c['info'].get('nome') and 'canaleta' not in c['info'].get('tipo', '')}
    OBS_CX = [c for c in C if c['disc'] == 'EST'] + [dict(c, zb=min(c['zb'], ref_zb().get(c['id'], c['zb']))) for c in C
                                                     if c['disc'] in ('ELE', 'SDAI', 'AF') and not c['info'].get('equipamento')]
    fn = os.path.join(SAIDA, 'JAN_cota_grav.json')

    def chave(e, k):
        n = _nos(e)[0 if k == 0 else 1]
        if n in CXG: return n
        p = e.get('pts_planta0', e['pts'])[k]; return 'J:%.1f,%.1f' % (round(p[0] * 10) / 10, round(p[1] * 10) / 10)

    adj = {}
    for e in G:
        for k in (0, -1): adj.setdefault(chave(e, k), []).append((e, k))
    L = {e['id']: max(float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T))), 1e-6) for e in G}
    s0 = {e['id']: (e['pts'][0, 2] - e['pts'][-1, 2]) / L[e['id']] for e in G}               # escoa da ponta 0 para a -1
    smin = {i: min(s, 0.01 if next(x['de'] for x in G if x['id'] == i) >= 0.1 else 0.02) - 1e-4 for i, s in s0.items()}

    def perfil(e, z0, z1):
        S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T))]); P = e['pts'].copy()
        P[:, 2] = z0 + (z1 - z0) * S / max(S[-1], 1e-6); return P

    def aplicar(grupo, dz, real=False):
        novo = {}
        for n in grupo:
            for e, k in adj.get(n, []):
                P = novo.get(e['id'], e['pts']); z0, z1 = P[0, 2], P[-1, 2]
                if k == 0: z0 = e['pts'][0, 2] + dz
                else: z1 = e['pts'][-1, 2] + dz
                novo[e['id']] = perfil(e, z0, z1)
        if real:
            for e in G:
                if e['id'] in novo: e['pts'] = novo[e['id']]; e['pts_sol'] = novo[e['id']].copy()
            for n in grupo:
                if n in CXG:
                    CXG[n]['zb'] += dz; CXG[n]['info']['dz_cota'] = round(CXG[n]['info'].get('dz_cota', 0.0) + dz, 3)
                    for kk in ('CF',):
                        if kk in CXG[n]['info']: CXG[n]['info'][kk] = round(CXG[n]['info'][kk] + dz, 2)
                    if 'prof' in CXG[n]['info']: CXG[n]['info']['prof'] = round(CXG[n]['info']['prof'] - dz, 2)
        return novo

    def fecho(grupo, dz):
        grupo = set(grupo)
        for _ in range(25):
            novo = aplicar(grupo, dz); ruim = None
            for i, P in novo.items():
                if (P[0, 2] - P[-1, 2]) / L[i] < smin[i]:
                    e = next(x for x in G if x['id'] == i)
                    fora = [chave(e, k) for k in (0, -1) if chave(e, k) not in grupo]
                    if not fora: return None
                    ruim = fora[0]; break
            if ruim is None: return grupo, novo
            grupo.add(ruim)
        return None

    R = dict(regras, folga=0.03)

    def criticos(els):
        ids = {x['id'] for x in els}
        lo = np.min([x['pts_sol'][:, :2].min(0) for x in els], 0); hi = np.max([x['pts_sol'][:, :2].max(0) for x in els], 0)
        ref = _perto(ref_press(), lo, hi); cxs = _perto(OBS_CX, lo, hi)
        outra = _perto([x for x in G if x['id'] not in ids and x['disc'] != els[0]['disc']], lo, hi)
        out = []
        for c in cl.detectar(els + ref + outra, cxs, R):
            if c['ligacao'] or c['folga'] >= 0.0 or not ({c['a'], c['b']} & ids): continue
            out.append(c)
        return out

    # alvos: clash na hora (não depende da rodada anterior), sem os pilares (pilar pede planta: jan_ajustes.ajustar)
    PIL = {c['id'] for c in OBS_CX if c['disc'] == 'EST' and (c['info'] or {}).get('tipo') == 'pilar'}
    dec, reg = [], []
    for passada in range(3):
        todos = criticos([dict(x, pts_sol=x['pts']) for x in G])
        alvos = []
        for c in sorted(todos, key=lambda c: c['folga']):
            if c['b'] in PIL or c['a'] in PIL: continue
            for i_ in (c['a'], c['b']):
                e = next((x for x in G if x['id'] == i_), None)
                if e and e not in alvos: alvos.append(e)
        feito = 0
        for e in alvos:
            base = [c for c in criticos([dict(e, pts_sol=e['pts'])]) if c['b'] not in PIL and c['a'] not in PIL]
            if not base: continue
            n0, n1 = chave(e, 0), chave(e, -1)
            melhor = None; DBG = os.environ.get('JAN_DBG') == e['trecho']
            for dz, g0 in [(s * p, g) for p in np.arange(0.05, 0.4001, 0.05) for s in (1, -1) for g in ({n0}, {n1}, {n0, n1})]:
                f = fecho(g0, dz)              # só uma ponta (o tubo inclina) ou o tubo inteiro
                if not f:
                    if DBG: log(f'    dz {dz:+.2f} {sorted(g0)}: fecho falhou')
                    continue
                grupo, novo = f
                els = [dict(x, pts_sol=novo[x['id']]) for x in G if x['id'] in novo]
                okc = True
                for x in els:
                    Q = cl.amostra(x['pts_sol'], 0.5); zt = np.array(ter.z(Q[:, :2]), float)
                    if np.any(np.isfinite(zt) & (Q[:, 2] + x['de'] / 2 > zt - 0.30)): okc = False; break
                if not okc:
                    if DBG: log(f'    dz {dz:+.2f} {sorted(grupo)}: recobrimento < 0,30 m')
                    continue
                antes = [c for c in criticos([dict(x, pts_sol=x['pts']) for x in G if x['id'] in novo]) if c['b'] not in PIL]
                depois = [c for c in criticos(els) if c['b'] not in PIL]
                if DBG: log(f'    dz {dz:+.2f} {len(grupo)} nós: antes {len(antes)} depois {len(depois)}: ' + '; '.join(f"{c['a'].split(':')[-1]} x {c['b']} {c['folga']:+.2f}" for c in depois[:4]))
                if any(e['id'] in (c['a'], c['b']) for c in depois) or len(depois) >= len(antes): continue
                custo = abs(dz) * len(grupo) + 0.001 * (dz < 0)
                if melhor is None or custo < melhor[0]: melhor = (custo, dz, grupo)
            ob = ', '.join(sorted({(c['b'] if c['a'] == e['id'] else c['a']).split(':')[-1] if not c['b'].startswith('EST:') else 'estrutura' for c in base}))
            if not melhor:
                if passada == 2: reg.append(dict(trecho=e['trecho'], obstaculo=ob, status='sem cota livre até ±0,40 m')); log(f"  {e['trecho']} × {ob[:40]}: sem cota livre até ±0,40 m")
                continue
            _, dz, grupo = melhor
            aplicar(grupo, dz, real=True); feito += 1
            dec.append({'nos': sorted(grupo), 'dz': round(float(dz), 3), 'trecho': e['trecho'], 'obstaculo': ob})
            reg.append(dict(trecho=e['trecho'], obstaculo=ob, dz=round(dz, 3), nos=sorted(grupo), status='cota ajustada'))
            log(f"  {e['trecho']} × {ob[:40]}: {'sobe' if dz > 0 else 'desce'} {abs(dz):.2f} m com {len(grupo)} nó(s)")
        if not feito and passada < 2: continue
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(dec, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(reg, open(os.path.join(SAIDA, 'JAN_cota_grav_registro.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    # caixas com cota nova (para as etiquetas CF/CS/CE das pranchas)
    json.dump({n: c['info']['dz_cota'] for n, c in CXG.items() if c['info'].get('dz_cota')}, open(os.path.join(SAIDA, 'JAN_cota_grav_caixas.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return dec


def mover_postes(E, C, regras, log=print):
    fn = os.path.join(SAIDA, 'JAN_postes.json'); dec = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else {}
    P = {c['id']: c for c in C if c['info'].get('classe_ifc') == 'IfcLightFixture'}
    G = [e for e in E if e['tipo'] == 'gravidade']
    OB = [c for c in C if c['disc'] in ('DRE', 'ESG', 'EST', 'SDAI', 'AF') and c['id'] not in P and not c['info'].get('equipamento')]
    R = dict(regras, folga=0.05)

    def ligados(c):
        out = []
        for e in E:
            if e['tipo'] != 'pressao' or e['disc'] != 'ELE': continue
            for k in (0, -1):
                qx, qy = md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])
                if qx < 0.30 and qy < 0.30: out.append((e, k))
        return out

    def ruins(c):
        lig = {e['id'] for e, _ in ligados(c)}
        # a elétrica do próprio poste (eletrodutos da iluminação) se acomoda em volta da base: não bloqueia
        lo = np.array([c['E'], c['N']]); els = [x for x in _perto(G + [r for r in ref_press() if r['disc'] != 'ELE'], lo, lo, 3.0) if x['id'] not in lig]
        out = [x for x in cl.detectar(els, [c], R) if not x['ligacao'] and x['folga'] < 0.05 and c['id'] in (x['a'], x['b'])]   # só o que pega o poste
        out += [o['id'] for o in _perto(OB, lo, lo, 4.0) if cl.folga_caixas(c, o)[0] < 0.05]
        return out

    for r in criticos_anteriores():
        if 'Poste' not in r['trecho_A'] + r['trecho_B']: continue
        p = np.array([float(r['E'].replace(',', '.')), float(r['N'].replace(',', '.'))])
        c = min(P.values(), key=lambda c: np.hypot(c['E'] - p[0], c['N'] - p[1]))
        if np.hypot(c['E'] - p[0], c['N'] - p[1]) > 1.0 or c['id'] in dec: continue
        u0 = np.array([c['E'], c['N']]) - p
        u0 = u0 / np.hypot(*u0) if np.hypot(*u0) > 0.02 else np.array([1.0, 0.0])
        dirs = [np.array([u0[0] * np.cos(a) - u0[1] * np.sin(a), u0[0] * np.sin(a) + u0[1] * np.cos(a)]) for a in np.radians([0, 45, -45, 90, -90, 135, -135, 180])]
        feito = None
        for d in np.arange(0.20, 2.5001, 0.10):
            for u in dirs:
                if not ruins(dict(c, E=c['E'] + u[0] * d, N=c['N'] + u[1] * d)): feito = [float(u[0] * d), float(u[1] * d)]; break
            if feito: break
        if feito: dec[c['id']] = feito
        else: log(f"  poste {c['id']}: sem posição livre até 2,50 m")
    reg = []
    for pid, v in dec.items():
        if pid not in P: continue
        c = P[pid]; v = np.array(v); lig = ligados(c)
        de = (c['E'], c['N']); c['E0'], c['N0'] = de; c['E'] += v[0]; c['N'] += v[1]
        for e, k in lig:
            e.setdefault('pts_planta0', e['pts'].copy()); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy()
        reg.append(dict(poste=pid, nome=c['info'].get('nome'), de=list(de), E=c['E'], N=c['N'], desloc=round(float(np.hypot(*v)), 2),
                        eletrodutos=[e['trecho'] for e, _ in lig]))
        log(f"  poste {pid} anda {np.hypot(*v):.2f} m; eletrodutos que acompanham: {', '.join(e['trecho'] for e, _ in lig) or '-'}")
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(dec, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(reg, open(os.path.join(SAIDA, 'JAN_postes_registro.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return reg


def caixas_extra():
    """caixas de passagem que ficaram críticas com tubo pressurizado de outra disciplina na rodada anterior: (caixa, tubo)."""
    out = set()
    for r in criticos_anteriores():
        if r['tipo'] == 'tubo×caixa' and r['disc_B'] in ('ELE', 'SDAI') and r['disc_A'] in ('ELE', 'SDAI', 'AF', 'HID') and r['disc_A'] != r['disc_B'] \
                and r['trecho_B'].startswith('CX-'):
            out.add((r['trecho_B'], r['trecho_A']))
    fn = os.path.join(SAIDA, 'JAN_caixas_extra.json')
    ant = {tuple(x) for x in json.load(open(fn, encoding='utf-8'))} if os.path.exists(fn) else set()
    tudo = sorted(ant | out); json.dump(tudo, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return tudo


def forcar_juncoes(E, moves, log=print):
    """junção de tubos por gravidade (sem caixa) levada à posição livre achada por busca_posicao.py: {(E, N) original: (dE, dN)}.
    Os tubos que chegam nela andam a ponta (cota igual). Acrescenta os tubos ao JAN_ajustes_gravidade_final.json (pranchas)."""
    fn = os.path.join(SAIDA, 'JAN_ajustes_gravidade_final.json'); fin = json.load(open(fn, encoding='utf-8'))
    for p, v in moves.items():
        p = np.array(p, float); v = np.array(v, float); lig = []
        for e in E:
            if e['tipo'] != 'gravidade': continue
            for k in (0, -1):
                if np.hypot(*(e['pts'][k, :2] - p)) < 0.15: lig.append((e, k))          # posição depois do ajustar
        for e, k in lig:
            e.setdefault('pts_planta0', e['pts'].copy()); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy()
            fin['tubos'] = [t for t in fin['tubos'] if t['elemento'] != e['id']] + [dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'],
                                                                                      antigo=e['pts_planta0'][:, :2].tolist(), novo=e['pts'][:, :2].tolist())]
        log(f"  junção em {p.round(2).tolist()} anda {np.hypot(*v):.2f} m (posição livre): {', '.join(e['trecho'] for e, _ in lig)}")
    json.dump(fin, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)


def forcar_caixas(E, C, moves, log=print):
    """caixa de passagem levada à posição livre achada por busca_posicao.py: {nome: (dE, dN)}; os eletrodutos que chegam nela acompanham.
    Acrescenta ao JAN_caixas_ele.json (pranchas)."""
    fn = os.path.join(SAIDA, 'JAN_caixas_ele.json'); reg = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    for nome, v in moves.items():
        b = next((c for c in C if c['info'].get('nome') == nome and c['disc'] in ('ELE', 'SDAI')), None)
        if b is None: continue
        v = np.array(v, float); lig = []
        for e in E:
            if e['tipo'] != 'pressao' or e['disc'] != b['disc']: continue
            for k in (0, -1):
                qx, qy = md.planta_local(b, e['pts'][k, 0], e['pts'][k, 1])
                if qx < 0.10 and qy < 0.10: lig.append((e, k))
        de = (b.get('E0', b['E']), b.get('N0', b['N'])); b['E0'], b['N0'] = de; b['E'] += v[0]; b['N'] += v[1]
        for e, k in lig:
            e.setdefault('pts_planta0', e['pts'].copy()); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy()
        reg = [r for r in reg if r.get('caixa') != nome] + [dict(caixa=nome, disc=b['disc'], elemento=b['id'], status='caixa deslocada', de=list(de), E=b['E'], N=b['N'],
                                                               desloc=round(float(np.hypot(b['E'] - de[0], b['N'] - de[1])), 2), lado=round(2 * b.get('mx', b['meia']), 3),
                                                               lado_y=round(2 * b.get('my', b['meia']), 3), rot=float(b.get('rot', 0.0)), tubos=[e['trecho'] for e, _ in lig])]
        log(f"  caixa {nome} anda {np.hypot(*v):.2f} m (posição livre); eletrodutos que acompanham: {', '.join(e['trecho'] for e, _ in lig) or '-'}")
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
