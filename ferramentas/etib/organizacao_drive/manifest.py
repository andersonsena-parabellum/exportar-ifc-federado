"""Monta o manifesto de download por escola a partir das listagens do Drive e das seleções (sel/*.json)."""
import json, re, sys, os
sys.stdout.reconfigure(encoding='utf-8')
D = 'listagens_2026-10-18'
SCHOOLS = {  # chave da listagem -> pasta local
    'APORA-ITAMIRA': 'ETIB-APORA-ITAMIRA',
    'APORA-PROF-AUREA': 'ETIB-APORA-PROF-AUREA',
    'CATU': 'ETIB-CATU',
    'POJUCA': 'ETIB-POJUCA',
    'SATIRO-DIAS': 'ETIB-SATIRO-DIAS',
    'JANDAIRA': 'ETIB-JANDAIRA',
    'ALAGOINHAS': 'ETIB-ALAGOINHAS',
}
ASBUILT = {
    'CATU': 'PASTA2-QG/004-25-09-2026-05-12-QG as built Catu/',
    'POJUCA': 'PASTA2-QG/004-25-10-2026-05-12-QG as built Pojuca/',
    'SATIRO-DIAS': 'PASTA2-QG/004-25-01-2026-04-30-QG as built Sátiro Dias/',
    'APORA-PROF-AUREA': 'PASTA2-QG/004-25-02-2026-03-31-QG as built Aporá sede/',
    'APORA-ITAMIRA': 'PASTA2-QG/004-25-03-2026-03-31-QG as built Aporá Itamira/',
}
BLK = {'SUBESTAÇÃO': 'SB3', 'VESTIÁRIO': 'VST', 'IMPLANTAÇÃO': 'IMP', 'Implantação': 'IMP', 'RTS': 'RST'}
REV = re.compile(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)')

def load(k):
    return json.load(open(os.path.join(D, f'drive_listing_{k}.json'), encoding='utf-8'))

asb = load('PASTA2-QG')
man = []
def add(school, dest, name, fid, size, origem):
    man.append(dict(school=school, dir=SCHOOLS[school], dest=dest, name=name, id=fid,
                    size=int(size or 0), origem=origem))

for k in SCHOOLS:
    lst = load(k)
    # 1) projeto original: implantação (e BA2 em Alagoinhas)
    for sub in (['BA2'] if k == 'ALAGOINHAS' else ['IMP']):
        s = json.load(open(f'sel/{k}_{sub}.json', encoding='utf-8'))
        for i in s['selected']:
            add(k, f'PROJETO_ORIGINAL\\{sub}\\{i["cat"]}', i['name'], i['id'], i['size'], i['drive'])
    # 2) memoriais de incêndio da implantação guardados na pasta AVCB
    have = {m['name'] for m in man if m['school'] == k}
    for x in lst:
        p = x.get('path', ''); n = p.split('/')[-1]
        if x.get('d') or '/AVCB/' not in p or re.search('OBSOLET', p, re.I):
            continue
        if re.search(r'-IMP-MD-IN-', n) and n not in have:
            add(k, 'PROJETO_ORIGINAL\\IMP\\05_PCI', n, x['id'], x['size'], p); have.add(n)
    # 3) lista mestra mais recente
    lm = [x for x in lst if not x.get('d') and '/1 - LISTA MESTRA/' in x.get('path', '')
          and x['path'].lower().endswith('.xlsx')]
    if lm:
        best = max(lm, key=lambda x: int((REV.findall(x['path'].split('/')[-1]) or ['-1'])[-1]))
        add(k, 'PROJETO_ORIGINAL\\LISTA_MESTRA', best['path'].split('/')[-1], best['id'], best['size'], best['path'])
    # 4) RVTs as built: IMP + fundação/estrutura (sem arquitetura, sem IFC, sem metálica grande)
    if k in ASBUILT:
        root = ASBUILT[k]; seen = set()
        for x in asb:
            p = x.get('path', '')
            if x.get('d') or not p.startswith(root) or not p.lower().endswith('.rvt'):
                continue
            rel = p[len(root):]; n = rel.split('/')[-1]; top = rel.split('/')[0]
            if top == 'VST' and '/GUA/' in rel:      # cópia repetida da guarita
                continue
            is_imp = BLK.get(top, top) == 'IMP'
            ok = is_imp or re.search(r'-PE-(FUN|ECC)-', n) or (re.search(r'-PE-EMT-', n) and top == 'QDC')
            if not ok or n in seen:
                continue
            seen.add(n)
            add(k, f'REFERENCIAS_RVT\\{BLK.get(top, top)}', n, x['id'], x['size'], p)
    if k == 'ALAGOINHAS':   # arquitetura do BA2 (base para modelar as instalações do bloco)
        for x in asb:
            if x.get('path', '').endswith('BA2-PE-ARQ-001-MOD-R00.rvt'):
                add(k, 'REFERENCIAS_RVT\\BA2', x['path'].split('/')[-1], x['id'], x['size'], x['path'])

json.dump(man, open('manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import defaultdict
agg = defaultdict(lambda: [0, 0])
for m in man:
    a = agg[(m['school'], m['dest'].split('\\')[0])]; a[0] += 1; a[1] += m['size']
for (s, d), (n, b) in sorted(agg.items()):
    print(f'{s:18s} {d:18s} {n:4d} arq  {b/1e6:8.1f} MB')
print('TOTAL', len(man), f'{sum(m["size"] for m in man)/1e9:.2f} GB')
for m in man:
    if m['dest'].startswith('REFERENCIAS'):
        print('   ', m['school'], m['dest'], m['name'], f"{m['size']/1e6:.1f}")
