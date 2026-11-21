"""Seleciona, numa listagem do Drive, os arquivos do escopo da proposta (por escola).

uso: python -I sel.py <listing.json> <raiz_no_drive/> <SUB> <saida.json>
SUB = IMP (implantação) ou BA2 etc. (bloco). Mantém só a última revisão de cada documento.
"""
import json, re, sys, os, collections
sys.stdout.reconfigure(encoding='utf-8')

fn, root, sub, out = sys.argv[1:5]
items = json.load(open(fn, encoding='utf-8'))

CATS = [
    ('00_BASE', r'^\d+ - IMPLANTA|TOPOGR|TERRAPLAN|PAVIMENTA'),
    ('01_AF', r'[ÁA]GUA(?!S PLUV)'),
    ('02_ESG', r'ESGOTO'),
    ('03_DRE', r'DRENAGEM'),
    ('04_ELE', r'EL[ÉE]TRICA'),
    ('05_PCI', r'INC[ÊE]NDIO'),
    ('06_CLI', r'CLIMATIZA'),
]
if sub != 'IMP':                       # bloco: base = arquitetura não entra aqui
    CATS = [c for c in CATS if c[0] != '00_BASE']
EXCL_PATH = re.compile(r'OBSOLET|ESTA[ÇC][ÃA]O DE TRATAMENTO|^ETE\b|/ETE\b|MEMORIAL ETE', re.I)
EXCL_NAME = re.compile(r'\.(png|jpe?g|ctb|stb|log|dwl2?|bak|tmp)$|-ETE[-_]|^~\$', re.I)
REV = re.compile(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)', re.I)

def cat_of(folder):
    for c, rx in CATS:
        if re.search(rx, folder, re.I):
            return c
    return None

sel, skipped_old, out_scope, excluded = {}, [], collections.Counter(), []
for x in items:
    p = x.get('path', '')
    if x.get('d') or x.get('err') or x.get('warn') or not p.startswith(root):
        continue
    rel = p[len(root):]
    folder = rel.split('/')[0]
    name = rel.split('/')[-1]
    c = cat_of(folder)
    if c is None:
        out_scope[folder] += 1
        continue
    if EXCL_PATH.search(rel) or EXCL_NAME.search(name):
        excluded.append(rel)
        continue
    m = list(REV.finditer(name))
    rev = int(m[-1].group(1)) if m else -1
    base, ext = os.path.splitext(name)
    key = (c, (REV.sub('', base) if m else base).upper(), ext.lower())
    it = dict(cat=c, sub=sub, name=name, id=x['id'], size=int(x.get('size') or 0),
              mod=x.get('mod'), rev=rev, drive=rel)
    cur = sel.get(key)
    if cur is None or (rev, it['mod'] or 0) > (cur['rev'], cur['mod'] or 0):
        if cur is not None and cur['rev'] != rev:
            skipped_old.append(cur['drive'])
        sel[key] = it
    elif cur['rev'] != rev:
        skipped_old.append(rel)

res = dict(selected=sorted(sel.values(), key=lambda i: (i['cat'], i['name'])),
           older_revisions=sorted(skipped_old), excluded=sorted(excluded),
           out_of_scope=dict(out_scope))
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot = sum(i['size'] for i in res['selected'])
print(f"{root}  ->  {len(res['selected'])} arquivos, {tot/1e6:.1f} MB")
for i in res['selected']:
    print(f"  {i['cat']:8s} {i['size']/1e6:7.2f}  {i['name']}")
print('  revisoes antigas puladas:', len(skipped_old), '| excluidos (obsoleto/ETE/imagem):', len(excluded))
print('  fora do escopo:', ', '.join(f'{k}({v})' for k, v in sorted(out_scope.items())))
