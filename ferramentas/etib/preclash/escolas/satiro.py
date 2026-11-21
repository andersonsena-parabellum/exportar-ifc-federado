# -*- coding: utf-8 -*-
"""Adaptador da ETIB Sátiro Dias — fluxo novo (21/10/2026, o mesmo validado na Jandaíra e em Alagoinhas).
A escola não tem modelos de rede em RVT: as redes vêm das fases 2/3 feitas sobre os DWG georreferenciados (RELATORIOS/FASE2_REDES_2026-10-18,
FASE3_COTAS_2026-10-18; o adaptador anterior, de 19/10, ficou em escolas/satiro_2026-10-19.py). Daqui para a frente vale o padrão novo:
  - só rede externa (Anderson, 21/10/2026): contorno dos prédios pela estrutura as built (FERRAMENTAS/satiro/ifc/predios.py); a rede é
    cortada na face e o que fica dentro (trechos, caixas, quadros) sai do modelo e do clash; a estrutura dos prédios não entra no clash;
  - terreno do IMP as built levado às CT das caixas de esgoto/pluvial/drenagem do campo das pranchas (vale a base);
  - pressurizadas (AF, HID, SDAI, ELE): estudo de cota (água uma por rede; elétrica uma por trecho entre caixas, sempre acima da água),
    sem mergulho pontual; profundidade máxima 2,00 m (terreno ao topo) para todas; perto dos reservatórios fica a cota do modelo;
  - gravidade (ESG, pluvial, drenagem do campo): cotas das pranchas; gravidade × gravidade desloca a caixa até 0,60 m (cenário AD);
  - conexões comerciais 45°/90°; eletroduto (PVC corrugado / PEAD) e hidrante (PEAD) curvam no tubo até 30°; vértice não anda em planta;
  - material pela legenda das pranchas: AF PVC soldável marrom (AF-001); esgoto PVC Série Normal; pluvial PVC Série Reforçada até 150 mm
    (nota P3 do ESG-001), Série Normal em 200 e Vinilfort a partir de 250; dreno PVC corrugado perfurado (PVC-DR); dreno do ar-condicionado
    PVC soldável; elétrica eletroduto PVC corrugado flexível (EL-001/002) e corrugado PEAD no campo (CPS ELE-001); hidrante PEAD e
    SDAI eletroduto PEAD (IN-001);
  - galeria 2 × Ø1200 ("rede futura se necessário") fora, como na entrega anterior: decisão da construtora pendente;
  - canaletas de superfície fora (não são rede enterrada; a posição do desenho é aproximada e só gerava falso conflito com postes)."""
import os, sys, csv, math, json
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\ifc')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro')
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Sátiro Dias'
SIGLA = 'SAT'
BASE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS'
REL = os.path.join(BASE, 'RELATORIOS')
F2 = os.path.join(REL, 'FASE2_REDES_2026-10-18')
F3 = os.path.join(REL, 'FASE3_COTAS_2026-10-18')
SAIDA = os.environ.get('SAT_SAIDA') or os.path.join(REL, 'PRECLASH_2026-10-21')
DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
TER_IMP = os.path.join(DADOS, 'satiro_terreno.npz')            # IMP as built (satiro_terreno.py)
TERRENO = os.path.join(DADOS, 'satiro_terreno_base.npz')       # o mesmo levado às CT das caixas das pranchas
ORIGEM = (546000.0, 8716200.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (545840.0, 8716080.0, 546070.0, 8716290.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'estudo': {
        'por_rede': ['AF', 'HID'],
        'por_trecho': ['ELE', 'SDAI'],
        # premissas da entrega de 19/10: AF 0,30; hidrante e SDAI 0,50 (nota 5 do IN-001); elétrica 0,70 (NBR 5410)
        'cob_min': {'AF': 0.30, 'HID': 0.50, 'ELE': 0.70, 'SDAI': 0.50},
        'prof_max': 1.90,          # 2,00 m é o máximo do projeto; 0,10 m de margem para a descida dos taludes medida no terreno de entrega
        'passo': 0.05,
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],
        # reservatórios no chão: a AF chega enterrada e sobe dentro do equipamento (nada fica na cota do modelo)
        'fixar_perto_de': [], 'raio_fixo': 3.0,
        # o IMP tem covas de 0,3–0,5 m nos pisos (vazios de caixa/canaleta do as built): o perfil não mergulha nelas
        'preencher_rebaixo': 1,
    },
    'mergulho_local': False,
    'caixas_moveis_grav': ['DRE', 'ESG', 'AP'],
    'desloc_max_grav': 0.60,
    'contornos': False,
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
    'estrutura': ['EST'],
    'ligacao_entre': [{'AP', 'DRE'}],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'AP', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}
NOMES_DISC = {'AF': 'Água fria (alimentação, distribuição e reúso)', 'ESG': 'Esgoto', 'AP': 'Drenagem pluvial',
              'DRE': 'Drenagem do campo society', 'ELE': 'Elétrica enterrada (alimentação e iluminação externa)', 'HID': 'Hidrantes (PCI)',
              'SDAI': 'SDAI (PCI)', 'EST': 'Estrutura as built'}
MOTIVO_PONTA = {'ELE': 'chegada na face da edificação ou no quadro/poste (sobe para o quadro)',
                'ESG': 'saída de esgoto da edificação (ramal predial)', 'AP': 'ramal/descida pluvial da edificação',
                'DRE': 'início do dreno do campo', 'AF': 'entrada da edificação, torneira de jardim ou ligação ao reservatório',
                'HID': 'hidrante, recalque ou casa de bombas', 'SDAI': 'chegada na central de alarme / edificação'}

MAT_AF = 'Tubo PVC soldável marrom'
COB_HID = float(os.environ.get('SAT_COB_HID') or 0) or None
COB_FIXO = {}        # recobrimento fixado por elemento (o estudo não procura outro; senão ele desce até achar zero folga curta)
MAT_PRESS = {'HID': 'Tubo PEAD', 'SDAI': 'Eletroduto PEAD flexível'}


def mat_grav(disc, mat, dn, classe):
    m = (mat or '').upper().replace('-', '')
    if 'DR' in m or 'dreno (PVC-DR)' in (classe or ''): return 'Tubo PVC corrugado perfurado (dreno)'
    if (classe or '') == 'dreno' or (dn and dn <= 50 and disc == 'AP'): return 'Tubo PVC soldável'
    if disc == 'ESG': return 'Tubo PVC Série Reforçada' if 'PVCR' in m else 'Tubo PVC Série Normal'
    if dn and dn >= 250: return 'Tubo PVC Vinilfort'
    if dn and dn >= 200: return 'Tubo PVC Série Normal'
    return 'Tubo PVC Série Reforçada'


def _esperada():
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_AD_verificacao.csv')
    out = {}
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
            if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: out[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]
            if r['tipo'] == 'pedaço curto' and r['disc'] in ('ELE', 'SDAI'): out[('pedaço curto', r['trecho'])] = 'trecho curto entre a caixa e a face da edificação'
    return out


VERIFICACAO_ESPERADA = _esperada()


