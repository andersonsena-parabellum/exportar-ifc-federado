# -*- coding: utf-8 -*-
"""Adaptador da ETIB Catu para o preclash.
Fontes (só leitura), da thread da escola:
  - gravidade: ETIB-CATU/RELATORIOS/FASE3_COTAS_2026-10-18/CAT_fase3_{DRE,ESG}_{trechos,caixas}.csv
    (fase 2 + CF corrigidas = CT − profundidade nas 5 caixas da DRE com rótulo incoerente: opção recomendada no checkpoint);
  - pressurizadas (só planta, fase 2): FERRAMENTAS/georef/work/CATU/rede/{af,inc,ele}_rede.json -> perfil_por_recobrimento().
Opções recomendadas adotadas enquanto o Anderson não responde às dúvidas da fase 2 (RELATORIOS/CATU_fase2_redes_extraidas_2026-10-18.md):
  - recobrimentos iguais aos da Sátiro Dias: AF 0,30 m; hidrantes 0,50 m (nota 5 do PCI); SDAI 0,50 m; elétrica 0,70 m (NBR 5410);
  - drenos Ø40 de ar-condicionado = sistema interno, fora do clash externo (classe 'dreno');
  - ESG/DRE: vale a cota das caixas (CF a CF) quando o i do rótulo não fecha; ESG-26 (CF sobe) fica como no projeto;
  - hidrante PEAD 2½" = DE 75; SDAI PEAD Ø2" = DE 60; eletroduto sem rótulo = Ø3/4" (nota do projeto); banco: cada eletroduto
    com o maior Ø rotulado da rota (a favor da segurança no clash).
Terreno: provisório (escolas/catu_terreno.py): CT das caixas + níveis da SIT + platô do TER (−1,92 m em E) + TOP-001.
  O IMP as built (lido no Revit em 19/10) tem os platôs 1,6 a 5,1 m acima da SIT R02 e das CT do ESG/DRE: decisão do Anderson;
  até lá vale o terreno do projeto (as redes por gravidade foram projetadas nele).
Cenários (19/10/2026):
  A  = projeto + opções recomendadas, só profundidade;
  B  = A + ajustes em planta antes do clash (FERRAMENTAS/georef/catu_ajustes.py): caixas do SDAI/elétrica desenhadas em cima
       de PV/CA/CE (o clash não testa caixa × caixa) e nós da AF dentro de caixa do esgoto andam o mínimo;
  BD = B + desvios em planta automáticos (cenário de entrega).
Limites de Δz/profundidade maiores que o padrão (1,50 m / 2,50 m nas redes que não são AF): o Anderson prefere só profundidade
(traçado novo = executivo novo), então o mergulho mais fundo vem antes do desvio.
Equipamentos (FERRAMENTAS/georef/equip_catu.py): hidrantes, abrigos, recalque, casa de bombas, quadros, postes e bases,
caixas dos registros, prumadas AP e canaletas do campo; dimensões de premissa quando o projeto não traz."""
import os, re, sys, json, copy, csv
import numpy as np
from preclash import leitura as lt
from preclash import modelo as md
from preclash.terreno import Terreno

ESCOLA = 'ETIB Catu'
SIGLA = 'CAT'
BASE = r'D:\Projeto Modelagem\ETIB-CATU'
F3 = os.path.join(BASE, 'RELATORIOS', 'FASE3_COTAS_2026-10-18')
REDE = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\rede'
SAIDA = os.path.join(BASE, 'RELATORIOS', 'PRECLASH_2026-10-18')
TERRENO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'catu_terreno.npz')
ORIGEM = (567700.0, 8634650.0, 0.0)        # origem proposta dos RVTs (AGENTS.md)
EPSG = 31984                               # SIRGAS 2000 / UTM 24S
CAIXA_OBRA = (567625.0, 8634540.0, 567800.0, 8634715.0)

