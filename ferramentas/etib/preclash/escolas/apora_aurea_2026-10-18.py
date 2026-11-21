# -*- coding: utf-8 -*-
"""Adaptador da ETIB Aporá Prof. Áurea para o preclash.
Fontes (só leitura): ETIB-APORA-PROF-AUREA/RELATORIOS/GEORREF_E_REDES_2026-10-18 (thread da escola, rev. 2):
  - revit/dre_tubos.csv + revit/dre_caixas.csv: drenagem pluvial (AF-002-HIG R00, que é drenagem), cenário A = CT do projeto,
    eixo 3D por peça (H = horizontal, VP = vertical do pé de prumada AP / ralo da canaleta);
  - ele_trechos.csv / ele_nos.csv: eletrodutos QDLT-QUA (Ø1") e QDLT-BOMB (Ø2") caixa a caixa, 7 caixas 80x80 (só planta);
  - pci_trechos.csv: 5,1 m de hidrante 2½" PEAD e 5,1 m de laço SDAI (só planta).
Decisões sem resposta do usuário em 18/10/2026 (usada a opção recomendada ou a única possível, ver LEIA-ME da escola):
  - terreno: o do IMP as built (recomendado) não se lê sem Revit -> provisório SIT + platô da quadra 188,00 (apora_aurea_terreno.npz);
  - drenagem conforme o projeto (cenário A, o de entrega); B = hipótese CT 188 no mesmo terreno; C = CT 188 com ELE/PCI
    no terreno TOP no norte (sensibilidade, com o terreno TOP próprio do cenário);
  - ELE topo a 0,70 m (sem nota no projeto; mesma premissa da Alagoinhas); PCI e SDAI a 0,50 m (nota do IN-001);
  - pasta "10 - QUADRA" do Drive não baixada (download precisa do ok do usuário).
Equipamentos (19/10/2026, revit/equipamentos.csv): canaletas com grelha (0,20 m x 0,30 m, topo 188,00), interligação com a
rede geral existente e quadros QGBT/QDLT-QUA/QDLT-BOMB (0,60 x 0,25 x 1,00 m, base a 0,80 m do piso) como caixas retangulares."""
import os
import numpy as np
from preclash import leitura as lt, modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Aporá Prof. Áurea'
SIGLA = 'AUR'
BASE = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA'
F = os.path.join(BASE, 'RELATORIOS', 'GEORREF_E_REDES_2026-10-18')
SAIDA = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'apora_aurea_terreno.npz')
TERRENO_TOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'apora_aurea_terreno_top.npz')
ORIGEM = (600000.0, 8711300.0, 0.0)       # origem proposta dos RVTs (E, N, cota) — AGENTS.md
EPSG = 31984                              # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (600010.0, 8711225.0, 600110.0, 8711410.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID'],            # DRE fica fixa (gravidade, cotas do projeto)
    'dz_max': {'ELE': 1.00, 'SDAI': 1.00, 'HID': 1.00},
    'prof_max_topo': {'ELE': 2.00, 'SDAI': 2.00, 'HID': 2.00},
    'agua_acima_de': [],
}
DESVIOS = ['A']
CENARIO_ENTREGA = 'AD'
CENARIO_PROJETO = 'A'
DISCIPLINAS_ENTREGA = {'HIDRO': ('DRE',), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}
NOMES_DISC = {'DRE': 'Drenagem pluvial (AF-002)', 'ELE': 'Elétrica enterrada', 'HID': 'Hidrante (PCI)', 'SDAI': 'SDAI (PCI)'}
COB = {'ELE': 0.70, 'HID': 0.50, 'SDAI': 0.50}


