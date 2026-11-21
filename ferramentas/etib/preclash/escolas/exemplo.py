# -*- coding: utf-8 -*-
"""Adaptador MODELO de uma escola para o preclash. Copie para escolas/<escola>.py e troque o que está marcado com <>.
Todos os valores abaixo são fictícios.

O adaptador diz ao rodar.py:
  - onde estão os dados da escola (CSV das fases 2 e 3, terreno .npz);
  - a georreferência (ORIGEM, EPSG) e o retângulo da obra;
  - as regras de solução (REGRAS), os cenários e o que vira IFC de entrega.

Fontes (só leitura): <ESCOLA>/RELATORIOS/FASE2_REDES_<data> (planta) e FASE3_COTAS_<data> (cotas).
Terreno: escolas/dados/exemplo_terreno.npz, gravado por escolas/exemplo_terreno.py.
Uso: etib-python rodar.py exemplo
"""
import os
from preclash import leitura as lt
from preclash.terreno import Terreno

ESCOLA = 'ETIB <Nome da Escola>'
SIGLA = 'EXE'                                   # 3 letras, única por escola
BASE = r'D:\Projeto Modelagem\ETIB-<ESCOLA>'    # na nuvem o etib-python troca por $ETIB_RAIZ/ETIB-<ESCOLA>
F2 = os.path.join(BASE, 'RELATORIOS', 'FASE2_REDES_<data>')
F3 = os.path.join(BASE, 'RELATORIOS', 'FASE3_COTAS_<data>')
SAIDA = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_<data>')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'exemplo_terreno.npz')

ORIGEM = (500000.0, 8700000.0, 0.0)     # ponto UTM redondo perto da obra, sem rotação, cota 0 (a mesma em todos os IFC da escola)
EPSG = 31984                            # SIRGAS 2000 / UTM 24S (trocar pela zona da obra)
CAIXA_OBRA = (499850.0, 8699850.0, 500150.0, 8700150.0)   # Emin, Nmin, Emax, Nmax da obra

# Regras de solução (capítulo 05 da metodologia). O que não estiver aqui vem de preclash/parametros.py.
REGRAS = {
    'folga': 0.20,                                         # folga mínima entre redes (m)
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],           # quem se move primeiro; ESG/AP/DRE ficam fixas
    'dz_max': {'ELE': 1.00, 'SDAI': 1.00, 'HID': 1.00, 'AF': 0.80},
    'estudo': {                                            # estudo de cota das pressurizadas (preclash/estudo.py)
        'por_rede': ['AF', 'HID'],                         # uma cota por rede
        'por_trecho': ['ELE', 'SDAI'],                     # uma cota por trecho entre caixas
        'cob_min': {'AF': 0.30, 'HID': 0.30, 'ELE': 0.60, 'SDAI': 0.60},
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],   # elétrica sempre acima da água
        'fixar_perto_de': ('IfcPump', 'IfcTank'),          # barrilete e casa de bombas na cota do modelo
    },
    'caixas_moveis_grav': ['DRE', 'ESG'], 'desloc_max_grav': 0.60,           # aplicar e avisar: caixa até 0,60 m
}

DESVIOS = ['A']             # cenários que ganham o passo 2 (desvios em planta e caixa deslocada); o resultado é o cenário 'AD'
CENARIO_ENTREGA = 'AD'      # cenário que vira os IFC por disciplina
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'AP', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}

NOMES_DISC = {'AF': 'Água fria', 'ESG': 'Esgoto', 'AP': 'Pluvial', 'DRE': 'Drenagem', 'ELE': 'Elétrica enterrada',
              'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)', 'EST': 'Estrutura as built'}

# Itens já explicados que a verificação de continuidade não deve contar (tipo, trecho): motivo
VERIFICACAO_ESPERADA = {
    # ('ponta solta', '*ELE-01'): 'fim de rede no quadro',
}


def carregar():
    ter = Terreno(TERRENO)
    E = []
    # pressurizadas com eixo 3D da fase 3 (colunas padrão; ver preclash/leitura.py)
    E += lt.pressurizadas(os.path.join(F3, 'EXE_fase3_pressurizadas_cotas.csv'),
                          {'AF': 'AF', 'HID': 'HID', 'SDAI': 'SDAI', 'ELE': 'ELE'})
    # gravidade pelas cotas do projeto (CF/CT); sem cota, declividade do rótulo, nó, ou terreno - 0,60 (marcado "cota estimada")
    esg = lt.gravidade(os.path.join(F2, 'EXE_fase2_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    ap = lt.gravidade(os.path.join(F2, 'EXE_fase2_AP_trechos.csv'), 'AP', 'AP', ter)
    E += esg + ap
    C = []
    C += lt.caixas(os.path.join(F2, 'EXE_fase2_ESG_caixas.csv'), 'ESG', 'ESG', ter, esg)
    C += lt.caixas(os.path.join(F2, 'EXE_fase2_AP_caixas.csv'), 'AP', 'AP', ter, ap)
    ele = [e for e in E if e['disc'] == 'ELE']
    C += lt.caixas_de_nos(os.path.join(F2, 'EXE_fase2_ELE_nos.csv'), 'ELE', 'ELE', ter, ele, {'CX 60x60': 0.60, 'POSTE': 0.80})
    # Pressurizada só em planta: lt.perfil_por_recobrimento(pontos_2d, DE, recobrimento, ter) + lt.elemento_3d(...)
    # Reservatório: caixa com info['classe_ifc'] = 'IfcTank'. Estrutura as built: disciplina 'EST' com info['malha'] (forma real).
    cenarios = {
        'A': {'nome': 'projeto', 'excluir': lambda e: e.get('pendente', False)},
        # 'B': {'nome': 'com a rede pendente', 'excluir': lambda e: False},   # um cenário por dúvida que muda o clash
    }
    return {'elementos': E, 'caixas': C, 'terreno': ter, 'cenarios': cenarios}
