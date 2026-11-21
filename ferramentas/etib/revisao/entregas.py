# -*- coding: utf-8 -*-
"""Entregas a revisar, por escola. Atualizar ao chegar uma entrega nova (caminhos, exceções aprovadas e pendências declaradas).
- excecoes: só o que o dono do projeto aprovou por escrito, com a fonte; vale para profundidade (IFC e notas das pranchas).
- declaradas: trechos/peças das colisões que a entrega já declara como pendência de terceiros (aparecem como observação).
- cob_min: recobrimento mínimo de referência (m) para o aviso D2 (o valor de cada projeto vale mais)."""
R = r'D:\Projeto Modelagem'

ESCOLAS = {
    # MODELO (valores fictícios): copie o bloco, troque o nome da chave (o mesmo do adaptador) e os caminhos.
    'exemplo': dict(
        nome='ETIB <Nome da Escola>', sigla='EXE', epsg=31984, origem=(500000.0, 8700000.0, 0.0),
        entrega='R01 do IFC e revisão seguinte das pranchas (pasta de envio local ENVIO_<data>)',
        ifc=R + r'\ETIB-<ESCOLA>\RELATORIOS\ENVIO_<data>\03_IFC',
        pdf=R + r'\ETIB-<ESCOLA>\RELATORIOS\EXECUTIVO_<data>\PDF',
        dwg=R + r'\ETIB-<ESCOLA>\RELATORIOS\EXECUTIVO_<data>',
        envio=R + r'\ETIB-<ESCOLA>\RELATORIOS\ENVIO_<data>', cde=R + r'\PRANCHAS\ETIB-<ESCOLA>',
        origem_pdf=[R + r'\PRANCHAS\ETIB-<ESCOLA>\_SUPERADAS', R + r'\ETIB-<ESCOLA>\PROJETO_ORIGINAL'],
        # só o que o dono aprovou por escrito, com a fonte. Ex.: dict(disc=('AF', 'HID'), ate=2.20, fonte='dono, <data>: "..."')
        excecoes=[],
        # trechos/peças das colisões declaradas como pendência de terceiros no LEIA-ME de envio. Ex.: ['DRE-12', 'ESG-03']
        declaradas=[],
        # cotas de caixa alteradas e declaradas (aplicar e avisar). Ex.: dict(folha='DRE-001', tipo='CF', de=100.40, para=100.20, fonte='...')
        cotas_declaradas=[],
        cob_min=0.30, perfil='revit',
        verificacao_csv=R + r'\ETIB-<ESCOLA>\RELATORIOS\PRECLASH_<data>\EXE_preclash_AD_verificacao.csv',
        # opcionais: barrilete=('PCI-AF-',), aceitos=[dict(item='C3', trecho='...', motivo='...')], nao_reais=['DRE-10:forma real +0,12 m']
    ),
}
