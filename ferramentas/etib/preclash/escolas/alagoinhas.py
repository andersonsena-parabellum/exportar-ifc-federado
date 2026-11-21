# -*- coding: utf-8 -*-
"""Adaptador da ETIB Alagoinhas — implantação no padrão novo (21/10/2026, o mesmo fluxo validado na Jandaíra).
Modelo montado dos RVT da escola, sem abrir o Revit: FERRAMENTAS/alagoinhas/ifc/alh_modelo.py (HS, DRN, ELE, INC e a estrutura
as built de todos os blocos com a malha real), terreno do IMP levado às CT das caixas de ESG/DRE das pranchas.
  - pressurizadas (AF, HID, SDAI, ELE): estudo de cota (água uma por rede; elétrica uma por trecho entre caixas, sempre acima
    da água), sem mergulho pontual; profundidade máxima 2,00 m (terreno ao topo); barrilete das bombas fora do estudo;
  - gravidade × gravidade: desloca a caixa de DRE ou ESG (até 0,60 m) no cenário AD; ELE/SDAI: caixa de passagem anda;
  - conexões comerciais 45°/90° (+ tês e junções); eletroduto (PVC corrugado), alarme (PEAD) e hidrante (PEAD) curvam no tubo até 30°;
    nenhum vértice anda em planta para caber na peça (o que não encaixa fica 'fora_do_comercial');
  - clash com a estrutura pela forma real (malha das peças as built).
Sigla ALI (o ALH é o bloco BA2, escolas/alagoinhas_ba2.py)."""
import os, sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.terreno import Terreno

ESCOLA = 'ETIB Alagoinhas'
SIGLA = 'ALI'
BASE = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS'
REL = os.path.join(BASE, 'RELATORIOS')
SAIDA = os.environ.get('ALI_SAIDA') or os.path.join(REL, 'PRECLASH_IMP_R03')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'alagoinhas_terreno.npz')
ORIGEM = (561500.0, 8658000.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (561470.0, 8657865.0, 561610.0, 8658070.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'estudo': {
        'por_rede': ['AF', 'HID'],
        'por_trecho': ['ELE', 'SDAI'],
        # elétrica 0,70 m (NBR 5410, premissa da modelagem de 15/10); alarme e hidrante 0,60; água fria 0,30
        'cob_min': {'AF': 0.30, 'HID': 0.60, 'ELE': 0.70, 'SDAI': 0.60},
        'prof_max': 2.00,
        'passo': 0.05,
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],
        # o reservatório é existente e a saída dele é rede enterrada: só junto das bombas a tubulação fica na cota do modelo
        'fixar_perto_de': ['IfcPump'], 'raio_fixo': 3.0,
    },
    'mergulho_local': False,
    'caixas_moveis_grav': ['DRE', 'ESG'],
    'desloc_max_grav': 0.60,
    'contornos': False,
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
    'estrutura': ['EST'],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}   # estrutura: só referência (alh_entrega.py)
NOMES_DISC = {'AF': 'Água fria (alimentação e distribuição)', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial',
              'ELE': 'Elétrica enterrada (BT e iluminação externa)', 'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)',
              'EST': 'Estrutura as built'}
# pontas que terminam fora de caixa e são reais (não falta de peça): a rede chega na edificação / quadro / reservatório
MOTIVO_PONTA = {'ELE': 'chegada na face da edificação (sobe para o quadro/predial; os eletrodutos foram cortados na face dos blocos)',
                'ESG': 'saída de esgoto da edificação (ramal predial)', 'DRE': 'ramal/descida pluvial da edificação',
                'AF': 'entrada da edificação ou ligação ao reservatório/barrilete das bombas', 'HID': 'ligação às bombas e ao reservatório (casa de bombas) ou hidrante dentro do bloco',
                'SDAI': 'chegada na central de alarme / edificação'}


def _esperada():
    import csv as _csv
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_AD_verificacao.csv')
    out = {}
    if os.path.exists(fn):
        for r in _csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
            if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: out[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]
            if r['tipo'] == 'pedaço curto' and r['disc'] == 'ELE': out[('pedaço curto', r['trecho'])] = 'trecho curto entre a caixa e a face da edificação'
    return out


VERIFICACAO_ESPERADA = _esperada()