REGRAS = {
    'folga': 0.20,
    'ordem_mover': ['ELE', 'SDAI', 'HID', 'AF'],       # ESG/DRE fixas; mexer primeiro em elétrica e PCI, depois AF
    'dz_max': {'ELE': 1.50, 'SDAI': 1.50, 'HID': 1.50, 'AF': 0.80},          # 19/10: preferir profundidade a desvio
    'prof_max_topo': {'ELE': 2.50, 'SDAI': 2.50, 'HID': 2.50, 'AF': 1.50},
    'agua_acima_de': ['ESG'],
}
DESVIOS = ['B']                  # 19/10: AD (só a ferramenta) deu 71 críticos × BD 62; fica só o BD
CENARIO_ENTREGA = 'BD'
DISCIPLINAS_ENTREGA = {'HIDRO': ('AF', 'ESG', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}
NOMES_DISC = {'AF': 'Água fria', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial', 'ELE': 'Elétrica enterrada (BT + iluminação)',
              'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)', 'EST': 'Fundação/estrutura as built (obstáculo)'}

COB = {'AF': 0.30, 'HID': 0.50, 'SDAI': 0.50, 'ELE': 0.70}
DE_RNC40 = {'3/4': 26.7, '1': 33.4, '1.1/4': 42.2, '1.1/2': 48.3, '2': 60.3, '2.1/2': 73.0, '3': 88.9, '4': 114.3, '5': 141.3, '6': 168.3}


def _de_eletroduto(rotulos):
    """maior Ø rotulado da rota (texto 'QDAC-REF Ø3"; ...'); sem rótulo, Ø3/4" (nota do projeto)."""
    des = []
    for m in re.finditer(r'Ø\s*([\d./]+)"', rotulos or ''):
        k = m.group(1).replace('. ', '.').strip('.')
        if k in DE_RNC40: des.append(DE_RNC40[k])
    return (max(des) if des else DE_RNC40['3/4']) / 1000.0, ('rótulo da rota' if des else 'sem rótulo: Ø3/4" (nota do projeto)')


def _perfil(id_, disc, rede, trecho, pts2d, de, ter, **info):
    P = lt.perfil_por_recobrimento(pts2d, de, COB[disc], ter)
    return md.elemento(id_, disc, rede, trecho, 'pressao', de, P, cob_min=COB[disc],
                       cota=f'premissa: recobrimento {COB[disc]:.2f} m sobre o terreno provisório', **info)


def _caixas_pressao(nos, disc, rede, ter, elementos, lado_por_tipo, prof_sob_eixo=0.15, raio_busca=1.0):
    pts = [(e, p) for e in elementos for p in e['pts']]
    out = []
    for n in nos:
        lado = lado_por_tipo.get(n['tipo'])
        if lado is None: continue
        E, N = n['c']; zt = float(ter.z([[E, N]])[0])
        if np.isnan(zt): continue
        zs = [p[2] - e['de'] / 2 for e, p in pts if np.hypot(p[0] - E, p[1] - N) < raio_busca]
        zb = (min(zs) if zs else zt - 0.6) - prof_sob_eixo
        out.append(md.caixa(f'{rede}:{n["id"]}', disc, rede, 'q', E, N, lado / 2 + 0.05, zb, zt, nome=n['id'], tipo=n['tipo'],
                            cota='topo no terreno; fundo 0,15 m abaixo do eletroduto mais baixo' if zs else 'sem eletroduto chegando: 0,60 m'))
    return out


def carregar():
    ter = Terreno(TERRENO)
    E, C = [], []
    # ---- gravidade (cotas do projeto, fixas)
    dre = lt.gravidade(os.path.join(F3, 'CAT_fase3_DRE_trechos.csv'), 'DRE', 'DRE', ter, excluir_classe=('dreno',))
    esg = lt.gravidade(os.path.join(F3, 'CAT_fase3_ESG_trechos.csv'), 'ESG', 'ESG', ter)
    E += dre + esg
    C += lt.caixas(os.path.join(F3, 'CAT_fase3_DRE_caixas.csv'), 'DRE', 'DRE', ter, dre)
    C += lt.caixas(os.path.join(F3, 'CAT_fase3_ESG_caixas.csv'), 'ESG', 'ESG', ter, esg)
    # ---- água fria
    af = json.load(open(os.path.join(REDE, 'af_rede.json'), encoding='utf-8'))
    for t in af['trechos']:
        de = float(t.get('DN_adotado') or t.get('DN_mm') or 32) / 1000.0        # PVC soldável: o rótulo já é o DE
        E.append(_perfil(f'AF:{t["trecho"]}', 'AF', 'AF', t['trecho'], t['pts'], de, ter, DN_mm=t.get('DN_adotado'),
                         material='PVC soldável', destino=t.get('destino_jusante', ''), obs=t.get('obs', '')))
    # ---- incêndio
    inc = json.load(open(os.path.join(REDE, 'inc_rede.json'), encoding='utf-8'))
    for t in inc['hidrantes']:
        E.append(_perfil(f'HID:{t["trecho"]}', 'HID', 'HID', t['trecho'], t['pts'], 0.075, ter, DN='2.1/2"', material='PEAD (DE 75, premissa)', obs=t.get('obs', '')))
    sdai = []
    for t in inc['sdai']:
        sdai.append(_perfil(f'SDAI:{t["trecho"]}', 'SDAI', 'SDAI', t['trecho'], t['pts'], 0.060, ter, DN='2"', material='PEAD (nota do projeto)',
                            lacos=(t.get('lacos_rotulo') or '') + ((' (inferidos: ' + t['lacos_inferidos'] + ')') if t.get('lacos_inferidos') else ''),
                            obs=t.get('obs', '')))
    E += sdai
    C += _caixas_pressao([{'id': c['id'], 'tipo': c['tipo'], 'c': c['c']} for c in inc['caixas_sdai']], 'SDAI', 'SDAI', ter, sdai, {'CX': 0.30})          # a central do SDAI é equipamento na parede (equip_catu)
    # ---- elétrica (EL-001 alimentação BT e EL-002 iluminação externa: redes separadas, ambas disciplina ELE)
    ele = json.load(open(os.path.join(REDE, 'ele_rede.json'), encoding='utf-8'))
    for tag, rede in (('EL1', 'ELE-BT'), ('EL2', 'ELE-IL')):
        rot = {r['rota']: r for r in ele[tag]['rotas']}
        els = []
        for t in ele[tag]['eletrodutos']:
            de, org = _de_eletroduto(rot.get(t['rota'], {}).get('circuitos_rotulo', ''))
            els.append(_perfil(f'{rede}:{t["eletroduto"]}', 'ELE', rede, t['eletroduto'], t['pts'], de, ter, rota=t['rota'],
                               circuitos=rot.get(t['rota'], {}).get('circuitos_rotulo', ''), DE_origem=org))
        E += els
        nos = [{'id': n['id'], 'tipo': n['tipo'], 'c': n['c'], 'raio': n['raio']} for n in ele[tag]['nos']]
        lados = {'CX': 0.80} if tag == 'EL1' else {'CX': 0.60}
        C += _caixas_pressao(nos, 'ELE', rede, ter, els, lados)
    # ---- equipamentos (todos os cenários)
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
    import equip_catu, catu_ajustes, est_catu
    Ceq, Eeq, _ = equip_catu.equipamentos(ter, E)
    C += Ceq; E += Eeq
    Cest, rest = est_catu.estrutura(ter)          # fundações/arranques/baldrames dos blocos as built (RST, CDG, CDR, GUA, SB5)
    C += Cest
    print('  estrutura as built:', ', '.join(f'{b} {n} peças (Δz {dz:+.2f} m)' for b, n, dz in rest))
    # ---- cenário B: ajustes em planta antes do clash
    EB, CB = copy.deepcopy(E), copy.deepcopy(C)
    reg = catu_ajustes.aplicar(EB, CB, ter, COB, REGRAS, log=print)
    _gravar_ajustes(reg)
    cenarios = {'A': {'nome': 'projeto + opções recomendadas (só profundidade)', 'excluir': lambda e: False},
                'B': {'nome': 'A + caixas e nós fora de PV/CA/CE', 'excluir': lambda e: False, 'elementos': EB, 'caixas': CB}}
    return {'elementos': E, 'caixas': C, 'terreno': ter, 'cenarios': cenarios}


def _gravar_ajustes(reg):
    os.makedirs(SAIDA, exist_ok=True)
    f2 = lambda v: '' if v is None else f'{v:.2f}'.replace('.', ',')
    f3 = lambda v: '' if v is None else f'{v:.3f}'.replace('.', ',')
    cols = ['n', 'disciplina', 'tipo', 'item', 'status', 'deslocamento_m', 'folga_antes_m', 'folga_depois_m', 'trechos_que_acompanham', 'E', 'N', 'E_novo', 'N_novo', 'nota_para_planta']
    with open(os.path.join(SAIDA, f'{SIGLA}_preclash_B_ajustes_manuais.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(cols)
        for n, r in enumerate(reg, 1):
            w.writerow([n, r['disc'], r['tipo'], r['item'], r['status'], f2(r.get('desloc')), f2(r.get('antes')), f2(r.get('depois')), r.get('trechos', ''),
                        f3(r['E']), f3(r['N']), f3(r.get('E_novo')), f3(r.get('N_novo')), r.get('nota', '')])
