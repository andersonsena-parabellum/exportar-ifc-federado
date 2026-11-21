# -*- coding: utf-8 -*-
"""Jandaíra R03 (20/10/2026): correções de prancha apontadas pela Revisão de qualidade, preparadas fora da entrega
(EXECUTIVO_R03_IFC/_revisao_qualidade/, DWG + PDF A0) para trocar na pasta de envio e no CDE só depois do ok do Anderson:
  - trecho redesenhado que saiu com tipo de linha "Continuous" numa rede tracejada pela layer (EL-002: 7 trechos) -> ByLayer
    (causa: o entmake sem o grupo 6 usa o CELTYPE do desenho; o revisao.lsp agora põe ByLayer no que o original não declara);
  - nota de profundidade em cima de texto da prancha (DRE-001: "PROF. 1,04 m" sobre "DEP. DE") -> apaga e põe de novo pelo
    asbuilt.nota (MTEXT de várias linhas agora conta a altura inteira).
Uso: python -X utf8 jan_revisao_qualidade.py [--so-comandos]"""
import os, sys, re, math, json, shutil
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever, dxfgeo
import carimbo_qg as CQ
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
R3 = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'; COP = os.path.join(R3, '_copias')
OUT = os.path.join(R3, '_revisao_qualidade'); TRAB = os.path.join(OUT, '_trab'); PDF = os.path.join(OUT, 'PDF')
LSP = r'D:/Projeto Modelagem/FERRAMENTAS/preclash/executivo/revisao.lsp'
LOGOS = [x for x in os.listdir(R3) if x.startswith('CARIMBO_QG_logo_') and x.endswith('.png')]
NOTA = re.compile(r'^PROF\. \d+,\d\d m$')
M = json.load(open(os.path.join(R3, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
# EL-002 (tipo de linha) e as notas de AF/EL/IN saem pelo jan_notas_r03.py com JAN_NOTAS_SAIDA = esta pasta
FOLHAS = {'DRE-001': '24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R02'}


def brutos(fn):
    _, model = dxfgeo.parse(fn); out = {}
    for typ, data in model:
        d = dxfgeo._first(data)
        if 5 in d and str(d.get(67, '0')).strip() != '1': out[str(d[5]).strip()] = (typ, d)
    return out


def planejar(chave):
    nome = FOLHAS[chave]
    ler = os.path.join(COP, nome + '_ler.dxf'); orig = os.path.join(COP, os.path.splitext(os.path.basename(S._DWG[chave]))[0] + '.dxf')
    B, B0 = brutos(ler), brutos(orig); L = []
    # 1) tipo de linha: linha nova "Continuous" na layer cujas linhas originais não declaram tipo (seguem a layer)
    lay_bl = {d.get(8) for t, d in B0.values() if t in ('LINE', 'LWPOLYLINE') and d.get(6) is None}
    for h, (t, d) in B.items():
        if h in B0 or t not in ('LINE', 'LWPOLYLINE'): continue
        if str(d.get(6, '')).upper() == 'CONTINUOUS' and d.get(8) in lay_bl: L.append(f'LT\t{h}\tByLayer')
    nlt = len(L)
    # 2) nota de profundidade em cima de texto da prancha
    E = ab.entidades(ler, arcos=True, blocos=True); h0 = set(B0)
    notas = [e for e in E if e['typ'] == 'TEXT' and NOTA.match(str(e.get('txt', '')).strip()) and e['h'] not in h0]
    Pl0 = ab.Plano([e for e in E if e not in notas], tol=S.EXECUTIVO_TOL, ext=S.EXECUTIVO_EXT, caixa_sem_simbolo=S.EXECUTIVO_CAIXA_SEM_SIMBOLO)
    ret = lambda t: ab._ret(*(lambda a, tw, th, p0: (p0, a, tw, th))(*Pl0._ret_texto(t)))

    txts = [(t, ret(t)) for t in Pl0.textos] + [(t, ret(t)) for t in E if t['typ'] == 'BTXT']      # BTXT: texto de bloco (arquitetura)
    # todas as notas de profundidade da folha são postas de novo pela regra atual (desvia de texto de bloco, atributo e círculo)
    ruins = notas if '--todas' in sys.argv else [n for n in notas if any(ab._sobrepoe(ret(n), R) for _, R in txts)]
    rot, tt = S.TRANSF_DWG[S._DWG[chave]]; a = math.radians(rot); Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda P: np.array([Rm.T @ (np.asarray(p[:2], float) - np.array(tt)) for p in P])
    Pl = ab.Plano([e for e in E if e not in ruins], tol=S.EXECUTIVO_TOL, ext=S.EXECUTIVO_EXT, caixa_sem_simbolo=S.EXECUTIVO_CAIXA_SEM_SIMBOLO)
    Pl.alt_nota = S.EXECUTIVO_NOTA_ALT
    for n in ruins:
        txt = n['txt'].strip()
        # o mergulho que gerou a nota: mesmo texto e planta mais perto da nota
        ms = [m for m in M if m['folha'] == chave and m['tipo'] == 'mergulho' and m.get('nota') == txt]
        m = min(ms, key=lambda m: np.min(np.hypot(*(loc(m['planta']) - n['p']).T))) if ms else None
        if m is None: print('  sem mergulho para', txt); continue
        L.append(f'DEL\t{n["h"]}'); Pl.nota(loc(m['planta']), txt, m['trecho'])
    L += Pl.L
    print(f'== {chave}: {nlt} trecho(s) com tipo de linha ByLayer; {len(ruins)} nota(s) em cima de texto refeitas')
    for x in Pl.log: print('   ', x)
    return nome, L


def aplicar(nome, L):
    os.makedirs(TRAB, exist_ok=True); os.makedirs(PDF, exist_ok=True)
    trab = os.path.join(TRAB, nome + '.dwg'); shutil.copy2(os.path.join(R3, nome + '.dwg'), trab)
    for lg in LOGOS: shutil.copy2(os.path.join(R3, lg), os.path.join(TRAB, lg)); shutil.copy2(os.path.join(R3, lg), os.path.join(OUT, lg))
    cmd = os.path.join(TRAB, f'_cmd_{nome}.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    dst = os.path.join(OUT, nome + '.dwg')
    if os.path.exists(dst): os.replace(dst, os.path.join(TRAB, nome + '_anterior.dwg'))
    lay = re.search(r'\(setvar "CTAB" "([^"]+)"\)', open(os.path.join(COP, f'carqg_pdf_{nome}.lsp'), encoding='ascii').read()).group(1)
    pdf = os.path.join(PDF, nome)
    if os.path.exists(pdf + '.pdf'): os.replace(pdf + '.pdf', os.path.join(TRAB, nome + '_anterior.pdf'))
    fpl = os.path.join(TRAB, f'pdf_{nome}.lsp'); open(fpl, 'w', encoding='ascii').write(CQ.lisp_pdf(pdf, [lay]))
    out = rever.console(trab, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % LSP, 'REVR01', '(load "%s")' % fpl.replace('\\', '/'), '_.QUIT', '_Y'],
                        trab + '.rq.log', {'REV_CMD': cmd, 'REV_OUT': dst.replace('\\', '/')})
    print('   ', out[-120:].replace('\n', ' '), '->', 'DWG OK' if os.path.exists(dst) else 'DWG FALHOU', '|', 'PDF OK' if os.path.exists(pdf + '.pdf') else 'PDF FALHOU')


if __name__ == '__main__':
    for k in FOLHAS:
        nome, L = planejar(k)
        if L and '--so-comandos' not in sys.argv: aplicar(nome, L)