def so_externo(E, C, log=print):
    """regra do Anderson (21/10/2026): só a rede externa, da face da parede para fora. Dentro do contorno dos prédios
    (alagoinhas/ifc/predios.py) nada é modelado nem conta como conflito: os trechos são cortados na face, o que fica dentro sai,
    caixas e equipamentos de dentro saem, e a estrutura dos prédios (fundações, pilares, vigas) sai do clash — vai só como
    referência no IFC de estrutura (alh_entrega.py)."""
    import predios as PR
    from shapely.geometry import Point
    U = PR.uniao(); Ui = U.buffer(-0.05)
    novos, n_cort, n_fora = [], 0, 0
    for e in E:
        pecas = PR.cortar(U, e['pts'])
        if not pecas: n_fora += 1; continue
        if len(pecas) == 1 and len(pecas[0]) == len(e['pts']) and np.allclose(pecas[0], e['pts']): novos.append(e); continue
        n_cort += 1
        for k, P in enumerate(pecas):
            if len(P) < 2: continue
            e2 = dict(e, id=e['id'] + (f'~{k + 1}' if len(pecas) > 1 else ''), pts=P, pts_sol=P.copy(), info=dict(e['info']))
            e2.pop('S', None); novos.append(e2)
    C2 = [c for c in C if c['disc'] != 'EST' and not Ui.contains(Point(c['E'], c['N']))]
    log(f'  só rede externa: {n_fora} trechos inteiros dentro dos prédios saíram, {n_cort} cortados na face; '
        f'{sum(1 for c in C if c["disc"] != "EST") - len(C2)} caixas/equipamentos de dentro e {sum(1 for c in C if c["disc"] == "EST")} peças de estrutura fora do clash')
    return novos, C2


