# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — segunda linha no quadro de revisões: as pranchas refeitas do original já saem do jan_carimbo.py na revisão
publicada antes (linha 02 de 19/10); aqui cada uma vira a revisão seguinte (linha nova, data de hoje, descrição própria) e ganha o
PDF A0. As intermediárias (DWG e PDF da revisão anterior) vão para _copias/.
Uso: JAN_EXEC_OUT=<pasta> JAN_CARIMBO_DATA=20/10/2026 JAN_CARIMBO_DESC="..." python -X utf8 jan_carimbo_seguinte.py"""
import os, sys, glob, re, shutil, json
OUT = os.environ['JAN_EXEC_OUT']; COP = os.path.join(OUT, '_copias'); PDF = os.path.join(OUT, 'PDF')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_carimbo as JC, rever
sys.stdout.reconfigure(encoding='utf-8')
bases = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(OUT, '*-R0[0-9].dwg')))
R = []
for b in bases:
    # a prancha da revisão anterior passa a ser a "revisada" de entrada, com o DXF do papel em _copias
    rev = os.path.join(OUT, b + '_REVISADO.dwg'); shutil.move(os.path.join(OUT, b + '.dwg'), rev)
    dxf = os.path.join(COP, b + '.dxf')
    rever.console(rev, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                  rev + '.dxf.log', {'DXF_OUT': dxf.replace('\\', '/')})
    for p in glob.glob(os.path.join(PDF, b + '_*.pdf')): shutil.move(p, os.path.join(COP, os.path.basename(p)))
    R.append(JC.processar(b))
    shutil.move(rev, os.path.join(COP, os.path.basename(rev)))
json.dump(R, open(os.path.join(OUT, 'JAN_carimbo_seguinte.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