def terreno_base(log=print):
    """IMP as built -> levado às CT das caixas de gravidade das pranchas (vale a base; só a CA-01 diverge, +0,85 m)."""
    from preclash import terreno as tr
    base = []
    for fn, dsc in (('SAT_fase2_ESG_caixas.csv', 'ESG'), ('SAT_fase2_AP_caixas.csv', 'AP'), ('SAT_fase2_CPS-DRE_caixas.csv', 'DRE')):
        for r in lt.ler_csv(os.path.join(F2, fn)):
            ct = lt.fl(r.get('CT'))
            if ct is None or r['tipo'] == 'TS': continue
            E_, N_ = CAIXA_NOVA.get(dsc + ':' + r['caixa'], (lt.fl(r['E']), lt.fl(r['N'])))   # caixa que anda: a CT vale no lugar novo
            base.append((E_, N_, ct))
    rel = tr.ajustar(TER_IMP, base, TERRENO, modo='local', raio=6.0, fonte='CT das caixas de esgoto, pluvial e drenagem do campo das pranchas')
    log(f"  terreno: {rel['pontos']} CT; resíduo mediano {rel['antes_mediana']:+.2f} m (p95 {rel['antes_p95_abs']:.2f}) -> "
        f"{rel['depois_mediana']:+.3f} (p95 {rel['depois_p95_abs']:.3f})")
    # o terreno do clash passa a ser a própria malha de 0,50 m que vai no IFC de entrega (mesmos vértices e triângulos): a Revisão
    # mede profundidade e degrau nela, e nos taludes a interpolação de outra malha dava até 0,4 m de diferença
    T = Terreno(TERRENO); V, F = T.grade(CAIXA_OBRA, 0.5)
    D = dict(np.load(TERRENO, allow_pickle=False)); D['pts'] = V; D['tri'] = F
    D['fonte'] = str(D.get('fonte', '')) + ' + reamostrado na malha de 0,50 m da entrega'
    np.savez_compressed(TERRENO, **D)
    return rel


def equipamentos(ter):
    """equipamentos da implantação (equip_sat.py: postes, quadros, hidrantes, reservatórios, torneiras) como caixas com a classe IFC."""
    import equip_sat
    out = []
    for q in equip_sat.equipamentos(ter):
        # sem a fundação de premissa abaixo do chão: a rede da própria disciplina chega por baixo do equipamento (reservatório,
        # torneira, hidrante, quadro); a base enterrada do poste é a caixa 80x80 do nó
        zt0 = q['terreno'] + float(q['base_sobre_terreno'])
        zb = q['terreno'] + (0.30 if q['forma'] == 'poste' else 0.0) if zt0 <= q['terreno'] + 0.01 else zt0
        lx, ly = float(q['dim_a']), float(q['dim_b'])
        if q['forma'] in ('poste', 'cil'): ly = lx
        if q['forma'] == 'taca': lx = ly = float(q['dim_b'])
        pred = {'HID-RECALQUE': 'BREECHINGINLET', 'MEDICAO': 'ENERGYMETER'}.get(q['id'])
        out.append(md.caixa_retangular(f"EQ:{q['id']}", q['disciplina'], q['disciplina'], q['E'], q['N'], lx, ly, math.radians(q['rot_graus']),
                                       zb, zt0 + float(q['altura']), nome=q['id'], tipo=q['tipo'], equipamento=True, classe_ifc=q['classe_ifc'],
                                       **({'pred': pred} if pred else {}), cota='terreno do IMP'))
    return out


def canaletas(ter):
    """canaletas de superfície (pluvial do ESG-001 e campo): prisma de 0,40 × 0,40 m (campo 0,30) por segmento, topo no terreno.
    Só obstáculo do clash (as pressurizadas passam por baixo); não vão para o IFC de entrega."""
    can = [(r['canaleta'], np.array([[lt.fl(r['E_ini']), lt.fl(r['N_ini'])], [lt.fl(r['E_fim']), lt.fl(r['N_fim'])]]), 'AP', 0.40)
           for r in lt.ler_csv(os.path.join(F2, 'SAT_fase2_AP_canaletas.csv'))]
    import sat_comum as sc
    J = json.load(open(os.path.join(sc.WRK, 'cps_dre_rede.json'), encoding='utf-8'))
    can += [(f'CPS-CAN-{i + 1:02d}', np.array(c)[:, :2], 'DRE', 0.30) for i, c in enumerate(J['canaletas'])]
    out = []
    for nome, P, disc, b in can:
        for k, (a, c) in enumerate(zip(P[:-1], P[1:])):
            L = float(np.hypot(*(c - a)))
            if L < 0.05: continue
            Q = np.array([a + (c - a) * t for t in np.linspace(0, 1, max(2, int(L / 1.0) + 1))]); z = ter.z(Q)
            if np.isnan(z).all(): continue
            m = (a + c) / 2
            out.append(md.caixa_retangular(f'CAN:{nome}.{k + 1}', disc, 'CPS-DRE' if disc == 'DRE' else 'AP', m[0], m[1], L, b,
                                           math.atan2(*(c - a)[::-1]), float(np.nanmin(z)) - b, float(np.nanmax(z)),
                                           nome=f'{nome} (canaleta)', tipo='canaleta de superfície', so_clash=True, cota='topo no terreno'))
    return out


def _ca15(E, C):
    """a CA-06 do CPS DRE-001 é a CA-15 do ESG-001 (0,53 m entre os dois desenhos; o campo descarrega nela): fica a CA-15, com as
    cotas do ESG-001, e os dois trechos do campo que chegam/saem da CA-06 vão para o centro dela. O AF-11 (reúso) começa no
    FILTRO-01 da pluvial: a ponta para na face do filtro."""
    c15 = next(c for c in C if c['id'] == 'AP:CA-15')
    C[:] = [c for c in C if c['id'] != 'CPS-DRE:CPS-CA-06']
    for e in E:
        if e['rede'] != 'CPS-DRE': continue
        for k, no in ((0, 'de_no'), (-1, 'para_no')):
            if e['info'].get(no) == 'CPS-CA-06':
                e['pts'][k, :2] = (c15['E'], c15['N'])
                if k == -1: e['pts'][k, 2] = max(e['pts'][k, 2], c15['info']['CF'] + e['de'] / 2)
                e['pts_sol'] = e['pts'].copy()
    fil = next(c for c in C if c['id'] == 'AP:FILTRO-01')
    import predios as PR
    from shapely.geometry import box as _box
    for e in E:
        if e['trecho'] != 'AF-11': continue
        h = fil['meia'] + e['de'] / 2 + 0.05
        pecas = PR.cortar(_box(fil['E'] - h, fil['N'] - h, fil['E'] + h, fil['N'] + h), e['pts'])
        e['pts'] = max(pecas, key=lambda P: np.sum(np.hypot(*np.diff(P[:, :2], axis=0).T))); e['pts_sol'] = e['pts'].copy()


def so_externo(E, C, log=print):
    """regra do Anderson (21/10/2026): só a rede externa, da face da parede para fora (ver o mesmo trecho de escolas/alagoinhas.py)."""
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
            e2 = dict(e, id=e['id'] + (f'~{k + 1}' if len(pecas) > 1 else ''), pts=P, pts_sol=P.copy(), info=dict(e['info']), cortado=True)
            e2.pop('S', None); novos.append(e2)
    C2 = [c for c in C if c['disc'] != 'EST' and not Ui.contains(Point(c['E'], c['N']))]
    log(f'  só rede externa: {n_fora} trechos inteiros dentro dos prédios saíram, {n_cort} cortados na face; '
        f'{sum(1 for c in C if c["disc"] != "EST") - len(C2)} caixas/equipamentos de dentro saíram')
    return novos, C2


