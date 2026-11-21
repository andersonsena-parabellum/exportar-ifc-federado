# -*- coding: utf-8 -*-
"""MODELO: congela o terreno da escola em escolas/dados/<escola>_terreno.npz para o preclash.
Entrada: pontos do terreno em UTM (CSV E;N;Z), vindos do IMP as built (lido no Revit), da topografia (TOP/TER) ou das curvas.
Saída: pts (n,3) e, opcional, tri (Delaunay), platôs (plat_n, plat_xy, plat_z) e linhas da arquitetura da situação (arq).
Depois, se o terreno divergir das cotas da base (CT das caixas, implantação, TOP, TER), ajustar com preclash.terreno.ajustar.
Uso: etib-python preclash/escolas/exemplo_terreno.py <pontos.csv>"""
import os, sys, csv
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'exemplo_terreno.npz')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(sys.argv[1], encoding='utf-8') as f:
    pts = np.array([[float(r[0]), float(r[1]), float(r[2])] for r in csv.reader(f, delimiter=';') if r and r[0][0].isdigit()])
np.savez_compressed(OUT, pts=pts, fonte=np.array(os.path.basename(sys.argv[1])))
print('gravado', OUT, '| pontos', len(pts))