def _drenagem(cen='A'):
    """Drenagem do cenário: A = CT do projeto (dre_tubos.csv/dre_caixas.csv); B = CT 188,00 em todas as caixas com a mesma
    profundidade h (dre_tubos_B.csv/dre_caixas_B.csv, hipótese da thread da escola)."""
    suf = '' if cen == 'A' else '_B'
    rotulo = 'CT/CF do projeto' if cen == 'A' else 'hipótese CT 188,00 (mesma profundidade h)'
    tubos = lt.ler_csv(os.path.join(F, 'revit', f'dre_tubos{suf}.csv'))
    vp = {r['peca_nome'][:-3]: r for r in tubos if r['peca'] == 'VP'}
    E = []
    for r in tubos:
        if r['peca'] != 'H':
            continue
        dn = lt.fl(r['DN']); de = md.de_gravidade(dn, r['material'])
        gim, gij = lt.fl(r['GI_mont']), lt.fl(r['GI_jus'])
        a = (lt.fl(r['x0_utm']), lt.fl(r['y0_utm']), gim + de / 2); b = (lt.fl(r['x1_utm']), lt.fl(r['y1_utm']), gij + de / 2)
        P = [a, b]
        if r['peca_nome'] in vp:                       # vertical do pé de prumada / ralo até a superfície
            v = vp[r['peca_nome']]
            P = [(a[0], a[1], lt.fl(v['z1_eixo']))] + P
        E.append(md.elemento(f"DRE:{r['peca_nome']}", 'DRE', 'DRE', r['peca_nome'], 'gravidade', de, P,
                             DN=int(dn), material=r['material'], GI_mont=gim, GI_jus=gij,
                             cota=f'{rotulo}; ramais de jusante para montante na declividade do rótulo', obs=r['obs']))
    C = []
    for r in lt.ler_csv(os.path.join(F, 'revit', f'dre_caixas{suf}.csv')):
        ct, cf, dim = lt.fl(r['CT']), lt.fl(r['CF']), lt.fl(r['dimensao_m'])
        forma = 'c' if r['tipo'] == 'PVP' else 'q'
        C.append(md.caixa(f"DRE:{r['id']}", 'DRE', 'DRE', forma, lt.fl(r['x_utm']), lt.fl(r['y_utm']), dim / 2, cf - 0.10, ct,
                          nome=r['id'], tipo=r['tipo'], cota=f'{rotulo}; fundo 0,10 m abaixo da CF', obs=r['obs']))
    return E, C


def _pressurizada(ter, pts2d, disc, rede, trecho, de, nome_ter, **info):
    P = lt.perfil_por_recobrimento(pts2d, de, COB[disc], ter)
    return md.elemento(f'{disc}:{trecho}', disc, rede, trecho, 'pressao', de, P, cob_min=COB[disc],
                       cota=f'provisória: topo a {COB[disc]:.2f} m do terreno {nome_ter} (trocar pelo IMP)', **info)


def _ele_pci(ter, nome_ter):
    """ELE (trechos caixa a caixa por circuito), caixas 80x80 e PCI (hidrante + laço SDAI) sobre o terreno dado."""
    E, C = [], []
    DE_ELE = {'QDLT-QUA': 0.032, 'QDLT-BOMB': 0.063}
    ele = []
    for r in lt.ler_csv(os.path.join(F, 'ele_trechos.csv')):
        pts = [(lt.fl(r['x0']), lt.fl(r['y0'])), (lt.fl(r['x1']), lt.fl(r['y1']))]
        ele.append(_pressurizada(ter, pts, 'ELE', 'ELE', r['trecho'], DE_ELE[r['circuito']], nome_ter, circuito=r['circuito'],
                                 eletroduto=r['eletroduto'], material='PEAD corrugado'))
    E += ele
    for r in lt.ler_csv(os.path.join(F, 'ele_nos.csv')):
        if not r['no'].startswith('CX'):
            continue
        x, y = lt.fl(r['x']), lt.fl(r['y']); zt = float(ter.z([[x, y]])[0])
        zs = [p[2] - e['de'] / 2 for e in ele for p in e['pts'] if np.hypot(p[0] - x, p[1] - y) < 1.0]
        zb = (min(zs) if zs else zt - 0.86) - 0.15
        C.append(md.caixa(f"ELE:{r['no']}", 'ELE', 'ELE', 'q', x, y, 0.40 + 0.05, zb, zt, nome=r['no'], tipo='CX 80x80',
                          cota=f'topo no terreno {nome_ter}; fundo 0,15 m abaixo do eletroduto mais baixo'))
    for r in lt.ler_csv(os.path.join(F, 'pci_trechos.csv')):
        pts = [(lt.fl(r['x0']), lt.fl(r['y0'])), (lt.fl(r['x1']), lt.fl(r['y1']))]
        if r['layer'].startswith('HI-'):
            E.append(_pressurizada(ter, pts, 'HID', 'HID', 'HID-01', 0.075, nome_ter, material='PEAD 2½"', obs='vem das instalações existentes (compatibilizar in loco)'))
        else:
            E.append(_pressurizada(ter, pts, 'SDAI', 'SDAI', 'SDAI-L01', 0.063, nome_ter, material='eletroduto PEAD 2"', obs='laço L01, 24 Vcc'))
    return E, C


