# -*- coding: utf-8 -*-
"""Adaptador da ETIB Pojuca (PJC) — fluxo novo (25/10/2026, o mesmo da Catu, Sátiro, Olindina, Itamira e Prof. Áurea).
A versão do piloto de 19/10 (teto de 1,50 m, mergulhos, contornos da AF e bancos deslocados) ficou em escolas/pojuca_2026-10-19.py.
Entrada (INVENTARIO.md, quadro "Entrada"): decisões P1 a P4 sem resposta -> vale a recomendada:
  P1 profundidade máxima 2,00 m; P2 caixas de elétrica/SDAI sobre esgoto e pluvial deslocadas até 1,50 m (aplicar e avisar), o resto
  na página de pendências; P3 a implantação da quadra (PI000) fica fora; P4 vale o IC-001-INC R01.
Terreno: IMP as built (escolas/dados/pojuca_terreno.npz, pojuca_terreno.py v3: pisos externos > plataformas > terreno modificado >
natural). As CT das pranchas de esgoto e drenagem são todas 61,00 (valor único do projetista): a tampa vai para o terreno do IMP e o
fundo fica na CF do projeto.
O IFC as built da implantação (REFERENCIAS_RVT/IFC) coincide em planta com o projeto e não tem cota coerente com o terreno: não muda nada
aqui (INVENTARIO.md).
Fontes (só leitura): RELATORIOS/PJC_fase2_*.csv (redes extraídas em 18/10; ver PJC_Fases_2-3_redes_sem_Revit.md).
Padrão:
  - só rede externa: contorno dos prédios pela estrutura as built (pojuca/ifc/pjc_estrutura.py, fecho dos pilares; a quadra coberta
    não tem parede e fica de fora); a rede é cortada na face e o que fica dentro sai;
  - pressurizadas: estudo de cota (água, reúso, alimentação e hidrante uma cota por rede; elétrica e alarme por trecho entre caixas,
    sempre acima da água), sem mergulho pontual; profundidade máxima 2,00 m; recobrimento mínimo AF 0,30 (premissa), hidrante 0,50
    (nota 5 do IC-001), alarme 0,50, elétrica 0,70 (NBR 5410, o EL-001/002 não informa);
  - gravidade (esgoto e drenagem): cotas das pranchas; gravidade × gravidade desloca a caixa até 0,60 m (aplicar e avisar);
  - drenagem do campo society pelo CPS-DRE-001 R01 (a espinha da DRE-001 dentro do campo sai, decisão de 18/10);
  - material pela legenda: AF tubo PVC soldável; esgoto PVC Série Normal (PVCR onde rotulado); pluvial PVC Série Reforçada
    (PVC-R), Vinilfort (PVC-V) e dreno corrugado perfurado (PVC-DR); hidrante PEAD; alarme eletroduto PEAD; elétrica enterrada
    eletroduto PEAD corrugado flexível (regra do projeto);
  - estrutura as built dos 8 blocos pela forma real (pojuca/ifc/pjc_estrutura.py)."""
