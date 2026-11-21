# -*- coding: utf-8 -*-
"""Carimbo padrão QG as built nas pranchas que modificamos (pedido do Anderson, 20/10/2026): DWG e PDF.
O carimbo vem da família Revit "ARQ_SIMB_CARIMBO_PROJETO EXECUTIVO-QG AS BUILT.rfa" (raiz do projeto), exportada para
carimbo_qg/fonte/ e montada como bloco com atributos em carimbo_qg/CARIMBO_QG_ASBUILT.dwg (carimbo_qg/montar_bloco.lsp).
Tem o mesmo tamanho do carimbo QG que as pranchas dos projetistas já trazem (175 mm de largura, quadro de revisões em cima),
então entra no mesmo lugar: o carimbo antigo sai (linhas, textos, logos, linhas de revisão) e o bloco entra com o canto
inferior direito no canto do antigo. Os campos saem do carimbo antigo da própria prancha:
  PROJETO      1ª linha do título ("ESCOLA DE TEMPO INTEGRAL DA BAHIA")
  DISCIPLINA   disciplina do assunto + setor ("INST. HIDRÁULICAS - IMPLANTAÇÃO")
  ENDERECO     "ENDEREÇO: " + 3ª linha do título (município)
  ETAPA        início do assunto ("PROJETO EXECUTIVO")
  NOME_FOLHA   2ª linha do assunto ("PLANTA BAIXA")
  FOLHA, CODIGO, ARQUIVO, ESCALA, RESP_PROJETO, CAU_CREA, COORDENADOR, DESENHISTA: os do carimbo antigo; DATA: a da emissão.
  Quadro de revisões: as linhas do antigo (e a nova, se passada), da mais antiga (embaixo) para a mais nova.
Qualquer campo pode ser trocado por `campos={...}`.

Uso como módulo (depois de a prancha estar na revisão nova, com a linha nova no quadro):
    import carimbo_qg; carimbo_qg.trocar(dwg, pdf_dir=..., data='20/10/2026')
Uso pela linha de comando:
    python -X utf8 carimbo_qg.py <prancha.dwg> [--saida PASTA] [--pdf PASTA] [--data dd/mm/aaaa] [--so-ler]
       sem --saida, troca no próprio DWG (o anterior vai para <pasta>/_copias/<nome>_carimbo-antigo.dwg).
    python -X utf8 carimbo_qg.py --montar      remonta o bloco a partir da exportação do Revit.
Um accoreconsole por vez (rever.console espera os das outras threads)."""
import os, sys, re, json, shutil, datetime, collections
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import rever
sys.stdout.reconfigure(encoding='utf-8')
PASTA = os.path.join(AQUI, 'carimbo_qg')
BLOCO = os.path.join(PASTA, 'CARIMBO_QG_ASBUILT.dwg')
LOGOS = ['CARIMBO_QG_logo_QG.png', 'CARIMBO_QG_logo_CONDER.png', 'CARIMBO_QG_logo_GOVBA.png']
DXFOUT = 'D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp'
LARG = 175.0                         # largura do carimbo (antigo e novo), mm de papel
CAB = (113.77, 117.60)               # faixa do cabeçalho do quadro de revisões no bloco, acima da base
LIN = 3.83                           # altura da linha de revisão (a do cabeçalho)
COLS = (0.0, 17.0, 44.0, 149.55, 174.95)   # REV | DATA | DESCRIÇÃO | RESP.
AJUSTE = dict(PROJETO=(3.5, 1, 168), DISCIPLINA=(3.5, 1, 168), ENDERECO=(2.5, 1, 168), ETAPA=(4.0, 1, 118), NOME_FOLHA=(3.5, 1, 118),
              FOLHA=(4.5, 0.7, 48), CODIGO=(4.0, 1, 168), RESP_PROJETO=(1.6, 1, 40), COORDENADOR=(1.6, 1, 41), DESENHISTA=(1.6, 1, 41),
              ARQUIVO=(1.5, 1, 80))                    # altura, fator de largura do estilo, largura útil (mm)
MESES = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']


def u(s):
    """texto para o arquivo de comandos (ASCII; o AutoCAD lê \\U+XXXX)."""
    return ''.join(c if ord(c) < 128 else '\\U+%04X' % ord(c) for c in s).replace('\t', ' ')


def limpa(t):
    """tira a formatação do MTEXT."""
    t = re.sub(r'\\[pP][^;]*;', '', t); t = re.sub(r'\\[FfHhWwQqTtAaCc][^;]*;', '', t)
    t = t.replace('{', '').replace('}', '').replace('\\P', ' ').replace('\\~', ' ')
    t = re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), t)
    return re.sub(r'\s+', ' ', t).strip()


