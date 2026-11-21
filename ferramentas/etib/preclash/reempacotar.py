# -*- coding: utf-8 -*-
"""Remonta o visualizador com o template atual (preclash/visualizador.html) reaproveitando os dados de um HTML já gerado,
sem rodar o clash de novo. Útil quando só a interface mudou.
Uso: ..\\.venv\\Scripts\\python.exe -X utf8 reempacotar.py <SIGLA>_preclash_visualizador.html [pasta_do_artifact]"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rodar import versao_artefato, pagina_portal, AQUI

fn = sys.argv[1]
html = open(fn, encoding='utf-8').read()
m = re.search(r'<script id="dados" type="application/json">(.*?)</script>', html, re.S)
titulo = re.search(r'<title>(.*?)</title>', html).group(1)
tpl = open(os.path.join(AQUI, 'preclash', 'visualizador.html'), encoding='utf-8').read()
novo = tpl.replace('__TITULO__', titulo).replace('__DADOS__', m.group(1))
open(fn, 'w', encoding='utf-8').write(novo)
print('remontado', fn)
if len(sys.argv) > 2:
    fa = os.path.join(sys.argv[2], 'preclash_portal.html')
    open(fa, 'w', encoding='utf-8').write(pagina_portal())
    print('página do visualizador único', fa)
