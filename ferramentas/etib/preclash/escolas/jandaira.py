# -*- coding: utf-8 -*-
"""Adaptador da ETIB Jandaíra para o preclash — padrão novo (19/10/2026 noite, Anderson e Daniel), escola-piloto.
Modelo montado dos 5 JAN-*.rvt já extraídos (compat_R01/geo e geo_exec), sem abrir o Revit: FERRAMENTAS/jandaira/ifc/jan_modelo.py.
  - terreno do IMP levado às cotas da base (CT 147,50 das caixas de DRE/ESG nas pranchas e da SIT): correção local IDW;
  - gravidade (DRE, ESG) com as CT/CF/CS/CE das pranchas (FERRAMENTAS/jandaira/ifc/rotulos_grav.py); drenagem do campo 50x30
    descarregando a oeste na CX-43 (CF 146,49);
  - pressurizadas (AF, HID, SDAI, ELE) só com a planta; a cota sai do estudo (uma por rede na água; uma por trecho entre
    caixas na elétrica, com a elétrica acima da água), sem mergulho pontual: mudança de cota só dentro das caixas;
  - reservatório inferior de reúso (5,0 x 2,0 x 1,8 m, premissa da altura), equipamentos e estrutura as built (obstáculo);
  - gravidade × gravidade: desloca a caixa de DRE ou ESG (até 0,60 m) no cenário AD;
  - conexões comerciais (11,25°/22,5°/45°/90°) em toda mudança de direção acima de 5°.
Passo 7 (executivo/rever.py): as pranchas da implantação no padrão de executivo final (ver EXECUTIVO_* abaixo)."""
import os, sys, json, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\ifc')
from preclash.terreno import Terreno

ESCOLA = 'ETIB Jandaíra'
SIGLA = 'JAN'
BASE = r'D:\Projeto Modelagem\ETIB-JANDAIRA'
REL = os.path.join(BASE, 'RELATORIOS')
SAIDA = os.environ.get('JAN_SAIDA') or os.path.join(REL, 'PRECLASH_R02')     # JAN_SAIDA: rodada de teste em outra pasta
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'jandaira_terreno.npz')
ORIGEM = (631578.10, 8721003.57, 0.0)      # origem interna dos modelos JAN (AGENTS.md)
EPSG = 31984                               # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (631500.0, 8720950.0, 631700.0, 8721200.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],
    # 20/10 (Anderson): "se precisar pode aumentar profundidade também além do 1,5 m" -> o estudo pode ir a 2,00 m
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'dz_max': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00, 'AF': 2.00},
    'estudo': {
        'por_rede': ['AF', 'HID'],
        'por_trecho': ['ELE', 'SDAI'],
        'cob_min': {'AF': 0.30, 'HID': 0.60, 'ELE': 0.60, 'SDAI': 0.60},
        'prof_max': 2.00,
        'passo': 0.05,
        'acima': [('ELE', 'AF'), ('ELE', 'HID'), ('SDAI', 'AF'), ('SDAI', 'HID')],
        # 20/10 noite (troca de classes do IFC e barrilete): as redes ficam nas cotas da R03 entregue (pranchas já enviadas);
        # o eixo pelo maior diâmetro e a regra dos 3 m de bomba/tanque da ferramenta mudariam as cotas (AFP 1,30 -> 1,55 m).
        # O barrilete da casa de bombas já entra fixo pelo jan_modelo (info estudo=False).
        'eixo_maior_diametro': False,
        'fixar_perto_de': [],
    },
    'mergulho_local': False,
    'caixas_moveis_grav': ['DRE', 'ESG'],
    'desloc_max_grav': 0.60,
    'contornos': False,
    # 21/10/2026 (Anderson): peças comerciais 45° e 90° (+ tês e junções); elétrica/alarme em eletroduto flexível e hidrante em PEAD curvam no tubo até 30°
    'conexoes': {'angulos': [45.0, 90.0], 'flexivel': 5.0, 'tol': 3.0, 'flexivel_disc': {'ELE': 30.0, 'SDAI': 30.0, 'HID': 30.0}},
}
# reúso: com 0,80 m a elétrica (recobrimento mínimo 0,60 m) não cabe por cima com 20 cm de folga e ficava por baixo em 31 cruzamentos;
# com mínimo de 0,90 m o estudo leva o reúso a 1,50 m (0 colisões) e os críticos caem de 43 para 27 (teste_variantes.py, 19/10 noite)
COB_REDE = {'AR': 0.90}
# cotas congeladas na R03 entregue (Pset PRECLASH 'recobrimento_estudo' do federado entregue, IFC_R03 = rodada de 20/10 manhã); JAN_COB_FIXO='' desliga
_cf = os.environ.get('JAN_COB_FIXO', os.path.join(REL, 'IFC_R03', 'JAN_R03_FEDERADO.ifc'))
if _cf and os.path.exists(_cf):
    from preclash import estudo as _est0
    REGRAS['estudo']['cob_fixo'] = _est0.cobs_de_ifc(_cf)
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI'), 'EST': ('EST',)}
NOMES_DISC = {'AF': 'Água fria (alimentação, potável e reúso)', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial (implantação e campo)',
              'ELE': 'Elétrica enterrada (BT, iluminação externa e campo)', 'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)',
              'EST': 'Estrutura as built (obstáculo)'}