def carregar():
    if not os.path.exists(TERRENO) or os.environ.get('SAT_TERRENO_REFAZER') == '1': terreno_base()
    ter = Terreno(TERRENO)
    E = []
    pr = lt.pressurizadas(os.path.join(F3, 'SAT_fase3_pressurizadas_cotas.csv'), {'AF': 'AF', 'HID': 'HID', 'SDAI': 'SDAI', 'ELE': 'ELE'})
    for e in pr:
        if e['disc'] == 'AF':
            sub = e['info'].get('sub') or 'distribuição'
            if sub == 'AF': sub = 'distribuição'
            # alimentação e distribuição são a mesma água potável, ligadas no reservatório/casa de bombas: uma rede só
            e['rede'] = 'AF-' + ('potável' if sub in ('alimentação', 'distribuição') else sub); e['info']['material'] = MAT_AF
            # reúso (torneiras de jardim) corre sob a pluvial rasa do platô 233 junto com a iluminação externa: a 1,40 m deixa a faixa
            # entre o fundo da pluvial e o topo da água para a elétrica, que fica sempre acima da água, e passa sobre a pluvial Ø300 do
            # filtro (AP-096/097); mais fundo bate nela e nos hidrantes (1,60 a 1,95 testados)
            if sub == 'reúso': e['cob_min'] = 1.40; COB_FIXO[e['id']] = 1.40
            # distribuição: abaixo da elétrica que cruza o platô 233 (AL-016) com a folga de 0,20 m
            if sub in ('distribuição', 'alimentação'): e['cob_min'] = 1.20; COB_FIXO[e['id']] = 1.20
        elif e['disc'] == 'ELE':
            e['info']['material'] = 'Eletroduto corrugado PEAD' if e['trecho'].startswith('CP') else 'Eletroduto PVC corrugado flexível'
        else:
            e['info']['material'] = MAT_PRESS[e['disc']]
            if e['disc'] == 'HID' and COB_HID: e['cob_min'] = COB_HID; COB_FIXO[e['id']] = COB_HID
        e['info']['DN_mm'] = round(e['de'] * 1000)
    for e in pr: _sem_pontinha(e)
    E += pr
    REGRAS['estudo']['cob_fixo'] = dict(COB_FIXO)
    esg = lt.gravidade(os.path.join(F2, 'SAT_fase2_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    ap = lt.gravidade(os.path.join(F2, 'SAT_fase2_AP_trechos.csv'), 'AP', 'AP', ter)
    cps = lt.gravidade(os.path.join(F2, 'SAT_fase2_CPS-DRE_trechos.csv'), 'DRE', 'CPS-DRE', ter)
    for e in esg + ap + cps:
        dn = lt.fl(e['info'].get('DN_mm'))
        e['info']['material'] = mat_grav(e['disc'], e['info'].get('material'), dn, e['info'].get('classe'))
    ap = _sem_cobertos(_sem_duplicados(ap)); cps = _sem_cobertos(cps)
    curtos = _sem_curtos(esg + ap + cps)
    esg, ap, cps = ([e for e in x if e['id'] not in curtos] for x in (esg, ap, cps))
    _drenos_no_eixo(ap)
    E += esg + ap + cps
    # prumadas do pluvial: subida do tubo enterrado até 0,30 m acima do terreno (as que ficam fora dos prédios)
    import equip_sat
    E += [x for x in equip_sat.elementos_extra(esg + ap + cps, ter, md) if x['id'].startswith('AP:') and x['id'].endswith('-subida')]
    for x in E:
        if x['id'].endswith('-subida'): x['info']['material'] = mat_grav('AP', '', lt.fl(x['info'].get('DN_mm')), 'coletor')
    C = []
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_ESG_caixas.csv'), 'ESG', 'ESG', ter, esg, ignorar_tipos=('TS',))   # tanque séptico = ETE, fora
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_AP_caixas.csv'), 'AP', 'AP', ter, ap)
    C += lt.caixas(os.path.join(F2, 'SAT_fase2_CPS-DRE_caixas.csv'), 'DRE', 'CPS-DRE', ter, cps)
    ele = [e for e in E if e['disc'] == 'ELE']; sdai = [e for e in E if e['disc'] == 'SDAI']
    C += lt.caixas_de_nos(os.path.join(F2, 'SAT_fase2_ELE_nos.csv'), 'ELE', 'ELE', ter, ele, {'CX 60x60': 0.60, 'POSTE': 0.80})
    C += lt.caixas_de_nos(os.path.join(F2, 'SAT_fase2_PCI_nos.csv'), 'SDAI', 'SDAI', ter, sdai, {'caixa de passagem SDAI': 0.30})
    C = [c for c in C if not c['id'].startswith('ELE:CP2-')]
    _ca15(E, C)   # CPS ELE-002 é alternativa de tensão do mesmo traçado: vale o ELE-001
    for c in C:
        if c['disc'] == 'ELE' and str(c['info'].get('tipo', '')).startswith('POSTE'): c['info']['tipo'] = 'caixa de passagem 80x80 (base do poste)'
    C += equipamentos(ter)
    E = _sem_soltos(E, C)
    E, C = so_externo(E, C)
    E = [e for e in E if not (e['id'].count('~') or e.get('cortado')) or _comp(e) >= 0.80]   # sobra de menos de 0,80 m na face do prédio
    # ajustes em planta sobre os pares críticos da rodada anterior (sat_pares.py): contornos curtos e caixas deslocadas
    fp = os.path.join(SAIDA, 'SAT_ajustes_pares.json')
    if os.path.exists(fp) and os.environ.get('SAT_SEM_AJUSTES') != '1':
        import sat_ajustes as AJ
        J = json.load(open(fp, encoding='utf-8'))
        AJ.mover_caixas(E, C, set(J['caixas']), SAIDA, passo_max=3.0)
        AJ.contornar(E, C, [tuple(x) for x in J['contornos']] + CONTORNOS_EXTRA, SAIDA)
        AJ.afastar_pontas(E, C, SAIDA)
        # a caixa da base do poste que andou leva o poste junto
        eq = {c['info'].get('nome'): c for c in C if c['info'].get('equipamento')}
        for c in C:
            if 'E0' in c and not c['info'].get('equipamento') and c['info'].get('nome') in eq:
                q = eq[c['info']['nome']]; q['E0'], q['N0'] = q['E'], q['N']; q['E'] += c['E'] - c['E0']; q['N'] += c['N'] - c['N0']
        for c in C:
            if 'E0' in c:
                dz = float(ter.z([[c['E'], c['N']]])[0] - ter.z([[c['E0'], c['N0']]])[0])
                if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
    _juncoes_na_caixa(E, C)
    for nome in CAIXAS_A_AFASTAR: _afastar_caixa(nome, E, C)
    _nos_fora_das_caixas(E, C)
    _tj02(E, C)
    _decisoes_pagina(E, C)
    _registrar_planta(E)
    _custo_eletrica_acima()
    _perfil_nos_taludes()
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas, sem a galeria Ø1200',
                               'excluir': lambda e: False}}}


