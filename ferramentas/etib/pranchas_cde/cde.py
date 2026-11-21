# -*- coding: utf-8 -*-
"""Monta o CDE local das pranchas em D:\\Projeto Modelagem\\PRANCHAS\\<ESCOLA>\\ (cópias; o Drive não é tocado) e o INDICE.md.
Uso: python -X utf8 cde.py   (depois do plotar.py)"""
import os, sys, shutil, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from originais import L
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(H, 'work')
CDE = r'D:\Projeto Modelagem\PRANCHAS'
LIB = json.load(open(os.path.join(H, 'biblioteca.json'), encoding='utf-8')) if os.path.exists(os.path.join(H, 'biblioteca.json')) else {}
NOME = {'ETIB-<ESCOLA>': '<Nome da Escola>'}      # MODELO (fictício): uma linha por escola
SUB = {'IMP': 'Implantação', 'CPS': 'Campo society'}
OBS = {
 'ETIB-<ESCOLA>': 'Observação curta sobre o que o Drive da construtora traz ou não traz.',
}

linhas = {}; arquivos = []
for e, s, f, rev, x, m in L:
    os.makedirs(os.path.join(CDE, e), exist_ok=True)
    if isinstance(x, tuple):
        nome = os.path.splitext(os.path.basename(x[1]))[0]
        pdfs = sorted(glob.glob(os.path.join(W, nome + '__*.pdf')))
        if not pdfs: print('SEM PDF PLOTADO:', nome); continue
        dest = []
        for i, p in enumerate(pdfs):
            alvo = f'{nome}.pdf' if len(pdfs) == 1 else f'{nome}_F{i + 1}.pdf'
            shutil.copy2(p, os.path.join(CDE, e, alvo)); dest.append(alvo)
        origem = 'plotado do DWG em A0'
    else:
        alvo = os.path.basename(x); shutil.copy2(x, os.path.join(CDE, e, alvo)); dest = [alvo]; origem = 'PDF do Drive'
    arquivos += [os.path.join(CDE, e, d) for d in dest]
    linhas.setdefault(e, []).append((s, f, rev, m, dest, origem))

with open(os.path.join(H, 'arquivos.txt'), 'w', encoding='utf-8') as fo: fo.write('\n'.join(arquivos) + '\n')

out = ['# Pranchas das escolas: índice do CDE', '',
       'Atualizado em 19/10/2026. Um PDF por folha, das disciplinas do contrato (água fria, esgoto, drenagem, elétrica e incêndio; no BA2 também climatização). '
       'Cada linha diz qual versão vale hoje.', '',
       '- **Original**: a folha do projeto da construtora, na última revisão do Drive. É a que vale.',
       '- **Em revisão**: a folha está sendo refeita com as mudanças da compatibilização, no padrão de campo (traçado redesenhado, sem nuvem, notas curtas). '
       'Até a nova versão entrar aqui, vale a original listada.', '',
       'Ficam fora: folhas de base (topografia, situação, terraplanagem, pavimentação), memoriais e listas de material.', '',
       'Na biblioteca do projeto os PDFs ficam soltos, com o nome oficial da folha; no computador do escritório a mesma cópia está separada por escola em '
       '`D:\\Projeto Modelagem\\PRANCHAS\\<ESCOLA>\\`. As folhas que só existiam em DWG foram plotadas em A0 a partir do arquivo da construtora.', '']
tot = {'o': 0, 'r': 0}
for e in NOME:
    if e not in linhas: continue
    out += [f'## {NOME[e]}', '']
    if e in OBS: out += [OBS[e], '']
    out += ['| Folha | Situação | Revisão que vale | Arquivo |', '|---|---|---|---|']
    for s, f, rev, m, dest, origem in linhas[e]:
        sit = 'Em revisão' if m else 'Original'; tot['r' if m else 'o'] += 1
        arq = '<br>'.join(f'[{d}]({LIB.get(d, "/mnt/project-files/" + d)})' for d in dest)
        nota = '' if origem == 'PDF do Drive' else ' (PDF plotado do DWG)'
        out.append(f'| {SUB[s]}: {f} | {sit} | {rev}{nota} | {arq} |')
    out.append('')
out += ['## Como entra uma folha revisada', '',
        '1. O PDF novo vai para `D:\\Projeto Modelagem\\PRANCHAS\\<ESCOLA>\\` e a original que ele substitui vai para `PRANCHAS\\<ESCOLA>\\_SUPERADAS\\`.',
        '2. A linha da folha passa a "Modificada", com a revisão nova e o arquivo novo.',
        '3. O PDF novo e este índice sobem para a biblioteca do projeto.', '',
        f'Total: {tot["o"] + tot["r"]} folhas, {tot["r"]} em revisão.']
open(os.path.join(CDE, 'PRANCHAS_INDICE.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
if os.path.exists(os.path.join(CDE, 'INDICE.md')): os.remove(os.path.join(CDE, 'INDICE.md'))
if os.path.exists(os.path.join(CDE, 'arquivos.txt')): os.remove(os.path.join(CDE, 'arquivos.txt'))
print(len(arquivos), 'PDFs em', CDE, '|', round(sum(os.path.getsize(a) for a in arquivos) / 1e6, 1), 'MB |', tot)
