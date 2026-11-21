# -*- coding: utf-8 -*-
"""números da entrega R03 de Alagoinhas para o LEIA-ME e para a pergunta ao Anderson."""
import csv, collections, json, os
R = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS'
for sig, p in (('ALI', os.path.join(R, 'PRECLASH_IMP_R03')), ('ALH', os.path.join(R, 'PRECLASH_BA2_R03'))):
    L = [r for r in csv.DictReader(open(os.path.join(p, f'{sig}_preclash_AD_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';') if r['gravidade'] == 'CRÍTICA']
    A = [r for r in csv.DictReader(open(os.path.join(p, f'{sig}_preclash_A_conflitos_antes.csv'), encoding='utf-8-sig'), delimiter=';') if r['gravidade'] == 'CRÍTICA']
    c = collections.Counter(tuple(sorted((r['disc_A'], r['disc_B']))) for r in L)
    print(sig, 'antes', len(A), 'depois', len(L), c.most_common())
    if sig == 'ALI':
        est = [r for r in L if 'EST' in (r['disc_A'], r['disc_B'])]
        print('  blocos:', collections.Counter(r['rede_B'] if r['disc_B'] == 'EST' else r['rede_A'] for r in est))
        print('  outros:', [r['descricao'][:110] for r in L if 'EST' not in (r['disc_A'], r['disc_B']) and not {r['disc_A'], r['disc_B']} <= {'DRE', 'ESG'}])
P = os.path.join(R, 'PRECLASH_IMP_R03')
J = json.load(open(os.path.join(P, 'ALI_caixas_movidas.json'), encoding='utf-8'))
print('caixas (ajustes):', [(r['caixa'], r.get('desloc')) for r in J if r['status'] == 'caixa deslocada'], 'sem lugar:', [r['caixa'] for r in J if r['status'] != 'caixa deslocada'])
J = json.load(open(os.path.join(P, 'ALI_contornos.json'), encoding='utf-8'))
print('contornos:', len(J), collections.Counter(r['disc'] for r in J), sorted({(r['trecho'], r['caixa']) for r in J}))
M = json.load(open(os.path.join(P, 'ALI_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
print('mudanças por folha:', collections.Counter((m['folha'], m['tipo']) for m in M))
pr = [m['prof_topo'] for m in M if m['tipo'] == 'mergulho']; print('PROF. min/max', min(pr), max(pr))
