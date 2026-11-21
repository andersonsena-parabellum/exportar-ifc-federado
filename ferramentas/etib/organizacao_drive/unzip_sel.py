"""Extrai de zips baixados do Drive só os arquivos do manifesto da escola (nome + tamanho exatos).

uso: python -I unzip_sel.py <ESCOLA> <zip1> [zip2 ...]
"""
import json, os, sys, zipfile, shutil
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__))
school, zips = sys.argv[1], sys.argv[2:]
BASE = r'D:\Projeto Modelagem'
man = [m for m in json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8')) if m['school'] == school]

def fix(n):   # zips antigos sem a flag UTF-8 vêm como cp437
    try:
        return n.encode('cp437').decode('utf-8')
    except Exception:
        return n

members = {}
for zp in zips:
    z = zipfile.ZipFile(zp)
    for info in z.infolist():
        if info.is_dir():
            continue
        name = info.filename if info.flag_bits & 0x800 else fix(info.filename)
        members.setdefault((os.path.basename(name), info.file_size), (zp, info))

done = skip = 0; missing = []
for m in man:
    dest = os.path.join(BASE, m['dir'], m['dest'], m['name'])
    if os.path.exists(dest) and os.path.getsize(dest) == m['size']:
        skip += 1; continue
    hit = members.get((m['name'], m['size']))
    if not hit:
        missing.append(m); continue
    zp, info = hit
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with zipfile.ZipFile(zp) as z, z.open(info) as src, open(dest, 'wb') as out:
        shutil.copyfileobj(src, out)
    done += 1
print(f'{school}: extraidos {done}, ja estavam {skip}, nao achados no zip {len(missing)}')
for m in missing:
    print('   FALTA', m['dest'], m['name'])
