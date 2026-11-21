# -*- coding: utf-8 -*-
"""Adaptador da ETIB Aporá Itamira (ITA) — fluxo novo (22/10/2026, o mesmo da Olindina, Sátiro e Alagoinhas).
A versão de 19/10 (cenário de entrega AD com a ELE-06 proposta) está em itamira_2026-10-19.py.
Fontes (só leitura): ETIB-APORA-ITAMIRA/RELATORIOS/PRECLASH_INSUMOS_2026-10-18:
  - ITA_asbuilt_campo_trechos.csv / ITA_asbuilt_campo_caixas.csv: drenagem e eletrodutos do campo JÁ EXECUTADOS, lidos do IFC as
    built do IMP (24-049-APR-ITA-ETIB-IMP-PE-001-MOD-R00.ifc, coordenadas = UTM). Ficam fixos (situacao = executado);
  - ITA_ELE_trechos.csv / ITA_ELE_caixas.csv: EL-001-ELG-R00 da implantação georreferenciada (ELE-01..05, CX-01, CX-02) e a
    ELE-06 proposta em 19/10 (CX-02 -> muros NE/SE do campo -> QD1 executado), que só entra no cenário A;
  - ITA_equipamentos.csv: postes, quadros, gerador, ralos, reservatório e base (as built).
Decisões (fichas <link privado da página>, respondidas pelo Anderson em 24/10/2026):
  - I1 "Revise o EL-001": entrega = cenário AD, a ELE-06 (CX-02 -> muros NE/SE do campo -> QD1 executado) no lugar de ELE-04/05,
    que passavam sob o reservatório executado; sai a EL-001 R01 (itamira/exe/ita_el_r01.py). O cenário B (R00 como está) fica;
  - I2 drenagem = a executada (IFC as built), com a DRE-001 R01 redesenhada por ela (23/10);
  - só há projeto de DRE e ELE na implantação (AF, ESG e PCI no pedido à construtora). O campo não tem rede de incêndio enterrada.
Padrão: estudo de cota da elétrica por trecho entre caixas (topo 0,70 m, NBR 5410; o EL-001 não informa), profundidade máxima
2,00 m, sem mergulho pontual, conexões 45°/90°, eletroduto PVC corrugado flexível (legenda do EL-001) curvando até 30° no tubo.
Rede externa: os quadros QGBT e QD-BOMB ficam na ponta desenhada do EL-001 (o IMP traz a escola só como uma massa aproximada, que
cobre também o reservatório; não serve de face)."""
import os
import math
from preclash import leitura as lt
from preclash import modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Aporá Itamira'
SIGLA = 'ITA'
BASE = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA'
INS = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_INSUMOS_2026-10-18')
SAIDA = os.environ.get('ITA_SAIDA') or os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-24')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'itamira_terreno.npz')
ORIGEM = (584400.0, 8704300.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (584330.0, 8704195.0, 584455.0, 8704320.0)
COB_ELE = 0.70

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE'],                       # só a elétrica da implantação muda de cota; o executado fica fixo
    'prof_max_topo': {'ELE': 2.00},
    'dz_max': {'ELE': 2.00},
    'estudo': {
        'por_rede': [],
        'por_trecho': ['ELE'],
        'cob_min': {'ELE': COB_ELE},
        'prof_max': 2.00,
        'passo': 0.05,
        'acima': [],
        'fixar_perto_de': [], 'raio_fixo': 3.0,
    },
    'mergulho_local': False,
    'caixas_moveis_grav': [],
    'desloc_max_grav': 0.60,
    'contornos': False,
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0}},
    'estrutura': ['EST'],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'                # decisão I1 do Anderson (24/10/2026, "Revise o EL-001"): ELE-06 até o QD1, EL-001 R01
CENARIO_PROJETO = 'B'
DISCIPLINAS_ENTREGA = {'HIDRO': ('DRE', 'AF'), 'ELE': ('ELE',)}
NOMES_DISC = {'DRE': 'Drenagem do campo (executada)', 'ELE': 'Elétrica enterrada (implantação e campo)',
              'AF': 'Reservatório existente'}
EXIST = 'AS BUILT CAMPO'          # uma rede só para o executado: ele não se testa contra ele mesmo
MAT_AB = {'dreno': 'Tubo PVC corrugado perfurado para drenagem', 'tubo_liso': 'Tubo PVC liso',
          'calha': 'Calha semicircular de concreto', 'eletroduto': 'Eletroduto PVC corrugado flexível'}
