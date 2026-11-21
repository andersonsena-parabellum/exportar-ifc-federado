# -*- coding: utf-8 -*-
"""Revisão de qualidade de uma entrega de escola, contra o CHECKLIST.md (mesma pasta). Só lê os arquivos da escola.
Uso:  ..\\.venv\\Scripts\\python.exe -X utf8 revisar.py <escola> [--classes-suspensas] [--recortes] [--sem-ifc] [--sem-pdf] [--sem-envio]
      [--ifc PASTA] [--pdf PASTA] [--dwg PASTA] [--envio PASTA]   (sobrescrevem os caminhos de escolas.py)
Saída: relatorios\\<ESCOLA>\\REVISAO_<SIGLA>_<data>.md (+ _achados.csv; recortes\\ com origem | revisada para a conferência visual)."""
import os, sys, glob, argparse, collections
import ifcopenshell
from rev_comum import Revisao, SAIDA, gravar
from entregas import ESCOLAS
import ifc_conf, pdf_conf, envio_conf

ITENS = [
    ('A1', 'Entregável completo (IFC por disciplina + terreno + federado; PDF + DWG das folhas modificadas; LEIA-ME)'),
    ('A2', 'Só a revisão vigente, sem arquivo de trabalho'),
    ('A3', 'Envio idêntico ao conferido (e ao CDE)'),
    ('A4', 'PDF com DWG e logos do carimbo'),
    ('A5', 'Nomes no padrão da lista mestra'),
    ('A6', 'LEIA-ME sem processo interno nem disciplina fora do escopo'),
    ('B1', 'IFC georreferenciado (EPSG e origem da escola)'),
    ('B2', "Classes IFC do perfil 'revit' (tubo, eletroduto = IfcCableSegment, caixa elétrica = IfcJunctionBox, caixa hidráulica = equipamento hidráulico, IfcValve, IfcTank)"),
    ('B3', 'PredefinedType preenchido'),
    ('B4', 'Material associado'),
    ('B5', 'Diâmetro em propriedade padrão'),
    ('B6', 'Sistema (IfcDistributionSystem com tipo)'),
    ('B7', 'Nome/código do projeto em cada peça'),
    ('B8', 'Federado = soma das disciplinas, só com os pontos pendentes, sem Pset da ferramenta nem nome de pessoa'),
    ('B9', 'IFC sem processo interno (nome de ferramenta, pessoa, texto de trabalho)'),
    ('B10', 'recobrimento_estudo nas pressurizadas'),
    ('B11', 'Caixas ocas no padrão (fundo, parede/anel, tampa, grelha FoFo nas CA/BL) com dimensão interna e profundidade útil'),
    ('B12', 'Furo de passagem dos tubos nas caixas (observação até a ferramenta fazer)'),
    ('B13', 'Aberto no Revit 2025 e num visualizador neutro (analista)'),
    ('C1', 'Rede contínua, sem ponta solta'),
    ('C2', 'Sem folga entre peças nem ligação no meio do tubo'),
    ('C3', 'Sem segmento menor que a conexão'),
    ('C4', 'Sem peças sobrepostas'),
    ('C5', 'Conexão no vértice e alinhada'),
    ('C6', 'Conexão comercial em toda mudança de direção e junção nos nós'),
    ('D1', 'Profundidade máxima da escola'),
    ('D2', 'Recobrimento mínimo / rede enterrada'),
    ('D3', 'Sem degrau em Z; cota só muda na caixa'),
    ('D4', 'Elétrica sempre acima da água'),
    ('D5', 'Caixas nem enterradas nem sobrando; fundo abaixo do tubo'),
    ('D6', 'Clash independente com a estrutura pela forma real; colisões declaradas'),
    ('D7', 'Gravidade com as cotas do projeto'),
    ('D8', 'Reservatório inferior modelado'),
    ('D9', 'Nada fora do escopo do contrato'),
    ('E1', 'Folha A0, uma por PDF'),
    ('E2', 'Carimbo QG as built no PDF e no DWG'),
    ('E3', 'Revisão coerente (arquivo, carimbo, quadro)'),
    ('E4', 'Uma nota de profundidade por trecho'),
    ('E5', 'Notas dentro da profundidade máxima'),
    ('E6', 'Nada sobreposto: notas e folha inteira'),
    ('E7', 'Etiquetas e cotas do projeto preservadas'),
    ('E8', 'Sem nuvem, rascunho ou nota de processo'),
    ('E9', 'Traçado novo no padrão da prancha (conferência visual)'),
    ('E10', 'Prancha × modelo (amostra visual)'),
    ('E11', 'Padrão gráfico: rede existente, altura dos textos'),
]
SUSPENSOS = ('B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B11')


