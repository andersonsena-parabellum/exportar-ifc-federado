# -*- coding: utf-8 -*-
"""Pojuca — quanto do projeto (fase 2) o as built do IFC cobre, e o contrário, por disciplina (folga de 0,60 m em planta)."""
import csv, os
import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union
D = os.path.dirname(os.path.abspath(__file__)); REL = r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS'
R = list(csv.DictReader(open(os.path.join(D, 'PJC_ifc_asbuilt_redes.csv'), encoding='utf-8-sig'), delimiter=';'))
FAM = {'AF': ('Tubos - diâmetro interno comercial', 'Tubo multicamada'), 'ESG': ('Tubo PVC ponta-bolsa',),
       'DRE': ('Série R', 'PVC Liso', 'corrugado perfurado'), 'ELE': ('Eletroduto',), 'PCI': ('CPVC Fire',)}
def seg(r): return LineString([(float(r['E_ini']), float(r['N_ini'])), (float(r['E_fim']), float(r['N_fim']))])
def proj(d):
    if d in ('ESG', 'DRE'):
        out = []
        for fn in ({'ESG': ['PJC_fase2_ESG_trechos.csv'], 'DRE': ['PJC_fase2_DRE_trechos.csv', 'PJC_fase2_CPS_DRE_trechos.csv']}[d]):
            for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
                out.append((r['trecho'], LineString([(float(r['E_ini']), float(r['N_ini'])), (float(r['E_fim']), float(r['N_fim']))])))
        return out
    fns = {'AF': ['PJC_fase2_AF_trechos.csv'], 'ELE': ['PJC_fase2_ELE_trechos.csv', 'PJC_fase2_CPS_ELE_trechos.csv'], 'PCI': ['PJC_fase2_PCI_trechos.csv']}[d]
    out = []
    for fn in fns:
        for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
            P = [tuple(float(v) for v in xy.split(',')) for xy in r['vertices_UTM'].split(';') if xy]
            if len(P) > 1: out.append((r['trecho'], LineString(P)))
    return out
for d, fams in FAM.items():
    A = [seg(r) for r in R if r['tipo'] == 'flowsegment' and r['tipo_familia'].startswith('Forma direta') and any(f in r['tipo_familia'] for f in fams) and float(r['L']) > 0.05]
    UA = unary_union(A).buffer(0.60); P = proj(d); UP = unary_union([g for _, g in P]).buffer(0.60)
    Lp = sum(g.length for _, g in P); Lp_cob = sum(g.intersection(UA).length for _, g in P)
    La = sum(a.length for a in A); La_cob = sum(a.intersection(UP).length for a in A)
    fora = sorted(((t, g.length - g.intersection(UA).length) for t, g in P), key=lambda x: -x[1])
    print(f'{d}: projeto {Lp:.0f} m, {100 * Lp_cob / max(Lp, 1):.0f}% com as built a 0,6 m | as built {La:.0f} m, {100 * La_cob / max(La, 1):.0f}% sobre o projeto')
    print('   projeto sem as built:', ', '.join(f'{t} {x:.0f}' for t, x in fora[:25] if x > 2))
