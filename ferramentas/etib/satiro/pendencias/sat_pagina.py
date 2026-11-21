# -*- coding: utf-8 -*-
"""Sátiro Dias — página de pendências (mesmo modelo da "Pendências Alagoinhas R03"): uma ficha por pendência, recorte da prancha de
cada disciplina com o ponto no círculo vermelho, vistas 3D e planta do modelo em botões, encaminhamento e texto salvos na página
(capability db, coleção 'decisoes', docs d01..), filtros no topo. Lê fichas.json e img/prancha.json; grava <saida>/index.html e
copia img/. Uso: python -X utf8 sat_pagina.py <pasta de saída>"""
import os, sys, json, shutil, html, io, base64
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, 'img'), exist_ok=True)
F = json.load(open(os.path.join(AQUI, 'fichas.json'), encoding='utf-8'))
PR = json.load(open(os.path.join(AQUI, 'img', 'prancha.json'), encoding='utf-8'))
for x in os.listdir(os.path.join(AQUI, 'img')):
    if x.endswith('.jpg'): shutil.copy2(os.path.join(AQUI, 'img', x), os.path.join(OUT, 'img', x))
# imagens embutidas no HTML (o celular não carregava o arquivo separado): JPG 960 px, qualidade 72
IMG = {}
for x in sorted(os.listdir(os.path.join(AQUI, 'img'))):
    if not x.endswith('.jpg'): continue
    im = Image.open(os.path.join(AQUI, 'img', x)).convert('RGB'); im.thumbnail((960, 960))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=72, optimize=True); IMG[x] = base64.b64encode(b.getvalue()).decode()
nd = sum(f['grupo'] == 'D' for f in F); ng = sum(f['grupo'] == 'G' for f in F)
modelo = open(os.path.join(AQUI, 'pagina_modelo.html'), encoding='utf-8').read()
pag = (modelo.replace('__DADOS__', json.dumps(F, ensure_ascii=False).replace('</', '<\/'))
       .replace('__PRANCHAS__', json.dumps(PR, ensure_ascii=False)).replace('__NT__', str(len(F)))
       .replace('__ND__', str(nd)).replace('__NG__', str(ng)).replace('__IMAGENS__', json.dumps(IMG)))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(pag)
print('página', os.path.join(OUT, 'index.html'), len(F), 'fichas')