def ler_dxf(fn):
    """entidades do papel por layout: tipo, handle, layer, pontos, texto."""
    L = [x.strip() for x in open(fn, encoding='utf-8', errors='replace')]
    P = [(L[k], L[k + 1]) for k in range(0, len(L) - 1, 2)]
    sec, i, ent, lay = None, 0, [], {}
    while i < len(P):
        c, v = P[i]
        if c == '0' and v == 'SECTION': sec = P[i + 1][1]; i += 2; continue
        if c == '0' and sec in ('ENTITIES', 'OBJECTS') and v != 'ENDSEC':
            d = collections.defaultdict(list); j = i + 1; sub = ''; nm = None; br = None
            while j < len(P) and P[j][0] != '0':
                cc, vv = P[j]; d[cc].append(vv)
                if cc == '100': sub = vv
                elif v == 'LAYOUT' and sub == 'AcDbLayout' and cc == '1' and nm is None: nm = vv
                elif v == 'LAYOUT' and sub == 'AcDbLayout' and cc == '330': br = vv
                j += 1
            if v == 'LAYOUT' and nm and br: lay[br] = nm
            elif sec == 'ENTITIES' and (d['67'] or ['0'])[0] == '1' and v not in ('ATTRIB', 'SEQEND'):
                f = lambda k: [float(x) for x in d[k]]
                pts = list(zip(f('10'), f('20')))
                if v == 'LINE': pts = pts[:1] + list(zip(f('11'), f('21')))[:1]
                elif v not in ('LWPOLYLINE',): pts = pts[:1]        # MTEXT de 2018 repete o 10/20 nos dados de coluna
                ent.append(dict(tipo=v, h=(d['5'] or [''])[0], own=(d['330'] or [''])[0], lay=(d['8'] or [''])[0], pts=pts,
                                bloco=(d['2'] or [''])[0] if v == 'INSERT' else '', alt=float((d['40'] or ['0'])[0] or 0),
                                larg_ole=max([float(x) for x in d['1040']] + [0]) if v == 'OLE2FRAME' else 0,
                                txt=limpa(''.join(d['3']) + ''.join(d['1'])) if v in ('TEXT', 'MTEXT') else ''))
            i = j; continue
        i += 1
    for e in ent: e['layout'] = lay.get(e['own'])
    return ent


def carimbos(ent):
    """um carimbo por layout, ancorado no texto 'ANO DO CTR - …' (3,58 mm da borda esquerda, 21,79 mm acima da base)."""
    out = []
    for a in ent:
        if a['tipo'] in ('TEXT', 'MTEXT') and a['txt'].startswith('ANO DO CTR') and a['pts']:
            x0, y0 = a['pts'][0][0] - 3.58, a['pts'][0][1] - 21.79
            if any(abs(c['x0'] - x0) < 1 and c['layout'] == a['layout'] for c in out): continue
            out.append(dict(layout=a['layout'], x0=x0, y0=y0))
        elif a['tipo'] == 'INSERT' and a['bloco'] == 'CARIMBO_QG_ASBUILT':   # já trocado antes: refaz no mesmo lugar
            out.append(dict(layout=a['layout'], x0=a['pts'][0][0] - LARG, y0=a['pts'][0][1], refazer=True))
    return out


def dentro(e, c, topo):
    return e['pts'] and all(c['x0'] - 1.0 <= x <= c['x0'] + LARG + 1.0 and c['y0'] - 1.0 <= y <= topo for x, y in e['pts'])


