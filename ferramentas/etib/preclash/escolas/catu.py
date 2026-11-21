# -*- coding: utf-8 -*-
"""Adaptador da ETIB Catu (CAT) — fluxo novo (25/10/2026, o mesmo da Sátiro, Olindina, Itamira e Prof. Áurea).
A versão de 19/10 (terreno provisório, limites de 1,50/2,50 m, cenário BD) ficou em escolas/catu_2026-10-19.py.
Entrada (INVENTARIO.md, quadro "Entrada"): decisões C1 a C3 sem resposta -> vale a recomendada:
  C1 terreno = IMP as built levado às cotas da base (catu/ifc/cat_terreno.py: campo 78,25, restaurante e bloco sul 82,50, bloco a
     oeste 82,00, teatro 84,50; ajuste local às CT das caixas de esgoto e drenagem);
  C2 esgoto × drenagem: dentro dos limites do "aplicar e avisar" resolvemos (caixa até 0,60 m), o resto vai à página de pendências;
  C3 refazer no fluxo atual (profundidade máxima 2,00 m, estrutura pela forma real), sem aproveitar o EXECUTIVO_REVISADO de 19/10.
Fontes (só leitura): gravidade = RELATORIOS/FASE3_COTAS_2026-10-18 (fase 2 + CF = CT − profundidade nas 5 caixas da DRE com rótulo
incoerente); pressurizadas = georef/work/CATU/rede/{af,inc,ele}_rede.json (só planta); equipamentos = georef/equip_catu.py.
Padrão:
  - só rede externa: contorno dos prédios pela SIT (catu/ifc/predios.py); a rede é cortada na face e o que fica dentro sai;
  - pressurizadas: estudo de cota (água e hidrante uma cota por rede; elétrica e alarme por trecho entre caixas, sempre acima da
    água), sem mergulho pontual; profundidade máxima 2,00 m; recobrimento mínimo AF 0,30 (premissa), hidrante e alarme 0,50 (nota do
    INC-001), elétrica 0,70 (NBR 5410, o EL-001/002 não informa);
  - gravidade (esgoto e drenagem): cotas das pranchas; gravidade × gravidade desloca a caixa até 0,60 m (aplicar e avisar);
  - drenos Ø40 de ar-condicionado fora (sistema dos prédios, decisão de 18/10); canaletas do campo só como obstáculo;
  - material pela legenda: AF tubo PVC soldável marrom; esgoto PVC Série Normal (PVCR onde rotulado); pluvial PVC Série Reforçada
    (PVC-R), Vinilfort (PVC-V) e dreno corrugado perfurado (PVC-DR); hidrante PEAD; alarme eletroduto PEAD; elétrica enterrada
    eletroduto PEAD corrugado flexível (regra do projeto: a legenda só traz o embutido);
  - estrutura as built dos blocos novos pela forma real (catu/ifc/cat_estrutura.py)."""
import os, sys, csv, json, math, importlib.util
import numpy as np
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Catu'
SIGLA = 'CAT'
BASE = r'D:\Projeto Modelagem\ETIB-CATU'
REL = os.path.join(BASE, 'RELATORIOS')
F3 = os.path.join(REL, 'FASE3_COTAS_2026-10-18')
REDE = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\rede'
CATU = r'D:\Projeto Modelagem\FERRAMENTAS\catu\ifc'
SAIDA = os.environ.get('CAT_SAIDA') or os.path.join(REL, 'PRECLASH_2026-10-25')
DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
TER_IMP = os.path.join(DADOS, 'catu_terreno_imp.npz')
TERRENO = os.path.join(DADOS, 'catu_terreno_base.npz')
ORIGEM = (567700.0, 8634650.0, 0.0)
EPSG = 31984
CAIXA_OBRA = (567620.0, 8634530.0, 567806.0, 8634722.0)

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
NOMES_DISC = {'AF': 'Água fria', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial', 'ELE': 'Elétrica enterrada (alimentação e iluminação externa)',
              'HID': 'Hidrantes (PCI)', 'SDAI': 'Alarme de incêndio (PCI)', 'EST': 'Estrutura as built (referência)'}
MOTIVO_PONTA = {'ELE': 'chegada na face da edificação ou no quadro/poste (sobe para o quadro)',
                'ESG': 'saída de esgoto da edificação (ramal predial) ou lançamento na rede existente',
                'DRE': 'descida/ramal pluvial da edificação ou lançamento',
                'AF': 'entrada da edificação ou saída do reservatório existente',
                'HID': 'hidrante, recalque ou casa de bombas', 'SDAI': 'chegada na central de alarme / edificação'}
COB = REGRAS['estudo']['cob_min']
MAT_AF = 'Tubo PVC soldável marrom'
MAT_ELE = 'Eletroduto PEAD corrugado flexível'
MAT_PRESS = {'HID': 'Tubo PEAD', 'SDAI': 'Eletroduto PEAD'}
DE_RNC = {'3/4': 26.7, '1': 33.4, '1.1/4': 42.2, '1.1/2': 48.3, '2': 60.3, '2.1/2': 73.0, '3': 88.9, '4': 114.3, '5': 141.3, '6': 168.3}
APLICADO = []
# recobrimento das redes de água (uma cota por rede), escolhido com catu/ifc/cat_diag_estudo.py entre os de menos colisões no
# terreno de entrega: AF 1,30 (sobra só a EL2-CX02, caixa de passagem que anda) e hidrante 1,75 (nenhuma; a Sátiro ficou em 1,85);
# a água fica abaixo da elétrica com folga
# trecho de elétrica com o recobrimento fixado: EL2-021 a 0,95 m passa sob o ramal DRE-125 e o DRE-056 (rasos, junto da CA-13) e
# ainda fica acima do hidrante HID-09; o estudo ficava no mínimo (0,70) e batia no DRE-125
COB_TRECHO = {'ELE:EL2-021': 0.95,
              # banco EL1-R12 (CX07 -> CX14) a 1,10 m: passa sob o ESG-15 junto da PVE-03
              'ELE:EL1-005': 1.10, 'ELE:EL1-010': 1.10, 'ELE:EL1-025': 1.10, 'ELE:EL1-038': 1.10,
              # banco EL1-R08 no mínimo: passa sobre o ESG-17 na saída da PVE-04 (o estudo descia a 0,95-1,00 e encostava nele)
              'ELE:EL1-029': 0.70, 'ELE:EL1-039': 0.70, 'ELE:EL1-046': 0.70, 'ELE:EL1-068': 0.70}
COB_REDE = {'AF': float(os.environ.get('CAT_COB_AF') or 1.30), 'HID': float(os.environ.get('CAT_COB_HID') or 1.75)}