def federado(rv, pasta, declaradas=()):
    """B8: federado = soma das disciplinas; só os marcadores das pendências declaradas (nada de "atenção");
    sem o Pset da ferramenta (PRECLASH) e sem nome de pessoa (ex.: "modelo do Daniel")."""
    import re
    import ifcopenshell.util.element as ue
    fed = [x for x in glob.glob(os.path.join(pasta, '*.ifc')) if 'FEDERADO' in os.path.basename(x).upper()]
    if not fed:
        rv.add('B8', 'PENDENCIA', pasta, '-', 'sem IFC federado', 'B8 federado'); return
    disc = [x for x in glob.glob(os.path.join(pasta, '*.ifc')) if x not in fed]
    g = collections.Counter()
    for x in disc:
        for p in ifcopenshell.open(x).by_type('IfcProduct'):
            if p.Representation and not p.is_a('IfcSite'): g[p.is_a()] += 1
    F = ifcopenshell.open(fed[0]); nome = os.path.basename(fed[0])
    f = collections.Counter(p.is_a() for p in F.by_type('IfcProduct') if p.Representation and not p.is_a('IfcSite'))
    marc = collections.Counter()
    for p in F.by_type('IfcBuildingElementProxy'):
        ps = {k: v for d in ue.get_psets(p).values() for k, v in d.items()}
        marc[str(ps.get('gravidade') or p.Description or p.Name)] += 1
    aten = sum(v for k, v in marc.items() if 'ATEN' in k.upper())
    crit = sum(marc.values()) - aten
    if aten:
        rv.add('B8', 'PENDENCIA', nome, f'{aten} marcadores', f'federado com {aten} marcadores de "atenção" (folga curta é trabalho interno)', 'B8 federado só com o entregável')
    if crit > max(len(declaradas), 0):
        rv.add('B8', 'PENDENCIA', nome, f'{crit} marcadores', f'{crit} marcadores de colisão e a entrega declara {len(declaradas)} pendências', 'B8 federado só com o entregável')
    psets = {ps.Name for ps in F.by_type('IfcPropertySet')}
    if any(re.search(r'preclash', n or '', re.I) for n in psets):
        rv.add('B8', 'PENDENCIA', nome, 'Pset', 'federado com o Pset "PRECLASH" (nome da ferramenta)', 'B8/B9 federado sem processo interno')
    pessoas = sum(1 for v in F.by_type('IfcPropertySingleValue') if v.NominalValue and re.search(r'daniel|claude|anderson', str(v.NominalValue.wrappedValue), re.I))
    if pessoas:
        rv.add('B8', 'PENDENCIA', nome, f'{pessoas} propriedades', 'federado com nome de pessoa nas propriedades (ex.: "modelo do Daniel")', 'B8/B9 federado sem processo interno')
    falta = g - f; sobra = f - g
    if falta:
        rv.add('B8', 'PENDENCIA', nome, '-', 'federado sem elementos das disciplinas: ' + ', '.join(f'{k} {v}' for k, v in falta.items()), 'B8 federado')
    rv.ev('B8', f'{nome}: {sum(f.values())} elementos; disciplinas somam {sum(g.values())}; a mais no federado: '
                + (', '.join(f'{k} {v}' for k, v in sobra.items()) or 'nada') + f'; marcadores {dict(marc) or "nenhum"}')


def esperados(rv, csv_fn):
    """a verificação da própria ferramenta (_verificacao.csv) explica pontas, pedaços e degraus esperados (coluna 'esperado').
    O analista lê o motivo: o achado de continuidade do mesmo trecho vira observação com o motivo ao lado."""
    import csv, re
    if not csv_fn or not os.path.exists(csv_fn): return
    motivos = {}
    for r in csv.DictReader(open(csv_fn, encoding='utf-8-sig'), delimiter=';'):
        if (r.get('esperado') or '').strip(): motivos[r['trecho'].strip()] = r['esperado'].strip()
    n = 0
    for x in rv.achados:
        if x.item not in ('C1', 'C2', 'C3', 'D3') or x.nivel != 'PENDENCIA': continue
        t = next((t for t in motivos if re.search(r'(^|[\s×(])' + re.escape(t) + r'([\s,—)]|$)', x.local)), None)
        if t:
            x.nivel = 'OBSERVACAO'; x.problema += f' — esperado pela entrega: {motivos[t]}'; n += 1
    rv.ev('C1', f'{len(motivos)} itens esperados na verificação da entrega; {n} achados explicados por eles')


