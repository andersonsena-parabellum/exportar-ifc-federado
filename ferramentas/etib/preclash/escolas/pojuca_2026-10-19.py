# -*- coding: utf-8 -*-
"""Adaptador da ETIB Pojuca para o preclash.
Fontes (só leitura): ETIB-POJUCA/RELATORIOS/PJC_fase2_*.csv (thread da escola, 18/10/2026; ver PJC_Fases_2-3_redes_sem_Revit.md).
Decisões em aberto com o usuário — usada a opção recomendada (18/10/2026, liberação para seguir sem o Revit):
  - drenagem do campo society = CPS-DRE-001 R01 (cenário A: a espinha de drenos da DRE-001 dentro do campo sai);
    o cenário B é o projeto como está desenhado (as duas drenagens no campo);
  - IMP_QUADRA (PI000) fora (é outra implantação);
  - profundidades das pressurizadas (premissas P1-P4 do relatório): AF/reúso/alimentação 0,30 m; hidrantes 0,50 m (nota 5
    do IC-001); SDAI 0,60 m; elétrica 0,70 m — topo do tubo/eletroduto abaixo do terreno; sem polígono de área de veículos;
  - alimentador do QD-ETE (EL-001) incluído até o quadro (conduto da implantação; a ETE em si está fora).
Decisões pequenas do preclash de 18/10 (opção recomendada, 19/10/2026, Anderson fora — registrar na entrega):
  - elétrica aceita Δz de até 1,25 m por cruzamento (era 1,00), para o AF-03 × EL1-029 (Δz 1,20 m) sair por profundidade;
  - caixas EL2-CX05 e EL2-CX12 deslocadas em planta (ver CAIXAS_MOVIDAS), com os eletrodutos que chegam nelas.
Piloto do padrão de entrega (19/10/2026, Anderson e Daniel): mergulho antes de mudar traçado (SDAI/HID/AF até Δz 1,20 m),
nenhuma rede com topo a mais de 1,50 m do terreno; água fria com nós a cada 4 m (o perfil acompanha o terreno, P1 = 0,30 m);
contornos curtos da água fria/reúso nas caixas que estão sobre o traçado (PJC_af_desvios.csv, AF_DESVIOS) no lugar dos
deslocamentos longos (40 a 60 m) que a ferramenta escolhia; postes deslocados pela ferramenta entram no
PJC_caixas_deslocadas.csv (base e haste juntas).
Pressurizadas sem cota no projeto: leitura.perfil_por_recobrimento() sobre o terreno do IMP as built.
Elétrica: um eletroduto por circuito (bancos lado a lado, afastados de DE + 0,05 m); '3x4"' = 3 eletrodutos de 4".
Elétrica do campo society (CPS EL-001 R01): eletroduto PEAD Ø1" caixa a caixa (PJC_fase2_CPS_ELE_*.csv), rede ELE-CPS.
Equipamentos (PJC_equipamentos.csv, gerado por work/POJUCA/scripts/equipamentos_pojuca.py): postes e bases, quadros,
reservatórios, hidrante de recalque, abrigo e extintores do campo, como caixas retangulares/circulares (dimensões de premissa
onde o projeto não dá).
Terreno: IMP as built (escolas/dados/pojuca_terreno.npz, pojuca_terreno.py v3: pisos externos, plataformas e taludes).
Estrutura as built (EST): blocos+pedestais, sapatas, baldrames e arranques dos RVT de fundação/estrutura de REFERENCIAS_RVT,
posicionados pelos vínculos do IMP (PJC_estrutura_asbuilt.csv, work/POJUCA/scripts/estrutura_pojuca.py); só a 1,5 m das redes."""
import os, math, csv, collections
import numpy as np
from preclash import leitura as lt
from preclash import modelo as md
from preclash.terreno import Terreno
from shapely.geometry import Point as Point2

