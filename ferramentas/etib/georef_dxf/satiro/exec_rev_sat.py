# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — revisão dos executivos (fase 7 da skill modelagem-ifc-sem-revit), 19/10/2026.
Para cada DWG de disciplina com solução no cenário de entrega (AD): copia o ORIGINAL (PROJETO_ORIGINAL, só leitura) para
RELATORIOS/EXECUTIVOS_REVISADOS_2026-10-19/<nome>_REV-COMP01.dwg e desenha nele, em coordenadas locais do desenho
(inversa da transformação do georreferenciamento):
  - layer REV-COMP01-NOVO (vermelho): traçado novo dos desvios em planta e caixa na posição nova;
  - layer REV-COMP01-CANCELADO (cinza, tracejado, com X): trecho/caixa que deixa de existir, desenhado por cima do original
    (o BREAK no original deixava o accoreconsole preso num prompt; o original fica e o projetista apaga na limpeza final);
  - layer REV-COMP01-NUVEM (magenta): nuvem de revisão em cada item;
  - layer REV-COMP01-NOTA: número do item, nota com a solução (mergulho: cota do eixo e Δz; desvio: deslocamento) e chamada;
  - quadro "REVISÃO COMP-01" com a legenda e a lista dos itens.
Mergulhos não mudam a planta: entram como nota + nuvem (o perfil é o do IFC compatibilizado).
Também no ESG-001: CF corrigidas (PVE-01, CI-03) e a drenagem do campo que sai do desenho de esgoto (vale o CPS DRE-001).
Um accoreconsole por vez (run_one.ps1). Uso: .venv/Scripts/python.exe -X utf8 exec_rev_sat.py [--so-lisp]"""
import os, sys, json, csv, math, shutil, subprocess, collections, re
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sat_comum as sc   # noqa: E402

BASE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS'
ORIG = os.path.join(BASE, 'PROJETO_ORIGINAL')
PRE = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
OUT = os.path.join(BASE, 'RELATORIOS', 'EXECUTIVOS_REVISADOS_2026-10-19')
TRANSF = os.path.join(BASE, 'CAD_GEORREFERENCIADO', 'transformacoes_local_para_UTM.json')
RUN = os.path.join(os.path.dirname(AQUI), 'run_one.ps1')
CEN = 'AD'
REV = 'REV-COMP01'
DATA = '19/10/2026'
H = 0.50          # altura do texto das notas (m no desenho): 2,5 mm na escala 1:200 das pranchas

# desenho de origem de cada solução: (tag do sat_comum, trecho/caixa casa com o padrão, disciplinas)
DESENHOS = {
    'EL-001': dict(tag='EL1', arq='IMP-PE-EL-001-ELG-R01', disc=('ELE',), pad=r'^(IE-)', letra='E1'),
    'EL-002': dict(tag='EL2', arq='IMP-PE-EL-002-ELG-R01', disc=('ELE',), pad=r'^(AL-)', letra='E2'),
    'CPS-ELE-001': dict(tag='CPS_EL1', arq='CPS-PE-ELE-001-ELG-R00', disc=('ELE',), pad=r'^(CP1-)', letra='EC'),
    'IN-001': dict(tag='IN', arq='IMP-PE-IN-001-ING-R03', disc=('HID', 'SDAI'), pad=r'.', letra='P'),
    'AF-001': dict(tag='AF', arq='IMP-PE-AF-001-HIG-R00', disc=('AF',), pad=r'.', letra='A'),
    'ESG-001': dict(tag='ESG', arq='IMP-PE-ESG-001-HIG-R00', disc=(), pad=r'$^', letra='S'),
}
CAMADAS_REDE = ('ELETRODUTO', 'CONDUTOS', 'DETECÇÃO', 'DETECCAO')


def acha_original(chave):
    alvo = DESENHOS[chave]['arq']
    for raiz, _, fs in os.walk(ORIG):
        for f in fs:
            if f.lower().endswith('.dwg') and alvo in f and '_GEO' not in f: return os.path.join(raiz, f)
    raise FileNotFoundError(alvo)


def transf(chave):
    J = json.load(open(TRANSF, encoding='utf-8'))['arquivos']
    alvo = DESENHOS[chave]['arq']
    for k, v in J.items():
        if alvo in k: return float(v['rot_deg']), np.array(v['t'], float)
    raise KeyError(alvo)


def para_local(P, rot, t):
    a = -math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.atleast_2d(np.asarray(P, float))[:, :2] - t) @ R.T


def ponto_s(P, s):
    P = np.asarray(P)[:, :2]; L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = min(max(s, 0), L[-1]); i = min(max(0, np.searchsorted(L, s) - 1), len(P) - 2)
    u = (s - L[i]) / max(L[i + 1] - L[i], 1e-9); return P[i] + (P[i + 1] - P[i]) * u


def trecho_entre(P, s0, s1, passo=0.25):
    P = np.asarray(P)[:, :2]; L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    out = [ponto_s(P, s0)] + [P[i] for i in range(len(P)) if s0 < L[i] < s1] + [ponto_s(P, s1)]
    return np.array(out)


def parte_desviada(orig, novo, tol=0.02):
    """pedaço do traçado novo que se afasta do original (> tol) e o pedaço correspondente do original."""
    o = np.asarray(orig)[:, :2]; n = np.asarray(novo)[:, :2]
    Ln = np.r_[0, np.cumsum(np.hypot(*np.diff(n, axis=0).T))]
    ss = np.arange(0, Ln[-1], 0.1); Q = np.array([ponto_s(n, s) for s in ss])
    d = np.array([dist_pl(q, o)[0] for q in Q]); fora = np.where(d > tol)[0]
    if len(fora) == 0: return None
    a, b = ss[max(0, fora[0] - 1)], ss[min(len(ss) - 1, fora[-1] + 1)]
    pa, pb = ponto_s(n, a), ponto_s(n, b)
    sa, sb = sorted([dist_pl(pa, o)[1], dist_pl(pb, o)[1]])
    return trecho_entre(n, a, b), trecho_entre(o, sa, sb)


def dist_pl(p, P):
    """distância do ponto à polilinha e a abscissa do pé."""
    P = np.asarray(P)[:, :2]; best = (1e9, 0.0); acc = 0.0
    for a, b in zip(P[:-1], P[1:]):
        ab = b - a; L = np.hypot(*ab)
        t = 0 if L < 1e-9 else max(0, min(1, np.dot(p - a, ab) / L ** 2)); q = a + ab * t; d = np.hypot(*(p - q))
        if d < best[0]: best = (d, acc + t * L)
        acc += L
    return best


# ---------------------------------------------------------------- LISP
def lsp_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def quebra(txt, n=48):
    out, lin = [], ''
    for w in txt.split():
        if len(lin) + len(w) + 1 > n and lin: out.append(lin); lin = w
        else: lin = (lin + ' ' + w).strip()
    if lin: out.append(lin)
    return '\\P'.join(out)


class Lisp:
    def __init__(self):
        self.L = []; self.Q = []; self.P = None; self.notas = []

    def colocar_notas(self, lay=f'{REV}-NOTA', larg=18.0):
        """põe cada nota (código + texto, Arial) ao lado da sua nuvem, voltada para o miolo do desenho e sem sobrepor outra nota."""
        if not self.notas: return
        meio = np.mean([n[2] for n in self.notas], axis=0)
        ocup = []
        dirs = [np.array(v, float) / np.hypot(*v) for v in ((1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1))]
        for cod, txt, c, raio in self.notas:
            corpo = quebra(txt)
            h = (corpo.count('\\P') + 2 + len(txt) // 70) * H * 1.7; w = larg
            alvo = meio - c; alvo = alvo / (np.hypot(*alvo) or 1)
            ordem = sorted(dirs, key=lambda d: -np.dot(d, alvo))
            esc = None
            for k in range(14):
                for d in ordem:
                    p = c + d * (raio + 1.0 + 2.5 * k)
                    x0 = p[0] if d[0] >= 0 else p[0] - w; y0 = p[1] if d[1] >= 0 else p[1] - h
                    R = (x0 - 0.5, y0 - 0.5, x0 + w + 0.5, y0 + h + 0.5)
                    if all(R[2] < o[0] or R[0] > o[2] or R[3] < o[1] or R[1] > o[3] for o in ocup):
                        esc = (d, p, x0, y0); break
                if esc: break
            if esc is None:
                d = ordem[0]; p = c + d * (raio + 1.0); esc = (d, p, p[0], p[1])
            d, p, x0, y0 = esc
            ocup.append((x0, y0, x0 + w, y0 + h))
            canto = np.array([x0 if d[0] >= 0 else x0 + w, y0 if d[1] >= 0 else y0 + h])
            self.pl(lay, [c + d * raio * 0.95, canto])
            self.txt(lay, (x0, y0 + h), f'{{\\fArial|b1|i0|c0|p34;{cod}}}\\P{{\\fArial|b0|i0|c0|p34;{corpo}}}', w=w, anexo=1)

    def pt(self, p): return f'(list {p[0]:.4f} {p[1]:.4f} 0.0)'

    def pl(self, lay, P, fechada=False, larg=0.0, bulge=None, lt=None):
        P = np.asarray(P)[:, :2]
        if len(P) < 2: return
        v = []
        for i, p in enumerate(P):
            v.append(f'(cons 10 (list {p[0]:.4f} {p[1]:.4f}))')
            if bulge is not None: v.append(f'(cons 42 {bulge:.4f})')
        extra = f" (cons 6 {lsp_str(lt)})" if lt else ''
        self.L.append(f"(entmake (append (list '(0 . \"LWPOLYLINE\") '(100 . \"AcDbEntity\") (cons 8 {lsp_str(lay)}){extra} '(100 . \"AcDbPolyline\") "
                      f"(cons 90 {len(P)}) (cons 70 {1 if fechada else 0}) (cons 43 {larg:.3f})) (list {' '.join(v)})))")

    def txt(self, lay, p, s, h=H, w=0.0, anexo=1):
        # texto em blocos de até 240 caracteres (grupos 3 + o último no 1): entmake de MTEXT com grupo 1 > 250 falha sem erro
        self.L.append(f"(entmake (append (list '(0 . \"MTEXT\") '(100 . \"AcDbEntity\") (cons 8 {lsp_str(lay)}) '(100 . \"AcDbMText\") "
                      f"(cons 10 {self.pt(p)}) (cons 40 {h:.3f}) (cons 41 {w:.3f}) (cons 71 {anexo})) (rv:grupos {lsp_str(s)}) (list (cons 7 \"Standard\"))))")

    def nuvem(self, lay, c, r):
        r = max(r, 0.8); n = max(8, int(2 * math.pi * r / 0.6))
        P = [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.pl(lay, P, fechada=True, larg=0.04, bulge=-0.5)

    def xis(self, lay, P, passo=1.5, tam=0.25):
        P = np.asarray(P)[:, :2]; L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        for s in np.arange(passo / 2, L[-1], passo):
            q = ponto_s(P, s)
            self.pl(lay, [(q[0] - tam, q[1] - tam), (q[0] + tam, q[1] + tam)]); self.pl(lay, [(q[0] - tam, q[1] + tam), (q[0] + tam, q[1] - tam)])

    def quebrar(self, handle, p1, p2):
        """cada BREAK vai num arquivo próprio (carregado por uma linha do script): se um falhar, os outros e o PDF seguem."""
        self.Q.append(f'(setvar "TILEMODE" 1) (if (and (setq rv:e (handent "{handle}")) (= (cdr (assoc 410 (entget rv:e))) "Model")) '
                      f'(progn (command "_.BREAK" rv:e "_F" {self.pt(p1)} {self.pt(p2)}) (princ "\\nREV quebra ok {handle}")))\n(princ)\n')

    def plotar_pdf(self, base_pdf, a0=False):
        """plota todas as folhas (layouts) em PDF: <base_pdf>_<layout>.pdf (DWG To PDF.pc3). Padrão: configuração da própria
        folha. a0=True: folha com configuração ANSI A (IN-001) -> ISO full bleed A0, extensão, ajustar, centrado."""
        b = base_pdf.replace(os.sep, '/')
        if a0:
            cmd = ('(command "_.-PLOT" "_Y" (cdr x) "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_E" "_F" "_C" '
                   f'"_Y" "." "_Y" "_N" "_N" "_N" (strcat {lsp_str(b)} "_" (cdr x) ".pdf") "_N" "_Y")')
        else:
            cmd = f'(command "_.-PLOT" "_N" (cdr x) "" "DWG To PDF.pc3" (strcat {lsp_str(b)} "_" (cdr x) ".pdf") "_N" "_Y")'
        self.P = ('(setvar "BACKGROUNDPLOT" 0) (setvar "FILEDIA" 0) (setvar "TILEMODE" 1)\n'
                  '(foreach x (dictsearch (namedobjdict) "ACAD_LAYOUT") (if (and (= (car x) 3) (/= (strcase (cdr x)) "MODEL")) '
                  f'{cmd}))\n(setvar "TILEMODE" 1)\n(princ)\n')

    def quebrar_depois(self):
        pass

    def texto(self):
        cab = [
            ';; gerado por exec_rev_sat.py (ETIB Sátiro Dias, revisão de compatibilização)',
            '(setvar "CMDECHO" 0) (setq rv:nq 0) (setvar "TILEMODE" 1)   ; o DWG abre na folha: tudo vai para o espaço do modelo',
            "(if (not (tblsearch \"LTYPE\" \"REV_TRACO\")) (entmake '((0 . \"LTYPE\") (100 . \"AcDbSymbolTableRecord\") (100 . \"AcDbLinetypeTableRecord\") (2 . \"REV_TRACO\") (70 . 0) (3 . \"Tracejado revisao __ __\") (72 . 65) (73 . 2) (40 . 1.2) (49 . 0.8) (74 . 0) (49 . -0.4) (74 . 0))))",
        ]
        for nm, cor, lt in ((f'{REV}-NOVO', 1, 'Continuous'), (f'{REV}-CANCELADO', 8, 'REV_TRACO'), (f'{REV}-NUVEM', 6, 'Continuous'), (f'{REV}-NOTA', 5, 'Continuous')):
            cab.append(f"(if (not (tblsearch \"LAYER\" \"{nm}\")) (entmake (list '(0 . \"LAYER\") '(100 . \"AcDbSymbolTableRecord\") '(100 . \"AcDbLayerTableRecord\") (cons 2 \"{nm}\") '(70 . 0) (cons 62 {cor}) (cons 6 \"{lt}\"))))")
        cab.append('(setvar "CLAYER" "0")')
        cab.append('(defun rv:grupos (s / out n) (while (> (strlen s) 240) (setq n 240)'
                   ' (while (= (substr s n 1) "\\\\") (setq n (1- n)))'
                   ' (setq out (cons (cons 3 (substr s 1 n)) out) s (substr s (1+ n)))) (append (reverse out) (list (cons 1 s))))')
        return '\n'.join(cab + self.L + ['(princ "\\nREV entidades ok")', '(princ)']) + '\n'

    def arquivos(self, base):
        """grava <base>.lsp (entidades), <base>_q<n>.lsp (um BREAK cada) e <base>_pdf.lsp; devolve a lista na ordem de carga."""
        out = [base + '.lsp']
        open(out[0], 'w', encoding='cp1252', errors='replace').write(self.texto())
        for n, q in enumerate(self.Q, 1):
            fn = f'{base}_q{n}.lsp'; open(fn, 'w', encoding='cp1252', errors='replace').write(q); out.append(fn)
        if self.P:
            fn = base + '_pdf.lsp'; open(fn, 'w', encoding='cp1252', errors='replace').write(self.P); out.append(fn)
        return out


# ---------------------------------------------------------------- itens por desenho
def handles_rede(tag, P_utm, tol=0.10):
    """objetos soltos (fora de bloco) de rede que passam pelo meio do trecho antigo (coordenadas do _GEO = UTM)."""
    E = sc.carrega(tag)
    m = np.asarray(P_utm)[:, :2]; meio = ponto_s(m, np.hypot(*np.diff(m, axis=0).T).sum() / 2)
    cand = []
    for d in E:
        if d['tipo'] not in ('PL', 'LINE') or d['path'] or not any(k in d['layer'].upper() for k in CAMADAS_REDE): continue
        p = d['pts'][:, :2]
        if not (p[:, 0].min() - 1 < meio[0] < p[:, 0].max() + 1 and p[:, 1].min() - 1 < meio[1] < p[:, 1].max() + 1): continue
        dm = dist_pl(meio, p)[0]; d0 = dist_pl(m[0], p)[0]; d1 = dist_pl(m[-1], p)[0]
        if dm < tol and d0 < tol and d1 < tol: cand.append(d['raiz'])
    return sorted(set(cand))


def montar(chave, G, sol, desv):
    cfg = DESENHOS[chave]; rot, t = transf(chave)
    loc = lambda P: para_local(P, rot, t)
    pad = re.compile(cfg['pad'])
    L = Lisp(); itens = []
    nov, can, nuv, nota = f'{REV}-NOVO', f'{REV}-CANCELADO', f'{REV}-NUVEM', f'{REV}-NOTA'

    def item(txt, c_utm, raio):
        n = len(itens) + 1; cod = f"{cfg['letra']}-{n:02d}"
        c = loc([c_utm])[0]
        L.nuvem(nuv, c, raio)
        L.notas.append((cod, txt, c, raio))           # a nota é posicionada no fim, sem sobrepor as outras
        itens.append({'item': cod, 'descricao': txt, 'E': round(float(c_utm[0]), 3), 'N': round(float(c_utm[1]), 3)})
    # desvios em planta (contorno) e caixas deslocadas
    els = {e['id']: e for e in G['elementos']}
    for d in desv:
        if d.get('status') != 'aplicado': continue
        disc = d['disc']; nome = d['trecho']
        if disc not in cfg['disc'] or not pad.search(str(nome)): continue
        if d['tipo'] == 'contorno':
            e = els.get(d['elemento'])
            if not e: continue
            r = parte_desviada(e['pts_original'], e['pts'])
            if r is None: continue
            novo, velho = r
            L.pl(nov, loc(novo), larg=0.08)
            L.pl(can, loc(velho), larg=0.03, lt='REV_TRACO'); L.xis(can, loc(velho))
            # o BREAK do trecho antigo no original deixava o console preso num prompt: o original fica, marcado como cancelado
            c = np.vstack([novo, velho]).mean(0); raio = max(np.hypot(*(np.vstack([novo, velho]) - c).T).max() + 0.6, 1.0)
            item(f"DESVIO EM PLANTA — {d['txt'].split('; ', 1)[-1]} (traçado novo em vermelho; trecho cancelado tracejado com X)", c, raio)
        elif d['tipo'] == 'caixa deslocada' and abs(d.get('desloc') or 0) >= 0.10:     # menos de 10 cm não vai para a prancha
            cx = next((c for c in G['caixas_deslocadas'] if c['nome'] == nome or c['id'].endswith(':' + nome)), None)
            if not cx: continue
            a = cx['meia'] - 0.05; p0 = np.array([cx['E0'], cx['N0']]); p1 = np.array([cx['E'], cx['N']])
            sq = lambda c: [c + np.array(v) for v in ((-a, -a), (a, -a), (a, a), (-a, a))]
            L.pl(nov, loc(sq(p1)), fechada=True, larg=0.05)
            L.pl(can, loc(sq(p0)), fechada=True, lt='REV_TRACO'); L.xis(can, loc([p0 - [a, 0], p0 + [a, 0]]), passo=2 * a, tam=a * 0.7)
            L.pl(nov, loc([p0, p1]))
            item(f"CAIXA DESLOCADA — {d['txt'].split('; ', 1)[-1]}", (p0 + p1) / 2, a + 0.8)
    # mergulhos: agrupados por trecho (uma nota por trecho, nuvem em cada mergulho)
    por = collections.defaultdict(list)
    for s in sol:
        if s['disc'] in cfg['disc'] and pad.search(str(s['trecho'])): por[s['trecho']].append(s)
    for tr, ss in sorted(por.items()):
        ss.sort(key=lambda s: s['s0'])
        partes = [f"{'rebaixar' if s['dz'] < 0 else 'elevar'} {abs(s['dz']):.2f} m entre {s['s0']:.1f} e {s['s1']:.1f} m do início (eixo {s['eixo_depois']:.2f})".replace('.', ',')
                  for s in ss]
        mot = sorted({m for s in ss for m in re.findall(r'de (.*?);', s['txt'])})
        c = np.mean([[s['E'], s['N']] for s in ss], axis=0)
        raio = max(max(np.hypot(s['E'] - c[0], s['N'] - c[1]) + s['extensao'] / 2 for s in ss) + 0.5, 1.0)
        if raio > 12:                               # mergulhos espalhados: uma nuvem por mergulho, nota no primeiro
            for s in ss[1:]: L.nuvem(nuv, loc([[s['E'], s['N']]])[0], s['extensao'] / 2 + 0.5)
            c = np.array([ss[0]['E'], ss[0]['N']]); raio = ss[0]['extensao'] / 2 + 0.5
        item(f"MERGULHO (planta não muda) — {tr}: " + '; '.join(partes) + (f"; para passar sob/sobre {', '.join(mot)}" if mot else '') +
             '; conexões verticais nas pontas. Perfil no IFC compatibilizado.', c, raio)
    return L, itens


def extras_esg(L, itens, chave):
    cfg = DESENHOS[chave]; rot, t = transf(chave); loc = lambda P: para_local(P, rot, t)
    nuv, nota, can = f'{REV}-NUVEM', f'{REV}-NOTA', f'{REV}-CANCELADO'
    cx = {r['caixa']: r for r in csv.DictReader(open(os.path.join(sc.REL, 'SAT_fase2_ESG_caixas.csv'), encoding='utf-8-sig'), delimiter=';')}
    for nome, cf_d, cf_c in (('PVE-01', '235,99', '234,99'), ('CI-03', '235,86', '235,26')):
        r = cx.get(nome)
        if not r: continue
        c_utm = np.array([float(r['E']), float(r['N'])]); c = loc([c_utm])[0]
        L.nuvem(nuv, c, 1.2)
        cod = f"S-{len(itens) + 1:02d}"
        txt = f"CF CORRIGIDA — {nome}: CF = {cf_c} (o desenho trazia {cf_d}, incompatível com a profundidade do próprio rótulo e com a declividade do trecho)."
        L.notas.append((cod, txt, c, 1.2))
        itens.append({'item': cod, 'descricao': txt, 'E': round(float(c_utm[0]), 3), 'N': round(float(c_utm[1]), 3)})
    # drenagem do campo que saiu do desenho de esgoto
    R = list(csv.DictReader(open(os.path.join(sc.REL, 'SAT_fase2_AP_removidos_campo.csv'), encoding='utf-8-sig'), delimiter=';'))
    P = []
    for r in R:
        try: a = np.array([float(r['E_ini']), float(r['N_ini'])]); b = np.array([float(r['E_fim']), float(r['N_fim'])])
        except (KeyError, ValueError): continue
        L.pl(can, loc([a, b]), lt='REV_TRACO'); P += [a, b]
    if P:
        P = np.array(P); c = P.mean(0); raio = np.hypot(*(P - c).T).max() + 1.0
        L.nuvem(nuv, loc([c])[0], raio)
        cod = f"S-{len(itens) + 1:02d}"
        txt = ('DRENAGEM DO CAMPO RETIRADA DESTE DESENHO — a espinha de drenos sob o campo society (CA-11, CA-12 e 28 trechos) não pertence ao projeto de esgoto/pluvial; '
               'vale a drenagem do CPS-DRE-001 R01.')
        L.notas.append((cod, txt, loc([c])[0], raio))
        itens.append({'item': cod, 'descricao': txt, 'E': round(float(c[0]), 3), 'N': round(float(c[1]), 3)})


def quadro(L, itens, chave, cen_nome):
    """carimbo de revisão em cada folha: no espaço do papel, no canto de baixo à esquerda da maior viewport, com máscara."""
    if not itens: return
    cods = [i['item'] for i in itens]
    linhas = [f'{{\\fArial|b1;REVISÃO COMP-01 — COMPATIBILIZAÇÃO ({DATA})}}',
              f'Cenário {CEN}: {cen_nome}. Base: IFC compatibilizado da ETIB Sátiro Dias (pré-compatibilização 3D).',
              'Vermelho (REV-COMP01-NOVO) = traçado/caixa novos. Tracejado cinza com X (REV-COMP01-CANCELADO) = cancelado.',
              'Nuvem magenta = item revisado; nota azul ao lado. Mergulho = só cota (planta não muda), conexões verticais nas pontas.',
              f'Itens desta folha: {cods[0]} a {cods[-1]} ({len(cods)}). Lista completa: <nome do arquivo>_itens.csv.']
    txt = lsp_str('{\\fArial|b0|i0|c0|p34;' + '\\P'.join(linhas) + '}')
    L.L.append('(defun rv:carimbo (lay txt / ss i e d best)'
               ' (setq ss (ssget "X" (list (cons 0 "VIEWPORT") (cons 410 lay))) best nil i 0)'
               ' (if ss (repeat (sslength ss) (setq d (entget (ssname ss i)) i (1+ i))'
               ' (if (and (/= (cdr (assoc 69 d)) 1) (or (null best) (> (* (cdr (assoc 40 d)) (cdr (assoc 41 d))) (* (cdr (assoc 40 best)) (cdr (assoc 41 best)))))) (setq best d))))'
               ' (if best (entmake (append (list (cons 0 "MTEXT") (cons 100 "AcDbEntity") (cons 67 1) (cons 410 lay) (cons 8 "REV-COMP01-NOTA") (cons 100 "AcDbMText")'
               ' (list 10 (+ (- (cadr (assoc 10 best)) (/ (cdr (assoc 40 best)) 2.0)) 6.0) (+ (- (caddr (assoc 10 best)) (/ (cdr (assoc 41 best)) 2.0)) 6.0) 0.0)'
               ' (cons 40 2.5) (cons 41 (min 330.0 (* 0.6 (cdr (assoc 40 best))))) (cons 71 7)) (rv:grupos txt) (list (cons 7 "Standard"))))))')
    L.L.append(f'(setq rv:txt {txt})')
    L.L.append('(foreach x (dictsearch (namedobjdict) "ACAD_LAYOUT") (if (and (= (car x) 3) (/= (strcase (cdr x)) "MODEL")) (rv:carimbo (cdr x) rv:txt)))')


def linha_revisao(L, atual, nova, desc):
    """linha nova no quadro de revisões do carimbo da QG (mesmo modelo da Aporá Prof. Áurea): acha o '00' da emissão inicial
    em cada folha, sobe 5,115 mm a partir da última revisão escrita na coluna e escreve número, data, descrição e POPULUS;
    troca o código DISCIPL_SETOR-FOLHA_REV (…_R<atual> -> …_R<nova>)."""
    a, n = f'{atual:02d}', f'{nova:02d}'
    L.L.append('(defun rv:revlinha (nova data desc / ss i d lay p0 x0 y0 s2 j d2 q ymax y est ok)'
               ' (setq ss (ssget "X" (list (cons 0 "TEXT,MTEXT") (cons 67 1) (cons 1 "00"))) i 0)'
               ' (if ss (repeat (sslength ss) (setq d (entget (ssname ss i)) i (1+ i) lay (cdr (assoc 410 d)) p0 (cdr (assoc 10 d)) x0 (car p0) y0 (cadr p0) ok nil ymax y0)'
               '  (setq s2 (ssget "X" (list (cons 0 "TEXT,MTEXT") (cons 67 1) (cons 410 lay))) j 0)'
               '  (if s2 (repeat (sslength s2) (setq d2 (entget (ssname s2 j)) j (1+ j) q (cdr (assoc 10 d2)))'
               '   (if (and (wcmatch (strcase (cdr (assoc 1 d2))) "*EMISS*") (< (abs (- (cadr q) y0)) 1.5) (> (car q) x0) (< (car q) (+ x0 60.0))) (setq ok T))'
               '   (if (and (wcmatch (cdr (assoc 1 d2)) "##") (< (abs (- (car q) x0)) 0.3) (> (cadr q) ymax) (< (cadr q) (+ y0 40.0))) (setq ymax (cadr q)))))'
               '  (if ok (progn (setq y (+ ymax 5.115) est (if (tblsearch "STYLE" "ETIB") "ETIB" "Standard"))'
               '   (foreach it (list (list 0.0 0.0 nova 4.0) (list 10.239 0.718 data 15.0) (list 29.013 0.581 desc 125.0) (list 157.132 0.336 "POPULUS" 20.0))'
               '    (entmake (list (cons 0 "MTEXT") (cons 100 "AcDbEntity") (cons 67 1) (cons 410 lay) (cons 8 (cdr (assoc 8 d))) (cons 100 "AcDbMText")'
               '     (list 10 (+ x0 (car it)) (+ y (cadr it)) 0.0) (cons 40 1.842) (cons 41 (cadddr it)) (cons 71 1) (cons 1 (caddr it)) (cons 7 est))))'
               '   (princ (strcat "\\nREV linha " nova " em " lay)))))))')
    L.L.append(f'(rv:revlinha "{n}" "{DATA}" {lsp_str(desc)})')
    L.L.append(f'(setq rv:ss (ssget "X" (list (cons 0 "TEXT,MTEXT") (cons 67 1))) rv:i 0)'
               f' (if rv:ss (repeat (sslength rv:ss) (setq rv:d (entget (ssname rv:ss rv:i)) rv:i (1+ rv:i) rv:t (cdr (assoc 1 rv:d)))'
               f' (if (wcmatch rv:t "*_???-###_R{a}") (progn (entmod (subst (cons 1 (strcat (substr rv:t 1 (- (strlen rv:t) 2)) "{n}")) (assoc 1 rv:d) rv:d)) (princ (strcat "\\nREV código " rv:t))))))')


def rodar_console(dwg, lsp, log, formato=None):
    """um accoreconsole por vez (run_one.ps1). formato='2013': AUDIT e SAVEAS 2013 por cima (caso do IN-001)."""
    lin = ['SECURELOAD 0', 'FILEDIA 0', 'EXPERT 5']
    if formato: lin += ['_.AUDIT _Y']
    lin += [f'(load "{x.replace(os.sep, "/")}")' for x in (lsp if isinstance(lsp, list) else [lsp])]
    lin += [f'_.SAVEAS {formato} "{dwg}"'] if formato else ['_.QSAVE']
    arr = ', '.join("'" + x.replace("'", "''") + "'" for x in lin)
    cmd = f"& '{RUN}' -Dwg '{dwg}' -Log '{log}' -ScrLines @({arr}) -TimeoutSec 900"
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', cmd], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def main():
    so_lisp = '--so-lisp' in sys.argv
    os.makedirs(OUT, exist_ok=True)
    G = json.load(open(os.path.join(PRE, 'SAT_entrega_geometria.json'), encoding='utf-8'))[CEN]
    sol, desv = G['mergulhos'], G['desvios']
    resumo = []
    so = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--so=')]
    for chave in DESENHOS:
        if so and chave not in so[0].split(','): continue
        L, itens = montar(chave, G, sol, desv)
        if chave == 'ESG-001': extras_esg(L, itens, chave)
        L.colocar_notas()
        if not itens: print(chave, ': nada a revisar'); continue
        quadro(L, itens, chave, G['nome'])
        src = acha_original(chave)
        # revisão nova no nome (os campos do carimbo mostram o nome do arquivo) e linha nova no quadro de revisões
        m = re.search(r'-R(\d\d)$', os.path.splitext(os.path.basename(src))[0]); atual = int(m.group(1)); nova = atual + 1
        dst = os.path.join(OUT, os.path.splitext(os.path.basename(src))[0][:-2] + f'{nova:02d}.dwg')
        linha_revisao(L, atual, nova, f'COMPATIBILIZAÇÃO DAS REDES EXTERNAS (REVISÃO COMP-01: ITENS {itens[0]["item"]} A {itens[-1]["item"]})')
        lsp = os.path.join(OUT, '_lisp', os.path.splitext(os.path.basename(dst))[0] + '.lsp'); os.makedirs(os.path.dirname(lsp), exist_ok=True)
        L.quebrar_depois()
        L.plotar_pdf(os.path.join(OUT, 'PDF', os.path.splitext(os.path.basename(dst))[0]), a0=(chave == 'IN-001')); os.makedirs(os.path.join(OUT, 'PDF'), exist_ok=True)
        lsp = L.arquivos(os.path.splitext(lsp)[0])
        with open(os.path.splitext(dst)[0] + '_itens.csv', 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['item', 'descricao', 'E', 'N'], delimiter=';'); w.writeheader(); w.writerows(itens)
        resumo.append((chave, len(itens), os.path.basename(dst)))
        print(chave, len(itens), 'itens ->', os.path.basename(dst))
        if so_lisp: continue
        shutil.copy2(src, dst)
        print('  ', rodar_console(dst, lsp, os.path.join(OUT, '_lisp', os.path.splitext(os.path.basename(dst))[0] + '.log'),
                                  formato='2013' if chave == 'IN-001' else None))
    return resumo


if __name__ == '__main__':
    main()
