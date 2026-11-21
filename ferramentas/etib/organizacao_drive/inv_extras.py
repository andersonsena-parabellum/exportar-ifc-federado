"""Acrescenta ao fim do INVENTARIO.md a seção das redes externas fora da "4 - IMPLANTAÇÃO" (lote extras).
Não regenera o arquivo: as threads de cada escola também escrevem nele.

uso: python -I inv_extras.py <CHAVE_ESCOLA>
"""
import json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
k = sys.argv[1]
BASE = r'D:\Projeto Modelagem'
MARK = '## Acréscimo 18/10/2026 — redes externas fora da pasta "4 - IMPLANTAÇÃO"'
man = [m for m in json.load(open('manifest.json', encoding='utf-8')) if m['school'] == k and m.get('lote') == 'extras-2026-10-18']
d = man[0]['dir']
inv = os.path.join(BASE, d, 'INVENTARIO.md')
txt = open(inv, encoding='utf-8').read()
if MARK in txt:
    txt = txt[:txt.index(MARK)].rstrip() + '\n'

def rev(n):
    m = re.findall(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)', n)
    return f'R{int(m[-1]):02d}' if m else '—'

# blocos de edificação com disciplinas do escopo, que ficaram de fora
DISC = r'[ÁA]GUA|ESGOTO|DRENAGEM|EL[ÉE]TRIC|INC[ÊE]NDIO|CLIMATIZA'
L = json.load(open(f'listagens_2026-10-18/drive_listing_{k}.json', encoding='utf-8'))
blocos = collections.defaultdict(set)
for x in L:
    p = x.get('path', ''); parts = p.split('/')
    if x.get('d') or x.get('err') or len(parts) < 4 or re.search('OBSOLET', p, re.I):
        continue
    if parts[1].startswith(('1 - ', '4 - IMPLANTA', 'AVCB', 'LEGALIZA', 'VIABILIDADE')) or 'CAMPO' in parts[1]:
        continue
    if re.search(DISC, parts[2], re.I) and not re.search(r'IMPLANTA', parts[2], re.I):
        blocos[parts[1].strip()].add(re.sub(r'^\d+\s*-\s*', '', parts[2]).strip().title())

S = ['', MARK, '',
     'Critério: entram as redes externas que estão guardadas fora da pasta de implantação — o **campo society** (área aberta: '
     'drenagem, iluminação/alimentação e incêndio) e documentos de **implantação** dentro da pasta de um bloco. '
     'Projetos de **edificação** (instalações internas de guarita, vestiário, quadra coberta, subestação, casa de gás, '
     'reservatórios, blocos de salas, teatro, refeitório) não fazem parte da "modelagem da implantação" da proposta e não foram baixados.',
     '']
groups = collections.OrderedDict()
for m in sorted(man, key=lambda m: (m['dest'], m['name'])):
    groups.setdefault(m['dest'], []).append(m)
tot = 0
for g, its in groups.items():
    S += [f'**`{g}\\`**', '', '| Arquivo | Rev. | MB | Origem no Drive | Conferido |', '|---|---|---|---|---|']
    for m in its:
        f = os.path.join(BASE, d, m['dest'], m['name'])
        ok = os.path.exists(f) and os.path.getsize(f) == m['size']
        tot += m['size']
        S.append(f"| {m['name']} | {rev(m['name'])} | {m['size']/1e6:.1f} | {m['origem']} | {'ok' if ok else 'FALTA'} |")
    S.append('')
S.append(f'Total do acréscimo: {len(man)} arquivos, {tot/1e6:.0f} MB. Não abri esses DWGs: o sistema de coordenadas deles fica para o referenciamento conferir.')
if k == 'POJUCA':
    S.append('')
    S.append('`IMP_QUADRA\` são pranchas de implantação feitas pelo projetista da quadra (código PI000, com uma subpasta "POJUCA IMPLANTAÇÃO NOVA" no Drive). Cobrem urbanismo, elétrica, água fria e PCI da implantação, diferentes das pranchas 24-049 da pasta principal: comparar as duas antes de modelar. GLP e o arquivo da subestação ficaram de fora.')
S.append('')
if blocos:
    S.append('**Projetos de edificação no Drive com disciplinas do escopo, não baixados:** ' +
             '; '.join(f"{b} ({', '.join(sorted(v))})" for b, v in sorted(blocos.items())) + '.')
    S.append('')
open(inv, 'w', encoding='utf-8').write(txt + '\n'.join(S))
print('ok', inv, len(man), 'arquivos')
