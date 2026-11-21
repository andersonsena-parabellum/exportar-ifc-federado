# -*- coding: utf-8 -*-
"""Conferência da pasta de envio (item A do CHECKLIST.md): conteúdo, só a revisão vigente, arquivos idênticos aos conferidos,
PDF com DWG, nomes no padrão e LEIA-ME sem processo interno nem disciplina fora do escopo.
Uso direto: python -X utf8 envio_conf.py <pasta de envio> --pdf PASTA --dwg PASTA --ifc PASTA [--cde PASTA]"""
import os, re, glob, collections
from rev_comum import Revisao, folha, sha1

RX_TRABALHO = re.compile(r'_REVISADO|_carimbo-antigo|_versao|_copia|\.bak$|\.dxf$|\.log$|\.scr$|\.lsp$|\.tmp$|~\$|\.dwl2?$|_ler\b', re.I)
RX_LEIAME_PROC = re.compile(r'pr[eé][- ]?compat|preclash|\bthread|claude|\bscript|\bIA\b|intelig[eê]ncia artificial|visualizador|'
                            r'\bnuvem|rascunho|revis[aã]o interna|python|ifcopenshell|accoreconsole|\bJSON\b|\bCSV\b', re.I)
RX_FORA_ESCOPO = re.compile(r'\b(ETE|EEE|GLP|g[aá]s|CFTV|solar|fotovolt)\b', re.I)
PROPS_TRABALHO = (b"'fora_do_comercial'", b"'angulo_real'", b"'deflexao_junta_graus'")   # só no registro interno (limpar_entrega.py)
RX_LINHA_LIMPEZA = re.compile(r"^(#\d+=IFCPROPERTYSET\(|#\d+=IFCPROPERTYSINGLEVALUE\('(fora_do_comercial|angulo_real|deflexao_junta_graus)'|FILE_NAME\(|FILE_DESCRIPTION\()")


def _props_trabalho(x):
    b = open(x, 'rb').read(); return sum(b.count(k) for k in PROPS_TRABALHO)


def _igual_sem_props(x, conferido):
    """o IFC do envio é o conferido só sem as propriedades de trabalho (limpar_entrega.py)?"""
    a = set(open(x, encoding='latin-1').read().splitlines()); b = set(open(conferido, encoding='latin-1').read().splitlines())
    return all(RX_LINHA_LIMPEZA.match(l) for l in a ^ b)


IFC_ESPERADOS = (('HIDRO', r'HIDRO'), ('ELÉTRICA', r'ELE'), ('PCI', r'PCI'), ('TERRENO', r'TERRENO'), ('FEDERADO', r'FEDERADO'))


