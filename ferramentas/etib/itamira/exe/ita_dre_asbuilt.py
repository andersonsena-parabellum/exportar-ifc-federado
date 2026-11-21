# -*- coding: utf-8 -*-
"""Itamira — DRE-001 R01 redesenhada pela drenagem construída do campo (decisão I2 do Anderson, 23/10/2026: "Redesenhe. O as built
sempre vai ser o mais recente do que o projeto original").
Padrão de executivo final (AGENTS.md > Pranchas), numa cópia do R00:
  - sai a rede do R00 (toda dentro do bloco zw$F9C4) e a chamada "SEGUE PARA A REDE EXISTENTE" (MTEXT + linha de chamada);
  - entra a rede construída, lida do IFC as built do IMP (os mesmos CSV que geraram o ITA_IMP_HIDRO_R01.ifc), nos layers e no
    desenho da própria folha: tubo PVC liso em linha dupla no AP-Condutos (item "Rede de Águas Pluviais (PVC-R)" da legenda),
    dreno PVC corrugado perfurado em linha dupla tracejada (layer novo AP-Condutos-perfurado, mesma cor, DASHED2 por layer: item
    "PVC Corrugado perfurado" da legenda), caixa de areia como o símbolo CA da folha (AP-Caixa de alvenaria), ralos (Simbolos),
    seta de sentido (AP-Sentido conduto) e etiquetas "PVC 150 mm / i=1%" em Arial 0,40 (AP-Textos conduto), como as do R00;
  - calha semicircular de concreto (não existe na legenda): layer AP-Calha em cor que a legenda não usa (200, violeta; a legenda usa 14, 30, 74, 150 e 174) e quadro
    novo na legenda, abaixo das notas (como o onn_existente.lsp da Olindina);
  - caixas com nome e CT/CF do as built; nenhuma nuvem, nota de processo ou rede "suprimida".
Saída: RELATORIOS/EXECUTIVO_2026-10-23/<R00>_REVISADO.dwg; depois o carimbo QG (R01, linha no quadro de revisões) e o PDF A0.
Um accoreconsole por vez (rever.console espera os das outras threads).
Uso: ..\\..\\.venv\\Scripts\\python.exe -X utf8 ita_dre_asbuilt.py [--so-lsp] [--so-carimbo]"""
import os, sys, csv, json, math, re, glob, shutil
import numpy as np
from shapely.geometry import Polygon, LineString, Point
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import dxfgeo  # noqa: E402

E = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA'
NOME = '24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R00'
ORIG = os.path.join(E, r'PROJETO_ORIGINAL\IMP\03_DRE', NOME + '.dwg')
OUT = os.path.join(E, r'RELATORIOS\EXECUTIVO_2026-10-23'); PDF = os.path.join(OUT, 'PDF')
COP = os.path.join(OUT, '_copias'); os.makedirs(PDF, exist_ok=True); os.makedirs(COP, exist_ok=True)
REV = os.path.join(OUT, NOME + '_REVISADO.dwg')
INS = os.path.join(E, r'RELATORIOS\PRECLASH_INSUMOS_2026-10-18')
DATA = '23/10/2026'
L1 = 'REDE DE DRENAGEM DO CAMPO CONFORME EXECUTADO'
H = 0.40                                   # altura das etiquetas da rede no R00 (Arial, AP-Textos conduto)
APAGAR = ['23FD2F', '24B962', '24B961']    # bloco da rede R00, "SEGUE PARA A REDE EXISTENTE" e a linha de chamada

G = json.load(open(os.path.join(E, r'CAD_GEORREFERENCIADO\transformacao_DRE_local_para_UTM.json'), encoding='utf-8'))['rigid']
_a = math.radians(G['rot_deg']); _R = np.array([[math.cos(_a), -math.sin(_a)], [math.sin(_a), math.cos(_a)]]); _t = np.array(G['t'])
loc = lambda p: (np.asarray(p, float)[:2] - _t) @ _R          # UTM -> local da folha (inverso de UTM = R.p + t)
rd = lambda fn: list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'))
fl = lambda v: float(str(v).replace(',', '.'))
br = lambda x, n=2: f'{x:.{n}f}'.replace('.', ',')