def perfil_talude(pts2d, de, cob, ter, passo=0.1, desvio=0.05, trecho_min=0.1):
    """perfil que acompanha o terreno nos dois sentidos: o Douglas-Peucker da ferramenta só põe vértice onde a reta ficaria rasa
    demais (nunca onde ficaria funda), então a rede que desce o talude entre dois platôs ia em reta e passava 5 m abaixo do platô
    de cima. Aqui o vértice entra onde o desvio (para cima ou para baixo) passa de 'desvio', e os nós ficam exatamente no
    recobrimento (vértices a cada 0,1 m, desvio de 3 cm): a descida do talude tem o mesmo recobrimento nas duas pontas de cada peça
    (Revisão, D3) e entre os nós o recobrimento não varia mais que 3 cm."""
    P = [np.asarray(p[:2], float) for p in pts2d]
    S_, Q = [0.0], [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = np.linalg.norm(b - a); k = max(1, int(L / passo))
        for j in range(1, k + 1): Q.append(a + (b - a) * j / k); S_.append(S_[-1] + L / k)
    S_ = np.array(S_); Q = np.array(Q)
    zt = ter.z(Q); zt = np.where(np.isnan(zt), np.nanmin(zt), zt)
    # covas de até 1 m de largura no piso do IMP (vazio de caixa/grelha do as built) fechadas: o tubo passa reto por cima delas;
    # degraus de talude e vales mais largos do terreno natural continuam (o fechamento só tira o que desce e volta em menos de 1 m)
    w = max(1, int(round(0.5 / passo)))
    pad = np.pad(zt, w, mode='edge')
    mx_ = np.max(np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1), axis=1)
    pad = np.pad(mx_, w, mode='edge')
    # sem passar de 0,35 m de recobrimento real em vale estreito do terreno natural
    zt = np.minimum(np.min(np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1), axis=1), zt + max(cob - 0.35, 0.0))
    zr = zt - cob - de / 2
    cum = np.cumsum([0] + [np.linalg.norm(b - a) for a, b in zip(P[:-1], P[1:])])
    qb = {0, len(S_) - 1} | {int(np.argmin(np.abs(S_ - s))) for s in cum}

    def dp(i0, i1):
        if i1 <= i0 + 1: return
        line = zr[i0] + (zr[i1] - zr[i0]) * (S_[i0 + 1:i1] - S_[i0]) / (S_[i1] - S_[i0] + 1e-12)
        dev = np.abs(line - zr[i0 + 1:i1]); k = int(np.argmax(dev)) + i0 + 1
        if dev.max() > desvio and S_[k] - S_[i0] >= trecho_min and S_[i1] - S_[k] >= trecho_min:
            qb.add(k); dp(i0, k); dp(k, i1)
    for i0, i1 in zip(sorted(qb)[:-1], sorted(qb)[1:]): dp(i0, i1)
    qs = sorted(qb); z = {i: zr[i] for i in qs}        # nós no recobrimento: no talude a subida/descida acompanha o terreno
    # peça íngreme (45° ou mais) com recobrimento diferente nas duas pontas (vale estreito do terreno natural, onde a cova não foi
    # toda fechada): a ponta mais alta desce até a peça ficar a 42°; o recobrimento só aumenta
    zreal = ter.z(Q); zreal = np.where(np.isnan(zreal), zt, zreal)
    for _ in range(200):
        mud = False
        for i0, i1 in zip(qs[:-1], qs[1:]):
            dxy = S_[i1] - S_[i0]; dz = z[i1] - z[i0]
            if abs(dz) < 0.95 * dxy or abs((zreal[i0] - z[i0]) - (zreal[i1] - z[i1])) <= 0.08: continue
            if dz > 0: z[i1] = z[i0] + 0.9 * dxy
            else: z[i0] = z[i1] + 0.9 * dxy
            mud = True
        if not mud: break
    # o rebaixamento acima não passa da profundidade máxima: no muro entre os platôs 233 e 236 (AL-007, junto da CA-06) a ponta de
    # cima descia até 2,9 m; ali a peça sobe íngreme junto do muro (Revisão D1, 22/10)
    lim = REGRAS['estudo']['prof_max'] + de / 2
    for i in qs: z[i] = max(z[i], zreal[i] - lim)
    return np.array([(Q[i][0], Q[i][1], z[i]) for i in qs])


# caixas de passagem de ELE/SDAI desenhadas em cima de caixa de esgoto, equipamento e outras redes (canto da guarita: CI-01, HID-H-03,
# QD-GUA) que o deslocamento padrão não tira (ele exige folga de todos os lados dentro de 3 m)
CAIXAS_A_AFASTAR = ['AL-CX-04', 'SDAI-CX-01', 'AL-CX-22', 'SDAI-CX-15']
# eletroduto que atravessa caixa de passagem da outra rede elétrica e a caixa não tem para onde ir: o eletroduto contorna
CONTORNOS_EXTRA = [('SDAI-12', 'AL-CX-22'), ('AL-002', 'SDAI-CX-15')]


