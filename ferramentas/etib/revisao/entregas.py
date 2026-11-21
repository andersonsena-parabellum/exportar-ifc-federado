# -*- coding: utf-8 -*-
"""Entregas a revisar, por escola. Atualizar ao chegar uma entrega nova (caminhos, exceções aprovadas e pendências declaradas).
- excecoes: só o que o Anderson aprovou por escrito, com a fonte; vale para profundidade (IFC e notas das pranchas).
- declaradas: trechos/peças das colisões que a entrega já declara como pendência de terceiros (aparecem como observação).
- cob_min: recobrimento mínimo de referência (m) para o aviso D2 (o valor de cada projeto vale mais)."""
R = r'D:\Projeto Modelagem'

ESCOLAS = {
    'jandaira': dict(
        nome='ETIB Jandaíra', sigla='JAN', epsg=31984, origem=(631578.10, 8721003.57, 0.0),
        entrega=r'R03 final (PRECLASH_R03_FINAL5\ENTREGA_IFC_R03 de 20/10 23h33 + pranchas e LEIA-ME de EXECUTIVO_R03_IFC\_revisao_qualidade)',
        ifc=R + r'\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R03_FINAL5\ENTREGA_IFC_R03',
        pdf=R + r'\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\_revisao_qualidade\PDF',
        dwg=R + r'\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\_revisao_qualidade',
        envio=r'G:\Meu Drive\ETIB_ENVIOS\ETIB-JANDAIRA_2026-10-20',
        cde=R + r'\PRANCHAS\ETIB-JANDAIRA',
        origem_pdf=[R + r'\PRANCHAS\ETIB-JANDAIRA\_SUPERADAS', R + r'\ETIB-JANDAIRA\PROJETO_ORIGINAL'],
        excecoes=[dict(disc=('AF', 'HID'), ate=2.00,
                       fonte='Anderson, 20/10/2026 ("Sim. Tudo"): água e hidrante podem passar de 1,50 m na R03')],
        declaradas=['DRE-133', 'DRE-061.1', 'DRE-019',
                    'DRE-017'],     # DRE-017 encosta na mesma viga, na junção com o DRE-019 (pendência 3)
        cotas_declaradas=[dict(folha='DRE-001', tipo=t, de=146.90, para=146.49,
                               fonte='CX-43 rebaixada em 19/10 para receber o campo; pendência 4 do LEIA-ME de envio') for t in ('CF', 'CS')]
        + [dict(folha='DRE-001', tipo='CF', de=146.14, para=145.90,
                fonte='CX-32 aprofundada 0,24 m (Anderson, 20/10); pendência 5 do LEIA-ME de envio')],
        cob_min=0.30, perfil='revit', barrilete=('PCI-AF-',),
        verificacao_csv=R + r'\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R03_FINAL5\JAN_preclash_AD_verificacao.csv',
        # aceitos como observação na conferência final (coordenação, 21/10/2026)
        aceitos=[dict(item='C3', trecho='DRE-CPS-E11', motivo='aceito como observação (coordenação, 21/10/2026)'),
                 dict(item='C3', trecho='PCI-AF-H04', motivo='aceito como observação (coordenação, 21/10/2026)'),
                 dict(item='C2', trecho='DRE-CPS-D04', motivo='queda de 18 cm aceita como observação (coordenação, 21/10/2026)'),
                 dict(item='D5', trecho='CX-18', motivo='aceito como observação (coordenação, 21/10/2026)'),
                 dict(item='C5', local='E 631589.5 / N 8721144.5',
                      motivo='perna do ramal DRE-CPS-D04, cuja queda de 18 cm foi aceita como observação (coordenação, 21/10/2026)')],
        # colisões com a caixa envolvente que a forma real (malha do RVT as built) descarta, conferência da thread da escola em 20/10
        nao_reais=['DRE-124:forma real +0,12 m (Jandaíra, 20/10)', 'DRE-135:forma real +0,17 m (Jandaíra, 20/10)',
                   'DRE-126:forma real +0,66 m (Jandaíra, 20/10)'],
    ),
    'pojuca': dict(
        nome='ETIB Pojuca', sigla='PJC', epsg=31984, origem=(572450.0, 8626500.0, 0.0),
        entrega='R02 do IFC e revisão seguinte de 7 pranchas (fluxo novo, 26/10: ENTREGA_IFC_2026-10-26 + EXECUTIVO_2026-10-26)',
        ifc=R + r'\ETIB-POJUCA\RELATORIOS\ENTREGA_IFC_2026-10-26',
        pdf=R + r'\ETIB-POJUCA\RELATORIOS\EXECUTIVO_2026-10-26\PDF',
        dwg=R + r'\ETIB-POJUCA\RELATORIOS\EXECUTIVO_2026-10-26',
        envio=None,
        cde=R + r'\PRANCHAS\ETIB-POJUCA',
        # origem plotada do DWG do projetista do mesmo jeito que a revisada (o CTB dele não veio: regra da entrada), como na Catu
        origem_pdf=[R + r'\ETIB-POJUCA\RELATORIOS\EXECUTIVO_2026-10-26\_origem_plotada', R + r'\PRANCHAS\ETIB-POJUCA\_SUPERADAS',
                    R + r'\ETIB-POJUCA\PROJETO_ORIGINAL'],
        excecoes=[],
        # colisões que vão na página de pendências para decisão (caixas de iluminação do corredor norte do bloco pedagógico)
        declaradas=['EL2-CX06', 'EL2-CX07', 'EL2-CX08', 'EL2-CX09', 'POSTE-IE-13', 'POSTE-IE-13:base', 'PVP-01', 'ESG-40', 'EL1-054.1', 'EL1-054.3', 'EL1-012'],
        # CT das caixas de esgoto e drenagem levadas ao terreno executado (aplicar e avisar: CT/CF incoerente com a profundidade)
        cotas_declaradas=[dict(folha=c.get('folha') or ('ESG-001' if c['caixa'].startswith(('PVE', 'CES', 'CG', 'CE')) else 'DRE-001'), tipo='CT', de=c['ct_projeto'], para=c['ct_nova'],
                               fonte='CT pelo terreno do IMP as built, aplicar e avisar (Anderson, 22/10); ficha "CT das caixas" da página de pendências')
                          for c in __import__('json').load(open(R + r'\ETIB-POJUCA\RELATORIOS\EXECUTIVO_2026-10-26\PJC_ct_corrigidas.json', encoding='utf-8'))],
        cob_min=0.30, perfil='revit',
        verificacao_csv=R + r'\ETIB-POJUCA\RELATORIOS\PRECLASH_2026-10-25\PJC_preclash_AD_verificacao.csv',
    ),
    'alagoinhas': dict(
        nome='ETIB Alagoinhas (implantação)', sigla='ALI', epsg=31984, origem=(561500.0, 8658000.0, 0.0),
        entrega='R03 da implantação (ENTREGA_IFC_R03\_revisao_IMP + EXECUTIVO_R03)',
        ifc=R + r'\FERRAMENTAS\revisao\relatorios\ETIB-ALAGOINHAS\_ifc_IMP',
        pdf=R + r'\ETIB-ALAGOINHAS\RELATORIOS\EXECUTIVO_R03\PDF',
        dwg=R + r'\ETIB-ALAGOINHAS\RELATORIOS\EXECUTIVO_R03',
        envio=None,
        cde=R + r'\PRANCHAS\ETIB-ALAGOINHAS',
        origem_pdf=[R + r'\PRANCHAS\ETIB-ALAGOINHAS', R + r'\ETIB-ALAGOINHAS\4 - IMPLANTAÇÃO-20261008T151806Z-1-001'],
        excecoes=[],
        # colisões que sobram (pergunta ao Anderson de 21/10/2026: drenagem/esgoto × estrutura as built e gravidade × gravidade para os
        # projetistas; o resto em pendências do LEIA-ME) — gerado de PRECLASH_IMP_R03\ALI_preclash_AD_conflitos_depois.csv
        declaradas=['DRN-164', 'CX03', 'DRN-165', 'Reservatório existente', 'ESG-07', 'DRN-191'],
        cob_min=0.30, perfil='revit', barrilete=('B1', 'B2', 'AF-02.1', 'AF-02.2', 'AF-02.3', 'AF-03.1', 'AF-04.1'),
        verificacao_csv=R + r'\ETIB-ALAGOINHAS\RELATORIOS\PRECLASH_IMP_R03\ALI_preclash_AD_verificacao.csv',
    ),
    'satiro': dict(
        nome='ETIB Sátiro Dias', sigla='SAT', epsg=31984, origem=(546000.0, 8716200.0, 0.0),
        entrega='envio de 22/10/2026 (ENVIO_2026-10-22: IFC de entrega + EXECUTIVO_2026-10-21)',
        ifc=R + r'\ETIB-SATIRO-DIAS\RELATORIOS\ENVIO_2026-10-22\03_IFC',
        pdf=R + r'\ETIB-SATIRO-DIAS\RELATORIOS\EXECUTIVO_2026-10-21\PDF',
        dwg=R + r'\ETIB-SATIRO-DIAS\RELATORIOS\EXECUTIVO_2026-10-21',
        envio=r'G:\Meu Drive\ETIB_ENVIOS\ETIB-SATIRO-DIAS_2026-10-22', cde=R + r'\PRANCHAS\ETIB-SATIRO-DIAS',
        origem_pdf=[R + r'\PRANCHAS\ETIB-SATIRO-DIAS\_SUPERADAS', R + r'\ETIB-SATIRO-DIAS\PROJETO_ORIGINAL'],   # revisadas no CDE desde 22/10
        excecoes=[],
        # os 3 esgoto × pluvial resolvidos por nós (Anderson, 22/10/2026): nada declarado
        declaradas=[],
        # PVE-06: fundo baixado 5 cm para o ESG-014 passar sob o AP-108 (Anderson, 22/10/2026: "Os 3 conflitos, você mesmo pode fazer")
        cotas_declaradas=[dict(folha='ESG-001', tipo='CF', de=234.30, para=234.25,
                               fonte='Anderson, 22/10/2026 (conflitos resolvidos por nós); LEIA-ME de envio')],
        cob_min=0.30, perfil='revit',
        verificacao_csv=R + r'\ETIB-SATIRO-DIAS\RELATORIOS\PRECLASH_2026-10-21\SAT_preclash_AD_verificacao.csv',
    ),
    'alagoinhas_ba2': dict(
        nome='ETIB Alagoinhas (bloco BA2)', sigla='ALH', epsg=31984, origem=(561500.0, 8658000.0, 0.0),
        entrega='R03 do bloco BA2 (ENTREGA_IFC_R03\_revisao_BA2)',
        ifc=R + r'\FERRAMENTAS\revisao\relatorios\ETIB-ALAGOINHAS\_ifc_BA2',
        pdf=R + r'\ETIB-ALAGOINHAS\RELATORIOS\EXECUTIVO_R03_BA2\PDF',
        dwg=R + r'\ETIB-ALAGOINHAS\RELATORIOS\EXECUTIVO_R03_BA2',
        envio=None, cde=R + r'\PRANCHAS\ETIB-ALAGOINHAS',
        origem_pdf=[R + r'\PRANCHAS\ETIB-ALAGOINHAS', R + r'\ETIB-ALAGOINHAS\PROJETO_ORIGINAL\BA2'],
        excecoes=[], declaradas=[], cob_min=0.30, perfil='revit',
        # BA2 é instalação predial: eletroduto rígido no entreforro e aço galvanizado aparente (legenda das pranchas EL e IN)
        materiais={'ELE': r'flex|corrugad|PEAD|r[ií]gid|galvaniz', 'SDAI': r'flex|PEAD|galvaniz'},
        verificacao_csv=R + r'\ETIB-ALAGOINHAS\RELATORIOS\PRECLASH_BA2_R03\ALH_preclash_AD_verificacao.csv',
    ),
    'olindina': dict(
        nome='ETIB Olindina', sigla='ONN', epsg=31984, origem=(573950.0, 8743250.0, 0.0),
        entrega='R01, pasta de envio local (ENVIO_2026-10-22: IFC de entrega + EXECUTIVO_2026-10-21)',
        ifc=R + r'\ETIB-OLINDINA\RELATORIOS\ENVIO_2026-10-22\03_IFC',
        pdf=R + r'\ETIB-OLINDINA\RELATORIOS\EXECUTIVO_2026-10-21\PDF',
        dwg=R + r'\ETIB-OLINDINA\RELATORIOS\EXECUTIVO_2026-10-21',
        envio=R + r'\ETIB-OLINDINA\RELATORIOS\ENVIO_2026-10-22', cde=R + r'\PRANCHAS\ETIB-OLINDINA',
        origem_pdf=[R + r'\PRANCHAS\ETIB-OLINDINA', R + r'\ETIB-OLINDINA\PROJETO_ORIGINAL'],
        excecoes=[], declaradas=[], cob_min=0.30, perfil='revit',
        # CA-06 do pluvial do BA5: etiqueta "CT:166.91" (fundo) corrigida para 166,81 (profundidade 1,19 m da própria etiqueta e i = 1 %)
        cotas_declaradas=[dict(folha=f, tipo=t, de=166.91, para=166.81,
                               fonte='Anderson, 22/10/2026 ("podemos nós mesmos alterar isso e gerar revisão"); LEIA-ME de envio')
                          for f in ('ESG-001', 'DRE-001') for t in ('CT', 'CF')],
        verificacao_csv=R + r'\ETIB-OLINDINA\RELATORIOS\PRECLASH_2026-10-21\ONN_preclash_AD_verificacao.csv',
    ),
    'itamira': dict(
        nome='ETIB Aporá Itamira', sigla='ITA', epsg=31984, origem=(584400.0, 8704300.0, 0.0),
        # DRE-001 R01 redesenhada inteira pela drenagem executada do campo (decisão I2 do Anderson, 23/10/2026: "o as built sempre vai
        # ser o mais recente"): as etiquetas da rede R00 saem junto com ela (E7 = observação esperada)
        # EL-001 R01 com a ELE-06 até o QD1 executado (decisão I1, 24/10/2026, "Revise o EL-001"): saem ELE-04/05 e a etiqueta do ELE-05
        entrega='R02, pasta de envio local (ENVIO_2026-10-24: IFC R02 com a ELE-06 + DRE-001 R01 + EL-001 R01)',
        ifc=R + r'\ETIB-APORA-ITAMIRA\RELATORIOS\ENVIO_2026-10-24\03_IFC',
        pdf=R + r'\ETIB-APORA-ITAMIRA\RELATORIOS\EXECUTIVO_2026-10-24\PDF',
        dwg=R + r'\ETIB-APORA-ITAMIRA\RELATORIOS\EXECUTIVO_2026-10-24',
        envio=R + r'\ETIB-APORA-ITAMIRA\RELATORIOS\ENVIO_2026-10-24', cde=R + r'\PRANCHAS\ETIB-APORA-ITAMIRA',
        origem_pdf=[R + r'\PRANCHAS\ETIB-APORA-ITAMIRA\_SUPERADAS', R + r'\PRANCHAS\ETIB-APORA-ITAMIRA', R + r'\ETIB-APORA-ITAMIRA\PROJETO_ORIGINAL'],
        excecoes=[], declaradas=['AB-403234'], cob_min=0.30, perfil='revit',
        ifc_ausentes={'PCI': 'a implantação não tem projeto de incêndio no acervo (pedido à construtora); o do campo é só sinalização e '
                              'iluminação de emergência, sem rede enterrada'},
        verificacao_csv=R + r'\ETIB-APORA-ITAMIRA\RELATORIOS\PRECLASH_2026-10-24\ITA_preclash_AD_verificacao.csv',
    ),
    'apora_aurea': dict(
        nome='ETIB Aporá Prof. Áurea', sigla='AUR', epsg=31984, origem=(600000.0, 8711300.0, 0.0),
        entrega='R01, pasta de envio local (ENVIO_2026-10-23: IFC de entrega + EXECUTIVO_2026-10-23)',
        ifc=R + r'\ETIB-APORA-PROF-AUREA\RELATORIOS\ENVIO_2026-10-23\03_IFC',
        pdf=R + r'\ETIB-APORA-PROF-AUREA\RELATORIOS\EXECUTIVO_2026-10-23\PDF',
        dwg=R + r'\ETIB-APORA-PROF-AUREA\RELATORIOS\EXECUTIVO_2026-10-23',
        envio=R + r'\ETIB-APORA-PROF-AUREA\RELATORIOS\ENVIO_2026-10-23', cde=R + r'\PRANCHAS\ETIB-APORA-PROF-AUREA',
        origem_pdf=[R + r'\PRANCHAS\ETIB-APORA-PROF-AUREA', R + r'\ETIB-APORA-PROF-AUREA\PROJETO_ORIGINAL'],
        excecoes=[], declaradas=['AB-024', 'AB-026', 'AB-027', 'AB-028', 'AB-043', 'AB-044', 'AB-045', 'AB-048', 'AB-050', 'AB-053'], cob_min=0.30, perfil='revit',
        # AF-002: CT 188,00 a leste (CA-06 a CA-10, PVP-01/02) com a mesma profundidade (aplicar e avisar, decisão A3 da página de entrada)
        cotas_declaradas=[dict(folha='AF-002', tipo=t, de=de, para=para,
                               fonte='aplicar e avisar (Anderson, 22/10/2026); decisão A3 da página de entrada; LEIA-ME de envio')
                          for t, de, para in [('CT', 190.00, 188.00), ('CT', 189.00, 188.00), ('CF', 189.25, 187.25), ('CF', 189.35, 187.35),
                                              ('CF', 189.40, 187.40), ('CF', 189.15, 187.15), ('CF', 189.07, 187.07), ('CF', 187.83, 186.83),
                                              ('CF', 188.00, 187.00)]],
        verificacao_csv=R + r'\ETIB-APORA-PROF-AUREA\RELATORIOS\PRECLASH_2026-10-23\AUR_preclash_AD_verificacao.csv',
    ),
    'catu': dict(
        nome='ETIB Catu', sigla='CAT', epsg=31984, origem=(567700.0, 8634650.0, 0.0),
        entrega='R01 do IFC e revisão seguinte das 6 pranchas, pasta de envio local (ENVIO_2026-10-25: ENTREGA_IFC_2026-10-25 + EXECUTIVO_2026-10-25)',
        ifc=R + r'\ETIB-CATU\RELATORIOS\ENVIO_2026-10-25\03_IFC',
        pdf=R + r'\ETIB-CATU\RELATORIOS\EXECUTIVO_2026-10-25\PDF',
        dwg=R + r'\ETIB-CATU\RELATORIOS\EXECUTIVO_2026-10-25',
        envio=R + r'\ETIB-CATU\RELATORIOS\ENVIO_2026-10-25', cde=R + r'\PRANCHAS\ETIB-CATU',
        # origem plotada do DWG do projetista do mesmo jeito que a revisada (o CTB dele não veio: regra da entrada), antes do PDF dele
        origem_pdf=[R + r'\ETIB-CATU\RELATORIOS\EXECUTIVO_2026-10-25\_origem_plotada', R + r'\PRANCHAS\ETIB-CATU', R + r'\ETIB-CATU\PROJETO_ORIGINAL'],
        excecoes=[], declaradas=[], cob_min=0.30, perfil='revit',
        verificacao_csv=R + r'\ETIB-CATU\RELATORIOS\PRECLASH_2026-10-25\CAT_preclash_AD_verificacao.csv',
    ),
}