def dados():
    tr = [r for r in rd(os.path.join(INS, 'ITA_asbuilt_campo_trechos.csv')) if r['categoria'] != 'eletroduto']
    ca = [r for r in rd(os.path.join(INS, 'ITA_asbuilt_campo_caixas.csv')) if r['tipo'] == 'CA']
    ralos = [r for r in rd(os.path.join(INS, 'ITA_equipamentos.csv')) if r['id'].startswith('RALO')]
    return tr, ca, ralos


def textos_base(dxf):
    """retângulos (local) dos textos que ficam na folha: base de arquitetura e o que não é da rede R00."""
    out = []
    for t in dxfgeo.load(dxf)['texts']:
        if 'zw$F9C4' in str(t.get('path')) or not str(t['t']).strip(): continue
        p = np.array(t['p'][:2], float); h = float(t['h']); w = max(1, len(re.sub(r'\\[A-Za-z][^;]*;|[{}]', '', str(t['t'])))) * 0.6 * h
        a = math.radians(float(t['rot'])) if abs(float(t['rot'])) > 6.3 else float(t['rot'])
        out.append(ret(p + np.array([math.cos(a), math.sin(a)]) * w / 2, a, w, h))
    return out


def ret(c, a, w, h):
    u = np.array([math.cos(a), math.sin(a)]); v = np.array([-u[1], u[0]]); c = np.asarray(c, float)
    return Polygon([c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2, c + u * w / 2 + v * h / 2, c - u * w / 2 + v * h / 2])


def legivel(a):
    """ângulo do texto ao longo do tubo, sempre lido da esquerda para a direita."""
    while a > math.pi / 2 + 1e-6: a -= math.pi
    while a <= -math.pi / 2 + 1e-6: a += math.pi
    return a


def pct(i):
    return f'{round(i):.0f}%' if abs(i - round(i)) < 0.15 else f'{br(i, 1)}%'


# ---------------------------------------------------------------- LISP
def L(x): return f'{x:.4f}'
def P(p): return f'(list {L(p[0])} {L(p[1])} 0.0)'


def lw(lay, pts, fechado=False, larg=None, lt=None):
    s = [f"'(0 . \"LWPOLYLINE\") '(100 . \"AcDbEntity\") (cons 8 \"{lay}\")"]
    if lt: s.append(f'(cons 6 "{lt}")')
    s += ["'(100 . \"AcDbPolyline\")", f"'(90 . {len(pts)})", f"'(70 . {129 if fechado else 128})"]   # 128 = geração de linetype
    for v in pts:
        if isinstance(v, tuple) and len(v) == 3:      # (ponto, largura inicial, largura final)
            s.append(f'(cons 10 (list {L(v[0][0])} {L(v[0][1])}))'); s.append(f"'(40 . {v[1]})"); s.append(f"'(41 . {v[2]})")
        else:
            s.append(f'(cons 10 (list {L(v[0])} {L(v[1])}))')
            if larg is not None: s.append(f"'(40 . {larg})"); s.append(f"'(41 . {larg})")
    return '(entmake (list ' + ' '.join(s) + '))'


def circ(lay, c, r):
    return f"(entmake (list '(0 . \"CIRCLE\") '(100 . \"AcDbEntity\") (cons 8 \"{lay}\") '(100 . \"AcDbCircle\") (cons 10 {P(c)}) (cons 40 {r})))"


def mt(lay, p, txt, at, rot=0.0, h=H, st='Arial'):
    txt = txt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\\\P')
    return (f"(entmake (list '(0 . \"MTEXT\") '(100 . \"AcDbEntity\") (cons 8 \"{lay}\") '(100 . \"AcDbMText\") (cons 10 {P(p)}) "
            f"(cons 40 {h}) '(41 . 0.0) (cons 71 {at}) (cons 7 \"{st}\") (cons 50 {rot:.6f}) (cons 1 \"{txt}\")))")


def dupla(lay, A, B, d):
    u = (B - A) / np.linalg.norm(B - A); n = np.array([-u[1], u[0]]) * d / 2
    return [lw(lay, [A + n, B + n]), lw(lay, [A - n, B - n])]


