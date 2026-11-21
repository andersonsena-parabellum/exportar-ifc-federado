# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — equipamentos e peças que completam as redes externas no modelo (19/10/2026).
Duas saídas:
  1. equipamentos(ter) -> lista de equipamentos para o IFC (postes, quadros, hidrantes, central de alarme, reservatórios,
     hidrômetro, torneiras), gravada em RELATORIOS/FASE2_REDES_2026-10-18/SAT_fase2_equipamentos.csv;
  2. elementos_extra(E, ter) -> elementos lineares que entram no clash: subidas (prumadas do pluvial, torneiras de jardim,
     hidrante de recalque, eletrodutos que sobem nos quadros) e canaletas (pluvial e campo, aproximadas por cápsula).
Posições em UTM tiradas dos _GEO (fase 2); cotas sobre o terreno do adaptador (IMP as built desde 19/10/2026).
O que não está no desenho é premissa e vai marcado na coluna 'premissa'."""
import os, sys, csv, json, math
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sat_comum as sc   # noqa: E402

F2 = sc.REL
SAIDA_CSV = os.path.join(F2, 'SAT_fase2_equipamentos.csv')


def _csv(fn):
    with open(os.path.join(F2, fn), encoding='utf-8-sig') as f:
        return list(csv.DictReader(f, delimiter=';'))


def _fl(v):
    try: return float(str(v).replace(',', '.'))
    except (TypeError, ValueError): return None


def pontas_ele():
    """posição de cada nó (PONTA/TE/CX) pelas pontas dos eletrodutos da fase 2."""
    P = {}
    for t in _csv('SAT_fase2_ELE_trechos.csv'):
        P.setdefault(t['de'] + '@' + t['folha'][:6], (_fl(t['E_ini']), _fl(t['N_ini']), t['trecho'], t['diametro']))
        P.setdefault(t['para'] + '@' + t['folha'][:6], (_fl(t['E_fim']), _fl(t['N_fim']), t['trecho'], t['diametro']))
    return P


# quadros: nó onde termina o alimentador (fase 2, coluna 'destino') ou junção da medição
QUADROS = [('QGBT', 'PONTA-22', 'EL-002', 'Quadro geral (chegada do alimentador 5")'),
           ('MEDICAO', 'TE-51', 'EL-002', 'Medição / QGBT da entrada (símbolo MEDIDOR)'),
           ('QD-BOMB', 'PONTA-20', 'EL-002', 'Quadro das bombas de recalque'),
           ('QD-B.INC', 'PONTA-69', 'EL-002', 'Quadro da bomba de incêndio'),
           ('QDLT-QUA', 'PONTA-12', 'EL-002', 'Quadro de iluminação da quadra'),
           ('QDLT-CAM', 'PONTA-1', 'EL-002', 'Quadro de iluminação do campo (alimentador)'),
           ('QDLT-VEST', 'PONTA-72', 'EL-002', 'Quadro de iluminação do vestiário'),
           ('QD-GUA', 'PONTA-15', 'EL-002', 'Quadro da guarita')]
# o CPS ELE-001 põe o QDLT-CAMPO 4,2 m ao lado do ponto onde o EL-002 leva o alimentador (PONTA-1): vale o EL-002 (implantação);
# a diferença vai para as pendências de projeto.


def equipamentos(ter):
    Q = []
    z0 = lambda E, N: float(ter.z([[E, N]])[0])

    def add(id, disc, grupo, tipo, classe, E, N, forma, a, b, h, base, rot=0.0, origem='', premissa='', **extra):
        zt = z0(E, N)
        Q.append(dict(id=id, disciplina=disc, grupo_entrega=grupo, tipo=tipo, classe_ifc=classe, E=round(E, 3), N=round(N, 3),
                      terreno=round(zt, 3), rot_graus=round(rot, 3), forma=forma, dim_a=a, dim_b=b, altura=h, base_sobre_terreno=base,
                      origem=origem, premissa=premissa, **extra))
    # ---- elétrica: postes da iluminação externa (EL-001, bloco 'POSTE UMA PETALA') e do campo (CPS ELE-001)
    nos = _csv('SAT_fase2_ELE_nos.csv')
    E1 = sc.carrega('EL1')
    blocos = [(d['pts'][0][:2], d['rot']) for d in E1 if d['tipo'] == 'INSERT' and d.get('nome') == 'POSTE UMA PETALA']
    for r in nos:
        if r['tipo'] != 'POSTE' or not r['no'].startswith('IE-'): continue
        E, N = _fl(r['E']), _fl(r['N'])
        rot = min(blocos, key=lambda b: np.hypot(b[0][0] - E, b[0][1] - N))[1] if blocos else 0.0
        add(r['no'], 'ELE', 'ELE', 'poste de iluminação externa, 1 pétala', 'IfcLightFixture', E, N, 'poste', 0.15, 0.60, 6.0, 0.0, rot,
            'EL-001 R01 (bloco POSTE UMA PETALA)', 'altura 6,00 m e Ø 0,15 m (o desenho não dá a altura)')
    cp = [(r['no'], _fl(r['E']), _fl(r['N'])) for r in nos if r['tipo'] == 'POSTE' and r['no'].startswith('CP1-')]
    usados = set()
    for n, E, N in cp:                                   # nós a menos de 2 m = o mesmo poste (dois grupos de refletores)
        if n in usados: continue
        grupo = [(m, e, nn) for m, e, nn in cp if np.hypot(e - E, nn - N) < 2.0]
        usados |= {m for m, _, _ in grupo}
        Em = float(np.mean([g[1] for g in grupo])); Nm = float(np.mean([g[2] for g in grupo]))
        add('/'.join(g[0] for g in grupo), 'ELE', 'ELE', 'poste do campo society, refletores LED 200 W', 'IfcLightFixture', Em, Nm, 'poste', 0.20, 1.20, 8.0, 0.0,
            127.744, 'CPS ELE-001 R00 (detalhe 02: poste reto flangeado h = 8 m)', 'Ø 0,20 m e cruzeta de refletores de 1,20 m (forma aproximada)')
    # ---- quadros (caixa 0,60 x 0,25 x 0,90, centro a 1,50 m, legenda do EL: "Quadro de distribuição, h=1.50m")
    PE = pontas_ele()
    for nome, no, folha, desc in QUADROS:
        k = next((k for k in PE if k.split('@')[0] == no and (folha in k or folha == 'CPS EL' and k.endswith('@CPS EL'))), None)
        if k is None: continue
        E, N = PE[k][0], PE[k][1]
        add(nome, 'ELE', 'ELE', desc, 'IfcElectricDistributionBoard' if nome != 'MEDICAO' else 'IfcFlowMeter', E, N, 'caixa', 0.60, 0.25, 0.90, 1.05, 127.96,
            f'{folha}: ponta do alimentador ({no})', 'dimensão do quadro e altura de montagem pela legenda (h = 1,50 m)', no=no)
    # ---- PCI
    pci = {r['no']: r for r in _csv('SAT_fase2_PCI_nos.csv')}
    hid_t = {r['trecho']: r for r in _csv('SAT_fase2_PCI_trechos.csv')}
    t = hid_t.get('HID-03')
    if t:
        add('HID-RECALQUE', 'HID', 'PCIP', 'hidrante de recalque com válvula de retenção', 'IfcFireSuppressionTerminal', _fl(t['E_fim']), _fl(t['N_fim']),
            'cil', 0.25, 0.25, 0.80, 0.0, 0.0, 'IN-001 R03 (ponta do HID-03, texto HIDRANTE DE RECALQUE)', 'coluna Ø 0,25 x 0,80 m (forma aproximada)', pred='FIREHYDRANT')
    for k in ('HID-H-02', 'HID-H-03'):
        if k in pci:
            add(k, 'HID', 'PCIP', 'hidrante (símbolo do IN-001; tipo e montagem a conferir)', 'IfcFireSuppressionTerminal', _fl(pci[k]['E']), _fl(pci[k]['N']),
                'caixa', 0.90, 0.30, 0.60, 0.90, 127.96, 'IN-001 R03 (símbolo)', 'abrigo 0,90 x 0,60 x 0,30 a 0,90 m do piso (premissa)', pred='FIREHYDRANT')
    add('CENTRAL-SDAI', 'SDAI', 'PCIP', 'central de alarme e detecção com bateria', 'IfcUnitaryControlElement', 545978.5, 8716253.2, 'caixa', 0.40, 0.15, 0.50, 1.25, 127.96,
        'IN-001 R03 (texto CENTRAL DE ALARME E DETECÇÃO)', 'posição pelo texto; dimensão de catálogo (premissa)', pred='ALARMPANEL')
    # ---- água fria / reservação (posições do PCI; o AF-001 não desenha os reservatórios)
    af = {r['no']: r for r in _csv('SAT_fase2_AF_nos.csv')}
    if 'CASA-BOMBAS' in af:
        r = af['CASA-BOMBAS']
        add('RES-TACA', 'AF', 'HIDRO', 'reservatório metálico tipo taça 55 m³ (18 m³ RTI + 37 m³ consumo)', 'IfcTank', _fl(r['E']), _fl(r['N']), 'taca', 1.30, 2.86, 19.5, 0.0, 0.0,
            'IN-001 R03 (nota A: altura 19,5 m, Ø coluna 1,30 m, Ø superior 2,86 m)', 'taça modelada como coluna + cilindro de 55 m³ no topo', pred='STORAGE')
    for k in ('RES-INF-1', 'RES-INF-2', 'RES-INF-3'):
        if k in af:
            add(k, 'AF', 'HIDRO', 'reservatório inferior 15 m³ (tanque PB 15.000 L)', 'IfcTank', _fl(af[k]['E']), _fl(af[k]['N']), 'cil', 2.95, 2.95, 2.70, 0.0, 0.0,
                'IN-001 R03 (bloco TANQUE PB - 15.000)', 'Ø 2,95 x 2,70 m (catálogo típico de 15.000 L)', pred='STORAGE')
    if 'HIDROMETRO' in af:
        add('HIDROMETRO', 'AF', 'HIDRO', 'hidrômetro / cavalete 1" em abrigo', 'IfcFlowMeter', _fl(af['HIDROMETRO']['E']), _fl(af['HIDROMETRO']['N']), 'caixa', 0.60, 0.35, 0.50, 0.0, 127.96,
            'AF-001 R00', 'abrigo 0,60 x 0,35 x 0,50 m (premissa)', pred='WATERMETER')
    for k, r in af.items():
        if k.startswith('TJ-'):
            add(k, 'AF', 'HIDRO', 'torneira de jardim 25 x 1/2" (água não potável) em pilarete', 'IfcValve', _fl(r['E']), _fl(r['N']), 'caixa', 0.15, 0.15, 0.70, 0.0, 127.96,
                'AF-001 R00', 'pilarete 0,15 x 0,15 x 0,70 m (premissa)', pred='FAUCET')
    with open(SAIDA_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        cols = ['id', 'disciplina', 'grupo_entrega', 'tipo', 'classe_ifc', 'E', 'N', 'terreno', 'rot_graus', 'forma', 'dim_a', 'dim_b', 'altura', 'base_sobre_terreno', 'origem', 'premissa']
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';', extrasaction='ignore'); w.writeheader(); w.writerows(Q)
    return Q


# parte enterrada de cada equipamento (fundação/base), para o clash: premissas
# (poste: a base enterrada já é a caixa 80x80 do nó do poste; o fuste entra a partir de 0,30 m acima do terreno)
FUNDACAO = {'poste': -0.30, 'taca': 1.50, 'RES-INF': 0.20, 'HID-RECALQUE': 0.60, 'HIDROMETRO': 0.30, 'TJ-': 0.30}


def caixas_equipamento(ter, md, Q=None):
    """equipamentos como prismas (preclash: modelo.caixa_retangular) para entrarem no clash e no visualizador.
    rede = a da disciplina (não se testa contra a própria rede); fundo = base − fundação (premissa)."""
    Q = Q or equipamentos(ter)
    out = []
    for q in Q:
        fnd = FUNDACAO.get(q['forma']) or next((v for k, v in FUNDACAO.items() if q['id'].startswith(k)), 0.0)
        zt0 = q['terreno'] + float(q['base_sobre_terreno'])
        zb = (q['terreno'] - fnd) if fnd else zt0
        if fnd < 0: zb = q['terreno'] - fnd
        lx, ly = float(q['dim_a']), float(q['dim_b'])
        if q['forma'] == 'poste': ly = lx
        if q['forma'] == 'taca': lx = ly = float(q['dim_b'])
        if q['forma'] == 'cil': ly = lx
        rede = {'ELE': 'ELE', 'HID': 'HID', 'SDAI': 'SDAI', 'AF': 'AF'}[q['disciplina']]
        out.append(md.caixa_retangular(f"EQ:{q['id']}", q['disciplina'], rede, q['E'], q['N'], lx, ly, math.radians(q['rot_graus']),
                                       zb, zt0 + float(q['altura']), nome=q['id'], tipo=q['tipo'], equipamento=True,
                                       cota=(f"terreno do IMP; fundação {fnd:.2f} m (premissa)" if fnd > 0 else 'terreno do IMP; fuste a partir de 0,30 m (a base é a caixa do nó)' if fnd < 0
                                             else 'terreno do IMP (equipamento acima do piso)')))
    return out


def _ponta_mais_proxima(E, xy, discs, tol):
    best = None
    for e in E:
        if e['disc'] not in discs: continue
        for P in (e['pts'][0], e['pts'][-1]):
            d = math.hypot(P[0] - xy[0], P[1] - xy[1])
            if d < tol and (best is None or d < best[0]): best = (d, e, P)
    return best


def elementos_extra(E, ter, md):
    """subidas e canaletas (entram no clash). md = preclash.modelo."""
    out = []
    zt = lambda x, y: float(ter.z([[x, y]])[0])
    # prumadas do pluvial com tubo enterrado ligado: do eixo do tubo até 0,30 m acima do terreno
    for r in _csv('SAT_fase2_AP_prumadas.csv'):
        xy = (_fl(r['E']), _fl(r['N']))
        b = _ponta_mais_proxima(E, xy, ('AP',), 0.6)
        if b is None: continue
        d, e, P = b; z = zt(*xy)
        if np.isnan(z) or z - P[2] < 0.05: continue
        de = md.de_gravidade(_fl(r['DN_rotulo_mm']) or 100)
        out.append(md.elemento(f"AP:{r['prumada']}-subida", 'AP', e['rede'], f"{r['prumada']} (subida da prumada)", 'gravidade', de,
                               [(P[0], P[1], P[2]), (P[0], P[1], z + 0.30)], DN_mm=r['DN_rotulo_mm'], material='PVC', classe='prumada',
                               cota='eixo do tubo ligado até 0,30 m acima do terreno', obs='subida modelada (prumada desce da cobertura)'))
    # torneiras de jardim: subida do eixo da AF até 0,60 m acima do terreno
    for r in _csv('SAT_fase2_AF_nos.csv'):
        if not r['no'].startswith('TJ-'): continue
        xy = (_fl(r['E']), _fl(r['N'])); b = _ponta_mais_proxima(E, xy, ('AF',), 0.8)
        if b is None: continue
        d, e, P = b; z = zt(*xy)
        out.append(md.elemento(f"AF:{r['no']}-subida", 'AF', e['rede'], f"{r['no']} (subida da torneira)", 'pressao', 0.025,
                               [(P[0], P[1], P[2]), (P[0], P[1], z + 0.60)], movel=False, cota='eixo da AF até a torneira (0,60 m acima do terreno)'))
    # hidrante de recalque: subida do PEAD 2.1/2" até a coluna
    hid = [e for e in E if e['disc'] == 'HID' and e['trecho'] == 'HID-03']
    if hid:
        e = hid[0]; P = e['pts'][-1]; z = zt(P[0], P[1])
        out.append(md.elemento('HID:HID-03-subida', 'HID', e['rede'], 'HID-03 (subida do recalque)', 'pressao', e['de'],
                               [(P[0], P[1], P[2]), (P[0], P[1], z + 0.50)], movel=False, cota='eixo do HID-03 até a coluna do recalque'))
    # eletrodutos que sobem nos quadros (do eixo até a base do quadro, 1,05 m acima do terreno)
    PE = pontas_ele()
    for nome, no, folha, desc in QUADROS:
        k = next((k for k in PE if k.split('@')[0] == no and (folha in k or folha == 'CPS EL' and k.endswith('@CPS EL'))), None)
        if k is None: continue
        b = _ponta_mais_proxima(E, PE[k][:2], ('ELE',), 0.3)
        if b is None: continue
        d, e, P = b; z = zt(P[0], P[1])
        out.append(md.elemento(f'ELE:{nome}-subida', 'ELE', e['rede'], f'{nome} (eletroduto que sobe no quadro)', 'pressao', e['de'],
                               [(P[0], P[1], P[2]), (P[0], P[1], z + 1.05)], movel=False, cota='eixo do eletroduto até a base do quadro'))
    # canaletas: pluvial (ESG-001, ao pé dos muros/taludes) e campo society (CPS DRE-001, meia-cana com grelha)
    can = [(r['canaleta'], np.array([[_fl(r['E_ini']), _fl(r['N_ini'])], [_fl(r['E_fim']), _fl(r['N_fim'])]]), 'AP', 'AP', 0.40)
           for r in _csv('SAT_fase2_AP_canaletas.csv')]
    J = json.load(open(os.path.join(sc.WRK, 'cps_dre_rede.json'), encoding='utf-8'))
    for i, c in enumerate(J['canaletas']):
        can.append((f'CPS-CAN-{i + 1:02d}', np.array(c)[:, :2], 'DRE', 'CPS-DRE', 0.30))
    for nome, P, disc, rede, de in can:
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            k = max(1, int(np.linalg.norm(b - a) / 2.0)); Q += [a + (b - a) * j / k for j in range(1, k + 1)]
        Q = np.array(Q); z = ter.z(Q)
        if np.isnan(z).all(): continue
        z = np.where(np.isnan(z), np.nanmin(z), z)
        pts = np.column_stack([Q, z - de / 2])
        out.append(md.elemento(f'{rede}:{nome}', disc, rede, f'{nome} (canaleta)', 'gravidade', de, pts, material='concreto', classe='canaleta',
                               cota=f'topo no terreno (aproximada por cápsula Ø {de:.2f} m para o clash)',
                               obs='canaleta de superfície; seção real a confirmar no detalhe'))
    return out


if __name__ == '__main__':
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
    from preclash.terreno import Terreno
    ter = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\satiro_terreno.npz')
    Q = equipamentos(ter)
    import collections
    print(len(Q), 'equipamentos', collections.Counter(q['tipo'][:30] for q in Q))
    for q in Q:
        if np.isnan(q['terreno']): print('  sem terreno:', q['id'])
