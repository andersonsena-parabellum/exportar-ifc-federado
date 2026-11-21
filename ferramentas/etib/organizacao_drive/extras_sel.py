"""Projetos fora da "4 - IMPLANTAÇÃO" que entram no escopo (rede externa): campo society e a implantação
própria da quadra de Pojuca. Acrescenta ao manifest.json (campo "lote": "extras-2026-10-18").

Critério (18/10/2026): entram só redes externas — campo society (área aberta: drenagem, iluminação, PCI) e
documentos de IMPLANTAÇÃO guardados dentro da pasta de um bloco. Projetos de edificação (guarita, vestiário,
quadra coberta, subestação, casa de gás, reservatórios, blocos de salas, teatro, refeitório) ficam de fora,
exceto o BA2 de Alagoinhas, que a proposta cita nominalmente. As duas escolas de Aporá não entram aqui
(as threads delas estão decidindo com o usuário).
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
D = 'listagens_2026-10-18'
DIRS = {'POJUCA': 'ETIB-POJUCA', 'SATIRO-DIAS': 'ETIB-SATIRO-DIAS', 'JANDAIRA': 'ETIB-JANDAIRA'}
CPS = [(r'INC[ÊE]NDIO', '05_PCI'), (r'DRENAGEM', '03_DRE'), (r'EL[ÉE]TRICA', '04_ELE')]
JOBS = [
    ('POJUCA', 'POJUCA/18 - CAMPO (30X50)/', 'CPS', CPS),
    ('SATIRO-DIAS', 'SATIRO-DIAS/18 - CAMPO SOCIETY/', 'CPS', CPS),
    ('JANDAIRA', 'JANDAIRA/18 - CAMPO SOCIETY/', 'CPS', CPS),
    ('POJUCA', 'POJUCA/10 - QUADRA (30X18)/6 - IMPLANTAÇÃO/', 'IMP_QUADRA',
     [(r'URBANISMO', '00_BASE'), (r'[ÁA]GUA', '01_AF'), (r'EL[ÉE]TRICA', '04_ELE'), (r'PCI|INC[ÊE]NDIO', '05_PCI')]),
]
EXCL = re.compile(r'OBSOLET|\.(png|jpe?g|ctb|log|dwl2?|bak|tmp)$|/~|/SE POJUCA', re.I)
REV = re.compile(r'[-_ ]R(\d{1,2})(?=[^0-9]|$)', re.I)

man = [m for m in json.load(open('manifest.json', encoding='utf-8')) if m.get('lote') != 'extras-2026-10-18']
novos, antigos = [], []
for k, root, sub, cats in JOBS:
    L = json.load(open(f'{D}/drive_listing_{k}.json', encoding='utf-8'))
    best = {}
    for x in L:
        p = x.get('path', '')
        if x.get('d') or x.get('err') or not p.startswith(root) or EXCL.search(p):
            continue
        rel = p[len(root):]; top = rel.split('/')[0]; n = rel.split('/')[-1]
        cat = next((c for rx, c in cats if re.search(rx, top, re.I)), None)
        if not cat:
            continue
        m = list(REV.finditer(n)); rev = int(m[-1].group(1)) if m else -1
        stem, ext = os.path.splitext(n)
        # a mesma prancha às vezes aparece com o código do bloco trocado (CP1-CPS / ETIB-CPS): a chave ignora isso
        key = (cat, re.sub(r'-(CP1|CP2A|ETIB)-', '-', REV.sub('', stem) if m else stem).upper(), ext.lower())
        it = dict(school=k, dir=DIRS[k], dest=f'PROJETO_ORIGINAL\\{sub}\\{cat}', name=n, id=x['id'],
                  size=int(x.get('size') or 0), origem=p[len(k) + 1:], lote='extras-2026-10-18', rev=rev)
        cur = best.get(key)
        if cur is None or rev > cur['rev']:
            if cur: antigos.append(cur['origem'])
            best[key] = it
        else:
            antigos.append(it['origem'])
    novos += best.values()
for it in novos:
    it.pop('rev', None)
json.dump(man + novos, open('manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(antigos, open('sel/extras_revisoes_antigas.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot = 0
for it in sorted(novos, key=lambda i: (i['school'], i['dest'], i['name'])):
    tot += it['size']; print(f"{it['school']:12s} {it['dest']:36s} {it['size']/1e6:6.2f}  {it['name']}")
print(len(novos), 'arquivos', f'{tot/1e6:.1f} MB; revisões antigas puladas:', len(antigos))