class _ter_perfil:
    """terreno para o PERFIL das pressurizadas com os rebaixos estreitos preenchidos (fechamento morfológico de 11 m numa grade de 1 m):
    a área rebaixada junto do BP4 (piso 146,88, 0,62 m abaixo do entorno, ~6 x 18 m) fazia o AR-12 inteiro descer 0,62 m para manter
    o recobrimento lá dentro e ficar a 2,17 m do terreno no resto. Com o preenchimento a rede passa no recobrimento do entorno e fica
    com 0,88 m sob o piso rebaixado. Degrau entre platôs não muda (o fechamento só enche vale).
    folga (20/10, verificação da ferramenta: o ELE-I-24 ficou 7 a 11 cm ACIMA do piso rebaixado): o preenchimento vale no máximo
    recobrimento escolhido − recobrimento mínimo da rede, então o topo nunca fica a menos do mínimo do terreno real. A elétrica no
    mínimo (0,60 m) acompanha o rebaixo; a água a 1,30–1,50 m passa reta por cima dele."""
    delta = None

    def __init__(self, ter, folga=np.inf):
        self.ter = ter; self.folga = max(0.0, float(folga))
        if _ter_perfil.delta is None:
            x0, y0, x1, y1 = CAIXA_OBRA; xs = np.arange(x0, x1 + 0.5, 1.0); ys = np.arange(y0, y1 + 0.5, 1.0)
            X, Y = np.meshgrid(xs, ys); Z = np.array(ter.z(np.c_[X.ravel(), Y.ravel()]), float).reshape(X.shape)
            ok = np.isfinite(Z); Zf = np.where(ok, Z, np.nanmin(Z))
            def filtro(A, f, r=5):
                P = np.pad(A, r, mode='edge'); out = A.copy()
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        out = f(out, P[r + dy:r + dy + A.shape[0], r + dx:r + dx + A.shape[1]])
                return out
            C = filtro(filtro(Zf, np.maximum), np.minimum)
            _ter_perfil.delta = (xs, ys, np.where(ok, np.maximum(C - Zf, 0.0), 0.0))

    def z(self, Q):
        Q = np.atleast_2d(np.asarray(Q, float)); z = np.array(self.ter.z(Q), float)
        xs, ys, D = _ter_perfil.delta
        fx = np.clip((Q[:, 0] - xs[0]) / 1.0, 0, len(xs) - 1.001); fy = np.clip((Q[:, 1] - ys[0]) / 1.0, 0, len(ys) - 1.001)
        i, j = fx.astype(int), fy.astype(int); u, v = fx - i, fy - j
        d = D[j, i] * (1 - u) * (1 - v) + D[j, i + 1] * u * (1 - v) + D[j + 1, i] * (1 - u) * v + D[j + 1, i + 1] * u * v
        return z + np.minimum(d, self.folga)

    def __getattr__(self, k):
        return getattr(self.ter, k)


JM_BARRILETE = ('PCI-AF',)          # = jan_modelo.BARRILETE


def congelar(E, C, fn=None):
    """traçado em planta e cota da gravidade e caixas como na R03 entregue (IFC_R03/JAN_R03_preclash.json, cópia do JAN.json da
    rodada de 20/10 manhã). Os ajustes do adaptador (cota da gravidade em bloco, caixas, contornos, mover_ele) partem dos críticos
    da rodada anterior e não se repetem iguais: rodar de novo mudava DRE-106/131/140 em 0,40 m. JAN_CONGELAR='' desliga.
    Elemento ou caixa que não existia na R03 (barrilete da casa de bombas, peças) fica como o jan_modelo montou."""
    fn = os.environ.get('JAN_CONGELAR', os.path.join(REL, 'IFC_R03', 'JAN_R03_preclash.json')) if fn is None else fn
    if not fn or not os.path.exists(fn): return
    J = json.load(open(fn, encoding='utf-8')); o = np.array(ORIGEM[:2]); zr = J['zref']
    # o JSON da R03 tem id repetido (PCI-AH-05 e PCI-AH-08: trecho longo + pedaço até o hidrante com o mesmo id): casa pela
    # ordem — a 1ª ocorrência com o id sem sufixo, a 2ª com '#2' (o jan_modelo agora numera as cadeias do mesmo trecho)
    el = {}
    for r in J['elementos']:
        k = r['id']; n = 1
        while (k if n == 1 else f'{k}#{n}') in el: n += 1
        el[k if n == 1 else f'{k}#{n}'] = r
    cx = {c['id']: c for c in J['caixas']}
    ne = nc = 0
    for e in E:
        r = el.get(e['id'])
        # barrilete da casa de bombas: na R03 entrou achatado (0,60 m); agora vem do modelo em 3D — o id de um tubo de um
        # pedaço só coincide com o da R03 e o congelamento o devolvia à cota antiga (PCI-AF-S03, S04, S06c, S08b)
        if r is None or str(e['trecho']).startswith(JM_BARRILETE): continue
        P = np.array(r['p'], float); P[:, :2] += o; P[:, 2] += zr
        e['pts'] = P; e['pts_sol'] = P.copy(); e.pop('S', None); ne += 1
    for c in C:
        r = cx.get(c['id'])
        if r is None: continue
        c['E'], c['N'] = r['x'] + o[0], r['y'] + o[1]; c['zb'], c['zt'] = r['zb'] + zr, r['zt'] + zr; c['meia'] = r.get('m', c['meia'])
        if c['forma'] == 'r' and 'rot' in r: c['rot'], c['mx'], c['my'] = r['rot'], r['mx'], r['my']
        nc += 1
    print(f'  congelado na R03 entregue: {ne} trechos e {nc} caixas ({os.path.basename(fn)})')