def ler_carimbo(ent, c):
    """campos e quadro de revisões do carimbo antigo; handles a apagar."""
    x0, y0, lay = c['x0'], c['y0'], c['layout']
    E = [e for e in ent if e['layout'] == lay]
    # topo do quadro de revisões: linhas horizontais de largura total empilhadas acima do corpo do carimbo
    hs = sorted({round(e['pts'][0][1] - y0, 2) for e in E if e['tipo'] == 'LINE' and e['lay'] == 'ARQ_TXT' and abs(e['pts'][0][1] - e['pts'][1][1]) < 0.01
                 and abs(abs(e['pts'][0][0] - e['pts'][1][0]) - LARG) < 0.5 and min(e['pts'][0][0], e['pts'][1][0]) > x0 - 1})
    topo = max([h for h in hs if h < 260] + [CAB[1]]) + 1.0
    # linhas de revisão acrescentadas só com texto (sem a linha horizontal) ficam acima da última linha do quadro: empilhadas
    # a menos de 7 mm uma da outra, entram no quadro
    for y in sorted(e['pts'][0][1] - y0 for e in E if e['tipo'] in ('TEXT', 'MTEXT') and e['txt'] and e['pts']
                    and x0 - 1 <= e['pts'][0][0] <= x0 + LARG + 1 and topo - 1 < e['pts'][0][1] - y0 < 260):
        if y <= topo + 7: topo = max(topo, y + 3.0)
    # sai tudo o que está inteiro dentro do corpo do carimbo antigo, de qualquer layer (o título antigo da IN-001 não é ARQ_TXT);
    # na faixa do quadro de revisões só linhas e textos (na IN-001 o título de vista "INDICAÇÃO DE DESENHO" fica logo acima)
    corpo = max([h for h in hs if h < 125] + [CAB[1]]) + 1.0
    apagar = [e for e in E if e['tipo'] != 'VIEWPORT' and (dentro(e, c, y0 + corpo) or
                                                         (dentro(e, c, y0 + topo) and e['tipo'] in ('LINE', 'LWPOLYLINE', 'TEXT', 'MTEXT')))]
    apagar += [e for e in E if e['tipo'] == 'OLE2FRAME' and not e['pts'] and e['larg_ole'] < 80]   # logos do projetista (OLE sem posição no DXF)
    T = [dict(t=e['txt'], x=e['pts'][0][0] - x0, y=e['pts'][0][1] - y0, h=e['alt']) for e in E
         if e['tipo'] in ('TEXT', 'MTEXT') and e['txt'] and dentro(e, c, y0 + topo)]
    pega = lambda f: [t for t in T if f(t)]
    titulo = [t['t'] for t in sorted(pega(lambda t: 45 < t['y'] < 75 and t['x'] < 120 and t['t'] not in ('CONTRATADA', 'CONTRATANTE')), key=lambda t: -t['y'])]
    assunto = [t['t'] for t in sorted(pega(lambda t: 20 < t['y'] < 47 and t['x'] < 120 and t['t'] != 'ASSUNTO'), key=lambda t: -t['y'])]
    um = lambda f, d='': (pega(f) or [dict(t=d)])[0]['t']
    linha_nomes = sorted(pega(lambda t: 6.5 < t['y'] < 9.5 and t['h'] > 1.3), key=lambda t: t['x'])
    nome = lambda xa, xb: ' '.join(t['t'] for t in linha_nomes if xa <= t['x'] < xb)
    F = dict(titulo=titulo, assunto=assunto,
             codigo=um(lambda t: re.fullmatch(r'\d\d-\d{3}-[A-Z0-9-]+-R\d\d', t['t'])),
             folha=um(lambda t: re.fullmatch(r'[A-Z]+_[A-Z]+-\d{3}_R\d\d', t['t'])),
             arquivo=um(lambda t: t['t'].upper().endswith('.DWG')),
             escala=um(lambda t: 1.5 < t['y'] < 5 and 45 < t['x'] < 88 and t['h'] > 1.3),     # sem o rótulo "ESCALA" (1,1 mm)
             data=um(lambda t: 1.5 < t['y'] < 5 and 10 < t['x'] < 45 and t['h'] > 1.3),
             resp=nome(0, 45), cau=nome(45, 88), coord=nome(88, 132), desenhista=nome(132, 176))
    # quadro de revisões: linhas de texto acima do cabeçalho "REV."
    cab = [t for t in T if t['t'] in ('REV.', 'REV') and t['x'] < 10]
    ycab = max(t['y'] for t in cab) if cab else 110.0
    rows = []                                          # agrupa por y (as colunas da mesma linha variam até ~0,8 mm)
    for t in sorted((t for t in T if t['y'] > ycab + 2.0), key=lambda t: t['y']):
        if rows and t['y'] - rows[-1][0]['y'] < 2.0: rows[-1].append(t)
        else: rows.append([t])
    revs = []
    for R in rows:
        R = sorted(R, key=lambda t: t['x'])
        col = lambda xa, xb: ' '.join(t['t'] for t in R if xa <= t['x'] < xb)
        revs.append(dict(rev=col(-1, 10), data=col(10, 30), desc=col(30, 155), resp=col(155, 180)))
    revs = [r for r in revs if r['rev'] or r['desc']]
    return F, revs, [e['h'] for e in apagar], topo


