# -*- coding: utf-8 -*-
"""Jandaíra — drenagem no padrão de executivo final (campo society 50x30 entrando no lugar da espinha 45x25).
Duas pranchas, numa CÓPIA de cada DWG de PROJETO_ORIGINAL (nunca no original), com os comandos de preclash/executivo/revisao.lsp:

IMP DRE-001 R00 (implantação)
  - sai a espinha de peixe do campo 45x25 (DRE-001..011, 014, 015, 016, 022) e o DRE-040 (tubos, setas, tags e conexões);
  - entra a rede do campo 50x30 como está no JAN-DRE (espinha DN150 a 1 % descarregando a oeste na CX-43, drenos DN100 em espinha
    de peixe, canaletas dos lados longos), em linha dupla no layer e no estilo dos tubos da prancha, com setas e tags copiadas das da prancha;
  - os 6 ramais das caixas do perímetro (CX-40/41/42 e CX-14/16/19) encurtam até a canaleta (ponta, conexão e tags acompanham);
  - CX-43 mais funda: CF, CS e profundidade da etiqueta da caixa (mesma CT da prancha; profundidade = a do modelo).
CPS DRE-001 R01 (campo)
  - espinha com caimento para oeste (setas invertidas), prolongada até a CX-43 existente; sai o trecho a leste, a caixa de areia de lá
    vai para a posição da CX-43 e saem a saída e o aviso "interligar";
  - saídas das canaletas: no lugar das caixas de areia do projeto do campo, ligação direta nas caixas existentes do perímetro, no
    ponto dos ramais existentes (tubo, seta, tags e conexão da canaleta acompanham; a caixa de areia do desenho vai para a caixa existente).
Saída: ETIB-JANDAIRA/RELATORIOS/EXECUTIVO_R02/<prancha>_REVISADO.dwg (+ _cmd_*.txt e registro em JAN_dre_exec.json).
Uso: python -X utf8 jan_dre_exec.py [--so-comandos]"""
import sys, os, json, math, re, shutil, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral')
import asbuilt as ab, rever, jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Projeto Modelagem\ETIB-JANDAIRA'
OUT = os.path.join(BASE, r'RELATORIOS\EXECUTIVO_R02'); COP = os.path.join(OUT, '_copias'); os.makedirs(COP, exist_ok=True)
C = os.path.join(BASE, r'RELATORIOS\compat_R01')
DWG_IMP = r'PROJETO_ORIGINAL\IMP\03_DRE\24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg'
DWG_CPS = r'PROJETO_ORIGINAL\CPS\03_DRE\24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dwg'
SAI = ['DRE-%03d' % k for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 22, 40)]
RAM = {'DRE-079': 'N', 'DRE-053': 'N', 'DRE-018': 'N', 'DRE-084': 'S', 'DRE-058': 'S', 'DRE-031': 'S'}
CT_PRANCHA = 147.50          # CT da etiqueta da CX-43 na prancha (platô); a profundidade nova vem do modelo
rot = lambda a: np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
f4 = lambda v: '%.4f' % v


def dxf_da_copia(dwg_rel):
    base = os.path.splitext(os.path.basename(dwg_rel))[0]; copia = os.path.join(COP, base + '.dwg')
    if not os.path.exists(copia[:-4] + '.dxf'):
        shutil.copy2(os.path.join(BASE, dwg_rel), copia)
        rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '_.AUDIT', '_Y', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")',
                              'DXFX', '_.QUIT', '_Y'], copia + '.dxf.log', {'DXF_OUT': copia[:-4].replace('\\', '/') + '.dxf'})
    return base, copia, ab.entidades(copia[:-4] + '.dxf')


def dseg(p, a, b):
    d = b - a; L2 = d @ d; t = 0.0 if L2 < 1e-12 else float(np.clip((p - a) @ d / L2, 0, 1)); return float(np.hypot(*(a + d * t - p))), t


