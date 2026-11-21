# -*- coding: utf-8 -*-
"""Conferência das pranchas em PDF (item E do CHECKLIST.md) e da coerência PDF × DWG.
Lê o texto vetorial do PDF plotado pelo AutoCAD (PyMuPDF), já girado para a folha em paisagem, e compara com a revisão de origem
(a folha que serviu de base, na pasta _SUPERADAS do CDE ou no PROJETO_ORIGINAL).
Uso direto: python -X utf8 pdf_conf.py <pdf ou pasta> [--origem PASTA] [--sigla EXE]"""
import os, re, sys, glob, math, collections, datetime
import numpy as np
import pymupdf
from rev_comum import Revisao, folha

MM = 72 / 25.4
CARIMBO_W, CARIMBO_H = 190, 150                 # mm: faixa do carimbo da construtora (canto inferior direito)
COLUNA_W = 190                                  # mm: coluna de legendas/notas à direita
# folha desenhada em A1 e plotada ajustada no A0 (AF-002 da escola F, 23/10/2026): o carimbo e a coluna crescem junto. A escala
# sai da distância do rótulo "CONTRATADA" do carimbo da construtora à borda direita (521 pt numa folha A0 desenhada em A0)
REF_CONTRATADA_PT = 521.0
_K = 1.0
RX_COTA = re.compile(r'\b(C[TFSE])\.?\s*:?\s*(\d{2,3}[.,]\d{2})')
DIS_DISC = {'AF': ('AF',), 'AGF': ('AF',), 'ESG': ('ESG',), 'DRE': ('DRE',), 'EL': ('ELE',), 'IN': ('HID', 'SDAI'), 'INC': ('HID', 'SDAI'), 'IC': ('HID', 'SDAI')}
RX_PROF = re.compile(r'PROF\.?\s*(\d+[,.]\d+)\s*m\b|A\s+(\d+[,.]\d+)\s*m\s+DE\s+PROFUNDIDADE', re.I)
# 'XXX' solto é marcador de rascunho; dentro de um código (AA-CTR-MUN-LOC-ETIB-…, o código da lista mestra da escola C) não é
RX_PROCESSO = re.compile(r'PR[EÉ][- ]?COMPAT|PRECLASH|CLASH|CONFLITO|INTERFER[EÊ]NCIA|MERGULHO|NUVEM|RASCUNHO|SUBSTITU[IÍ]D|CANCELAD|'
                         r'REVIS[AÃ]O INTERNA|N[AÃ]O EMITIR|PRELIMINAR|\bCP-\d{2}\b|VER RELAT[OÓ]RIO|A DEFINIR|A CONFIRMAR|\?\?|(?<![-\w])XXX+(?![-\w])|'
                         r'\bTESTE\b|\bTODO\b|CLAUDE|\bSCRIPT\b|\bTHREAD\b|IFC_R\d|PRECLASH', re.I)
RX_LAYER_RUIM = re.compile(r'NUVEM|CLOUD|COMPAT|PRECLASH|SUBSTITU|RASCUNHO|CANCEL|R\d\d-NOVO|R\d\d-NOTA|REV-?INT|CONFLIT|CLASH|TEMP\b|TESTE', re.I)
RX_TAG = re.compile(r'(Ø|ø|DN\s*\d|\d+\s*mm\b|\d+(?:\.\d/\d)?"|\bPVC\b|PEAD|PPR|\bC[TFSE]\b|\bGI\b|i\s*=|\b[A-Z]{1,5}-[A-Z]?-?\d{1,3}(?:\.\d+)?\b|'
                    r'\b(CX|PV|PVE|CI|CG|CP|CA|PI|QD|QGBT|QDLT|IE|SDAI|AH)[-\s]?\w*\d)', re.I)
CARIMBO_QG = ('CONTRATADA', 'CONTRATANTE', 'DISCIPL_SETOR-FOLHA_REV', 'RESP. PROJETO', 'CAU/CREA', 'COORDENADOR', 'DESENHISTA', 'ARQUIVO', 'ESCALA', 'ANO DO CTR')