def materiais_gravidade(E):
    """material de cada trecho de DRE/ESG no info (IFC): etiqueta do trecho na prancha ou a especificação pelo diâmetro."""
    import materiais_grav as MG
    T = _transf(utm=True)
    C = MG.materiais(E, {k: T[_DWG[k]] for k in ('DRE-001', 'CPS-DRE-001', 'ESG-001')})
    n = 0
    for e in E:
        if e['id'] in C: e['info']['material'], e['info']['material_fonte'] = C[e['id']]; n += 1
    print(f'  material da drenagem/esgoto em {n} trechos')


def costurar(E, C, log=print):
    """vãos de dado (20/10, verificação de continuidade do IFC): o contorno curto e as junções deslocadas deixaram pontas a
    16–94 cm da ponta seguinte da mesma rede, na mesma cota (AL-07 -> AL-07.b, AFP-04 -> AFP-04.b, DRE-122 -> V83 sob o BP4). A ponta solta ganha um
    vértice na ponta vizinha (só planta; a cota sai do estudo). Ponta a menos de 1 m de uma caixa da disciplina e fora dela vai
    até o centro da caixa (ELE-CPS-01 -> CX-C07). Barrilete, ponta já ligada (5 cm) e derivação ficam como estão."""
    press = [e for e in E if e['tipo'] in ('pressao', 'gravidade') and not str(e['trecho']).startswith(JM_BARRILETE)]
    cx_disc = [c for c in C if c['disc'] in ('ELE', 'SDAI', 'AF', 'DRE', 'ESG') and not c['info'].get('equipamento')]
    cxs = [c for c in C if c['disc'] in ('ELE', 'SDAI', 'AF') and not c['info'].get('equipamento') and 'reservat' not in str(c['info'].get('tipo', ''))]
    feitos = []
    for e in press:
        if e['trecho'] not in COSTURA: continue
        for k in (0, -1):
            p = e['pts'][k]
            outras = [(float(np.hypot(*(o['pts'][j][:2] - p[:2]))), o, j) for o in press if o is not e and o['rede'] == e['rede'] for j in (0, -1)]
            if any(d < 0.05 for d, _, _ in outras): continue
            meio = False
            for o in press:
                if o is e or o['rede'] != e['rede']: continue
                for a, b in zip(o['pts'][:-1], o['pts'][1:]):
                    dv = b[:2] - a[:2]; L2 = float(dv @ dv)
                    t = 0.0 if L2 < 1e-12 else float(np.clip((p[:2] - a[:2]) @ dv / L2, 0, 1))
                    if 0.01 < t < 0.99 and np.hypot(*(a[:2] + dv * t - p[:2])) < 0.05: meio = True; break
                if meio: break
            if meio: continue
            dentro = [c for c in cx_disc if c['disc'] == e['disc'] and max(md_planta(c, p)) < 0.02]
            if dentro: continue
            tz = 0.10 if e['tipo'] == 'pressao' else 0.05      # pressurizada: a cota ainda sai do estudo (diâmetros diferentes)
            sobre = lambda q: min(float(np.hypot(*(a[:2] + (b[:2] - a[:2]) * np.clip((q[:2] - a[:2]) @ (b[:2] - a[:2]) / max((b[:2] - a[:2]) @ (b[:2] - a[:2]), 1e-12), 0, 1) - q[:2])))
                                  for a, b in zip(e['pts'][:-1], e['pts'][1:]))
            # nunca ligar a uma ponta que fica sobre o próprio trecho nem a um vizinho já ligado na outra ponta dele
            cand = [(d, o, j) for d, o, j in outras if d <= 1.0 and abs(o['pts'][j][2] - p[2]) < tz and sobre(o['pts'][j]) > 0.05
                    and not any(np.hypot(*(o['pts'][jj][:2] - e['pts'][-1 - k if k == 0 else 0][:2])) < 0.05 for jj in (0, -1))]
            if cand:
                d, o, j = min(cand, key=lambda x: x[0]); q = o['pts'][j].copy(); alvo = o['trecho']
            else:
                if e['tipo'] != 'pressao': continue
                perto = [(float(np.hypot(c['E'] - p[0], c['N'] - p[1])), c) for c in cxs if c['disc'] == e['disc'] and max(md_planta(c, p)) < 1.0]
                if not perto: continue
                d, c = min(perto, key=lambda x: x[0]); q = np.array([c['E'], c['N'], p[2]]); alvo = c['id']
            e['pts'] = np.vstack([q[None], e['pts']]) if k == 0 else np.vstack([e['pts'], q[None]])
            e['pts_sol'] = e['pts'].copy(); e.pop('S', None); feitos.append(f"{e['trecho']} -> {alvo} ({d:.2f} m)")
    log(f'  costura de vãos de dado: {len(feitos)} ponta(s): ' + '; '.join(feitos))