def pts_de(e): return e['pts'] if 'pts' in e else np.array([e['p']])


def centro(e): return pts_de(e).mean(0)


def ang(v): return math.degrees(math.atan2(v[1], v[0]))


def offset(P, w):
    """polilinha paralela a P a w (esquerda +), com quina em esquadria."""
    P = np.asarray(P, float); n = len(P); N = []
    for i in range(n - 1):
        u = (P[i + 1] - P[i]) / np.hypot(*(P[i + 1] - P[i])); N.append(np.array([-u[1], u[0]]))
    Q = [P[0] + N[0] * w]
    for i in range(1, n - 1):
        m = N[i - 1] + N[i]; m = m / np.hypot(*m); Q.append(P[i] + m * w / max(0.3, m @ N[i]))
    Q.append(P[-1] + N[-1] * w); return np.array(Q)


def seta_par(E, s):
    """seta de fluxo da prancha = linha (LWPOLYLINE) + ponta preenchida (HATCH) no mesmo layer; centro = meio da linha."""
    c = s['pts'].mean(0)
    return [s] + [e for e in E if e['typ'] == 'HATCH' and e['lay'] == s['lay'] and np.hypot(*(e['p'] - c)) < 0.35], c


def plc(L, molde, P, fechado=False):
    L.append('PLC\t%s\t%d\t%s' % (molde, 1 if fechado else 0, '\t'.join('%s\t%s' % (f4(x), f4(y)) for x, y in P)))


# ------------------------------------------------------------------ modelo (JAN-DRE: hoje e revisado)
SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None); JD.agrupar_caixas(SH, MH)
SX, MX = JD.carregar(g=os.path.join(C, 'geo_exec'), est=None); JD.agrupar_caixas(SX, MX)
T = JD.Terreno(g=os.path.join(C, 'geo'))
H = {s['trecho']: s for s in SH if s['disc'] == 'DRE'}; X = {s['trecho']: s for s in SX if s['disc'] == 'DRE'}
CX = {}
for M in MH + MX:              # posição das caixas pelo modelo de hoje (o agrupamento do revisado perde CX-18/19/20/40); a CX-43 vem do revisado
    g = str(M.get('grupo', ''))
    if M['disc'] == 'DRE' and re.match(r'^(CX|PI)-\d+$', g) and M.get('glo') is not None: CX[g] = M
cx_c = {g: ((M['glo'] + M['ghi']) / 2) for g, M in CX.items()}
ESP = [X['DRE-CPS-E%02d' % k] for k in range(1, 14)]
DRN = [X['DRE-CPS-D%02d' % k] for k in range(1, 13)]
INS = [l.rstrip('\n').split('\t') for l in open(os.path.join(C, 'cps_dre_instrucoes.tsv'), encoding='utf-8') if l.strip()]
CAN = [(r[1], np.array([float(r[2]), float(r[3])]), np.array([float(r[4]), float(r[5])])) for r in INS if r[0] == 'CAN']
c43 = cx_c['CX-43']; fundo43 = 147 + CX['CX-43']['glo'][2]; prof43 = 147 + T.z(c43[0], c43[1]) - fundo43
caixa_do_ramal = {mk: min(cx_c, key=lambda g: np.hypot(*(cx_c[g][:2] - X[mk]['b'][:2]))) for mk in RAM}
reg = {'CX-43': dict(fundo_modelo=round(fundo43, 3), prof=round(prof43, 2)), 'ramais': caixa_do_ramal}
print('CX-43: fundo do modelo %.3f, profundidade %.2f m; ramais -> %s' % (fundo43, prof43, caixa_do_ramal))


