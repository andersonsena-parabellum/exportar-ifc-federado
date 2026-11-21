# -*- coding: utf-8 -*-
"""ETIB Catu — executivos revisados no padrão das outras escolas (Sátiro exec_rev_sat.py / Prof. Áurea pranchas_r01.py), 19/10/2026.
Para cada prancha com alteração (AF, EL-001, EL-002, INC-001), a partir do ORIGINAL (PROJETO_ORIGINAL, só leitura):
  - cópia com a REVISÃO SEGUINTE no nome (…-R02 -> …-R03) em ETIB-CATU/EXECUTIVO_REVISADO/;
  - no modelo, o desenho da compatibilização de exec_catu.py (layers COMPAT-R01-*: removido tracejado, novo, nuvem Rnn, mergulho Mnn,
    quadro de notas);
  - no papel de cada folha: linha nova no quadro de revisões do carimbo da QG (número, data, descrição, POPULUS — mesmas colunas da
    Sátiro), código da folha …_R<atual> -> …_R<nova> e a legenda "REVISÃO COMP-01" no canto da viewport principal;
  - um PDF por folha (DWG To PDF.pc3, configuração da própria folha) e um PDF com a lista completa das notas (Rnn/Mnn).
As posições do carimbo saem do DXF da cópia revisada (work/CATU/exec/*_COMPAT-R01.dxf, papel intocado), pelas linhas do quadro
(texto "##" com data "*/20##" 10,24 mm à direita). Um accoreconsole por vez (run_acc.ps1).
Uso: .venv/Scripts/python.exe -X utf8 georef/exec_padrao_catu.py [--so=AF,EL1]"""
import os, sys, re, csv, glob, shutil, subprocess, collections
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exec_catu as ex          # noqa: E402
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

SAI = ex.SAI; WRK = ex.WRK; DATA = ex.DATA
ANT = os.path.join(WRK, '_anteriores')


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
                    tx.append({'own': g('330'), 'h5': g('5'), 'x': float(g('10')), 'y': float(g('20')), 't': g('1') or '', 'lay': g('8'), 'st': g('7'), 'alt': float(g('40') or 0)})
            i = j
        else: i += 1
    for o in tx + vp: o['layout'] = lay.get(o['own'])
    return tx, vp, lay


def quadro_revisoes(tx):
    """por layout: coluna REV (x0), y das linhas, espaçamento, layer e estilo do texto."""
    out = {}
    for d in tx:
        if not re.fullmatch(r'\d\d', d['t']): continue
        dt = [e for e in tx if e['layout'] == d['layout'] and re.search(r'/20\d\d$', e['t']) and abs(e['x'] - d['x'] - 10.239) < 1.5 and abs(e['y'] - d['y'] - 0.718) < 1.0]
        if not dt: continue
        q = out.setdefault(d['layout'], {'x0': d['x'], 'ys': [], 'revs': [], 'lay': d['lay'], 'st': d['st']})
        if abs(q['x0'] - d['x']) < 0.5: q['ys'].append(d['y']); q['revs'].append(int(d['t']))
    for q in out.values():
        ys = sorted(q['ys']); q['ymax'] = ys[-1]; q['esp'] = float(np.median(np.diff(ys))) if len(ys) > 1 else 5.115; q['ultima'] = max(q['revs'])
    return out