import os, sys, csv, json, math, importlib.util, collections
import numpy as np
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Pojuca'
SIGLA = 'PJC'
BASE = r'D:\Projeto Modelagem\ETIB-POJUCA'
REL = os.path.join(BASE, 'RELATORIOS')
PJC = r'D:\Projeto Modelagem\FERRAMENTAS\pojuca\ifc'
SAIDA = os.environ.get('PJC_SAIDA') or os.path.join(REL, 'PRECLASH_2026-10-25')
DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
TERRENO = os.path.join(DADOS, 'pojuca_terreno.npz')
ORIGEM = (572450.0, 8626500.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (572370.0, 8626420.0, 572570.0, 8626615.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'estudo': {
        'por_rede': ['AF', 'HID'],
        'por_trecho': ['ELE', 'SDAI'],
        'cob_min': {'AF': 0.30, 'HID': 0.50, 'ELE': 0.70, 'SDAI': 0.50},
        'prof_max': 1.90,          # 2,00 m do projeto com 0,10 m de margem para a descida dos taludes
        'passo': 0.05,
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],
        'fixar_perto_de': [], 'raio_fixo': 3.0,
        'preencher_rebaixo': 1,
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
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI'), 'EST': ('EST',)}
NOMES_DISC = {'AF': 'Água fria, reúso e alimentação dos reservatórios', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial (implantação e campo society)',
              'ELE': 'Elétrica enterrada (alimentação e iluminação externa)', 'HID': 'Hidrantes e equipamentos de PCI',
              'SDAI': 'Alarme de incêndio (PCI)', 'EST': 'Estrutura as built (referência)'}
MOTIVO_PONTA = {'ELE': 'chegada na face da edificação ou no quadro/poste (sobe para o quadro)',
                'ESG': 'saída de esgoto da edificação (ramal predial) ou lançamento na rede',
                'DRE': 'descida/ramal pluvial da edificação ou lançamento',
                'AF': 'entrada da edificação, torneira de jardim ou saída do reservatório',
                'HID': 'hidrante, recalque ou casa de bombas', 'SDAI': 'chegada na central de alarme / edificação'}
COB = REGRAS['estudo']['cob_min']
MAT_AF = 'Tubo PVC soldável'
MAT_ELE = 'Eletroduto PEAD corrugado flexível'
MAT_PRESS = {'HID': 'Tubo PEAD', 'SDAI': 'Eletroduto PEAD'}
DE_ELE = {'3/4"': 0.0267, '1"': 0.0334, '1.1/4"': 0.0422, '1.1/2"': 0.0483, '2"': 0.0603, '2.1/2"': 0.0730, '3"': 0.0889, '4"': 0.1143}
DE_PEAD = {'2.1/2"': 0.075, '3"': 0.085}
DE_AF_PADRAO = {'AF': 0.050, 'RU': 0.025, 'AL': 0.032}
# campo society (bloco CAMPO30x50 da SIT levado ao UTM): centro, giro, meios lados
CAMPO = (572450.75784, 8626477.20656, 28.552937, 27.15, 17.15)
APLICADO = []
# recobrimento fixado por rede de água (pojuca/ifc/pjc_diag_estudo.py e rodadas de 25/10): no miolo entre o BP2, o teatro e a casa de
# bombas passam os coletores DRE-177/181/182/190/192 (PVC-V 250 e 300, topo entre 59,4 e 60,0) com o terreno em 61,0:
#  - hidrante 0,85: passa por cima dos coletores (mais fundo cruza o DRE-181/190/192; abaixo deles não cabe até 1,90 m);
#  - água potável 1,00 e alimentação dos reservatórios 1,12 (uma sob a outra no cruzamento AF-06 × AL-03): abaixo do hidrante e acima dos coletores (sobram as fundações 2166270 e
#    2148756 do BP2, contornadas); na mesma cota do hidrante as duas se cruzavam (AF-01 × HI-04, AF-04 × HI-09, AL-03 × HI-01/04/12);
#  - reúso 1,85: só a fundação 2163137 do BP2 (contornada).
# A elétrica fica por cima de todas (0,70 m no mínimo).
COB_REDE = {'HID': float(os.environ.get('PJC_COB_HID') or 0.85),
            'AF-AF': float(os.environ.get('PJC_COB_AF') or 1.00),
            'AF-AL': float(os.environ.get('PJC_COB_AL') or 1.12),
            'AF-RU': float(os.environ.get('PJC_COB_RU') or 1.85)}
# recobrimento fixado por trecho: o EL2-012 desce o talude a oeste do bloco pedagógico (o terreno sobe 1 m em 2 m) e a 0,70 m o topo
# ficava 2 cm acima do terreno no pé do talude
COB_TRECHO = {'ELE:EL2-012': 0.85,
              # elétrica e alarme por cima da água (Revisão D4, 26/10): o estudo descia o EL1-004 sob o HI-15/16 na casa de bombas e o
              # SD-12 sob o AF-03
              'ELE:EL1-004': 0.70, 'SDAI:SD-12': 0.50,
              # o EL1-049 descia a 1,60 m e levava o fundo da EL1-CX23 para baixo da água (AF-03); vai junto com o EL1-039 do mesmo banco
              'ELE:EL1-049': 0.75}


def _mod(nome, arq):
    spec = importlib.util.spec_from_file_location(nome, arq); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


EST = _mod('pjc_estrutura', os.path.join(PJC, 'pjc_estrutura.py'))
GEO = _mod('pjc_geometria', os.path.join(PJC, 'pjc_geometria.py'))


def mat_grav(disc, mat, dn):
    m = (mat or '').upper().replace('-', '')
    if 'DR' in m: return 'Tubo PVC corrugado perfurado (dreno)'
    if disc == 'ESG': return 'Tubo PVC Série Reforçada' if 'PVCR' in m else 'Tubo PVC Série Normal'
    if 'PVCV' in m or (dn and dn >= 250): return 'Tubo PVC Vinilfort'
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
VERIFICACAO_ESPERADA[('degrau', 'DRE-180')] = 'ramal Ø40 chega na junção do coletor Ø200 (DRE-213) pela geratriz de cima'


def pts_csv(s):
    return [tuple(float(v) for v in xy.split(',')) for xy in s.split(';') if xy]


def offset(P, d):
    """polilinha deslocada d m para a esquerda (normal média nos vértices)."""
    P = np.asarray(P, float)
    if abs(d) < 1e-9 or len(P) < 2: return P
    dirs = np.diff(P, axis=0); dirs /= np.linalg.norm(dirs, axis=1)[:, None] + 1e-12
    nrm = np.column_stack([-dirs[:, 1], dirs[:, 0]])
    nv = np.vstack([nrm[0], (nrm[:-1] + nrm[1:]) / 2, nrm[-1]]) if len(nrm) > 1 else np.vstack([nrm[0], nrm[0]])
    nv /= np.linalg.norm(nv, axis=1)[:, None] + 1e-12
    return P + d * nv


def _densificar(P, passo=4.0):
    out = [tuple(P[0][:2])]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(math.ceil(L / passo)))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(1, k + 1)]
    return out


def _perfil(id_, disc, rede, trecho, pts2d, de, ter, **info):
    P = lt.perfil_por_recobrimento(_densificar([tuple(p[:2]) for p in pts2d]), de, COB[disc], ter)
    info.setdefault('DN_mm', round(de * 1000))
    return md.elemento(id_, disc, rede, trecho, 'pressao', de, P, cob_min=COB[disc], situacao='novo',
                       cota=f'topo a {COB[disc]:.2f} m do terreno no mínimo', **info)