# ================================================================== IMP DRE-001 (implantação)
def plano_imp(E):
    TF = json.load(open(os.path.join(BASE, r'RELATORIOS\EXECUTIVO_R01\transformacoes_dwg_interno.json'), encoding='utf-8'))['DRE-001']
    Ri, ti = rot(math.radians(TF['rot_inv_graus'])), np.array(TF['t_inv'])
    D = lambda p: Ri @ np.asarray(p[:2], float) + ti
    sai = [(D(H[m]['a0']), D(H[m]['b0'])) for m in SAI]
    fica = [(D(s['a0']), D(s['b0'])) for s in SH if s['disc'] == 'DRE' and s['trecho'] not in SAI]
    caixas = [D(c) for c in cx_c.values()]
    camada = lambda e: e['lay'].startswith(('AP-', 'Simbolos'))
    dmin = lambda p, segs: min(dseg(p, a, b)[0] for a, b in segs)
    perto_cx = lambda P: any(all(np.hypot(*(q - c)) < 0.75 for q in P) for c in caixas)      # peça da própria caixa (símbolo, tampa)
    apagar, log = [], []
    for e in E:
        if not camada(e): continue
        P = pts_de(e); dd = [dmin(p, sai) for p in P]
        if 'pts' in e and e['lay'] != 'AP-Sentido conduto':
            if max(dd) <= 0.40 and not perto_cx(P) and min(dmin(p, fica) for p in P) > 0.25: apagar.append(e)
        else:
            c = centro(e); d1 = dmin(c, sai)
            if d1 <= 1.5 and d1 < dmin(c, fica) - 0.10 and not perto_cx([c]): apagar.append(e)
    ap = {e['h'] for e in apagar}
    log.append('espinha 45x25 e DRE-040: %d entidades saem (%s)' % (len(apagar), dict(collections.Counter(e['lay'] for e in apagar))))
    # moldes (antes de apagar): linha de tubo DN150 (DRE-040), de dreno (DRE-001), tags e setas
    def molde_linha(mk):
        a, b = D(H[mk]['a0']), D(H[mk]['b0'])
        c = [e for e in apagar if e['typ'] in ('LINE', 'LWPOLYLINE') and e['lay'] == 'AP-Condutos' and max(dseg(p, a, b)[0] for p in e['pts']) < 0.2]
        return max(c, key=lambda e: np.hypot(*(e['pts'][-1] - e['pts'][0])))
    def molde_tags(mk):
        a, b = D(H[mk]['a0']), D(H[mk]['b0']); m = (a + b) / 2
        tx = sorted([e for e in apagar if e['typ'] in ('TEXT', 'MTEXT') and e['lay'] == 'AP-Textos conduto'], key=lambda e: np.hypot(*(e['p'] - m)))
        g = [tx[0]] + [t for t in tx[1:] if np.hypot(*(t['p'] - tx[0]['p'])) < 1.2][:2]
        seta = min([e for e in apagar if e['lay'] == 'AP-Sentido conduto' and 'pts' in e], key=lambda e: dseg(centro(e), a, b)[0] + 0.01 * np.hypot(*(centro(e) - m)))
        jus = (b - a) if H[mk]['a0'][2] > H[mk]['b0'][2] else (a - b)        # sentido de escoamento do tubo de onde vem a seta
        return g, seta, jus
    L_cria, L_mod, L_del = [], [], []
    m150, m100 = molde_linha('DRE-040')['h'], molde_linha('DRE-001')['h']
    tg150, seta150, jus150 = molde_tags('DRE-040'); tg100, seta100, jus100 = molde_tags('DRE-001')
    log.append('moldes: tubo DN150 %s, DN100 %s; tags %s / %s; setas %s / %s' % (m150, m100, [t['txt'] for t in tg150], [t['txt'] for t in tg100], seta150['h'], seta100['h']))
    # espinha nova: E01..E12 em linha + E13 até a borda da CX-43
    P = [D(ESP[0]['a'])] + [D(s['b']) for s in ESP[:-1]]
    u = P[-1] - D(c43); u = u / np.hypot(*u); fim = D(c43) + u * 0.40
    Pesp = np.array(ab.simplificar(np.array(P + [fim]), 0.02))
    for w in (0.075, -0.075): plc(L_cria, m150, offset(Pesp, w))
    eixo_esp = [(D(s['a']), D(s['b'])) for s in ESP]
    dir_esp = (Pesp[-1] - Pesp[0]) / np.hypot(*(Pesp[-1] - Pesp[0]))
    # drenos: da ponta alta até a parede da espinha
    for s in DRN:
        a, b = D(s['a']), D(s['b']); v = (b - a) / np.hypot(*(b - a)); sn = abs(np.cross(v, dir_esp))
        b2 = b - v * (0.075 / max(sn, 0.2))
        for w in (0.05, -0.05): plc(L_cria, m100, offset(np.array([a, b2]), w))
    # tags e setas: copiadas das da prancha
    def tags(g, base_seg, a, b, lado=1.0, frac=0.5):
        cen = np.mean([t['p'] for t in g], 0); v = (b - a) / np.hypot(*(b - a)); n = np.array([-v[1], v[0]])
        if n[1] < 0: n = -n
        alvo = a + (b - a) * frac + n * 0.75 * lado
        for t in g: L_cria.append('CPR\t%s\t%s\t%s\t%s\t%s\t0' % (t['h'], f4(cen[0]), f4(cen[1]), f4(alvo[0]), f4(alvo[1])))
    def seta(sm, jus, a, b, frac=0.3):
        par, c = seta_par(E, sm); p = a + (b - a) * frac
        for x in par: L_cria.append('CPR\t%s\t%s\t%s\t%s\t%s\t%.3f' % (x['h'], f4(c[0]), f4(c[1]), f4(p[0]), f4(p[1]), ang(b - a) - ang(jus)))
    for s in DRN:
        a, b = D(s['a']), D(s['b']); tags(tg100, None, a, b, frac=0.45); seta(seta100, jus100, a, b, frac=0.7)
    for k in (2, 6, 10, 12):                                           # espinha: tags em alguns trechos e no trecho até a CX-43
        a, b = eixo_esp[k]; tags(tg150, None, a, b, lado=-1.0); seta(seta150, jus150, a, b, frac=0.5)
    # canaletas (54 x 0,50) e nota
    for nome, c, ux in CAN:
        vy = np.array([-ux[1], ux[0]])
        Q = [D(c + su * ux * 27.0 + sv * vy * 0.25) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        plc(L_cria, m150, Q, fechado=True)
        lado = 1 if nome.endswith('N') else -1; q = D(c + ux * 8.0 + vy * (0.85 * lado)) if lado > 0 else D(c + ux * 8.0 - vy * 1.25)
        L_cria.append('TXC\t%s\t%s\t%s\t%.6f\tCANALETA SEMICIRCULAR EM CONCRETO COM GRELHA METÁLICA' % (tg150[0]['h'], f4(q[0]), f4(q[1]), 0.0))
    q = D(np.array([90.95, 114.11]) + np.array([0.0, -4.0]))
    L_cria.append('TXC\t%s\t%s\t%s\t%.6f\tDRENOS ENVELOPADOS EM GEOTÊXTIL E COLCHÃO DE BRITA' % (tg150[0]['h'], f4(q[0] - 6), f4(q[1]), 0.0))
    # ramais encurtados até a canaleta
    for mk in RAM:
        o, n = H[mk], X[mk]; pa0, pna, pb = D(o['a0']), D(n['a']), D(o['b0']); v = pna - pa0; Lr = np.hypot(*(pb - pa0))
        nv = nm = nt = 0
        for e in E:
            if e['h'] in ap: continue
            Pp = pts_de(e)
            if e['lay'] == 'AP-Condutos' and 'pts' in e and np.ptp(Pp, axis=0).max() > 0.5:
                if max(dseg(p, pa0, pb)[0] for p in Pp) > 0.25: continue
                for k in (0, len(Pp) - 1):
                    if dseg(Pp[k], pa0, pb)[1] * Lr < 0.35:
                        kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1); q = Pp[k] + v
                        L_mod.append('VTX\t%s\t%d\t%s\t%s' % (e['h'], kk, f4(q[0]), f4(q[1]))); nv += 1
            elif camada(e) and np.ptp(Pp, axis=0).max() < 0.5 and np.hypot(*(Pp - pa0).T).max() < 0.35:
                L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(v[0]), f4(v[1]))); nm += 1
            elif e['lay'] in ('AP-Textos conduto', 'AP-Sentido conduto'):
                c = centro(e); d, t = dseg(c, pa0, pb)
                if d < 1.5 and d <= dmin(c, fica + sai) + 1e-6 and t * Lr < Lr / 2 + 1.0:
                    L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(v[0] / 2), f4(v[1] / 2))); nt += 1
        log.append('%s encurtado %.2f m até a canaleta: %d ponta(s) de tubo, %d conexão(ões), %d tag(s)/seta(s)' % (mk, np.hypot(*v), nv, nm, nt))
    # CX-43: etiqueta com CF, profundidade e CS novos
    c43d = D(c43); tx = [e for e in E if e['typ'] in ('TEXT', 'MTEXT') and e['lay'] == 'TQ-Textos conduto' and np.hypot(*(e['p'] - c43d)) < 6.0]
    num = lambda t: float(re.findall(r'[\d.]+', t['txt'].replace(',', '.'))[-1])
    cf = min([t for t in tx if t['txt'].startswith('CF')], key=lambda t: np.hypot(*(t['p'] - c43d)))       # etiqueta CT/CF/(prof) da caixa
    ct = min([t for t in tx if t['txt'].startswith('CT')], key=lambda t: np.hypot(*(t['p'] - cf['p'])))
    cf_novo = num(ct) - prof43
    alvo = {'CF': cf, 'PROF': min([t for t in tx if re.match(r'^\(\d', t['txt'])], key=lambda t: np.hypot(*(t['p'] - cf['p']))),
            'CS': min([t for t in tx if t['txt'].startswith('CS') and abs(num(t) - num(cf)) < 0.005], key=lambda t: np.hypot(*(t['p'] - c43d)))}
    reg['CX-43'].update(ct_prancha=num(ct), cf_prancha=num(cf), cf_novo=round(cf_novo, 2))
    novo = {'CF': 'CF.: %.2f' % cf_novo, 'PROF': '(%05.2f)' % prof43, 'CS': 'CS.: %.2f' % cf_novo}
    for k, t in alvo.items():
        L_mod.append('ST\t%s\t%s' % (t['h'], novo[k])); log.append('CX-43 %s: %r -> %r (%s)' % (k, t['txt'], novo[k], t['h']))
    for e in apagar: L_del.append('DEL\t%s' % e['h'])
    return L_cria + L_mod + L_del, log