def spans(pdf, chars=False):
    """lista de (texto, Rect em pontos na folha girada, tamanho[, caixas dos caracteres]) e a página."""
    d = pymupdf.open(pdf); p = d[0]; M = p.rotation_matrix
    out = []
    for b in p.get_text('rawdict' if chars else 'dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if chars:
                    t = ''.join(c['c'] for c in s['chars']).strip()
                    cx = [pymupdf.Rect(c['bbox']) * M for c in s['chars'] if c['c'].strip()]
                    if t: out.append((t, pymupdf.Rect(s['bbox']) * M, s['size'], cx))
                else:
                    t = s['text'].strip()
                    if t: out.append((t, pymupdf.Rect(s['bbox']) * M, s['size']))
    # só a folha com o carimbo da construtora define a escala; a de origem (carimbo do projetista) é lida com a escala da revisada que a chamou
    global _K
    if any('DISCIPL_SETOR' in t for t, *_ in out):
        xs = [r.x0 for t, r, *_ in out if t.startswith('CONTRATADA') and r.x0 > p.rect.width / 2]
        k = (p.rect.width - max(xs)) / REF_CONTRATADA_PT if xs else 1.0
        _K = k if k > 1.2 else 1.0
    return out, p, d


def regiao(r, W, H):
    if r.x0 > W - CARIMBO_W * MM * _K and r.y0 > H - CARIMBO_H * MM * _K: return 'carimbo'
    if r.x0 > W - COLUNA_W * MM * _K: return 'legenda'
    return 'desenho'


def _num(s):
    return float(s.replace(',', '.'))


def escala(sp, W, H):
    """escala do carimbo; se o carimbo diz "EM PLANTA"/"INDICADA", a mais comum nos títulos do desenho."""
    for t, r, *_ in sp:
        m = re.fullmatch(r'1\s*:\s*(\d+)', t)
        if m and regiao(r, W, H) == 'carimbo': return int(m.group(1))
    c = collections.Counter(int(m.group(1)) for t, r, *_ in sp for m in [re.search(r'\b1\s*:\s*(\d{2,4})\b', t)] if m and regiao(r, W, H) != 'carimbo')
    return c.most_common(1)[0][0] if c else None


def quadro_revisoes(sp, W, H):
    """[(rev, data, descrição)] do quadro de revisões do carimbo, de cima para baixo (sobe a partir do cabeçalho "REV.")."""
    cab = [r for t, r, *_ in sp if t.upper().startswith('REV.') and r.x0 > W - CARIMBO_W * MM * _K]
    if not cab: return []
    yc = max(cab, key=lambda r: r.y0).y0
    x0 = W - CARIMBO_W * MM * _K
    lin = collections.defaultdict(list)
    for t, r, *_ in sp:
        if r.x0 > x0 and yc - 120 * MM * _K < r.y0 < yc: lin[round(r.y0 / MM * 2) / 2].append((r.x0, t))
    out = []; yant = yc
    for y in sorted(lin, reverse=True):
        it = sorted(lin[y])
        # coluna REV. até 30 mm da borda da faixa do carimbo: o carimbo da construtora da escola G, plotado pela janela A0, tem 170 mm e a coluna
        # fica a 22 mm (com 20 mm o quadro "não era encontrado")
        if not (it and re.fullmatch(r'\d{2}', it[0][1]) and it[0][0] < x0 + 30 * MM * _K and len(it) >= 3): continue
        if yant - y * MM > 9 * MM * _K: break
        data = next((t for _, t in it if re.fullmatch(r'[A-Z]{3}/\d{4}|\d{2}/\d{2}/\d{4}', t)), '')
        out.append((int(it[0][1]), data, ' '.join(t for _, t in it[1:] if t != data))); yant = y * MM
    return out[::-1]


def origem_da_folha(pdf, pastas_origem):
    """revisão de base da mesma folha: a de menor revisão sem sufixo em _SUPERADAS do CDE, senão a do PROJETO_ORIGINAL."""
    f = folha(pdf)
    if not f: return None
    cand = []
    for pasta in pastas_origem:
        for fn in glob.glob(os.path.join(pasta, '**', '*.pdf'), recursive=True):
            g = folha(fn)
            if g and g['base'] == f['base'] and g['rev'] < f['rev']: cand.append((g['rev'], fn))
        if cand: break
    return min(cand)[1] if cand else None


def _sobre(cn, cx2, frac=0.25):
    """alguma caixa de caractere da nota (cn) cobre mais de frac de uma caixa de caractere do outro texto (cx2)?"""
    for a in cn:
        for b in cx2:
            i = a & b
            if not i.is_empty and i.get_area() > frac * min(a.get_area(), b.get_area()): return True
    return False


def cotas(sp, W, H):
    """[(tipo CT/CF/CS/CE, valor, centro)] das etiquetas de cota das caixas no desenho."""
    out = []
    for t, r, *_ in sp:
        if regiao(r, W, H) != 'desenho': continue
        for m in RX_COTA.finditer(t):
            out.append((m.group(1).upper(), _num(m.group(2)), ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)))
    return out