# só os trechos que a verificação do IFC de 20/10 apontou como vão de dado (o resto das pontas a menos de 1 m é ligação real,
# derivação, chegada em quadro ou é fechado pela costura da própria ferramenta, até 15 cm)
# (a 1ª versão também ligava AL-07/11/16, AL-23.b, AFP-02.b, AFP-04 e ELE-CPS-01, mas a ponta "vizinha" deles era a continuação
# do próprio trecho partido no contorno: o tubo ia e voltava sobre si — Revisão de 20/10 23h13; são fim de ramal, ver ESPERADA)
COSTURA = {'AL-10', 'AL-25.J1', 'AL-25.J2'}


def aprovados_20_10(E, log=print, C_=None):
    """decisões do Anderson em 20/10/2026 (20h56, "Sim" às três propostas da verificação do IFC):
    1) ELE-I-31 inteiro a 0,85 m (o trecho tinha 0,65 e 0,85 m sem caixa no meio: a caixa andou na solução);
    2) junção V81 sob o BP4: a DRE-117 chegava 0,25 m abaixo do início da DRE-121 — a 121, a 122, a 124 e a 135 (que leva à CX-32)
       descem para continuar a 117 com caimento: 121 e 122 a 1 %, 124 a ~0,5 % (para a 135 chegar na CX-32 no CF 146,14 a 1 %);
       pendência para o projetista de drenagem junto com a do BP4;
    3) DRE-031 (canaleta sul do campo -> CX-14) e DRE-046 (CX-25 -> CX-26) voltam às cotas da prancha DRE-001: chegam no CE da
       caixa (146,83 / 146,78) a 1 % (no IFC entregue chegavam 0,46 / 0,38 m abaixo do fundo das caixas)."""
    cf = REGRAS['estudo'].get('cob_fixo')
    if cf is not None:
        for e in E:
            if str(e['trecho']).startswith('ELE-I-31.'): cf[e['id']] = 0.85
            # com a DRE-031 e a DRE-046 de volta às cotas do projeto, o ELE-I-12 e o alarme PCI-EL-01b/03 batiam nelas (a drenagem
            # tinha sido rebaixada no lugar deles): pela regra, quem muda é a elétrica/alarme — o estudo escolhe de novo a cota
            # desses trechos (entre caixas), o resto fica na R03
            if str(e['trecho']).startswith(('ELE-I-12', 'PCI-EL-01', 'PCI-EL-03')): cf.pop(e['id'], None)
    G = {e['trecho']: e for e in E if e['disc'] == 'DRE'}

    def L(e): return float(np.sum(np.hypot(*np.diff(e['pts'][:, :2], axis=0).T)))

    def grav(e, i0, i1):
        P = e['pts']; S = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P[:, :2], axis=0).T))])
        P[:, 2] = i0 + (i1 - i0) * S / max(S[-1], 1e-6) + e['de'] / 2; e['pts_sol'] = P.copy(); e.pop('S', None)
        e['info']['cota'] = 'ajuste aprovado em 20/10/2026 (verificação do IFC)'
        log(f"  {e['trecho']}: GI {i0:.3f} -> {i1:.3f} ({(i0 - i1) / max(L(e), 1e-6) * 100:.2f} %)")
    if all(k in G for k in ('DRE-117', 'DRE-121', 'DRE-122', 'DRE-124', 'DRE-135')):
        e117 = G['DRE-117']; v81 = float(e117['pts'][-1, 2] - e117['de'] / 2)
        v83 = v81 - 0.01 * L(G['DRE-121']); grav(G['DRE-121'], v81, v83)
        grav(G['DRE-122'], v83 + 0.01 * L(G['DRE-122']), v83)
        # CF da CX-32: 146,14 na prancha; JAN_CX32_CF testa a caixa mais funda para a DRE-135 passar sob a AL-04 (opção a)
        cx32 = float(os.environ.get('JAN_CX32_CF') or 145.90); v85 = cx32 + 0.01 * L(G['DRE-135'])     # 145,90: opção (a) do Anderson, 20/10 22h21
        if cx32 < 146.14:
            for c in C_ or []:
                if c['id'] == 'DRE:CX-32': c['zb'] = min(c['zb'], cx32 - 0.10); log(f"  CX-32: fundo a {cx32 - 0.10:.2f} (CF {cx32:.2f})")
        grav(G['DRE-124'], v83, v85); grav(G['DRE-135'], v85, cx32)
    for t, ce in (('DRE-031', 146.83), ('DRE-046', 146.78)):
        if t in G: grav(G[t], ce + 0.01 * L(G[t]), ce)


