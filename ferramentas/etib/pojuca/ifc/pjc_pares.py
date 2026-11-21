# -*- coding: utf-8 -*-
"""pares críticos da rodada anterior -> ajustes em planta da próxima (pjc_ajustes.py): contornos curtos e caixas a deslocar.
Acumula com o arquivo existente (os ajustes já feitos somem dos críticos e têm de continuar valendo).
Uso: python cat_pares.py [pasta da rodada] [cenário]"""
import csv, json, os, sys
pasta = sys.argv[1] if len(sys.argv) > 1 else r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS\PRECLASH_2026-10-25'
cen = sys.argv[2] if len(sys.argv) > 2 else 'AD'
fn = os.path.join(pasta, 'PJC_ajustes_pares.json')
J = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else {'contornos': [], 'caixas': []}
cont = {tuple(x) for x in J['contornos']}; cxs = set(J['caixas'])
PRESS = ('ELE', 'SDAI', 'HID', 'AF'); MOV = ('ELE', 'SDAI', 'AF')
for r in csv.DictReader(open(os.path.join(pasta, f'PJC_preclash_{cen}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
    if r['gravidade'] != 'CRÍTICA' or '(canaleta)' in r['trecho_A'] + r['trecho_B']: continue
    a, b = (r['disc_A'], r['trecho_A']), (r['disc_B'], r['trecho_B'])
    if r['tipo'] == 'tubo×caixa':
        caixa_movel = b[0] in MOV and 'Reservatório' not in b[1] and not b[1].startswith('Registro') and 'Bomba' not in b[1]
        if caixa_movel: cxs.add(b[1])                                       # caixa de passagem/alçapão no caminho: a caixa anda
        elif a[0] in PRESS and b[0] in ('DRE', 'ESG', 'EST'): cont.add((a[1], b[1]))   # pressurizada atravessa PV/peça: contorno
    elif r['tipo'] == 'caixa×caixa':
        for d, n in (a, b):
            if d in MOV: cxs.add(n)
json.dump({'contornos': sorted(cont), 'caixas': sorted(cxs)}, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cont), 'contornos', len(cxs), 'caixas ->', fn)
