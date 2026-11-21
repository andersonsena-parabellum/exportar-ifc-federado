# -*- coding: utf-8 -*-
"""Gera o pranchas.json lido pela aba "Pranchas" do visualizador (artifact Pré-compatibilização ETIB), a partir da lista
de folhas (originais.py) e dos IDs do Google Drive (drive_ids.py, pasta ETIB_PRANCHAS_CDE).
Situação: 'Original' (sem revisão), 'Em revisão' (vale a original até a nova versão), 'Modificada' (MODIFICADAS abaixo).
Uso: python -X utf8 pranchas_json.py [saida.json]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from originais import L
from drive_ids import IDS, PASTAS, PASTA, INDICE

from originais import CTR
SIGLA = {'ETIB-<ESCOLA>': 'EXE'}                  # MODELO (fictício)
NOME = {'ETIB-<ESCOLA>': '<Nome da Escola>'}
SUB = {'IMP': 'Implantação', 'CPS': 'Campo society'}
OBS = {'ETIB-<ESCOLA>': 'Observação curta que aparece no topo da escola na aba Pranchas.'}
# folhas já substituídas pela versão revisada: (escola, sub, código da folha) -> {'rev': 'R0x', 'id': '<id do Drive>', 'arquivo': '<nome.pdf>'}
MODIFICADAS = {
    ('ETIB-<ESCOLA>', 'IMP', 'AGF-001'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': f'{CTR}-EXE-XXX-ETIB-IMP-PE-AGF-001-HIG-R03.pdf'},
}

def url(i): return f'https://drive.google.com/file/d/{i}/view'
def baixar(i): return f'https://drive.google.com/uc?export=download&id={i}'


esc = {}
for e, s, f, rev, x, m in L:
    nome = os.path.splitext(os.path.basename(x[1] if isinstance(x, tuple) else x))[0]
    i = IDS[nome[len(CTR) + 1:]]
    item = {'grupo': SUB[s], 'folha': f, 'situacao': 'Em revisão' if m else 'Original', 'rev': rev, 'arquivo': nome + '.pdf',
            'ver': url(i), 'baixar': baixar(i)}
    mod = MODIFICADAS.get((e, s, f.split()[0]))
    if mod:
        item.update(situacao='Modificada', rev=mod['rev'], arquivo=mod['arquivo'], ver=url(mod['id']), baixar=baixar(mod['id']))
    esc.setdefault(e, []).append(item)
saida = {'atualizado': time.strftime('%d/%m/%Y'), 'pasta': f'https://drive.google.com/drive/folders/{PASTA}',
         'indice': url(INDICE),
         'escolas': [{'sigla': SIGLA[e], 'nome': NOME[e], 'pasta': f'https://drive.google.com/drive/folders/{PASTAS[e]}',
                      'obs': OBS.get(e, ''), 'folhas': esc[e]} for e in NOME if e in esc]}
fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pranchas.json')
json.dump(saida, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(fn, sum(len(v) for v in esc.values()), 'folhas')
