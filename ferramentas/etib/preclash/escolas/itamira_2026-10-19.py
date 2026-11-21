# -*- coding: utf-8 -*-
"""Adaptador da ETIB Aporá Itamira para o preclash.
Fontes (só leitura): ETIB-APORA-ITAMIRA/RELATORIOS/PRECLASH_INSUMOS_2026-10-18 (thread da escola, 18/10/2026):
  - ITA_asbuilt_campo_trechos.csv / ITA_asbuilt_campo_caixas.csv: redes do campo JÁ EXECUTADAS, lidas do IFC as built do IMP
    (24-049-APR-ITA-ETIB-IMP-PE-001-MOD-R00.ifc, coordenadas compartilhadas = UTM): drenos, tubos lisos, calhas, caixas de areia;
    eletrodutos enterrados e caixas CX da iluminação do campo. Ficam fixas (existentes);
  - ITA_ELE_trechos.csv / ITA_ELE_caixas.csv: EL-001-ELG-R00 da implantação georreferenciada (ELE-01..05, CX-01, CX-02) e a
    PROPOSTA ELE-06 (alimentação do QD1 executado no canto S do campo; caixas CX-P1..P3).
Decisões sem resposta do usuário (opção recomendada, 18/10/2026):
  - o campo vale como executado (IFC as built), não a SIT R01 (40x20) nem as pranchas CPS (que não batem com o as built);
  - drenagem: a DRE-001 R00 da implantação foi substituída pelo executado (as 7 saídas atravessam o muro e descarregam no limite do
    terreno, como no memorial do campo) -> sem rede de drenagem nova; a do campo entra como existente;
  - elétrica: proposta ELE-06 (CX-02 -> por dentro dos muros NE e SE do campo, a 0,8 m -> QD1) no lugar de ELE-04/05, que vão ao
    QDLT antigo (63 m do QD1) e cujo ELE-04 atravessa o reservatório executado (cenário A, o de entrega). Cenário B = R00 como está;
  - recobrimento da elétrica 0,70 m (NBR 5410, mesma premissa da Alagoinhas) sobre o terreno as built.
Terreno: IFC as built do IMP (faces de topo do sólido topográfico) em escolas/dados/itamira_terreno.npz.
Equipamentos (19/10/2026): ITA_equipamentos.csv (gerado por FERRAMENTAS/georef/work/ITAMIRA/scr/equip_ita.py a partir do IFC as built):
4 postes do campo, QD1, QGBT, QD-BOMB, gerador, 6 ralos, reservatório e a base dele — caixas (cilindro ou md.caixa_retangular)
da rede do existente, que entram no clash contra a elétrica nova, no IFC e no visualizador."""
import os
import math
from preclash import leitura as lt
from preclash import modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Aporá Itamira'
SIGLA = 'ITA'
BASE = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA'
INS = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_INSUMOS_2026-10-18')
SAIDA = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'itamira_terreno.npz')
ORIGEM = (584400.0, 8704300.0, 0.0)       # origem proposta dos RVTs (E, N, cota) — registrada no licoes-modelagem.md
EPSG = 31984                              # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (584330.0, 8704195.0, 584455.0, 8704320.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE'],                       # só a elétrica nova muda de cota; o campo executado e a drenagem ficam fixos
    'dz_max': {'ELE': 1.00},
    'prof_max_topo': {'ELE': 2.00},
    'agua_acima_de': [],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
CENARIO_PROJETO = 'A'
DISCIPLINAS_ENTREGA = {'HIDRO': ('DRE', 'AF'), 'ELE': ('ELE',)}
NOMES_DISC = {'DRE': 'Drenagem do campo (as built)', 'ELE': 'Elétrica enterrada (implantação + campo as built)',
              'AF': 'Água fria (reservatório existente)'}
COB_ELE = 0.70
EXIST = 'AS BUILT CAMPO'          # uma rede só para o existente: o executado não se testa contra ele mesmo