def _afastar_caixa(nome, E, C, rmax=2.5, folga=0.15, log=print):
    """leva a caixa de passagem ao ponto mais perto (até rmax) onde ela fica a 'folga' de toda peça de outra rede em planta
    (tubos de outras disciplinas, caixas, equipamentos); as pontas dos eletrodutos dela acompanham. Grava em SAT_caixas_movidas.json."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union
    c = next((c for c in C if c['info'].get('nome') == nome and not c['info'].get('equipamento')), None)
    if c is None: return
    def poli(x, E_=None, N_=None):
        mx, my, rot = x.get('mx', x['meia']), x.get('my', x['meia']), x.get('rot', 0.0) if x['forma'] == 'r' else 0.0
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([E_ if E_ is not None else x['E'], N_ if N_ is not None else x['N']])
        return Polygon([p + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    perto = lambda x, y: abs(x - c['E']) < rmax + 6 and abs(y - c['N']) < rmax + 6
    obs = [LineString(e['pts'][:, :2]).buffer(e['de'] / 2) for e in E if e['disc'] != c['disc'] and np.any(np.abs(e['pts'][:, 0] - c['E']) < rmax + 6)
           and np.any(np.abs(e['pts'][:, 1] - c['N']) < rmax + 6)]
    obs += [poli(x) for x in C if x is not c and perto(x['E'], x['N']) and (x['disc'] != c['disc'] or x['info'].get('equipamento'))]
    O = unary_union(obs)
    pecas = [(e, k) for e in E if e['disc'] == c['disc'] and e['tipo'] == 'pressao' for k in (0, -1)
             if max(md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])) < 0.30]
    best = None
    for r in np.arange(0.1, rmax + 1e-6, 0.1):
        for a in np.radians(np.arange(0, 360, 10)):
            v = np.array([math.cos(a), math.sin(a)]) * r
            if poli(c, c['E'] + v[0], c['N'] + v[1]).buffer(folga).intersects(O): continue
            # os eletrodutos que acompanham não podem atravessar caixa de esgoto/drenagem
            ok = all(not LineString(np.vstack([e['pts'][1 if k == 0 else -2, :2], e['pts'][k, :2] + v])).buffer(e['de'] / 2).intersects(
                unary_union([poli(x) for x in C if x['disc'] in ('ESG', 'AP', 'DRE') and perto(x['E'], x['N'])])) for e, k in pecas)
            if ok: best = v; break
        if best is not None: break
    if best is None: log(f'  {nome}: sem posição livre até {rmax:.1f} m'); return
    de = (c['E'], c['N']); c.setdefault('E0', c['E']); c.setdefault('N0', c['N']); c['E'] += best[0]; c['N'] += best[1]
    for e, k in pecas:
        e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = e['pts'].copy(); e['pts'][k, :2] += best; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    fn = os.path.join(SAIDA, 'SAT_caixas_movidas.json')
    reg = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    reg = [x for x in reg if x.get('caixa') != nome]
    reg.append(dict(caixa=nome, disc=c['disc'], elemento=c['id'], status='caixa deslocada', de=[c['E0'], c['N0']], E=c['E'], N=c['N'],
                    desloc=round(float(np.hypot(c['E'] - c['E0'], c['N'] - c['N0'])), 2), lado=round(2 * c.get('mx', c['meia']), 3),
                    lado_y=round(2 * c.get('my', c['meia']), 3), rot=float(c.get('rot', 0.0)), forma=c['forma'], tubos=[e['trecho'] for e, _ in pecas]))
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    log(f'  {nome} afastada {np.hypot(*best):.2f} m das outras redes; {len(pecas)} eletrodutos acompanham')


def _comp(e):
    return float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)))


def _drenos_no_eixo(T, log=print, i=0.01):
    """drenos de Ø40 (ar-condicionado, sem cota no projeto: cota estimada pela declividade) que entram num coletor fora de caixa
    chegavam com a geratriz inferior alinhada, 12–14 cm abaixo do eixo do coletor, e a junção ficava fora das pontas (Revisão, C6).
    A cota deles é refeita de jusante para montante: a ponta que entra no coletor fica no eixo dele, e cada dreno sobe 1 % até a
    ponta de montante, que vira a ponta de jusante dos drenos que chegam nela."""
    dren = [e for e in T if e['de'] <= 0.06]
    perto = lambda p, q: np.hypot(*(p[:2] - q[:2])) < 0.03
    z_no, fila = {}, []
    for e in dren:
        for o in T:
            if o['de'] <= e['de'] + 0.05: continue
            for m in (0, -1):
                if perto(o['pts'][m], e['pts'][-1]): z_no[e['id']] = float(o['pts'][m, 2]); fila.append(e)
    feitos, n = set(), 0
    while fila:
        e = fila.pop(0)
        if e['id'] in feitos: continue
        feitos.add(e['id'])
        L = float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)))
        z1 = z_no[e['id']]; z0 = z1 + i * L
        P = e['pts'].copy(); s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
        P[:, 2] = z0 + (z1 - z0) * s_ / max(L, 1e-9)
        e['pts'] = P; e['pts_sol'] = P.copy(); e['info']['GI_mont'] = z0 - e['de'] / 2; e['info']['GI_jus'] = z1 - e['de'] / 2; n += 1
        for y in dren:
            if y['id'] not in feitos and perto(y['pts'][-1], P[0]): z_no[y['id']] = z0; fila.append(y)
    if n: log(f'  {n} drenos de ar-condicionado com a cota refeita a partir do eixo do coletor onde entram')


def _sem_pontinha(e, lim=0.15):
    """perna de menos de 15 cm na ponta do trecho (AF-09 volta 8 cm sobre o AF-08 no TE-15; AF-07 e AF-06 com 0,2–0,4 m na
    ponta): a perna sai e o vértice vira a ponta."""
    P = e['pts']
    while len(P) > 2 and np.hypot(*(P[1, :2] - P[0, :2])) < lim: P = np.vstack([P[:1], P[2:]])
    while len(P) > 2 and np.hypot(*(P[-1, :2] - P[-2, :2])) < lim: P = np.vstack([P[:-2], P[-1:]])
    e['pts'] = P; e['pts_sol'] = P.copy()


def _sem_cobertos(T, log=print):
    """trecho desenhado por cima de outros dois da mesma rede (AP-170 = AP-171 + AP-177): sai o que está inteiro dentro dos outros."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    fora = set()
    for e in T:
        L = LineString(e['pts'][:, :2])
        if L.length < 1.0: continue
        outros = [LineString(o['pts'][:, :2]).buffer(0.05) for o in T if o is not e and o['id'] not in fora and o['rede'] == e['rede']
                  and LineString(o['pts'][:, :2]).distance(L) < 0.05]
        if outros and unary_union(outros).buffer(0.01).contains(L): fora.add(e['id'])
    if fora: log(f"  {len(fora)} trechos desenhados por cima de outros saíram: {', '.join(sorted(x.split(':')[1] for x in fora))}")
    return [e for e in T if e['id'] not in fora]


def _sem_curtos(T, lim=0.60, log=print):
    """trecho de gravidade de menos de 0,60 m entre dois nós sem caixa (AP-193, 0,35 m; CPS-DRE-038, 0,41 m), menor que a própria
    conexão: o nó de jusante vem para o de montante (os trechos que chegam nele acompanham) e o pedaço sai."""
    fora = []
    for e in T:
        if np.hypot(*(e['pts'][-1, :2] - e['pts'][0, :2])) >= lim or len(e['pts']) > 2: continue
        a, b = e['pts'][0].copy(), e['pts'][-1].copy()
        for o in T:
            if o is e: continue
            for k in (0, -1):
                if np.hypot(*(o['pts'][k, :2] - b[:2])) < 0.03:
                    o['pts'] = o['pts'].copy(); o['pts'][k, :2] = a[:2]; o['pts_sol'] = o['pts'].copy()
        fora.append(e['id'])
    if fora: log(f"  {len(fora)} pedaços de menos de {lim:.2f} m na gravidade saíram (o nó foi unido): {', '.join(x.split(':')[1] for x in fora)}")
    return set(fora)


def _sem_duplicados(T, log=print):
    """trechos da pluvial extraídos duas vezes do ESG-001 (mesmas pontas: AP-024/AP-095, AP-043/AP-094, AP-073/AP-167, AP-075/AP-199):
    fica um só, o de maior diâmetro e, no empate, o que tem rótulo no desenho."""
    fora = set()
    for i, a in enumerate(T):
        for b in T[i + 1:]:
            if a['id'] in fora or b['id'] in fora: continue
            pa, pb = a['pts'][[0, -1], :2], b['pts'][[0, -1], :2]
            if min(np.abs(pa - pb).max(), np.abs(pa - pb[::-1]).max()) > 0.05: continue
            chave = lambda x: (lt.fl(x['info'].get('DN_mm')) or 0, 'sem rótulo' not in x['info'].get('obs', ''))
            fora.add(b['id'] if chave(a) >= chave(b) else a['id'])
    if fora: log(f"  pluvial: {len(fora)} trechos repetidos no desenho saíram ({', '.join(sorted(x.split(':')[1] for x in fora))})")
    return [e for e in T if e['id'] not in fora]


