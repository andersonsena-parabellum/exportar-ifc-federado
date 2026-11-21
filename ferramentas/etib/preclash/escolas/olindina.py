# -*- coding: utf-8 -*-
"""Adaptador da ETIB Olindina (ONN) — fluxo novo (21/10/2026, o mesmo da Jandaíra, Alagoinhas e Sátiro Dias).
O projeto da Olindina é a ampliação do bloco BA5 (5 salas) e a ligação dele às redes existentes da escola: as pranchas R00
(AF-001, ESG-001 = DRE-001, EL-001, IN-001) desenham as redes novas e, como cadastro, as redes existentes onde elas se ligam.
Redes extraídas em olindina/rede/onn_fase2.py (RELATORIOS/FASE2_REDES_2026-10-21). Padrão aplicado:
  - só rede externa (Anderson, 21/10/2026): a rede é cortada na face do BA5 (contorno pela estrutura as built) e o que fica dentro sai;
  - redes existentes (cadastro da prancha) entram como obstáculo e no IFC com 'situacao' = existente; as caixas existentes não andam;
  - pressurizadas (AF, HID, ELE): estudo de cota (água uma por rede; elétrica uma por trecho entre caixas, sempre acima da água),
    sem mergulho pontual; profundidade máxima 2,00 m (terreno ao topo). A AF nova é um ramal de 2,9 m da rede existente PVC 60 mm:
    a existente não tem cota no cadastro e não entra no modelo;
  - gravidade (pluvial, esgoto): cotas das pranchas; gravidade × gravidade desloca a caixa nova até 0,60 m (cenário AD);
  - conexões comerciais 45°/90°; eletroduto (PVC corrugado flexível, legenda do EL-001) e hidrante (PEAD, legenda do IN-001)
    curvam no tubo até 30°; nenhum vértice anda em planta;
  - material pela legenda das pranchas: pluvial PVC Série Reforçada nos Ø150 ("PVCR") e PVC Série Normal nos Ø200 ("PVC"), drenos
    Ø40 PVC soldável; esgoto PVC Série Normal; AF PVC soldável marrom; ELE eletroduto PVC corrugado flexível Ø3"; hidrante PEAD 2.1/2";
  - recobrimento mínimo: AF 0,30; hidrante 0,50 (nota 5 do IN-001: termoplástico enterrado a 0,50 m); elétrica 0,70 (NBR 5410)."""
import os, sys, csv, json, math
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\ifc')
import numpy as np
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Olindina'
SIGLA = 'ONN'
BASE = r'D:\Projeto Modelagem\ETIB-OLINDINA'
REL = os.path.join(BASE, 'RELATORIOS')
F2 = os.path.join(REL, 'FASE2_REDES_2026-10-21')
SAIDA = os.environ.get('ONN_SAIDA') or os.path.join(REL, 'PRECLASH_2026-10-21')
DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
TER_IMP = os.path.join(DADOS, 'olindina_terreno_imp.npz')                 # IMP as built (quando lido no Revit)
TER_PROV = os.path.join(DADOS, 'olindina_terreno_provisorio.npz')         # cotas da base (olindina_terreno.py)
TERRENO = os.path.join(DADOS, 'olindina_terreno.npz')                     # o do clash e do IFC
ORIGEM = (573950.0, 8743250.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (573870.0, 8743225.0, 573965.0, 8743350.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'estudo': {
        'por_rede': ['AF', 'HID'],
        'por_trecho': ['ELE', 'SDAI'],
        'cob_min': {'AF': 0.30, 'HID': 0.50, 'ELE': 0.70, 'SDAI': 0.50},
        'prof_max': 2.00,
        'passo': 0.05,
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],
        'fixar_perto_de': [], 'raio_fixo': 3.0,
    },
    'mergulho_local': False,
    'caixas_moveis_grav': ['AP', 'ESG'],
    'desloc_max_grav': 0.60,
    'contornos': False,
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
    'estrutura': ['EST'],
    'ligacao_entre': [{'AP', 'DRE'}],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'AP'), 'ELE': ('ELE',), 'PCIP': ('HID',)}
NOMES_DISC = {'AF': 'Água fria', 'ESG': 'Esgoto', 'AP': 'Drenagem pluvial', 'ELE': 'Elétrica enterrada (alimentador do BA5)',
              'HID': 'Hidrantes (PCI)', 'EST': 'Estrutura as built'}
MOTIVO_PONTA = {'ELE': 'chegada na face da edificação (sobe para o quadro)', 'ESG': 'saída de esgoto da edificação (ramal predial) ou rede existente que segue',
                'AP': 'descida pluvial/dreno da edificação ou rede existente que segue', 'AF': 'entrada da edificação ou rede existente que segue',
                'HID': 'ligação à rede existente (in loco) ou entrada da edificação'}
