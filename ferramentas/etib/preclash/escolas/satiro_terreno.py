# -*- coding: utf-8 -*-
"""Sátiro Dias — congela o TERRENO do preclash em escolas/dados/satiro_terreno.npz.
Desde 19/10/2026: terreno acabado do IMP as built (sólidos topográficos + pisos lidos no Revit; fase3_sat.TerrenoIMP,
grade de 1 m). O provisório anterior (platôs TER + talude + TOP/DRE-002) fica em satiro_terreno_provisorio.npz;
para voltar a ele: SAT_TERRENO=provisorio.
Só LÊ o código e os dados da fase 3 (FERRAMENTAS/georef_dxf/satiro/fase3_sat.py).
Uso: .venv/Scripts/python.exe -X utf8 preclash/escolas/satiro_terreno.py
"""
import os, sys
import numpy as np
SAT = r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro'
sys.path.insert(0, SAT)
import fase3_sat as f3          # noqa: E402
from esg_sat import arq_sit     # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'satiro_terreno.npz')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

if os.environ.get('SAT_TERRENO') == 'provisorio':
    ter = f3.Terreno(); fonte = 'fase3_sat.Terreno (platôs TER-001 + talude + TOP-001/DRE-002), provisório'
else:
    ter = f3.TerrenoIMP(); fonte = 'IMP as built (Revit, 19/10/2026): sólidos topográficos + pisos, grade de 1 m'
Y = ter.Y
tri = ter.tri.triangles
segs = np.array(arq_sit(), float)           # linhas da arquitetura da SIT (n, 2, 2)
extra = {}
if ter.plat:
    extra = dict(plat_n=np.array([len(P) for P, z in ter.plat]), plat_xy=np.vstack([P for P, z in ter.plat]), plat_z=np.array([z for P, z in ter.plat]))
np.savez_compressed(OUT, pts=Y, tri=tri, arq=segs, fonte=np.array(fonte), **extra)
print('gravado', OUT, '| pontos', len(Y), '| triângulos', len(tri), '| platôs', [round(z, 2) for P, z in ter.plat], '| linhas SIT', len(segs))