def acabamento_20_10(E, C, log=print):
    """acabamento pedido pela Revisão de qualidade (20/10, 23h13), só no IFC (nenhuma cota de prancha muda):
    - caixa de registro da AF (premissa "topo no terreno"): topo no terreno do IFC (a AGF (44,3; 4,0) sobrava 6 cm);
    - drenagem do campo: a DRE-CPS-E13 começava 5,3 cm acima do fim da DRE-CPS-E12 (subia) e o dreno DRE-CPS-D06 chegava 5 cm
      abaixo do coletor E06/E07 — a ponta passa à cota do vizinho."""
    T_ = Terreno(TERRENO)
    for c in C:
        if c['disc'] == 'AF' and str(c['info'].get('cota', '')).startswith('topo no terreno; 0,45'):
            zt = float(T_.z([[c['E'], c['N']]])[0])
            if np.isfinite(zt): c['zt'], c['zb'] = zt, zt - 0.45
    G = {e['trecho']: e for e in E if e['disc'] == 'DRE'}
    if 'DRE-CPS-E12' in G and 'DRE-CPS-E13' in G:
        e = G['DRE-CPS-E13']; e['pts'][0, 2] = G['DRE-CPS-E12']['pts'][-1, 2]; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    if 'DRE-CPS-D06' in G and 'DRE-CPS-E07' in G:
        e = G['DRE-CPS-D06']; o = G['DRE-CPS-E07']
        e['pts'][-1, 2] = o['pts'][0, 2] - o['de'] / 2 + e['de'] / 2; e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    log('  acabamento: tampas das caixas de registro da AF no terreno; E13 e D06 na cota do vizinho')


def md_planta(c, p):
    from preclash import modelo as _md
    return _md.planta_local(c, p[0], p[1])


# itens da verificação de continuidade que são reais (não erro de dado): (tipo, trecho) -> motivo; a ferramenta marca 'esperado'
VERIFICACAO_ESPERADA = {
    ('ponta solta', 'ELE-F-01'): 'chegada na subestação (SB3)',
    ('ponta solta', 'ELE-F-03.1'): 'saída do QGBT: os bancos F-03 (1,30 m) e F-04 (1,00 m) sobem no quadro',
    ('ponta solta', 'ELE-F-04.1'): 'saída do QGBT: os bancos F-03 (1,30 m) e F-04 (1,00 m) sobem no quadro',
    ('ponta solta', 'ELE-F-21'): 'chegada no QDLT-CAMPO (subida no quadro)',
    ('ponta solta', 'ELE-CPS-04'): 'saída do QDLT-CAMPO (subida no quadro)',
    ('ponta solta', 'ELE-CPS-04b'): 'saída do QDLT-CAMPO (subida no quadro)',
    ('degrau', 'ELE-F-03.11'): 'mudança de cota no pé do quadro/poste (equipamento), não no meio do trecho',
    ('ponta solta', 'PCI-EL-02'): 'entrada do alarme no bloco BP4',
    ('ponta solta', 'ESG-24'): 'saída de esgoto da edificação (BP4)',
    ('ponta solta', 'DRE-129'): 'queda de 0,15 m na junção sob o BP4 (pendência 1 do projetista de drenagem)',
    ('ponta solta', 'DRE-122'): 'início do ramal (ponta de montante V84), como no modelo do projeto',
    ('pedaço curto', 'PCI-AF-S03'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S05b'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S06'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S06a'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S06b'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S08a'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S08b'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S06c'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S08'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S08c'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S07'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S07a'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-S07b'): 'niple entre válvulas no barrilete',
    ('pedaço curto', 'PCI-AF-D03a'): 'niple entre válvulas no barrilete',
    ('ponta solta', 'AL-07'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'AL-11'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'AL-16'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'AL-23.b'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'AFP-02.b'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'AFP-04'): 'fim do ramal (a ponta mais perto é a continuação do próprio trecho, partido no contorno)',
    ('ponta solta', 'ELE-CPS-01'): 'chegada no poste/quadro do campo (subida)',
    ('pedaço curto', 'DRE-CPS-E11'): 'trecho de 31 cm entre duas derivações dos drenos do campo (DRE-CPS-D02 e D01)',
}


def _ligar_fixos(E, log=print):
    """refaz a ligação vertical entre os trechos fixos (barrilete da casa de bombas) e os estudados: a regra da ferramenta liga
    TODA ponta fixa a menos de 10 cm em planta de uma ponta estudada, e as peças verticais do barrilete (V01a, V01b, V01c, as
    duas pontas no mesmo ponto em planta) ganhavam seis descidas de 0,66 a 2,81 m. Aqui cada ponta estudada liga só a ponta fixa
    mais próxima em cota (o pé da descida V01c)."""
    fix = [e for e in E if e['tipo'] == 'pressao' and e['info'].get('estudo') is False]
    for e in fix:
        if e['info'].pop('subida_estudo', None) and 'pts_projeto' in e:
            e['pts'] = e['pts_projeto'].copy(); e['pts_sol'] = e['pts'].copy(); e.pop('S', None)
    for o in [e for e in E if e['tipo'] == 'pressao' and isinstance(e.get('estudo'), dict)]:
        for j in (0, -1):
            q = o['pts'][j]
            cand = [(abs(e['pts'][k][2] - q[2]), e, k) for e in fix if e['rede'] == o['rede'] for k in (0, -1)
                    if np.hypot(*(e['pts'][k][:2] - q[:2])) < 0.10]
            if not cand: continue
            dz, e, k = min(cand, key=lambda x: x[0])
            if dz < 0.02: continue
            p = e['pts'][k]; add = np.array([[p[0], p[1], q[2]], [q[0], q[1], q[2]]])
            e['pts'] = np.vstack([add[::-1], e['pts']]) if k == 0 else np.vstack([e['pts'], add])
            e['pts_sol'] = e['pts'].copy(); e.pop('S', None); e['info']['subida_estudo'] = 'sim'
            log(f"  {e['trecho']}: fica na cota do modelo; descida/subida de {dz:.2f} m até {o['trecho']}")


