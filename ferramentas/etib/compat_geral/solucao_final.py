# -*- coding: utf-8 -*-
"""Solução final = otimizador (solucao_dz.json) + ajustes manuais testados:
 - DRN junto à divisa sul (coletor DRN-409/411/416 e caixas de areia CA66/CA78/CA79): deslocar 1,3 m para dentro do lote
   (norte), mantendo as cotas (rede por gravidade, só translação em planta)."""
import json, csv
R = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02" + "\\"
sol = json.load(open(R + 'solucao_dz.json', encoding='utf-8'))
import sys
NORTE = (0.102428, 0.99474); D = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
alvos_seg = {'DRN-409', 'DRN-411', 'DRN-416'}; alvos_mesh = {'CA66', 'CA78', 'CA79'}
ids_s, ids_m = set(), set()
for l in open(R + r'geo_sol\DRN_segs.tsv', encoding='utf-8'):
    r = l.rstrip('\n').split('\t')
    if len(r) > 5 and r[5].split('.')[0] in alvos_seg: ids_s.add(r[1])
for l in open(R + r'geo_sol\DRN_mesh.tsv', encoding='utf-8'):
    r = l.split('\t', 7)
    if r[4] in alvos_mesh: ids_m.add(r[1])
for i in ids_s: sol['seg'][i] = {'dz': 0.0, 'dxy': [NORTE[0] * D, NORTE[1] * D]}
for i in ids_m: sol.setdefault('mesh', {})[i] = {'dxy': [NORTE[0] * D, NORTE[1] * D]}
json.dump(sol, open(R + 'solucao_final.json', 'w', encoding='utf-8'), indent=0)
print('DRN deslocados: segmentos', len(ids_s), '| caixas', len(ids_m), '| ok solucao_final.json')

