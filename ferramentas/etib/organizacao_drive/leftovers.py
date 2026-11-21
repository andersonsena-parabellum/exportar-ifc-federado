"""Lista (e com --apagar remove) cópias em ~/Downloads que já existem idênticas (hash) na pasta da escola."""
import json, os, sys, hashlib
sys.stdout.reconfigure(encoding='utf-8')
DL = os.path.expanduser(r'~\Downloads')
man = json.load(open('manifest.json', encoding='utf-8'))
def h(p):
    m = hashlib.sha1()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): m.update(b)
    return m.hexdigest()
for m in man:
    src = os.path.join(DL, m['name']); dst = os.path.join(r'D:\Projeto Modelagem', m['dir'], m['dest'], m['name'])
    if os.path.exists(src) and os.path.exists(dst) and h(src) == h(dst):
        if '--apagar' in sys.argv:
            try: os.remove(src); print('removido', m['name'])
            except Exception as e: print('PRESO', m['name'], e)
        else: print('duplicado', m['name'])