MAT_GRAV = {('AP', 'PVCR'): 'Tubo PVC Série Reforçada', ('AP', 'PVC'): 'Tubo PVC Série Normal', ('ESG', 'PVC'): 'Tubo PVC Série Normal'}


def _esperada():
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_AD_verificacao.csv')
    out = {}
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
            if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: out[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]
            if r['tipo'] == 'pedaço curto' and r['disc'] in ('ELE', 'AP'): out[('pedaço curto', r['trecho'])] = 'trecho curto entre a caixa e a face da edificação'
    return out


VERIFICACAO_ESPERADA = _esperada()


def terreno_base(log=print):
    """IMP as built (quando houver) levado às CT das caixas das pranchas (vale a base); sem o IMP, o provisório das cotas da base."""
    from preclash import terreno as tr
    if not os.path.exists(TER_IMP):
        import shutil; shutil.copy(TER_PROV, TERRENO); log('  terreno: PROVISÓRIO (CT das caixas + cotas de piso da SIT)'); return None
    base = []
    for fn in ('ONN_fase2_AP_caixas.csv', 'ONN_fase2_ESG_caixas.csv'):
        for r in lt.ler_csv(os.path.join(F2, fn)): base.append((lt.fl(r['E']), lt.fl(r['N']), lt.fl(r['CT'])))
    rel = tr.ajustar(TER_IMP, base, TERRENO, modo='local', raio=6.0, fonte='CT das caixas de esgoto e pluvial das pranchas')
    log(f"  terreno: {rel['pontos']} CT; resíduo mediano {rel['antes_mediana']:+.2f} m (p95 {rel['antes_p95_abs']:.2f}) -> "
        f"{rel['depois_mediana']:+.3f} (p95 {rel['depois_p95_abs']:.3f})")
    # o IMP já vem numa grade de 0,50 m (olindina/ifc/onn_terreno_imp.py); as CT entram como vértices (tampa da caixa = terreno) e
    # a mesma malha vai para o clash e para o IFC de entrega (não reamostrar: a CT entre nós da grade saía até 8 cm fora)
    return rel


def _densificar(P, passo=4.0):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(math.ceil(L / passo)))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(1, k + 1)]
    return out


def pressurizadas(ter):
    """a rede de AF existente (PVC 60 mm do reservatório, desenhada no AF-001 só como referência) não entra: o cadastro não tem cota
    e qualquer cota adotada cria cruzamento que não existe (com a pluvial existente na saída do PVP-36 e com o alimentador do BA5).
    Fica só o ramal novo AF-01, que sai dela."""
    out = []
    cob = REGRAS['estudo']['cob_min']
    for r in lt.ler_csv(os.path.join(F2, 'ONN_fase2_pressurizadas.csv')):
        d = r['sistema']; de = lt.fl(r['DE_mm']) / 1000.0
        if d == 'AF' and r['situacao'] == 'existente': continue
        P = [tuple(map(float, v.split(','))) for v in r['vertices_UTM'].split()]
        P3 = lt.perfil_por_recobrimento(_densificar(P), de, cob[d], ter)
        e = md.elemento(f"{d}:{r['trecho']}", d, d, r['trecho'], 'pressao', de, P3, cob_min=cob[d], de_no=r['de'], para_no=r['para'],
                        material=r['material'], DN_mm=round(de * 1000), situacao=r['situacao'], obs=r['obs'])
        out.append(e)
    return out


def gravidade(ter):
    E, C = [], []
    for disc in ('AP', 'ESG'):
        T = lt.gravidade(os.path.join(F2, f'ONN_fase2_{disc}_trechos.csv'), disc, disc, ter)
        sit = {r['trecho']: r['situacao'] for r in lt.ler_csv(os.path.join(F2, f'ONN_fase2_{disc}_trechos.csv'))}
        for e in T:
            mat = e['info'].get('material', ''); dn = lt.fl(e['info'].get('DN_mm'))
            e['info']['material'] = 'Tubo PVC soldável' if dn and dn <= 50 else MAT_GRAV.get((disc, mat), 'Tubo PVC Série Normal')
            e['info']['situacao'] = sit[e['trecho']]
        cx = lt.caixas(os.path.join(F2, f'ONN_fase2_{disc}_caixas.csv'), disc, disc, ter, T)
        sc = {r['caixa']: r['situacao'] for r in lt.ler_csv(os.path.join(F2, f'ONN_fase2_{disc}_caixas.csv'))}
        for c in cx: c['info']['situacao'] = sc[c['info']['nome']]
        E += T; C += cx
    return E, C


