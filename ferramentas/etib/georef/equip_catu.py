# -*- coding: utf-8 -*-
"""ETIB Catu — equipamentos e peças das redes para o preclash/IFC (19/10/2026), a partir da fase 2 (work/CATU/rede/*.json e
RELATORIOS/DRE_fase2_*.csv). Tudo com dimensão de PREMISSA quando o projeto não traz (marcado em info['cota'/'premissa']):
  HID : hidrantes (coluna Ø100 do tubo até +1,00 m), abrigos de mangueira 0,90 × 0,30 de +0,60 a +1,80 (na parede), caixa do registro de recalque
        0,60 × 0,40, casa de bombas (contorno do projeto, h 2,80 m);
  ELE : QGBT e quadros 0,60 × 0,25 (h 0,40 a 2,00 m, na face da edificação), postes da iluminação (Ø0,16, h 6,00 m) com base
        enterrada 0,50 × 0,50 × 1,00 m;
  AF  : caixas dos registros RG 0,30 × 0,30 (fundo 0,10 m abaixo do tubo);
  DRE : prumadas AP (Ø100 vertical do ramal até o terreno) e as 2 canaletas do campo (semicircular Ø30, esquemática no terreno).
Os ids começam com 'EQ:' para o pós-processamento do IFC trocar a classe (catu_ifc_pos.py).
O que fica acima do terreno (abrigos, casa de bombas, poste) começa a +0,25 m (base/pedestal), para não contar como
conflito com o tampo das caixas enterradas vizinhas (folga 0,20 m também na vertical)."""
import os, csv, json
import numpy as np
from preclash import modelo as md

REDE = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\rede'
REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
PREM = 'dimensão de premissa (o projeto não traz)'


def _zt(ter, E, N, padrao=None):
    z = float(ter.z([[E, N]])[0])
    return padrao if np.isnan(z) else z


def _ponta(E_els, rede, E, N, raio=1.5):
    """cota do eixo e ponto da ponta de trecho da rede mais perto de (E, N)."""
    melhor = None
    for e in E_els:
        if e['rede'] != rede: continue
        for i in (0, len(e['pts']) - 1):
            d = np.hypot(e['pts'][i, 0] - E, e['pts'][i, 1] - N)
            if d < raio and (melhor is None or d < melhor[0]): melhor = (d, e['pts'][i].copy(), e)
    return melhor


def _ret_min(P):
    """retângulo de área mínima (centro, lx, ly, rot) de uma nuvem 2D."""
    P = np.asarray(P, float); best = None
    for a, b in zip(P[:-1], P[1:]):
        t = b - a; L = np.hypot(*t)
        if L < 0.2: continue
        u = t / L; v = np.array([-u[1], u[0]])
        pu, pv = P @ u, P @ v
        area = (pu.max() - pu.min()) * (pv.max() - pv.min())
        if best is None or area < best[0]:
            c = u * (pu.max() + pu.min()) / 2 + v * (pv.max() + pv.min()) / 2
            best = (area, c, pu.max() - pu.min(), pv.max() - pv.min(), float(np.arctan2(u[1], u[0])))
    return best[1:]