def conferir_pdf(rv, pdf, prof_max, origem=None, excecoes=(), recortes=None, cotas_decl=()):
    """excecoes: [dict(disc=(...), ate=m, fonte=texto)] aceitas pelo dono do projeto (vale para as notas da folha das disciplinas citadas)."""
    nome = os.path.basename(pdf); f = folha(pdf); curto = f['curto'] + f' R{f["rev"]:02d}' if f else nome
    sp, p, d = spans(pdf, chars=True); W, H = p.rect.width, p.rect.height
    # E1 formato
    wmm, hmm = W / MM, H / MM
    if len(d) != 1: rv.add('E1', 'PENDENCIA', curto, '-', f'PDF com {len(d)} páginas (uma folha por PDF)', 'E1 formato')
    if abs(max(wmm, hmm) - 1189) > 3 or abs(min(wmm, hmm) - 841) > 3:
        rv.add('E1', 'PENDENCIA', curto, '-', f'folha {wmm:.0f} × {hmm:.0f} mm (esperado A0 1189 × 841)', 'E1 formato A0')
    else:
        rv.ev('E1', f'{curto}: A0 {wmm:.0f} × {hmm:.0f} mm')
    # E2 carimbo da construtora
    txt_car = ' '.join(t for t, r, *_ in sp if regiao(r, W, H) == 'carimbo')
    faltam = [k for k in CARIMBO_QG if k not in txt_car]
    imgs = [im for im in p.get_image_info() if regiao(pymupdf.Rect(im['bbox']) * p.rotation_matrix, W, H) == 'carimbo']
    if faltam or len(imgs) < 3:
        rv.add('E2', 'PENDENCIA', curto, 'carimbo', f'carimbo da construtora as built incompleto ou ausente (faltam {", ".join(faltam) or "-"}; {len(imgs)} logos)',
               'E2 carimbo da construtora as built')
    else:
        rv.ev('E2', f'{curto}: carimbo da construtora as built no PDF (campos e {len(imgs)} logos)')
    # E3 revisão coerente
    esc = escala(sp, W, H)
    if f:
        stem = f['stem']
        if stem not in txt_car.replace(' ', ''):
            rv.add('E3', 'PENDENCIA', curto, 'carimbo', f'código da folha no carimbo diferente do nome do arquivo ({stem})', 'E3 código = arquivo')
        if (stem + '.DWG').upper() not in txt_car.upper().replace(' ', ''):
            rv.add('E3', 'PENDENCIA', curto, 'carimbo', f'campo ARQUIVO não traz {stem}.DWG', 'E3 código = arquivo')
        m = re.search(r'\b[A-Z]+_[A-Z0-9]+-\d{3}_R(\d{2})\b', txt_car)
        if m and int(m.group(1)) != f['rev']:
            rv.add('E3', 'PENDENCIA', curto, 'carimbo', f'código curto com R{m.group(1)} e arquivo R{f["rev"]:02d}', 'E3 revisão coerente')
        qr = quadro_revisoes(sp, W, H)
        if not qr:
            rv.add('E3', 'PENDENCIA', curto, 'quadro de revisões', 'quadro de revisões não encontrado', 'E3 revisão coerente')
        else:
            topo = qr[0]
            if topo[0] != f['rev']:
                rv.add('E3', 'PENDENCIA', curto, 'quadro de revisões', f'linha mais nova é {topo[0]:02d}, arquivo é R{f["rev"]:02d}', 'E3 revisão coerente')
            nums = [r for r, _, _ in qr]
            if len(set(nums)) != len(nums) or sorted(set(nums), reverse=True) != list(range(max(nums), min(nums) - 1, -1)):
                rv.add('E3', 'OBSERVACAO', curto, 'quadro de revisões',
                       f'numeração das linhas {", ".join(f"{n:02d}" for n in nums)} (repetida ou pulada; conferir se já vinha do original)', 'E3 revisão coerente')
            rv.ev('E3', f'{curto}: escala 1:{esc}; quadro ' + '; '.join(f'{n:02d} {d_} {ds[:38]}' for n, d_, ds in qr[:2]))
    else:
        rv.add('A5', 'PENDENCIA', nome, '-', 'nome do arquivo fora do padrão da lista mestra', 'A5 nome padrão')
    discs = DIS_DISC.get(f['dis'], ()) if f else ()
    exc = next((e for e in excecoes if set(e.get('disc', ())) & set(discs)), None)
    # E4/E5/E6 notas de profundidade
    notas = []; tam_nota = []
    for t, r, s, cx in sp:
        m = RX_PROF.search(t)
        if m and regiao(r, W, H) == 'desenho':
            notas.append((t, r, _num(m.group(1) or m.group(2)), cx)); tam_nota.append(s)
    raio = (15000.0 / esc * MM) if esc else None              # 15 m no papel
    if raio:
        usados = set()
        for i, (t, r, v, _) in enumerate(notas):
            if i in usados: continue
            c = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            grupo = [j for j, (t2, r2, v2, _) in enumerate(notas) if v2 == v and math.hypot((r2.x0 + r2.x1) / 2 - c[0], (r2.y0 + r2.y1) / 2 - c[1]) < raio]
            if len(grupo) >= 2:
                usados.update(grupo)
                rv.add('E4', 'PENDENCIA' if len(grupo) >= 3 else 'OBSERVACAO', curto,
                       f'x {c[0] / MM:.0f} mm, y {c[1] / MM:.0f} mm da folha',
                       f'{len(grupo)} notas "{t}" a menos de 15 m uma da outra (uma nota por trecho; se forem redes diferentes, ok)',
                       'E4 uma nota de profundidade por trecho')
    for t, r, v, _ in notas:
        if v > prof_max + 0.005:
            if exc and v <= exc.get('ate', 99):
                rv.add('E5', 'OBSERVACAO', curto, f'x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm', f'nota "{t}" acima de {prof_max:.2f} m, aceita ({exc["fonte"]})',
                       'E5 nota ≤ profundidade máxima')
            else:
                rv.add('E5', 'PENDENCIA', curto, f'x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm', f'nota "{t}" acima da profundidade máxima {prof_max:.2f} m',
                       'E5 nota ≤ profundidade máxima')
    n_sob = 0
    for (t, r, v, cn), sn in zip(notas, tam_nota):
        for t2, r2, s2, c2 in sp:
            if r2 == r or not r2.intersects(r): continue
            if _sobre(cn, c2):
                # só encosta na ponta de um texto miúdo da base (≤ metade da nota e ≤ 25% dos caracteres cobertos) = observação
                cobertos = sum(1 for b in c2 if _sobre(cn, [b]))
                leve = s2 <= 0.5 * sn and cobertos <= 0.25 * max(len(c2), 1)
                n_sob += 0 if leve else 1
                rv.add('E6', 'OBSERVACAO' if leve else 'PENDENCIA', curto, f'x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm',
                       f'nota "{t}" ' + (f'encosta em {cobertos} de {len(c2)} letras do texto miúdo "{t2[:30]}" da base (nota legível)' if leve
                                         else f'escrita por cima de "{t2[:30]}"'), 'E6 nota legível')
                break
    rv.ev('E4', f'{curto}: {len(notas)} notas de profundidade' + (f' (valores {", ".join(sorted({f"{v:.2f}" for _, _, v, _ in notas}))})' if notas else ''))
    rv.ev('E6', f'{curto}: {n_sob} notas sobre outro texto')
    # textos que existem na revisada e não na origem (só eles podem trazer nota de processo)
    norm = lambda t: re.sub(r'\s+', '', t).upper()
    if origem:
        so, po, do = spans(origem); Wo, Ho = po.rect.width, po.rect.height
        antigos = collections.Counter(norm(t) for t, *_ in so)
    else:
        so = None; antigos = collections.Counter()
    # E8 processo e layers
    for t, r, *_ in sp:
        if not RX_PROCESSO.search(t) or antigos[norm(t)]: continue
        reg = regiao(r, W, H)
        if reg == 'carimbo' and re.search(r'COMPATIBILIZA', t, re.I) and not re.search(r'PR[EÉ]', t, re.I): continue
        rv.add('E8', 'PENDENCIA', curto, f'{reg}, x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm', f'texto de processo/rascunho na folha: "{t[:60]}"',
               'E8 sem nota de processo')
    ocg = sorted({v['name'] for v in d.get_ocgs().values()})
    ruins = [n for n in ocg if RX_LAYER_RUIM.search(n)]
    if ruins:
        rv.add('E8', 'PENDENCIA', curto, 'layers do PDF', f'layer de revisão/rascunho na folha: {", ".join(ruins[:6])}', 'E8 sem nuvem/rascunho')
    rv.ev('E8', f'{curto}: {len(ocg)} layers, nenhum de rascunho' if not ruins else f'{curto}: layers suspeitos {ruins[:4]}')
    # E7 etiquetas e cotas em relação à revisão de origem
    if so is not None:
        A = collections.Counter(norm(t) for t, r, *_ in so if regiao(r, Wo, Ho) == 'desenho' and RX_TAG.search(t) and not RX_PROF.search(t))
        B = collections.Counter(norm(t) for t, r, *_ in sp if regiao(r, W, H) == 'desenho' and RX_TAG.search(t) and not RX_PROF.search(t))
        falta = A - B; n = sum(falta.values())
        if n:
            ex = ', '.join(f'"{k}"' + (f' ×{v}' if v > 1 else '') for k, v in falta.most_common(8))
            rv.add('E7', 'OBSERVACAO', curto, f'comparada com {os.path.basename(origem)}',
                   f'{n} etiqueta(s) da origem não aparecem mais ({ex}): conferir nos recortes se saíram junto com o trecho removido', 'E7 tags visíveis')
        rv.ev('E7', f'{curto}: {sum(B.values())} etiquetas na revisada × {sum(A.values())} na origem ({os.path.basename(origem)}); faltam {n}')
        # cotas de caixa alteradas (gravidade mantém CT/CF/CS/CE do projeto)
        co, cn_ = cotas(so, Wo, Ho), cotas(sp, W, H)
        for tp, v, c in co:
            mesmo = [x for x in cn_ if x[0] == tp and abs(x[1] - v) < 0.005 and math.hypot(x[2][0] - c[0], x[2][1] - c[1]) < 40 * MM]
            if mesmo: continue
            perto = [x for x in cn_ if x[0] == tp and math.hypot(x[2][0] - c[0], x[2][1] - c[1]) < 3 * MM]
            if perto:
                decl = next((d for d in cotas_decl if d['folha'] in curto and d['tipo'] == tp and abs(d['de'] - v) < 0.005
                             and abs(d['para'] - perto[0][1]) < 0.005), None)
                if decl:
                    rv.add('E7', 'OBSERVACAO', curto, f'x {c[0] / MM:.0f} mm, y {c[1] / MM:.0f} mm',
                           f'cota de caixa alterada {tp} {v:.2f} → {perto[0][1]:.2f}, declarada no envio ({decl["fonte"]})', 'D7/E7 cotas das caixas = projeto')
                else:
                    rv.add('E7', 'PENDENCIA', curto, f'x {c[0] / MM:.0f} mm, y {c[1] / MM:.0f} mm',
                           f'cota de caixa alterada: {tp} {v:.2f} → {perto[0][1]:.2f} (gravidade mantém as cotas do projeto; se aprovado, declarar no envio)',
                           'D7/E7 cotas das caixas = projeto')
            else:
                rv.add('E7', 'OBSERVACAO', curto, f'x {c[0] / MM:.0f} mm, y {c[1] / MM:.0f} mm', f'etiqueta {tp} {v:.2f} da origem não achada na revisada',
                       'E7 tags visíveis')
        eo = escala(so, Wo, Ho)
        if eo and esc and eo != esc:
            rv.add('E3', 'OBSERVACAO', curto, 'carimbo', f'escala 1:{esc} diferente da origem 1:{eo}', 'E3 carimbo coerente')
        if recortes: recortar(origem, pdf, recortes)
        conferir_tipo_linha(rv, pdf, origem)
    else:
        rv.add('E7', 'OBSERVACAO', curto, '-', 'revisão de origem não encontrada para comparar as etiquetas', 'E7 tags visíveis')
    conferir_grafico(rv, pdf, origem, sp)
    return notas


