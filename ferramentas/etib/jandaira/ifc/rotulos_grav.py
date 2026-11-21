# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — cotas das redes por gravidade tiradas das PRANCHAS (DRE-001 R00 e ESG-001 R01):
para cada caixa/poço do modelo do Daniel, os rótulos CT/CF/(prof) e CS/CE ligados a ela pela linha de chamada da prancha.
1) cópia do DWG em EXECUTIVO_R02/_copias e DXF (accoreconsole, um por vez);
2) ESG: transformação DWG -> interno por ICP com os tubos do modelo (semente = a da AF-001, mesma base HIG);
3) rótulo -> linha de chamada (ponta perto do texto) -> outra ponta -> caixa mais próxima do modelo (≤ 1,2 m).
Grava ETIB-JANDAIRA/RELATORIOS/IFC_R02/rotulos_gravidade.json (interno, m) e a conferência (CF prancha − CF modelo)."""
import os, sys, re, json, math, shutil, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import asbuilt as ab, rever, jan_dados as JD, dxfgeo, casar
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Projeto Modelagem\ETIB-JANDAIRA'
COP = os.path.join(BASE, r'RELATORIOS\EXECUTIVO_R02\_copias')
OUT = os.path.join(BASE, r'RELATORIOS\IFC_R02'); os.makedirs(OUT, exist_ok=True)
C = os.path.join(BASE, r'RELATORIOS\compat_R01')
TFJ = json.load(open(os.path.join(BASE, r'RELATORIOS\EXECUTIVO_R01\transformacoes_dwg_interno.json'), encoding='utf-8'))
DWG = {'DRE': r'PROJETO_ORIGINAL\IMP\03_DRE\24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg',
       'ESG': r'PROJETO_ORIGINAL\IMP\02_ESG\24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R01.dwg'}
rot = lambda a: np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
num = lambda s: float(re.findall(r'\d+[.,]\d+', s)[-1].replace(',', '.'))


def dxf(rel):
    base = os.path.splitext(os.path.basename(rel))[0]; copia = os.path.join(COP, base + '.dwg')
    if not os.path.exists(copia[:-4] + '.dxf'):
        shutil.copy2(os.path.join(BASE, rel), copia)
        rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '_.AUDIT', '_Y', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")',
                              'DXFX', '_.QUIT', '_Y'], copia + '.dxf.log', {'DXF_OUT': copia[:-4].replace('\\', '/') + '.dxf'})
    return copia[:-4] + '.dxf'


def transf_esg(fn, S):
    """DWG -> interno por ICP com os eixos dos tubos de esgoto (semente: AF-001, mesma base de arquitetura)."""
    g = dxfgeo.load(fn)
    S = [s for s in S if s['disc'] == 'ESG' and np.linalg.norm(s['b'][:2] - s['a'][:2]) > 0.5]
    M = np.array([s['a'][:2] + (s['b'][:2] - s['a'][:2]) * u for s in S for u in np.linspace(0, 1, max(2, int(np.linalg.norm(s['b'][:2] - s['a'][:2]) / 0.5)))])
    GS = casar.GradeSeg(casar.segmentos(g, lambda s: True, max_seg=300.0))
    # semente: campo 45x25 da base de arquitetura casado com o da SIT (como no exe_transf.py)
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\cps'); import retangulos
    Rc, oc = JD.tf_compart(JD.meta('ELE', os.path.join(C, 'geo')))
    u2i = lambda P: np.c_[P, np.zeros(len(P))] @ Rc.T + oc
    C_SIT = u2i(np.array([[631596.346, 8721147.338]]))[0][:2]
    p2 = u2i(np.array([[631596.346 + math.cos(math.radians(25.7107)), 8721147.338 + math.sin(math.radians(25.7107))]]))[0][:2]
    ANG = math.degrees(math.atan2(p2[1] - C_SIT[1], p2[0] - C_SIT[0]))
    Rr = [r for r in retangulos.retangulos(g, 44.9, 45.1) if abs(r['b'] - 25.0) < 0.02]
    cands = []
    for r0 in Rr[:1]:
        for flip in (0.0, 180.0):
            aa = math.radians(ANG - r0['ang'] + flip); tt = C_SIT - rot(aa) @ r0['c']; Ri = rot(-aa); ti = -Ri @ tt; cands.append((-aa, ti[0], ti[1]))
    if not cands:
        a0 = math.radians(TFJ['AF-001']['rot_inv_graus']); t0 = TFJ['AF-001']['t_inv']; cands = [(a0, t0[0], t0[1])]
    melhor = None
    for T0 in cands:
        T, n = casar.icp_seg(M, GS, T0, raios=(3.0, 1.0, 0.4, 0.15, 0.05, 0.02), it_por_raio=6)
        ad, d = casar.aderencia_seg(M, GS, T)
        if melhor is None or ad[0.05] > melhor[1][0.05]: melhor = (T, ad, d)
    T, ad, d = melhor
    a = -T[0]; t = -rot(a) @ np.array(T[1:])
    print('ESG: rot %.4f° t %s | %.0f%% a < 5 cm, mediana %.3f m' % (math.degrees(a), np.round(t, 3), 100 * ad[0.05], float(np.nanmedian(d))))
    return a, t, dict(rot_graus=math.degrees(a), t=t.tolist(), rot_inv_graus=math.degrees(T[0]), t_inv=list(T[1:]), aderencia_5cm=round(float(ad[0.05]), 3))


def rotulos(fn, a, t, caixas, raios=None):
    """caixas: {nome: centro interno (x, y)}. Devolve {nome: {'CT':[(v, ancora)], 'CF':..., 'P':..., 'CS':..., 'CE':...}}."""
    E = ab.entidades(fn); Rm = rot(a); I = lambda p: Rm @ np.asarray(p, float) + t
    tx = [e for e in E if e['typ'] in ('TEXT', 'MTEXT')]
    lab = []
    for e in tx:
        s = re.sub(r'\\[A-Za-z][^;]*;|[{}]', '', str(e['txt'])).strip().upper()
        m = re.match(r'^(CT|CF|CS|CE)\s*[.:]*\s*:?\s*(\d+[.,]\d+)', s)
        if m: lab.append((m.group(1), float(m.group(2).replace(',', '.')), e)); continue
        m = re.match(r'^\((\d+[.,]\d+)\)$', s)
        if m: lab.append(('P', float(m.group(1).replace(',', '.')), e))
    linhas = [e for e in E if 'pts' in e and not e.get('fechada') and len(e['pts']) >= 2 and np.ptp(e['pts'], axis=0).max() > 0.2
              and not e['lay'].startswith(('AP-Condutos', 'Simbolos', 'AP-Caixa', 'ES-Condutos', 'ESG-Condutos')) and 'Condut' not in e['lay']]
    pontas = collections.defaultdict(list)
    for L in linhas:
        for k_, q in ((0, L['pts'][0]), (-1, L['pts'][-1])): pontas[(round(q[0], 2), round(q[1], 2))].append((L, k_))
    def seguir(L, k_):
        """anda pela chamada a partir da ponta k_ (oposta ao texto) por linhas encostadas, até a ponta final (na caixa)."""
        vis = {L['h']}; q = L['pts'][k_]
        for _ in range(6):
            prox = [(M_, kk) for M_, kk in pontas.get((round(q[0], 2), round(q[1], 2)), []) if M_['h'] not in vis]
            if not prox: break
            M_, kk = prox[0]; vis.add(M_['h']); q = M_['pts'][-1 if kk == 0 else 0]
        return q
    nomes = list(caixas); CXc = np.array([caixas[n] for n in nomes])
    out = collections.defaultdict(lambda: collections.defaultdict(list)); sem = []
    for k, v, e in lab:
        p = e['p']; melhor = None
        for L in linhas:
            P = L['pts']
            for k_fim, k_outra in ((-1, 0), (0, -1)):
                # o texto fica sobre o último trecho da chamada (horizontal), até ~0,7 m acima/abaixo e dentro do comprimento
                seg = (P[-2], P[-1]) if k_fim == -1 else (P[1], P[0])
                d = ab.projetar(np.array(seg), p)[1]
                if d < 0.75 and (melhor is None or d < melhor[0]): melhor = (d, L, k_outra)
        if melhor is None: sem.append((k, v, e['h'])); continue
        anc = I(seguir(melhor[1], melhor[2])); dist = np.hypot(*(CXc - anc).T) - np.array([(raios or {}).get(n, 0.4) for n in nomes]); i = int(np.argmin(dist))
        if dist[i] > 0.9: sem.append((k, v, e['h'], round(float(dist[i]), 2))); continue
        out[nomes[i]][k].append((v, anc.tolist(), e['h']))
    return out, sem


if __name__ == '__main__':
    SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None); JD.agrupar_caixas(SH, MH)
    res = {}
    for disc in ('DRE', 'ESG'):
        fn = dxf(DWG[disc])
        if disc == 'DRE':
            tf = TFJ['DRE-001']; a, t = math.radians(tf['rot_graus']), np.array(tf['t'])
        else:
            a, t, info = transf_esg(fn, SH); res['transf_ESG'] = info
        grupos, raios = {}, {}
        for M in MH:
            g = str(M.get('grupo', ''))
            if M['disc'] == disc and M.get('glo') is not None and not g.startswith(('AN_', 'PLUV', 'PVC', disc + ' caixa')):
                grupos[g] = ((M['glo'] + M['ghi']) / 2)[:2]; raios[g] = max(0.0, float(np.max(M['ghi'][:2] - M['glo'][:2])) / 2)
        out, sem = rotulos(fn, a, t, grupos, raios)
        res[disc] = {n: dict(v) for n, v in out.items()}; res[disc + '_sem_caixa'] = sem
        # conferência com o modelo do Daniel
        dif = []
        for n, v in out.items():
            Mg = [M for M in MH if M.get('grupo') == n]
            if v.get('CF') and Mg: dif.append(v['CF'][0][0] - (147 + min(M['glo'][2] for M in Mg)))
        print('%s: %d caixas com rótulo de %d; %d rótulos sem caixa (%s)' % (disc, len(out), len(grupos), len(sem), collections.Counter(s[0] for s in sem)))
        if dif: print('   CF prancha − fundo modelo: mediana %+.2f, p10 %+.2f, p90 %+.2f' % (np.median(dif), np.percentile(dif, 10), np.percentile(dif, 90)))
    json.dump(res, open(os.path.join(OUT, 'rotulos_gravidade.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
