# -*- coding: utf-8 -*-
"""Adaptador da ETIB Aporá Prof. Áurea (AUR) — fluxo novo (23/10/2026, o mesmo da Itamira, Olindina e Sátiro).
A versão de 18/10 (terreno provisório SIT + platô, cenários A/B/C) está em apora_aurea_2026-10-18.py.
Escopo (Anderson, 23/10/2026): só as disciplinas cujos projetos estão na pasta da escola: drenagem pluvial (AF-002-HIG R00, que é
a drenagem da quadra), elétrica (EL-001-ELG R00) e incêndio (IN-001-ING R00: 5 m de hidrante e o laço do alarme). A pasta "10 -
QUADRA" do Drive (baixada em 23/10) é o projeto padrão da quadra (drenagem igual à do AF-002, elétrica e incêndio internos): entra só
a fundação (sapatas pré-moldadas) como estrutura.
Drenagem: a da quadra JÁ ESTÁ EXECUTADA e vem do IFC as built do IMP (FERRAMENTAS/aurea/ifc/aur_asbuilt.py: 10 caixas de areia,
coletores e ramais das descidas), fixa e como está no as built (mesmo critério da Itamira, decisão I2). As caixas executadas estão de
0,4 a 3,5 m das do AF-002 (as do lado leste a 2,1 m dos pilares, como no projeto padrão da quadra): o AF-002 não é redesenhado e a
divergência vai declarada. Do AF-002 entra só o que liga a quadra à rede (novo): CA-04 -> PVP-01, CA-10 -> PVP-02, PVP-02 -> PVP-01,
PVP-01 a PVP-06 e o lançamento, com a CT 188,00 a leste (decisão A3: CA-06 a CA-10 com CT 190,00 e PVP-01/02 com 189,00 contra o
platô 188,00; mesma profundidade de cada caixa). Canaletas e ralos da quadra são do piso da quadra (dentro) e não entram.
Fontes (só leitura): ETIB-APORA-PROF-AUREA/RELATORIOS/GEORREF_E_REDES_2026-10-18 (fases 2 e 3 de 18/10):
  - revit/dre_tubos_B.csv + revit/dre_caixas_B.csv (AF-002 com a CT 188); ele_trechos.csv / ele_nos.csv (QDLT-QUA Ø1" e QDLT-BOMB
    Ø2" do QGBT existente, 7 caixas 80x80); pci_trechos.csv (hidrante 2½" PEAD e laço L01); revit/equipamentos.csv (quadros e
    interligação com a rede geral).
Terreno (decisão A2): IMP as built ajustado à base (aurea/ifc/aur_terreno_imp.py): o IMP foi posto na posição da quadra da SIT e
1,00 m abaixo (platô 189,00 no IMP x 188,00 na TER, no TOP e nas CT da drenagem); fora do IMP, TOP-001.
Estrutura: 14 sapatas SP-01 (QDC-FUN-001/002 R01) nos pilares do IMP (aurea/ifc/aur_estrutura.py), forma real (tronco de pirâmide).
Padrão: estudo de cota das pressurizadas (hidrante uma cota por rede; elétrica e alarme por trecho entre caixas, sempre acima da
água), sem mergulho pontual, profundidade máxima 2,00 m, conexões 45°/90°; eletroduto da elétrica e do alarme PEAD corrugado
flexível e hidrante PEAD curvando até 30° no tubo; recobrimento: elétrica 0,70 (NBR 5410, o EL-001 não informa), hidrante e alarme
0,50 (nota do IN-001); caixa nova de drenagem desloca até 0,60 m (aplicar e avisar)."""
import csv, json, math, os
import numpy as np
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Aporá Prof. Áurea'
SIGLA = 'AUR'
BASE = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA'
F = os.path.join(BASE, 'RELATORIOS', 'GEORREF_E_REDES_2026-10-18')
SAIDA = os.environ.get('AUR_SAIDA') or os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-23')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'apora_aurea_terreno_imp_base.npz')
AUR = r'D:\Projeto Modelagem\FERRAMENTAS\aurea\ifc'
ESTRUTURA = os.path.join(AUR, 'aur_estrutura.json')
ORIGEM = (600000.0, 8711300.0, 0.0)       # AGENTS.md
EPSG = 31984
CAIXA_OBRA = (600010.0, 8711225.0, 600110.0, 8711410.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID'],
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00},
    'estudo': {
        'por_rede': ['HID'],
        'por_trecho': ['ELE', 'SDAI'],
        'cob_min': {'HID': 0.50, 'ELE': 0.70, 'SDAI': 0.50},
        'prof_max': 2.00,
        'passo': 0.05,
        'acima': [('ELE', 'HID'), ('SDAI', 'HID')],
        'fixar_perto_de': [], 'raio_fixo': 3.0,
    },
    'mergulho_local': False,
    'caixas_moveis_grav': ['DRE'],
    'desloc_max_grav': 0.60,
    'contornos': False,
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
    'estrutura': ['EST'],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