def no_campo(E, N, folga=0.5):
    cx, cy, a, hu, hv = CAMPO
    r = math.radians(a); dx, dy = E - cx, N - cy
    u = dx * math.cos(r) + dy * math.sin(r); v = -dx * math.sin(r) + dy * math.cos(r)
    return abs(u) < hu - folga and abs(v) < hv - folga


def _fase3(tag):
    """planta da fase 2 com a GI da fase 3 nas pontas (declividade do rótulo a partir da CF de montante; o que sobra é queda dentro
    da caixa de jusante, conexão vertical): sem isso o tubo ia reto de CF a CF (DRE-020: 27,8 % em vez de 1 % + queda de 1,14 m)."""
    g3 = {r['trecho']: r for r in lt.ler_csv(os.path.join(REL, f'PJC_fase3_{tag}_trechos.csv'))}
    R = lt.ler_csv(os.path.join(REL, f'PJC_fase2_{tag}_trechos.csv'))
    for r in R:
        f = g3.get(r['trecho'])
        if f and f.get('GI_montante') and f.get('GI_jusante'):
            r['CF_montante'], r['CF_jusante'] = f['GI_montante'], f['GI_jusante']
    fn = os.path.join(SAIDA, f'_grav_{tag}.csv')
    with open(fn, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(R[0]), delimiter=';'); w.writeheader(); w.writerows(R)
    return fn


def gravidade(ter):
    esg = lt.gravidade(_fase3('ESG'), 'ESG', 'ESG', ter)
    dre = lt.gravidade(_fase3('DRE'), 'DRE', 'DRE', ter)
    cps = lt.gravidade(os.path.join(REL, 'PJC_fase2_CPS_DRE_trechos.csv'), 'DRE', 'DRE-CPS', ter)
    for e in cps:                    # os trechos do CPS-DRE-001 também se chamam DRE-xxx: prefixo CPS- para não confundir com a DRE-001
        e['trecho'] = 'CPS-' + e['trecho']; e['id'] = f"DRE-CPS:{e['trecho']}"
    grav = [e for e in esg + dre + cps if np.hypot(*(e['pts'][-1, :2] - e['pts'][0, :2])) > 0.05]
    grav = _sem_duplicados(grav)
    _gi_ajuste(grav)
    fora = [e for e in grav if e['rede'] == 'DRE' and no_campo(*e['pts'][0, :2]) and no_campo(*e['pts'][-1, :2])]
    grav = [e for e in grav if e not in fora]
    for e in grav:
        e['info']['material'] = mat_grav(e['disc'], e['info'].get('material'), lt.fl(e['info'].get('DN_mm')))
        e['info']['situacao'] = 'novo'
        e['info']['folha'] = {'ESG': 'ESG-001', 'DRE': 'DRE-001', 'DRE-CPS': 'CPS-DRE-001'}[e['rede']]
    C = lt.caixas(os.path.join(REL, 'PJC_fase2_ESG_caixas.csv'), 'ESG', 'ESG', ter, [e for e in grav if e['rede'] == 'ESG'])
    C += lt.caixas(os.path.join(REL, 'PJC_fase2_DRE_caixas.csv'), 'DRE', 'DRE', ter, [e for e in grav if e['rede'] == 'DRE'])
    C += lt.caixas(os.path.join(REL, 'PJC_fase2_CPS_DRE_caixas.csv'), 'DRE', 'DRE-CPS', ter, [e for e in grav if e['rede'] == 'DRE-CPS'])
    # tampa no terreno do IMP as built (as CT das pranchas são todas 61,00); fundo na CF do projeto
    n = 0
    for c in C:
        z = float(ter.z([[c['E'], c['N']]])[0])
        if not np.isfinite(z): continue
        if abs(z - c['zt']) > 0.10:
            c['info']['CT_projeto'] = c['info'].get('CT'); c['info']['CT'] = round(z, 2); n += 1
        c['zt'] = z
    print(f'  {len(fora)} trechos da DRE-001 dentro do campo saíram (vale o CPS-DRE-001 R01); {n} caixas com a tampa no terreno do IMP (CT ≠ 61,00)')
    return grav, C


# geratriz ajustada (aplicar e avisar, até 0,20 m, declividade mantida) e cota de trecho sem cota no projeto: {trecho: (Δz montante,
# Δz jusante, motivo)}
GI_AJUSTE = {'ESG-12': (0.15, 0.15, 'ramal da edificação sobe inteiro e chega 0,15 m acima do fundo da CES-07; passa sobre o DRE-212'),
             'CPS-DRE-021': (0.0, 0.25, 'trecho do campo sem cota no projeto: chega na CA-02 0,25 m acima do fundo, por cima do DRE-042'),
             'DRE-204': (0.15, 0.15, 'ramal sem cota no projeto (estimada pelo terreno): 0,15 m mais alto, sobre a sapata da guarita')}