ESCOLA = 'ETIB Pojuca'
SIGLA = 'PJC'
BASE = r'D:\Projeto Modelagem\ETIB-POJUCA'
REL = os.path.join(BASE, 'RELATORIOS')
SAIDA = os.path.join(REL, 'PRECLASH_2026-10-18')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'pojuca_terreno.npz')
ORIGEM = (572450.0, 8626500.0, 0.0)       # origem proposta dos RVTs (E, N, cota) — AGENTS.md
EPSG = 31984                              # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (572370.0, 8626420.0, 572570.0, 8626615.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    'dz_max': {'ELE': 1.25, 'SDAI': 1.20, 'HID': 1.20, 'AF': 1.20},      # mergulho mais fundo antes de mudar traçado (Anderson e Daniel, 19/10; teto 1,50 m)
    'prof_max_topo': {'ELE': 1.50, 'SDAI': 1.50, 'HID': 1.50, 'AF': 1.50},   # teto de 1,50 m do terreno ao topo (Anderson, 19/10)
    'agua_acima_de': ['ESG'],
}

DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'AP', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}
# classe IFC dos equipamentos (palavra do tipo -> classe, predefinido); estrutura sai pelo tipo (viga -> IfcBeam, pilar -> IfcColumn, resto IfcFooting)
CLASSE_EQ = [('base de concreto', 'IfcFooting', 'PAD_FOOTING'), ('poste', 'IfcLightFixture', 'NOTDEFINED'),
             ('quadro', 'IfcElectricDistributionBoard', 'DISTRIBUTIONBOARD'), ('reservatório', 'IfcTank', 'STORAGE'),
             ('recalque', 'IfcFireSuppressionTerminal', 'BREECHINGINLET'), ('abrigo', 'IfcFireSuppressionTerminal', 'HOSEREEL'),
             ('extintor', 'IfcFireSuppressionTerminal', 'USERDEFINED')]

# ---------------- passo 7 (executivo/rever.py): prancha de cada mudança e transformação local -> UTM de cada DWG
REVISAO = 'R01'
EXECUTIVO_TEXTO = 0.30
_DWG = {'EL1': 'PROJETO_ORIGINAL/IMP/04_ELE/24-049-PJC-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg',
        'EL2': 'PROJETO_ORIGINAL/IMP/04_ELE/24-049-PJC-CTO-ETIB-IMP-PE-EL-002-ELG-R00.dwg',
        'CPS': 'PROJETO_ORIGINAL/CPS/04_ELE/24-049-PJC-CTO-ETIB-CPS-PE-EL-001-ELG-R01.dwg',
        'AF': 'PROJETO_ORIGINAL/IMP/01_AF/24-049-PJC-CTO-ETIB-IMP-PE-AF-001-AFR-R00.dwg',
        'PCI': 'PROJETO_ORIGINAL/IMP/05_PCI/24-049-PJC-CTO-ETIB-IMP-PE-IC-001-INC-R01.dwg'}


def executivo_dwg(m):
    el = m.get('elemento') or ''
    for pref, k in (('ELE:EL1', 'EL1'), ('ELE-EL1:', 'EL1'), ('ELE:EL2', 'EL2'), ('ELE-EL2:', 'EL2'), ('ELE:CPS', 'CPS'), ('ELE-CPS:', 'CPS'),
                    ('EQ:POSTE-CAMPO', 'CPS'), ('EQ:QDLT-CAMPO', 'CPS'), ('EQ:POSTE-IE', 'EL2'), ('EQ:Q', 'EL1'), ('AF:', 'AF'),
                    ('HID:', 'PCI'), ('SDAI:', 'PCI'), ('EQ:HID', 'PCI')):
        if el.startswith(pref):
            return _DWG[k]
    return None


def _transf():
    import glob, json
    out = {}
    for fn in glob.glob(os.path.join(BASE, 'CAD_GEORREFERENCIADO', 'transformacao_*_local_para_UTM.json')):
        J = json.load(open(fn, encoding='utf-8'))
        if 'rigid' in J and 'fonte' in J:
            out[J['fonte']] = (float(J['rigid']['rot_deg']), tuple(J['rigid']['t']))
    return out


TRANSF_DWG = _transf()