CENARIO_PROJETO = 'A'
DISCIPLINAS_ENTREGA = {'HIDRO': ('DRE',), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI'), 'EST': ('EST',)}
NOMES_DISC = {'DRE': 'Drenagem pluvial (quadra executada + AF-002)', 'ELE': 'Elétrica enterrada', 'HID': 'Hidrante (PCI)',
              'SDAI': 'Alarme de incêndio (PCI)', 'EST': 'Fundação da quadra (referência)'}
COB = REGRAS['estudo']['cob_min']
MAT_DRE = {'PVCR': 'Tubo PVC Série Reforçada', 'PVC REFORÇADO': 'Tubo PVC Série Reforçada', 'PVC': 'Tubo PVC Série Normal',
           'PVC (rótulo PVC)': 'Tubo PVC Série Normal', 'PVC-V': 'Tubo PVC Vinilfort'}
MAT_ELE = 'Eletroduto PEAD corrugado flexível'
EXEC = 'AS BUILT QUADRA'               # uma rede só para o executado: ele não se testa contra ele mesmo
NOVOS_DRE = ('DRE-065', 'DRE-066', 'DRE-059', 'DRE-064', 'DRE-003', 'DRE-044', 'DRE-063', 'DRE-067')
CAIXAS_NOVAS = ('CA-10', 'PVP-01', 'PVP-02', 'PVP-03', 'PVP-04', 'PVP-05', 'PVP-06')
MOTIVO_PONTA = {'ELE': 'chegada no quadro (QGBT existente, QDLT-QUA ou QDLT-BOMB)',
                'DRE': 'executado: descida da cobertura no pilar ou ponta do as built / lançamento na rede geral existente',
                'HID': 'vem da rede existente (compatibilizar in loco) / sobe para a quadra',
                'SDAI': 'vem das instalações existentes / segue para a quadra'}
APLICADO = []          # soluções do "aplicar e avisar" feitas no carregamento (vão para a página e para o LEIA-ME)
# decisões da página de pendências (Anderson, 24/10/2026): ficha 2 = manter a declividade do DRE-065 e ajustar a caixa: o fundo da
# CA-04 executada (ABC-011, 187,39 no as built) desce até a geratriz de saída do DRE-065 do AF-002 (187,11)
REBAIXAR_EXECUTADA = {'ABC-011': 'DRE-065'}


def _rebaixar_executadas(cX, eN):
    gi = {e['trecho']: e['info']['GI_mont'] for e in eN}
    for c in cX:
        tr = REBAIXAR_EXECUTADA.get(c['info'].get('nome'))
        if not tr: continue
        antes, depois = c['zb'], gi[tr]
        c['zb'] = depois
        c['info']['cota'] = f'posição do as built; fundo rebaixado de {antes:.2f} para {depois:.2f} (saída do {tr}); tampa no terreno acabado'
        APLICADO.append(dict(tipo='fundo de caixa executada rebaixado', caixa=c['info']['nome'], trecho=tr, antes=round(antes, 3),
                             depois=round(depois, 3), dz=round(antes - depois, 3), E=c['E'], N=c['N'], decisao='Anderson, 24/10/2026'))


def _executado(ter):
    """drenagem executada da quadra (IFC as built): planta e cota como estão; sai o trecho de descida acima do piso (é do prédio).
    A tampa das caixas vai para o terreno acabado (o as built as põe todas em 188,00, de 6 a 33 cm acima dele), com o fundo mantido
    (mesmo critério da Itamira)."""
    E, C = [], []
    for r in lt.ler_csv(os.path.join(AUR, 'AUR_asbuilt_trechos.csv')):
        if r['disc'] != 'DRE': continue
        P = [(lt.fl(r['E0']), lt.fl(r['N0']), lt.fl(r['z0'])), (lt.fl(r['E1']), lt.fl(r['N1']), lt.fl(r['z1']))]
        if min(P[0][2], P[1][2]) > 187.95: continue            # descida no pilar, acima do piso
        de = lt.fl(r['de'])
        E.append(md.elemento(f"AB:{r['id']}", 'DRE', EXEC, r['id'], 'gravidade', de, P, movel=False, DN_mm=150,
                             material='Tubo PVC Série Reforçada', situacao='executado', guid=r['guid'], cota='as built (IFC do IMP)'))
    for r in lt.ler_csv(os.path.join(AUR, 'AUR_asbuilt_caixas.csv')):
        if r['disc'] != 'DRE': continue
        C.append(md.caixa_retangular(f"AB:{r['id']}", 'DRE', EXEC, lt.fl(r['E']), lt.fl(r['N']), lt.fl(r['lx']), lt.fl(r['ly']),
                                     math.radians(lt.fl(r['rot_graus'])), lt.fl(r['zb']), float(ter.z([[lt.fl(r['E']), lt.fl(r['N'])]])[0]),
                                     nome=r['id'], tipo='caixa de areia (executada)', situacao='executado', guid=r['guid'],
                                     cota='posição e fundo do as built (IFC do IMP); tampa no terreno acabado'))
    return E, C


def _nomear_executado(C, caixas_af):
    """dá às caixas executadas o nome da caixa do AF-002 mais perto (CA-01 a CA-10), para a página e o relatório."""
    for c in C:
        if c['info'].get('situacao') != 'executado': continue
        d, nome = min((math.hypot(c['E'] - x, c['N'] - y), n) for n, (x, y) in caixas_af.items())
        c['info']['nome'] = f"{nome} (executada)"; c['info']['afastamento_AF002'] = round(d, 2)


def _drenagem_nova(ter):
    """AF-002 com a CT 188,00 a leste (A3): só a ligação da quadra à rede. Trecho que chega abaixo do fundo da caixa de jusante: a
    geratriz de chegada sobe até o fundo (aplicar e avisar, até 0,20 m), com a declividade em 0,5% ou mais."""
    tubos = lt.ler_csv(os.path.join(F, 'revit', 'dre_tubos_B.csv'))
    caixas = lt.ler_csv(os.path.join(F, 'revit', 'dre_caixas_B.csv'))
    cf = {r['id']: (lt.fl(r['x_utm']), lt.fl(r['y_utm']), lt.fl(r['CF']), lt.fl(r['dimensao_m'])) for r in caixas}
    E = []
    for r in tubos:
        if r['peca'] != 'H' or r['peca_nome'] not in NOVOS_DRE: continue
        dn = lt.fl(r['DN']); de = md.de_gravidade(dn, r['material'])
        gim, gij = lt.fl(r['GI_mont']), lt.fl(r['GI_jus'])
        x0, y0, x1, y1 = (lt.fl(r[k]) for k in ('x0_utm', 'y0_utm', 'x1_utm', 'y1_utm'))
        L = math.hypot(x1 - x0, y1 - y0)
        for nome, (cx, cy, f, dim) in cf.items():
            if math.hypot(x1 - cx, y1 - cy) < dim / 2 + 0.3 and gij < f - 0.005 and f - gij <= 0.20 and (gim - f) / L >= 0.005:
                APLICADO.append(dict(tipo='geratriz de chegada', trecho=r['peca_nome'], caixa=nome, antes=round(gij, 3), depois=round(f, 3),
                                     dz=round(f - gij, 3), i_antes=round((gim - gij) / L * 100, 2), i_depois=round((gim - f) / L * 100, 2),
                                     E=x1, N=y1))
                gij = f
        E.append(md.elemento(f"DRE:{r['peca_nome']}", 'DRE', 'DRE', r['peca_nome'], 'gravidade', de,
                             [(x0, y0, gim + de / 2), (x1, y1, gij + de / 2)], DN_mm=int(dn), material=MAT_DRE.get(r['material'], r['material']),
                             GI_mont=gim, GI_jus=gij, situacao='novo', cota='CT/CF do AF-002 (CT 188,00 a leste, mesma profundidade)'))
    C = []
    for r in caixas:
        if r['id'] not in CAIXAS_NOVAS: continue
        ct, f, dim = lt.fl(r['CT']), lt.fl(r['CF']), lt.fl(r['dimensao_m'])
        forma = 'c' if r['tipo'] == 'PVP' else 'q'
        C.append(md.caixa(f"DRE:{r['id']}", 'DRE', 'DRE', forma, lt.fl(r['x_utm']), lt.fl(r['y_utm']), dim / 2, f - 0.10, ct,
                          nome=r['id'], tipo='caixa de areia 80x80' if r['tipo'] == 'CA' else 'poço de visita pluvial Ø1,00', situacao='novo',
                          cota='CT/CF do AF-002 (CT 188,00 a leste); fundo 0,10 m abaixo da CF'))
    af = {r['id']: (lt.fl(r['x_utm']), lt.fl(r['y_utm'])) for r in caixas if r['tipo'] == 'CA'}
    return E, C, af


def _costurar_executado(E, C, tol=0.40):
    """o IFC as built traz os tubos da quadra parados na face das caixas e das conexões: ponta executada a menos de 'tol' de outra
    ponta executada vai para o ponto médio, e a que fica a menos de 'tol' da face de uma caixa (executada ou nova) entra até a
    parede dela, para a rede ficar contínua. Planta e cota do as built não mudam além disso."""
    ex = [e for e in E if e['info'].get('situacao') == 'executado']
    pontas = [(e, k) for e in ex for k in (0, -1)]
    feito, n = set(), 0
    for i, (e, k) in enumerate(pontas):
        if (id(e), k) in feito: continue
        g = [(e, k)] + [(f, j) for f, j in pontas[i + 1:] if f is not e and (id(f), j) not in feito
                        and np.linalg.norm(f['pts'][j, :2] - e['pts'][k, :2]) < tol]
        if len(g) < 2: continue
        m = np.mean([x['pts'][j] for x, j in g], axis=0)
        for x, j in g:
            x['pts'] = x['pts'].copy(); x['pts'][j] = m; x['pts_sol'] = x['pts'].copy(); feito.add((id(x), j))
        n += 1
    nc = 0
    cxs = [c for c in C if c['disc'] == 'DRE' and not c['info'].get('equipamento')]
    for e in ex:
        for k, k2 in ((0, 1), (-1, -2)):
            if (id(e), k) in feito: continue
            p, q = e['pts'][k], e['pts'][k2]
            for c in cxs:
                dx, dy = md.planta_local(c, p[0], p[1])
                if max(dx, dy) <= 0 or max(dx, dy) > tol: continue
                u = (p[:2] - q[:2]) / (np.linalg.norm(p[:2] - q[:2]) + 1e-9)
                for t in np.arange(0.02, tol + 0.05, 0.02):
                    if max(md.planta_local(c, p[0] + u[0] * t, p[1] + u[1] * t)) <= -0.02: break
                e['pts'] = e['pts'].copy(); e['pts'][k, :2] = p[:2] + u * t; e['pts_sol'] = e['pts'].copy(); nc += 1
                break
    print(f'  executado: {n} nós costurados, {nc} pontas levadas até a parede da caixa')


def _densificar(P, passo=4.0):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(math.ceil(L / passo)))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(1, k + 1)]
    return out