def _mod(nome, arq):
    spec = importlib.util.spec_from_file_location(nome, arq); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


PR = _mod('cat_predios', os.path.join(CATU, 'predios.py'))
EST = _mod('cat_estrutura', os.path.join(CATU, 'cat_estrutura.py'))


def mat_grav(disc, mat, dn):
    m = (mat or '').upper().replace('-', '')
    if 'DR' in m: return 'Tubo PVC corrugado perfurado (dreno)'
    if disc == 'ESG': return 'Tubo PVC Série Reforçada' if 'PVCR' in m else 'Tubo PVC Série Normal'
    if 'PVCV' in m or (dn and dn >= 250): return 'Tubo PVC Vinilfort'
    return 'Tubo PVC Série Reforçada'


DEGRAU_FACE = ('EL1-044', 'EL1-066', 'EL1-014', 'EL1-018')


def _esperada():
    fn = os.path.join(SAIDA, f'{SIGLA}_preclash_AD_verificacao.csv')
    out = {}
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'):
            if r['tipo'] == 'ponta solta' and r['disc'] in MOTIVO_PONTA: out[('ponta solta', r['trecho'])] = MOTIVO_PONTA[r['disc']]
            if r['tipo'] == 'pedaço curto' and r['disc'] in ('ELE', 'SDAI'): out[('pedaço curto', r['trecho'])] = 'trecho curto entre a caixa e a face da edificação'
            if r['tipo'] == 'degrau' and r['disc'] == 'ELE' and r['trecho'] in DEGRAU_FACE:
                out[('degrau', r['trecho'])] = 'eletrodutos de bancos diferentes chegando lado a lado na face da subestação (sobem ao QGBT)'
    return out


VERIFICACAO_ESPERADA = _esperada()


def _densificar(P, passo=4.0):
    out = [tuple(P[0][:2])]
    for a, b in zip(P[:-1], P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(math.ceil(L / passo)))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(1, k + 1)]
    return out


def _perfil(id_, disc, rede, trecho, pts2d, de, ter, **info):
    P = lt.perfil_por_recobrimento(_densificar(pts2d), de, COB[disc], ter)
    return md.elemento(id_, disc, rede, trecho, 'pressao', de, P, cob_min=COB[disc], DN_mm=round(de * 1000), situacao='novo',
                       cota=f'topo a {COB[disc]:.2f} m do terreno no mínimo', **info)


def _de_eletroduto(rotulos):
    import re
    des = [DE_RNC[m.group(1).replace('. ', '.').strip('.')] for m in re.finditer(r'Ø\s*([\d./]+)"', rotulos or '')
           if m.group(1).replace('. ', '.').strip('.') in DE_RNC]
    return (max(des) if des else DE_RNC['3/4']) / 1000.0


# o ramal desenhado passando do registro e voltando (AF-01 vai ao TE-5 e o AF-03 volta 0,36 m ao RG-02; o mesmo no AF-02/RG-01 e no
# AF-08/RG-05): o trecho termina no registro, e o ramal curto liga o registro ao tê
AF_PONTA = {'AF-01': (567701.93, 8634680.94), 'AF-02': (567729.88, 8634705.83), 'AF-08': (567745.14, 8634608.33)}
# banco de eletrodutos: no desenho uma linha por eletroduto, ~0,15 m uma da outra; na extração todos ficaram no mesmo eixo
ESP_BANCO = 0.15


def _paralela(pts, d):
    from shapely.geometry import LineString
    if abs(d) < 1e-6: return pts
    g = LineString(pts).offset_curve(d, join_style=2, mitre_limit=5.0)
    Q = list(g.coords) if g.geom_type == 'LineString' else list(max(g.geoms, key=lambda x: x.length).coords)
    a = np.array(pts[0]); return [list(q) for q in (Q if np.hypot(*(np.array(Q[0]) - a)) <= np.hypot(*(np.array(Q[-1]) - a)) else Q[::-1])]


def pressurizadas(ter):
    E = []
    af = json.load(open(os.path.join(REDE, 'af_rede.json'), encoding='utf-8'))
    for t in af['trechos']:
        if t['trecho'] in AF_PONTA: t = dict(t, pts=t['pts'][:-1] + [list(AF_PONTA[t['trecho']])])
        de = float(t.get('DN_adotado') or t.get('DN_mm') or 32) / 1000.0
        E.append(_perfil(f'AF:{t["trecho"]}', 'AF', 'AF', t['trecho'], t['pts'], de, ter, material=MAT_AF, obs=t.get('obs', '')))
    inc = json.load(open(os.path.join(REDE, 'inc_rede.json'), encoding='utf-8'))
    for t in inc['hidrantes']:
        E.append(_perfil(f'HID:{t["trecho"]}', 'HID', 'HID', t['trecho'], t['pts'], 0.075, ter, material=MAT_PRESS['HID'], diametro='2½"'))
    for t in inc['sdai']:
        E.append(_perfil(f'SDAI:{t["trecho"]}', 'SDAI', 'SDAI', t['trecho'], t['pts'], 0.060, ter, material=MAT_PRESS['SDAI'], diametro='2"',
                         lacos=(t.get('lacos_rotulo') or t.get('lacos_inferidos') or '')))
    ele = json.load(open(os.path.join(REDE, 'ele_rede.json'), encoding='utf-8'))
    for tag, rede in (('EL1', 'ELE-BT'), ('EL2', 'ELE-IL')):
        rot = {r['rota']: r for r in ele[tag]['rotas']}
        # o mesmo eixo pode vir desenhado nos dois sentidos (EL1-039 e EL1-068 da EL1-R08): a chave do banco é o eixo num sentido só
        def chave(t):
            f = tuple(map(tuple, np.round(t['pts'], 2).tolist())); return (t['rota'], min(f, f[::-1])), min(f, f[::-1]) != f
        banco = {}
        for t in ele[tag]['eletrodutos']: banco.setdefault(chave(t)[0], []).append(t['eletroduto'])
        for t in ele[tag]['eletrodutos']:
            circ = rot.get(t['rota'], {}).get('circuitos_rotulo', '')
            k_, inv = chave(t); irm = banco[k_]
            d = (irm.index(t['eletroduto']) - (len(irm) - 1) / 2) * ESP_BANCO
            if len(irm) > 1:
                base = t['pts'][::-1] if inv else t['pts']; pts = _paralela(base, d); pts = pts[::-1] if inv else pts
            else:
                pts = [list(p) for p in t['pts']]
            for k in (0, -1):            # ponta fora de caixa (o banco segue em outro trecho): fica no nó do desenho
                if not any(np.hypot(*(np.array(t['pts'][k]) - np.array(n['c']))) < 0.5 for n in ele[tag]['nos']): pts[k] = list(t['pts'][k])
            e = _perfil(f'ELE:{t["eletroduto"]}', 'ELE', 'ELE', t['eletroduto'], pts, _de_eletroduto(circ), ter,
                        material=MAT_ELE, rota=t['rota'], circuitos=circ, folha=('EL-001' if tag == 'EL1' else 'EL-002'))
            if len(irm) > 1: e['_banco'] = (tag, k_); e['_banco_d'] = d; e['_banco_inv'] = inv; e['_banco_n'] = len(irm)
            E.append(e)
    return E


