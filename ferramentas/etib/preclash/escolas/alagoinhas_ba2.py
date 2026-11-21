# -*- coding: utf-8 -*-
"""Adaptador da ETIB Alagoinhas — bloco BA2 (24 salas, instalações INTERNAS do bloco) para o preclash. Sigla ALH.
Fonte (só leitura): ETIB-ALAGOINHAS/RELATORIOS/BA2_FASE3_2026-10-18/ (gerado por
FERRAMENTAS/georef/work/ALAGOINHAS_BA2/scripts/ba2_fase3.py a partir das redes da fase 2 e dos _GEO do BA2).
Opções recomendadas adotadas (o usuário liberou seguir com elas em 18/10/2026):
  - pluvial = hidrossanitário ESG-001/002 R01 (a drenagem DRE-001/002 R00 e a DRN da implantação ficam como referência);
  - premissas de cota da fase 3 (BA2_fase3_resumo.md), com as cotas do ARQ as built lidas no Revit em 19/10: redes de forro ACIMA
    do forro (139,18 / 143,38), em camadas sob a laje e entre as vigas pré-moldadas; térreo enterrado a 0,30 m do piso (136,10).
  - equipamentos (evaporadoras, condensadoras, quadros, abrigos) como caixas retangulares giradas.
Rede interna no forro: o 'terreno' do preclash é o piso do térreo (136,10, platô) e o cobrimento das redes de teto é NEGATIVO
(cob = piso − topo do tubo); assim perfil_por_recobrimento(), o solver ('por cima' limitado ao fundo da viga) e o desvio em
planta mantêm a rede na altura do forro.
Padrão novo (21/10/2026, o fluxo validado na Jandaíra):
  - estrutura as built (ECC/FUN) pela FORMA REAL: a malha das peças extraídas dos RVT (compat_R02/geo/EST_mesh.tsv), no lugar das
    caixas envolventes e das vigas em cápsulas da fase 3; o clash e o IFC usam a malha;
  - material pela legenda das pranchas e pelo memorial (não pelo tipo do Revit): AF PVC soldável; esgoto e ventilação PVC Série
    Normal; pluvial PVC Série Reforçada (drenos de ar-condicionado em PVC soldável); frigorígenas em cobre com isolamento
    elastomérico; eletroduto rígido no entreforro, PVC corrugado flexível no contrapiso e aço galvanizado na cobertura (alimentação
    das condensadoras); SDAI em ferro galvanizado aparente e PEAD no contrapiso; hidrantes em aço galvanizado aparente e PEAD enterrado;
  - profundidade máxima 2,00 m (terreno ao topo; parâmetro do projeto, Anderson 20/10/2026), peças comerciais 45°/90° (+ tês e
    junções), eletroduto e alarme flexíveis curvam no tubo até 30°; nenhum vértice anda em planta para caber na peça."""
import os, csv, json, re
import numpy as np
from preclash import modelo as md
from preclash import leitura as lt
from preclash.terreno import Terreno
from preclash.leitura_ifc import retangulo_minimo

ESCOLA = 'ETIB Alagoinhas — bloco BA2'
SIGLA = 'ALH'
BASE = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS'
F3 = os.path.join(BASE, 'RELATORIOS', 'BA2_FASE3_2026-10-18')
GEO = os.path.join(BASE, r'RELATORIOS\compat_R02\geo')
SAIDA = os.environ.get('ALH_SAIDA') or os.path.join(BASE, 'RELATORIOS', 'PRECLASH_BA2_R03')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'alagoinhas_ba2_terreno.npz')
ORIGEM = (561500.0, 8658000.0, 0.0)      # origem interna dos RVTs da ETIB — AGENTS.md
EPSG = 31984                             # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (561518.0, 8657993.0, 561602.0, 8658056.0)

REGRAS = {
    'folga': 0.10,                                           # instalações internas: 10 cm entre redes (no enterrado da implantação era 0,20)
    'ordem_mover': ['ELE', 'SDAI', 'CLI', 'HID', 'AF'],     # ESG, ventilação, pluvial e estrutura ficam fixas
    'dz_max': {'ELE': 0.70, 'SDAI': 0.70, 'CLI': 0.30, 'HID': 0.50, 'AF': 0.40},   # até o forro (139,18 / 143,38) a partir das camadas sob a laje
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'CLI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'agua_acima_de': ['ESG'],
    'ligacao_entre': [{'AP', 'DRE'}, {'AP', 'CLI'}],         # dreno de condensado (AP Ø32/40) termina na evaporadora (CLI)
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
    'estrutura': ['EST'],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'CV', 'AP'), 'ELE': ('ELE',), 'CLI': ('CLI',), 'PCIP': ('HID', 'SDAI'), 'EST': ('EST',)}
NOMES_DISC = {'AF': 'Água fria', 'ESG': 'Esgoto', 'CV': 'Ventilação', 'AP': 'Pluvial (ESG-001/002)', 'ELE': 'Elétrica',
              'CLI': 'Climatização', 'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)', 'EST': 'Estrutura as built'}
VERIFICACAO_ESPERADA = {}


def _pts(s):
    return [tuple(float(v) for v in q.split()) for q in s.split('|')]