def carregar():
    import jan_modelo as JM
    T, aj, n = JM.terreno(TERRENO)
    print(f'  terreno: {n} pontos (IMP + correção às CT das pranchas, mediana {aj.med:+.2f} m)')
    E, C, _ = JM.montar()
    import jan_ajustes
    import jan_ajustes2
    T0 = Terreno(TERRENO)
    jan_ajustes.ajustar(E, C, REGRAS)          # caixas e junções de DRE/ESG fora de pilar/sapata e uma da outra (até 0,60 m; 1,50 m no pilar)
    # 20/10 ("Sim. Tudo"): cota da gravidade em bloco sobre/sob sapata, viga e cruzamentos; postes; caixas até 1,50 m
    # DRE-032: o início (pé da descida da guarita) fica entre a sapata e a sapata corrida; posição livre 1,20 m a leste (busca_posicao.py)
    jan_ajustes2.forcar_juncoes(E, {(631622.80, 8721028.01): (1.20, 0.0)})
    jan_ajustes2.cota_grav(E, C, REGRAS, T0)
    jan_ajustes.mover_ele(E, C, REGRAS, passo_max=2.50, extra=jan_ajustes2.caixas_extra(), ref=jan_ajustes2.ref_press(), refzb=jan_ajustes2.ref_zb())
    # CX-F10 e CX-I33: o ramal raso de drenagem passa pelo fundo; posição livre a 0,2-0,3 m (busca_posicao.py sobre a rodada 7)
    jan_ajustes2.forcar_caixas(E, C, {'CX-F10': (-0.20, -0.20), 'CX-I33': (0.05, -0.20)})
    jan_ajustes2.mover_postes(E, C, REGRAS)
    for c in C:
        if 'E0' in c:
            dz = float(T0.z([[c['E'], c['N']]])[0] - T0.z([[c['E0'], c['N0']]])[0])
            if np.isfinite(dz): c['zt'] += dz; c['zb'] += dz
    ex = os.path.join(SAIDA, 'contornar_extra.json')
    jan_ajustes.contornar(E, C, extra=json.load(open(ex, encoding='utf-8')) if os.path.exists(ex) else ())   # contorno curto em planta
    congelar(E, C)
    materiais_gravidade(E)
    # 21/10/2026 (Anderson: "Sim, flexível"): elétrica e alarme enterrados em eletroduto FLEXÍVEL; a curva até 30° fica no próprio tubo.
    # Material conforme as pranchas: legenda da EL-001/EL-002 ("Eletroduto em PVC corrugado flexível embutido no contrapiso") e
    # da IN-001 R03 ("Eletroduto embutido no contrapiso para SDAI em PEAD, Ø2"). O modelo do Revit trazia o tipo padrão "Rígido PVC Roscável".
    for e in E:
        if e['tipo'] != 'pressao': continue
        if e['disc'] == 'ELE': e['info']['material'] = 'Eletroduto PVC corrugado flexível'
        elif e['disc'] == 'SDAI': e['info']['material'] = 'Eletroduto PEAD flexível'
    costurar(E, C)
    aprovados_20_10(E, C_=C)
    acabamento_20_10(E, C)
    # perfil das pressurizadas colado ao terreno (desvio de 5 cm em vez de 20 cm no Douglas-Peucker do estudo): sem isso a rede
    # afunda até 20 cm no meio do vão e a elétrica encosta na água nos cruzamentos (resíduos de 1 a 4 cm na rodada de 19/10)
    from preclash import estudo as _est, leitura as _lei, desvio as _dsv
    # o limite do preenchimento do rebaixo vale só para o ELE-I-24 (o único que a verificação pegou acima do piso rebaixado); o resto
    # fica como na R03 entregue
    _est._perfil = lambda e, cob, ter: _lei.perfil_por_recobrimento(
        e['pts'][:, :2], e['de'], cob, _ter_perfil(ter, (cob - (e.get('cob_min') or 0.30) - 0.05) if str(e['trecho']).startswith('ELE-I-24') else np.inf),
        desvio=0.05)
    if not getattr(_est, '_jan', False):
        _estudar, _mover = _est.estudar, _dsv.mover_caixas

        def estudar(E_, C_, R_, ter_, log=print):
            # depois do estudo, o fundo da caixa de passagem/registro desce até 10 cm abaixo do eletroduto/tubo mais fundo que chega nela
            rel = _estudar(E_, C_, R_, ter_, log)
            _ligar_fixos(E_, log)
            for c in C_:
                if c['disc'] not in ('ELE', 'SDAI', 'AF') or c['info'].get('equipamento') or c['info'].get('tipo') == 'reservatório enterrado': continue
                L = JM.ligados(c, E_)
                if L: c['zb'] = min(c['zb'], min(float(e['pts'][k, 2]) - e['de'] / 2 for e, k in L) - 0.10)
            return rel

        def mover_caixas(E_, C_, pend, R_, log=print):
            # só colisão de fato (não folga curta), e poste/quadro/abrigo não andam (a prancha não move equipamento)
            eq = {c['id'] for c in C_ if c['info'].get('equipamento')}
            antes = {c['id']: (c['E'], c['N']) for c in C_}
            out = _mover(E_, C_, [p for p in pend if p['folga'] < -0.002 and p['a'] not in eq and p['b'] not in eq], R_, log)
            T_ = Terreno(TERRENO)
            for c in C_:                 # caixa de passagem que andou: topo no terreno do lugar novo
                if c['disc'] in ('ELE', 'SDAI', 'AF') and (c['E'], c['N']) != antes[c['id']]:
                    dz = float(T_.z([[c['E'], c['N']]])[0] - T_.z([list(antes[c['id']])])[0])
                    if np.isfinite(dz): c['zt'] += dz; c['zb'] = min(c['zb'] + dz, c['zb'])
            return out
        _custo = _est.custo
        from preclash import clash as _cl, modelo as _md

        def custo(cand, outros, caixas, regras, cfg, disc, futuros=None, ter=None):
            # elétrica/SDAI: a cota do trecho também desce o fundo das caixas das pontas; conta o que a caixa mais funda passa a pegar
            c, nc, nk = _custo(cand, outros, caixas, regras, cfg, disc, futuros, ter)
            if disc not in ('ELE', 'SDAI'): return c, nc, nk
            folga = regras['folga']; oA, oB, oR, oD = outros; novo = {}
            for e, P in cand:
                for k in (0, -1):
                    for b in caixas:
                        if b['disc'] != disc or b['info'].get('equipamento'): continue
                        qx, qy = _md.planta_local(b, P[k, 0], P[k, 1])
                        if qx < 0.10 and qy < 0.10: novo[b['id']] = min(novo.get(b['id'], b['zb']), float(P[k, 2]) - e['de'] / 2 - 0.10)
            cr = ct = 0
            for b in caixas:
                if b['id'] not in novo or novo[b['id']] >= b['zb'] - 1e-6: continue
                b2 = dict(b, zb=novo[b['id']]); m = b['meia'] + folga
                if len(oA):
                    sel = ((np.minimum(oA[:, 0], oB[:, 0]) - oR <= b['E'] + m) & (np.maximum(oA[:, 0], oB[:, 0]) + oR >= b['E'] - m) &
                           (np.minimum(oA[:, 1], oB[:, 1]) - oR <= b['N'] + m) & (np.maximum(oA[:, 1], oB[:, 1]) + oR >= b['N'] - m) &
                           (np.minimum(oA[:, 2], oB[:, 2]) - oR <= b['zt']) & (np.maximum(oA[:, 2], oB[:, 2]) + oR >= b2['zb'] - folga) & (oD != disc))
                    for i in np.nonzero(sel)[0]:
                        Q = _cl.amostra(np.array([oA[i], oB[i]]), 0.05)
                        s1 = float(np.min(_cl.sd_caixa(Q, b2))) - oR[i]; s0 = float(np.min(_cl.sd_caixa(Q, b))) - oR[i]
                        if s1 < _cl.TOL <= s0: cr += 1
                        elif s1 < folga <= s0: ct += 1
                for o in caixas:
                    if o['disc'] == disc or abs(o['E'] - b['E']) > 4 or abs(o['N'] - b['N']) > 4: continue
                    f1 = _cl.folga_caixas(b2, o)[0]; f0 = _cl.folga_caixas(b, o)[0]
                    if f1 < _cl.TOL <= f0: cr += 1
                    elif f1 < folga <= f0: ct += 1
            # 20/10: a liberação além de 1,50 m vale para a água e o hidrante; a elétrica/SDAI fica até 1,50 m e SEMPRE por cima da água
            # (rodada 7: com 2,00 m livres a elétrica desceu a 1,80 m e passou por baixo da água em 12 cruzamentos)
            pen = 0
            for e, P in cand:
                Q = _cl.amostra(P, 0.5); zt = np.array(ter.z(Q[:, :2]), float); ok = np.isfinite(zt)
                if ok.any() and float(np.max(zt[ok] - Q[ok, 2] - e['de'] / 2)) > 1.51: pen += 1000
            if len(oA):
                agua = np.isin(oD, ['AF', 'HID'])
                for e, P in cand:
                    for a, b_ in zip(P[:-1], P[1:]):
                        j = np.nonzero(agua & (np.minimum(oA[:, 0], oB[:, 0]) - 0.3 <= max(a[0], b_[0])) & (np.maximum(oA[:, 0], oB[:, 0]) + 0.3 >= min(a[0], b_[0]))
                                       & (np.minimum(oA[:, 1], oB[:, 1]) - 0.3 <= max(a[1], b_[1])) & (np.maximum(oA[:, 1], oB[:, 1]) + 0.3 >= min(a[1], b_[1])))[0]
                        if not len(j): continue
                        d, C1, C2 = _cl.dist_seg_seg(np.repeat(a[None], len(j), 0), np.repeat(b_[None], len(j), 0), oA[j], oB[j])
                        cruza = np.hypot(C1[:, 0] - C2[:, 0], C1[:, 1] - C2[:, 1]) < e['de'] / 2 + oR[j] + 0.05
                        pen += 100 * int(np.sum(cruza & (C1[:, 2] - e['de'] / 2 < C2[:, 2] + oR[j] + folga)))
            return c + 10 * cr + ct + pen, nc + cr, nk + ct
        _est.estudar, _est.custo, _dsv.mover_caixas, _est._jan = estudar, custo, mover_caixas, True
    cob_rede = json.loads(os.environ.get('JAN_COB_REDE', '{}') or '{}') or COB_REDE
    for e in E:
        if e['tipo'] == 'pressao' and e['rede'] in cob_rede: e['cob_min'] = max(e['cob_min'] or 0, cob_rede[e['rede']])
    ter = Terreno(TERRENO)
    return {'elementos': E, 'caixas': C, 'terreno': ter,
            'cenarios': {'A': {'nome': 'padrão novo: estudo de cota das pressurizadas, gravidade das pranchas', 'excluir': lambda e: False}}}