def _contornar_bancos(AJ, E, C, pares, ter):
    """contorno curto de PV (cat_ajustes.contornar); no banco de eletrodutos o contorno é do banco inteiro: contorna o eixo, com a
    largura do banco, e cada eletroduto sai paralelo a ele (cada um contornando sozinho, os quatro do banco EL1-R12 em volta da
    PVP-09 caíam nos mesmos cantos, um por cima do outro)."""
    tr_b = {e['trecho']: e['_banco'] for e in E if e.get('_banco')}
    simples = [p for p in pares if p[0] not in tr_b]
    por_banco = {}
    for tr, nome in pares:
        if tr in tr_b: por_banco.setdefault(tr_b[tr], []).append(nome)
    reg = AJ.contornar(E, C, simples, SAIDA)
    for b, nomes in por_banco.items():
        M = [e for e in E if e.get('_banco') == b]; m0 = M[0]; meia = max(abs(m['_banco_d']) for m in M)
        can = lambda P, inv: P[::-1] if inv else P
        eixo = np.array(_paralela(can(m0['pts'][:, :2], m0['_banco_inv']).tolist(), -m0['_banco_d']))
        z0 = float(np.median(m0['pts'][:, 2]))
        tmp = dict(m0, id='ELE:~banco', trecho='~banco', de=m0['de'] + 2 * meia, pts=np.column_stack([eixo, np.full(len(eixo), z0)]))
        tmp['info'] = dict(m0['info'])
        AJ.contornar([tmp], C, [('~banco', n) for n in dict.fromkeys(nomes)], os.path.join(SAIDA, '_tmp_banco'), log=lambda *a: None)
        if tmp['pts'] is None or len(tmp['pts']) == len(eixo) and np.allclose(tmp['pts'][:, :2], eixo): continue
        for m in M:
            novo = np.array(_paralela(tmp['pts'][:, :2].tolist(), m['_banco_d'])); novo = can(novo, m['_banco_inv'])
            for k in (0, -1): novo[k] = m['pts'][k, :2]           # pontas no mesmo lugar (caixa ou nó do desenho)
            P = lt.perfil_por_recobrimento(_densificar(novo.tolist()), m['de'], COB['ELE'], ter)
            antigo = m.get('pts_planta0', m['pts']).copy(); m['pts_planta0'] = antigo
            m['pts'] = np.asarray(P, float); m['pts_sol'] = m['pts'].copy(); m.pop('S', None)
            reg.append(dict(trecho=m['trecho'], disc=m['disc'], elemento=m['id'], caixa=' + '.join(dict.fromkeys(nomes)), status='contorno em planta',
                            antigo=[list(map(float, p[:2])) for p in antigo], pontos=[list(map(float, p[:2])) for p in m['pts']]))
            print(f"  {m['trecho']} contorna {', '.join(dict.fromkeys(nomes))} em planta (banco)")
    json.dump(reg, open(os.path.join(SAIDA, 'CAT_contornos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _caixas_pressao(nos, disc, rede, ter, elementos, lados, prof_sob_eixo=0.15, raio=1.0, tipo_nome=None):
    out = []
    for n in nos:
        lado = lados.get(n['tipo'])
        if lado is None: continue
        E, N = n['c']; zt = float(ter.z([[E, N]])[0])
        if np.isnan(zt): continue
        zs = [p[2] - e['de'] / 2 for e in elementos for p in e['pts'] if np.hypot(p[0] - E, p[1] - N) < raio]
        zb = (min(zs) if zs else zt - 0.6) - prof_sob_eixo        # provisório: o estudo de cota acerta o fundo (_patches)
        out.append(md.caixa(f'{disc}:{n["id"]}', disc, rede, 'q', E, N, lado / 2, zb, zt, nome=n['id'],
                            tipo=(tipo_nome or {}).get(n['tipo'], n['tipo']), situacao='novo',
                            cota='tampa no terreno; fundo 0,15 m abaixo do eletroduto mais baixo'))
    return out


def gravidade(ter):
    dre = lt.gravidade(os.path.join(F3, 'CAT_fase3_DRE_trechos.csv'), 'DRE', 'DRE', ter, excluir_classe=('dreno', 'calha'))
    esg = lt.gravidade(os.path.join(F3, 'CAT_fase3_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    for e in dre + esg:
        e['info']['material'] = mat_grav(e['disc'], e['info'].get('material'), lt.fl(e['info'].get('DN_mm')))
        e['info']['situacao'] = 'novo'
        # ESG-34 (Ø50) e ESG-35 (Ø100) chegam na CES-04 no mesmo ponto, 0,15 m um do outro na saída: o Ø50 chega 0,15 m ao lado
        if e['trecho'] == 'ESG-34':
            e['pts'] = e['pts'].copy(); e['pts'][-1, 1] -= 0.15; e['pts_sol'] = e['pts'].copy()
    C = lt.caixas(os.path.join(F3, 'CAT_fase3_DRE_caixas.csv'), 'DRE', 'DRE', ter, dre)
    C += lt.caixas(os.path.join(F3, 'CAT_fase3_ESG_caixas.csv'), 'ESG', 'ESG', ter, esg)
    return dre + esg, C


def equipamentos(ter, E):
    """equipamentos de equip_catu.py (hidrantes, abrigos, recalque, casa de bombas, quadros, postes, registros, prumadas AP,
    canaletas) com a classe IFC; a central do alarme fica dentro do prédio e sai; canaleta só como obstáculo do clash."""
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
    import equip_catu
    Ceq, Eeq, _ = equip_catu.equipamentos(ter, E)
    CL = {'hidrante': 'IfcFireSuppressionTerminal', 'abrigo': 'IfcFireSuppressionTerminal', 'recalque': 'IfcFireSuppressionTerminal',
          'casa de bombas': 'IfcBuildingElementProxy', 'quadro': 'IfcElectricDistributionBoard', 'poste': 'IfcLightFixture',
          'registro': 'IfcValve'}
    C = []
    for c in Ceq:
        q = c['info'].get('equip')
        if q == 'central': continue                              # dentro do prédio
        if q == 'base de poste':                                  # a base enterrada do poste é uma caixa de passagem (como na Sátiro)
            c['info'].update(tipo='caixa de passagem da base do poste', situacao='novo'); c['rede'] = 'ELE'; C.append(c); continue
        if q == 'poste': c['zb'] = float(ter.z([[c['E'], c['N']]])[0]) + 0.30
        c['info'].update(equipamento=True, classe_ifc=CL.get(q, 'IfcBuildingElementProxy'), situacao='novo')
        if c['disc'] == 'ELE': c['rede'] = 'ELE'                       # elétrica numa rede só (o poste é da rede de quem chega nele)
        if q == 'recalque': c['info']['pred'] = 'BREECHINGINLET'
        if q == 'registro': c['info']['pred'] = 'ISOLATING'; c['info']['equipamento'] = False     # caixa do registro anda como caixa de passagem
        C.append(c)
    Ex = []
    for e in Eeq:
        if e['info'].get('equip') == 'canaleta':
            P = e['pts']
            for k, (a, b) in enumerate(zip(P[:-1], P[1:])):
                m = (a + b) / 2; L = float(np.hypot(*(b[:2] - a[:2])))
                if L < 0.05: continue
                C.append(md.caixa_retangular(f'CAN:{e["trecho"]}.{k + 1}', 'DRE', 'DRE-CAN', m[0], m[1], L, 0.30, math.atan2(b[1] - a[1], b[0] - a[0]),
                                             min(a[2], b[2]) - 0.15, max(a[2], b[2]) + 0.15, nome=f'{e["trecho"]} (canaleta)',
                                             tipo='canaleta de superfície', so_clash=True, cota='topo no terreno'))
        else:
            e['info']['material'] = 'Tubo PVC Série Reforçada'; e['info']['situacao'] = 'novo'; Ex.append(e)
    return C, Ex


def so_externo(E, C, log=print):
    """só a rede externa (Anderson, 21/10/2026): trecho cortado na face do prédio; o que fica dentro sai."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    # a estrutura dos prédios novos (pilar, baldrame, sapata da fachada) passa até ~0,25 m da face do pilar: a rede para ali
    U = unary_union([PR.uniao()] + [p.buffer(0.25, join_style=2) for _, p in EST.contornos()]); Ui = U.buffer(-0.05)
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
    C2 = [c for c in C if c['disc'] == 'EST' or c['info'].get('so_clash') or not Ui.contains(Point(c['E'], c['N']))]
    novos = [e for e in novos if not e.get('cortado') or _comp(e) >= 0.80]
    log(f'  só rede externa: {n_fora} trechos inteiros dentro dos prédios saíram, {n_cort} cortados na face; '
        f'{len(C) - len(C2)} caixas/equipamentos de dentro saíram')
    return novos, C2


def _aparar_sapatas(E, C, folga=0.03, log=print):
    """ponta cortada na face do prédio que cai sobre a sapata da fachada (a sapata passa da face; o SDAI-38 entrava na casa de
    resíduos 4,8 cm dentro da sapata cônica): a rede para antes da sapata, fora da projeção dela."""
    from preclash import clash as cl
    sap = [c for c in C if c['disc'] == 'EST' and c['forma'] == 'r']
    for e in E:
        if not e.get('cortado') or e['tipo'] != 'pressao': continue
        r = e['de'] / 2 + folga
        dentro = lambda q: any(max(md.planta_local(c, q[0], q[1])) < r for c in sap if abs(c['E'] - q[0]) < 3 and abs(c['N'] - q[1]) < 3)
        for k in (0, -1):
            P = e['pts'] if k == 0 else e['pts'][::-1]
            if not dentro(P[0]): continue
            Q = cl.amostra(P, 0.02); S = np.r_[0, np.cumsum(np.hypot(*np.diff(Q[:, :2], axis=0).T))]
            i = next((i for i in range(len(Q)) if not dentro(Q[i])), None)
            if i is None or S[i] > 1.0: continue
            s0 = np.r_[0, np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))]; j = int(np.searchsorted(s0, S[i], side='right'))
            novo = np.vstack([Q[i], P[j:]]); novo = novo if k == 0 else novo[::-1]
            e['pts'] = novo; e['pts_sol'] = novo.copy(); e.pop('S', None)
            log(f'  {e["id"]}: ponta na face sobre a sapata; para {S[i]:.2f} m antes, fora dela')


def _comp(e):
    return float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)))


def _sem_soltos(E, C, log=print):
    """pedaço de eletroduto/alarme solto na extração (componente com menos de 3 m sem ponta em caixa da disciplina) sai."""
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
    """pontas de pressurizadas da mesma disciplina a menos de 3 cm (tê do alarme TE-20: SDAI-15 a 1 cm do SDAI-16/17) viram o mesmo nó,
    para o estudo de cota tratar o tê como um nó só (sem degrau)."""
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
    """trecho de pressão que mudou em planta entra em CAT_contornos.json com o traçado original e o final (para a prancha)."""
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


def _suavizar_rigido(E, ter, lim=4.5, log=print):
    """tubo rígido (água fria, PVC soldável): a mudança de inclinação em cada vértice fica em até 'lim' graus (a junta absorve até 5°;
    acima disso precisaria de peça, e a peça comercial só tem 45° e 90°). No cume o vértice desce até a corda; no vale ele sobe até a
    corda sem ficar com menos de 1,00 m de terra em cima (o resto, os vizinhos descem até 0,50 m). As pontas (nós) não mudam."""
    t = math.tan(math.radians(lim)); n_ = 0
    for e in E:
        if e['disc'] != 'AF' or e['tipo'] != 'pressao' or len(e['pts']) < 3: continue
        P = e['pts'].copy(); z0 = P[:, 2].copy(); s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
        zt = ter.z(P[:, :2]); zt = np.where(np.isfinite(zt), zt, P[:, 2] + 1.3)
        zmax = zt - 1.00 - e['de'] / 2; zmin = z0 - 0.50
        for _ in range(3000):
            mud = False
            for i in range(1, len(P) - 1):
                L1, L2 = s_[i] - s_[i - 1], s_[i + 1] - s_[i]
                if L1 < 1e-3 or L2 < 1e-3: continue
                d = math.degrees(math.atan((P[i + 1, 2] - P[i, 2]) / L2) - math.atan((P[i, 2] - P[i - 1, 2]) / L1))
                corda = P[i - 1, 2] + (P[i + 1, 2] - P[i - 1, 2]) * L1 / (L1 + L2)
                if d < -lim and P[i, 2] > corda:
                    P[i, 2] = max(corda, P[i, 2] - 0.01); mud = True
                elif d > lim and P[i, 2] < corda:
                    if P[i, 2] + 0.005 <= zmax[i]: P[i, 2] = min(corda, P[i, 2] + 0.005); mud = True
                    else:
                        for k in (i - 1, i + 1):
                            if 0 < k < len(P) - 1 and P[k, 2] - 0.005 >= zmin[k]: P[k, 2] -= 0.005; mud = True
            if not mud: break
        if not np.allclose(P, e['pts']):
            e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None); n_ += 1
    if n_: log(f'  {n_} trechos de água fria com a inclinação suavizada (até {lim:.1f}° por junta)')


def _patches():
    """perfil que acompanha o terreno nos taludes, pontas rebaixadas em rampa, elétrica por cima da água (mesmas funções da Sátiro,
    escolas/satiro.py) e o poste anda com a base."""
    from preclash import estudo as _est, desvio as _dsv
    if getattr(_est, '_cat', False): return
    S = _mod('sat_aux', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'satiro.py'))
    S.REGRAS['estudo']['prof_max'] = REGRAS['estudo']['prof_max']
    def perfil(pts2d, de, cob, ter, passo=0.5, desvio=0.20, trecho_min=2.0):
        return S.perfil_talude(pts2d, de, cob, ter)
    _est.perfil_por_recobrimento = perfil; _dsv.perfil_por_recobrimento = perfil
    est0 = _est.estudar

    def estudar(E, caixas, regras, ter, log=print):
        rel = est0(E, caixas, regras, ter, log=log)
        S._rampas(E, caixas, ter, log)
        _suavizar_rigido(E, ter, log=log)
        for c in caixas:                     # caixa de passagem/registro com a tampa no terreno do lugar onde ficou
            if c['disc'] in ('ELE', 'SDAI', 'AF') and not c['info'].get('equipamento'):
                z = float(ter.z([[c['E'], c['N']]])[0])
                if np.isfinite(z): c['zt'] = z
        # fundo da caixa de passagem de elétrica/alarme a 0,10 m do eletroduto mais fundo que chega nela, depois do estudo (no
        # carregamento ele vinha do perfil provisório e podia ficar mais fundo que o necessário: EL2-CX02 sobre o AF-01)
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
        for e in E:
            a = antes.get(e['id'])
            if a is not None and (a.shape != e['pts'][:, :2].shape or np.abs(a - e['pts'][:, :2]).max() > 0.01):
                e.setdefault('pts_planta0', np.column_stack([a, e['pts'][:len(a), 2]]) if a.shape[0] <= len(e['pts']) else e['pts'].copy())
        _registrar_planta(E)
        return dv
    _dsv.aplicar = aplicar
    S._custo_eletrica_acima()
    # trecho de água com cota própria (COB_TRECHO) sai do grupo da rede e vira um grupo só dele, com a cota fixada
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
    # rede cortada na face do prédio × estrutura do próprio prédio junto da face (baldrame, pilar, sapata a menos de 0,60 m do
    # contorno): é a passagem da rede pela parede, não conflito de rede externa (mesmo critério da Sátiro, que tira a estrutura
    # dos prédios do clash); a estrutura que avança além disso continua contando
    from preclash import clash as _cl
    from shapely.geometry import Point
    from shapely.ops import unary_union
    B = unary_union([PR.uniao()] + [p.buffer(0.25, join_style=2) for _, p in EST.contornos()]).boundary
    det0 = _cl.detectar

    def detectar(elementos, caixas, regras, *a, **k):
        conf = det0(elementos, caixas, regras, *a, **k)
        cort = {x['id'] for x in elementos if x.get('cortado') or min(B.distance(Point(*x['pts'][k, :2])) for k in (0, -1)) < 1.00}
        est = {x['id'] for x in caixas if x['disc'] == 'EST'}
        return [c for c in conf if not (((c['a'] in est and c['b'] in cort) or (c['b'] in est and c['a'] in cort))
                                         and B.distance(Point(c['E'], c['N'])) < 0.60)]
    _cl.detectar = detectar
    _est._cat = True


# caixas de passagem de elétrica e alarme desenhadas em cima de PV/caixa de drenagem, sem posição livre para a ferramenta (aplicar e
# avisar: caixa de passagem até 1,50 m, os eletrodutos que chegam nela acompanham). Posições (UTM) escolhidas nas imagens de
# catu/ifc/cat_spot.py: a EL2-CX04 sai da PVP-05 para sudoeste (o EL2-013 contorna o PV); as caixas do alarme CX-09 e CX-12 saem
# de dentro da PVP-05 e da PVP-07 para nordeste do coletor Ø280; a EL2-CX08 sai 0,25 m de cima do hidrante HID-08.
# Hidrante desenhado em cima de tubo de drenagem recua pelo próprio ramal (como a torneira de jardim da Sátiro): H-10 sobre o DRE-205.
RECUO = {'H-10': ('HID-06', 0.35)}


# geratriz de chegada ajustada (aplicar e avisar, até 0,20 m, declividade mínima mantida): a gravidade sobe um pouco na chegada
# para a pressurizada (que tem cota única ou fica acima da água) passar com folga. {trecho: (Δz na jusante, Δz na montante)};
# ramal que vem de prumada (sem CF no projeto) sobe inteiro, com os ramais e a prumada de montante.
CHEGADA = {'ESG-04': (0.13, 0.0),          # CE-06 -> PVE-04: i 1,65 % -> 1,00 %; passa sobre o EL1-069
           'ESG-15': (0.20, 0.0),          # PVE-02 -> PVE-03: i 9,5 % -> 8,4 %; passa sobre o EL1-010 e o EL1-025
           'DRE-125': (0.20, 0.20),        # ramal da AP-7 na CA-13: chega 0,20 m acima do fundo; passa sobre o EL2-021
           'DRE-218': (0.20, 0.20),        # ramal da AP-6 na PVP-02: chega 0,20 m acima do fundo; passa sobre o AF-01
           'DRE-212': (0.10, 0.10), 'DRE-032': (0.10, 0.10), 'DRE-104': (0.10, 0.10)}   # ramais das AP-17/18 na PVP-05; sobre o AF-07
PRUMADA_SOBE = {'AP-6': 0.20, 'AP-7': 0.20, 'AP-17': 0.10, 'AP-18': 0.10}


def _chegadas(E, log=print):
    for e in E:
        if e['tipo'] != 'gravidade': continue
        if e['trecho'] in CHEGADA:
            dj, dm = CHEGADA[e['trecho']]; P = e['pts'].copy()
            s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))]); t = s_ / max(s_[-1], 1e-9)
            P[:, 2] += dm + (dj - dm) * t
            e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None)
            for k, d in (('GI_mont', dm), ('GI_jus', dj)):
                if e['info'].get(k) is not None: e['info'][k] = round(float(e['info'][k]) + d, 3)
            APLICADO.append(dict(tipo='geratriz de chegada', trecho=e['trecho'], dz_jusante=dj, dz_montante=dm,
                                 E=float(P[-1, 0]), N=float(P[-1, 1])))
            log(f"  {e['trecho']}: chegada {dj * 100:.0f} cm mais alta" + (f', montante {dm * 100:.0f} cm' if dm else ''))
        elif e['trecho'] in PRUMADA_SOBE:
            e['pts'] = e['pts'].copy(); e['pts'][0, 2] += PRUMADA_SOBE[e['trecho']]; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)


def _sem_duplicados(E, log=print):
    """tubo de gravidade desenhado duas vezes (mesmas pontas: DRE-212/DRE-262): fica o que tem rótulo."""
    fora = set(); G = [e for e in E if e['tipo'] == 'gravidade']
    for i, a in enumerate(G):
        for b in G[i + 1:]:
            if a['id'] in fora or b['id'] in fora: continue
            pa, pb = a['pts'][[0, -1], :2], b['pts'][[0, -1], :2]
            if min(np.abs(pa - pb).max(), np.abs(pa - pb[::-1]).max()) > 0.05: continue
            fora.add(b['id'] if a['info'].get('material') else a['id'])
    if fora: log(f"  {len(fora)} tubos repetidos no desenho saíram: {', '.join(sorted(x.split(':', 1)[1] for x in fora))}")
    return [e for e in E if e['id'] not in fora]


# contorno de um grupo de peças juntas (PV + sapata vizinha): a pressurizada passa por fora do conjunto, pelo lado mais curto, com
# 0,30 m de folga e cantos em 90° (aplicar e avisar: desvio lateral até 2,00 m). {trecho: [nomes das peças]}
CONTORNO_GRUPO = {'EL2-008': ['PVP-13', 'casa de resíduos fundacao 2046420'],
                  }


def _contornar_grupo(E, C, folga=0.30, log=print):
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union, substring
    porn = {c['info'].get('nome', c['id']): c for c in C}
    def poli(c, b):
        if c['forma'] == 'c': return Point(c['E'], c['N']).buffer(c['meia'] + b, join_style=2)
        mx, my, rot = c.get('mx', c['meia']), c.get('my', c['meia']), c.get('rot', 0.0)
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); p = np.array([c['E'], c['N']])
        return Polygon([p + a * (mx + b) * u + d * (my + b) * v for a, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    fn = os.path.join(SAIDA, f'{SIGLA}_contornos_grupo.json'); reg = []
    for tr, nomes in CONTORNO_GRUPO.items():
        e = next((e for e in E if e['trecho'] == tr and e['tipo'] == 'pressao'), None)
        if e is None or any(n not in porn for n in nomes): continue
        B = unary_union([poli(porn[n], folga + e['de'] / 2) for n in nomes]).buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
        B = Polygon(B.exterior) if B.geom_type == 'Polygon' else Polygon(max(B.geoms, key=lambda g: g.area).exterior)
        L = LineString(e['pts'][:, :2]); X = L.intersection(B.exterior)
        if X.is_empty: continue
        pts_x = [X] if X.geom_type == 'Point' else [g for g in getattr(X, 'geoms', [X]) if g.geom_type == 'Point']
        if len(pts_x) < 2: continue
        s_ = sorted(L.project(q) for q in pts_x); a, b = L.interpolate(s_[0]), L.interpolate(s_[-1])
        R = B.exterior; ra, rb = R.project(a), R.project(b)
        arc1 = substring(R, min(ra, rb), max(ra, rb)); arc2 = LineString(list(substring(R, max(ra, rb), R.length).coords) + list(substring(R, 0, min(ra, rb)).coords)[1:])
        arc = min((arc1, arc2), key=lambda g: g.length); Q = np.array(arc.coords)
        if np.hypot(*(Q[0] - np.array(a.coords[0]))) > np.hypot(*(Q[-1] - np.array(a.coords[0]))): Q = Q[::-1]
        P = e['pts']; S_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
        z = lambda s: float(np.interp(s, S_, P[:, 2]))
        antes = [p for p, s in zip(P, S_) if s < s_[0] - 1e-6]; depois = [p for p, s in zip(P, S_) if s > s_[-1] + 1e-6]
        meio = [(q[0], q[1], z(s_[0] + (s_[-1] - s_[0]) * k / max(len(Q) - 1, 1))) for k, q in enumerate(Q)]
        novo = np.array([tuple(p) for p in antes] + meio + [tuple(p) for p in depois])
        e.setdefault('pts_planta0', P.copy()); e['pts'] = novo; e['pts_sol'] = novo.copy(); e.pop('S', None)
        reg.append(dict(trecho=tr, disc=e['disc'], elemento=e['id'], caixa=' + '.join(nomes), status='contorno em planta',
                        antigo=[list(map(float, p[:2])) for p in P], pontos=[list(map(float, p[:2])) for p in novo]))
        APLICADO.append(dict(tipo='contorno em planta', trecho=tr, obstaculos=nomes, acrescimo=round(float(LineString(novo[:, :2]).length - L.length), 2),
                             E=float(a.x), N=float(a.y)))
        log(f'  {tr} contorna {" + ".join(nomes)} pelo lado mais curto ({LineString(novo[:, :2]).length - L.length:+.2f} m)')
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


# traçado novo em planta (aplicar e avisar: desvio lateral até 2,00 m): o EL2-025 da iluminação está desenhado em cima do esgoto
# ESG-29/ESG-11 (CE-04 -> CE-03) por 17 m, atravessando as caixas CES-01, CE-04 e CE-03; passa paralelo, 0,90 m a sudeste do eixo do
# esgoto, e a EL2-CX02 vai para o mesmo lado da CE-03 (estava sobre o ESG-01). {trecho: [vértices UTM]}
_U = np.array([0.7606, 0.6492]); _N = np.array([0.6492, -0.7606]); _CE04 = np.array([567699.2, 8634680.0])
TRACADO_NOVO = {'EL2-025': [tuple(_CE04 + _U * -3.0 + _N * 0.70), tuple(_CE04 + _U * 9.0 + _N * 0.70)]}
CAIXA_NOVA_ROTA = {'ELE:EL2-CX02': tuple(_CE04 + _U * 10.2 + _N * 0.85)}


def _tracado_novo(E, C, log=print):
    fn = os.path.join(SAIDA, f'{SIGLA}_tracados_novos.json'); reg = []; regc = []
    for cid, novo in CAIXA_NOVA_ROTA.items():
        c = next((c for c in C if c['id'] == cid), None)
        if c is None: continue
        de = np.array([c['E'], c['N']]); v = np.array(novo) - de
        for e in E:
            if e['disc'] != c['disc'] or e['tipo'] != 'pressao' or e['trecho'] in TRACADO_NOVO: continue
            for k in (0, -1):
                if max(md.planta_local(c, *e['pts'][k, :2])) < 0.10:
                    e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = e['pts'].copy(); e['pts'][k, :2] += v; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
        c['E0'], c['N0'] = c['E'], c['N']; c['E'], c['N'] = float(novo[0]), float(novo[1])
        APLICADO.append(dict(tipo='caixa de passagem deslocada', caixa=cid.split(':', 1)[1], disc=c['disc'], desloc=round(float(np.hypot(*v)), 2),
                             E=float(de[0]), N=float(de[1])))
        regc.append(dict(caixa=cid.split(':', 1)[1], disc=c['disc'], elemento=cid, status='caixa deslocada', de=list(map(float, de)), E=c['E'], N=c['N'],
                         desloc=round(float(np.hypot(*v)), 2), lado=round(2 * c.get('mx', c['meia']), 3), lado_y=round(2 * c.get('my', c['meia']), 3),
                         rot=float(c.get('rot', 0.0)), forma=c['forma'], tubos=list(TRACADO_NOVO)))
        log(f'  {cid} vai para o traçado novo ({np.hypot(*v):.2f} m)')
    porn = {c['info'].get('nome'): c for c in C}
    for tr, meio in TRACADO_NOVO.items():
        e = next((e for e in E if e['trecho'] == tr and e['tipo'] == 'pressao'), None)
        if e is None: continue
        P = e['pts']; a, b = P[0], P[-1]
        # as pontas ficam nas caixas (que podem ter andado)
        def na_caixa(p):                     # a caixa pelo lugar original (ela pode ter andado acima)
            for c in C:
                c0 = dict(c, E=c.get('E0', c['E']), N=c.get('N0', c['N']))
                if c['disc'] == e['disc'] and not c['info'].get('equipamento') and max(md.planta_local(c0, *p[:2])) < 0.40: return np.array([c['E'], c['N']])
            return p[:2]
        A, B = na_caixa(a), na_caixa(b)
        Q = np.array([A] + [np.array(m) for m in meio] + [B])
        L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
        novo = np.column_stack([Q, a[2] + (b[2] - a[2]) * L / L[-1]])
        e.setdefault('pts_planta0', P.copy()); e['pts'] = novo; e['pts_sol'] = novo.copy(); e.pop('S', None)
        reg.append(dict(trecho=tr, disc=e['disc'], elemento=e['id'], caixa='', status='contorno em planta', antigo=[list(map(float, p[:2])) for p in P],
                        pontos=[list(map(float, p[:2])) for p in novo]))
        APLICADO.append(dict(tipo='traçado novo em planta', trecho=tr, E=float(Q[1][0]), N=float(Q[1][1]), desloc=0.70))
        log(f'  {tr}: traçado novo ao lado do esgoto')
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(regc, open(os.path.join(SAIDA, f'{SIGLA}_caixas_movidas_rota.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)


def _recuar(E, C, log=print):
    for nome, (tr, d) in RECUO.items():
        e = next((e for e in E if e['trecho'] == tr), None); h = next((c for c in C if c['info'].get('nome') == nome), None)
        if e is None or h is None: continue
        P = e['pts']; k = -1 if np.hypot(*(P[-1, :2] - [h['E'], h['N']])) < np.hypot(*(P[0, :2] - [h['E'], h['N']])) else 0
        j = -2 if k == -1 else 1; u = P[j, :2] - P[k, :2]; u = u / np.hypot(*u)
        e.setdefault('pts_planta0', P.copy()); e['pts'] = P.copy(); e['pts'][k, :2] += u * d; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
        h['E0'], h['N0'] = h['E'], h['N']; h['E'], h['N'] = float(e['pts'][k, 0]), float(e['pts'][k, 1])
        APLICADO.append(dict(tipo='hidrante recuado pelo ramal', caixa=nome, trecho=tr, desloc=d, E=h['E0'], N=h['N0']))
        log(f'  {nome} recua {d:.2f} m pelo {tr}')
CAIXA_NOVA = {'EQ:AF:RG-03': (567746.15, 8634631.74),     # caixa do registro RG-03 recua 1,2 m pelo AF-10 (estava sobre o DRE-223)
              # RG-01 encostava na CE-01: anda 0,15 m pelo próprio eixo (AF-02/AF-05 em linha), para o tê TE-8; as curvas seguem a 90°
              # (o deslocamento livre da ferramenta levava 0,28 m de lado e a curva do AF-02 ficava com 79,7°)
              'EQ:AF:RG-01': (567729.977, 8634705.716),
              'ELE:EL2-CX04': (567721.85, 8634671.38), 'ELE:EL2-CX08': (567676.27, 8634659.70), 'SDAI:CX-09': (567723.79, 8634672.28), 'SDAI:CX-12': (567730.85, 8634663.90)}


def _mover_manual(E, C, ter, log=print):
    fn = os.path.join(SAIDA, f'{SIGLA}_caixas_movidas_manual.json'); reg = []
    for cid, novo in CAIXA_NOVA.items():
        c = next((c for c in C if c['id'] == cid), None)
        if c is None: continue
        de = np.array([c['E'], c['N']]); v = np.array(novo) - de
        tubos = []
        for e in E:
            if e['disc'] != c['disc'] or e['tipo'] != 'pressao': continue
            for k in (0, -1):
                if max(md.planta_local(c, *e['pts'][k, :2])) < 0.10:
                    e.setdefault('pts_planta0', e['pts'].copy()); e['pts'] = e['pts'].copy(); e['pts'][k, :2] += v
                    e['pts_sol'] = e['pts'].copy(); e.pop('S', None); tubos.append(e['trecho'])
        c['E0'], c['N0'] = c['E'], c['N']; c['E'], c['N'] = float(novo[0]), float(novo[1])
        dz = float(ter.z([novo])[0] - ter.z([de])[0])
        if np.isfinite(dz): c['zt'] += dz
        reg.append(dict(caixa=cid.split(':', 1)[1], disc=c['disc'], elemento=cid, status='caixa deslocada', de=list(map(float, de)), E=c['E'], N=c['N'],
                        desloc=round(float(np.hypot(*v)), 2), lado=round(2 * c.get('mx', c['meia']), 3), lado_y=round(2 * c.get('my', c['meia']), 3),
                        rot=float(c.get('rot', 0.0)), forma=c['forma'], tubos=tubos))
        APLICADO.append(dict(tipo='caixa de passagem deslocada', caixa=cid.split(':', 1)[1], disc=c['disc'], desloc=round(float(np.hypot(*v)), 2),
                             E=float(de[0]), N=float(de[1]), tubos=tubos))
        log(f'  {cid} deslocada {np.hypot(*v):.2f} m; acompanham {", ".join(tubos)}')
    json.dump(reg, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)


def carregar():
    os.makedirs(SAIDA, exist_ok=True)
    APLICADO.clear()
    ter = Terreno(TERRENO)
    E = pressurizadas(ter)
    G, C = gravidade(ter)
    E += _sem_duplicados(G)
    ele = [e for e in E if e['disc'] == 'ELE']; sdai = [e for e in E if e['disc'] == 'SDAI']
    jn = json.load(open(os.path.join(REDE, 'ele_rede.json'), encoding='utf-8'))
    C += _caixas_pressao(jn['EL1']['nos'], 'ELE', 'ELE', ter, ele, {'CX': 0.80}, tipo_nome={'CX': 'caixa de passagem 80x80'})
    C += _caixas_pressao(jn['EL2']['nos'], 'ELE', 'ELE', ter, ele, {'CX': 0.60}, tipo_nome={'CX': 'caixa de passagem 60x60'})
    inc = json.load(open(os.path.join(REDE, 'inc_rede.json'), encoding='utf-8'))
    C += _caixas_pressao(inc['caixas_sdai'], 'SDAI', 'SDAI', ter, sdai, {'CX': 0.30}, tipo_nome={'CX': 'caixa de passagem do alarme'})
    Ceq, Eeq = equipamentos(ter, E)
    C += Ceq; E += Eeq
    _chegadas(E)
    E = _sem_soltos(E, C)
    _soldar_pontas(E)
    E, C = so_externo(E, C)
    C += EST.estrutura(ter, Terreno(TER_IMP))
    _aparar_sapatas(E, C)
    _mover_manual(E, C, ter)
    _recuar(E, C)
    _tracado_novo(E, C)
    _contornar_grupo(E, C)
    # ajustes em planta sobre os pares críticos da rodada anterior (catu/ifc/cat_pares.py -> CAT_ajustes_pares.json): caixas de
    # passagem deslocadas até 1,50 m com os eletrodutos, contornos curtos de PV/peça da estrutura, vértice fora de caixa (aplicar e avisar)
    fp = os.path.join(SAIDA, f'{SIGLA}_ajustes_pares.json')
    if os.path.exists(fp) and os.environ.get('CAT_SEM_AJUSTES') != '1':
        AJ = _mod('cat_ajustes', os.path.join(CATU, 'cat_ajustes.py'))
        J = json.load(open(fp, encoding='utf-8'))
        antes = {c['id']: (c['E'], c['N']) for c in C}
        AJ.mover_caixas(E, C, set(J['caixas']) - {k.split(':', 1)[1] for k in CAIXA_NOVA}, SAIDA, passo_max=1.50)
        _contornar_bancos(AJ, E, C, [tuple(x) for x in J['contornos']], ter)
        AJ.afastar_pontas(E, C, SAIDA)
        for c in C:                          # caixa que o ajuste deslocou: tampa no terreno do lugar novo
            a = antes.get(c['id'])
            if a and (abs(c['E'] - a[0]) + abs(c['N'] - a[1])) > 1e-6:
                dz = float(ter.z([[c['E'], c['N']]])[0] - ter.z([a])[0])
                if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
    REGRAS['estudo']['cob_fixo'] = {e['id']: COB_REDE[e['disc']] for e in E if e['disc'] in COB_REDE and e['tipo'] == 'pressao'}
    REGRAS['estudo']['cob_fixo'].update({e['id']: COB_TRECHO[e['id'].split('~')[0]] for e in E if e['id'].split('~')[0] in COB_TRECHO})
    _patches()
    json.dump(APLICADO, open(os.path.join(SAIDA, f'{SIGLA}_aplicado_carregamento.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas, terreno do IMP na base',
                               'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py): pranchas no padrão de executivo final
REVISAO = 'R03'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.30
EXECUTIVO_EXT = 1.0
EXECUTIVO_NOTA_ALT = (0.20, 0.50)       # nota nunca maior que as etiquetas do projetista (7,9 pt na AGF-001)
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1] if el.count(':') >= 1 else el
_PO = 'PROJETO_ORIGINAL/IMP/'
_DWG = {'AGF-001': _PO + '01_AF/24-049-CAU-RNV-ETIB-IMP-PE-AGF-001-R02.dwg',
        'ESG-001': _PO + '02_ESG/24-049-CAU-RNV-ETIB-IMP-PE-ESG-001-HIG-R02.dwg',
        'DRE-001': _PO + '03_DRE/24-049-CAU-RNV-ETIB-IMP-PE-DRE-001-DRG-R02.dwg',
        'EL-001': _PO + '04_ELE/24-049-CAU-RNV-ETIB-IMP-PE-EL-001-ELG-R05.dwg',
        'EL-002': _PO + '04_ELE/24-049-CAU-RNV-ETIB-IMP-PE-EL-002-ELG-R02.dwg',
        'INC-001': _PO + '05_PCI/24-049-CAU-RNV-ETIB-IMP-PE-INC-001-ING-R03.dwg'}


def folha(m):
    d = m['disc']; t = str(m.get('trecho') or '')
    if d == 'ELE': return 'EL-002' if t.startswith('EL2') else 'EL-001'
    return {'AF': 'AGF-001', 'ESG': 'ESG-001', 'DRE': 'DRE-001', 'HID': 'INC-001', 'SDAI': 'INC-001'}.get(d)


def executivo_dwg(m):
    return _DWG.get(m.get('folha') or folha(m))


def _transf(nome):
    j = json.load(open(os.path.join(BASE, 'CAD_GEORREFERENCIADO', nome), encoding='utf-8'))['rigid']     # UTM = local + t
    return (float(j['rot_deg']), tuple(j['t']))


TRANSF_DWG = {_DWG['AGF-001']: _transf('transformacao_AF_local_para_UTM.json'),
              _DWG['ESG-001']: _transf('transformacao_ESG_local_para_UTM.json'),
              _DWG['DRE-001']: _transf('transformacao_DRE_local_para_UTM.json'),
              _DWG['EL-001']: _transf('transformacao_EL1_local_para_UTM.json'),
              _DWG['EL-002']: _transf('transformacao_EL2_local_para_UTM.json'),
              _DWG['INC-001']: _transf('transformacao_INC_local_para_UTM.json')}
