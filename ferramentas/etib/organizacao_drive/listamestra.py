"""Lê a lista mestra (.xlsx) só com a biblioteca padrão e lista os documentos da implantação (IMP).

uso: python -I listamestra.py <arquivo.xlsx> [filtro_regex]
"""
import re, sys, zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
fn = sys.argv[1]
flt = re.compile(sys.argv[2] if len(sys.argv) > 2 else r'-IMP-', re.I)
z = zipfile.ZipFile(fn)
ss = []
if 'xl/sharedStrings.xml' in z.namelist():
    for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
        ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
wb = ET.fromstring(z.read('xl/workbook.xml'))
names = [s.get('name') for s in wb.find('m:sheets', NS)]
sheets = sorted(n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
for idx, sh in enumerate(sorted(sheets, key=lambda s: int(re.findall(r'\d+', s)[-1]))):
    root = ET.fromstring(z.read(sh))
    out = []
    for row in root.iter('{%s}row' % NS['m']):
        vals = []
        for c in row.findall('m:c', NS):
            v = c.find('m:v', NS); t = c.get('t')
            if t == 's' and v is not None:
                vals.append(ss[int(v.text)])
            elif t == 'inlineStr':
                vals.append(''.join(x.text or '' for x in c.iter('{%s}t' % NS['m'])))
            elif v is not None:
                vals.append(v.text)
        line = ' | '.join(x.strip() for x in vals if x and x.strip())
        if flt.search(line):
            out.append(line)
    if out:
        print(f'### aba {names[idx] if idx < len(names) else sh}')
        for l in out:
            print('  ', l[:220])