# ================================================================== CPS DRE-001 (campo)
def plano_cps(E):
    TC = json.load(open(os.path.join(BASE, r'CAD_GEORREFERENCIADO\transformacao_CPS_DRE-001-DRG-R01_local_para_UTM.json'), encoding='utf-8'))
    R, t = rot(math.radians(TC['rot_int_graus'])), np.array(TC['t_int'])
    Lc = lambda p: R.T @ (np.asarray(p[:2], float) - t)                 # interno -> local do CPS
    L_cria, L_mod, L_del, log = [], [], [], []
    feitos = set()
    lay = lambda e, *k: e['lay'].startswith(k)
    Y0 = 17.07                                                           # eixo da espinha no desenho
    c43l = Lc(c43)
    # --- setas da espinha: invertidas (caimento para oeste)
    setas = [seta_par(E, e) for e in E if lay(e, 'AP-Sentido') and 'pts' in e and abs(centro(e)[1] - Y0) < 0.2 and 3.0 < centro(e)[0] < 50.5]
    # --- trecho a leste da última junção (tubo, conexões, caixa de areia, saída, tags e aviso): sai; a caixa vai para a CX-43
    ca_l = np.array([61.27, 16.96])
    leste = [e for e in E if centro(e)[0] > 50.55 and pts_de(e)[:, 0].min() > 50.40 and abs(centro(e)[1] - Y0) < 2.6 and centro(e)[0] < 70]
    ca = [e for e in leste if np.hypot(*(pts_de(e) - ca_l).T).max() < 0.6]
    # --- prolongamento a oeste até a CX-43
    oeste = [e for e in E if lay(e, 'AP-Condutos') and 'pts' in e and abs(e['pts'][:, 0].min() - 3.58) < 0.05 and abs(centro(e)[1] - Y0) < 0.12]
    x_borda = c43l[0] + 0.40
    tg_esp = sorted([e for e in E if lay(e, 'AP-Textos') and 45.5 < e['p'][0] < 47.5 and abs(e['p'][1] - Y0) < 0.4], key=lambda e: e['p'][0])
    par_o, cs = min(setas, key=lambda s: s[1][0])
    xm = (3.58 + x_borda) / 2; cen = np.mean([e['p'] for e in tg_esp], 0)
    for e in tg_esp: L_cria.append('CPR\t%s\t%s\t%s\t%s\t%s\t0' % (e['h'], f4(cen[0]), f4(cen[1]), f4(xm - 2.0), f4(cen[1])))
    for e in par_o: L_cria.append('CPR\t%s\t%s\t%s\t%s\t%s\t180' % (e['h'], f4(cs[0]), f4(cs[1]), f4(xm + 1.5), f4(cs[1])))
    interl = [e for e in E if e['typ'] in ('TEXT', 'MTEXT') and 'INTERLIGAR' in e['txt']]
    molde_txt = interl[0]['h']
    # a CX-43 fica fora da janela da folha (borda oeste em x = -8,26): o aviso vai junto da borda, sob a espinha
    L_cria.append('TXC\t%s\t%s\t%s\t0\tSEGUE PARA CAIXA EXISTENTE (DRE-001 DA IMPLANTAÇÃO)' % (molde_txt, f4(-7.9), f4(Y0 - 1.35)))
    for par, c in setas:
        for e in par: L_mod.append('RT\t%s\t%s\t%s\t180' % (e['h'], f4(c[0]), f4(c[1]))); feitos.add(e['h'])
    for e in oeste:
        p = e['pts'][0] if e['pts'][0][0] < e['pts'][-1][0] else e['pts'][-1]; k = 0 if e['pts'][0][0] < e['pts'][-1][0] else (len(e['pts']) - 1 if e['typ'] == 'LWPOLYLINE' else 1)
        L_mod.append('VTX\t%s\t%d\t%s\t%s' % (e['h'], k, f4(x_borda), f4(p[1]))); feitos.add(e['h'])
    v43 = c43l - np.mean(np.vstack([pts_de(e) for e in ca if lay(e, 'AP-Caixa')]), 0)
    for e in ca: L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(v43[0]), f4(v43[1]))); feitos.add(e['h'])
    for e in leste:
        if e['h'] not in feitos: L_del.append('DEL\t%s' % e['h']); feitos.add(e['h'])
    log.append('espinha: %d setas invertidas; prolongada de x=3,58 até a CX-43 (x=%.2f; %d linhas); leste: %d entidades saem, caixa de areia (%d entidades) vai para a CX-43'
               % (len(setas), x_borda, len(oeste), len([e for e in leste if e not in ca]), len(ca)))
    # --- saídas das canaletas -> caixas existentes do perímetro
    yc = {'N': 34.06, 'S': 0.08}; yca = {'N': 39.97, 'S': -5.82}
    saidas = {}
    for sd in ('N', 'S'):           # eixo de cada saída: par de linhas verticais entre a canaleta e a caixa de areia
        xs = sorted(float(e['pts'][:, 0].mean()) for e in E if lay(e, 'AP-Condutos') and 'pts' in e and len(e['pts']) == 2
                    and abs(e['pts'][0][0] - e['pts'][1][0]) < 0.01 and abs(min(e['pts'][:, 1], key=lambda y: abs(y - yc[sd])) - yc[sd]) < 0.2
                    and abs(max(e['pts'][:, 1], key=lambda y: abs(y - yc[sd])) - yca[sd]) < 0.6)
        pares = []
        for x in xs:
            if pares and x - pares[-1][-1] < 0.2: pares[-1].append(x)
            else: pares.append([x])
        saidas[sd] = [float(np.mean(p)) for p in pares]
    log.append('saídas das canaletas no desenho: %s' % {k: [round(x, 2) for x in v] for k, v in saidas.items()})
    for mk, sd in RAM.items():
        na, bx = Lc(X[mk]['a']), Lc(cx_c[caixa_do_ramal[mk]])
        xo = min(saidas[sd], key=lambda x: abs(x - na[0]))
        sg = 1 if sd == 'N' else -1
        y_in, y_ca = yc[sd], yca[sd]
        entre = lambda y: (min(y_in, y_ca) - 0.15) < y < (max(y_in, y_ca) + 0.15)
        alem = lambda y: (y - y_ca) * sg > 0.25
        perto_x = lambda e, w: np.abs(pts_de(e)[:, 0] - xo).max() < w
        tubo1 = [e for e in E if lay(e, 'AP-Condutos') and 'pts' in e and perto_x(e, 0.15) and all(entre(y) for y in e['pts'][:, 1]) and np.ptp(e['pts'][:, 1]) > 1]
        seta1 = [seta_par(E, e) for e in E if lay(e, 'AP-Sentido') and 'pts' in e and perto_x(e, 0.15) and entre(centro(e)[1])]
        tag1 = [e for e in E if lay(e, 'AP-Textos') and abs(e['p'][0] - xo) < 0.8 and entre(e['p'][1]) and 'CANALETA' not in e['txt']]
        cap = [e for e in E if lay(e, 'Simbolos') and perto_x(e, 0.2) and np.abs(pts_de(e)[:, 1] - y_in).max() < 0.15]
        ca_c = np.vstack([pts_de(e) for e in E if lay(e, 'AP-Caixa') and np.hypot(*(centro(e) - np.array([xo, y_ca]))) < 0.8]).mean(0)
        cxa = [e for e in E if e['h'] not in feitos and np.hypot(*(pts_de(e) - ca_c).T).max() < 0.65]
        fora = [e for e in E if e['h'] not in feitos and abs(centro(e)[0] - xo) < 0.5 and alem(centro(e)[1]) and abs(centro(e)[1] - y_ca) < 3.6 and e['lay'] != '0']
        fim = [e for e in E if e['typ'] == 'INSERT' and re.match(r'\*U1[01]$', e['nome']) and abs(e['p'][0] - xo) < 0.3 and abs(e['p'][1] - y_ca) < 3.6 and alem(e['p'][1])]
        av = [e for e in interl if abs(e['p'][0] - (xo + 4.5)) < 1.5 and abs(e['p'][1] - y_ca) < 5.0 and alem(e['p'][1])]
        lid = [e for e in E if e['lay'] == '0' and e['typ'] == 'LWPOLYLINE' and len(e['pts']) == 3 and any(np.hypot(*(e['pts'][0] - (a['p'] + [0, 0.27]))) < 0.6 or abs(e['pts'][0][1] - a['p'][1]) < 0.4 and abs(e['pts'][0][0] - a['p'][0]) < 0.2 for a in av)]
        # tubo novo: da canaleta (ponto do ramal) até a parede da caixa existente
        u = (bx - na) / np.hypot(*(bx - na)); fimt = bx - u * 0.40; ini = np.array([na[0], y_in + 0.06 * sg])
        mold = tubo1[0]['h']
        for w in (0.075, -0.075): plc(L_cria, mold, offset(np.array([ini, fimt]), w))
        mid_old = np.array([xo, (y_in + y_ca) / 2]); mid_new = (ini + fimt) / 2
        for par, c in seta1:
            dv = mid_new + u * 0.3 - c; da = ang(u) - (90 if sd == 'N' else -90)
            for e in par:
                L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(dv[0]), f4(dv[1])))
                if abs(da) > 0.5: L_mod.append('RT\t%s\t%s\t%s\t%.3f' % (e['h'], f4(c[0] + dv[0]), f4(c[1] + dv[1]), da))
        seta1 = [e for par, _ in seta1 for e in par]
        dv = mid_new - mid_old
        for e in tag1: L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(dv[0]), f4(dv[1])))
        dv = np.array([ini[0] - xo, 0.0])
        for e in cap: L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(dv[0]), f4(dv[1])))
        dv = bx - ca_c
        for e in cxa: L_mod.append('MV\t%s\t%s\t%s' % (e['h'], f4(dv[0]), f4(dv[1])))
        q = bx + np.array([0.6, 0.25 if sd == 'N' else -0.45])
        L_cria.append('TXC\t%s\t%s\t%s\t0\tCAIXA EXISTENTE DA REDE EXTERNA' % (molde_txt, f4(q[0]), f4(q[1])))
        sai_ = {e['h'] for e in tubo1 + fora + fim + av + lid} - {e['h'] for e in cxa + seta1 + tag1 + cap}
        for h in sorted(sai_): L_del.append('DEL\t%s' % h)
        for e in tubo1 + seta1 + tag1 + cap + cxa: feitos.add(e['h'])
        feitos |= sai_
        log.append('%s (%s, saída x=%.2f -> ramal x=%.2f): tubo %d, seta %d, tags %d, conexão %d, caixa %d entidades -> %s; saem %d (tubo além da caixa, fim, aviso, linha de chamada)'
                   % (mk, sd, xo, na[0], len(tubo1), len(seta1), len(tag1), len(cap), len(cxa), caixa_do_ramal[mk], len(sai_)))
    return L_cria + L_mod + L_del, log