def _gi_ajuste(E, log=print):
    for e in E:
        if e['tipo'] != 'gravidade' or e['trecho'] not in GI_AJUSTE: continue
        dm, dj, mot = GI_AJUSTE[e['trecho']]; P = e['pts'].copy()
        s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))]); t = s_ / max(s_[-1], 1e-9)
        P[:, 2] += dm + (dj - dm) * t
        e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None)
        for k, d in (('GI_mont', dm), ('GI_jus', dj)):
            if e['info'].get(k) is not None: e['info'][k] = round(float(e['info'][k]) + d, 3)
        estimada = 'estimada' in str(e['info'].get('cota', ''))
        APLICADO.append(dict(tipo='cota de trecho sem cota no projeto' if estimada else 'geratriz ajustada', trecho=e['trecho'], disc=e['disc'],
                             dz_montante=dm, dz_jusante=dj, motivo=mot, E=float(P[-1, 0]), N=float(P[-1, 1])))
        log(f"  {e['trecho']}: GI {dm * 100:+.0f} cm na montante, {dj * 100:+.0f} cm na jusante ({mot})")


def _sem_duplicados(T, tol=0.25, log=print):
    """tubo de gravidade desenhado duas vezes, lado a lado (DRE-211 sem rótulo a 0,15 m do DRE-212 PVC 200: o mesmo coletor; DRE-163
    Ø40 com as mesmas pontas do DRE-218 PVCR 150): fica o que tem rótulo, depois o de maior Ø."""
    fora = set()
    for i, a in enumerate(T):
        for b in T[i + 1:]:
            if a['id'] in fora or b['id'] in fora or a['disc'] != b['disc']: continue
            pa, pb = a['pts'][[0, -1], :2], b['pts'][[0, -1], :2]
            if min(np.abs(pa - pb).max(), np.abs(pa - pb[::-1]).max()) > tol: continue
            chave = lambda e: (bool(e['info'].get('material')), lt.fl(e['info'].get('DN_mm')) or 0, _comp(e))   # rótulo, maior Ø, mais longo
            fora.add(b['id'] if chave(a) >= chave(b) else a['id'])
    if fora: log(f"  {len(fora)} tubos repetidos no desenho saíram: {', '.join(sorted(x.split(':', 1)[1] for x in fora))}")
    return [e for e in T if e['id'] not in fora]


def pressurizadas(ter):
    E = []
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_AF_trechos.csv')):
        sis = r['sistema']
        de = float(r['diam'].split()[-1]) / 1000 if r['diam'].startswith('DN') else DE_AF_PADRAO[sis]
        E.append(_perfil(f'AF:{r["trecho"]}', 'AF', f'AF-{sis}', r['trecho'], pts_csv(r['vertices_UTM']), de, ter, sistema_af=sis,
                         sub=r['descricao'], material=MAT_AF, folha='AF-001',
                         obs=r['obs'] + ('' if r['diam'] else f' | sem rótulo: DE {de * 1000:.0f} mm (premissa)')))
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_PCI_trechos.csv')):
        P2 = pts_csv(r['vertices_UTM'])
        if r['sistema'] == 'HI':
            E.append(_perfil(f'HID:{r["trecho"]}', 'HID', 'HID', r['trecho'], P2, DE_PEAD.get(r['diam'], 0.075), ter, material=MAT_PRESS['HID'],
                             diametro=r['diam'] or '2.1/2"', folha='IC-001', obs=r['obs']))
        else:
            E.append(_perfil(f'SDAI:{r["trecho"]}', 'SDAI', 'SDAI', r['trecho'], P2, DE_ELE['1"'], ter, material=MAT_PRESS['SDAI'], diametro='1"',
                             folha='IC-001', sub=r['obs'], obs='Ø não rotulado no IC-001: 1" (premissa)'))
    # elétrica: um eletroduto por circuito; bancos lado a lado
    banco = collections.defaultdict(list)
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_ELE_trechos.csv')):
        n = int(r['diam'].split('x')[0]) if 'x' in r['diam'] else 1
        d = r['diam'].split('x')[-1] if r['diam'] else '1"'
        for k in range(n): banco[(r['prancha'], frozenset((r['de'], r['para'])))].append((r, d, k, n))
    for (prancha, _), itens in banco.items():
        itens.sort(key=lambda t: (t[0]['circuito'], t[2]))
        des = [DE_ELE.get(d, 0.0334) for r, d, k, n in itens]; passo = max(des) + 0.05
        for j, ((r, d, k, n), de) in enumerate(zip(itens, des)):
            off = (j - (len(itens) - 1) / 2) * passo
            P2 = offset(np.array(pts_csv(r['vertices_UTM'])), off)
            tr = r['trecho'] + (f'.{k + 1}' if n > 1 else '')
            E.append(_perfil(f'ELE:{tr}', 'ELE', 'ELE', tr, P2, de, ter, sub=f"{prancha} {r['circuito']}", diametro=d, material=MAT_ELE,
                             folha=prancha, circuitos=r['circuito'],
                             obs='; '.join(x for x in (r['fonte_diam'], r['obs'], 'sem rótulo: 1" (premissa)' if not r['diam'] else '',
                                                       f'banco: {len(itens)} eletrodutos lado a lado' if len(itens) > 1 else '') if x)))
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_CPS_ELE_trechos.csv')):
        E.append(_perfil(f'ELE:{r["trecho"]}', 'ELE', 'ELE', r['trecho'], pts_csv(r['vertices_UTM']), DE_ELE['1"'], ter, diametro='1"',
                         sub=f'CPS EL-001 circuitos {r["circuitos"]}', material=MAT_ELE, folha='CPS-EL-001', circuitos=r['circuitos'],
                         obs=f'{r["de"]} -> {r["para"]}; traçado reto caixa a caixa (marcas de fiação da prancha)'))
    return E