def _sem_soltos(E, C, log=print):
    """pedaços de eletroduto soltos na extração (AL-003/004/005: três riscos de 0,6–1,4 m sem Ø junto da CA-01, que não ligam em
    nada): componente de ELE/SDAI com menos de 3 m no total e sem ponta em caixa ou equipamento da disciplina sai."""
    els = [e for e in E if e['disc'] in ('ELE', 'SDAI') and e['tipo'] == 'pressao']
    pai = list(range(len(els)))
    def raiz(i):
        while pai[i] != i: pai[i] = pai[pai[i]]; i = pai[i]
        return i
    for i, a in enumerate(els):
        for j in range(i + 1, len(els)):
            b = els[j]
            if a['disc'] == b['disc'] and min(np.hypot(*(a['pts'][k][:2] - b['pts'][m][:2])) for k in (0, -1) for m in (0, -1)) < 0.10:
                pai[raiz(i)] = raiz(j)
    comp = {}
    for i, e in enumerate(els): comp.setdefault(raiz(i), []).append(e)
    fora = set()
    for es in comp.values():
        if sum(_comp(e) for e in es) >= 3.0: continue
        if any(c['disc'] == e['disc'] and max(md.planta_local(c, *e['pts'][k][:2])) < 0.10 for e in es for k in (0, -1) for c in C): continue
        fora |= {e['id'] for e in es}
    if fora: log(f"  {len(fora)} pedaços de eletroduto soltos (extração) saíram: {', '.join(sorted(x.split(':')[1] for x in fora))}")
    return [e for e in E if e['id'] not in fora]


def _nos_fora_das_caixas(E, C, log=print):
    """nó de eletrodutos (derivação ou fim) desenhado dentro de caixa de esgoto/pluvial/drenagem (AL-003/004/005 na CA-01): o nó sai
    para o ponto livre mais perto (0,30 m da parede), sem os eletrodutos que chegam nele atravessarem a caixa."""
    from shapely.geometry import LineString, Point, Polygon
    def poli(x):
        mx, my, rot = x.get('mx', x['meia']), x.get('my', x['meia']), x.get('rot', 0.0) if x['forma'] == 'r' else 0.0
        if x['forma'] == 'c': return Point(x['E'], x['N']).buffer(x['meia'])
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([x['E'], x['N']])
        return Polygon([p + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    grav = [(c, poli(c)) for c in C if c['disc'] in ('ESG', 'AP', 'DRE')]
    nos = {}
    for e in E:
        if e['disc'] not in ('ELE', 'SDAI') or e['tipo'] != 'pressao': continue
        for k in (0, -1): nos.setdefault((e['disc'], round(float(e['pts'][k, 0]), 2), round(float(e['pts'][k, 1]), 2)), []).append((e, k))
    fn = os.path.join(SAIDA, 'SAT_contornos.json')
    ant = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    for (d, x, y), lst in nos.items():
        x, y = lst[0][0]['pts'][lst[0][1], :2]
        c = next((c for c, pg in grav if pg.buffer(0.05).contains(Point(x, y))), None)
        if c is None: continue
        pg = next(pg for cc, pg in grav if cc is c)
        viz = [e['pts'][1 if k == 0 else -2, :2] for e, k in lst]
        achou = None
        for r in np.arange(0.3, 3.01, 0.1):
            for ang in np.radians(np.arange(0, 360, 10)):
                q = np.array([x, y]) + r * np.array([math.cos(ang), math.sin(ang)])
                if pg.buffer(0.30).contains(Point(*q)): continue
                if any(LineString([v, q]).intersects(pg.buffer(0.10)) for v in viz): continue
                if any(Point(*q).distance(p2) < 0.30 for cc, p2 in grav if cc is not c): continue
                achou = q; break
            if achou is not None: break
        if achou is None: log(f'  nó de {", ".join(e["trecho"] for e, _ in lst)} fica dentro da {c["info"].get("nome")}'); continue
        for e, k in lst:
            antigo = e.get('pts_planta0', e['pts']).copy(); e['pts_planta0'] = antigo
            e['pts'] = e['pts'].copy(); e['pts'][k, :2] = achou; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
            ant = [r_ for r_ in ant if not (r_.get('elemento') == e['id'] and r_.get('no_fora'))]
            ant.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa=c['info'].get('nome'), status='contorno em planta', no_fora=True,
                            antigo=[list(map(float, p[:2])) for p in antigo], pontos=[list(map(float, p[:2])) for p in e['pts']]))
        log(f'  nó de {", ".join(e["trecho"] for e, _ in lst)} sai de dentro da {c["info"].get("nome")} ({np.hypot(achou[0] - x, achou[1] - y):.2f} m)')
    json.dump(ant, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


# decisões da página de pendências (22/10/2026; Anderson: d02; Daniel: d08 a d10)
# d02 CA-01: desenhada na crista do talude do platô 236 (as built 235,1 no ponto): 1,20 m para dentro do platô, pelo eixo do AP-011
_P01 = np.array([545963.635, 8716263.264]); _U01 = np.array([545968.399, 8716256.884]) - _P01; _U01 = _U01 / np.hypot(*_U01)
# d10 CA-05: afastada 0,35 m da CI-03 (o ESG-004 passava encostado na parede dela; com ela o AP-074 também sai de perto da CI-03, d09)
_P05 = np.array([545962.035, 8716236.138]); _U05 = _P05 - np.array([545962.522, 8716237.314]); _U05 = _U05 / np.hypot(*_U05)


def _longe(c, a, b, d):
    """posição da caixa c (E, N) afastada d metros do eixo do tubo a-b, para o lado em que ela já está."""
    c, a, b = (np.asarray(x, float) for x in (c, a, b)); u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]])
    return tuple(c + n * d * np.sign(n @ (c - a)))


# esgoto × pluvial que ficariam com o projetista (Anderson, 22/10/2026: "Os 3 conflitos, você mesmo pode fazer")
# CI-02 (esgoto): o AP-145 passa raspando o canto dela; 0,25 m para longe do eixo do AP-145 (os três tubos de esgoto acompanham)
# PVE-09 (esgoto): o AP-110 Ø250 corta a parede do PV e do outro lado, paralelo, passa o AF-09; 0,135 m para longe do AP-110 deixa
# o PV entre os dois (ESG-011, ESG-018 e ESG-020 acompanham)
CAIXA_NOVA = {'AP:CA-01': tuple(_P01 + _U01 * 1.20), 'AP:CA-05': tuple(_P05 + _U05 * 0.35),
              'ESG:CI-02': _longe((545975.824, 8716247.697), (545978.413, 8716251.571), (545975.635, 8716246.501), 0.25),
              'ESG:PVE-09': _longe((545984.293, 8716150.704), (545982.648, 8716153.791), (545987.343, 8716147.853), 0.135)}
# chegada acima do fundo da caixa de jusante (m; GI de projeto na chegada):
# d08 AP-199 × ESG-026 (encostados): o AP-199 chega na CA-04 4 cm acima do fundo, passando por cima do ESG-026
CHEGADA = {'AP-199': ('CA-04', 0.04, 235.09)}
# ESG-014 × AP-108 (2 cm de interferência a 1 m da PVE-06): o ESG-014 sai da PVE-06 5 cm mais baixo (fundo da PVE-06 de 234,30 para
# 234,25; i de 0,97 % para 0,67 %). Subir a chegada do AP-108 na PVP-06 não dá: logo antes ele passa sob o AF-08 com 4 cm.
SAIDA_ABAIXO = {'ESG-014': ('ESG:PVE-06', 0.05)}


