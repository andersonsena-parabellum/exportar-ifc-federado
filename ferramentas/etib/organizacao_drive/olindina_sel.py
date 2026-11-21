"""Olindina (no contrato desde 21/10/2026): acrescenta ao manifest.json a implantação, a lista mestra e os RVTs as built.
Lote "olindina-2026-10-21". Escopo igual às outras: implantação HIDRO + ELE + PCI; o BA5 é edificação e fica de fora.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
D = 'listagens_2026-10-21'
LOTE = 'olindina-2026-10-21'
REV = re.compile(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)')
man = [m for m in json.load(open('manifest.json', encoding='utf-8')) if m.get('lote') != LOTE]
novos = []
def add(dest, name, fid, size, origem):
    novos.append(dict(school='OLINDINA', dir='ETIB-OLINDINA', dest=dest, name=name, id=fid,
                      size=int(size or 0), origem=origem, lote=LOTE))
for i in json.load(open('sel/OLINDINA_IMP.json', encoding='utf-8'))['selected']:
    add(f'PROJETO_ORIGINAL\\IMP\\{i["cat"]}', i['name'], i['id'], i['size'], i['drive'])
L = json.load(open(f'{D}/drive_listing_OLINDINA.json', encoding='utf-8'))
lm = [x for x in L if not x.get('d') and '/1 - LISTA MESTRA/' in x['path'] and x['path'].lower().endswith('.xlsx')]
best = max(lm, key=lambda x: int((REV.findall(x['path'].split('/')[-1]) or ['-1'])[-1]))
add('PROJETO_ORIGINAL\\LISTA_MESTRA', best['path'].split('/')[-1], best['id'], best['size'], best['path'])
BLK = {'Implantação': 'IMP'}
for x in json.load(open(f'{D}/drive_listing_ASBUILT-OLINDINA.json', encoding='utf-8')):
    p = x.get('path', ''); n = p.split('/')[-1]
    if x.get('d') or not n.lower().endswith('.rvt'):
        continue
    top = p.split('/')[1]
    if BLK.get(top) == 'IMP' or re.search(r'-PE-(FUN|ECC)-', n):
        add(f'REFERENCIAS_RVT\\{BLK.get(top, top)}', n, x['id'], x['size'], 'CT049_2024/004-25-01-2026-03-31-QG as built Olindina/' + p.split('/', 1)[1])
json.dump(man + novos, open('manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for m in novos:
    print(f"{m['dest']:34s} {m['size']/1e6:7.2f}  {m['name']}")
print(len(novos), 'arquivos', f"{sum(m['size'] for m in novos)/1e6:.1f} MB")
print(json.dumps([m['id'] for m in novos if not m['name'].lower().endswith('.pdf')]))