def caixas_pressao(E, ter):
    C = []
    def fundo(els, Ex, Nx, raio, zt):
        zs = [p[2] - e['de'] / 2 for e in els for p in e['pts'] if np.hypot(p[0] - Ex, p[1] - Nx) < raio]
        return (min(zs) if zs else zt - 0.6) - 0.15
    sdai = [e for e in E if e['disc'] == 'SDAI']; ele = [e for e in E if e['disc'] == 'ELE']
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_PCI_nos.csv')):
        if r['sistema'] != 'SD': continue
        Ex, Nx = float(r['E']), float(r['N']); zt = float(ter.z([[Ex, Nx]])[0])
        C.append(md.caixa(f'SDAI:{r["no"]}', 'SDAI', 'SDAI', 'q', Ex, Nx, 0.25, fundo(sdai, Ex, Nx, 1.0, zt), zt, nome=r['no'], situacao='novo',
                          tipo='caixa de passagem do alarme (0,40 premissa)', folha='IC-001', cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto'))
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_ELE_caixas.csv')):
        Ex, Nx, lado = float(r['E']), float(r['N']), float(r['lado_desenhado_m']); zt = float(ter.z([[Ex, Nx]])[0])
        pr = 'EL-001' if r['prancha'] == 'EL1' else 'EL-002'
        els = [e for e in ele if e['info'].get('folha') == pr]
        nome = r['caixa'] if r['caixa'].startswith(r['prancha']) else f'{r["prancha"]}-{r["caixa"]}'
        C.append(md.caixa(f'ELE:{nome}', 'ELE', 'ELE', 'q', Ex, Nx, lado / 2 + 0.05, fundo(els, Ex, Nx, max(1.0, lado), zt), zt,
                          nome=nome, tipo=r['rotulo'] or f'caixa {lado:.2f}', situacao='novo', folha=pr,
                          cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto mais baixo'))
    cps = [e for e in ele if e['info'].get('folha') == 'CPS-EL-001']
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_CPS_ELE_caixas.csv')):
        Ex, Nx = float(r['E']), float(r['N']); zt = float(ter.z([[Ex, Nx]])[0])
        C.append(md.caixa(f'ELE:CPS-{r["caixa"]}', 'ELE', 'ELE', 'q', Ex, Nx, float(r['lado_m']) / 2 + 0.05, fundo(cps, Ex, Nx, 1.0, zt), zt,
                          nome=f'CPS-{r["caixa"]}', tipo=r['rotulo'], situacao='novo', folha='CPS-EL-001', cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto'))
    return C


CLASSE_EQ = [('base de concreto', 'IfcFooting', 'PAD_FOOTING'), ('poste', 'IfcLightFixture', 'NOTDEFINED'),
             ('quadro', 'IfcElectricDistributionBoard', 'DISTRIBUTIONBOARD'), ('reservatório', 'IfcTank', 'STORAGE'),
             ('recalque', 'IfcFireSuppressionTerminal', 'BREECHINGINLET'), ('abrigo', 'IfcFireSuppressionTerminal', 'HOSEREEL'),
             ('extintor', 'IfcFireSuppressionTerminal', 'USERDEFINED')]


def equipamentos(ter):
    C = []
    for r in lt.ler_csv(os.path.join(REL, 'PJC_equipamentos.csv')):
        if 'ETE' in r['id'].upper().split('-'): continue          # quadro da ETE: fora do escopo (a rede termina no limite)
        Ex, Nx = float(r['E']), float(r['N'])
        z0 = float(ter.z([[Ex, Nx]])[0]) if r['z_ref'] == 'terreno' else float(r['z_ref'])
        zb, zt = z0 + float(r['zb_rel']), z0 + float(r['zt_rel'])
        info = dict(nome=r['id'], tipo=r['tipo'], cota=('relativa ao terreno do IMP' if r['z_ref'] == 'terreno' else f'base na cota {z0:.2f}'),
                    fonte=r['fonte'], premissa=r['premissa'], equipamento=True, situacao='novo')
        info.update(next(({'classe_ifc': k, 'pred': p} for chave, k, p in CLASSE_EQ if chave in r['tipo'].lower()), {}))
        disc = r['disc']; rede = 'ELE' if disc == 'ELE' else r['rede']
        if r['forma'] == 'c':
            C.append(md.caixa(f'EQ:{r["id"]}', disc, rede, 'c', Ex, Nx, float(r['lx']) / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f'EQ:{r["id"]}', disc, rede, Ex, Nx, float(r['lx']), float(r['ly']),
                                         math.radians(float(r['rot_graus'])), zb, zt, **info))
    return C


def _predios():
    from shapely.ops import unary_union
    return unary_union([p for n, p in EST.contornos() if n != 'quadra coberta'])


def cortar(U, P):
    """polilinha 3D -> pedaços FORA dos prédios (lista de arrays n×3), com a cota interpolada no corte."""
    from shapely.geometry import LineString, Point
    P = np.asarray(P, float)
    if len(P) < 2: return [P]
    L = LineString(P[:, :2])
    if not L.intersects(U): return [P]
    fora = L.difference(U)
    if fora.is_empty: return []
    S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
    pecas = []
    for g in (fora.geoms if hasattr(fora, 'geoms') else [fora]):
        if g.length < 0.05: continue
        Q = np.array(g.coords); s = np.array([L.project(Point(q)) for q in Q])
        z = np.interp(s, S, P[:, 2]) if S[-1] > 0 else np.full(len(Q), P[0, 2])
        pecas.append(np.column_stack([Q, z]))
    return pecas


def _comp(e):
    return float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)))


def so_externo(E, C, log=print):
    """só a rede externa (Anderson, 21/10/2026): trecho cortado na face do prédio; o que fica dentro sai."""
    from shapely.geometry import Point
    U = _predios(); Ui = U.buffer(-0.05)
    novos, n_cort, n_fora = [], 0, 0
    for e in E:
        pecas = cortar(U, e['pts'])
        if not pecas: n_fora += 1; continue
        if len(pecas) == 1 and len(pecas[0]) == len(e['pts']) and np.allclose(pecas[0], e['pts']): novos.append(e); continue
        n_cort += 1
        for k, P in enumerate(pecas):
            if len(P) < 2: continue
            e2 = dict(e, id=e['id'] + (f'~{k + 1}' if len(pecas) > 1 else ''), pts=P, pts_sol=P.copy(), info=dict(e['info']), cortado=True)
            e2.pop('S', None); novos.append(e2)
    C2 = [c for c in C if c['disc'] == 'EST' or c['info'].get('so_clash') or not Ui.contains(Point(c['E'], c['N']))]
    novos = [e for e in novos if not e.get('cortado') or _comp(e) >= 0.80]
    log(f'  só rede externa: {n_fora} trechos inteiros dentro dos prédios saíram, {n_cort} cortados na face; '
        f'{len(C) - len(C2)} caixas/equipamentos de dentro saíram')
    return novos, C2


def _sem_soltos(E, C, log=print):
    """pedaço de eletroduto/alarme solto (componente com menos de 3 m sem ponta em caixa da disciplina) sai."""
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
    if fora: log(f"  {len(fora)} pedaços de eletroduto soltos saíram: {', '.join(sorted(x.split(':')[1] for x in fora))}")
    return [e for e in E if e['id'] not in fora]


def _soldar_pontas(E, tol=0.03):
    pts = [(e, k) for e in E if e['tipo'] == 'pressao' for k in (0, -1)]
    feito = set()
    for i, (e, k) in enumerate(pts):
        if (id(e), k) in feito: continue
        g = [(e, k)] + [(f, j) for f, j in pts[i + 1:] if f['disc'] == e['disc'] and (id(f), j) not in feito
                        and 0 < np.hypot(*(f['pts'][j, :2] - e['pts'][k, :2])) < tol]
        if len(g) < 2: continue
        m = np.mean([x['pts'][j, :2] for x, j in g], axis=0)
        for x, j in g:
            x['pts'] = x['pts'].copy(); x['pts'][j, :2] = m; x['pts_sol'] = x['pts'].copy(); x.pop('S', None); feito.add((id(x), j))


def _registrar_planta(E):
    fn = os.path.join(SAIDA, f'{SIGLA}_contornos.json')
    reg = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []
    reg = [r for r in reg if not r.get('final')]
    for e in E:
        if e['tipo'] != 'pressao' or 'pts_planta0' not in e: continue
        a, b = np.asarray(e['pts_planta0'])[:, :2], e['pts'][:, :2]
        if a.shape == b.shape and np.abs(a - b).max() < 0.01: continue
        reg.append(dict(trecho=e['trecho'], disc=e['disc'], elemento=e['id'], caixa='', status='contorno em planta', final=True,
                        antigo=[list(map(float, p)) for p in a], pontos=[list(map(float, p)) for p in b]))
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _patches():
    """perfil que acompanha o terreno nos taludes, pontas rebaixadas em rampa, elétrica por cima da água (funções da Sátiro,
    escolas/satiro.py), fundo das caixas de passagem pelo eletroduto mais fundo e o poste anda com a base."""
    from preclash import estudo as _est, desvio as _dsv
    if getattr(_est, '_pjc', False): return
    S = _mod('sat_aux', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'satiro.py'))
    S.REGRAS['estudo']['prof_max'] = REGRAS['estudo']['prof_max']
    def perfil(pts2d, de, cob, ter, passo=0.5, desvio=0.20, trecho_min=2.0):
        return GEO.perfil_suave(S.perfil_talude(pts2d, de, cob, ter), ter, cob, de)      # rampa até 1:0,8 no degrau de piso
    _est.perfil_por_recobrimento = perfil; _dsv.perfil_por_recobrimento = perfil
    est0 = _est.estudar

    def estudar(E, caixas, regras, ter, log=print):
        rel = est0(E, caixas, regras, ter, log=log)
        S._rampas(E, caixas, ter, log)
        for c in caixas:
            if c['disc'] not in ('ELE', 'SDAI') or c['info'].get('equipamento'): continue
            L = _est._ligados(c, E)
            if L: c['zb'] = min(float(e['pts'][k, 2]) - e['de'] / 2 for e, k in L) - 0.10
        return rel
    _est.estudar = estudar
    ap0 = _dsv.aplicar

    def aplicar(E, C, pend, regras, ter, log=print):
        antes = {e['id']: e['pts'][:, :2].copy() for e in E}
        dv = ap0(E, C, pend, regras, ter, log=log)
        S._postes_com_a_base(C, ter)
        GEO.curvas_no_tubo(E, log=log)          # canto novo dos desvios da ferramenta também vira curva no PEAD
        for e in E:
            a = antes.get(e['id'])
            if a is not None and (a.shape != e['pts'][:, :2].shape or np.abs(a - e['pts'][:, :2]).max() > 0.01):
                e.setdefault('pts_planta0', np.column_stack([a, e['pts'][:len(a), 2]]) if a.shape[0] <= len(e['pts']) else e['pts'].copy())
        _registrar_planta(E)
        return dv
    _dsv.aplicar = aplicar
    mv0 = _dsv.mover_caixas

    def mover_caixas(E, C, pend, regras, log=print, ter=None):
        """caixa que a ferramenta deslocou: a tampa vai para o terreno do lugar novo (Revisão D5: a PVE-07 ficava 8 cm acima e a CX03
        do alarme 19 cm); o fundo fica."""
        antes = {c['id']: (c['E'], c['N']) for c in C}
        r = mv0(E, C, pend, regras, log=log, ter=ter)
        T = ter or Terreno(TERRENO)
        for c in C:
            a = antes.get(c['id'])
            if a and (abs(c['E'] - a[0]) + abs(c['N'] - a[1])) > 1e-6 and c['disc'] != 'EST':
                z = float(T.z([[c['E'], c['N']]])[0])
                if np.isfinite(z): c['zt'] = z
        return r
    _dsv.mover_caixas = mover_caixas
    S._custo_eletrica_acima()
    g0 = _est.grupos

    def grupos(E, caixas, cfg):
        out = []
        for g in g0(E, caixas, cfg):
            sep = [e for e in g['els'] if e['id'].split('~')[0] in COB_TRECHO and g['disc'] in cfg['por_rede']]
            resto = [e for e in g['els'] if e not in sep]
            if resto: out.append(dict(g, els=resto))
            out += [{'disc': g['disc'], 'nome': f"{g['disc']} trecho {e['trecho']}", 'els': [e]} for e in sep]
        return out
    _est.grupos = grupos
    # rede cortada na face do prédio × estrutura do próprio prédio junto da face (a menos de 0,60 m do contorno): é a passagem da rede
    # pela parede, não conflito de rede externa (mesmo critério da Sátiro e da Catu)
    from preclash import clash as _cl
    from shapely.geometry import Point
    B = _predios().boundary
    det0 = _cl.detectar

    def detectar(elementos, caixas, regras, *a, **k):
        conf = det0(elementos, caixas, regras, *a, **k)
        cort = {x['id'] for x in elementos if x.get('cortado') or min(B.distance(Point(*x['pts'][k, :2])) for k in (0, -1)) < 1.00}
        est = {x['id'] for x in caixas if x['disc'] == 'EST'}
        conf = [c for c in conf if not (((c['a'] in est and c['b'] in cort) or (c['b'] in est and c['a'] in cort))
                                        and B.distance(Point(c['E'], c['N'])) < 0.60)]
        # ramal pluvial que nasce na descida da cobertura junto do pilar da quadra coberta (prumada AP no pilar) × a fundação desse
        # pilar, a menos de 1,00 m da ponta do ramal: é a ligação com a descida, não conflito de rede externa
        qdc = {x['id'] for x in caixas if x['disc'] == 'EST' and x['info'].get('bloco') == 'QDC'}
        pontas = {x['id']: x['pts'][[0, -1], :2] for x in elementos if x['tipo'] == 'gravidade'}
        def na_ponta(c):
            t = c['a'] if c['b'] in qdc else c['b']
            return t in pontas and min(np.hypot(*(q - (c['E'], c['N']))) for q in pontas[t]) < 1.00
        return [c for c in conf if not ((c['a'] in qdc or c['b'] in qdc) and na_ponta(c))]
    _cl.detectar = detectar
    _est._pjc = True


def carregar():
    os.makedirs(SAIDA, exist_ok=True)
    APLICADO.clear()
    ter = Terreno(TERRENO)
    E = pressurizadas(ter)
    G, C = gravidade(ter)
    E += G
    C += caixas_pressao(E, ter)
    C += equipamentos(ter)
    E = _sem_soltos(E, C)
    _soldar_pontas(E)
    E, C = so_externo(E, C)
    C += EST.estrutura(md=md)
    # bancos de eletrodutos no mesmo caminho vão para o lado antes dos contornos (os contornos são calculados no caminho já separado)
    GEO.separar_bancos(E)
    # ajustes em planta sobre os pares críticos da rodada anterior (pojuca/ifc/pjc_pares.py -> PJC_ajustes_pares.json): caixas de
    # passagem e postes (com a base) deslocados até 1,50 m com os eletrodutos, contornos curtos de PV/peça da estrutura, vértice fora
    # de caixa (aplicar e avisar)
    fp = os.path.join(SAIDA, f'{SIGLA}_ajustes_pares.json')
    if os.path.exists(fp) and os.environ.get('PJC_SEM_AJUSTES') != '1':
        AJ = _mod('pjc_ajustes', os.path.join(PJC, 'pjc_ajustes.py'))
        J = json.load(open(fp, encoding='utf-8'))
        antes = {c['id']: (c['E'], c['N']) for c in C}
        AJ.mover_caixas(E, C, set(J['caixas']), SAIDA, passo_max=1.50)
        AJ.contornar(E, C, [tuple(x) for x in J['contornos']], SAIDA)
        AJ.afastar_pontas(E, C, SAIDA)
        for c in C:                          # caixa/poste que o ajuste deslocou: tampa no terreno do lugar novo
            a = antes.get(c['id'])
            if a and (abs(c['E'] - a[0]) + abs(c['N'] - a[1])) > 1e-6:
                dz = float(ter.z([[c['E'], c['N']]])[0] - ter.z([a])[0])
                if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
    # limpeza da geometria (Revisão de 26/10: C2, C4, C6, D6): tubo repetido, bancos no mesmo caminho, curvas no PEAD, bases de poste
    E = GEO.sem_repetidos(E, lt)
    E = GEO.juntar_curtos(E)
    GEO.soldar_gravidade(E, C, md)
    GEO.separar_trechos(E)
    GEO.curvas_no_tubo(E)
    for b in GEO.bases_de_poste(E, C, ter, md):
        APLICADO.append(dict(tipo='base de poste deslocada', texto=b))
    GEO.pontas_nas_bases(E, C, md)
    REGRAS['estudo']['fixar_perto_de'] = [c['id'] for c in C if 'reservatório' in c['info'].get('tipo', '').lower()]
    REGRAS['estudo']['cob_fixo'] = {e['id']: COB_REDE.get(e['rede'], COB_REDE.get(e['disc'])) for e in E if e['tipo'] == 'pressao' and (e['rede'] in COB_REDE or e['disc'] in COB_REDE)}
    REGRAS['estudo']['cob_fixo'].update({e['id']: COB_TRECHO[e['id'].split('~')[0]] for e in E if e['id'].split('~')[0] in COB_TRECHO})
    _patches()
    json.dump(APLICADO, open(os.path.join(SAIDA, f'{SIGLA}_aplicado_carregamento.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas, terreno do IMP as built',
                               'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py): pranchas no padrão de executivo final
REVISAO = 'R01'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.30
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.60)
EXECUTIVO_NOTA_RAIO = 25.0         # a alimentação dos reservatórios (AF-001) ramifica muito: 3 notas iguais a menos de 15 m (Revisão E4)
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1] if el.count(':') >= 1 else el
_PO = 'PROJETO_ORIGINAL/'
_DWG = {'AF-001': _PO + 'IMP/01_AF/24-049-PJC-CTO-ETIB-IMP-PE-AF-001-AFR-R00.dwg',
        'ESG-001': _PO + 'IMP/02_ESG/24-049-PJC-CTO-ETIB-IMP-PE-ESG-001-HIG-R00.dwg',
        'DRE-001': _PO + 'IMP/03_DRE/24-049-PJC-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg',
        'EL-001': _PO + 'IMP/04_ELE/24-049-PJC-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg',
        'EL-002': _PO + 'IMP/04_ELE/24-049-PJC-CTO-ETIB-IMP-PE-EL-002-ELG-R00.dwg',
        'IC-001': _PO + 'IMP/05_PCI/24-049-PJC-CTO-ETIB-IMP-PE-IC-001-INC-R01.dwg',
        'CPS-DRE-001': _PO + 'CPS/03_DRE/24-049-PJC-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dwg',
        'CPS-EL-001': _PO + 'CPS/04_ELE/24-049-PJC-CTO-ETIB-CPS-PE-EL-001-ELG-R01.dwg'}


def folha(m):
    d = m['disc']; t = str(m.get('trecho') or m.get('elemento') or '')
    if d == 'ELE':
        if 'CPS' in t or 'CAMPO' in t: return 'CPS-EL-001'
        return 'EL-002' if ('EL2' in t or 'IE-' in t) else 'EL-001'
    if d == 'DRE': return 'CPS-DRE-001' if 'CPS' in t else 'DRE-001'
    return {'AF': 'AF-001', 'ESG': 'ESG-001', 'HID': 'IC-001', 'SDAI': 'IC-001'}.get(d)


def executivo_dwg(m):
    return _DWG.get(m.get('folha') or folha(m))


def _transf():
    import glob
    out = {}
    for fn in glob.glob(os.path.join(BASE, 'CAD_GEORREFERENCIADO', 'transformacao_*_local_para_UTM.json')):
        J = json.load(open(fn, encoding='utf-8'))
        if 'rigid' in J and 'fonte' in J:
            out[J['fonte']] = (float(J['rigid']['rot_deg']), tuple(J['rigid']['t']))
    return out


TRANSF_DWG = _transf()
