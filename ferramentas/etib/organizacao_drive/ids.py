import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
school = sys.argv[1]
DL = os.path.expanduser(r'~\Downloads')
man = [m for m in json.load(open('manifest.json', encoding='utf-8')) if m['school'] == school]
ids = []
for m in man:
    p = os.path.join(DL, m['name']); d = os.path.join(r'D:\Projeto Modelagem', m['dir'], m['dest'], m['name'])
    if (os.path.exists(p) and os.path.getsize(p) == m['size']) or (os.path.exists(d) and os.path.getsize(d) == m['size']):
        continue
    ids.append(m['id'])
print(json.dumps(ids))
