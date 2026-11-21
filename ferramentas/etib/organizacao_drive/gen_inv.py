"""Gera <ESCOLA>\\INVENTARIO.md a partir do manifesto, das seleções e das listagens do Drive.

uso: python -I gen_inv.py <CHAVE_ESCOLA>
"""
import json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
k = sys.argv[1]
DATA = sys.argv[2] if len(sys.argv) > 2 else '18/10/2026'
BASE = r'D:\Projeto Modelagem'
INFO = {
    'CATU': ('ETIB Catu-BA', 'CAU', 'CATU', '004-25-09-2026-05-12-QG as built Catu', '5-CATU'),
    'SATIRO-DIAS': ('ETIB Sátiro Dias-BA', 'STK', 'SÁTIRO DIAS', '004-25-01-2026-04-30-QG as built Sátiro Dias', '8-SÁTIRO DIAS'),
    'POJUCA': ('ETIB Pojuca-BA', 'PJC', 'POJUCA', '004-25-10-2026-05-12-QG as built Pojuca', '7-POJUCA'),
    'APORA-PROF-AUREA': ('ETIB Aporá – Prof. Áurea (sede)-BA', 'APR-CTO', 'APORÁ - PROF. ÁUREA', '004-25-02-2026-03-31-QG as built Aporá sede', '4-APORÁ PROF. (SEDE)'),
    'APORA-ITAMIRA': ('ETIB Aporá – Itamira-BA', 'APR-ITA', 'APORÁ ITAMIRA', '004-25-03-2026-03-31-QG as built Aporá Itamira', '3-APORÁ ITAMIRA'),
    'JANDAIRA': ('ETIB Jandaíra-BA', 'JDI', 'JANDAÍRA', '004-25-10-2026-05-12-QG as built Jandaíra', '6-JANDAÍRA'),
    'OLINDINA': ('ETIB Olindina-BA', 'ONN', 'OLINDINA', '004-25-01-2026-03-31-QG as built Olindina', '2-OLINDINA'),
    'ALAGOINHAS': ('ETIB Alagoinhas-BA', 'ALH', 'ALAGOINHAS', '004-25-10-2026-05-12-QG as built Alagoinhas', '1-ALAGOINHAS'),
}
nome, sigla, pasta_drive, pasta_asb, pasta_ifc = INFO[k]
NOTAS = json.load(open('notas.json', encoding='utf-8')).get(k, [])
man = [m for m in json.load(open('manifest.json', encoding='utf-8')) if m['school'] == k]
d = man[0]['dir']
CATN = {'00_BASE': 'Base (SIT, topografia, terraplanagem, pavimentação)', '01_AF': 'Água fria (AF)',
        '02_ESG': 'Esgoto (ESG)', '03_DRE': 'Drenagem (DRE)', '04_ELE': 'Elétrica (ELE)',
        '05_PCI': 'Incêndio (PCIP)', '06_CLI': 'Climatização (CLI)'}
subs = ['BA2'] if k == 'ALAGOINHAS' else ['IMP']
sels = {s: json.load(open(f'sel/{k}_{s}.json', encoding='utf-8')) for s in subs}

def rev(n):
    m = re.findall(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)', n)
    return f'R{int(m[-1]):02d}' if m else '—'

def mb(b):
    return f'{b/1e6:.1f}'

def present(path):
    p = os.path.join(BASE, d, path)
    return os.path.exists(p)

L = []
L.append(f'# Inventário — {nome}')
L.append('')
L.append(f'Contrato 24-049 (Construtora QG / CONDER). Atualizado em {DATA} pela thread "Organização dos arquivos das escolas".')
L.append('')
if k == 'ALAGOINHAS':
    L.append('**Escopo (proposta comercial):** modelagem do **bloco BA2** (HIDRO, ELE, CLI, PCIP) e da **implantação** (HIDRO, ELE, CLI, PCIP) + compatibilização. HIDRO = AF, ESG e drenagem.')
else:
    L.append('**Escopo (proposta comercial):** modelagem da **implantação** — HIDRO (AF, ESG, drenagem), ELE e PCIP — + compatibilização. Fora: ETE, GLP, CFTV/dados, energia solar, contenção, paisagismo.')
L.append('')
L.append(f'**Fontes no Drive (somente leitura, não mexer):** `CT 049-2024 › {pasta_drive}` (projetos) e `CT049_2024 › {pasta_asb}` (RVTs as built). '
         'Regra de seleção: só a última revisão de cada documento, nada de pastas OBSOLETO(S).')
L.append('')

