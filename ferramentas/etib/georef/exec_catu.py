# -*- coding: utf-8 -*-
"""ETIB Catu — executivos revisados da compatibilização (R01), em CÓPIAS dos DWG originais (PROJETO_ORIGINAL só é lido).
Para cada prancha com traçado alterado no cenário de entrega do preclash (AF, EL-001, EL-002, INC-001):
  - trecho antigo: as entidades do desenho que coincidem com o trecho alterado vão para o layer COMPAT-R01-REMOVIDO (tracejado);
    quando a entidade também cobre trecho não alterado, o pedaço antigo é redesenhado tracejado por cima;
  - trecho novo: polilinha no layer COMPAT-R01-NOVO; caixa deslocada: cópia do bloco na posição nova (NOVO) e a original em REMOVIDO;
  - nuvem de revisão (COMPAT-R01-NUVEM) em volta de cada alteração, com etiqueta Rnn;
  - mergulhos (só profundidade, sem mudar a planta): marcador Mnn no ponto;
  - quadro de notas (COMPAT-R01-NOTAS) à direita da rede, com o texto pronto de cada Rnn/Mnn (dos CSV do preclash).
Coordenadas: UTM -> local pela translação do georreferenciamento (CAD_GEORREFERENCIADO/transformacao_*_local_para_UTM.json).
Saída: ETIB-CATU/EXECUTIVO_REVISADO/<nome original>_COMPAT-R01.dwg + _COMPAT-R01_notas.csv; scripts em work/CATU/exec/.
O accoreconsole roda UM por vez (run_acc.ps1), só nas cópias.
Uso: .venv/Scripts/python.exe -X utf8 georef/exec_catu.py [cenario] [--so-gerar]"""
import os, sys, csv, json, shutil, subprocess, collections
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from dxf_ler import ler          # noqa: E402

BASE = r'D:\Projeto Modelagem\ETIB-CATU'
PRE = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
GEO = os.path.join(BASE, 'CAD_GEORREFERENCIADO')
ORIG = os.path.join(BASE, 'PROJETO_ORIGINAL', 'IMP')
SAI = os.path.join(BASE, 'EXECUTIVO_REVISADO')
WRK = os.path.join(AQUI, 'work', 'CATU', 'exec')
DXF = os.path.join(AQUI, 'work', 'CATU', 'dxf')
ORIGEM = np.array([567700.0, 8634650.0])
DATA = '19/10/2026'
P = '24-049-CAU-RNV-ETIB-IMP-PE-'
PRANCHAS = {   # tag -> (arquivo original, subpasta, redes do preclash, prefixos de trecho)
    'AF': (P + 'AGF-001-R02', '01_AF', ('AF',)),
    'EL1': (P + 'EL-001-ELG-R05', '04_ELE', ('ELE-BT',)),
    'EL2': (P + 'EL-002-ELG-R02', '04_ELE', ('ELE-IL',)),
    'INC': (P + 'INC-001-ING-R03', '05_PCI', ('HID', 'SDAI')),
}
f2 = lambda v: f'{v:.2f}'.replace('.', ',')


def t_local(tag):
    J = json.load(open(os.path.join(GEO, f'transformacao_{tag}_local_para_UTM.json'), encoding='utf-8'))
    assert abs(J['rigid']['rot_deg']) < 1e-9
    return np.array(J['rigid']['t'])


def lisp_str(s):
    out = []
    for ch in s:
        if ch == '\\': out.append('\\\\')
        elif ch == '"': out.append('\\"')
        elif ord(ch) < 128: out.append(ch)
        else: out.append('\\\\U+%04X' % ord(ch))
    return '"' + ''.join(out) + '"'


def mtext_str(s):
    """texto para MTEXT: \\P quebra de linha; não ASCII como \\U+XXXX."""
    return ''.join('\\P' if ch == '\n' else ch for ch in s)


def dist_poli(Q, P):
    """distância de cada ponto Q (n,2) à polilinha P (m,2)."""
    best = np.full(len(Q), np.inf)
    for a, b in zip(P[:-1], P[1:]):
        v = b - a; L2 = max(float(v @ v), 1e-12)
        t = np.clip(((Q - a) @ v) / L2, 0, 1); q = a + t[:, None] * v
        best = np.minimum(best, np.hypot(*(Q - q).T))
    return best