def _decisoes_pagina(E, C, log=print):
    """aplica as decisões da página de pendências e as dos conflitos de esgoto × pluvial: caixas deslocadas (CT e CF iguais; os
    tubos da mesma rede que chegam nelas acompanham) e chegadas de pluvial acima do fundo da caixa."""
    fn = os.path.join(SAIDA, 'SAT_caixas_movidas.json')
    reg = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    for cid, novo in CAIXA_NOVA.items():
        c = next((c for c in C if c['id'] == cid), None)
        if c is None: continue
        nome = cid.split(':', 1)[1]
        de = np.array([c['E'], c['N']]); v = np.array(novo) - de
        if np.hypot(*v) < 0.01: continue
        c['E0'], c['N0'] = c['E'], c['N']; c['E'], c['N'] = float(novo[0]), float(novo[1])
        tubos = []
        for e in E:
            if e['disc'] != c['disc']: continue
            for k in (0, -1):
                if np.hypot(*(e['pts'][k, :2] - de)) < 0.05:
                    e['pts'] = e['pts'].copy(); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy(); e.pop('S', None); tubos.append(e['trecho'])
        reg = [r for r in reg if r.get('caixa') != nome]
        reg.append(dict(caixa=nome, disc=c['disc'], elemento=c['id'], status='caixa deslocada', de=[float(de[0]), float(de[1])], E=c['E'], N=c['N'],
                        desloc=round(float(np.hypot(*v)), 2), lado=round(2 * c['meia'], 3), lado_y=round(2 * c['meia'], 3), rot=0.0,
                        forma=c['forma'], tubos=tubos))
        log(f'  {nome} deslocada {np.hypot(*v):.2f} m (CT e CF mantidas); acompanham {", ".join(tubos)}')
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    for e in E:
        if e['disc'] == 'AP' and e['trecho'] in CHEGADA:
            cx, dz, _ = CHEGADA[e['trecho']]
            e['pts'] = e['pts'].copy(); e['pts'][-1, 2] += dz; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
            e['info']['GI_jus'] = round(e['info'].get('GI_jus', 0) + dz, 3)
            log(f"  {e['trecho']} chega na {cx} {dz * 100:.0f} cm acima do fundo")
    for tr, (cid, dz) in SAIDA_ABAIXO.items():
        c = next(c for c in C if c['id'] == cid); c['zb'] -= dz
        c['info']['CF'] = round(float(c['info']['CF']) - dz, 3)
        for e in E:
            if e['disc'] == 'ESG' and e['trecho'] == tr:
                e['pts'] = e['pts'].copy(); e['pts'][0, 2] -= dz; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
                e['info']['GI_mont'] = round(float(e['info']['GI_mont']) - dz, 3)
        log(f"  {tr} sai da {cid.split(':')[1]} {dz * 100:.0f} cm mais baixo (fundo da caixa {c['info']['CF']:.2f})")


def _tj02(E, C, log=print):
    """a torneira de jardim TJ-02 (fim do AF-16, pé do talude) está desenhada em cima da saída do AP-018: o AF-16 cruzaria a pluvial
    na descida do talude. A torneira recua pelo próprio ramal até a 0,35 m do eixo do AP-018 (só o fim do ramal encurta)."""
    from shapely.geometry import LineString, Point
    af = next((e for e in E if e['trecho'] == 'AF-16'), None); ap = next((e for e in E if e['trecho'] == 'AP-018'), None)
    if af is None or ap is None: return
    P = af['pts']; L = LineString(P[:, :2]); A = LineString(ap['pts'][:, :2])
    x = L.intersection(A)
    if x.is_empty: return
    s = L.project(x if x.geom_type == 'Point' else Point(list(x.coords)[0])) - 0.35
    q = np.array(L.interpolate(s).coords[0]); antigo = P.copy()
    S_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
    k = int(np.searchsorted(S_, s)); z = np.interp(s, S_, P[:, 2])
    af['pts_planta0'] = antigo; af['pts'] = np.vstack([P[:k], [q[0], q[1], z]]); af['pts_sol'] = af['pts'].copy(); af.pop('S', None)
    tj = next((c for c in C if c['info'].get('nome') == 'TJ-02'), None)
    if tj is not None: tj['E0'], tj['N0'] = tj['E'], tj['N']; tj['E'], tj['N'] = float(q[0]), float(q[1])
    fn = os.path.join(SAIDA, 'SAT_contornos.json')
    ant = [r for r in (json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []) if r.get('trecho') != 'AF-16']
    ant.append(dict(trecho='AF-16', disc='AF', elemento=af['id'], caixa='TJ-02', status='contorno em planta', torneira=True,
                    antigo=[list(map(float, p[:2])) for p in antigo], pontos=[list(map(float, p[:2])) for p in af['pts']]))
    json.dump(ant, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log(f"  TJ-02 recua {L.length - s:.2f} m pelo AF-16 (sai de cima da saída do AP-018)")


def _juncoes_na_caixa(E, C, raio=1.30, log=print):
    """derivação de eletroduto enterrado só dentro de caixa (NBR 5410): no EL-001 a derivação da iluminação externa (TE) fica
    desenhada a 0,3–1,3 m da caixa do poste ou da caixa de passagem vizinha. O nó vai para dentro da caixa mais próxima (a 5 cm
    da parede, do lado de onde vinha) e os eletrodutos que chegam nele acompanham; assim a cota de cada trecho pode mudar na caixa.
    Registrado como contorno em planta (vai para a prancha)."""
    nos = {}
    for e in E:
        if e['disc'] != 'ELE' or e['tipo'] != 'pressao': continue
        for k in (0, -1): nos.setdefault((round(float(e['pts'][k, 0]), 1), round(float(e['pts'][k, 1]), 1)), []).append((e, k))
    cx = [c for c in C if c['disc'] == 'ELE' and not c['info'].get('equipamento')]
    reg = []
    for p, lst in nos.items():
        if len(lst) < 3: continue
        dentro = [c for c in cx if max(md.planta_local(c, p[0], p[1])) < 0.0]
        if dentro: continue
        perto = [c for c in cx if np.hypot(c['E'] - p[0], c['N'] - p[1]) < raio + c['meia']]
        if not perto: continue
        c = min(perto, key=lambda c: np.hypot(c['E'] - p[0], c['N'] - p[1]))
        v = np.array(p) - np.array([c['E'], c['N']]); h = min(c.get('mx', c['meia']), c.get('my', c['meia'])) - 0.10
        q = np.array([c['E'], c['N']]) + (v / np.hypot(*v) * min(h, np.hypot(*v)) if np.hypot(*v) > 1e-6 else 0)
        for e, k in lst:
            antigo = e.get('pts_planta0', e['pts']).copy(); e['pts_planta0'] = antigo
            e['pts'] = e['pts'].copy(); e['pts'][k, :2] = q; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
            reg.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa=c['info'].get('nome', c['id']), status='contorno em planta',
                            antigo=[list(map(float, x[:2])) for x in antigo], pontos=[list(map(float, x[:2])) for x in e['pts']]))
        log(f"  derivação {', '.join(e['trecho'] for e, _ in lst)}: nó levado para dentro da {c['info'].get('nome')} ({np.hypot(*(q - np.array(p))):.2f} m)")
    fn = os.path.join(SAIDA, 'SAT_contornos.json')
    ant = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    ant = [r for r in ant if not (r.get('status') == 'contorno em planta' and r.get('derivacao'))]
    json.dump(ant + [dict(r, derivacao=True) for r in reg], open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _perfil_nos_taludes():
    """o perfil das pressurizadas é o perfil_talude (acompanha o terreno nos dois sentidos, covas de piso fechadas) em todo trecho."""
    from preclash import estudo as _est, desvio as _dsv, leitura as _lt, clash as _cl
    if getattr(_est, '_sat_talude', False): return
    def perfil(pts2d, de, cob, ter, passo=0.5, desvio=0.20, trecho_min=2.0):
        return perfil_talude(pts2d, de, cob, ter)
    _est.perfil_por_recobrimento = perfil; _dsv.perfil_por_recobrimento = perfil; _est._sat_talude = True
    est0 = _est.estudar

    def estudar(E, caixas, regras, ter, log=print):
        rel = est0(E, caixas, regras, ter, log=log)
        _rampas(E, caixas, ter, log)
        return rel
    _est.estudar = estudar
    ap0 = _dsv.aplicar

    def aplicar(E, C, pend, regras, ter, log=print):
        antes = {e['id']: e['pts'][:, :2].copy() for e in E}
        dv = ap0(E, C, pend, regras, ter, log=log)
        _postes_com_a_base(C, ter)
        for e in E:                       # pontas que acompanharam a caixa deslocada pela ferramenta: traçado novo para a prancha
            a = antes.get(e['id'])
            if a is not None and (a.shape != e['pts'][:, :2].shape or np.abs(a - e['pts'][:, :2]).max() > 0.01):
                e.setdefault('pts_planta0', np.column_stack([a, e['pts'][:len(a), 2]]) if a.shape[0] <= len(e['pts']) else e['pts'].copy())
        _registrar_planta(E)
        return dv
    _dsv.aplicar = aplicar


def _registrar_planta(E):
    """todo trecho de pressão que mudou em planta (contorno, derivação levada à caixa, ponta que acompanhou caixa deslocada) entra em
    SAT_contornos.json com o traçado original e o final: na prancha o eletroduto é muitas vezes uma polilinha só por vários trechos, e
    o rever.py precisa da mudança inteira dela de uma vez (sat_mudancas.py junta os trechos seguidos)."""
    fn = os.path.join(SAIDA, 'SAT_contornos.json')
    reg = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    reg = [r for r in reg if not r.get('final')]
    for e in E:
        if e['tipo'] != 'pressao' or 'pts_planta0' not in e: continue
        a, b = np.asarray(e['pts_planta0'])[:, :2], e['pts'][:, :2]
        if a.shape == b.shape and np.abs(a - b).max() < 0.01: continue
        reg.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa='', status='contorno em planta', final=True,
                        antigo=[list(map(float, p)) for p in a], pontos=[list(map(float, p)) for p in b]))
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _postes_com_a_base(C, ter):
    """a caixa da base do poste que a ferramenta deslocou (cenário de desvios) leva o poste junto, como no ajuste do adaptador."""
    eq = {c['info'].get('nome'): c for c in C if c['info'].get('equipamento')}
    for c in C:
        q = eq.get(c['info'].get('nome'))
        if q is None or c['info'].get('equipamento') or 'E0' not in c: continue
        dE, dN = c['E'] - c['E0'], c['N'] - c['N0']
        if abs(dE) + abs(dN) < 1e-6 or q.get('_base') == (c['E'], c['N']): continue
        q.setdefault('E0', q['E']); q.setdefault('N0', q['N'])
        dz = float(ter.z([[q['E0'] + dE, q['N0'] + dN]])[0] - ter.z([[q['E'], q['N']]])[0])
        q['E'], q['N'] = q['E0'] + dE, q['N0'] + dN; q['_base'] = (c['E'], c['N'])
        if np.isfinite(dz): q['zt'] += dz; q['zb'] += dz