def aceitos(rv, lista):
    """itens que a coordenação aceitou como observação (com o motivo), sem reprovar: [dict(item, trecho, motivo)]."""
    import re
    n = 0
    for a in lista or ():
        for x in rv.achados:
            if x.nivel != 'PENDENCIA' or x.item != a['item']: continue
            if (a.get('local') and a['local'] in x.local) or (a.get('trecho') and re.search(r'(^|[\s×(])' + re.escape(a['trecho']) + r'([\s,—)]|$)', x.local)):
                x.nivel = 'OBSERVACAO'; x.problema += f' — {a["motivo"]}'; n += 1
    if lista: rv.ev('C1', f'{n} achados aceitos como observação pela coordenação ({len(lista)} itens na lista de entregas.py)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('escola'); ap.add_argument('--classes-suspensas', action='store_true'); ap.add_argument('--recortes', action='store_true')
    ap.add_argument('--sufixo', default='', help='acrescenta ao nome do relatório (ex.: _pranchas_v2)')
    ap.add_argument('--rodada', default='', help='nome da rodada revisada (ex.: FINAL5); entra no nome do relatório')
    ap.add_argument('--entrega', help='texto da entrega revisada (sobrescreve o de entregas.py)')
    for k in ('ifc', 'pdf', 'dwg', 'envio'): ap.add_argument('--' + k)
    for k in ('ifc', 'pdf', 'envio'): ap.add_argument('--sem-' + k, action='store_true')
    a = ap.parse_args()
    E = dict(ESCOLAS[a.escola])
    for k in ('ifc', 'pdf', 'dwg', 'envio'):
        if getattr(a, k): E[k] = getattr(a, k)
    pasta = os.path.join(SAIDA, os.path.basename(E['cde']) if E.get('cde') else a.escola.upper())
    os.makedirs(pasta, exist_ok=True)
    rv = Revisao(E['nome'], E['sigla'])
    from preclash import parametros as PAR
    pm = PAR.prof_max(E['sigla'])
    cab = [f'- Profundidade máxima da escola: {pm:.2f} m (`preclash\\parametros.py`)']
    cab += [f'- Exceção aprovada: {e["fonte"]}' for e in E.get('excecoes', [])]
    if E.get('declaradas'): cab.append(f'- Pendências declaradas pela entrega: {", ".join(E["declaradas"])}')
    if a.classes_suspensas: cab.append('- Itens B2 a B6 (classes, tipo, material, diâmetro e sistema do IFC) suspensos até a correção da ferramenta (pedido de 20/10/2026)')
    if not a.sem_envio and E.get('envio'):
        print('envio...'); envio_conf.conferir_envio(rv, E['envio'], E['pdf'], E['dwg'], E['ifc'], E.get('cde'), E.get('ifc_ausentes'))
    if not a.sem_ifc:
        print('IFC...')
        arqs = [x for x in glob.glob(os.path.join(E['ifc'], '*.ifc')) if 'FEDERADO' not in os.path.basename(x).upper()]
        ifc_conf.BARRILETE = tuple(E.get('barrilete', ()))
        R = ifc_conf.ler(arqs)
        ifc_conf.conferir_informacao(rv, R, E.get('epsg'), E.get('origem'), E.get('perfil', 'revit'), E.get('materiais'))
        T = ifc_conf.terreno(R, os.path.join(pasta, f'_terreno_{E["sigla"]}.npz'))
        ifc_conf.conferir_continuidade(rv, R)
        ifc_conf.conferir_regras(rv, R, T, pm, E.get('excecoes', ()), E.get('declaradas', ()), cob_min=E.get('cob_min', 0.30), nao_reais=E.get('nao_reais', ()))
        federado(rv, E['ifc'], E.get('declaradas', ()))
        esperados(rv, E.get('verificacao_csv'))
        aceitos(rv, E.get('aceitos'))
        rv.ev('D7', 'cotas das caixas de gravidade: conferidas nas pranchas (E7, cotas alteradas) e na tampa/fundo (D5)')
    if not a.sem_pdf:
        print('PDF...')
        for x in sorted(glob.glob(os.path.join(E['pdf'], '*.pdf'))):
            o = pdf_conf.origem_da_folha(x, E.get('origem_pdf', []))
            pdf_conf.conferir_pdf(rv, x, pm, o, E.get('excecoes', ()), os.path.join(pasta, 'recortes' + a.sufixo) if a.recortes else None,
                                  E.get('cotas_declaradas', ()))
            if E.get('dwg'): pdf_conf.conferir_dwg_pdf(rv, x, E['dwg'])
    if a.classes_suspensas:
        for x in rv.achados:
            if x.item in SUSPENSOS and x.nivel in ('PENDENCIA', 'OBSERVACAO'):
                x.nivel = 'AGUARDANDO'; x.problema += ' [suspenso: correção das classes IFC em andamento]'
    for it in ('E9', 'E10'):
        rv.ev(it, 'conferência visual nos recortes (origem | revisada) da pasta recortes\\' if a.recortes else 'conferência visual: rodar com --recortes')
    fn, ver, n = gravar(rv, pasta, a.entrega or E['entrega'], ITENS, cab, (f'_{a.rodada}' if a.rodada else '') + a.sufixo)
    print(ver, dict(n)); print(fn)


if __name__ == '__main__':
    main()
