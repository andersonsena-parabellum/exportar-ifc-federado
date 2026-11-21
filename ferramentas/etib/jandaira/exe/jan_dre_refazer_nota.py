# -*- coding: utf-8 -*-
"""DRE-001 R02 (20/10/2026, Revisão de qualidade, 3ª conferência): só a nota "PROF. 0,54 m" (DRE-017) ainda encostava no texto
"BANCO H=0.75m" da arquitetura (bloco). Refaz só ela: parte dos comandos da 2ª passada (_revisao_qualidade/_trab/_cmd_...txt),
mantém as outras 9 notas onde a Revisão aprovou, e põe esta pela regra atual (texto de bloco com retângulo conservador e busca em
volta até 4 m), desviando das 9. Gera o DWG e o PDF de novo na pasta de preparo.
Uso: python -X utf8 jan_dre_refazer_nota.py "PROF. 0,54 m" [--so-comandos]"""
import os, sys, re, math, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_revisao_qualidade as RQ
ab, S = RQ.ab, RQ.S
alvo = sys.argv[1]
nome = RQ.FOLHAS['DRE-001']; chave = 'DRE-001'
cmd0 = os.path.join(RQ.TRAB, f'_cmd_{nome}.txt')
L0 = [l.rstrip('\n') for l in open(cmd0, encoding='utf-8') if l.strip()]
ler = os.path.join(RQ.COP, nome + '_ler.dxf')
E = ab.entidades(ler, arcos=True, blocos=True)
apagar = {l.split('\t')[1] for l in L0 if l.startswith('DEL\t')}
Pl = ab.Plano([e for e in E if e['h'] not in apagar], tol=S.EXECUTIVO_TOL, ext=S.EXECUTIVO_EXT, caixa_sem_simbolo=S.EXECUTIVO_CAIXA_SEM_SIMBOLO)
Pl.alt_nota = S.EXECUTIVO_NOTA_ALT
H = {e['h']: e for e in E}
rot, tt = S.TRANSF_DWG[S._DWG[chave]]; a = math.radians(rot); Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
loc = lambda P: np.array([Rm.T @ (np.asarray(p[:2], float) - np.array(tt)) for p in P])
# inicializa o ocupado e põe as 9 notas que ficam como "notas novas" (nada cai em cima delas)
Pl.nota(np.array([[0.0, 0.0], [1.0, 0.0]]), 'X', 'init'); Pl.L.clear(); Pl.log.clear(); Pl.notas_novas.clear()
fica = []
for l in L0:
    c = l.split('\t')
    if c[0] == 'TXC' and c[5] == alvo: continue
    fica.append(l)
    if c[0] == 'TXC':
        h = H[c[1]]['alt']; Pl.notas_novas.append(ab._ret(np.array([float(c[2]), float(c[3])]), float(c[4]), len(c[5]) * h * 0.85, h))
ms = [m for m in RQ.M if m['folha'] == chave and m['tipo'] == 'mergulho' and m.get('nota') == alvo]
m = ms[0]
Pl.nota(loc(m['planta']), alvo, m['trecho'])
print('\n'.join(Pl.log)); print(Pl.L[-1])
if '--so-comandos' not in sys.argv:
    RQ.aplicar(nome, fica + Pl.L)