# E11 padrão gráfico (PDCA A3, dono do projeto 22/10/2026). A rede existente/de cadastro sai numa cor bem visível (nada de cinza: "ficou ruim de
# enxergar") que a legenda da folha não use para outro item, ByLayer, e está na legenda; cor ou elemento novo nosso entra na legenda;
# texto na altura padrão da folha; anotação nossa (texto que não existia na origem) nunca maior que o texto do projetista.
# COR_EXISTENTE = nome de uma cor obrigatória em CORES; None = qualquer cor visível que não repita outro item da legenda (regra atual).
RX_LAYER_EXISTENTE = re.compile(r'EXISTENT|CADASTR|\bEXIST\b|\bEX[-_ ]', re.I)
RX_LAYER_REDE = re.compile(r'COND|TUB|REDE|ELETROD|CABO|\bAF\b|ESG|DRE|PLUV|HID|SDAI|\bAP\b|\bTQ\b', re.I)
COR_EXISTENTE = None
CORES = {'cinza': lambda c: max(c) - min(c) <= 0.06 and 0.25 <= sum(c) / 3 <= 0.85}
TOL_ALTURA = 1.15          # 15 % acima do texto padrão ainda passa (fontes do AutoCAD variam no PDF)
APAGADA = lambda c: max(c) - min(c) <= 0.08 or min(c) >= 0.85          # cinza/preto/branco ou clara demais: não destaca a rede