# ---------------- passo 7 (executivo/rever.py): pranchas no padrão de executivo final
REVISAO = 'R02'
EXECUTIVO_TEXTO = 0.30
EXECUTIVO_TOL = 0.08          # IN-001 casa com mediana de 6 mm e a elétrica com 1 mm; 8 cm separa redes paralelas
EXECUTIVO_EXT = 2.0           # caixas do modelo do Daniel até ~1 m fora do vértice da prancha
EXECUTIVO_CAIXA_SEM_SIMBOLO = True   # EL-002: a caixa é só o texto "Cx. 80x80 cm" no vértice do eletroduto
EXECUTIVO_NOTA_ALT = (0.25, 0.60)    # notas na altura das etiquetas de rede (0,35 a 0,50 m), não na do texto miúdo dos quadros
EXECUTIVO_FAMILIA = lambda el: el.split(':')[1].rsplit('.', 1)[0] if el.startswith('ELE:') else el   # 'ELE:ELE-F-03.1:id' -> ELE-F-03 (uma nota)

_DWG = {'EL-001': 'PROJETO_ORIGINAL/IMP/04_ELE/24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R01.dwg',
        'EL-002': 'PROJETO_ORIGINAL/IMP/04_ELE/24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R01.dwg',
        'AF-001': 'PROJETO_ORIGINAL/IMP/01_AF/24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R01.dwg',
        'IN-001': 'PROJETO_ORIGINAL/IMP/05_PCI/24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R03.dwg',
        'ESG-001': 'PROJETO_ORIGINAL/IMP/02_ESG/24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R01.dwg',
        'CPS-EL-001': 'PROJETO_ORIGINAL/CPS/04_ELE/24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R01.dwg',
        # drenagem: a base é a prancha já com a rede do campo 50x30 (jan_dre_exec.py), copiada com o nome do original
        'DRE-001': 'RELATORIOS/EXECUTIVO_R02_IFC/_base/24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg',
        'CPS-DRE-001': 'RELATORIOS/EXECUTIVO_R02_IFC/_base/24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dwg'}


