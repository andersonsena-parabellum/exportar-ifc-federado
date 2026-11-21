# -*- coding: utf-8 -*-
"""Jandaíra — carimbo e PDF das pranchas no padrão de executivo final (EXECUTIVO_R02/*_REVISADO.dwg):
  - cópia com a revisão seguinte no nome (…-R01 -> …-R02) em EXECUTIVO_R02/;
  - no papel de cada folha: linha nova no quadro de revisões do carimbo da QG (número, data no formato das linhas de cima,
    descrição, POPULUS — mesmas colunas e altura das linhas existentes) e código da folha …_R<atual> -> …_R<nova>;
    nenhuma legenda de processo;
  - um PDF por folha em EXECUTIVO_R02/PDF/ (DWG To PDF.pc3, ISO full bleed A0, extensão ajustada).
As posições do quadro saem do DXF da cópia (papel intocado). Funções de leitura do papel iguais às de georef/exec_padrao_catu.py.
Uso: python -X utf8 jan_carimbo.py [--so-ler] [prancha ...]"""
import os, sys, re, glob, json, shutil, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import rever
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02'; COP = os.path.join(OUT, '_copias'); PDF = os.path.join(OUT, 'PDF')
DESC = os.environ.get('JAN_CARIMBO_DESC') or 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
DATA = tuple(int(x) for x in (os.environ.get('JAN_CARIMBO_DATA') or '19/10/2026').split('/'))
MES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']


