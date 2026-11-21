# -*- coding: utf-8 -*-
"""Antes × depois das notas de profundidade (20/10/2026): acha no PDF entregue os trechos com notas "PROF." amontoadas e recorta
a mesma área no PDF corrigido, lado a lado. Grava EXECUTIVO_R03_IFC/conferencia/notas_<folha>_<k>.png.
Uso: python -X utf8 jan_notas_antes_depois.py [n_recortes]"""
import os, sys, collections
import numpy as np
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
sys.stdout.reconfigure(encoding='utf-8')
R3 = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'
ANT = os.path.join(R3, '_copias', 'entregue_notas-repetidas'); NOV = os.path.join(R3, 'PDF_QG'); OUT = os.path.join(R3, 'conferencia')
nrec = int(sys.argv[1]) if len(sys.argv) > 1 else 2
Z = 2.5


def notas(pg):
    W = pg.get_text('words'); out = []
    for w in W:
        if w[4] == 'PROF.':
            c = fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2) * pg.rotation_matrix; out.append((c.x, c.y))
    return np.array(out)


def render(fn):
    pg = fitz.open(fn)[0]; pix = pg.get_pixmap(matrix=fitz.Matrix(Z, Z))
    return pg, Image.frombytes('RGB', (pix.width, pix.height), pix.samples)


try: fonte = ImageFont.truetype('arial.ttf', 34)
except Exception: fonte = ImageFont.load_default()
for fn in sorted(os.listdir(ANT)):
    if not fn.endswith('.pdf'): continue
    pa, ia = render(os.path.join(ANT, fn)); pn, inn = render(os.path.join(NOV, fn))
    P = notas(pa); Q = notas(pn); print(fn[19:-4], 'notas PROF.:', len(P), '->', len(Q))
    g = list(range(len(P)))
    def f(i):
        while g[i] != i: g[i] = g[g[i]]; i = g[i]
        return i
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            if np.hypot(*(P[i] - P[j])) < 60: g[f(i)] = f(j)
    cc = collections.defaultdict(list)
    for i in range(len(P)): cc[f(i)].append(i)
    for k, x in enumerate(sorted(cc.values(), key=len, reverse=True)[:nrec]):
        lo, hi = P[x].min(0) - 80, P[x].max(0) + 80
        box = tuple(int(v * Z) for v in (lo[0], lo[1], hi[0], hi[1]))
        a, b = ia.crop(box), inn.crop(box)
        W, H = a.width * 2 + 30, a.height + 60
        im = Image.new('RGB', (W, H), 'white'); im.paste(a, (0, 60)); im.paste(b, (a.width + 30, 60))
        d = ImageDraw.Draw(im); d.text((10, 10), f'ANTES ({len(x)} notas)', fill=(200, 0, 0), font=fonte)
        d.text((a.width + 40, 10), 'DEPOIS', fill=(0, 130, 0), font=fonte); d.line([(a.width + 15, 0), (a.width + 15, H)], fill=(150, 150, 150), width=3)
        nome = os.path.join(OUT, f"notas_{fn[20:-12].replace('-PE-', '_')}_{k}.png"); im.save(nome); print('  ', nome)