def conferir_envio(rv, envio, pasta_pdf, pasta_dwg, pasta_ifc, cde=None, ifc_ausentes=None):
    """ifc_ausentes: {disciplina: motivo} de entregas.py, para a escola sem projeto daquela disciplina (ex.: escola E sem PCI)."""
    ifc_ausentes = ifc_ausentes or {}
    if not os.path.isdir(envio):
        rv.add('A1', 'PENDENCIA', envio, '-', 'pasta de envio não encontrada', 'A1 entregável'); return
    todos = [os.path.join(r, f) for r, _, fs in os.walk(envio) for f in fs if f.lower() != 'desktop.ini']
    rel = lambda x: os.path.relpath(x, envio)
    rv.ev('A1', f'{len(todos)} arquivos em {envio}')
    pdfs = [x for x in todos if x.lower().endswith('.pdf')]
    dwgs = [x for x in todos if x.lower().endswith('.dwg')]
    ifcs = [x for x in todos if x.lower().endswith('.ifc')]
    # A2 arquivos de trabalho e revisões superadas
    for x in todos:
        if RX_TRABALHO.search(os.path.basename(x)):
            rv.add('A2', 'PENDENCIA', rel(x), '-', 'arquivo de trabalho/cópia na pasta de envio', 'A2 só o entregável')
    por_base = collections.defaultdict(list)
    for x in pdfs + dwgs:
        f = folha(x)
        if f: por_base[(f['base'], os.path.splitext(x)[1].lower())].append(f['rev'])
        else: rv.add('A5', 'PENDENCIA', rel(x), '-', 'nome fora do padrão da lista mestra (AA-CTR-<MUN>-<LOC>-ETIB-<SETOR>-PE-<DIS>-<NNN>-<CONT>-R<NN>)', 'A5 nome padrão')
    for (b, ext), revs in por_base.items():
        if len(revs) > 1:
            rv.add('A2', 'PENDENCIA', b + ext, '-', f'mais de uma revisão da mesma folha no envio: {sorted(revs)}', 'A2 só a revisão vigente')
    # A4 PDF com DWG e logos
    nomes_dwg = {os.path.splitext(os.path.basename(x))[0] for x in dwgs}
    nomes_pdf = {os.path.splitext(os.path.basename(x))[0] for x in pdfs}
    for n in sorted(nomes_pdf - nomes_dwg): rv.add('A4', 'PENDENCIA', n + '.pdf', '-', 'PDF sem o DWG correspondente no envio', 'A4 PDF + DWG')
    for n in sorted(nomes_dwg - nomes_pdf): rv.add('A4', 'PENDENCIA', n + '.dwg', '-', 'DWG sem o PDF correspondente no envio', 'A4 PDF + DWG')
    for pasta in sorted({os.path.dirname(x) for x in dwgs}):
        logos = glob.glob(os.path.join(pasta, 'CARIMBO_QG_logo_*.png'))
        if len(logos) < 3: rv.add('A4', 'PENDENCIA', rel(pasta) or '.', '-', f'{len(logos)} logos do carimbo ao lado dos DWG (esperado 3)', 'A4 logos do carimbo')
    rv.ev('A4', f'{len(pdfs)} PDF, {len(dwgs)} DWG, {len(ifcs)} IFC')
    rv.ev('A2', f'{len(por_base)} folhas (PDF/DWG), uma revisão cada; arquivos de trabalho procurados pelo nome (_REVISADO, .bak, .dxf, .log…)')
    rv.ev('A5', f'{sum(1 for x in pdfs + dwgs if folha(x))} de {len(pdfs + dwgs)} nomes de folha no padrão')
    # A3 idênticos aos conferidos
    for lista, pasta, tipo in ((pdfs, pasta_pdf, 'PDF'), (dwgs, pasta_dwg, 'DWG')):
        for x in lista:
            loc = os.path.join(pasta, os.path.basename(x)) if pasta else None
            if not loc or not os.path.exists(loc):
                rv.add('A3', 'PENDENCIA', rel(x), '-', f'{tipo} sem par com o mesmo nome na pasta conferida ({pasta})', 'A3 envio = conferido'); continue
            if sha1(x) != sha1(loc):
                rv.add('A3', 'PENDENCIA', rel(x), '-', f'{tipo} do envio diferente do conferido em {pasta}', 'A3 envio = conferido')
    h_loc = {sha1(x): os.path.basename(x) for x in glob.glob(os.path.join(pasta_ifc, '*.ifc'))} if pasta_ifc else {}
    for x in ifcs:
        h = sha1(x)
        n_tr = _props_trabalho(x)
        if n_tr: rv.add('B9', 'PENDENCIA', rel(x), '-', f'{n_tr} propriedades de trabalho (fora_do_comercial/angulo_real/deflexao_junta_graus) no IFC do envio: rodar revisao/limpar_entrega.py',
                        'B9 IFC entregue sem processo interno')
        par = os.path.join(pasta_ifc, os.path.basename(x)) if pasta_ifc else None
        if h in h_loc: rv.ev('A3', f'{os.path.basename(x)} = {h_loc[h]}')
        elif par and os.path.exists(par) and not n_tr and _igual_sem_props(x, par): rv.ev('A3', f'{os.path.basename(x)} = conferido, sem as propriedades de trabalho')
        else: rv.add('A3', 'PENDENCIA', rel(x), '-', f'IFC do envio não bate com nenhum IFC conferido em {pasta_ifc}', 'A3 envio = conferido')
    if cde:
        for x in pdfs:
            c = os.path.join(cde, os.path.basename(x))
            if not os.path.exists(c) or sha1(c) != sha1(x):
                rv.add('A3', 'OBSERVACAO', rel(x), '-', 'PDF do envio ausente ou diferente no CDE (PRANCHAS)', 'A3 CDE atualizado')
    # A1 IFC esperados
    for nome, rx in IFC_ESPERADOS:
        if nome in ifc_ausentes:
            rv.ev('A1', f'sem IFC {nome}: {ifc_ausentes[nome]}'); continue
        if not any(re.search(rx, os.path.basename(x), re.I) for x in ifcs):
            rv.add('A1', 'PENDENCIA', 'IFC', '-', f'falta o IFC {nome} no envio', 'A1 entregável (IFC por disciplina + federado)')
    # A6 LEIA-ME
    leias = [x for x in todos if re.match(r'leia-?me', os.path.basename(x), re.I)]
    if not leias:
        rv.add('A6', 'PENDENCIA', envio, '-', 'pasta de envio sem LEIA-ME', 'A6 LEIA-ME')
    for x in leias:
        txt = open(x, encoding='utf-8-sig', errors='replace').read()
        for k, l in enumerate(txt.splitlines(), 1):
            if RX_LEIAME_PROC.search(l):
                rv.add('A6', 'PENDENCIA', rel(x), f'linha {k}', f'menção a processo interno: "{l.strip()[:70]}"', 'A6 LEIA-ME sem processo')
            if RX_FORA_ESCOPO.search(l):
                rv.add('A6', 'PENDENCIA', rel(x), f'linha {k}', f'disciplina fora do escopo citada: "{l.strip()[:70]}"', 'A6/D9 escopo')
        # folhas citadas × folhas no envio
        citadas = set(re.findall(r'\b(AF|ESG|DRE|EL|IN)-(\d{3})\b\s*[ .a-zA-ZÀ-ú()]*?\bR(\d{2})\b', txt))
        no_envio = {(f['dis'], f['num'], f'{f["rev"]:02d}') for f in (folha(p) for p in pdfs) if f}
        for dis, num, r in sorted(citadas):
            if not any(d == dis and n == num and rr == r for d, n, rr in no_envio):
                rv.add('A6', 'OBSERVACAO', rel(x), f'{dis}-{num} R{r}', 'folha citada no LEIA-ME com revisão que não está no envio', 'A6 LEIA-ME coerente')
        rv.ev('A6', f'{rel(x)}: {len(txt.splitlines())} linhas lidas')
    return dict(pdfs=pdfs, dwgs=dwgs, ifcs=ifcs, leias=leias)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('envio'); ap.add_argument('--pdf'); ap.add_argument('--dwg'); ap.add_argument('--ifc'); ap.add_argument('--cde')
    a = ap.parse_args()
    rv = Revisao('teste', 'XXX')
    conferir_envio(rv, a.envio, a.pdf, a.dwg, a.ifc, a.cde)
    for x in rv.achados: print(x.item, x.nivel, x.onde, '|', x.local, '|', x.problema)
    for k, v in rv.evidencias.items():
        for l in v: print('EV', k, l)