def lisp_papel(tag, nome_novo, atual, nova, tx, vp, itens_r, itens_m, desc):
    s = ex.lisp_str; L = ['(setvar "CMDECHO" 0)']
    q = quadro_revisoes(tx)
    for lay, r in q.items():
        y = r['ymax'] + r['esp']; st = r['st'] or 'Standard'
        for dx, dy, t, w in ((0.0, 0.0, f'{nova:02d}', 4.0), (10.239, 0.718, DATA.split('/', 1)[1].replace('10/', 'OUT/'), 15.0), (29.013, 0.581, desc, 125.0), (157.132, 0.336, 'POPULUS', 20.0)):
            L.append(f'(entmake (list \'(0 . "MTEXT") \'(100 . "AcDbEntity") \'(67 . 1) (cons 410 {s(lay)}) (cons 8 {s(r["lay"] or "0")}) \'(100 . "AcDbMText") '
                     f'(list 10 {r["x0"] + dx:.4f} {y + dy:.4f} 0.0) \'(40 . 1.842) (cons 41 {w}) \'(71 . 1) (cons 1 {s(t)}) (cons 7 (if (tblsearch "STYLE" {s(st)}) {s(st)} "Standard"))))')
        L.append(f'(princ "\\nCOMPAT_REV linha {nova:02d} em {lay}")')
    for d in tx:      # código da folha DISC_IMP-###_Rxx
        if re.fullmatch(rf'[A-Z]+_[A-Z]{{3}}-\d{{3}}_R{atual:02d}', d['t']):
            novo = d['t'][:-2] + f'{nova:02d}'
            L.append(f'(if (setq rv:e (handent "{d["h5"]}")) (progn (setq rv:d (entget rv:e)) (entmod (subst (cons 1 {s(novo)}) (assoc 1 rv:d) rv:d)) (princ "\\nCOMPAT_REV codigo {novo}")))')
    # legenda no canto de baixo à esquerda da maior viewport de cada folha (com máscara)
    leg = (f'{{\\fArial|b1;REVISÃO COMP-01 — COMPATIBILIZAÇÃO DAS REDES EXTERNAS ({DATA})}}\\P'
           'Vermelho (COMPAT-R01-NOVO) = traçado/caixa novos. Tracejado cinza (COMPAT-R01-REMOVIDO) = traçado/caixa que sai.\\P'
           'Nuvem Rnn = alteração em planta. Círculo azul Mnn = só profundidade (mergulho com conexões verticais), planta não muda.\\P'
           f'Itens: {itens_r[0] + " a " + itens_r[-1] if itens_r else "—"} (planta); {itens_m[0] + " a " + itens_m[-1] if itens_m else "—"} (profundidade). '
           f'Notas completas: {nome_novo}_notas.pdf / _itens.csv e quadro de notas no modelo.')
    por = collections.defaultdict(list)
    for v in vp:
        if v['layout'] and v['id'] != '1': por[v['layout']].append(v)
    for lay, vs in por.items():
        v = max(vs, key=lambda v: v['w'] * v['h'])
        x, y = v['x'] - v['w'] / 2 + 6.0, v['y'] - v['h'] / 2 + 6.0 + 16.0
        L.append(f'(entmake (list \'(0 . "MTEXT") \'(100 . "AcDbEntity") \'(67 . 1) (cons 410 {s(lay)}) \'(8 . "COMPAT-R01-NOTAS") \'(100 . "AcDbMText") '
                 f'(list 10 {x:.3f} {y:.3f} 0.0) \'(40 . 2.5) (cons 41 {min(330.0, 0.6 * v["w"]):.1f}) \'(71 . 1) (cons 1 {s(leg)}) \'(90 . 3) \'(63 . 7) \'(45 . 1.3)))')
    L.append('(princ)')
    return '\n'.join(L) + '\n', q


def lisp_pdf(base_pdf, layouts):
    b = base_pdf.replace(os.sep, '/')
    # mesma sequência do plotpdf.lsp da Prof. Áurea: A0, extensão ajustada, cores do desenho (sem tabela de estilo)
    L = ['(setvar "BACKGROUNDPLOT" 0) (setvar "FILEDIA" 0) (setvar "CMDECHO" 1)']
    for lay in layouts:
        L.append(f'(setvar "CTAB" {ex.lisp_str(lay)})')
        L.append(f'(command "_.-PLOT" "_Y" {ex.lisp_str(lay)} "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_E" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N" '
                 f'{ex.lisp_str(b + "_" + re.sub(r"[^A-Za-z0-9-]+", "_", lay) + ".pdf")} "_N" "_Y")')
        L.append(f'(princ "\\nCOMPAT_PDF {lay}")')
    L.append('(princ)')
    return '\n'.join(L) + '\n'


def pdf_notas(fn, titulo, linhas):
    with PdfPages(fn) as pdf:
        por_pag = 46
        for k in range(0, max(1, len(linhas)), por_pag):
            fig = plt.figure(figsize=(11.69, 8.27)); fig.text(0.04, 0.95, titulo, fontsize=11, weight='bold')
            y = 0.91
            for marca, nota in linhas[k:k + por_pag]:
                fig.text(0.04, y, marca, fontsize=7.5, weight='bold'); fig.text(0.09, y, nota[:230], fontsize=7.5); y -= 0.0185
            fig.text(0.04, 0.02, f'ETIB Catu — compatibilização das redes externas — {DATA} — página {k // por_pag + 1}', fontsize=7, color='#555')
            pdf.savefig(fig); plt.close(fig)