def executivo_dwg(m):
    return _DWG.get(m.get('folha'))


def _transf(utm=None):
    """DWG -> interno dos modelos (exe_transf.py, rotulos_grav.py e georreferenciamento do CPS); com PRECLASH_UTM=1, DWG -> UTM."""
    J = json.load(open(os.path.join(REL, 'EXECUTIVO_R01', 'transformacoes_dwg_interno.json'), encoding='utf-8'))
    J['ESG-001'] = json.load(open(os.path.join(REL, 'IFC_R02', 'rotulos_gravidade.json'), encoding='utf-8'))['transf_ESG']
    for k, f in (('CPS-EL-001', 'transformacao_CPS_EL-001-ELG-R01_local_para_UTM.json'), ('CPS-DRE-001', 'transformacao_CPS_DRE-001-DRG-R01_local_para_UTM.json')):
        g = json.load(open(os.path.join(BASE, 'CAD_GEORREFERENCIADO', f), encoding='utf-8')); J[k] = {'rot_graus': g['rot_int_graus'], 't': g['t_int']}
    out = {_DWG[k]: (float(J[k]['rot_graus']), tuple(J[k]['t'])) for k in _DWG}
    if (os.environ.get('PRECLASH_UTM') if utm is None else utm):
        import jan_modelo as JM
        a_u = JM.ang_utm(0.0); o = JM.utm([[0, 0, 0]])[0][:2]
        for k, (r, t) in list(out.items()):
            a = math.radians(r); Ri = np.array([[math.cos(a_u), -math.sin(a_u)], [math.sin(a_u), math.cos(a_u)]])
            t_u = Ri @ np.array(t) + o
            out[k] = (math.degrees(a + a_u), tuple(t_u))
    return out


TRANSF_DWG = _transf()