def _ele_pci(ter):
    E, C = [], []
    DE = {'QDLT-QUA': 0.032, 'QDLT-BOMB': 0.063}
    nos = {r['no']: (lt.fl(r['x']), lt.fl(r['y'])) for r in lt.ler_csv(os.path.join(F, 'ele_nos.csv')) if r['no'].startswith('CX')}
    for r in lt.ler_csv(os.path.join(F, 'ele_trechos.csv')):
        a, b = np.array([lt.fl(r['x0']), lt.fl(r['y0'])]), np.array([lt.fl(r['x1']), lt.fl(r['y1'])])
        de = DE[r['circuito']]
        # o trecho da fase 2 passa reto pelas caixas do meio (CX-04 -> CX-03 passa pela CX-02 e pela CX-01): parte em cada caixa,
        # para a cota do estudo mudar só dentro delas
        u = (b - a) / np.linalg.norm(b - a); L = np.linalg.norm(b - a)
        meio = sorted((float((np.array(p) - a) @ u), n) for n, p in nos.items()
                      if 0.6 < (np.array(p) - a) @ u < L - 0.6 and abs(np.cross(u, np.array(p) - a)) < 0.6)
        cortes = [0.0] + [t for t, _ in meio] + [L]
        for k, (t0, t1) in enumerate(zip(cortes[:-1], cortes[1:])):
            nome = r['trecho'] + ('ABCDEFG'[k] if meio else '')
            pts = [tuple(a + u * t0), tuple(a + u * t1)]
            P = lt.perfil_por_recobrimento(_densificar(pts), de, COB['ELE'], ter)
            E.append(md.elemento(f"ELE:{nome}", 'ELE', 'ELE', nome, 'pressao', de, P, cob_min=COB['ELE'], circuito=r['circuito'],
                                 diametro=r['eletroduto'], material=MAT_ELE, DN_mm=round(de * 1000), situacao='novo',
                                 cota=f"topo a {COB['ELE']:.2f} m do terreno (NBR 5410)"))
    ele = list(E)
    for r in lt.ler_csv(os.path.join(F, 'ele_nos.csv')):
        if not r['no'].startswith('CX'): continue
        x, y = lt.fl(r['x']), lt.fl(r['y']); zt = float(ter.z([[x, y]])[0])
        zs = [p[2] - e['de'] / 2 for e in ele for p in e['pts'] if math.hypot(p[0] - x, p[1] - y) < 1.0]
        zb = (min(zs) if zs else zt - COB['ELE'] - 0.07) - 0.15
        C.append(md.caixa(f"ELE:{r['no']}", 'ELE', 'ELE', 'q', x, y, 0.40 + 0.05, zb, zt, nome=r['no'], tipo='caixa de passagem 80x80',
                          situacao='novo', cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto mais baixo'))
    for r in lt.ler_csv(os.path.join(F, 'pci_trechos.csv')):
        pts = [(lt.fl(r['x0']), lt.fl(r['y0'])), (lt.fl(r['x1']), lt.fl(r['y1']))]
        if r['layer'].startswith('HI-'):
            d, tr, de, mat, ob = 'HID', 'HID-01', 0.075, 'Tubo PEAD 2½"', 'vem das instalações existentes (compatibilizar in loco)'
        else:
            d, tr, de, mat, ob = 'SDAI', 'SDAI-L01', 0.063, MAT_ELE, 'laço L01, 24 Vcc'
        P = lt.perfil_por_recobrimento(pts, de, COB[d], ter)
        E.append(md.elemento(f'{d}:{tr}', d, d, tr, 'pressao', de, P, cob_min=COB[d], material=mat, DN_mm=round(de * 1000),
                             situacao='novo', obs=ob, cota=f'topo a {COB[d]:.2f} m do terreno (nota do IN-001)'))
    return E, C


def _equipamentos(ter, elementos):
    """quadros (QGBT existente, QDLT-QUA, QDLT-BOMB) e a interligação com a rede geral existente; as canaletas da quadra não entram."""
    C = []
    for r in lt.ler_csv(os.path.join(F, 'revit', 'equipamentos.csv')):
        if r['tipo'].startswith('canaleta'): continue
        x, y = lt.fl(r['E']), lt.fl(r['N']); zter = float(ter.z([[x, y]])[0])

        def cota(v, ref):
            if ref == 'ter': return zter + v
            if ref == 'eixo':
                zs = [p[2] for e in elementos if e['disc'] == r['disc'] for p in e['pts'] if math.hypot(p[0] - x, p[1] - y) < 1.5]
                return (min(zs) if zs else zter - 1.5) - v
            return v
        zb, zt = cota(lt.fl(r['zb']), r['zb_ref']), cota(lt.fl(r['zt']), r['zt_ref'])
        classe = 'IfcElectricDistributionBoard' if r['tipo'] == 'quadro elétrico' else 'IfcWasteTerminal'
        info = dict(nome=r['id'], tipo=r['tipo'], equipamento=True, classe_ifc=classe, obs=r['obs'],
                    situacao='existente' if r['id'] in ('QGBT', 'INTERLIGACAO-REDE-GERAL') else 'novo',
                    cota='no terreno' if 'ter' in (r['zb_ref'], r['zt_ref']) else 'cota absoluta')
        if r['forma'] == 'c':
            C.append(md.caixa(f"{r['disc']}:{r['id']}", r['disc'], r['disc'], 'c', x, y, lt.fl(r['lx']) / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f"{r['disc']}:{r['id']}", r['disc'], r['disc'], x, y, lt.fl(r['lx']), lt.fl(r['ly']),
                                         math.radians(lt.fl(r['rot_graus'])), zb, zt, **info))
    return C


def _tronco(cx, cy, rot, camadas):
    """malha (triângulos UTM) de uma pilha de troncos retangulares: camadas = [(z, meia_x, meia_y), ...] de baixo para cima."""
    u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]])
    anel = lambda z, a, b: [np.array([*(np.array([cx, cy]) + s * a * u + t * b * v), z]) for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    R = [anel(*c) for c in camadas]
    T = [(R[0][0], R[0][2], R[0][1]), (R[0][0], R[0][3], R[0][2]), (R[-1][0], R[-1][1], R[-1][2]), (R[-1][0], R[-1][2], R[-1][3])]
    for A, B in zip(R[:-1], R[1:]):
        for i in range(4):
            j = (i + 1) % 4
            T += [(A[i], A[j], B[j]), (A[i], B[j], B[i])]
    return np.array(T)


def _estrutura():
    """sapatas SP-01 (110 x 130, 1,05 m: placa de 0,20 m, tronco até o pedestal 60 x 75 e pedestal de 0,14 m até o topo do
    concreto bruto, 0,10 m abaixo do piso pronto). O prisma envolvente detecta; a malha (forma real) confirma."""
    C = []
    for p in json.load(open(ESTRUTURA, encoding='utf-8'))['pecas']:
        zb, zt = p['zb'], p['zt']; a, b = p['lx'] / 2, p['ly'] / 2; pa, pb = p['pedestal'][1] / 2, p['pedestal'][0] / 2
        M = _tronco(p['x'], p['y'], p['rot'], [(zb, a, b), (zb + 0.20, a, b), (zt - 0.14, pa, pb), (zt, pa, pb)])
        C.append(md.caixa_retangular(f"EST:{p['nome']}", 'EST', 'EST', p['x'], p['y'], p['lx'], p['ly'], p['rot'], zb, zt,
                                     nome=p['nome'], tipo='sapata SP-01 110x130 (QDC-FUN-002 R01)', equipamento=True, situacao='executado',
                                     classe_ifc='IfcFooting', malha=M, cota='piso da quadra (IMP as built - 1,00 m) - 0,10 m'))
    return C


VERIFICACAO_ESPERADA = {}


def _esperada():
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_{CENARIO_ENTREGA}_verificacao.csv')
    if not os.path.exists(fn): return
    for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
        if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: VERIFICACAO_ESPERADA[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]


_esperada()


def _patches():
    """(1) elétrica e alarme por cima da água: o trecho vizinho da mesma disciplina não é obstáculo no estudo (mesmo ajuste da
    Olindina e da Itamira); (2) o executado não passa pelo estudo e não se testa contra o que já existe (executado x executado não é
    conflito da compatibilização); (3) caixa executada não anda."""
    from preclash import estudo as _est, clash as _cl, desvio as _dsv
    if getattr(_est, '_aur', False): return
    _custo = _est.custo

    def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
        if len(outros[0]):
            m = outros[3] != disc; outros = tuple(x[m] for x in outros)
        return _custo(cand, outros, caixas, regras, cfg, disc, futuros, ter)
    f0 = _est.fixos_internos

    def fixos_internos(E, caixas, cfg):
        return set(f0(E, caixas, cfg)) | {e['id'] for e in E if e['info'].get('situacao') == 'executado'}
    det0 = _cl.detectar
    VELHO = ('executado', 'existente')

    def detectar(elementos, caixas, regras, *a, **k):
        conf = det0(elementos, caixas, regras, *a, **k)
        sit = {x['id']: x['info'].get('situacao') for x in list(elementos) + list(caixas)}
        return [c for c in conf if not (sit.get(c['a']) in VELHO and sit.get(c['b']) in VELHO)]
    mv0 = _dsv.mover_caixas

    def mover_caixas(E, C, pend, regras, log=print, ter=None):
        marc = [c for c in C if c['info'].get('situacao') in VELHO and not c['info'].get('equipamento')]
        for c in marc: c['info']['equipamento'] = True
        try:
            return mv0(E, C, pend, regras, log, ter=ter)
        finally:
            for c in marc: c['info'].pop('equipamento', None)
            # caixa de passagem deslocada: a tampa vai para o terreno do lugar novo (o fundo fica)
            for c in C:
                if 'E0' in c and c['disc'] == 'ELE' and ter is not None: c['zt'] = float(ter.z([[c['E'], c['N']]])[0])
    _est.custo, _est.fixos_internos, _cl.detectar, _dsv.mover_caixas, _est._aur = custo, fixos_internos, detectar, mover_caixas, True


def carregar():
    ter = Terreno(TERRENO)
    APLICADO.clear()
    eX, cX = _executado(ter)
    eN, cN, af = _drenagem_nova(ter)
    _rebaixar_executadas(cX, eN)
    _nomear_executado(cX, af)
    E, C = eX + eN, cX + cN
    _costurar_executado(E, C)
    eP, cP = _ele_pci(ter)
    E += eP; C += cP
    C += _equipamentos(ter, E)
    C += _estrutura()
    _patches()
    os.makedirs(SAIDA, exist_ok=True)
    json.dump(APLICADO, open(os.path.join(SAIDA, 'AUR_aplicado_carregamento.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'quadra executada (as built) + ligação do AF-002 com CT 188 a leste; estudo de cota da elétrica e do PCI',
                               'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py, via aurea/exe/aur_exec.py): pranchas no padrão de executivo final
REVISAO = 'R01'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.30
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.60)
_PO = 'PROJETO_ORIGINAL/IMP/'
_DWG = {'AF-002': _PO + '03_DRE/24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R00.dwg',
        'EL-001': _PO + '04_ELE/24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg',
        'IN-001': _PO + '05_PCI/24-049-APR-CTO-ETIB-IMP-PE-IN-001-ING-R00.dwg'}
_FOLHAS = {'DRE': ['AF-002'], 'ELE': ['EL-001'], 'HID': ['IN-001'], 'SDAI': ['IN-001']}


def folhas(m):
    return _FOLHAS.get(m['disc'], [])


def folha(m):
    return (folhas(m) or [None])[0]


def executivo_dwg(m):
    return _DWG.get(m.get('folha') or folha(m))


def _transf(nome):
    j = json.load(open(os.path.join(BASE, 'CAD_GEORREFERENCIADO', nome), encoding='utf-8'))
    return (float(j['rotacao_graus']), tuple(j['translacao']))


TRANSF_DWG = {_DWG['AF-002']: _transf('transformacao_DRE_local_para_UTM.json'),
              _DWG['EL-001']: _transf('transformacao_ELE_local_para_UTM.json'),
              _DWG['IN-001']: _transf('transformacao_PCI_local_para_UTM.json')}