def material(disc, rede, cob, dn, info):
    """material pela legenda das pranchas do BA2 e pelos memoriais (21/10/2026)."""
    enterrado = cob is not None and cob >= 0
    if disc == 'AF': return 'Tubo PVC soldável marrom'
    if disc in ('ESG', 'CV'): return 'Tubo PVC Série Normal'
    if disc == 'AP': return 'Tubo PVC soldável (dreno de ar-condicionado)' if (dn or 100) <= 40 else 'Tubo PVC Série Reforçada'
    if disc == 'CLI': return 'Tubo de cobre sem costura com isolamento elastomérico'
    if disc == 'ELE':
        if rede == 'CLI': return 'Eletroduto de aço galvanizado a fogo (cobertura)'
        return 'Eletroduto PVC corrugado flexível' if enterrado else 'Eletroduto PVC rígido (entreforro)'
    if disc == 'SDAI': return 'Eletroduto PEAD flexível' if enterrado else 'Eletroduto de ferro galvanizado (aparente)'
    if disc == 'HID': return 'Tubo PEAD' if enterrado else 'Tubo de aço galvanizado'
    return info.get('material')


def estrutura():
    """peças as built do BA2 (ECC e FUN) com a malha real, em UTM e cota absoluta."""
    C = []; o = np.array(ORIGEM)
    for l in open(os.path.join(GEO, 'EST_mesh.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t', 7)
        if len(r) < 8 or 'ETIB-BA2-' not in r[4] or r[2] not in ('Fundações estruturais', 'Pilares estruturais', 'Quadro estrutural'): continue
        V = np.array(r[7].split(','), dtype=float)
        if len(V) % 9: continue
        V = V.reshape(-1, 3) + o; lo, hi = V.min(0), V.max(0)
        cx, cy, lx, ly, rot, _ = retangulo_minimo(V[:, :2])
        tipo = 'pilar' if r[2].startswith('Pilar') else ('viga' if r[2].startswith('Quadro') else 'fundação')
        C.append(md.caixa_retangular(f'EST:{r[1]}', 'EST', 'EST', cx, cy, lx, ly, rot, lo[2], hi[2], nome=r[3].split(' : ')[-1][:60], tipo=tipo,
                                     bloco='BA2', familia=r[3][:80], malha=V.reshape(-1, 3, 3), cota='as built'))
    return C


def carregar():
    ter = Terreno(TERRENO)
    E, C = [], []
    with open(os.path.join(F3, 'BA2_fase3_elementos.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            if r['disc'] == 'EST': continue                       # estrutura: forma real (estrutura())
            info = json.loads(r['info'] or '{}')
            de = float(r['DE_m']); P = _pts(r['pontos_UTM'])
            movel = None if r['movel'] == '' else bool(int(r['movel']))
            cob = float(r['cobrimento_m']) if r['cobrimento_m'] not in ('', None) else None
            info['material'] = material(r['disc'], r['rede'], cob, info.get('DN_mm'), info)
            if r['modo'] == '2d_cob':
                P3 = lt.perfil_por_recobrimento([p[:2] for p in P], de, cob, ter)
                E.append(md.elemento(r['id'], r['disc'], r['rede'], r['trecho'], 'pressao', de, P3, cob_min=cob, movel=movel,
                                     pavimento=r['pavimento'], **info))
            else:
                if movel is None: movel = False
                E.append(md.elemento(r['id'], r['disc'], r['rede'], r['trecho'], r['tipo'], de, P, movel=movel, pavimento=r['pavimento'], **info))
    with open(os.path.join(F3, 'BA2_fase3_caixas.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            if r['disc'] == 'EST': continue
            if r['forma'] == 'r':
                C.append(md.caixa_retangular(r['id'], r['disc'], r['rede'], float(r['E']), float(r['N']), float(r['lx']), float(r['ly']), float(r['rot_rad']),
                                             float(r['zb']), float(r['zt']), nome=r['nome'], tipo=r['tipo'], cota=r['cota'],
                                             material='Alvenaria; tampa de concreto' if 'alvenaria' in r['tipo'] else None))
            else:
                C.append(md.caixa(r['id'], r['disc'], r['rede'], r['forma'], float(r['E']), float(r['N']), float(r['meia']), float(r['zb']), float(r['zt']),
                                  nome=r['nome'], tipo=r['tipo'], cota=r['cota'], material='Alvenaria; tampa de concreto' if 'alvenaria' in r['tipo'] else None))
    # equipamentos (evaporadoras, condensadoras, quadros, abrigos): equip_ba2.py
    CLS = {'evaporadora': 'IfcUnitaryEquipment', 'condensadora': 'IfcUnitaryEquipment', 'quadro': 'IfcElectricDistributionBoard',
           'abrigo': 'IfcFireSuppressionTerminal'}
    with open(os.path.join(F3, 'BA2_fase3_equipamentos.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            cl = next((v for k, v in CLS.items() if k in r['tipo']), None)
            C.append(md.caixa_retangular(r['id'], r['disc'], r['rede'], float(r['E']), float(r['N']), float(r['lx']), float(r['ly']), float(r['rot_rad']),
                                         float(r['zb']), float(r['zt']), nome=r['nome'], tipo=r['tipo'], cota=r['cota'],
                                         **({'classe_ifc': cl} if cl else {})))      # sem 'equipamento': condensadora/abrigo podem andar (v4)
    C += estrutura()
    cenarios = {'A': {'nome': 'pluvial do hidrossanitário (ESG-001/002 R01) e premissas de cota recomendadas', 'excluir': lambda e: False}}
    return {'elementos': E, 'caixas': C, 'terreno': ter, 'cenarios': cenarios}