MOTIVO_PONTA = {'ELE': 'chegada no quadro (QGBT, QD-BOMB ou QD1) ou poste do campo',
                'DRE': 'saída livre da drenagem do campo (deságue a confirmar) ou ralo'}


def _existentes(ter):
    """executado do IFC as built: planta e cota dos tubos como estão; a tampa das caixas e dos ralos vai para o terreno acabado
    (o as built as põe em cotas de nível genéricas, 238,00/238,03/237,60, e não no piso), com o fundo mantido."""
    E, C = [], []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_asbuilt_campo_trechos.csv')):
        cat = r['categoria']
        disc = 'ELE' if cat == 'eletroduto' else 'DRE'
        tipo = 'pressao' if disc == 'ELE' else 'gravidade'
        P = [(lt.fl(r['E_ini']), lt.fl(r['N_ini']), lt.fl(r['eixo_ini'])), (lt.fl(r['E_fim']), lt.fl(r['N_fim']), lt.fl(r['eixo_fim']))]
        extra = {}
        if disc == 'ELE':      # recobrimento real do executado (B10): menor distância do topo do eletroduto ao terreno acabado
            de = lt.fl(r['DE_m']); zt = ter.z([[p[0], p[1]] for p in P])
            extra['recobrimento_estudo'] = round(float(min(z - (p[2] + de / 2) for z, p in zip(zt, P))), 2)
        e = md.elemento(f"AB:{r['id']}", disc, EXIST, f"AB-{r['id']}", tipo, lt.fl(r['DE_m']), P, movel=False,
                        material=MAT_AB[cat], DN_mm=round(lt.fl(r['DE_m']) * 1000), situacao='executado', cota='as built (IFC do IMP)')
        if extra: e['estudo'] = {'cob': extra['recobrimento_estudo'], 'grupo': 'as built'}
        E.append(e)
    for r in lt.ler_csv(os.path.join(INS, 'ITA_asbuilt_campo_caixas.csv')):
        disc = 'DRE' if r['tipo'] == 'CA' else 'ELE'
        zt = float(ter.z([[lt.fl(r['E']), lt.fl(r['N'])]])[0])
        C.append(md.caixa(f"AB:{r['caixa']}", disc, EXIST, 'q', lt.fl(r['E']), lt.fl(r['N']), lt.fl(r['meia_m']), lt.fl(r['zb']), zt,
                          nome=r['caixa'], tipo='caixa de areia' if disc == 'DRE' else 'caixa de passagem do campo', situacao='executado',
                          cota='posição e fundo do as built; tampa no piso acabado'))
    return E, C