def _existentes():
    E, C = [], []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_asbuilt_campo_trechos.csv')):
        cat = r['categoria']
        disc = 'ELE' if cat == 'eletroduto' else 'DRE'
        tipo = 'pressao' if disc == 'ELE' else 'gravidade'
        P = [(lt.fl(r['E_ini']), lt.fl(r['N_ini']), lt.fl(r['eixo_ini'])), (lt.fl(r['E_fim']), lt.fl(r['N_fim']), lt.fl(r['eixo_fim']))]
        nome = {'dreno': 'dreno PVC corrugado perfurado', 'tubo_liso': 'tubo PVC liso', 'calha': 'calha semicircular de concreto',
                'eletroduto': 'eletroduto do campo'}[cat]
        E.append(md.elemento(f"AB:{r['id']}", disc, EXIST, f"AB-{r['id']}", tipo, lt.fl(r['DE_m']), P, movel=False,
                             material=nome, cota='as built (IFC do IMP)', obs='existente, executado'))
    for r in lt.ler_csv(os.path.join(INS, 'ITA_asbuilt_campo_caixas.csv')):
        disc = 'DRE' if r['tipo'] == 'CA' else 'ELE'
        C.append(md.caixa(f"AB:{r['caixa']}", disc, EXIST, 'q', lt.fl(r['E']), lt.fl(r['N']), lt.fl(r['meia_m']), lt.fl(r['zb']), lt.fl(r['zt']),
                          nome=r['caixa'], tipo='caixa de areia (as built)' if disc == 'DRE' else 'caixa CX do campo (as built)', cota='as built (IFC do IMP)'))
    return E, C


def _ele(ter):
    E = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_ELE_trechos.csv')):
        pts = [tuple(float(v) for v in xy.split(',')) for xy in r['vertices_UTM'].split()]
        de = lt.fl(r['DE_mm']) / 1000.0
        P = lt.perfil_por_recobrimento(pts, de, COB_ELE, ter)
        E.append(md.elemento(f"ELE:{r['trecho']}", 'ELE', 'ELE', r['trecho'], 'pressao', de, P, cob_min=COB_ELE,
                             circuito=r['circuito'], diametro=r['diam_pol'], origem=r['origem'],
                             cota=f'premissa: topo a {COB_ELE:.2f} m do terreno as built (NBR 5410)', obs=r['obs']))
    C = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_ELE_caixas.csv')):
        x, y = lt.fl(r['E']), lt.fl(r['N']); zt = float(ter.z([[x, y]])[0])
        zs = [p[2] - e['de'] / 2 for e in E for p in e['pts'] if ((p[0] - x) ** 2 + (p[1] - y) ** 2) ** 0.5 < 1.2]
        zb = (min(zs) if zs else zt - COB_ELE - 0.06) - 0.15
        C.append(md.caixa(f"ELE:{r['caixa']}", 'ELE', 'ELE', 'q', x, y, lt.fl(r['lado_m']) / 2 + 0.05, zb, zt, nome=r['caixa'], tipo=r['tipo'],
                          origem=r['origem'], cota='topo no terreno as built; fundo 0,15 m abaixo do eletroduto mais baixo'))
    return E, C


def _equipamentos():
    C = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_equipamentos.csv')):
        E, N, lx, ly, zb, zt = (lt.fl(r[k]) for k in ('E', 'N', 'lx', 'ly', 'zb', 'zt'))
        info = dict(nome=r['id'], tipo=r['tipo'], equipamento='sim', classe_ifc=r['classe_ifc'], pred=r['pred'], cruzeta_m=r['cruzeta_m'],
                    rot_graus=r['rot_graus'], origem=r['origem'], premissa=r['premissa'], cota='as built (IFC do IMP)' if 'IFC' in r['origem'] else 'premissa')
        if r['forma'] == 'c':
            C.append(md.caixa(f"EQ:{r['id']}", r['disciplina'], EXIST, 'c', E, N, lx / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f"EQ:{r['id']}", r['disciplina'], EXIST, E, N, lx, ly, math.radians(lt.fl(r['rot_graus'])), zb, zt, **info))
    return C


def carregar():
    ter = Terreno(TERRENO)
    eX, cX = _existentes()
    cX = cX + _equipamentos()
    eE, cE = _ele(ter)
    velhos = ('ELE-04', 'ELE-05'); novos = ('ELE-06',)
    eA = eX + [e for e in eE if e['trecho'] not in velhos]
    cA = cX + [c for c in cE if c['info']['nome'] != 'CX-01']
    eB = eX + [e for e in eE if e['trecho'] not in novos]
    cB = cX + [c for c in cE if not c['info']['nome'].startswith('CX-P')]
    nada = lambda e: False
    cenarios = {
        'A': {'nome': 'proposta: alimentação nova do QD1 (ELE-06) no lugar de ELE-04/05; campo as built', 'excluir': nada,
              'elementos': eA, 'caixas': cA},
        'B': {'nome': 'EL-001 R00 como está (ELE-04/05 até o QDLT antigo); campo as built', 'excluir': nada,
              'elementos': eB, 'caixas': cB},
    }
    return {'elementos': eA, 'caixas': cA, 'terreno': ter, 'cenarios': cenarios}