NOMES_DISC = {'AF': 'Água fria / reúso / alimentação', 'ESG': 'Esgoto', 'AP': 'Drenagem pluvial (DRE-001)',
              'DRE': 'Drenagem do campo society (CPS)', 'ELE': 'Elétrica enterrada e iluminação externa', 'HID': 'Hidrantes e equipamentos de PCI',
              'SDAI': 'SDAI (PCI)', 'EST': 'Estrutura as built (fundações e baldrames dos blocos)'}

COB = {'AF': 0.30, 'HID': 0.50, 'SDAI': 0.60, 'ELE': 0.70}                     # premissas P1-P4
DE_ELE = {'3/4"': 0.0267, '1"': 0.0334, '1.1/4"': 0.0422, '1.1/2"': 0.0483, '2"': 0.0603, '2.1/2"': 0.0730, '3"': 0.0889, '4"': 0.1143}
DE_PEAD = {'2.1/2"': 0.075, '3"': 0.085}                                         # quadro de bitolas do IC-001
DE_AF_PADRAO = {'AF': 0.050, 'RU': 0.025, 'AL': 0.032}
# caixas deslocadas em planta (id da caixa -> (dE, dN) em m); preenchido depois de conferir a rodada com o terreno do IMP
CAIXAS_MOVIDAS = {}
_desloc = os.path.join(REL, 'PJC_caixas_deslocadas.csv')     # gerado por work/POJUCA/scripts/mover_caixas_pojuca.py (deslizar no eletroduto primeiro)
if os.path.exists(_desloc) and not os.environ.get('PJC_SEM_DESLOC'):
    for _r in csv.DictReader(open(_desloc, encoding='utf-8-sig'), delimiter=';'):
        CAIXAS_MOVIDAS[_r['id']] = (float(_r['dE']), float(_r['dN']))
# campo society (bloco CAMPO30x50 da SIT levado ao UTM): centro, giro, meios lados (54,3 x 34,3)
CAMPO = (572450.75784, 8626477.20656, 28.552937, 27.15, 17.15)


def pts_csv(s):
    return [tuple(float(v) for v in xy.split(',')) for xy in s.split(';') if xy]


def offset(P, d):
    """polilinha deslocada d m para a esquerda (normal média nos vértices)."""
    P = np.asarray(P, float)
    if abs(d) < 1e-9 or len(P) < 2:
        return P
    dirs = np.diff(P, axis=0); dirs /= np.linalg.norm(dirs, axis=1)[:, None] + 1e-12
    nrm = np.column_stack([-dirs[:, 1], dirs[:, 0]])
    nv = np.vstack([nrm[0], (nrm[:-1] + nrm[1:]) / 2, nrm[-1]]) if len(nrm) > 1 else np.vstack([nrm[0], nrm[0]])
    nv /= np.linalg.norm(nv, axis=1)[:, None] + 1e-12
    return P + d * nv


def deslocar_rota(P, d):
    """rota deslocada d m para a esquerda no miolo, pontas fixas (nas caixas), transições a 45° de comprimento |d|."""
    P = np.asarray(P, float)[:, :2]
    if abs(d) < 1e-9 or len(P) < 2: return P
    S = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))]); L = S[-1]
    if L < 2 * abs(d) + 0.5: return P
    s = np.unique(np.concatenate([S, [abs(d), L - abs(d)]]))
    s = s[(s >= abs(d) - 1e-9) & (s <= L - abs(d) + 1e-9)]
    Q = np.column_stack([np.interp(s, S, P[:, 0]), np.interp(s, S, P[:, 1])])
    return np.vstack([P[0], offset(Q, d), P[-1]])


# bancos de eletrodutos deslocados inteiros (work/POJUCA/scripts/banco_pojuca.py): (prancha, frozenset(caixas)) -> (caixa de origem, d)
BANCOS = {}
_bancos = os.path.join(REL, 'PJC_bancos_deslocados.csv')
if os.path.exists(_bancos) and not os.environ.get('PJC_SEM_BANCOS'):
    for _r in csv.DictReader(open(_bancos, encoding='utf-8-sig'), delimiter=';'):
        BANCOS[(_r['prancha'], frozenset((_r['de'], _r['para'])))] = (_r['de'], float(_r['d_m']))