def equipamentos(ter, E_els):
    C, E, reg = [], [], []
    inc = json.load(open(os.path.join(REDE, 'inc_rede.json'), encoding='utf-8'))
    for n in inc['nos_h']:
        x, y = n['c']; zt = _zt(ter, x, y)
        if zt is None: continue
        if n['tipo'] == 'HID':
            p = _ponta(E_els, 'HID', x, y)
            z0 = p[1][2] if p else zt - 0.60
            C.append(md.caixa(f'EQ:HID:{n["id"]}', 'HID', 'HID', 'c', x, y, 0.05, z0 - 0.0375, zt + 1.00, nome=n['id'], tipo='hidrante (coluna)',
                              equip='hidrante', cota='do eixo do ramal até +1,00 m (premissa)'))
            if n.get('abrigo'):
                ax, ay = n['abrigo']; za = _zt(ter, ax, ay, zt); rot = float(np.arctan2(y - ay, x - ax)) + np.pi / 2
                C.append(md.caixa_retangular(f'EQ:HID:ABR-{n["id"]}', 'HID', 'HID', ax, ay, 0.90, 0.30, rot, za + 0.60, za + 1.80, nome=f'abrigo {n["id"]}',
                                             tipo='abrigo de mangueira', equip='abrigo', cota=PREM))
            reg.append(('HID', n['id'], 'hidrante + abrigo'))
        elif n['tipo'] == 'RECALQUE':
            p = _ponta(E_els, 'HID', x, y, 2.5); z0 = p[1][2] if p else zt - 0.60
            C.append(md.caixa_retangular('EQ:HID:RECALQUE', 'HID', 'HID', x, y, 0.60, 0.40, 0.0, z0 - 0.15, zt, nome='registro de recalque',
                                         tipo='caixa do recalque', equip='recalque', cota=PREM))
            reg.append(('HID', 'RECALQUE', 'caixa do recalque'))
        elif n['tipo'] == 'CASA DE BOMBAS':
            P = np.vstack([np.asarray(c) for c in n['contorno']])
            c, lx, ly, rot = _ret_min(P)
            C.append(md.caixa_retangular('EQ:HID:CB', 'HID', 'HID', c[0], c[1], lx, ly, rot, zt + 0.25, zt + 2.80, nome='casa de bombas',
                                         tipo='casa de bombas', equip='casa de bombas', cota='contorno do projeto; altura 2,80 m (premissa)'))
            reg.append(('HID', 'CB', f'casa de bombas {lx:.2f} × {ly:.2f}'))
    for n in inc['caixas_sdai']:
        if n['tipo'] != 'CENTRAL': continue
        x, y = n['c']; zt = _zt(ter, x, y)
        if zt is None: continue
        C.append(md.caixa_retangular('EQ:SDAI:CENTRAL', 'SDAI', 'SDAI', x, y, 0.50, 0.20, 0.0, zt + 1.20, zt + 1.70, nome='central de alarme',
                                     tipo='central SDAI', equip='central', cota=PREM + '; na parede, dentro da edificação'))
        reg.append(('SDAI', 'CENTRAL', 'central de alarme'))
    cb = next((c for c in C if c['id'] == 'EQ:HID:CB'), None)
    def na_cb(x, y):
        if cb is None: return False
        dx, dy = x - cb['E'], y - cb['N']; cs, sn = np.cos(cb['rot']), np.sin(cb['rot'])
        return abs(dx * cs + dy * sn) < cb['mx'] and abs(-dx * sn + dy * cs) < cb['my']
    ele = json.load(open(os.path.join(REDE, 'ele_rede.json'), encoding='utf-8'))
    for n in ele['EL1']['nos']:
        if n['tipo'] not in ('QGBT', 'QD'): continue
        x, y = n['c']; zt = _zt(ter, x, y)
        if zt is None: continue
        if na_cb(x, y): reg.append(('ELE', n['id'], 'quadro dentro da casa de bombas (não modelado à parte)')); continue
        lx = 1.00 if n['tipo'] == 'QGBT' else 0.60
        C.append(md.caixa_retangular(f'EQ:ELE:{n["id"]}', 'ELE', 'ELE-BT', x, y, lx, 0.25, 0.0, zt + 0.40, zt + 2.00, nome=n['id'], tipo=n['tipo'],
                                     equip='quadro', cota=PREM))
        reg.append(('ELE', n['id'], 'quadro'))
    for n in ele['EL2']['nos']:
        if n['tipo'] != 'POSTE': continue
        x, y = n['c']; zt = _zt(ter, x, y)
        if zt is None: continue
        C.append(md.caixa(f'EQ:ELE:{n["id"]}', 'ELE', 'ELE-IL', 'c', x, y, 0.08, zt + 0.25, zt + 6.00, nome=n['id'], tipo='poste', equip='poste',
                          cota='altura 6,00 m (premissa; bloco "POSTE UMA PÉTALA")'))
        C.append(md.caixa_retangular(f'EQ:ELE:BASE-{n["id"]}', 'ELE', 'ELE-IL', x, y, 0.50, 0.50, 0.0, zt - 1.00, zt + 0.25, nome=f'base {n["id"]}',
                                     tipo='base do poste', equip='base de poste', cota=PREM))
        reg.append(('ELE', n['id'], 'poste + base'))
    af = json.load(open(os.path.join(REDE, 'af_rede.json'), encoding='utf-8'))
    for n in af['nos']:
        x, y = n['c']; zt = _zt(ter, x, y)
        if zt is None: continue
        p = _ponta(E_els, 'AF', x, y, 1.0); z0 = p[1][2] if p else zt - 0.40
        C.append(md.caixa_retangular(f'EQ:AF:{n["id"]}', 'AF', 'AF', x, y, 0.30, 0.30, 0.0, z0 - 0.10 - 0.03, zt, nome=n['id'], tipo=f'registro {n.get("bitola", "")}',
                                     equip='registro', cota='fundo 0,10 m abaixo do tubo (premissa)'))
        reg.append(('AF', n['id'], 'caixa do registro'))
    for r in csv.DictReader(open(os.path.join(REL, 'DRE_fase2_prumadas_2026-10-18.csv'), encoding='utf-8-sig'), delimiter=';'):
        x, y = float(r['E']), float(r['N']); zt = _zt(ter, x, y)
        if zt is None: continue
        p = _ponta(E_els, 'DRE', x, y, 1.0)
        if not p: continue
        de = md.de_gravidade(float(r['DN_rotulo_mm'] or 100))
        P = np.array([p[1], [p[1][0], p[1][1], zt]])
        if P[1, 2] - P[0, 2] < 0.05: continue
        E.append(md.elemento(f'EQ:DRE:{r["prumada"]}', 'DRE', 'DRE', r['prumada'], 'gravidade', de, P, nome=r['prumada'], classe='prumada',
                             cota='do ramal até o terreno', equip='prumada'))
        reg.append(('DRE', r['prumada'], 'prumada'))
    for r in csv.DictReader(open(os.path.join(REL, 'DRE_fase2_canaletas_2026-10-18.csv'), encoding='utf-8-sig'), delimiter=';'):
        a = np.array([float(r['E_ini']), float(r['N_ini'])]); b = np.array([float(r['E_fim']), float(r['N_fim'])])
        k = max(2, int(np.hypot(*(b - a)) / 2.0) + 1)
        Q = np.array([a + (b - a) * t for t in np.linspace(0, 1, k)]); z = ter.z(Q)
        if np.isnan(z).any(): continue
        E.append(md.elemento(f'EQ:DRE:{r["canaleta"]}', 'DRE', 'DRE-CAN', r['canaleta'], 'gravidade', 0.30, np.column_stack([Q, z - 0.15]),
                             nome=r['canaleta'], classe='canaleta', cota='esquemática: eixo 0,15 m abaixo do terreno (i=3% do texto não aplicada)',
                             equip='canaleta', material='concreto, semicircular com grelha'))
        reg.append(('DRE', r['canaleta'], 'canaleta'))
    return C, E, reg