def legenda(p, sp=None):
    """itens da legenda da folha: [(cor, texto)] — amostra de linha colorida (6 a 40 mm de largura, até 4 mm de altura) na coluna da
    direita com o texto mais perto à direita na mesma linha."""
    M = p.rotation_matrix; W, H = p.rect.width, p.rect.height
    if sp is None: sp = spans_pagina(p)
    tx = [(t, r) for t, r, *_ in sp if regiao(r, W, H) == 'legenda']
    vistos, out = set(), []
    for d in p.get_drawings():
        r = d['rect'] * M; c = d.get('color')
        if not c or regiao(r, W, H) != 'legenda' or not (6 * MM <= r.width <= 40 * MM and r.height <= 4 * MM): continue
        c = tuple(round(x, 2) for x in c)
        if APAGADA(c): continue
        yc = (r.y0 + r.y1) / 2
        t = min(((rt.x0 - r.x1, t_) for t_, rt in tx if abs((rt.y0 + rt.y1) / 2 - yc) < 3 * MM and -1 * MM <= rt.x0 - r.x1 < 80 * MM), default=None)
        if not t or (c, t[1]) in vistos: continue
        vistos.add((c, t[1])); out.append((c, t[1]))
    return out


def spans_pagina(p):
    M = p.rotation_matrix; out = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s_ in l['spans']:
                if s_['text'].strip(): out.append((s_['text'].strip(), pymupdf.Rect(s_['bbox']) * M, s_['size']))
    return out


def _textos(p):
    """[(texto, Rect na folha girada, tamanho, cor RGB 0-1)] da área de desenho."""
    M = p.rotation_matrix; W, H = p.rect.width, p.rect.height; out = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip(); r = pymupdf.Rect(s['bbox']) * M
                if t and regiao(r, W, H) == 'desenho':
                    c = s['color']; out.append((t, r, round(s['size'], 1), ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)))
    return out


def _mesma_cor(a, b, tol=0.02):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def _cores_por_layer(p):
    """{layer do PDF: Counter(cor do traço)} da área de desenho."""
    M = p.rotation_matrix; W, H = p.rect.width, p.rect.height
    out = collections.defaultdict(collections.Counter)
    for d in p.get_drawings():
        r = d['rect'] * M
        if regiao(r, W, H) != 'desenho': continue
        c = d.get('color') or d.get('fill')
        if c: out[d.get('layer') or ''][tuple(round(x, 2) for x in c)] += 1
    return out


def _cor_existente(lay):
    """{layer de cadastro: cor dominante}."""
    return {n: cs.most_common(1)[0][0] for n, cs in lay.items() if n and RX_LAYER_EXISTENTE.search(n) and cs}


def _tamanho_padrao(txt, cores_ex):
    """altura de texto padrão da folha: o tamanho mais comum das etiquetas de rede do projetista (diâmetro, material, declividade,
    cota), fora as da rede existente; sem etiqueta, o tamanho mais comum da área de desenho."""
    tag = collections.Counter(s for t, r, s, c in txt if RX_TAG.search(t) and not any(_mesma_cor(c, e) for e in cores_ex))
    if not tag: tag = collections.Counter(s for t, r, s, c in txt if len(t) >= 2)
    return tag.most_common(1)[0][0] if tag else None