# contornos curtos da água fria/reúso em volta das caixas que ficam sobre o traçado (work/POJUCA/scripts/af_desvios_avaliar.py):
# trecho -> [(s0, s1, d)], estações no traçado original, d + = esquerda; no lugar dos deslocamentos longos que a ferramenta escolhia
AF_DESVIOS = collections.defaultdict(list)
_afd = os.path.join(REL, 'PJC_af_desvios.csv')
if os.path.exists(_afd) and not os.environ.get('PJC_SEM_AFDESV'):
    for _r in csv.DictReader(open(_afd, encoding='utf-8-sig'), delimiter=';'):
        AF_DESVIOS[_r['trecho']].append((float(_r['s0']), float(_r['s1']), float(_r['d_m'])))


def af_desviado(trecho, P2):
    from preclash.desvio import _deslocar
    P = np.asarray(P2, float)[:, :2]
    for s0, s1, d in sorted(AF_DESVIOS.get(trecho, []), reverse=True):      # do fim para o começo (estações do original)
        P = _deslocar(P, s0, s1, d)
    return P


def no_campo(E, N, folga=0.5):
    cx, cy, a, hu, hv = CAMPO
    r = math.radians(a); dx, dy = E - cx, N - cy
    u = dx * math.cos(r) + dy * math.sin(r); v = -dx * math.sin(r) + dy * math.cos(r)
    return abs(u) < hu - folga and abs(v) < hv - folga


AF_PASSO = 4.0      # AF: nós a cada 4 m para o perfil acompanhar o terreno (P1 = topo a 0,30 m); com só os vértices da planta
                    # a rampa reta afundava até 0,85 m no meio dos trechos longos e caía na cota da elétrica (19/10/2026)


def densificar(P2, passo):
    P = np.asarray(P2, float)[:, :2]; out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.hypot(*(b - a)) / passo)))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def pressao(id, disc, rede, trecho, P2, de, ter, **info):
    if disc == 'AF' and not os.environ.get('PJC_AF_RETO'): P2 = densificar(P2, AF_PASSO)
    P = lt.perfil_por_recobrimento(P2, de, COB[disc], ter)
    return md.elemento(id, disc, rede, trecho, 'pressao', de, P, cob_min=COB[disc],
                       cota=f'premissa: topo a {COB[disc]:.2f} m do terreno do IMP as built', **info)


