"""IDs para download direto (só o que não é PDF e não vem no zip da pasta de projeto)."""
import json, os, sys
school = sys.argv[1]
DL = os.path.expanduser(r'~\Downloads')
out = []
for m in json.load(open('manifest.json', encoding='utf-8')):
    if m['school'] != school: continue
    if m['dest'].startswith('PROJETO_ORIGINAL\IMP') or m['dest'].startswith('PROJETO_ORIGINAL\BA2'): continue
    if m['name'].lower().endswith('.pdf'): continue
    d = os.path.join(r'D:\Projeto Modelagem', m['dir'], m['dest'], m['name'])
    if os.path.exists(d) and os.path.getsize(d) == m['size']: continue
    out.append(m['id'])
print(json.dumps(out))
