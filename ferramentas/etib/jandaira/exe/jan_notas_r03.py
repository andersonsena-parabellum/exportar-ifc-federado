# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026, pedido do Anderson): as pranchas R03 saíram com a profundidade repetida no mesmo trecho (19 "PROF. 0,90 m"
na curva da EL-001), porque o modelo quebra as curvas em pedaços de 1,4 m e cada pedaço/eletroduto ganhava a própria nota.
Este script corrige as pranchas JÁ ENTREGUES sem refazer o resto (traçado, caixas, carimbo QG):
  1) guarda a versão entregue (DWG + PDF) em _copias/entregue_notas-repetidas/;
  2) apaga as notas "PROF. x,xx m" que a revisão pôs (textos que não existem no desenho original);
  3) põe as notas de novo pela regra nova do asbuilt (agrupar_notas: uma por trecho; ao lado da etiqueta de diâmetro/material
     do trecho quando houver, no estilo dela);
  4) grava o DWG no mesmo nome e plota o PDF A0 (mesmo -PLOT do carimbo QG) em PDF_QG/.
Um accoreconsole por vez (rever.console espera os das outras threads).
Uso: python -X utf8 jan_notas_r03.py [AF-001 EL-001 ...] [--so-comandos]"""
import os, sys, re, math, json, shutil, collections
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
R3 = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'
COP = os.path.join(R3, '_copias'); NOT = os.path.join(COP, 'notas'); BKP = os.path.join(COP, 'entregue_notas-repetidas')
PDF = os.path.join(R3, 'PDF_QG')
# JAN_NOTAS_SAIDA: pasta de preparo (DWG + PDF/ ali), para trocar na entrega só depois do ok (20/10 noite, Revisão de qualidade)
SAI = os.environ.get('JAN_NOTAS_SAIDA') or R3
PDF_SAI = PDF if SAI == R3 else os.path.join(SAI, 'PDF')
import carimbo_qg as CQ
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf'); import dxfgeo
FINAL = {'AF-001': '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03', 'EL-001': '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R03',
         'EL-002': '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R03', 'IN-001': '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R05',
         'CPS-EL-001': '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R03'}
LOGOS = [x for x in os.listdir(R3) if x.startswith('CARIMBO_QG_logo_') and x.endswith('.png')]
DXFOUT = 'D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp'
LSP = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo', 'revisao.lsp').replace('\\', '/')
NOTA = re.compile(r'^PROF\. \d+,\d\d m$')
M = json.load(open(os.path.join(R3, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
# trecho (sem o .N) -> profundidade do topo depois da R03 (decisões do Anderson em 20/10, 20h56 e 22h21): ELE-I-31 inteiro a
# 0,85 m; com a DRE-031/046 de volta às cotas da prancha, o ELE-I-12 e o alarme PCI-EL-01/03 passam por baixo delas
# (valores da rodada PRECLASH_R03_CX32, jan_prof_rodada.py)
AJUSTE_PROF = {'ELE-I-31': 0.85, 'ELE-I-12': 0.92, 'PCI-EL-03': 1.07, 'PCI-EL-03a': 0.94}
# trechos que não tinham nota e passam a ter (folha, profundidade); a planta sai da rodada nova
NOVAS_NOTAS = {'PCI-EL-01': ('IN-001', 1.05), 'PCI-EL-01b': ('IN-001', 0.95)}
RODADA_NOVA = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R03_CX32'


def _novas():
    if not NOVAS_NOTAS or not os.path.exists(os.path.join(RODADA_NOVA, 'JAN.json')): return []
    J = json.load(open(os.path.join(RODADA_NOVA, 'JAN.json'), encoding='utf-8')); o = np.array([631578.10, 8721003.57])
    out = []
    for e in J['elementos']:
        if e['trecho'] not in NOVAS_NOTAS or 'AD' not in e.get('cen', ['AD']): continue
        f, prof = NOVAS_NOTAS[e['trecho']]; Q = np.array((e.get('sol') or {}).get('AD') or e['p'], float)[:, :2] + o
        out.append(dict(tipo='mergulho', disc=e['disc'], trecho=e['trecho'], elemento=e['id'], folha=f, planta=Q.tolist(),
                        prof_topo=prof, extensao=float(np.sum(np.hypot(*np.diff(Q, axis=0).T))), nota='PROF. %s m' % ab.br(prof)))
    return out


M += _novas()


def dxf(dwg):
    fn = dwg[:-4] + '.dxf'
    if not os.path.exists(fn) or os.path.getmtime(fn) < os.path.getmtime(dwg):
        rever.console(dwg, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % DXFOUT, 'DXFX', '_.QUIT', '_Y'], dwg + '.dxf.log',
                      {'DXF_OUT': fn.replace('\\', '/')})
    return fn


def folha(chave, so_comandos=False):
    nome = FINAL[chave]; final = os.path.join(SAI, nome + '.dwg'); pdf = os.path.join(PDF_SAI, nome + '.pdf')
    os.makedirs(PDF_SAI, exist_ok=True)
    os.makedirs(NOT, exist_ok=True); os.makedirs(BKP, exist_ok=True)
    if not os.path.exists(os.path.join(BKP, nome + '.dwg')):                 # a versão entregue fica guardada uma vez só
        shutil.copy2(os.path.join(R3, nome + '.dwg'), os.path.join(BKP, nome + '.dwg'))
        if os.path.exists(os.path.join(PDF, nome + '.pdf')): shutil.copy2(os.path.join(PDF, nome + '.pdf'), os.path.join(BKP, nome + '.pdf'))
    trab = os.path.join(NOT, nome + '.dwg'); shutil.copy2(os.path.join(BKP, nome + '.dwg'), trab)   # sempre a partir da entregue
    for lg in LOGOS:
        shutil.copy2(os.path.join(R3, lg), os.path.join(NOT, lg))      # logos do carimbo carregados no console
        if SAI != R3: shutil.copy2(os.path.join(R3, lg), os.path.join(SAI, lg))
    # DXF lido pelo carimbo QG antes de trocar o carimbo (_ler.dxf): os textos do modelo têm os mesmos handles na R03 entregue
    ler = os.path.join(COP, nome + '_ler.dxf')
    # blocos=True: a nota também desvia dos textos da arquitetura inserida como bloco ("DEP. DE UTENSÍLIOS")
    E = ab.entidades(ler if os.path.exists(ler) else dxf(trab), arcos=True, blocos=True)
    dwg0 = S._DWG[chave]; orig = ab.entidades(os.path.join(COP, os.path.splitext(os.path.basename(dwg0))[0] + '.dxf'))
    h0 = {e['h'] for e in orig}
    velhas = [e for e in E if e['typ'] == 'TEXT' and NOTA.match(str(e.get('txt', '')).strip()) and e['h'] not in h0]
    hv = {e['h'] for e in velhas}
    rot, t = S.TRANSF_DWG[dwg0]; a = math.radians(rot); Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda P: np.array([Rm.T @ (np.asarray(p[:2], float) - np.array(t)) for p in P])
    Pl = ab.Plano([e for e in E if e['h'] not in hv], tol=S.EXECUTIVO_TOL, ext=S.EXECUTIVO_EXT, caixa_sem_simbolo=S.EXECUTIVO_CAIXA_SEM_SIMBOLO)
    Pl.alt_nota = S.EXECUTIVO_NOTA_ALT
    # o barrilete da casa de bombas (PCI-AF-*) fica acima do piso no modelo novo: não leva nota de profundidade
    ms = [m for m in M if m['folha'] == chave and m['tipo'] == 'mergulho' and not str(m['trecho']).startswith('PCI-AF')]
    # decisão do Anderson (20/10, 20h56): ELE-I-31 inteiro a 0,85 m (tinha 0,65 e 0,85 sem caixa no meio) -> uma nota só
    ms = [dict(m, prof_topo=AJUSTE_PROF[re.sub(r'\.\d+$', '', m['trecho'])]) if re.sub(r'\.\d+$', '', m['trecho']) in AJUSTE_PROF else m for m in ms]
    G = ab.agrupar_notas(ms, familia=S.EXECUTIVO_FAMILIA)
    for g in G: Pl.nota(loc(g['P']), g['texto'], g['rotulo'], disc=g.get('disc'))
    linhas = [f'DEL\t{h}' for h in sorted(hv)] + Pl.L
    # trecho redesenhado que ficou "Continuous" numa layer cujas linhas originais seguem o tipo da layer (rede tracejada) -> ByLayer
    def brutos(fn):
        return {str(d[5]).strip(): (t, d) for t, data in dxfgeo.parse(fn)[1] for d in [dxfgeo._first(data)] if 5 in d}
    B = brutos(ler) if os.path.exists(ler) else {}; B0 = brutos(os.path.join(COP, os.path.splitext(os.path.basename(dwg0))[0] + '.dxf'))
    lay_bl = {d.get(8) for t, d in B0.values() if t in ('LINE', 'LWPOLYLINE') and d.get(6) is None}
    lt = [f'LT\t{h}\tByLayer' for h, (t, d) in B.items() if h not in B0 and t in ('LINE', 'LWPOLYLINE')
          and str(d.get(6, '')).upper() == 'CONTINUOUS' and d.get(8) in lay_bl]
    linhas += lt
    cmd = os.path.join(NOT, f'_cmd_notas_{nome}.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    junto = sum(1 for x in Pl.log if 'encosta' in x)
    print(f'== {chave}: {len(velhas)} notas apagadas, {len(G)} notas novas ({len(ms)} mergulhos); {junto} encostando em texto; '
          f'{len(lt)} trecho(s) de volta ao tipo de linha da layer')
    for x in Pl.log: print('   ', x)
    if so_comandos: return
    # grava no nome final (o SAVEAS não pode encontrar o arquivo lá) e plota com o mesmo -PLOT do carimbo QG
    if os.path.exists(final): os.replace(final, os.path.join(NOT, nome + '_anterior.dwg'))
    if os.path.exists(pdf): os.replace(pdf, os.path.join(NOT, nome + '_anterior.pdf'))
    lay = re.search(r'\(setvar "CTAB" "([^"]+)"\)', open(os.path.join(COP, f'carqg_pdf_{nome}.lsp'), encoding='ascii').read()).group(1)
    plot = os.path.join(NOT, f'pdf_{nome}.lsp'); open(plot, 'w', encoding='ascii').write(CQ.lisp_pdf(pdf[:-4], [lay]))
    plot = plot.replace('\\', '/')
    out = rever.console(trab, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % LSP, 'REVR01', '(load "%s")' % plot, '_.QUIT', '_Y'],
                        trab + '.notas.log', {'REV_CMD': cmd, 'REV_OUT': final.replace('\\', '/')})
    print('   ', out[-160:].replace('\n', ' '), '->', 'DWG OK' if os.path.exists(final) else 'DWG FALHOU', '|', 'PDF OK' if os.path.exists(pdf) else 'PDF FALHOU')


if __name__ == '__main__':
    alvo = [x for x in sys.argv[1:] if not x.startswith('--')] or ['AF-001', 'EL-001', 'EL-002', 'IN-001']
    for k in alvo: folha(k, '--so-comandos' in sys.argv)
