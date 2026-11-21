# -*- coding: utf-8 -*-
"""Itamira — EL-001 R01 com a alimentação nova do quadro do campo (ELE-06), decisão I1 do Anderson (24/10/2026, "Revise o EL-001",
fichas <link privado da página>). Padrão de executivo final (AGENTS.md > Pranchas), numa cópia do R00:
  - saem o ELE-04 e o ELE-05 (passavam sob o reservatório executado, até o quadro do campo desenhado onde ele não foi instalado) e
    a etiqueta do ELE-05;
  - entra a ELE-06 (CX-02 -> por dentro dos muros NE e SE do campo -> QD1 executado), polilinha no layer, cor e espessura do
    eletroduto da folha (02. F_ELETRODUTO PISO);
  - o símbolo da CX-01 (com o texto "Cx. 60x60 cm" e os WIPEOUT) vai para a CX-P1 e é copiado para a CX-P2 e a CX-P3 (mudanças
    de direção); a etiqueta do ELE-04 (QDLT-CAMPO, Ø 2", #4) acompanha o traçado novo;
  - o quadro do campo (bloco QUADRO ELE e o texto QDLT-CAMPO) vai para a posição do QD1 executado. O QD1 fica 2 m abaixo da
    janela da folha: na borda entra uma chamada no estilo da folha ("SEGUE PARA O QDLT-CAMPO"), como a da drenagem;
  - sem nuvem, sem nota de processo e sem nota de profundidade (0,70 m, decisão I3: o EL-001 não informa).
Coordenadas: UTM -> local da folha pelo inverso da transformação da SIT (geo_SIT.json; o EL-001 está no sistema da SIT).
Saída: RELATORIOS/EXECUTIVO_2026-10-24/<R00>_REVISADO.dwg -> carimbo QG R01 + PDF A0. Um accoreconsole por vez.
Uso: ..\\..\\.venv\\Scripts\\python.exe -X utf8 ita_el_r01.py [--so-lsp] [--so-carimbo]"""
import os, sys, csv, json, math, re, glob, shutil
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab  # noqa: E402

E = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA'
NOME = '24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R00'
ORIG = os.path.join(E, r'PROJETO_ORIGINAL\IMP\04_ELE', NOME + '.dwg')
OUT = os.path.join(E, r'RELATORIOS\EXECUTIVO_2026-10-24'); PDF = os.path.join(OUT, 'PDF')
COP = os.path.join(OUT, '_copias'); os.makedirs(PDF, exist_ok=True); os.makedirs(COP, exist_ok=True)
REV = os.path.join(OUT, NOME + '_REVISADO.dwg')
INS = os.path.join(E, r'RELATORIOS\PRECLASH_INSUMOS_2026-10-18')
DATA = '24/10/2026'
L1 = 'ALIMENTAÇÃO DO QDLT-CAMPO CONFORME QUADRO EXECUTADO'
LINHA_ELE04, LINHA_ELE05 = 'EF3D0', 'EF1CC'
QUADRO = ['EF206', 'EF207', 'EF208', 'EF5DC']            # quadro do campo desenhado (hatch, contorno, bloco, texto)
JANELA = (4341.81, 1201.37, 4468.01, 1316.17)            # janela da folha no modelo (viewport 2: centro 4404,91/1258,77, 126,2 x 114,8 m)