def campos_padrao(F, data, nome):
    """nome = nome do DWG de saída (o código e o arquivo da prancha são campos de nome de arquivo no carimbo antigo)."""
    F = dict(F, codigo=nome.upper(), arquivo=nome.upper() + '.DWG')
    m = re.search(r'-R(\d\d)$', nome)                 # o código curto vai para a revisão do nome do arquivo
    if m and F['folha']: F['folha'] = re.sub(r'R\d\d$', 'R' + m.group(1), F['folha'])
    tit, ass = F['titulo'] + ['', '', ''], F['assunto'] + ['', '']
    m = re.match(r'(PROJETO (?:EXECUTIVO|BÁSICO|LEGAL)|ESTUDO PRELIMINAR|ANTEPROJETO)\s+(?:DE|DO|DA|DOS|DAS)\s+(.*)', ass[0])
    etapa, disc = (m.group(1), m.group(2)) if m else ('PROJETO EXECUTIVO', ass[0])
    return dict(PROJETO=tit[0], DISCIPLINA=' - '.join(x for x in (disc, tit[1]) if x), ENDERECO='ENDEREÇO: ' + tit[2] if tit[2] else 'ENDEREÇO:',
                ETAPA=etapa, NOME_FOLHA=ass[1], FOLHA=F['folha'], CODIGO=F['codigo'], ARQUIVO=F['arquivo'] or (F['codigo'] + '.DWG'),
                ESCALA=F['escala'], DATA=data, RESP_PROJETO=F['resp'], CAU_CREA=F['cau'], COORDENADOR=F['coord'], DESENHISTA=F['desenhista'])


def comandos(c, campos, revs, handles):
    x0, y0 = c['x0'], c['y0']
    L = [f'DEL\t{h}' for h in handles]
    for k, v in campos.items():                        # texto mais longo que a caixa: aperta a largura (fator do estilo × encaixe)
        h, wf, wmax = AJUSTE.get(k, (0, 1, 0))
        f = min(1.0, wmax / (len(v) * h * 0.82 * wf)) * wf if h and v else 0
        L.append(f'ATT\t{k}\t{u(v)}' + (f'\t{f:.3f}' if f and f < wf - 0.001 else ''))
    L.append(f'INS\t{c["layout"]}\t{x0 + LARG:.4f}\t{y0:.4f}\t1.0\t{BLOCO.replace(os.sep, "/")}')
    for i, r in enumerate(revs):                       # mais antiga embaixo, logo acima do cabeçalho
        ya, yb = y0 + CAB[1] + i * LIN, y0 + CAB[1] + (i + 1) * LIN; ym = (ya + yb) / 2
        L.append(f'LN\t{x0 + COLS[0]:.4f}\t{yb:.4f}\t{x0 + COLS[-1]:.4f}\t{yb:.4f}')
        for xc in COLS: L.append(f'LN\t{x0 + xc:.4f}\t{ya:.4f}\t{x0 + xc:.4f}\t{yb:.4f}')
        for k, (txt, hj) in enumerate(((r['rev'], 1), (r['data'], 1), (r['desc'], 0), (r['resp'], 1))):
            if not txt: continue
            xa, xb = COLS[k], COLS[k + 1]
            L.append(f'TX\t{x0 + (xa + 1.0 if hj == 0 else (xa + xb) / 2):.4f}\t{ym:.4f}\t1.8\t{hj}\tArial_1\t{u(txt)}')
    return L


def lisp_pdf(base_pdf, layouts):
    q = lambda s: '"' + u(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
    L = ['(setvar "BACKGROUNDPLOT" 0) (setvar "FILEDIA" 0) (setvar "CMDECHO" 1)']
    for lay in layouts:
        L.append(f'(setvar "CTAB" {q(lay)})')
        L.append(f'(command "_.-PLOT" "_Y" {q(lay)} "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_E" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N" '
                 f'{q(base_pdf.replace(os.sep, "/") + ("_" + re.sub(r"[^A-Za-z0-9-]+", "_", lay) if len(layouts) > 1 else "") + ".pdf")} "_N" "_Y")')
    return '\n'.join(L + ['(princ)']) + '\n'


def dxf_de(dwg, pasta):
    """DXF de uma cópia do DWG (handles iguais aos do DWG)."""
    cp = os.path.join(pasta, os.path.basename(dwg)[:-4] + '_ler.dwg'); dxf = cp[:-4] + '.dxf'
    if os.path.exists(dxf) and os.path.getmtime(dxf) > os.path.getmtime(dwg): return dxf
    shutil.copy2(dwg, cp)
    rever.console(cp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % DXFOUT, 'DXFX', '_.QUIT', '_Y'], cp + '.log',
                  {'DXF_OUT': dxf.replace(os.sep, '/')})
    os.remove(cp)
    return dxf


