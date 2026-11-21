# -*- coding: utf-8 -*-
"""Adaptador da ETIB Sátiro Dias para o preclash.
Fontes (só leitura): ETIB-SATIRO-DIAS/RELATORIOS/FASE2_REDES_2026-10-18 e FASE3_COTAS_2026-10-18 (thread da escola).
Decisões do usuário (18/10/2026) já aplicadas nos CSVs pela thread da escola:
  - drenagem do campo = CPS DRE-001 (a espinha de drenos sob o campo saiu da pluvial do ESG-001: SAT_fase2_AP_removidos_campo.csv);
  - CF corrigidas do esgoto (PVE-01 234,99; CI-03 235,26);
  - galeria 2 × Ø1200 'rede futura se necessário': pendente com a construtora -> elemento 'pendente' (cenário próprio).
Terreno: desde 19/10/2026, o do IMP as built (Revit), congelado em escolas/dados/satiro_terreno.npz (satiro_terreno.py);
o provisório da fase 3 ficou em satiro_terreno_provisorio.npz.
Também entram no clash (19/10/2026, FERRAMENTAS/georef_dxf/satiro/equip_sat.py): subidas das prumadas do pluvial, das
torneiras de jardim, do recalque e dos eletrodutos nos quadros, e as canaletas (pluvial e campo, aproximadas por cápsula).
Os equipamentos (postes, quadros, hidrantes, reservatórios...) entram só nos IFC, pelo FERRAMENTAS/georef_dxf/satiro/entrega_sat.py."""
import os
from preclash import leitura as lt
from preclash.terreno import Terreno
from preclash import modelo as md
import sys
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro')
import equip_sat   # noqa: E402

ESCOLA = 'ETIB Sátiro Dias'
SIGLA = 'SAT'
BASE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS'
F2 = os.path.join(BASE, 'RELATORIOS', 'FASE2_REDES_2026-10-18')
F3 = os.path.join(BASE, 'RELATORIOS', 'FASE3_COTAS_2026-10-18')
SAIDA = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'satiro_terreno.npz')
ORIGEM = (546000.0, 8716200.0, 0.0)       # origem proposta dos RVTs (E, N, cota) — AGENTS.md
EPSG = 31984                              # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (545840.0, 8716080.0, 546070.0, 8716290.0)

# regras de solução (podem ser trocadas por escola)
REGRAS = {
    'folga': 0.20,                                     # folga mínima entre redes (m) — critério do R02 da Alagoinhas
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],       # quem desce/sobe primeiro; DRE/ESG/AP ficam fixas
    'dz_max': {'ELE': 1.00, 'SDAI': 1.00, 'HID': 1.00, 'AF': 0.80},   # quanto cada uma pode mudar de cota num cruzamento
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 1.50},  # profundidade máxima do topo do tubo (m)
    'agua_acima_de': ['ESG'],                         # AF não deve passar por baixo do esgoto (alerta)
}

DESVIOS = ['A', 'B']     # cenários que ganham o passo 2 (desvios em planta testados): AD = entrega, BD = com a galeria
CENARIO_ENTREGA = 'AD'   # cenário que vira os IFC por disciplina (CONDER/QG aceitam IFC no federado)
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'AP', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}

NOMES_DISC = {'AF': 'Água fria / reúso', 'ESG': 'Esgoto', 'AP': 'Pluvial (ESG-001)', 'DRE': 'Drenagem (campo e galeria)',
              'ELE': 'Elétrica enterrada', 'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)', 'EST': 'Estrutura as built (fundações)'}


def carregar():
    ter = Terreno(TERRENO)
    E = []
    E += lt.pressurizadas(os.path.join(F3, 'SAT_fase3_pressurizadas_cotas.csv'),
                          {'AF': 'AF', 'HID': 'HID', 'SDAI': 'SDAI', 'ELE': 'ELE'})
    esg = lt.gravidade(os.path.join(F2, 'SAT_fase2_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    ap = lt.gravidade(os.path.join(F2, 'SAT_fase2_AP_trechos.csv'), 'AP', 'AP', ter)
    cps = lt.gravidade(os.path.join(F2, 'SAT_fase2_CPS-DRE_trechos.csv'), 'DRE', 'CPS-DRE', ter)
    gal = lt.galeria(os.path.join(F2, 'SAT_fase2_DRE_galeria.csv'), 'DRE', 'DRE-GAL', pendente=True)
    E += esg + ap + cps + gal
    E += equip_sat.elementos_extra(E, ter, md)          # subidas e canaletas (19/10/2026)
    C = []
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_ESG_caixas.csv'), 'ESG', 'ESG', ter, esg, ignorar_tipos=('TS',))   # tanque séptico = ETE, fora
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_AP_caixas.csv'), 'AP', 'AP', ter, ap)
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_CPS-DRE_caixas.csv'), 'DRE', 'CPS-DRE', ter, cps)
    ele = [e for e in E if e['disc'] == 'ELE']; sdai = [e for e in E if e['disc'] == 'SDAI']
    C += lt.caixas_de_nos(os.path.join(F2, 'SAT_fase2_ELE_nos.csv'), 'ELE', 'ELE', ter, ele, {'CX 60x60': 0.60, 'POSTE': 0.80})
    C += lt.caixas_de_nos(os.path.join(F2, 'SAT_fase2_PCI_nos.csv'), 'SDAI', 'SDAI', ter, sdai, {'caixa de passagem SDAI': 0.30})
    C = [c for c in C if not c['id'].startswith('ELE:CP2-')]   # CPS ELE-002 é alternativa de tensão do mesmo traçado: vale o ELE-001
    C += equip_sat.caixas_equipamento(ter, md)          # equipamentos (postes, quadros, hidrantes, reservatórios...) como prismas (19/10/2026)
    import est_sat
    C += est_sat.caixas_estrutura(md, ter)              # fundações/pilares as built (RVTs de fundação + vínculos do IMP; BP4 ajustado), 19/10/2026
    cenarios = {
        'A': {'nome': 'sem a galeria Ø1200 (pendente)', 'excluir': lambda e: e.get('pendente', False)},
        'B': {'nome': 'com a galeria Ø1200', 'excluir': lambda e: False},
    }
    return {'elementos': E, 'caixas': C, 'terreno': ter, 'cenarios': cenarios}
