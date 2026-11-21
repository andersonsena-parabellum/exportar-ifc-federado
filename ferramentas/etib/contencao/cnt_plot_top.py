# -*- coding: utf-8 -*-
"""Contexto topográfico (TOP-001) + muro de contenção (face) + blocos, em UTM. PIL."""
import sys, json, re, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
out = sys.argv[1]; bbox = [float(v) for v in sys.argv[2].split(',')]; WPX = int(sys.argv[3])
P3 = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)(?:,(-?\d+\.?\d*))?')
H = int(WPX * (bbox[3] - bbox[1]) / (bbox[2] - bbox[0])); s = WPX / (bbox[2] - bbox[0])
img = Image.new('RGB', (WPX, H), 'white'); dr = ImageDraw.Draw(img)
try: fnt = ImageFont.truetype("segoeui.ttf", 13)
except Exception: fnt = None
T = lambda x, y: ((x - bbox[0]) * s, (bbox[3] - y) * s)
cor = {'CURVAS': (150, 200, 150), 'TOP-MURO': (200, 40, 40), 'TOP-TALUDE': (230, 140, 0), 'TOP-MEIOFIO': (90, 90, 90),
       'TOP-PASSEIO': (130, 130, 200), 'TOP-ED': (60, 60, 60), 'TOP-ESCADA': (160, 100, 160), 'TOP-CAIXA': (0, 150, 150), 'TG': (200, 200, 200)}
cotas = []
for ln in open(W + r"\dumpz_TOP.tsv", encoding='cp1252', errors='replace'):
    p = ln.rstrip('\n').split('\t')
    if len(p) < 3: continue
    if p[0] == 'INSERT' and p[1] == 'TOP-COTAS':
        m = P3.match(p[2]); cotas.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
        continue
    if p[1] not in cor: continue
    body = p[2].split(' ', 1)[1] if p[2].startswith('elev=') else p[2]
    v = [(float(a), float(b)) for a, b, _ in P3.findall(body)]
    if len(v) >= 2: dr.line([T(*q) for q in v], fill=cor[p[1]], width=2 if p[1] in ('TOP-MURO', 'TOP-TALUDE') else 1)
for x, y, z in cotas:
    if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
        X, Y = T(x, y); dr.ellipse([X - 2, Y - 2, X + 2, Y + 2], fill=(0, 0, 0)); dr.text((X + 3, Y - 7), f'{z:.2f}', fill=(0, 0, 0), font=fnt)
F = json.load(open(W + r"\cnt_face.json", encoding='utf-8')); O = F['origem_interna_utm']
for sg in F['segmentos']:
    a = (sg['p0'][0] + O[0], sg['p0'][1] + O[1]); b = (sg['p1'][0] + O[0], sg['p1'][1] + O[1])
    dr.line([T(*a), T(*b)], fill=(0, 90, 220), width=4)
    n = sg['n_sul']; m = ((a[0] + b[0]) / 2 + n[0] * 3, (a[1] + b[1]) / 2 + n[1] * 3)
    dr.text(T(*m), f"seção {sg['secao']} H={sg['H']:.2f}", fill=(0, 90, 220), font=fnt)
for b in json.load(open(r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\blocos.json", encoding='cp1252')):
    v = [T(x + O[0], y + O[1]) for x, y in b['coords']]; dr.line(v + v[:1], fill=(0, 0, 0), width=2)
dr.text((8, 8), 'TOP-001: curvas verde, muro existente vermelho, talude laranja, meio-fio cinza, passeio lilás; cotas pontuais; CONTENÇÃO nova = azul (face); blocos = preto', fill='black', font=fnt)
img.save(out); print('ok', out)