def lisp_str(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + ''.join(c if ord(c) < 128 else '\\\\U+%04X' % ord(c) for c in s) + '"'


def dxf_papel(fn):
    """layouts (nome por handle do bloco de papel), textos do papel e viewports, do DXF ASCII."""
    L = [x.strip() for x in open(fn, encoding='utf-8', errors='replace')]
    P = [(L[k], L[k + 1]) for k in range(0, len(L) - 1, 2)]
    tx, vp, lay = [], [], {}
    i = 0
    while i < len(P):
        c, v = P[i]
        if c == '0' and v in ('TEXT', 'MTEXT', 'VIEWPORT', 'LAYOUT'):
            d = collections.defaultdict(list); j = i + 1; sub = ''; nome_lay = None; br = None
            while j < len(P) and P[j][0] != '0':
                cc, vv = P[j]; d[cc].append(vv)
                if cc == '100': sub = vv
                elif v == 'LAYOUT' and sub == 'AcDbLayout' and cc == '1' and nome_lay is None: nome_lay = vv
                elif v == 'LAYOUT' and sub == 'AcDbLayout' and cc == '330': br = vv
                j += 1
            g = lambda k, n=0: d[k][n] if len(d[k]) > n else None
            if v == 'LAYOUT':
                if nome_lay and br: lay[br] = nome_lay
            elif g('67') == '1':
                if v == 'VIEWPORT':
                    vp.append({'own': g('330'), 'x': float(g('10')), 'y': float(g('20')), 'w': float(g('40')), 'h': float(g('41')), 'id': g('69')})
                else:
                    tx.append({'own': g('330'), 'h5': g('5'), 'x': float(g('10')), 'y': float(g('20')), 't': g('1') or '', 'lay': g('8'), 'st': g('7'),
                               'alt': float(g('40') or 0), 'typ': v})
            i = j
        else: i += 1
    for o in tx + vp: o['layout'] = lay.get(o['own'])
    return tx, vp, lay


def quadro_revisoes(tx):
    """por layout: linhas do quadro de revisões (texto "##" com a data 10,24 mm à direita), colunas copiadas da última linha."""
    out = {}
    for d in tx:
        if not re.fullmatch(r'\d\d', d['t'].strip()): continue
        dt = [e for e in tx if e['layout'] == d['layout'] and re.search(r'/(20)?\d\d$', e['t'].strip()) and abs(e['x'] - d['x'] - 10.239) < 2.5 and abs(e['y'] - d['y']) < 1.5]
        if not dt: continue
        q = out.setdefault(d['layout'], {'x0': d['x'], 'linhas': []})
        if abs(q['x0'] - d['x']) < 0.5: q['linhas'].append(d)
    for lay, q in out.items():
        ls = sorted(q['linhas'], key=lambda d: d['y']); ys = [d['y'] for d in ls]
        q['esp'] = float(np.median(np.diff(ys))) if len(ys) > 1 else 5.115; q['ultima'] = max(int(d['t']) for d in ls)
        top = ls[-1]                                                     # colunas da última linha: textos na mesma faixa de y
        q['cols'] = sorted([e for e in tx if e['layout'] == lay and abs(e['y'] - top['y']) < 1.5 and e['x'] >= top['x'] - 0.5], key=lambda e: e['x'])
        q['top'] = top
    return out


def data_como(t):
    t = t.strip()
    if re.fullmatch(r'\d\d/\d\d/\d{4}', t): return '%02d/%02d/%d' % DATA
    if re.fullmatch(r'\d\d/\d\d/\d\d', t): return '%02d/%02d/%02d' % (DATA[0], DATA[1], DATA[2] % 100)
    if re.fullmatch(r'[A-Z]{3}/\d{4}', t): return '%s/%d' % (MES[DATA[1] - 1], DATA[2])
    if re.fullmatch(r'\d\d/\d{4}', t): return '%02d/%d' % (DATA[1], DATA[2])
    return '%02d/%02d/%d' % DATA


def lisp_papel(q, nova, atual, tx):
    L = ['(setvar "CMDECHO" 0)']
    for lay, r in q.items():
        dy = r['esp']; cols = r['cols']; top = r['top']
        for k, c in enumerate(cols):
            if c is top: t = '%02d' % nova
            elif re.search(r'/(20)?\d\d$', c['t'].strip()): t = data_como(c['t'])
            elif k == len(cols) - 1 and len(cols) >= 4: t = 'POPULUS'
            else: t = DESC
            ent = 'MTEXT' if c['typ'] == 'MTEXT' else 'TEXT'
            if ent == 'MTEXT':
                L.append(f'(setq e (entget (handent "{c["h5"]}"))) (entmake (append (vl-remove-if (function (lambda (g) (member (car g) (list -1 5 330 10 1 3 41 46)))) e) '
                         f'(list (list 10 {c["x"]:.4f} {c["y"] + dy:.4f} 0.0) (cons 1 {lisp_str(t)}))))')
            else:
                L.append(f'(setq e (entget (handent "{c["h5"]}"))) (entmake (append (vl-remove-if (function (lambda (g) (member (car g) (list -1 5 330 10 11 1)))) e) '
                         f'(list (list 10 {c["x"]:.4f} {c["y"] + dy:.4f} 0.0) (list 11 {c["x"]:.4f} {c["y"] + dy:.4f} 0.0) (cons 1 {lisp_str(t)}))))')
        L.append(f'(princ "\\nJAN_REV linha {nova:02d} em {lay}")')
    for d in tx:
        if re.fullmatch(rf'[A-Z]+_[A-Z]{{3}}-\d{{3}}_R{atual:02d}', d['t'].strip()):
            novo = d['t'].strip()[:-2] + f'{nova:02d}'
            L.append(f'(if (setq rv:e (handent "{d["h5"]}")) (progn (setq rv:d (entget rv:e)) (entmod (subst (cons 1 {lisp_str(novo)}) (assoc 1 rv:d) rv:d)) (princ "\\nJAN_REV codigo {novo}")))')
    L.append('(princ)')
    return '\n'.join(L) + '\n'


def lisp_pdf(base_pdf, layouts):
    b = base_pdf.replace(os.sep, '/')
    L = ['(setvar "BACKGROUNDPLOT" 0) (setvar "FILEDIA" 0) (setvar "CMDECHO" 1)']
    for lay in layouts:
        L.append(f'(setvar "CTAB" {lisp_str(lay)})')
        L.append(f'(command "_.-PLOT" "_Y" {lisp_str(lay)} "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_E" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N" '
                 f'{lisp_str(b + "_" + re.sub(r"[^A-Za-z0-9-]+", "_", lay) + ".pdf")} "_N" "_Y")')
        L.append(f'(princ "\\nJAN_PDF {lay}")')
    L.append('(princ)')
    return '\n'.join(L) + '\n'


def processar(base, so_ler=False):
    rev = os.path.join(OUT, base + '_REVISADO.dwg'); tx, vp, lays = dxf_papel(os.path.join(COP, base + '.dxf'))
    m = re.search(r'-R(\d\d)$', base); atual = int(m.group(1)); nova = atual + 1; nome_novo = base[:-2] + f'{nova:02d}'
    q = quadro_revisoes(tx)
    cod = [d['t'] for d in tx if re.fullmatch(rf'[A-Z]+_[A-Z]{{3}}-\d{{3}}_R{atual:02d}', d['t'].strip())]
    layouts = sorted({v['layout'] for v in vp if v['layout'] and v['id'] != '1'})
    info = dict(prancha=base, nova=nome_novo, quadros={k: dict(ultima=v['ultima'], esp=round(v['esp'], 3), colunas=[c['t'][:30] for c in v['cols']]) for k, v in q.items()},
                codigos=cod, layouts=layouts)
    print(json.dumps(info, ensure_ascii=False))
    if so_ler: return info
    os.makedirs(PDF, exist_ok=True)
    dst = os.path.join(OUT, nome_novo + '.dwg')
    if os.path.exists(dst): os.replace(dst, os.path.join(COP, nome_novo + '_anterior.dwg'))
    shutil.copy2(rev, dst)
    fpap = os.path.join(COP, f'pap_{nome_novo}.lsp'); open(fpap, 'w', encoding='ascii').write(lisp_papel(q, nova, atual, tx))
    fpdf = os.path.join(COP, f'pdf_{nome_novo}.lsp'); open(fpdf, 'w', encoding='ascii').write(lisp_pdf(os.path.join(PDF, nome_novo), layouts))
    out = rever.console(dst, ['SECURELOAD 0', 'FILEDIA 0', 'EXPERT 5', '(load "%s")' % fpap.replace('\\', '/'), '_.QSAVE', '(load "%s")' % fpdf.replace('\\', '/'), '_.QUIT', '_Y'],
                        dst + '.log', {})
    bak = dst[:-4] + '.bak'
    if os.path.exists(bak): os.replace(bak, os.path.join(COP, os.path.basename(bak)))
    log = open(dst + '.log', encoding='utf-8', errors='replace').read() if os.path.exists(dst + '.log') else ''
    info.update(dwg=dst, marcas=[l.strip() for l in log.splitlines() if 'JAN_' in l and not l.strip().startswith('(')],
                pdfs=sorted(os.path.basename(p) for p in glob.glob(os.path.join(PDF, nome_novo + '_*.pdf'))), console=out[-200:])
    print(nome_novo, '|', '; '.join(info['marcas']), '|', len(info['pdfs']), 'PDF')
    return info


if __name__ == '__main__':
    so_ler = '--so-ler' in sys.argv
    alvos = [a for a in sys.argv[1:] if not a.startswith('--')] or [os.path.basename(f)[:-len('_REVISADO.dwg')] for f in glob.glob(os.path.join(OUT, '*_REVISADO.dwg'))]
    R = [processar(a, so_ler) for a in alvos]
    if not so_ler: json.dump(R, open(os.path.join(OUT, 'JAN_carimbo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