def trocar(dwg, saida=None, pdf_dir=None, data=None, campos=None, nova=None, so_ler=False):
    """troca o carimbo de `dwg`; grava em `saida` (pasta) ou no próprio arquivo. nova = dict(rev, data, desc, resp) acrescenta linha."""
    pasta_out = saida or os.path.dirname(dwg); cop = os.path.join(pasta_out, '_copias'); os.makedirs(cop, exist_ok=True)
    data = data or datetime.date.today().strftime('%d/%m/%Y')
    ent = ler_dxf(dxf_de(dwg, cop))
    info = dict(dwg=dwg, carimbos=[])
    L = []
    for c in carimbos(ent):
        F, revs, hs, topo = ler_carimbo(ent, c)
        if nova: revs.append(nova)
        cp = campos_padrao(F, data, os.path.basename(dwg)[:-4]); cp.update(campos or {})
        L += comandos(c, cp, revs, hs)
        info['carimbos'].append(dict(layout=c['layout'], canto=(round(c['x0'] + LARG, 3), round(c['y0'], 3)), apagar=len(hs), campos=cp, revisoes=revs))
    print(json.dumps(info, ensure_ascii=False, indent=1))
    if so_ler or not info['carimbos']: return info
    dst = os.path.join(pasta_out, os.path.basename(dwg))
    if os.path.normcase(dst) == os.path.normcase(dwg):
        shutil.copy2(dwg, os.path.join(cop, os.path.basename(dwg)[:-4] + '_carimbo-antigo.dwg'))
    else: shutil.copy2(dwg, dst)
    for lg in LOGOS: shutil.copy2(os.path.join(PASTA, lg), os.path.join(pasta_out, lg))    # imagens pelo nome, ao lado do DWG
    nome = os.path.basename(dst)[:-4]
    fcmd = os.path.join(cop, f'carqg_{nome}.txt'); open(fcmd, 'w', encoding='ascii').write('\n'.join(L) + '\n')
    linhas = ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', 'EXPERT 5', '(load "%s")' % os.path.join(PASTA, 'aplicar.lsp').replace(os.sep, '/'), 'CARQGAPL', '_.QSAVE']
    if pdf_dir:
        os.makedirs(pdf_dir, exist_ok=True)
        for p in [os.path.join(pdf_dir, x) for x in os.listdir(pdf_dir) if x.startswith(nome) and x.endswith('.pdf')]:
            os.replace(p, os.path.join(cop, os.path.basename(p)[:-4] + '_anterior.pdf'))   # o -PLOT por cima de PDF existente pode parar perguntando
        fpdf = os.path.join(cop, f'carqg_pdf_{nome}.lsp')
        open(fpdf, 'w', encoding='ascii').write(lisp_pdf(os.path.join(pdf_dir, nome), sorted({c['layout'] for c in info['carimbos']})))
        linhas.append('(load "%s")' % fpdf.replace(os.sep, '/'))
    out = rever.console(dst, linhas + ['_.QUIT', '_Y'], dst + '.carqg.log', {'CARQG_CMD': fcmd.replace(os.sep, '/')})
    bak = dst[:-4] + '.bak'
    if os.path.exists(bak): os.replace(bak, os.path.join(cop, os.path.basename(bak)))
    log = open(dst + '.carqg.log', encoding='utf-16-le', errors='replace').read() if os.path.exists(dst + '.carqg.log') else ''
    info.update(saida=dst, console=out[-200:], marcas=[l.strip() for l in log.splitlines() if l.strip().startswith('CARQG_')])
    print(nome, '|', out[-120:], '|', '; '.join(info['marcas']))
    return info


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    if '--montar' in a:
        cp = os.path.join(PASTA, 'work', 'montar.dwg'); os.makedirs(os.path.dirname(cp), exist_ok=True)
        shutil.copy2(os.path.join(PASTA, 'fonte', 'carimbo_qg_export_revit.dwg'), cp)
        if os.path.exists(BLOCO): os.replace(BLOCO, os.path.join(PASTA, 'work', 'CARIMBO_QG_ASBUILT_anterior.dwg'))   # o WBLOCK pararia perguntando
        print(rever.console(cp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % os.path.join(PASTA, 'montar_bloco.lsp').replace(os.sep, '/'), 'CARQG', '_.QUIT', '_Y'],
                            cp + '.log', {'CARQG_OUT': BLOCO.replace(os.sep, '/')}))
    else:
        alvos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--saida', '--pdf', '--data'))]
        for dwg in alvos: trocar(dwg, opt('--saida'), opt('--pdf'), opt('--data'), so_ler='--so-ler' in a)