def amostra(P, passo=0.10):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / passo)))
        out += [a + (b - a) * j / k for j in range(1, k + 1)]
    return np.array(out)


def nuvem(x0, y0, x1, y1, arco=1.2):
    """retângulo como nuvem de revisão: vértices (x, y, bulge), sentido anti-horário, arcos para fora."""
    cantos = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    V = []
    for (ax, ay), (bx, by) in zip(cantos[:-1], cantos[1:]):
        L = np.hypot(bx - ax, by - ay); k = max(1, int(round(L / arco)))
        for j in range(k): V.append((ax + (bx - ax) * j / k, ay + (by - ay) * j / k, -0.45))
    return V


def fundir(caixas, folga=0.5):
    caixas = [list(c) for c in caixas]
    mudou = True
    while mudou:
        mudou = False
        for i in range(len(caixas)):
            for j in range(i + 1, len(caixas)):
                a, b = caixas[i], caixas[j]
                if a[0] - folga <= b[2] and b[0] - folga <= a[2] and a[1] - folga <= b[3] and b[1] - folga <= a[3]:
                    caixas[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    del caixas[j]; mudou = True; break
            if mudou: break
    return caixas


def ler_csv(fn):
    if not os.path.exists(fn): return []
    return list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'))


def preparar(cen):
    J = json.load(open(os.path.join(PRE, 'CAT.json'), encoding='utf-8'))
    sol = ler_csv(os.path.join(PRE, f'CAT_preclash_{cen}_solucoes.csv'))
    dv = ler_csv(os.path.join(PRE, f'CAT_preclash_{cen}_desvios.csv'))
    aj = ler_csv(os.path.join(PRE, f'CAT_preclash_{cen[0]}_ajustes_manuais.csv')) if cen.endswith('D') and len(cen) == 2 else []
    notas_dv = collections.defaultdict(list)
    for r in dv + aj:
        if not r.get('nota_para_planta'): continue
        chaves = {r.get('trecho_ou_caixa') or r.get('item')} | set((r.get('item') or '').split('/')) | {x.strip() for x in (r.get('trechos_que_acompanham') or '').split(',')}
        for k in chaves - {''}: notas_dv[k].append(r['nota_para_planta'])
    trab = {}
    for tag, (nome, sub, redes) in PRANCHAS.items():
        t = t_local(tag); L = lambda P: np.asarray(P)[:, :2] + ORIGEM - t      # local do preclash (origem) -> local do DWG
        mud, cxs = [], []
        for e in J['elementos']:
            if e['rede'] not in redes or str(e['id']).startswith('EQ:'): continue
            if not (e.get('dv') and cen in e['dv'] and e.get('sol') and cen in e['sol']): continue
            A = L(e['p']); B = L(e['sol'][cen])
            if len(A) == len(B) and np.allclose(A, B, atol=0.02): continue
            mud.append({'id': e['id'], 'trecho': e['trecho'], 'disc': e['disc'], 'antigo': A, 'novo': B})
        eq_rede = {'AF': ('AF',), 'EL1': ('ELE-BT',), 'EL2': ('ELE-IL',), 'INC': ('HID', 'SDAI')}[tag]
        for c in J['caixas']:
            if not (c.get('mv') and cen in c['mv']): continue
            partes = str(c['id']).split(':')
            if partes[0] == 'EQ':          # equipamento deslocado pela ferramenta (registro, hidrante, abrigo, base de poste)
                d = {'AF': 'AF', 'HID': 'HID', 'SDAI': 'SDAI'}.get(partes[1]) or ('ELE-IL' if 'EL2-' in partes[2] else 'ELE-BT')
                if d not in eq_rede: continue
                n = partes[2]; nm = ('abrigo ' + n[4:]) if n.startswith('ABR-') else ('base ' + n[5:]) if n.startswith('BASE-') else n
            elif partes[0] in redes: nm = c['id'].split(':', 1)[1]
            else: continue
            a = np.array([c['x'], c['y']]) + ORIGEM - t; b = np.array(c['mv'][cen]) + ORIGEM - t
            if np.hypot(*(b - a)) > 0.02: cxs.append({'id': c['id'], 'nome': nm, 'antigo': a, 'novo': b, 'meia': c['m'] or 0.3})
        mg = [r for r in sol if any(r['trecho'].startswith(p) for p in {'AF': ('AF-',), 'EL1': ('EL1-',), 'EL2': ('EL2-',), 'INC': ('HID-', 'SDAI-')}[tag])]
        trab[tag] = dict(nome=nome, sub=sub, t=t, mud=mud, cxs=cxs, mg=mg, notas_dv=notas_dv)
    return trab


def casar_entidades(nome, mud):
    """handles das entidades do desenho (nível superior, LINE/PL) que coincidem com os trechos alterados."""
    D = ler(os.path.join(DXF, nome + '.dxf'))
    ents = collections.defaultdict(list)
    for d in D:
        if d['path'] == '' and d['tipo'] in ('LINE', 'PL') and len(d['pts']) >= 2: ents[d['raiz']].append(d)
    hs_tot, sobras = set(), []
    for m in mud:
        A, B = m['antigo'], m['novo']
        Qa = amostra(A); muda = dist_poli(Qa, B) > 0.05          # pedaço do traçado antigo que deixou de existir
        if not muda.any(): continue
        Qm = Qa[muda]
        lo, hi = Qm.min(0) - 1.0, Qm.max(0) + 1.0
        cob = np.zeros(len(Qm), bool)
        for h, prims in ents.items():
            pts = np.vstack([p['pts'][:, :2] for p in prims])
            if pts[:, 0].max() < lo[0] or pts[:, 0].min() > hi[0] or pts[:, 1].max() < lo[1] or pts[:, 1].min() > hi[1]: continue
            Qe = np.vstack([amostra(p['pts'][:, :2]) for p in prims])
            if len(Qe) < 5: continue
            no_ant = dist_poli(Qe, A) < 0.12
            if no_ant.mean() < 0.9: continue                      # entidade não é deste trecho
            no_mud = dist_poli(Qe, Qm) < 0.12
            if no_mud.mean() >= 0.8:
                hs_tot.add(h); cob |= dist_poli(Qm, Qe) < 0.12
        if (~cob).any(): sobras.append(Qm[~cob])
    return D, sorted(hs_tot), sobras


def blocos_caixa(D, cxs):
    """bloco da caixa no desenho: inserção de nível superior cujo desenho (centro das primitivas) cai na caixa."""
    ins = {d['raiz']: d for d in D if d['path'] == '' and d['tipo'] == 'INSERT'}
    pts = collections.defaultdict(list)
    for d in D:
        if d['path'] != '' and d['raiz'] in ins and d['tipo'] in ('LINE', 'PL', 'CIRCLE', 'ARC'): pts[d['raiz']].append(d['pts'][:, :2])
    centro = {h: np.vstack(P).mean(0) for h, P in pts.items()}
    out = []
    for c in cxs:
        cand = sorted((float(np.hypot(*(q - c['antigo']))), h) for h, q in centro.items())
        cand = [(dd, h) for dd, h in cand if dd < max(0.35, c['meia'] + 0.15)]
        out.append((c, cand[0][1] if cand else None))
    return out


def gerar(tag, w):
    nome = w['nome']; os.makedirs(WRK, exist_ok=True); os.makedirs(SAI, exist_ok=True)
    D, hs, sobras = casar_entidades(nome, w['mud'])
    bc = blocos_caixa(D, w['cxs'])
    txt = [d for d in D if d['path'] == '' and d['tipo'] == 'TEXT' and d.get('h', 0) > 0.05]
    h = float(np.clip(np.median([d['h'] for d in txt]) if txt else 0.5, 0.25, 1.0))
    L = ['(defun r01-lay (n c lt lw) (if (not (tblsearch "LAYER" n)) (entmake (list \'(0 . "LAYER") \'(100 . "AcDbSymbolTableRecord") \'(100 . "AcDbLayerTableRecord") (cons 2 n) \'(70 . 0) (cons 62 c) (cons 6 lt) (cons 370 lw)))))',
         '(defun r01-pl (lay pts fech / l) (setq l (list \'(0 . "LWPOLYLINE") \'(100 . "AcDbEntity") (cons 8 lay) \'(100 . "AcDbPolyline") (cons 90 (length pts)) (cons 70 (if fech 1 0))))'
         ' (foreach p pts (setq l (append l (list (cons 10 (list (car p) (cadr p)))) (if (caddr p) (list (cons 42 (caddr p))) nil)))) (entmake l))',
         '(defun r01-tx (lay x y h s) (entmake (list \'(0 . "TEXT") (cons 8 lay) (cons 10 (list x y 0.0)) (cons 40 h) (cons 1 s) \'(50 . 0.0))))',
         '(defun r01-mt (lay x y h w partes / l) (setq l (list \'(0 . "MTEXT") \'(100 . "AcDbEntity") (cons 8 lay) \'(100 . "AcDbMText") (cons 10 (list x y 0.0)) (cons 40 h) (cons 41 w) \'(71 . 1)))'
         ' (foreach p (cdr (reverse partes)) (setq l (append l (list (cons 3 p))))) (entmake (append l (list (cons 1 (car (reverse partes)))))))',
         '(defun r01-ci (lay x y r) (entmake (list \'(0 . "CIRCLE") (cons 8 lay) (cons 10 (list x y 0.0)) (cons 40 r))))',
         '(defun r01-set (e lay / ed) (setq ed (entget e)) (setq ed (subst (cons 8 lay) (assoc 8 ed) ed))'
         ' (if (assoc 6 ed) (setq ed (subst (cons 6 "BYLAYER") (assoc 6 ed) ed))) (if (assoc 62 ed) (setq ed (subst (cons 62 256) (assoc 62 ed) ed))) (entmod ed) (entupd e))',
         '(setq r01-n 0 r01-falta 0)',
         '(defun r01-rem (h / e) (if (setq e (handent h)) (progn (r01-set e "COMPAT-R01-REMOVIDO") (setq r01-n (1+ r01-n))) (setq r01-falta (1+ r01-falta))))',
         '(defun r01-cop (h dx dy / e n) (if (setq e (handent h)) (progn (command "_.COPY" e "" (list 0.0 0.0 0.0) (list dx dy 0.0)) (setq n (entlast)) (r01-set n "COMPAT-R01-NOVO") (r01-rem h)) (setq r01-falta (1+ r01-falta))))',
         '(defun c:compatr01 ( / )',
         ' (setvar "CMDECHO" 0) (setvar "OSMODE" 0) (setvar "TILEMODE" 1) (setvar "CTAB" "Model")',
         ' (command "_.-LAYER" "_U" "*" "")',
         ' (if (not (tblsearch "LTYPE" "COMPAT_TRACO")) (entmake \'((0 . "LTYPE") (100 . "AcDbSymbolTableRecord") (100 . "AcDbLinetypeTableRecord") (2 . "COMPAT_TRACO") (70 . 0) (3 . "__ __ __") (72 . 65) (73 . 2) (40 . 1.5) (49 . 1.0) (74 . 0) (49 . -0.5) (74 . 0))))',
         ' (r01-lay "COMPAT-R01-REMOVIDO" 8 "COMPAT_TRACO" 35) (r01-lay "COMPAT-R01-NOVO" 1 "Continuous" 50) (r01-lay "COMPAT-R01-NUVEM" 1 "Continuous" 25)',
         ' (r01-lay "COMPAT-R01-NOTAS" 1 "Continuous" 18) (r01-lay "COMPAT-R01-MERGULHO" 4 "Continuous" 25)']
    for hh in hs: L.append(f' (r01-rem "{hh}")')
    for Q in sobras:                                             # pedaço antigo sem entidade só dele: redesenha tracejado
        for seg in np.split(Q, np.where(np.hypot(*np.diff(Q, axis=0).T) > 0.5)[0] + 1):
            if len(seg) >= 2: L.append(' (r01-pl "COMPAT-R01-REMOVIDO" (list ' + ' '.join(f'(list {p[0]:.4f} {p[1]:.4f})' for p in seg[::5].tolist() + [seg[-1].tolist()]) + ') nil)')
    for m in w['mud']:
        L.append(' (r01-pl "COMPAT-R01-NOVO" (list ' + ' '.join(f'(list {p[0]:.4f} {p[1]:.4f})' for p in m['novo']) + ') nil)')
    for c, hh in bc:
        dx, dy = c['novo'] - c['antigo']
        if hh: L.append(f' (r01-cop "{hh}" {dx:.4f} {dy:.4f})')
        else:
            s = c['meia']; x, y = c['novo']
            L.append(f' (r01-pl "COMPAT-R01-NOVO" (list (list {x - s:.4f} {y - s:.4f}) (list {x + s:.4f} {y - s:.4f}) (list {x + s:.4f} {y + s:.4f}) (list {x - s:.4f} {y + s:.4f})) T)')
    # nuvens: por alteração (trecho ou caixa), fundidas quando encostam
    caixas = []
    for m in w['mud']:
        Qa = amostra(m['antigo']); Qn = amostra(m['novo'])
        Q = np.vstack([Qa[dist_poli(Qa, m['novo']) > 0.05], Qn[dist_poli(Qn, m['antigo']) > 0.05]])
        if len(Q): caixas.append([*(Q.min(0) - 1.0), *(Q.max(0) + 1.0), [('trecho', m['trecho'])]])
    for c, _ in bc:
        Q = np.array([c['antigo'], c['novo']]); caixas.append([*(Q.min(0) - c['meia'] - 0.8), *(Q.max(0) + c['meia'] + 0.8), [('caixa', c['nome'])]])
    nuv = fundir(caixas)
    linhas = []
    for k, (x0, y0, x1, y1, itens) in enumerate(sorted(nuv, key=lambda c: (-c[3], c[0])), 1):
        rot = f'R{k:02d}'
        L.append(' (r01-pl "COMPAT-R01-NUVEM" (list ' + ' '.join(f'(list {x:.4f} {y:.4f} {b})' for x, y, b in nuvem(x0, y0, x1, y1)) + ') T)')
        L.append(f' (r01-tx "COMPAT-R01-NUVEM" {x1 + 0.2:.4f} {y1 + 0.2:.4f} {1.6 * h:.3f} {lisp_str(rot)})')
        vistos = set()
        for tipo, it in itens:
            if (tipo, it) in vistos: continue
            vistos.add((tipo, it))
            ns = w['notas_dv'].get(it) or [f"Traçado de {it} refeito (ver o 3D da compatibilização)."]
            for n in dict.fromkeys(ns): linhas.append((rot, n))
    # mergulhos: um marcador por trecho/trecho de solução
    mg = collections.OrderedDict()
    for r in sorted(w['mg'], key=lambda r: (r['trecho'], float(r['dist_inicio_trecho_m'].replace(',', '.')))):
        mg.setdefault(r['trecho'], []).append(r)
    k = 0
    for trecho, rs in mg.items():
        for r in rs:
            k += 1; rot = f'M{k:02d}'
            x, y = np.array([float(r['E'].replace(',', '.')), float(r['N'].replace(',', '.'))]) - w['t']
            L.append(f' (r01-ci "COMPAT-R01-MERGULHO" {x:.4f} {y:.4f} {0.6 * h:.3f})')
            L.append(f' (r01-tx "COMPAT-R01-MERGULHO" {x + 0.8 * h:.4f} {y + 0.4 * h:.4f} {h:.3f} {lisp_str(rot)})')
            linhas.append((rot, r['nota_para_planta']))
    # quadro de notas à direita da rede
    redes = np.vstack([m['antigo'] for m in w['mud']] + [c['antigo'][None] for c, _ in bc] +
                      [np.array([[float(r['E'].replace(',', '.')), float(r['N'].replace(',', '.'))]]) - w['t'] for r in w['mg']]) if (w['mud'] or bc or w['mg']) else np.zeros((1, 2))
    tx = [d['pts'][0, :2] for d in txt]
    # fora de tudo o que está desenhado no modelo (a folha é montada no modelo: tabelas e notas gerais ficam ao lado da planta);
    # assim o quadro fica no DWG mas não sai na folha — na folha vai a legenda do papel e o PDF de notas
    xs = np.concatenate([d['pts'][:, 0] for d in D if d['path'] == '' and len(d['pts'])])
    X0 = float(np.max(xs)) + 30.0; Y0 = redes[:, 1].max() + 5 * h
    cab = (f"COMPATIBILIZAÇÃO R01 ({DATA}) — PROPOSTA PARA VALIDAÇÃO\n"
           f"Base: {nome}. Pré-compatibilização 3D (IFC federado) da ETIB Catu.\n"
           "Tracejado cinza (COMPAT-R01-REMOVIDO): traçado/caixa que sai. Vermelho (COMPAT-R01-NOVO): traçado/caixa nova.\n"
           "Rnn: alteração em planta (nuvem). Mnn: só profundidade (mergulho com conexões verticais), planta inalterada.\n")
    corpo = '\n'.join(f'{r} — {n}' for r, n in linhas) if linhas else 'Sem alteração.'
    s = mtext_str(cab + '\n' + corpo)
    partes = [s[i:i + 240] for i in range(0, len(s), 240)]
    L.append(f' (r01-mt "COMPAT-R01-NOTAS" {X0:.3f} {Y0:.3f} {h:.3f} {60 * h:.3f} (list ' + ' '.join(lisp_str(p) for p in partes) + '))')
    L.append(' (princ (strcat "\\nCOMPAT_R01 removidos " (itoa r01-n) " sem_handle " (itoa r01-falta)))')
    L.append(' (princ))')
    fl = os.path.join(WRK, f'exec_{tag}.lsp')
    open(fl, 'w', encoding='ascii').write('\n'.join(L) + '\n')
    with open(os.path.join(SAI, f'{nome}_COMPAT-R01_notas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.writer(f, delimiter=';'); wr.writerow(['marca', 'nota']); wr.writerows(linhas)
    resumo = dict(tag=tag, nome=nome, trechos=len(w['mud']), caixas=len(bc), caixas_sem_bloco=sum(1 for _, hh in bc if not hh), entidades_tracejadas=len(hs),
                  pedacos_redesenhados=len(sobras), nuvens=len(nuv), mergulhos=k, altura_texto=h)
    return fl, resumo


def rodar(tag, w, fl):
    src = os.path.join(ORIG, w['sub'], w['nome'] + '.dwg')
    dst = os.path.join(SAI, w['nome'] + '_COMPAT-R01.dwg')
    shutil.copy2(src, dst)                                       # cópia: o original não é tocado
    scr = os.path.join(WRK, f'exec_{tag}.scr')
    open(scr, 'w', encoding='ascii', newline='\r\n').write('SECURELOAD\n0\nFILEDIA\n0\n_.AUDIT\n_Y\n(load "' + fl.replace('\\', '/') + '")\nCOMPATR01\n_.QSAVE\n_.QUIT\n')
    # AUDIT antes: o INC-001 salvava sem conseguir reabrir (ErrorStatus 53), como no _GEO de 18/10
    log = os.path.join(WRK, f'exec_{tag}_log.txt')
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(AQUI, 'run_acc.ps1'), '-Dwg', dst, '-Scr', scr, '-Log', log,
                        '-TimeoutSec', '600'], capture_output=True, text=True)
    b = open(log, 'rb').read() if os.path.exists(log) else b''
    out = b.decode('utf-16-le', errors='replace') if b[1:2] == b'\x00' else b.decode('utf-8', errors='replace')
    linha = [l for l in out.replace('\x00', '').splitlines() if 'COMPAT_R01' in l]
    bak = dst[:-4] + '.bak'
    if os.path.exists(bak): shutil.move(bak, os.path.join(WRK, os.path.basename(bak)))      # .bak do QSAVE sai da pasta de entrega
    return r.stdout.strip(), (linha[-1].strip() if linha else 'sem marcador no log'), dst


def main():
    cen = next((a for a in sys.argv[1:] if not a.startswith('--')), 'BD')
    so_gerar = '--so-gerar' in sys.argv
    trab = preparar(cen); res = []
    for tag, w in trab.items():
        if not (w['mud'] or w['cxs'] or w['mg']): print(tag, 'sem alteração'); continue
        fl, rs = gerar(tag, w); print(rs, flush=True)
        if not so_gerar:
            st, marca, dst = rodar(tag, w, fl); print('  ', st, '|', marca, flush=True); rs.update(console=st, marca=marca, dwg=dst)
        res.append(rs)
    json.dump(res, open(os.path.join(WRK, f'exec_resumo_{cen}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