def main():
    so = next((a.split('=', 1)[1].split(',') for a in sys.argv if a.startswith('--so=')), None)
    os.makedirs(ANT, exist_ok=True); os.makedirs(os.path.join(SAI, 'PDF'), exist_ok=True)
    trab = ex.preparar('BD'); res = []
    for tag, w in trab.items():
        if so and tag not in so: continue
        if not (w['mud'] or w['cxs'] or w['mg']): continue
        nome = w['nome']; m = re.search(r'-R(\d\d)$', nome); atual = int(m.group(1)); nova = atual + 1
        nome_novo = nome[:-2] + f'{nova:02d}'
        fl, rs = ex.gerar(tag, w)                                  # LISP do modelo (+ _notas.csv com o nome antigo)
        notas_csv = os.path.join(SAI, f'{nome}_COMPAT-R01_notas.csv')
        linhas = [(r['marca'], r['nota']) for r in csv.DictReader(open(notas_csv, encoding='utf-8-sig'), delimiter=';')]
        itens_r = [x for x, _ in linhas if x.startswith('R')]; itens_m = [x for x, _ in linhas if x.startswith('M')]
        dxf = os.path.join(WRK, f'{nome}_COMPAT-R01.dxf')
        tx, vp, lays = ex_papel = dxf_papel(dxf)
        desc = 'COMPATIBILIZAÇÃO DAS REDES EXTERNAS (REVISÃO COMP-01)'          # uma linha só no quadro (125 mm)
        lp, q = lisp_papel(tag, nome_novo, atual, nova, tx, vp, sorted(set(itens_r)), sorted(set(itens_m)), desc)
        fpap = os.path.join(WRK, f'pad_{tag}.lsp'); open(fpap, 'w', encoding='ascii').write(lp)
        layouts = sorted({v['layout'] for v in vp if v['layout']})
        fpdf = os.path.join(WRK, f'pdf_{tag}.lsp'); open(fpdf, 'w', encoding='ascii').write(lisp_pdf(os.path.join(SAI, 'PDF', nome_novo), layouts))
        src = os.path.join(ex.ORIG, w['sub'], nome + '.dwg'); dst = os.path.join(SAI, nome_novo + '.dwg')
        shutil.copy2(src, dst)
        scr = os.path.join(WRK, f'pad_{tag}.scr')
        open(scr, 'w', encoding='ascii', newline='\r\n').write(
            'SECURELOAD\n0\nFILEDIA\n0\nEXPERT\n5\n_.AUDIT\n_Y\n(load "' + fl.replace('\\', '/') + '")\nCOMPATR01\n(load "' + fpap.replace('\\', '/') + '")\n'
            '_.QSAVE\n(load "' + fpdf.replace('\\', '/') + '")\n_.QUIT\n_Y\n')
        log = os.path.join(WRK, f'pad_{tag}_log.txt')
        r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(AQUI, 'run_acc.ps1'), '-Dwg', dst, '-Scr', scr, '-Log', log,
                            '-TimeoutSec', '900'], capture_output=True, text=True)
        b = open(log, 'rb').read() if os.path.exists(log) else b''
        out = (b.decode('utf-16-le', errors='replace') if b[1:2] == b'\x00' else b.decode('utf-8', errors='replace')).replace('\x00', '')
        marcas = [l.strip() for l in out.splitlines() if 'COMPAT_' in l and not l.strip().startswith('(')]
        bak = dst[:-4] + '.bak'
        if os.path.exists(bak): shutil.move(bak, os.path.join(ANT, os.path.basename(bak)))
        # notas: CSV e PDF com o nome novo; as cópias COMPAT-R01 de antes vão para _anteriores
        shutil.copy2(notas_csv, os.path.join(SAI, nome_novo + '_itens.csv'))
        pdf_notas(os.path.join(SAI, 'PDF', nome_novo + '_notas.pdf'), f'{nome_novo} — notas da revisão COMP-01 (compatibilização, {DATA})', linhas)
        for f in glob.glob(os.path.join(SAI, f'{nome}_COMPAT-R01*')): shutil.move(f, os.path.join(ANT, os.path.basename(f)))
        pdfs = sorted(glob.glob(os.path.join(SAI, 'PDF', nome_novo + '_*.pdf')))
        rs.update(dwg=dst, console=r.stdout.strip(), marcas=marcas, quadro={k: {'linha': f'{nova:02d}', 'ultima_antes': v['ultima']} for k, v in q.items()},
                  pdfs=[os.path.basename(p) for p in pdfs])
        print(tag, nome_novo, r.stdout.strip(), '|', '; '.join(marcas), '|', len(pdfs), 'PDF', flush=True)
        res.append(rs)
    import json
    json.dump(res, open(os.path.join(WRK, 'exec_padrao_resumo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