def carregar():
    ter = Terreno(TERRENO)
    E, C = [], []
    # ---------------- gravidade (cotas do projeto)
    esg = lt.gravidade(os.path.join(REL, 'PJC_fase2_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    dre = lt.gravidade(os.path.join(REL, 'PJC_fase2_DRE_trechos.csv'), 'AP', 'DRE-001', ter)
    cps = lt.gravidade(os.path.join(REL, 'PJC_fase2_CPS_DRE_trechos.csv'), 'DRE', 'CPS-DRE', ter)
    grav = [e for e in esg + dre + cps if np.hypot(*(e['pts'][-1, :2] - e['pts'][0, :2])) > 0.05]   # tira laços de comprimento zero
    removidos = []
    for e in grav:
        if e['rede'] == 'DRE-001' and no_campo(*e['pts'][0, :2]) and no_campo(*e['pts'][-1, :2]):
            e['campo_dre001'] = True; removidos.append(e)
    os.makedirs(SAIDA, exist_ok=True)
    with open(os.path.join(SAIDA, 'PJC_preclash_DRE-001_espinha_do_campo_fora_no_cenario_A.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['trecho', 'DN_mm', 'L_m_planta', 'E_ini', 'N_ini', 'E_fim', 'N_fim'])
        for e in removidos:
            w.writerow([e['trecho'], e['info'].get('DN_mm'), round(float(np.hypot(*(e['pts'][-1, :2] - e['pts'][0, :2]))), 2),
                        *np.round(e['pts'][0, :2], 3), *np.round(e['pts'][-1, :2], 3)])
    E += grav
    C += lt.caixas(os.path.join(REL, 'PJC_fase2_ESG_caixas.csv'), 'ESG', 'ESG', ter, [e for e in grav if e['rede'] == 'ESG'])
    C += lt.caixas(os.path.join(REL, 'PJC_fase2_DRE_caixas.csv'), 'AP', 'DRE-001', ter, [e for e in grav if e['rede'] == 'DRE-001'])
    C += lt.caixas(os.path.join(REL, 'PJC_fase2_CPS_DRE_caixas.csv'), 'DRE', 'CPS-DRE', ter, [e for e in grav if e['rede'] == 'CPS-DRE'])
    # ---------------- água fria (AF potável, RU reúso, AL alimentação/barrilete)
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_AF_trechos.csv')):
        sis = r['sistema']
        de = float(r['diam'].split()[-1]) / 1000 if r['diam'].startswith('DN') else DE_AF_PADRAO[sis]
        E.append(pressao(f'AF:{r["trecho"]}', 'AF', f'AF-{sis}', r['trecho'], af_desviado(r['trecho'], pts_csv(r['vertices_UTM'])), de, ter,
                         sub=r['descricao'], DN_mm=round(de * 1000), material=r['material'] or 'PVC (premissa)',
                         obs=r['obs'] + ('' if r['diam'] else f' | sem rótulo: DE {de * 1000:.0f} mm (premissa)')))
    # ---------------- incêndio: hidrantes (HI) e SDAI (SD)
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_PCI_trechos.csv')):
        P2 = pts_csv(r['vertices_UTM'])
        if r['sistema'] == 'HI':
            de = DE_PEAD.get(r['diam'], 0.075)
            E.append(pressao(f'HID:{r["trecho"]}', 'HID', 'HID', r['trecho'], P2, de, ter, material='PEAD', DN_mm=r['diam'] or '2.1/2" (premissa)', obs=r['obs']))
        else:
            E.append(pressao(f'SDAI:{r["trecho"]}', 'SDAI', 'SDAI', r['trecho'], P2, DE_ELE['1"'], ter,
                             material='eletroduto (Ø1" premissa)', sub=r['obs'], obs='Ø não rotulado no IC-001: 1" (premissa)'))
    sdai = [e for e in E if e['disc'] == 'SDAI']
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_PCI_nos.csv')):
        if r['sistema'] != 'SD':
            continue
        Ex, Nx = float(r['E']), float(r['N']); zt = float(ter.z([[Ex, Nx]])[0])
        zs = [p[2] - e['de'] / 2 for e in sdai for p in e['pts'] if np.hypot(p[0] - Ex, p[1] - Nx) < 1.0]
        C.append(md.caixa(f'SDAI:{r["no"]}', 'SDAI', 'SDAI', 'q', Ex, Nx, 0.20 + 0.05, (min(zs) if zs else zt - 0.6) - 0.15, zt,
                          nome=r['no'], tipo='caixa de passagem SDAI (0,40 premissa)', cota='topo no terreno; fundo 0,15 m abaixo do eletroduto'))
    # ---------------- elétrica: um eletroduto por circuito; bancos lado a lado
    rows = lt.ler_csv(os.path.join(REL, 'PJC_fase2_ELE_trechos.csv'))
    banco = collections.defaultdict(list)
    for r in rows:
        n = int(r['diam'].split('x')[0]) if 'x' in r['diam'] else 1
        d = r['diam'].split('x')[-1] if r['diam'] else '1"'
        for k in range(n):
            banco[(r['prancha'], frozenset((r['de'], r['para'])))].append((r, d, k, n))
    for (prancha, _), itens in banco.items():
        itens.sort(key=lambda t: (t[0]['circuito'], t[2]))
        des = [DE_ELE.get(d, 0.0334) for r, d, k, n in itens]
        passo = max(des) + 0.05
        for j, ((r, d, k, n), de) in enumerate(zip(itens, des)):
            off = (j - (len(itens) - 1) / 2) * passo
            R0 = np.array(pts_csv(r['vertices_UTM']))
            bk = BANCOS.get((prancha, frozenset((r['de'], r['para']))))
            if bk:                                   # banco inteiro deslocado: mesma rota para todos os circuitos
                ini, dd = bk
                R0 = deslocar_rota(R0, dd) if r['de'] == ini else deslocar_rota(R0[::-1], dd)[::-1]
            P2 = offset(R0, off)
            rede = 'ELE-EL1' if prancha == 'EL-001' else 'ELE-EL2'
            tr = r['trecho'] + (f'.{k + 1}' if n > 1 else '')
            E.append(pressao(f'ELE:{tr}', 'ELE', rede, tr, P2, de, ter, sub=f"{prancha} {r['circuito']}", DN_mm=d,
                             material='eletroduto PVC rígido (DE da tabela RNC 40)',
                             obs='; '.join(x for x in (r['fonte_diam'], r['obs'], 'sem rótulo: 1" (premissa)' if not r['diam'] else '',
                                                       f'banco: {len(itens)} eletrodutos lado a lado' if len(itens) > 1 else '') if x)))
    ele = [e for e in E if e['disc'] == 'ELE']
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_ELE_caixas.csv')):
        Ex, Nx, lado = float(r['E']), float(r['N']), float(r['lado_desenhado_m'])
        rede = 'ELE-EL1' if r['prancha'] == 'EL1' else 'ELE-EL2'
        zt = float(ter.z([[Ex, Nx]])[0])
        zs = [p[2] - e['de'] / 2 for e in ele if e['rede'] == rede for p in e['pts'] if np.hypot(p[0] - Ex, p[1] - Nx) < max(1.0, lado)]
        C.append(md.caixa(f'{rede}:{r["caixa"]}', 'ELE', rede, 'q', Ex, Nx, lado / 2 + 0.05, (min(zs) if zs else zt - 0.6) - 0.15, zt,
                          nome=r['caixa'], tipo=r['rotulo'] or f'caixa {lado:.2f}', cota='topo no terreno; fundo 0,15 m abaixo do eletroduto mais baixo'))
    # ---------------- elétrica do campo society (CPS EL-001 R01): PEAD flexível Ø1", caixas 30x30
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_CPS_ELE_trechos.csv')):
        E.append(pressao(f'ELE:{r["trecho"]}', 'ELE', 'ELE-CPS', r['trecho'], pts_csv(r['vertices_UTM']), DE_ELE['1"'], ter,
                         sub=f'CPS EL-001 circuitos {r["circuitos"]}', DN_mm='1"', material='eletroduto PEAD flexível (CPS EL-001 R01)',
                         obs=f'{r["de"]} -> {r["para"]}; traçado reto caixa a caixa (marcas de fiação da prancha)'))
    cps_ele = [e for e in E if e['rede'] == 'ELE-CPS']
    for r in lt.ler_csv(os.path.join(REL, 'PJC_fase2_CPS_ELE_caixas.csv')):
        Ex, Nx = float(r['E']), float(r['N']); zt = float(ter.z([[Ex, Nx]])[0])
        zs = [p[2] - e['de'] / 2 for e in cps_ele for p in e['pts'] if np.hypot(p[0] - Ex, p[1] - Nx) < 1.0]
        C.append(md.caixa(f'ELE-CPS:{r["caixa"]}', 'ELE', 'ELE-CPS', 'q', Ex, Nx, float(r['lado_m']) / 2 + 0.05, (min(zs) if zs else zt - 0.6) - 0.15, zt,
                          nome=r['caixa'], tipo=r['rotulo'], cota='topo no terreno; fundo 0,15 m abaixo do eletroduto'))
    # ---------------- equipamentos (postes, quadros, reservatórios, recalque, abrigo, extintores)
    for r in lt.ler_csv(os.path.join(REL, 'PJC_equipamentos.csv')):
        Ex, Nx = float(r['E']), float(r['N'])
        z0 = float(ter.z([[Ex, Nx]])[0]) if r['z_ref'] == 'terreno' else float(r['z_ref'])
        zb, zt = z0 + float(r['zb_rel']), z0 + float(r['zt_rel'])
        info = dict(nome=r['id'], tipo=r['tipo'], cota=('relativa ao terreno do IMP' if r['z_ref'] == 'terreno' else f'base na cota {z0:.2f}'),
                    fonte=r['fonte'], premissa=r['premissa'], equipamento=True)
        info.update(next(({'classe_ifc': k, 'pred': p} for chave, k, p in CLASSE_EQ if chave in r['tipo'].lower()), {}))
        if r['forma'] == 'c':
            C.append(md.caixa(f'EQ:{r["id"]}', r['disc'], r['rede'], 'c', Ex, Nx, float(r['lx']) / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f'EQ:{r["id"]}', r['disc'], r['rede'], Ex, Nx, float(r['lx']), float(r['ly']),
                                         math.radians(float(r['rot_graus'])), zb, zt, **info))
    # ---------------- caixas deslocadas em planta (decisão pequena de 19/10): a caixa anda e as pontas dos eletrodutos acompanham
    for cid, (dx, dy) in CAIXAS_MOVIDAS.items():
        c = next(c for c in C if c['id'] == cid)
        for p in (q for q in C if cid.endswith(':base') and q['id'] == cid[:-5]):   # o poste acompanha a base
            p['E'] += dx; p['N'] += dy
        for e in E:
            if e['rede'] != c['rede']:
                continue
            for k in (0, -1):
                if np.hypot(e['pts'][k, 0] - c['E'], e['pts'][k, 1] - c['N']) < c['meia'] + 0.60:     # pontas do banco (lado a lado) também
                    e['pts'][k, 0] += dx; e['pts'][k, 1] += dy
                    e['info']['obs'] = (e['info'].get('obs', '') + f' | ponta acompanha a caixa {c["info"]["nome"]} deslocada').strip(' |')
        c['E'] += dx; c['N'] += dy
        z = float(ter.z([[c['E'], c['N']]])[0]); c['zb'] += z - c['zt']; c['zt'] = z
        c['info']['obs'] = f'deslocada {np.hypot(dx, dy):.2f} m em planta (decisão de 19/10)'
    # ---------------- estrutura as built (blocos, pedestais, sapatas, baldrames, arranques) só perto das redes (1,5 m)
    from shapely.geometry import LineString, Polygon
    from shapely.strtree import STRtree
    zona = [LineString(e['pts'][:, :2]).buffer(e['de'] / 2 + 1.5) for e in E if len(e['pts']) > 1]
    zona += [Point2(c['E'], c['N']).buffer(c['meia'] + 1.5) for c in C if not c['info'].get('equipamento')]
    arv = STRtree(zona); n_est = 0
    for r in lt.ler_csv(os.path.join(REL, 'PJC_estrutura_asbuilt.csv')):
        a = math.radians(float(r['rot_graus'])); hx, hy = float(r['lx']) / 2, float(r['ly']) / 2
        cs, sn = math.cos(a), math.sin(a); Ex, Nx = float(r['E']), float(r['N'])
        pg = Polygon([(Ex + u * cs - v * sn, Nx + u * sn + v * cs) for u, v in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))])
        if not any(zona[q].intersects(pg) for q in arv.query(pg)):
            continue
        C.append(md.caixa_retangular(f'EST:{r["id"]}', 'EST', f'EST-{r["bloco"]}', Ex, Nx, 2 * hx, 2 * hy, a, float(r['zb']), float(r['zt']),
                                     nome=r['id'], tipo=f'{r["categoria"]} ({r["tipo"]})', bloco=r['bloco'], fonte=r['arquivo'],
                                     cota='as built (RVT de estrutura posicionado pelo vínculo do IMP)'))
        n_est += 1
    cenarios = {
        'A': {'nome': 'drenagem do campo pelo CPS R01 (recomendada)', 'excluir': lambda e: e.get('campo_dre001', False)},
        # 'B' (como desenhado, DRE-001 e CPS no campo) deu clash idêntico ao A nas 3 rodadas de 18-19/10: saiu para a rodada caber na noite
    }
    return {'elementos': E, 'caixas': C, 'terreno': ter, 'cenarios': cenarios}