G = json.load(open(r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\ITAMIRA\geo_SIT.json', encoding='utf-8'))['rigid']
_a = math.radians(G['rot_deg']); _R = np.array([[math.cos(_a), -math.sin(_a)], [math.sin(_a), math.cos(_a)]]); _t = np.array(G['t'])
loc = lambda p: (np.asarray(p, float)[:2] - _t) @ _R
rd = lambda fn: list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'))


def wipeouts(dxf):
    L = open(dxf, encoding='utf-8', errors='replace').read().split('\n'); out = []; i = 0
    while i < len(L) - 1:
        if L[i].strip() == '0' and L[i + 1].strip() == 'WIPEOUT':
            j = i + 2; d = {}
            while L[j].strip() != '0': d.setdefault(L[j].strip(), L[j + 1].strip()); j += 2
            out.append((d.get('5'), float(d.get('10', 0)), float(d.get('20', 0)))); i = j
        else: i += 2
    return out


def P(p): return f'(list {p[0]:.4f} {p[1]:.4f} 0.0)'


def planejar(dxf):
    tr = {r['trecho']: r for r in rd(os.path.join(INS, 'ITA_ELE_trechos.csv'))}
    V6 = np.array([loc([float(v) for v in xy.split(',')]) for xy in tr['ELE-06']['vertices_UTM'].split()])
    cx = {r['caixa']: loc([float(r['E']), float(r['N'])]) for r in rd(os.path.join(INS, 'ITA_ELE_caixas.csv'))}
    ents = ab.entidades(dxf)
    perto = lambda e, c, r: np.hypot(*((e['pts'].mean(0) if 'pts' in e else e['p'])[:2] - c)) < r
    cx01 = [e['h'] for e in ents if e['lay'] == '0. F_SIMBOL' and perto(e, cx['CX-01'], 0.6)]
    cx01 += [e['h'] for e in ents if e['typ'] == 'MTEXT' and str(e.get('txt', '')).startswith('Cx.') and perto(e, cx['CX-01'], 2.0)]
    cx01 += [h for h, x, y in wipeouts(dxf) if np.hypot(x - cx['CX-01'][0], y - cx['CX-01'][1]) < 0.6]
    fia = [e for e in ents if e['lay'] == '01. F_FIAÇÃO-INDICAÇÃO' and e['h'] not in cx01]
    g04 = [e['h'] for e in fia if perto(e, np.array([4371.5, 1268.3]), 1.8)]
    g05 = [e['h'] for e in fia if perto(e, np.array([4372.6, 1257.4]), 1.8)]
    # as etiquetas têm chamada (LEADER, que o asbuilt não lê): a do ELE-05 sai com ela, a do ELE-04 anda junto, com a ponta da
    # chamada (no ELE-04) indo para o 1º terço do trecho CX-P1 -> CX-P2
    g05.append('EF450'); g04.append('EF48A')
    a04 = np.array([4374.652014, 1265.383855])
    alvo = V6[1] + (V6[2] - V6[1]) * 0.30
    # chamada na borda de baixo da folha: onde a ELE-06 sai da janela
    saida = None
    for A, B in zip(V6[:-1], V6[1:]):
        if (A[1] - JANELA[1]) * (B[1] - JANELA[1]) < 0:
            saida = A + (B - A) * (JANELA[1] - A[1]) / (B[1] - A[1])
    log = [f'CX-01: {len(cx01)} entidades do símbolo; etiqueta ELE-04: {len(g04)}; ELE-05: {len(g05)}',
           'vértices ELE-06 (local): ' + ' '.join(f'{p[0]:.2f},{p[1]:.2f}' for p in V6),
           f'QD1 local {V6[-1][0]:.2f},{V6[-1][1]:.2f}; janela y >= {JANELA[1]}; saída da janela: {saida}']
    hl = lambda hs: ' '.join(f'"{h}"' for h in hs)
    lsp = [r'''(defun ita:ss (hs / ss e) (setq ss (ssadd)) (foreach h hs (if (setq e (handent h)) (ssadd e ss))) ss)
(defun ita:del (hs / n e) (setq n 0) (foreach h hs (if (setq e (handent h)) (progn (entdel e) (setq n (1+ n))))) n)
(defun ita:prop (d k) (if (assoc k d) (list (assoc k d))))''',
           '(defun c:itael ( / d ss n)',
           '  (setvar "CMDECHO" 0) (setvar "TILEMODE" 1) (setvar "CTAB" "Model") (setvar "OSMODE" 0)',
           # eletroduto novo nas propriedades do ELE-04
           f'  (setq d (entget (handent "{LINHA_ELE04}")))',
           "  (entmake (append (list '(0 . \"LWPOLYLINE\") '(100 . \"AcDbEntity\") (assoc 8 d)) (ita:prop d 62) (ita:prop d 6) (ita:prop d 48) (ita:prop d 370)"
           f" (list '(100 . \"AcDbPolyline\") (cons 90 {len(V6)}) '(70 . 128)) (list "
           + ' '.join(f'(cons 10 (list {p[0]:.4f} {p[1]:.4f}))' for p in V6) + ')))',
           f'  (princ (strcat "\\nITAEL_APAGADAS=" (itoa (ita:del (list "{LINHA_ELE04}" "{LINHA_ELE05}" {hl(g05)})))))',
           # caixas
           f'  (setq ss (ita:ss (list {hl(cx01)})))',
           f'  (princ (strcat "\\nITAEL_CAIXA=" (itoa (sslength ss))))',
           f'  (command "_.COPY" ss "" {P(cx["CX-01"])} {P(cx["CX-P2"])})',
           f'  (command "_.COPY" ss "" {P(cx["CX-01"])} {P(cx["CX-P3"])})',
           f'  (command "_.MOVE" ss "" {P(cx["CX-01"])} {P(cx["CX-P1"])})',
           # etiqueta e quadro
           f'  (setq ss (ita:ss (list {hl(g04)})))',
           f'  (if (> (sslength ss) 0) (command "_.MOVE" ss "" {P(a04)} {P(alvo)}))',
           f'  (setq ss (ita:ss (list {hl(QUADRO)})))',
           f'  (if (> (sslength ss) 0) (command "_.MOVE" ss "" {P(cx["CX-01"] + (np.array([4378.156, 1258.498]) - cx["CX-01"]))} {P(V6[-1])}))']
    if saida is not None:
        txt = f'  (setq d (entget (handent "EF48C")))'
        q = saida + np.array([0.6, 1.4])
        lsp += [txt, "  (entmake (list '(0 . \"MTEXT\") '(100 . \"AcDbEntity\") (assoc 8 d) '(100 . \"AcDbMText\") "
                f"(cons 10 {P(q)}) (assoc 40 d) '(41 . 0.0) '(71 . 7) (assoc 7 d) (cons 1 \"SEGUE PARA O QDLT-CAMPO\")))"]
    lsp += ['  (command "_.REGENALL")', '  (princ "\\nITAEL_OK")', '  (princ))']
    return '\n'.join(lsp) + '\n', log


def carimbo():
    import carimbo_qg as CQ
    EXTRA = [dict(rev='01', data='OUT/2026', desc=L1, resp='POPULUS')]
    _ler = CQ.ler_carimbo

    def ler2(ent, c):
        F, revs, hs, topo = _ler(ent, c)
        return F, [r for r in revs if r['rev'] != '01'] + EXTRA, hs, topo
    CQ.ler_carimbo = ler2
    nome = NOME[:-3] + 'R01'; dst = os.path.join(OUT, nome + '.dwg')
    if os.path.exists(dst): shutil.move(dst, os.path.join(COP, nome + '_anterior.dwg'))
    shutil.copy2(REV, dst)
    for lg in glob.glob(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo\carimbo_qg\CARIMBO_QG_logo_*.png'): shutil.copy2(lg, OUT)
    cp0 = CQ.trocar(dst, data=DATA, so_ler=True)['carimbos'][0]['campos']; f0 = cp0.get('FOLHA', '')
    cmp = {'FOLHA': re.sub(r'R\d\d$', 'R01', f0)} if f0 else {}
    if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = '1:200'
    CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


if __name__ == '__main__':
    import rever
    if '--so-carimbo' not in sys.argv:
        cop = os.path.join(COP, NOME + '.dwg')
        if not os.path.exists(cop): shutil.copy2(ORIG, cop)
        dxf = cop[:-4] + '.dxf'
        if not os.path.exists(dxf):
            print(rever.console(cop, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")',
                                      'DXFX', '_.QUIT', '_Y'], cop + '.dxf.log', {'DXF_OUT': dxf.replace('\\', '/')}))
        lsp, log = planejar(dxf)
        print('\n'.join(log))
        fl_lsp = os.path.join(COP, 'ita_el_r01.lsp')
        open(fl_lsp, 'w', encoding='cp1252', errors='replace', newline='\r\n').write(lsp)
        if '--so-lsp' in sys.argv: sys.exit()
        if os.path.exists(REV): shutil.move(REV, os.path.join(COP, os.path.basename(REV)[:-4] + '_anterior.dwg'))
        tmp = os.path.join(COP, NOME + '_trab.dwg'); shutil.copy2(ORIG, tmp)
        out = rever.console(tmp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', f'(load "{fl_lsp.replace(chr(92), "/")}")', 'ITAEL',
                                  f'(command "_.SAVEAS" "2018" "{REV.replace(chr(92), "/")}")', '_.QUIT', '_Y'], tmp + '.log', {})
        lg = open(tmp + '.log', 'rb').read().replace(bytes(1), b'').decode('utf-8', 'replace') if os.path.exists(tmp + '.log') else ''
        print(out); print('\n'.join(l for l in lg.splitlines() if 'ITAEL' in l or 'error' in l.lower() or 'erro' in l.lower()))
        print('REVISADO', os.path.exists(REV))
    if '--so-lsp' not in sys.argv:
        carimbo()