def _sobrepostos(sp, W, H, frac=0.25):
    """pares (i, j) de textos da área de desenho com caracteres um por cima do outro (grade de 20 mm para não comparar tudo com tudo)."""
    idx = [i for i, (t, r, *_) in enumerate(sp) if regiao(r, W, H) == 'desenho']
    grade = collections.defaultdict(list); passo = 20 * MM
    for i in idx:
        r = sp[i][1]
        for gx in range(int(r.x0 // passo), int(r.x1 // passo) + 1):
            for gy in range(int(r.y0 // passo), int(r.y1 // passo) + 1): grade[gx, gy].append(i)
    pares = set()
    for lst in grade.values():
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                i, j = lst[a], lst[b]
                if (min(i, j), max(i, j)) in pares or not sp[i][1].intersects(sp[j][1]): continue
                if _sobre(sp[i][3], sp[j][3], frac): pares.add((min(i, j), max(i, j)))
    return pares


def conferir_grafico(rv, pdf, origem=None, sp=None):
    """E11 (cor e altura do texto da rede existente; anotação nova não maior que o texto do projetista) e E6 na folha inteira
    (texto sobre texto que não estava assim na origem)."""
    f = folha(pdf); curto = (f['curto'] + f' R{f["rev"]:02d}') if f else os.path.basename(pdf)
    if sp is None: sp, p, d = spans(pdf, chars=True)
    else: d = pymupdf.open(pdf); p = d[0]
    W, H = p.rect.width, p.rect.height
    norm = lambda t: re.sub(r'\s+', '', t).upper()
    txt = _textos(p); lay = _cores_por_layer(p); ex = _cor_existente(lay)
    if origem:
        so, po, _ = spans(origem, chars=True); Wo, Ho = po.rect.width, po.rect.height
        txo = _textos(po); exo = _cor_existente(_cores_por_layer(po))
        padrao = _tamanho_padrao(txo, list(exo.values()))
    else:
        so = None; padrao = _tamanho_padrao(txt, list(ex.values()))
    # rede existente: cor do layer de cadastro e altura dos textos dessa cor
    cores_novas = {c for n, cs in lay.items() if n and n not in ex and RX_LAYER_REDE.search(n) for c, _ in cs.most_common(2)}
    leg = legenda(p, sp)
    for nome, cor in ex.items():
        if COR_EXISTENTE and not CORES[COR_EXISTENTE](cor):
            rv.add('E11', 'PENDENCIA', curto, f'layer "{nome}"', f'rede existente na cor RGB {cor}, fora do padrão ({COR_EXISTENTE}, ByLayer)',
                   'E11 rede existente no padrão gráfico')
        elif not COR_EXISTENTE and APAGADA(cor):
            rv.add('E11', 'PENDENCIA', curto, f'layer "{nome}"', f'rede existente em cor apagada (RGB {cor}: cinza, preto ou clara demais); '
                   'usar uma cor bem visível que a legenda não use', 'E11 rede existente visível')
        if any(_mesma_cor(cor, c) for c in cores_novas):
            rv.add('E11', 'PENDENCIA', curto, f'layer "{nome}"', f'rede existente na mesma cor de uma rede nova (RGB {cor}): não se distingue',
                   'E11 rede existente no padrão gráfico')
        # legenda: a cor da existente está lá (num item de rede existente) e não repete a de outro item
        mesmos = [t for c, t in leg if _mesma_cor(c, cor, 0.04)]
        outros = [t for t in mesmos if not RX_LAYER_EXISTENTE.search(t)]
        if outros:
            rv.add('E11', 'PENDENCIA', curto, 'legenda', f'cor da rede existente (RGB {cor}) repete a do item "{outros[0][:45]}" da legenda',
                   'E11 cor sem repetir a legenda')
        if not any(RX_LAYER_EXISTENTE.search(t) for t in mesmos):
            rv.add('E11', 'PENDENCIA', curto, 'legenda', f'rede existente (layer "{nome}", RGB {cor}) não está na legenda da folha',
                   'E11 legenda completa')
        # o PDF não guarda o layer do texto: conta os textos da mesma cor; vale a altura mais comum (texto da base na mesma cor não pesa)
        tam = collections.Counter(s for t, r, s, c in txt if _mesma_cor(c, cor))
        if tam and padrao:
            alt, n = tam.most_common(1)[0]
            if n >= 3 and alt > padrao * TOL_ALTURA:            # 1 ou 2 textos na cor do cadastro não dizem a altura das etiquetas dele
                rv.add('E11', 'PENDENCIA', curto, f'layer "{nome}"', f'{n} texto(s) da rede existente com {alt:.1f} pt, maiores que as etiquetas '
                       f'do projetista ({padrao:.1f} pt)', 'E11 texto na altura padrão')
        rv.ev('E11', f'{curto}: rede existente "{nome}" RGB {cor}; textos {dict(tam.most_common(3))} pt (etiquetas do projetista {padrao} pt)')
    # cor nova na folha (não existia na origem) tem de estar na legenda: elemento ou rede que nós acrescentamos
    if origem:
        cores_o = {c for cs in _cores_por_layer(po).values() for c in cs}
        for nome, cs in lay.items():
            cor = cs.most_common(1)[0][0]
            if APAGADA(cor) or any(_mesma_cor(cor, c) for c in cores_o) or any(_mesma_cor(cor, c, 0.04) for c, _ in leg): continue
            if sum(cs.values()) < 10 and not RX_LAYER_REDE.search(nome or ''): continue      # 3 traços num layer de detalhe da base não é elemento novo
            rv.add('E11', 'PENDENCIA', curto, f'layer "{nome or "-"}"', f'cor nova na folha (RGB {cor}, {sum(cs.values())} traços) sem item na legenda',
                   'E11 legenda completa')
    rv.ev('E11', f'{curto}: legenda com {len(leg)} itens de cor' + (f' ({"; ".join(t[:25] for _, t in leg[:6])})' if leg else ''))
    # anotação nossa: texto da área de desenho que não existia na origem
    if so is not None and padrao:
        antigos = collections.Counter(norm(t) for t, *_ in so)
        novos = [(t, r, s) for t, r, s, c in txt if not antigos[norm(t)]]
        grandes = [(t, r, s) for t, r, s in novos if s > padrao * TOL_ALTURA]
        for t, r, s in grandes[:6]:
            rv.add('E11', 'PENDENCIA', curto, f'x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm',
                   f'texto novo "{t[:40]}" com {s:.1f} pt, maior que as etiquetas do projetista ({padrao:.1f} pt)', 'E11 anotação nossa ≤ texto do projetista')
        if len(grandes) > 6:
            rv.add('E11', 'PENDENCIA', curto, '-', f'mais {len(grandes) - 6} textos novos maiores que as etiquetas do projetista',
                   'E11 anotação nossa ≤ texto do projetista')
        rv.ev('E11', f'{curto}: {len(novos)} textos novos, {len(grandes)} acima de {padrao * TOL_ALTURA:.1f} pt; {len(ex)} layer(s) de rede existente')
    elif not ex:
        rv.ev('E11', f'{curto}: sem layer de rede existente; sem origem para comparar as anotações')
    # E6 na folha inteira: sobreposição nova (não estava na origem) = pendência; a que já vinha do projetista = observação (uma linha).
    # As notas de profundidade já são conferidas acima (E6 da nota).
    # "já vinha assim" = o mesmo par de textos sobreposto na origem, ou qualquer sobreposição da origem a menos de 5 mm do mesmo lugar
    # (o PDF de cada plotagem quebra os textos em pedaços diferentes: "PVC ø40" num pedaço só na origem e em dois na revisada)
    pares = _sobrepostos(sp, W, H)
    meio = lambda S, i, j: ((S[i][1].x0 + S[i][1].x1 + S[j][1].x0 + S[j][1].x1) / 4, (S[i][1].y0 + S[i][1].y1 + S[j][1].y0 + S[j][1].y1) / 4)
    po_ = _sobrepostos(so, Wo, Ho) if so is not None else set()
    velhos = {tuple(sorted((norm(so[i][0]), norm(so[j][0])))) for i, j in po_}
    lugares = np.array([meio(so, i, j) for i, j in po_]) if po_ else np.zeros((0, 2))
    ja_vinha = lambda i, j: (tuple(sorted((norm(sp[i][0]), norm(sp[j][0])))) in velhos
                             or (len(lugares) and np.min(np.hypot(*(lugares - np.array(meio(sp, i, j))).T)) < 5 * MM))
    novos_p = [(i, j) for i, j in pares if not ja_vinha(i, j) and not (RX_PROF.search(sp[i][0]) or RX_PROF.search(sp[j][0]))]
    for i, j in novos_p[:8]:
        r = sp[i][1]
        rv.add('E6', 'PENDENCIA', curto, f'x {r.x0 / MM:.0f} mm, y {r.y0 / MM:.0f} mm', f'"{sp[i][0][:30]}" escrito por cima de "{sp[j][0][:30]}"'
               + ('' if so is not None else ' (sem origem para saber se já vinha do projetista)'), 'E6 nada sobreposto na folha')
    if len(novos_p) > 8:
        rv.add('E6', 'PENDENCIA', curto, '-', f'mais {len(novos_p) - 8} pares de textos sobrepostos', 'E6 nada sobreposto na folha')
    ja = len(pares) - len(novos_p)
    if ja and so is not None:
        rv.add('E6', 'OBSERVACAO', curto, '-', f'{ja} par(es) de textos sobrepostos que já vinham assim na revisão de origem', 'E6 nada sobreposto na folha')
    rv.ev('E6', f'{curto}: folha inteira, {len(pares)} pares de textos sobrepostos ({len(novos_p)} novos)')


def _linhas_por_cor(pdf):
    """{cor: [(x0, y0, x1, y1) em pontos da folha girada]} das linhas retas da área de desenho (o AutoCAD plota o tracejado como pedaços)."""
    p = pymupdf.open(pdf)[0]; M = p.rotation_matrix; W, H = p.rect.width, p.rect.height
    out = collections.defaultdict(list)
    for d in p.get_drawings():
        c = tuple(round(x, 2) for x in (d.get('color') or (0, 0, 0)))
        for it in d['items']:
            if it[0] == 'l':
                a = it[1] * M; b = it[2] * M
                if regiao(pymupdf.Rect(a, a), W, H) == 'desenho': out[c].append((a.x, a.y, b.x, b.y))
    return out


def conferir_tipo_linha(rv, pdf, origem):
    """E9: cor de rede que na origem só tem tracejado (pedaços curtos) e na revisada ganhou linha contínua = traçado redesenhado sem o tipo de linha."""
    f = folha(pdf); curto = (f['curto'] + f' R{f["rev"]:02d}') if f else os.path.basename(pdf)
    A = _linhas_por_cor(origem); B = _linhas_por_cor(pdf)
    n = 0
    for c, la in A.items():
        if len(la) < 20 or c in ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)): continue
        L0 = max(math.hypot(x1 - x0, y1 - y0) for x0, y0, x1, y1 in la)
        if L0 > 15 * MM: continue                                   # cor com linha contínua na origem: não é rede tracejada
        # cor que quase não aparece na origem (setas, pontas: < 10 cm de traço na folha toda) não é rede: a diferença vem da
        # tabela de plotagem (CTB) do projetista, que troca a cor na plotagem (AGF/DRE de escola B: 50 pedaços de 0,3 mm)
        if sum(math.hypot(x1 - x0, y1 - y0) for x0, y0, x1, y1 in la) < 100 * MM: continue
        longos = [s for s in B.get(c, []) if math.hypot(s[2] - s[0], s[3] - s[1]) > max(2 * L0, 15 * MM)]
        grupos = []
        for s in longos:
            m = ((s[0] + s[2]) / 2, (s[1] + s[3]) / 2)
            g = next((g for g in grupos if math.hypot(g[0][0] - m[0], g[0][1] - m[1]) < 60 * MM), None)
            if g: g[1].append(s)
            else: grupos.append((m, [s]))
        for m, ss in grupos:
            n += 1
            comp = sum(math.hypot(s[2] - s[0], s[3] - s[1]) for s in ss) / MM
            rv.add('E9', 'PENDENCIA', curto, f'x {m[0] / MM:.0f} mm, y {m[1] / MM:.0f} mm',
                   f'trecho redesenhado com linha contínua ({comp:.0f} mm no papel) onde a rede é tracejada (cor RGB {c})', 'E9 traçado no tipo de linha da rede')
    rv.ev('E9', f'{curto}: {n} trecho(s) redesenhado(s) sem o tracejado da rede')


def recortar(fo, fn, pasta, nmax=10, dpi_baixo=30):
    """recortes lado a lado (origem | revisada) das regiões que mudaram, para a conferência visual (E8, E9, E10)."""
    os.makedirs(pasta, exist_ok=True)
    def img(f):
        p = pymupdf.open(f)[0]; pix = p.get_pixmap(dpi=dpi_baixo, colorspace=pymupdf.csGRAY)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width), p
    A, pa = img(fo); B, pb = img(fn)
    h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    D = np.abs(A[:h, :w].astype(int) - B[:h, :w].astype(int)) > 60
    blk = 40; Hh, Ww = h // blk, w // blk
    Mx = D[:Hh * blk, :Ww * blk].reshape(Hh, blk, Ww, blk).sum(axis=(1, 3))
    xcar = int((w - CARIMBO_W * dpi_baixo / 25.4) // blk)
    cand = sorted(((int(Mx[i, j]), i, j) for i in range(Hh) for j in range(Ww) if Mx[i, j] > 3 and j < xcar), reverse=True)
    feitos = []
    for n, i, j in cand:
        if any(abs(i - a) <= 2 and abs(j - b) <= 2 for a, b in feitos): continue
        feitos.append((i, j))
        if len(feitos) >= nmax: break
    esc = 72 / dpi_baixo; base = os.path.splitext(os.path.basename(fn))[0]
    for k, (i, j) in enumerate(feitos):
        r = pymupdf.Rect((j - 1) * blk * esc, (i - 1) * blk * esc, (j + 2) * blk * esc, (i + 2) * blk * esc)
        a = pa.get_pixmap(dpi=150, clip=r); b = pb.get_pixmap(dpi=150, clip=r)
        if min(a.width, a.height, b.width, b.height) < 8: continue
        ia = np.frombuffer(a.samples, np.uint8).reshape(a.height, a.width, a.n)[:, :, :3]
        ib = np.frombuffer(b.samples, np.uint8).reshape(b.height, b.width, b.n)[:, :, :3]
        hh = min(ia.shape[0], ib.shape[0]); ww = min(ia.shape[1], ib.shape[1])
        out = np.hstack([ia[:hh, :ww], np.zeros((hh, 6, 3), np.uint8), ib[:hh, :ww]])
        pymupdf.Pixmap(pymupdf.csRGB, out.shape[1], out.shape[0], out.tobytes(), False).save(os.path.join(pasta, f'{base}_{k:02d}.png'))
    return len(feitos)


def conferir_dwg_pdf(rv, pdf, pasta_dwg):
    """E2 (DWG): o DWG de mesmo nome existe, não é mais novo que o PDF e tem os logos do carimbo ao lado."""
    f = folha(pdf); curto = (f['curto'] + f' R{f["rev"]:02d}') if f else os.path.basename(pdf)
    dwg = os.path.join(pasta_dwg, os.path.splitext(os.path.basename(pdf))[0] + '.dwg')
    if not os.path.exists(dwg):
        rv.add('E2', 'PENDENCIA', curto, pasta_dwg, 'DWG da folha não encontrado com o mesmo nome do PDF', 'E2 DWG + PDF'); return
    dt = os.path.getmtime(dwg) - os.path.getmtime(pdf)
    if dt > 120:
        rv.add('E2', 'PENDENCIA', curto, os.path.basename(dwg), f'DWG gravado {dt / 60:.0f} min depois do PDF (PDF pode estar desatualizado)', 'E2 DWG = PDF')
    logos = glob.glob(os.path.join(pasta_dwg, 'CARIMBO_QG_logo_*.png'))
    if len(logos) < 3:
        rv.add('E2', 'PENDENCIA', curto, pasta_dwg, f'{len(logos)} logos CARIMBO_QG_logo_*.png ao lado do DWG (esperado 3)', 'E2 carimbo da construtora no DWG')
    rv.ev('E2', f'{curto}: DWG presente, gravado {"antes" if dt <= 0 else f"{dt:.0f} s depois"} do PDF, {len(logos)} logos ao lado')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('alvo'); ap.add_argument('--origem', nargs='*', default=[]); ap.add_argument('--prof', type=float, default=2.0)
    a = ap.parse_args()
    pdfs = sorted(glob.glob(os.path.join(a.alvo, '*.pdf'))) if os.path.isdir(a.alvo) else [a.alvo]
    rv = Revisao('teste', 'XXX')
    for x in pdfs:
        conferir_pdf(rv, x, a.prof, origem_da_folha(x, a.origem))
    for x in rv.achados: print(x.item, x.nivel, x.onde, '|', x.local, '|', x.problema)
    for k, v in rv.evidencias.items():
        for l in v: print('EV', k, l)
