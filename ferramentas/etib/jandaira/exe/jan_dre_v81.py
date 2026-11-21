# -*- coding: utf-8 -*-
"""DRE-001 R02 (20/10/2026, decisões do Anderson às 20h56 e 22h21): junção V81 sob o BP4 — a DRE-121/122/124/135 desceram para
continuar a DRE-117 e a CX-32 ficou 0,24 m mais funda (CF 146,14 -> 145,90). Parte dos comandos da prancha aprovada pela Revisão
(_revisao_qualidade/_trab/_cmd_...DRE...txt, com a nota 0,54 já afastada) e só troca:
  - as notas de profundidade da cadeia (V83 0,93 -> 1,17; V85 0,98 -> 1,41; a de V84, 0,92, sai: o ramal tem 0,87 m e fica com a
    mesma profundidade da V83 — duas notas iguais lado a lado);
  - na CX-32: "CF.: 146.14" -> "CF.: 145.90" e "(01.36)" -> "(01.60)".
Valores da rodada PRECLASH_R03_CX32 (jan_prof_rodada.py). Uso: python -X utf8 jan_dre_v81.py [--so-comandos]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_revisao_qualidade as RQ
nome = RQ.FOLHAS['DRE-001']
cmd = os.path.join(RQ.TRAB, f'_cmd_{nome}.txt')
L = [l.rstrip('\n') for l in open(cmd, encoding='utf-8') if l.strip()]
TROCA = {'PROF. 0,93 m': 'PROF. 1,17 m', 'PROF. 0,98 m': 'PROF. 1,41 m'}
SAI = {'PROF. 0,92 m', 'PROF. 1,16 m'}   # V81 (1,16) e V83 (1,17) ficaram com a mesma profundidade a 1,2 m: uma nota só (Revisão, 20/10 22h41)
out = []
for l in L:
    c = l.split('\t')
    if c[0] == 'TXC' and c[5] in SAI: continue
    if c[0] == 'TXC' and c[5] in TROCA: c[5] = TROCA[c[5]]; l = '\t'.join(c)
    out.append(l)
out += ['ST\t20E8DA\tCF.: 145.90', 'ST\t20E8DB\t(01.60)']
print('\n'.join(x for x in out if x.startswith(('TXC', 'ST'))))
if '--so-comandos' not in sys.argv:
    RQ.aplicar(nome, out)