# ---------- resumo por disciplina
L.append('## Resumo por disciplina')
L.append('')
for s in subs:
    sel = sels[s]['selected']
    L.append(f'**{"Bloco BA2" if s == "BA2" else "Implantação"}**')
    L.append('')
    L.append('| Disciplina | DWG | Prancha PDF | Memorial / documentos | Situação |')
    L.append('|---|---|---|---|---|')
    cats = ['01_AF', '02_ESG', '03_DRE', '04_ELE', '05_PCI'] + (['06_CLI'] if s == 'BA2' else [])
    if s == 'IMP':
        cats = ['00_BASE'] + cats
    extra = [m for m in man if m['dest'].startswith(f'PROJETO_ORIGINAL\\{s}\\')]
    for c in cats:
        its = [m for m in extra if m['dest'].endswith(c)]
        dwg = [m for m in its if m['name'].lower().endswith('.dwg')]
        pdf = [m for m in its if m['name'].lower().endswith('.pdf') and re.search(r'-PE-', m['name'])]
        mem = [m for m in its if not m['name'].lower().endswith('.dwg') and not (m['name'].lower().endswith('.pdf') and re.search(r'-PE-', m['name']))]
        def lst(x):
            return ', '.join(sorted({rev(m['name']) for m in x})) if x else '—'
        falta = []
        if not dwg: falta.append('sem DWG')
        if not pdf and c != '00_BASE': falta.append('sem prancha PDF')
        if not mem and c not in ('00_BASE',): falta.append('sem memorial')
        sit = 'completo' if not falta else 'falta no Drive: ' + ', '.join(falta)
        L.append(f'| {CATN[c]} | {len(dwg)} ({lst(dwg)}) | {len(pdf)} ({lst(pdf)}) | {len(mem)} | {sit} |')
    L.append('')
if NOTAS:
    L.append('**Observações**')
    L.append('')
    for n in NOTAS:
        L.append(f'- {n}')
    L.append('')

# ---------- baixado
L.append('## Baixado (o que está nesta pasta)')
L.append('')
groups = collections.OrderedDict()
for m in sorted(man, key=lambda m: (m['dest'], m['name'])):
    groups.setdefault(m['dest'], []).append(m)
tot = 0
for g, its in groups.items():
    L.append(f'**`{g}\\`**')
    L.append('')
    L.append('| Arquivo | Rev. | MB | Origem no Drive | Conferido |')
    L.append('|---|---|---|---|---|')
    for m in its:
        ok = os.path.exists(os.path.join(BASE, d, m['dest'], m['name'])) and \
             os.path.getsize(os.path.join(BASE, d, m['dest'], m['name'])) == m['size']
        tot += m['size']
        orig = m['origem'].replace('|', '/')
        L.append(f"| {m['name']} | {rev(m['name'])} | {mb(m['size'])} | {orig} | {'ok' if ok else 'FALTA'} |")
    L.append('')
L.append(f'Total: {len(man)} arquivos, {tot/1e6:.0f} MB. "Conferido" = arquivo presente com o mesmo tamanho em bytes do Drive.')
L.append('')

# ---------- não baixado
L.append('## No Drive, mas não baixado (de propósito)')
L.append('')
for s in subs:
    sl = sels[s]
    if sl['older_revisions']:
        L.append(f'- **Revisões anteriores** ({len(sl["older_revisions"])}): ' + '; '.join(sorted({o.split('/')[-1] for o in sl['older_revisions']})))
    nobs = [e for e in sl['excluded'] if not re.search(r'\.(png|jpe?g|ctb|log|dwl2?|bak)$', e, re.I)]
    if nobs:
        L.append(f'- **Obsoletos / ETE** ({len(nobs)} arquivos): pastas OBSOLETO(S) e estação de tratamento de esgoto.')
    if sl['out_of_scope']:
        L.append('- **Fora do escopo:** ' + ', '.join(f'{kk} ({v} arq.)' for kk, v in sorted(sl['out_of_scope'].items())))
asb = json.load(open('listagens_2026-10-18/drive_listing_PASTA2-QG.json', encoding='utf-8'))
have = {m['name'] for m in man}
rest = [x for x in asb if not x.get('d') and x.get('path', '').startswith('PASTA2-QG/' + pasta_asb + '/') and x['path'].split('/')[-1] not in have]
if k in ('JANDAIRA', 'ALAGOINHAS'):
    loc = set()
    for r, ds, fs in os.walk(os.path.join(BASE, d, 'REFERENCIAS_RVT')):
        loc.update(fs)
    rest = [x for x in rest if x['path'].split('/')[-1] not in loc]
if rest:
    L.append('- **RVTs as built não baixados** (arquitetura e metálica grandes; baixar só se um clash pedir o contorno exato): ' +
             '; '.join(f"{x['path'].split('/')[-1]} ({mb(int(x.get('size') or 0))} MB)" for x in sorted(rest, key=lambda x: x['path'])))
ifc = json.load(open('listagens_2026-10-18/drive_listing_AS-BUILT-CT049.json', encoding='utf-8'))
ifcs = [x for x in ifc if not x.get('d') and x.get('path', '').startswith('AS-BUILT-CT049/' + pasta_ifc + '/')]
if ifcs:
    L.append(f'- **IFCs as built** (`CT 049-2024 › 2 - AS BUILT CT 049.24 › {pasta_ifc}`, {len(ifcs)} arquivos, {sum(int(x.get("size") or 0) for x in ifcs)/1e9:.2f} GB): não baixados, os RVTs acima cobrem a mesma informação.')
L.append('')
L.append('## Próximo passo')
L.append('')
L.append('Referenciar os CADs: georreferenciar os DWGs de `PROJETO_ORIGINAL\\IMP\\` (SIT como base) e gravar os `*_GEO.dwg` + JSON em `CAD_GEORREFERENCIADO\\`. '
         'Não editar nada dentro de `PROJETO_ORIGINAL\\` (é a cópia fiel do Drive).')
open(os.path.join(BASE, d, 'INVENTARIO.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('ok', os.path.join(BASE, d, 'INVENTARIO.md'), len(L), 'linhas')