def _rampas(E, C, ter, log=print, incl=0.80):
    """o estudo leva as pontas de um nó (fora de caixa) à cota da peça mais funda; a peça mais rasa ficava com um degrau na ponta
    (Revisão, D3). A ponta rebaixada passa a chegar em rampa (1:0,8, menos de 45°), dentro do próprio trecho."""
    n = 0
    for e in E:
        if e['tipo'] != 'pressao' or not e.get('estudo'): continue
        P = e['pts'].copy()
        for k in (0, -1):
            j = 1 if k == 0 else -2
            if len(P) < 2: continue
            dxy = float(np.hypot(*(P[j, :2] - P[k, :2]))); dz = float(P[j, 2] - P[k, 2])
            if dz <= max(dxy * incl, 0.05): continue                       # a ponta não está abaixo do vizinho em degrau
            # caminha para dentro do trecho rebaixando até a rampa encontrar o perfil
            idx = list(range(len(P))) if k == 0 else list(range(len(P) - 1, -1, -1))
            z0 = P[k, 2]; S_ = 0.0; prev = P[k, :2]
            for i in idx[1:]:
                S_ += float(np.hypot(*(P[i, :2] - prev))); prev = P[i, :2]
                lim = z0 + S_ * incl
                if P[i, 2] <= lim: break
                P[i, 2] = lim
            n += 1
        if not np.allclose(P, e['pts']): e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None)
    if n: log(f'  {n} pontas rebaixadas no nó chegam em rampa (sem degrau)')


def _custo_eletrica_acima():
    """elétrica/SDAI SEMPRE por cima da água (Anderson): cada cruzamento por baixo pesa como 10 colisões (Jandaíra, Alagoinhas)."""
    from preclash import estudo as _est, clash as _cl
    if getattr(_est, '_sat', False): return
    _custo = _est.custo

    def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
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
    _est.custo, _est._sat = custo, True


# ---------------- passo 7 (executivo/rever.py): pranchas no padrão de executivo final
REVISAO = 'R01'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.30
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.60)
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1] if el.count(':') >= 1 else el
_PO = 'PROJETO_ORIGINAL/'
_DWG = {'AF-001': _PO + 'IMP/01_AF/24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00.dwg',
        'ESG-001': _PO + 'IMP/02_ESG/24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00.dwg',
        'EL-001': _PO + 'IMP/04_ELE/24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01.dwg',
        'EL-002': _PO + 'IMP/04_ELE/24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R01.dwg',
        'IN-001': _PO + 'IMP/05_PCI/24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03.dwg',
        'CPS-DRE-001': _PO + 'CPS/03_DRE/24-049-STK-XXX-ETIB-CPS-PE-DRE-001-DRG-R01.dwg',
        'CPS-ELE-001': _PO + 'CPS/04_ELE/24-049-STK-XXX-CP1-CPS-PE-ELE-001-ELG-R00.dwg'}


def folha(m):
    d = m['disc']; t = str(m.get('trecho') or '')
    if d == 'ELE':
        if t.startswith('CP'): return 'CPS-ELE-001'
        if t.startswith('IE'): return 'EL-001'
        return 'EL-002'
    if d == 'DRE': return 'CPS-DRE-001'
    return {'AF': 'AF-001', 'ESG': 'ESG-001', 'AP': 'ESG-001', 'HID': 'IN-001', 'SDAI': 'IN-001'}.get(d)


def executivo_dwg(m):
    return _DWG.get(m.get('folha') or folha(m))
