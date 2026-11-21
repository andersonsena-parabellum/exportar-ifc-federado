# -*- coding: utf-8 -*-
"""Mapa de diagnóstico: redes por disciplina + pontos de clash (vermelho = colisão, laranja = folga, azul = info).
Uso: mapa_pontos.py saida.png [filtro_par] [bbox xmin,ymin,xmax,ymax] [px_por_m]"""
import sys, csv, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
G = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo"
out = sys.argv[1]; filt = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '-' else None
bbox = [float(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] != '-' else [-35, -120, 112, 56]
S = float(sys.argv[4]) if len(sys.argv) > 4 else 12
W = int((bbox[2] - bbox[0]) * S); H = int((bbox[3] - bbox[1]) * S)
img = Image.new('RGB', (W, H), 'white'); dr = ImageDraw.Draw(img)
try: fnt = ImageFont.truetype("segoeui.ttf", max(10, int(S * 0.9)))
except Exception: fnt = None
T = lambda x, y: ((x - bbox[0]) * S, (bbox[3] - y) * S)
COL = {'AF': (47, 140, 255), 'ESG': (181, 101, 29), 'INC': (229, 57, 53), 'SDAI': (255, 143, 0), 'DRN': (46, 158, 91), 'ELE': (230, 190, 0), 'TEL': (156, 91, 214), 'CNT': (120, 100, 80)}
for b in json.load(open(r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\blocos.json", encoding='cp1252')):
    v = [T(x, y) for x, y in b['coords']]; dr.polygon(v, fill=(236, 238, 242), outline=(150, 150, 160))
    c = np.mean(b['coords'], axis=0); dr.text(T(*c), b['bloco'], fill=(110, 110, 120), font=fnt)
def disc_seg(f, r):
    if f == 'HS': return 'AF' if r[4].startswith('Água') else 'ESG'
    if f == 'INC': return 'SDAI' if (r[2] == 'Conduites' or 'SDAI' in r[3]) else 'INC'
    if f == 'ELE': return 'TEL' if r[3].startswith('TEL') else 'ELE'
    return f
for f in ('DRN', 'HS', 'ELE', 'INC'):
    for l in open(os.path.join(G, f + '_segs.tsv'), encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 13: continue
        d = disc_seg(f, r); a = tuple(map(float, r[7:9])); b = tuple(map(float, r[10:12]))
        dr.line([T(*a), T(*b)], fill=COL[d], width=max(1, int(S / 8)))
for l in open(os.path.join(G, 'CNT_mesh.tsv'), encoding='utf-8'):
    r = l.split('\t')
    if r[2] != 'Paredes': continue
    v = np.array(r[7].split(','), dtype=float).reshape(-1, 3)
    dr.line([T(v[:, 0].min(), v[v[:, 0].argmin(), 1]), T(v[:, 0].max(), v[v[:, 0].argmax(), 1])], fill=COL['CNT'], width=max(2, int(S / 3)))
rows = list(csv.DictReader(open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\pontos_clash.csv", encoding='utf-8-sig'), delimiter=';'))
CG = {'CRÍTICA': (200, 30, 30), 'ATENÇÃO': (240, 140, 0), 'INFORMAÇÃO': (60, 110, 190)}
for r in sorted(rows, key=lambda r: {'INFORMAÇÃO': 0, 'ATENÇÃO': 1, 'CRÍTICA': 2}[r['gravidade']]):
    if filt and filt not in r['par']: continue
    X, Y = T(float(r['x']), float(r['y'])); k = max(2, S / 4)
    dr.ellipse([X - k, Y - k, X + k, Y + k], fill=CG[r['gravidade']])
    if S >= 20: dr.text((X + k + 1, Y - k), r['par'], fill=CG[r['gravidade']], font=fnt)
# grade de 10 m com coordenadas
for x in range(int(bbox[0] // 10) * 10, int(bbox[2]) + 1, 10):
    dr.line([T(x, bbox[1]), T(x, bbox[3])], fill=(225, 225, 225)); dr.text(T(x + 0.3, bbox[3] - 0.5), str(x), fill=(150, 150, 150), font=fnt)
for y in range(int(bbox[1] // 10) * 10, int(bbox[3]) + 1, 10):
    dr.line([T(bbox[0], y), T(bbox[2], y)], fill=(225, 225, 225)); dr.text(T(bbox[0] + 0.3, y + 1.2), str(y), fill=(150, 150, 150), font=fnt)
img.save(out); print('ok', out, W, H)