def _caixas_existentes_fixas():
    """as caixas existentes não andam no cenário de desvios: o deslocamento é só da caixa nova."""
    from preclash import desvio as _dsv
    if getattr(_dsv, '_onn', False): return
    mv0 = _dsv.mover_caixas

    def mover_caixas(E, C, pend, regras, log=print, ter=None):
        marc = [c for c in C if c['info'].get('situacao') == 'existente' and not c['info'].get('equipamento')]
        for c in marc: c['info']['equipamento'] = True
        try:
            return mv0(E, C, pend, regras, log, ter=ter)
        finally:
            for c in marc: c['info'].pop('equipamento', None)
    _dsv.mover_caixas, _dsv._onn = mover_caixas, True


def _custo_eletrica_acima():
    """elétrica SEMPRE por cima da água (Anderson): cada cruzamento por baixo pesa como 100 colisões (Jandaíra, Alagoinhas, Sátiro).
    O custo de cada trecho ignora os trechos já estudados da mesma disciplina (a rede elétrica aqui é um alimentador só)."""
    from preclash import estudo as _est, clash as _cl
    if getattr(_est, '_onn', False): return
    _custo = _est.custo

    def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
        # o trecho vizinho da mesma rede (que chega na mesma caixa) não é obstáculo: senão a ponta dele, na caixa, empurra este
        # trecho 0,30 m para baixo e a elétrica sai alternando 0,70 / 1,00 m de uma caixa para a outra sem motivo
        if len(outros[0]):
            m = outros[3] != disc; outros = tuple(x[m] for x in outros)
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
    _est.custo, _est._onn = custo, True


# caixa de passagem desenhada em cima de rede existente (a CP-05 do EL-001 cai sobre o esgoto existente CE-22 -> CE-21, entre ele e a
# pluvial existente): o deslocamento padrão da ferramenta só procura até 1,50 m
# lado para onde ela anda: para o QDLT do BA5 (sudoeste), do outro lado da pluvial existente; assim o eletroduto ELE-05 cruza as
# redes de gravidade por baixo (1,20 m) e o ELE-06, curto, só cruza a água por cima
CAIXAS_A_AFASTAR = {'CP-05': (573906.478, 8743275.105)}