def _equipamentos(ter, elementos, nome_ter):
    """Canaletas com grelha (DRE), interligação com a rede existente (DRE) e quadros QGBT/QDLT (ELE) como caixas
    retangulares giradas (revit/equipamentos.csv, gerado pela thread da escola). Cotas: 'abs' = absoluta, 'ter' = acima do
    terreno do cenário, 'eixo' = abaixo do eixo do tubo da disciplina mais próximo."""
    C = []
    for r in lt.ler_csv(os.path.join(F, 'revit', 'equipamentos.csv')):
        x, y = lt.fl(r['E']), lt.fl(r['N']); zter = float(ter.z([[x, y]])[0])
        def cota(v, ref):
            if ref == 'ter':
                return zter + v
            if ref == 'eixo':
                zs = [p[2] for e in elementos if e['disc'] == r['disc'] for p in e['pts'] if np.hypot(p[0] - x, p[1] - y) < 1.5]
                return (min(zs) if zs else zter - 1.5) - v
            return v
        zb, zt = cota(lt.fl(r['zb']), r['zb_ref']), cota(lt.fl(r['zt']), r['zt_ref'])
        info = dict(nome=r['id'], tipo=r['tipo'], equipamento=True, obs=r['obs'],
                    cota=f"{'terreno ' + nome_ter if 'ter' in (r['zb_ref'], r['zt_ref']) else 'cota absoluta'} ({r['zb_ref']}/{r['zt_ref']})")
        if r['forma'] == 'c':
            C.append(md.caixa(f"{r['disc']}:{r['id']}", r['disc'], r['disc'], 'c', x, y, lt.fl(r['lx']) / 2, zb, zt, **info))
        else:
            C.append(md.caixa_retangular(f"{r['disc']}:{r['id']}", r['disc'], r['disc'], x, y, lt.fl(r['lx']), lt.fl(r['ly']),
                                         np.radians(lt.fl(r['rot_graus'])), zb, zt, **info))
    return C


def carregar():
    ter = Terreno(TERRENO)                       # terreno da ferramenta (profundidades, IFC, visualizador): SIT + platô
    ter_top = Terreno(TERRENO_TOP)               # só para gerar as cotas de ELE/PCI do cenário C
    dA, cA = _drenagem('A'); dB, cB = _drenagem('B')
    eS, xS = _ele_pci(ter, 'SIT + platô')
    eT, xT = _ele_pci(ter_top, 'TOP no norte + platô')
    qA = _equipamentos(ter, dA + eS, 'SIT + platô'); qB = _equipamentos(ter, dB + eS, 'SIT + platô')
    qC = _equipamentos(ter_top, dB + eT, 'TOP no norte + platô')
    nada = lambda e: False
    cenarios = {
        'A': {'nome': 'drenagem com as CT do projeto; ELE/PCI no terreno SIT + platô 188', 'excluir': nada,
              'elementos': dA + eS, 'caixas': cA + xS + qA},
        'B': {'nome': 'drenagem com CT 188 (hipótese); ELE/PCI no terreno SIT + platô 188', 'excluir': nada,
              'elementos': dB + eS, 'caixas': cB + xS + qB},
        'C': {'nome': 'drenagem com CT 188 (hipótese); ELE/PCI no terreno TOP no norte (sensibilidade)', 'excluir': nada,
              'elementos': dB + eT, 'caixas': cB + xT + qC, 'terreno': ter_top},
    }
    return {'elementos': dA + eS, 'caixas': cA + xS + qA, 'terreno': ter, 'cenarios': cenarios}
