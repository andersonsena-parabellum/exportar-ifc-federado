"""Move os downloads de uma escola de ~/Downloads para a pasta da escola, conferindo o tamanho.

uso: python -I mover.py <ESCOLA> [espera_max_s]
Procura cada arquivo do manifesto pelo nome (ou "nome (n)") com o tamanho exato do Drive.
"""
import json, os, re, shutil, sys, time
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__))
school = sys.argv[1]
wait = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
DL = os.path.expanduser(r'~\Downloads')
BASE = r'D:\Projeto Modelagem'
man = [m for m in json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8')) if m['school'] == school]
if '--direto' in sys.argv:   # só o que vem por link direto (RVT, lista mestra)
    man = [m for m in man if not re.match(r'PROJETO_ORIGINAL\\(IMP|BA2)', m['dest']) and not m['name'].lower().endswith('.pdf')]

if '--naopdf' in sys.argv:   # tudo menos PDF (os PDFs vêm em zip)
    man = [m for m in man if not m['name'].lower().endswith('.pdf')]

def candidates(name):
    stem, ext = os.path.splitext(name)
    rx = re.compile(re.escape(stem) + r'( \(\d+\))?' + re.escape(ext) + '$', re.I)
    return [f for f in os.listdir(DL) if rx.match(f)]

t0 = time.time()
pending = list(man)
moved, already = [], []
while True:
    rest = []
    for m in pending:
        dest_dir = os.path.join(BASE, m['dir'], m['dest'])
        dest = os.path.join(dest_dir, m['name'])
        if os.path.exists(dest) and os.path.getsize(dest) == m['size']:
            already.append(m); continue
        hit = None
        for f in candidates(m['name']):
            p = os.path.join(DL, f)
            if os.path.getsize(p) == m['size']:
                hit = p; break
        if hit:
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.move(hit, dest)
            except PermissionError:      # arquivo ainda preso (antivírus/Chrome): tenta na próxima volta
                if os.path.exists(dest) and os.path.getsize(dest) != m['size']:
                    os.remove(dest)
                rest.append(m); continue
            moved.append(m)
        else:
            rest.append(m)
    pending = rest
    if not pending or time.time() - t0 > wait:
        break
    time.sleep(10)

print(f'{school}: movidos {len(moved)}, ja estavam {len(already)}, faltando {len(pending)}')
for m in pending:
    print('   FALTA', m['dest'], m['name'], m['size'])