def _afastar_caixa(nome, E, C, rmax=2.5, folga=0.20, alvo=None, abertura=70.0, log=print):
    """leva a caixa de passagem ao ponto mais perto (até rmax) onde ela fica a 'folga' de toda peça de outra rede em planta; as pontas
    dos eletrodutos dela acompanham. Grava em ONN_caixas_movidas.json (vai para a prancha). Mesmo método do adaptador da Sátiro."""
    from shapely.geometry import LineString, Polygon, Point
    from shapely.ops import unary_union
    c = next((c for c in C if c['info'].get('nome') == nome), None)
    if c is None: return

    def poli(x, E_=None, N_=None):
        if x['forma'] == 'c': return Point(E_ if E_ is not None else x['E'], N_ if N_ is not None else x['N']).buffer(x['meia'])
        mx, my, rot = x.get('mx', x['meia']), x.get('my', x['meia']), x.get('rot', 0.0) if x['forma'] == 'r' else 0.0
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([E_ if E_ is not None else x['E'], N_ if N_ is not None else x['N']])
        return Polygon([p + a * mx * u + b * my * v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    # a água (AF, HID) passa por baixo da caixa (elétrica sempre acima da água): só conta a gravidade e as caixas
    O = unary_union([LineString(e['pts'][:, :2]).buffer(e['de'] / 2) for e in E if e['disc'] not in (c['disc'], 'AF', 'HID')] +
                    [poli(x) for x in C if x is not c and x['disc'] != c['disc']])
    pecas = [(e, k) for e in E if e['disc'] == c['disc'] and e['tipo'] == 'pressao' for k in (0, -1)
             if max(md.planta_local(c, e['pts'][k, 0], e['pts'][k, 1])) < 0.30]
    best = None
    a0 = math.degrees(math.atan2(alvo[1] - c['N'], alvo[0] - c['E'])) if alvo else 0.0
    angs = np.arange(a0 - abertura, a0 + abertura + 1e-6, 5) if alvo else np.arange(0, 360, 5)
    for r in np.arange(0.1, rmax + 1e-6, 0.05):
        for a in np.radians(angs):
            v = np.array([math.cos(a), math.sin(a)]) * r
            if poli(c, c['E'] + v[0], c['N'] + v[1]).buffer(folga).intersects(O): continue
            best = v; break
        if best is not None: break
    if best is None: log(f'  {nome}: sem posição livre até {rmax:.1f} m'); return
    c.setdefault('E0', c['E']); c.setdefault('N0', c['N']); c['E'] += best[0]; c['N'] += best[1]
    for e, k in pecas:
        e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = e['pts'].copy(); e['pts'][k, :2] += best; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    os.makedirs(SAIDA, exist_ok=True)
    fn = os.path.join(SAIDA, 'ONN_caixas_movidas.json')
    reg = [x for x in (json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []) if x.get('caixa') != nome]
    reg.append(dict(caixa=nome, disc=c['disc'], elemento=c['id'], status='caixa deslocada', de=[c['E0'], c['N0']], E=c['E'], N=c['N'],
                    desloc=round(float(np.hypot(c['E'] - c['E0'], c['N'] - c['N0'])), 2), lado=round(2 * c.get('mx', c['meia']), 3),
                    lado_y=round(2 * c.get('my', c['meia']), 3), rot=float(c.get('rot', 0.0)), forma=c['forma'], tubos=[e['trecho'] for e, _ in pecas]))
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    log(f'  {nome} afastada {np.hypot(*best):.2f} m das outras redes; {len(pecas)} eletrodutos acompanham')


def _sem_existente_x_existente():
    """conflito entre duas peças existentes (cadastro) não é da compatibilização: o que já está construído não muda.
    Sai da lista de conflitos (clash, soluções e desvios)."""
    from preclash import clash as _cl
    if getattr(_cl, '_onn', False): return
    det0 = _cl.detectar

    def detectar(elementos, caixas, regras, *a, **k):
        conf = det0(elementos, caixas, regras, *a, **k)
        sit = {x['id']: x['info'].get('situacao') for x in list(elementos) + list(caixas)}
        return [c for c in conf if not (sit.get(c['a']) == 'existente' and sit.get(c['b']) == 'existente')]
    _cl.detectar, _cl._onn = detectar, True


def so_externo(E, C, log=print):
    """regra do Anderson (21/10/2026): só a rede externa, da face da parede para fora (mesmo método da Sátiro e de Alagoinhas).
    Contorno do BA5 pela estrutura as built (olindina/ifc/predios.py); a rede é cortada na face e o que fica dentro sai."""
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
    C2 = [c for c in C if not Ui.contains(Point(c['E'], c['N']))]
    log(f'  só rede externa: {n_fora} trechos inteiros dentro do BA5 saíram, {n_cort} cortados na face; {len(C) - len(C2)} caixas de dentro saíram')
    return novos, C2


def carregar():
    if not os.path.exists(TERRENO) or os.environ.get('ONN_TERRENO_REFAZER') == '1': terreno_base()
    ter = Terreno(TERRENO)
    E = pressurizadas(ter)
    G, C = gravidade(ter)
    E += G
    ele = [e for e in E if e['disc'] == 'ELE']
    C += lt.caixas_de_nos(os.path.join(F2, 'ONN_fase2_ELE_caixas.csv'), 'ELE', 'ELE', ter, ele, {'CP 80x80': 0.80})
    for c in C:
        if c['disc'] == 'ELE': c['info']['tipo'] = 'caixa de passagem 80x80'; c['info']['situacao'] = 'novo'
    E, C = so_externo(E, C)
    for nome, alvo in CAIXAS_A_AFASTAR.items(): _afastar_caixa(nome, E, C, alvo=alvo)
    _caixas_existentes_fixas()
    _sem_existente_x_existente()
    _custo_eletrica_acima()
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas', 'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py): pranchas no padrão de executivo final
REVISAO = 'R01'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.30
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.60)
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1] if el.count(':') >= 1 else el
_PO = 'PROJETO_ORIGINAL/IMP/'
_DWG = {'AF-001': _PO + '01_AF/24-049-ONN-CTO-ETIB-IMP-PE-AF-001-AFR-R00.dwg',
        'ESG-001': _PO + '02_ESG/24-049-ONN-CTO-ETIB-IMP-PE-ESG-001-HIG-R00.dwg',
        'DRE-001': _PO + '03_DRE/24-049-ONN-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg',
        'EL-001': _PO + '04_ELE/24-049-ONN-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg',
        'IN-001': _PO + '05_PCI/24-049-ONN-CTO-ETIB-IMP-PE-IN-001-ING-R00.dwg'}
# ESG-001 e DRE-001 são o mesmo desenho (pluvial + esgoto do BA5): mudança de qualquer um dos dois sai nas duas folhas
_FOLHAS = {'AF': ['AF-001'], 'ESG': ['ESG-001', 'DRE-001'], 'AP': ['ESG-001', 'DRE-001'], 'ELE': ['EL-001'], 'HID': ['IN-001']}


def folhas(m):
    return _FOLHAS.get(m['disc'], [])


def folha(m):
    return (folhas(m) or [None])[0]


def executivo_dwg(m):
    return _DWG.get(m.get('folha') or folha(m))


_T_AF = (0.0, (574033.1579, 8743129.589))
TRANSF_DWG = {_DWG['AF-001']: _T_AF, _DWG['ESG-001']: _T_AF, _DWG['DRE-001']: _T_AF,
              _DWG['IN-001']: (0.0, (573528.4357723719, 8743203.6352746593)), _DWG['EL-001']: (0.0, (0.0, 0.0))}