def carregar():
    import alh_modelo as AM, alh_ajustes as AJ, json
    E, C, T = AM.montar()
    E, C = so_externo(E, C)
    # ajustes em planta sobre os pares críticos da rodada anterior (alh_pares.py): contornos curtos e caixas deslocadas
    fp = os.path.join(SAIDA, 'ALI_ajustes_pares.json')
    if os.path.exists(fp) and os.environ.get('ALI_SEM_AJUSTES') != '1':
        J = json.load(open(fp, encoding='utf-8'))
        AJ.mover_caixas(E, C, set(J['caixas']), SAIDA)
        AJ.contornar(E, C, [tuple(x) for x in J['contornos']], SAIDA)
        AJ.afastar_pontas(E, C, SAIDA)
    # decisões das 25 fichas da página de pendências (22/10/2026): ver alagoinhas/ifc/alh_decisoes.py
    import alh_decisoes as AD
    if os.environ.get('ALI_SEM_DECISOES') != '1':
        AD.antes_do_estudo(E, C, REGRAS)
        from preclash import desvio as _dv
        if not getattr(_dv, '_ali_dec', False):
            _apl = _dv.aplicar

            def aplicar(E_, C_, pend, regras, ter, log=print):
                feitos = _apl(E_, C_, pend, regras, ter, log)
                feitos += AD.depois_do_estudo(E_, C_, regras, ter, log)
                AD.gravar(SAIDA)
                return feitos
            _dv.aplicar, _dv._ali_dec = aplicar, True
    for c in C:                           # caixa de passagem que andou: tampa no terreno do lugar novo (esgoto/drenagem: CT/CF do projeto)
        if 'E0' in c and c['disc'] not in ('DRE', 'ESG'):
            dz = float(T.z([[c['E'], c['N']]])[0] - T.z([[c['E0'], c['N0']]])[0])
            if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
    from preclash import estudo as _est, clash as _cl
    if not getattr(_est, '_ali', False):
        _custo = _est.custo

        def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
            # elétrica/SDAI SEMPRE por cima da água (Anderson): cada cruzamento por baixo pesa como 10 colisões (Jandaíra)
            c, nc, nk = _custo(cand, outros, caixas, regras, cfg, disc, futuros, ter)
            if disc not in ('ELE', 'SDAI') or not len(outros[0]): return c, nc, nk
            oA, oB, oR, oD = outros; agua = np.isin(oD, ['AF', 'HID']); pen = 0
            for e, P in cand:
                for a, b_ in zip(P[:-1], P[1:]):
                    j = np.nonzero(agua & (np.minimum(oA[:, 0], oB[:, 0]) - 0.3 <= max(a[0], b_[0])) & (np.maximum(oA[:, 0], oB[:, 0]) + 0.3 >= min(a[0], b_[0]))
                                   & (np.minimum(oA[:, 1], oB[:, 1]) - 0.3 <= max(a[1], b_[1])) & (np.maximum(oA[:, 1], oB[:, 1]) + 0.3 >= min(a[1], b_[1])))[0]
                    if not len(j): continue
                    d, C1, C2 = _cl.dist_seg_seg(np.repeat(a[None], len(j), 0), np.repeat(b_[None], len(j), 0), oA[j], oB[j])
                    cruza = np.hypot(C1[:, 0] - C2[:, 0], C1[:, 1] - C2[:, 1]) < e['de'] / 2 + oR[j] + 0.05
                    pen += 100 * int(np.sum(cruza & (C1[:, 2] - e['de'] / 2 < C2[:, 2] + oR[j] + regras['folga'])))
            return c + pen, nc, nk
        _est.custo, _est._ali = custo, True
    return {'elementos': E, 'caixas': C, 'terreno': Terreno(TERRENO),
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas', 'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py): pranchas da implantação no padrão de executivo final
REVISAO = 'R03'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.15
EXECUTIVO_CAIXA_SEM_SIMBOLO = False   # (as caixas de EL-002 são só o texto 'Cx. 80x80 cm': tratadas em alh_exec.caixa_explodida)
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.60)
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1] if el.count(':') >= 1 else el
_IMP = '4 - IMPLANTAÇÃO-20261008T151806Z-1-001/4 - IMPLANTAÇÃO/'
_DWG = {'AGF-001': _IMP + '9 - REDE DE ÁGUA/24-049-ALH-SLJ-ETIB-IMP-PE-AGF-001-R06.dwg',
        'ESG-001': _IMP + '10 - REDE DE ESGOTO/24-049-ALH-SLJ-ETIB-IMP-PE-ESG-001-HIG-R06.dwg',
        'DRE-001': _IMP + '8 - DRENAGEM/24-049-ALH-SLJ-ETIB-IMP-PE-DRE-001-DRG-R04.dwg',
        'EL-001': _IMP + '12 - REDE ELÉTRICA E ILUMINAÇÃO/24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R07.dwg',
        'EL-002': _IMP + '12 - REDE ELÉTRICA E ILUMINAÇÃO/24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R05.dwg',
        # IN-001: o DWG do Drive não abre no console (ErrorStatus 53); vale o mesmo arquivo salvo de novo no AutoCAD do Anderson (22/10)
        'IN-001': 'RELATORIOS/EXECUTIVO_R03/_fonte_IN001/24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05.dwg'}


def folha(m):
    d = m['disc']; t = str(m.get('trecho') or ''); circ = str((m.get('info') or {}).get('circuito', ''))
    if d == 'ELE':
        if t.startswith('EL1') or 'EL-001' in circ: return 'EL-001'
        return 'EL-002'
    return {'AF': 'AGF-001', 'ESG': 'ESG-001', 'DRE': 'DRE-001', 'HID': 'IN-001', 'SDAI': 'IN-001'}.get(d)


def executivo_dwg(m):
    f = m.get('folha') or folha(m)
    return _DWG.get(f)


def _transf():
    import json as _j
    af = (0.04622757474485582, (561398.39297302, 8657855.98329653))       # AF/ESG/DRE local -> UTM (ICP do ARQ_BASE, 2 mm)
    el = _j.load(open(r'D:\Projeto Modelagem\FERRAMENTAS\eletrica\transformacao_ELE_local_para_UTM.json', encoding='utf-8'))
    a = np.radians(af[0]); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    t_in = tuple(np.array(af[1]) + R @ np.array([65.3108830209, 27.4284168787]))   # IN local + (65,31; 27,43) = AF local
    return {_DWG['AGF-001']: af, _DWG['ESG-001']: af, _DWG['DRE-001']: af, _DWG['IN-001']: (af[0], t_in),
            _DWG['EL-001']: (el['EL1']['rot_deg'], tuple(el['EL1']['t'])), _DWG['EL-002']: (el['EL2']['rot_deg'], tuple(el['EL2']['t']))}


TRANSF_DWG = _transf()