def aplicar(base, copia, linhas, so):
    cmd = os.path.join(OUT, '_cmd_%s.txt' % base); open(cmd, 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    dst = os.path.join(OUT, base + '_REVISADO.dwg')
    if so: return cmd, dst
    out = rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', '_.AUDIT', '_Y', '(load "%s")' % rever.LSP, 'REVR01', '_.AUDIT', '_Y', '_.QUIT', '_Y'],
                        copia + '.rev.log', {'REV_CMD': cmd, 'REV_OUT': dst.replace('\\', '/')})
    print('  ', out[-160:], '->', 'OK' if os.path.exists(dst) else 'FALHOU'); return cmd, dst


if __name__ == '__main__':
    so = '--so-comandos' in sys.argv
    res = {}
    for nome, dwg, plano in (('IMP DRE-001', DWG_IMP, plano_imp), ('CPS DRE-001', DWG_CPS, plano_cps)):
        if ('--so-cps' in sys.argv and nome.startswith('IMP')) or ('--so-imp' in sys.argv and nome.startswith('CPS')): continue
        base, copia, E = dxf_da_copia(dwg)
        linhas, log = plano(E)
        print('%s: %d comandos' % (nome, len(linhas)))
        for x in log: print('   ', x)
        cmd, dst = aplicar(base, copia, linhas, so)
        res[nome] = dict(dwg=dwg, saida=dst, comandos=cmd, registro=log)
    res['modelo'] = reg
    json.dump(res, open(os.path.join(OUT, 'JAN_dre_exec.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