def _ele(ter):
    E = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_ELE_trechos.csv')):
        pts = [tuple(float(v) for v in xy.split(',')) for xy in r['vertices_UTM'].split()]
        de = lt.fl(r['DE_mm']) / 1000.0
        # a ELE-06 muda de direção dentro das caixas CX-P1..P3: um trecho entre caixas, cada um no seu estudo de cota (24/10/2026)
        partes = [(r['trecho'], pts)] if len(pts) == 2 else [(f"{r['trecho']}.{i + 1}", [pts[i], pts[i + 1]]) for i in range(len(pts) - 1)]
        for tr, pp in partes:
            P = lt.perfil_por_recobrimento(pp, de, COB_ELE, ter)
            E.append(md.elemento(f"ELE:{tr}", 'ELE', 'ELE', tr, 'pressao', de, P, cob_min=COB_ELE,
                                 circuito=r['circuito'], diametro=r['diam_pol'], material='Eletroduto PVC corrugado flexível',
                                 DN_mm=round(de * 1000), situacao='novo', cota=f'topo a {COB_ELE:.2f} m do terreno (NBR 5410)'))
    C = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_ELE_caixas.csv')):
        x, y = lt.fl(r['E']), lt.fl(r['N']); zt = float(ter.z([[x, y]])[0])
        zs = [p[2] - e['de'] / 2 for e in E for p in e['pts'] if ((p[0] - x) ** 2 + (p[1] - y) ** 2) ** 0.5 < 1.2]
        zb = (min(zs) if zs else zt - COB_ELE - 0.06) - 0.15
        tipo = 'caixa de passagem 80x80' if '80' in r['tipo'] else 'caixa de passagem 60x60'
        C.append(md.caixa(f"ELE:{r['caixa']}", 'ELE', 'ELE', 'q', x, y, lt.fl(r['lado_m']) / 2, zb, zt, nome=r['caixa'], tipo=tipo,
                          situacao='novo', cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto mais baixo'))
    return E, C


def _equipamentos(ter):
    C = []
    for r in lt.ler_csv(os.path.join(INS, 'ITA_equipamentos.csv')):
        E, N, lx, ly, zb, zt = (lt.fl(r[k]) for k in ('E', 'N', 'lx', 'ly', 'zb', 'zt'))
        z0 = float(ter.z([[E, N]])[0])
        if r['classe_ifc'] == 'IfcWasteTerminal': zt, zb = z0, z0 - (zt - zb)      # ralo: grelha no piso acabado
        if r['classe_ifc'] == 'IfcLightFixture': zb = z0                           # poste: nasce no piso (sem fundação no as built)
        if r['id'] == 'RESERVATORIO-BASE': continue        # plataforma (envelope de vértices da família, premissa): não é rede nem caixa
        info = dict(nome=r['id'], tipo=r['tipo'], equipamento='sim', classe_ifc=r['classe_ifc'], pred=r['pred'], situacao='executado',
                    cota='as built (IFC do IMP)' if 'IFC' in r['origem'] else 'na ponta do eletroduto do EL-001')
        if r['forma'] == 'c':
            C.append(md.caixa(f"EQ:{r['id']}", r['disciplina'], EXIST, 'c', E, N, lx / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f"EQ:{r['id']}", r['disciplina'], EXIST, E, N, lx, ly, math.radians(lt.fl(r['rot_graus'])), zb, zt, **info))
    return C


def _executado_fixo():
    """o executado (as built) não passa pelo estudo de cota: fica na cota do IFC as built e só serve de obstáculo."""
    from preclash import estudo as _est
    if getattr(_est, '_ita', False): return
    f0 = _est.fixos_internos

    def fixos_internos(E, caixas, cfg):
        return set(f0(E, caixas, cfg)) | {e['id'] for e in E if e['info'].get('situacao') == 'executado'}
    # ELE-01 e ELE-02 saem juntos do QGBT, lado a lado a 0,20 m (mesma vala): eletroduto da mesma disciplina não é obstáculo no
    # estudo, senão um deles desce 0,20 m sem motivo (mesmo ajuste da Olindina)
    _custo = _est.custo

    def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
        if len(outros[0]):
            m = outros[3] != disc; outros = tuple(x[m] for x in outros)
        return _custo(cand, outros, caixas, regras, cfg, disc, futuros, ter)
    _est.custo = custo
    _est.fixos_internos, _est._ita = fixos_internos, True


def _afastar_postes(E, C, folga=0.05):
    """o as built só tem os refletores; o poste (premissa) ia no centro de cada grupo, que cai sobre a calha da borda do campo.
    O poste vai para fora do campo, perpendicular à calha, até ficar 'folga' livre dela (aplicar e avisar: até 1,50 m)."""
    import numpy as np
    calhas = [e for e in E if 'Calha' in e['info'].get('material', '')]
    centro = np.array([584390.0, 8704253.0])
    for c in C:
        if c['info'].get('classe_ifc') != 'IfcLightFixture': continue
        p = np.array([c['E'], c['N']])
        for e in calhas:
            a, b = e['pts'][0, :2], e['pts'][-1, :2]; u = (b - a) / np.linalg.norm(b - a)
            t = np.clip((p - a) @ u, 0, np.linalg.norm(b - a)); q = a + u * t
            d = np.linalg.norm(p - q); lim = e['de'] / 2 + c['meia'] + folga
            if d >= lim: continue
            n = np.array([-u[1], u[0]])
            if n @ (q - centro) < 0: n = -n
            novo = q + n * lim; dl = float(np.linalg.norm(novo - p))
            if dl > 1.50: print(f"  {c['info']['nome']}: precisaria andar {dl:.2f} m, fica"); continue
            c.setdefault('E0', c['E']); c.setdefault('N0', c['N']); c['E'], c['N'] = float(novo[0]), float(novo[1]); p = novo
            c['info']['cota'] = f"poste junto da calha da borda do campo (centro do grupo de refletores a {dl:.2f} m)"
            print(f"  {c['info']['nome']}: {dl:.2f} m para fora da calha")


def _costurar_executado(E, tol=0.30):
    """o IFC as built traz os tubos do campo parados na face das conexões (joelho, junção, ~0,21 m de vão), e as conexões do as
    built não entram no modelo: as pontas executadas a menos de 'tol' umas das outras vão para o ponto médio, para a rede ficar
    contínua e a conexão comercial sair no nó."""
    import numpy as np
    ex = [e for e in E if e['info'].get('situacao') == 'executado']
    pontas = [(e, k) for e in ex for k in (0, -1)]
    feito = set()
    n = 0
    for i, (e, k) in enumerate(pontas):
        if (id(e), k) in feito: continue
        grupo = [(e, k)] + [(f, j) for f, j in pontas[i + 1:] if f is not e and f['disc'] == e['disc'] and (id(f), j) not in feito
                            and np.linalg.norm(f['pts'][j, :2] - e['pts'][k, :2]) < tol]
        if len(grupo) < 2: continue
        m = np.mean([g['pts'][j] for g, j in grupo], axis=0)
        for g, j in grupo:
            g['pts'] = g['pts'].copy(); g['pts'][j] = m; g['pts_sol'] = g['pts'].copy(); g.pop('S', None); feito.add((id(g), j))
        n += 1
    print(f'  executado: {n} nós do campo costurados (vão ou sobreposição nas conexões do as built)')


def _entrar_na_caixa(E, C, raio=0.60):
    """no EL-001 o ELE-01, o ELE-02 e o ELE-03 param a ~0,45 m do centro da CX-02 (o símbolo da caixa está fora do vértice): a ponta
    é prolongada na própria direção até ficar dentro da caixa. A planta do trecho não muda (a prancha fica como está)."""
    import numpy as np
    cx = [c for c in C if c['disc'] == 'ELE' and not c['info'].get('equipamento') and c['info'].get('situacao') == 'novo']
    for e in E:
        if e['disc'] != 'ELE' or e['info'].get('situacao') == 'executado': continue
        for k, k2 in ((0, 1), (-1, -2)):
            p, q = e['pts'][k], e['pts'][k2]
            for c in cx:
                d = np.hypot(p[0] - c['E'], p[1] - c['N'])
                if not (c['meia'] - 0.05 < d < raio): continue
                u = (p[:2] - q[:2]) / np.linalg.norm(p[:2] - q[:2])
                t = (np.array([c['E'], c['N']]) - p[:2]) @ u
                if t <= 0: continue
                e['pts'] = e['pts'].copy(); e['pts'][k, :2] = p[:2] + u * t; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
                print(f"  {e['trecho']}: ponta prolongada {t:.2f} m até dentro da {c['info']['nome']}")


VERIFICACAO_ESPERADA = {}


def _esperada():
    import csv
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_{CENARIO_ENTREGA}_verificacao.csv')
    if not os.path.exists(fn): return
    for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
        if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: VERIFICACAO_ESPERADA[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]


_esperada()


def carregar():
    _executado_fixo()
    ter = Terreno(TERRENO)
    eX, cX = _existentes(ter)
    _costurar_executado(eX)
    cX = cX + _equipamentos(ter)
    _afastar_postes(eX, cX)
    eE, cE = _ele(ter)
    _entrar_na_caixa(eE, cE)
    velhos = ('ELE-04', 'ELE-05'); novos = ('ELE-06',)
    eA = eX + [e for e in eE if e['trecho'] not in velhos]
    cA = cX + [c for c in cE if c['info']['nome'] != 'CX-01']
    eB = eX + [e for e in eE if not e['trecho'].startswith(novos)]
    cB = cX + [c for c in cE if not c['info']['nome'].startswith('CX-P')]
    nada = lambda e: False
    cenarios = {
        'B': {'nome': 'EL-001 R00 como está; campo executado (entrega)', 'excluir': nada, 'elementos': eB, 'caixas': cB},
        'A': {'nome': 'alternativa: alimentação nova do QD1 (ELE-06) no lugar de ELE-04/05', 'excluir': nada, 'elementos': eA, 'caixas': cA},
    }
    return {'elementos': eB, 'caixas': cB, 'terreno': ter, 'cenarios': cenarios}
