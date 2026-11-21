# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — carimbo QG as built (aprovado pelo Anderson às 14h38) nas 8 pranchas modificadas, DWG e PDF A0.
Parte da prancha revisada ANTES do carimbo antigo ganhar as linhas novas (<original>_REVISADO.dwg) e passa as linhas novas do
quadro de revisões direto ao carimbo novo:
  - a 1ª tentativa direto sobre a R03 deixou as linhas que acrescentamos soltas acima do quadro (o leitor do carimbo só pega
    o que está até a última linha horizontal do quadro antigo) e, na IN-001, os textos do título antigo por baixo do novo (layer
    diferente de ARQ_TXT);
  - aqui as linhas novas entram pela lista de revisões e tudo o que estiver inteiro dentro do carimbo antigo sai, de qualquer layer.
Uso: python -X utf8 jan_carimbo_qg.py"""
import os, sys, glob, shutil, re
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import carimbo_qg as CQ
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS'
R3 = os.path.join(REL, 'EXECUTIVO_R03_IFC'); PDF = os.path.join(R3, 'PDF_QG'); os.makedirs(PDF, exist_ok=True)
V1 = os.path.join(R3, '_copias', 'carimbo_qg_tentativa1'); os.makedirs(V1, exist_ok=True)
L02 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'; L03 = 'AJUSTES DE COMPATIBILIZAÇÃO'
# (prancha revisada sem as linhas novas, nome final, linhas novas)
PRANCHAS = [
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03', [('02', L02), ('03', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R03', [('02', L02), ('03', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R02', [('01', L02), ('02', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R03', [('02', L02), ('03', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R03', [('02', L02), ('03', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R03_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R05', [('04', L02), ('05', L03)]),
    (os.path.join(R3, '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R03', [('02', L02), ('03', L03)]),
    (os.path.join(REL, 'EXECUTIVO_R02', '24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01_REVISADO.dwg'), '24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R02', [('02', L02)]),
]
EXTRA = []
_ler = CQ.ler_carimbo


def ler2(ent, c):
    # só acrescenta as linhas novas do quadro; o que apagar fica com a ferramenta (corrigida às 14h51: apaga o corpo do carimbo
    # antigo de qualquer layer e, na faixa do quadro, só linhas e textos — não leva o título de vista que fica logo acima)
    F, revs, hs, topo = _ler(ent, c)
    revs = [r for r in revs if r['rev'] not in {x['rev'] for x in EXTRA}] + EXTRA
    return F, revs, hs, topo


CQ.ler_carimbo = ler2
for src, nome, linhas in PRANCHAS:
    dst = os.path.join(R3, nome + '.dwg')
    if os.path.exists(dst): shutil.move(dst, os.path.join(V1, nome + '.dwg'))
    shutil.copy2(src, dst)
    EXTRA[:] = [dict(rev=r, data='OUT/2026', desc=d, resp='POPULUS') for r, d in linhas]
    print('==', nome)
    # código da folha: o carimbo antigo está na revisão de partida -> FOLHA na revisão nova (CODIGO e ARQUIVO saem do nome do DWG)
    cp0 = CQ.trocar(dst, data='20/10/2026', so_ler=True)['carimbos'][0]['campos']; f0 = cp0.get('FOLHA', '')
    cmp = {'FOLHA': re.sub(r'R\d\d$', nome[-3:], f0)} if f0 else {}
    if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'      # o carimbo antigo só tinha o rótulo (planta + detalhes)
    CQ.trocar(dst, pdf_dir=PDF, data='20/10/2026', campos=cmp or None)