def planejar(dxf):
    tr, ca, ralos = dados()
    ocup = textos_base(dxf)                       # retângulos ocupados (textos da folha + os nossos)
    seg = []                                      # (LineString local, categoria, id)
    for r in tr:
        A, B = loc([fl(r['E_ini']), fl(r['N_ini'])]), loc([fl(r['E_fim']), fl(r['N_fim'])])
        seg.append((A, B, fl(r['eixo_ini']), fl(r['eixo_fim']), r))
    linhas = [LineString([s[0], s[1]]) for s in seg]
    caixas = {r['caixa']: (loc([fl(r['E']), fl(r['N'])]), fl(r['meia_m']), fl(r['zt']), fl(r['zb'])) for r in ca}
    eixo = math.atan2(*(lambda d: (d[1], d[0]))(seg[[s[4]['categoria'] for s in seg].index('calha')][1] - seg[[s[4]['categoria'] for s in seg].index('calha')][0]))
    cx_pol = [ret(c, eixo, 2 * m + 0.2, 2 * m + 0.2) for c, m, _, _ in caixas.values()]
    centro = np.mean([c for c, *_ in caixas.values()], 0)
    cmd, log = [], []
    # traçado
    for (A, B, za, zb, r) in seg:
        cat = r['categoria']
        if cat == 'tubo_liso': cmd += dupla('AP-Condutos', A, B, 0.15)
        elif cat == 'dreno': cmd += dupla('AP-Condutos-perfurado', A, B, 0.15)
        else: cmd += dupla('AP-Calha', A, B, fl(r['DE_m']))
    # caixas de areia: símbolo CA da folha (quadrado contínuo + interno tracejado JIS_02_1.2, como no R00)
    for nm, (c, m, zt, zb) in caixas.items():
        u = np.array([math.cos(eixo), math.sin(eixo)]); v = np.array([-u[1], u[0]])
        for lado, lt in ((2 * m, None), (2 * m - 0.20, 'JIS_02_1.2')):
            q = [c + su * u * lado / 2 + sv * v * lado / 2 for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            cmd.append(lw('AP-Caixa de alvenaria', q, fechado=True, lt=lt))
    for r in ralos:
        c = loc([fl(r['E']), fl(r['N'])])
        cmd += [circ('Simbolos', c, 0.15), circ('Simbolos_int', c, 0.075)]
    # etiquetas e setas (trechos com 4 m ou mais), sem cobrir texto, caixa nem outro trecho
    for k, (A, B, za, zb, r) in enumerate(seg):
        cat = r['categoria']; Lm = float(np.linalg.norm(B - A))
        if Lm < 4.0: continue
        u = (B - A) / Lm; a = legivel(math.atan2(u[1], u[0])); ua = np.array([math.cos(a), math.sin(a)]); na = np.array([-ua[1], ua[0]])
        if cat == 'calha':
            t1, t2 = 'CALHA DE CONCRETO Ø30 cm', None
        else:
            dn = 150 if cat == 'tubo_liso' else 100
            t1 = f"PVC {dn} mm" if cat == 'tubo_liso' else f"DRENO {dn} mm"
            t2 = 'i=' + pct(abs(zb - za) / Lm * 100)
        w1 = len(t1) * 0.6 * H; w2 = len(t2) * 0.6 * H if t2 else 0
        feito = False
        for f in (0.5, 0.4, 0.6, 0.3, 0.7, 0.25, 0.75):
            m = A + (B - A) * f
            R1 = ret(m + na * (0.15 + H / 2 + 0.05), a, w1, H)
            R2 = ret(m - na * (0.15 + H / 2 + 0.05), a, w2, H) if t2 else None
            rs = [x for x in (R1, R2) if x is not None]
            if any(x.intersects(o) for x in rs for o in ocup + cx_pol): continue
            if any(x.intersects(linhas[j]) for x in rs for j in range(len(seg)) if j != k): continue
            cmd.append(mt('AP-Textos conduto', m + na * (0.15 + 0.05), t1, 8, a))
            if t2: cmd.append(mt('AP-Textos conduto', m - na * (0.15 + 0.05), t2, 2, a))
            ocup += rs; feito = True
            if cat != 'calha':                           # seta no sentido do escoamento (da ponta alta para a baixa)
                s = u if zb < za else -u; p0 = m - s * 0.25
                cmd.append(lw('AP-Sentido conduto', [(p0, 0.18, 0.0), (p0 + s * 0.5, 0.0, 0.0)]))
            break
        log.append(f"{r['id']} {cat} {Lm:.1f} m: " + (f'etiqueta "{t1}{" / " + t2 if t2 else ""}"' if feito else 'SEM LUGAR para a etiqueta'))
    # nome e cotas das caixas (fora do campo, horizontal)
    for nm, (c, m, zt, zb) in caixas.items():
        txt = f'{nm}\nCT {br(zt)}\nCF {br(zb)}'; w = 7 * 0.6 * H; hh = 3 * H * 1.25
        ok = False
        dirs = sorted([np.array([math.cos(t), math.sin(t)]) for t in np.radians(np.arange(0, 360, 30))], key=lambda d: -(d @ (c - centro)))
        for d in dirs:
            for dist in (1.0, 1.6, 2.4):
                q = c + d * (m + dist); R = ret(q, 0.0, w, hh)
                if R.intersects(Polygon(cx_pol[list(caixas).index(nm)].exterior)) or any(R.intersects(o) for o in ocup + cx_pol) \
                        or any(R.intersects(ln) for ln in linhas):
                    continue
                cmd.append(mt('AP-Textos conduto', q, txt, 5)); ocup.append(R); ok = True; break
            if ok: break
        log.append(f'{nm}: ' + ('rótulo CT/CF' if ok else 'SEM LUGAR para o rótulo'))
    return cmd, log


LEG = r'''
(defun ita:tem_dreno (nome / b e r)
  (if (setq b (tblobjname "BLOCK" nome))
    (progn (setq e (entnext b))
      (while (and e (not r))
        (if (and (= (cdr (assoc 0 (entget e))) "MTEXT") (wcmatch (cdr (assoc 1 (entget e))) "*Dreno AC*")) (setq r T))
        (setq e (entnext e)))))
  r)
(defun ita:leg ( / ss i d out)
  (if (setq ss (ssget "X" '((0 . "INSERT") (67 . 1))))
    (progn (setq i 0)
      (repeat (sslength ss)
        (setq d (entget (ssname ss i)))
        (if (and (null out) (ita:tem_dreno (cdr (assoc 2 d)))) (setq out (list (cdr (assoc 410 d)) (cdr (assoc 10 d)))))
        (setq i (1+ i)))))
  out)
(defun ita:estilo ( / b e d r)
  (if (setq b (tblobjname "BLOCK" "LEGENDA - ETIBs"))
    (progn (setq e (entnext b))
      (while (and e (not r))
        (setq d (entget e))
        (if (and (= (cdr (assoc 0 d)) "MTEXT") (wcmatch (cdr (assoc 1 d)) "*Dreno AC*")) (setq r (list (cdr (assoc 7 d)) (cdr (assoc 40 d)))))
        (setq e (entnext e)))))
  (if r r (list "Standard" 2.2)))
(defun ita:pl (lay pts lo fecha)
  (entmake (append (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(67 . 1) (cons 410 lo) (cons 8 lay) '(100 . "AcDbPolyline")
                         (cons 90 (length pts)) (cons 70 (if fecha 1 0)))
                   (mapcar '(lambda (p) (cons 10 p)) pts))))
(defun ita:mt (lay lo p h at txt st)
  (entmake (list '(0 . "MTEXT") '(100 . "AcDbEntity") '(67 . 1) (cons 410 lo) (cons 8 lay) '(100 . "AcDbMText")
                 (cons 10 (list (car p) (cadr p) 0.0)) (cons 40 h) '(41 . 0.0) (cons 71 at) (cons 7 st) (cons 1 txt))))
;; quadro "DRENAGEM DO CAMPO" na coluna da legenda (bloco inserido em -702,11 / 230,36: coluna x 603,07 a 763,18; as notas
;; gerais terminam em y 153,3 e o quadro de revisões começa abaixo de y ~100)
(defun ita:quadro ( / lg lo ins est st h x0 x1 y0 r n)
  (setq lg (ita:leg) n 0)
  (if (null lg) (princ "\nITALEG: legenda nao achada")
    (progn
      (setq lo (car lg) ins (cadr lg) est (ita:estilo) st (car est) h (cadr est))
      (setq x0 (+ (car ins) 1305.18) x1 (+ (car ins) 1465.28) y0 (- (+ (cadr ins) -77.04) 6.0) r 5.845)
      (if (ita:pl "DI-Tabelas" (list (list x0 y0) (list x1 y0) (list x1 (- y0 (* 2 r))) (list x0 (- y0 (* 2 r)))) lo T) (setq n (1+ n)))
      (if (ita:pl "DI-Tabelas" (list (list x0 (- y0 r)) (list x1 (- y0 r))) lo nil) (setq n (1+ n)))
      (if (ita:mt "DI-Tabelas" lo (list (/ (+ x0 x1) 2) (- y0 (/ r 2))) h 5 "DRENAGEM DO CAMPO SOCIETY" st) (setq n (1+ n)))
      (if (ita:pl "AP-Calha" (list (list (+ x0 4.0) (- y0 (* 1.5 r) -1.0)) (list (+ x0 22.0) (- y0 (* 1.5 r) -1.0))) lo nil) (setq n (1+ n)))
      (if (ita:pl "AP-Calha" (list (list (+ x0 4.0) (- y0 (* 1.5 r) 1.0)) (list (+ x0 22.0) (- y0 (* 1.5 r) 1.0))) lo nil) (setq n (1+ n)))
      (if (ita:mt "DI-Tabelas" lo (list (+ x0 26.0) (- y0 (* 1.5 r))) h 4 "Calha semicircular de concreto (Ø30 cm)" st) (setq n (1+ n)))
      (princ (strcat "\nITALEG_OK " (itoa n) " de 6 entidades no layout " lo)))))
'''


def lisp(cmd):
    cab = ['(defun ita:lay (nm cor lt) (if (not (tblsearch "LAYER" nm)) (entmake (list \'(0 . "LAYER") \'(100 . "AcDbSymbolTableRecord") '
           '\'(100 . "AcDbLayerTableRecord") (cons 2 nm) \'(70 . 0) (cons 62 cor) (cons 6 lt)))))',
           LEG,
           '(defun c:itadre ( / n e)',
           '  (setvar "CMDECHO" 0) (setvar "TILEMODE" 1) (setvar "CTAB" "Model")',
           '  (if (not (tblsearch "LTYPE" "DASHED2")) (command "_.-LINETYPE" "_L" "DASHED2" "acadiso.lin" ""))',
           '  (ita:lay "AP-Condutos-perfurado" 150 "DASHED2") (ita:lay "AP-Calha" 200 "Continuous")',
           '  (setq n 0)']
    for h in APAGAR:
        cab.append(f'  (if (setq e (handent "{h}")) (progn (entdel e) (setq n (1+ n))))')
    cab.append(f'  (princ (strcat "\\nITADRE_APAGADAS=" (itoa n) " de {len(APAGAR)}"))')
    corpo = [f'  {c}' for c in cmd]
    fim = [f'  (princ "\\nITADRE_NOVAS={len(cmd)}")', '  (ita:quadro)', '  (command "_.REGENALL")', '  (princ))']
    return '\n'.join(cab + corpo + fim) + '\n'


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
    print('carimbo', nome, cmp)
    CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


if __name__ == '__main__':
    import rever
    if '--so-carimbo' not in sys.argv:
        cop = os.path.join(COP, NOME + '.dwg'); shutil.copy2(ORIG, cop)
        dxf = cop[:-4] + '.dxf'
        if not os.path.exists(dxf):
            print(rever.console(cop, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")',
                                      'DXFX', '_.QUIT', '_Y'], cop + '.dxf.log', {'DXF_OUT': dxf.replace('\\', '/')}))
        cmd, log = planejar(dxf)
        print('\n'.join(log))
        fl_lsp = os.path.join(COP, 'ita_dre_asbuilt.lsp')
        open(fl_lsp, 'w', encoding='cp1252', errors='replace', newline='\r\n').write(lisp(cmd))
        if '--so-lsp' in sys.argv: sys.exit()
        if os.path.exists(REV): shutil.move(REV, os.path.join(COP, os.path.basename(REV)[:-4] + '_anterior.dwg'))
        tmp = os.path.join(COP, NOME + '_trab.dwg'); shutil.copy2(ORIG, tmp)
        out = rever.console(tmp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', f'(load "{fl_lsp.replace(chr(92), "/")}")', 'ITADRE',
                                  f'(command "_.SAVEAS" "2018" "{REV.replace(chr(92), "/")}")', '_.QUIT', '_Y'], tmp + '.log', {})
        lg = open(tmp + '.log', 'rb').read().replace(bytes(1), b'').decode('utf-8', 'replace') if os.path.exists(tmp + '.log') else ''
        print(out); print('\n'.join(l for l in lg.splitlines() if 'ITADRE' in l or 'ITALEG' in l or 'error' in l.lower() or 'erro' in l.lower()))
        print('REVISADO', os.path.exists(REV))
    if '--so-lsp' not in sys.argv:
        carimbo()
