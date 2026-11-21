"""Página única: rede v2 (CSV de exportação) sobre a arquitetura do PDF do projeto, por quadrantes.
Uso: python -I plotv2arq.py saida.pdf"""
import sys, pymupdf, pickle, math, os, csv
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
Image.MAX_IMAGE_PIXELS = None
W_ = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
a2, c2, tx2, ty2 = eval(open(W_ + 'pdf_transform_geo.txt').read())
T2 = lambda x, y: (a2 * x - c2 * y + tx2, -(a2 * y + c2 * x + ty2))
pdf = "D:/Projeto Modelagem/ETIB-ALAGOINHAS/4 - IMPLANTAÇÃO-20261008T151806Z-1-001/4 - IMPLANTAÇÃO/8 - DRENAGEM/24-049-ALH-SLJ-ETIB-IMP-PE-DRE-001-DRG-R04.pdf"
doc = pymupdf.open(pdf); oc = doc.get_ocgs()
keep = {'0', '0-PAREDE', '0-VISTA', 'A-DETL', 'ARQ-BASE', 'ARQ_BASE', 'ARQ-TEXTO', 'ARQ_TXT', 'Piso', 'AC - Máquina'}
doc.set_layer(-1, on=[x for x, v in oc.items() if v['name'] in keep], off=[x for x, v in oc.items() if v['name'] not in keep])
pg = doc[0]
x0, x1, y0, y1 = -30, 105, -112, 65
cs = [T2(x0, y1), T2(x1, y1), T2(x0, y0), T2(x1, y0)]
clip = pymupdf.Rect(min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
W = 4800; z = W / clip.width
pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
bg = ImageOps.grayscale(Image.frombytes('RGB', (pix.width, pix.height), pix.samples)).point(lambda v: 255 if v > 245 else int(v * 0.55 + 20)).convert('RGB')
TT = lambda p: ((T2(*p)[0] - clip.x0) * z, (T2(*p)[1] - clip.y0) * z)
ppm = z * math.hypot(a2, c2)
D = pickle.load(open(W_ + 'v2_net.pkl', 'rb'))
nodes, boxes, outs = D['nodes'], D['boxes'], D['outs']
P = list(csv.reader(open(W_ + 'v2_pipes.csv', encoding='utf-8'), delimiter=';'))
B = list(csv.reader(open(W_ + 'v2_boxes.csv', encoding='utf-8'), delimiter=';'))
d = ImageDraw.Draw(bg)
for r in P:
    if r[17] not in ('H', 'E'): continue
    DN = int(r[2]); w = 4 if DN <= 50 else (7 if DN <= 150 else 11)
    col = (150, 0, 200) if r[4] == 'INT' else (0, 90, 255)
    if 'registrar' in r[18] and ('DECLIVIDADE' in r[18]): col = (230, 0, 0)
    d.line([TT((float(r[5]), float(r[6]))), TT((float(r[8]), float(r[9])))], fill=col, width=w)
for r in P:   # seta de sentido nos trechos horizontais longos
    if r[17] != 'H': continue
    a = (float(r[5]), float(r[6])); b = (float(r[8]), float(r[9])); Lh = math.dist(a, b)
    if Lh < 3: continue
    ux, uy = (b[0] - a[0]) / Lh, (b[1] - a[1]) / Lh; m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    d.polygon([TT((m[0] + ux * 0.8, m[1] + uy * 0.8)), TT((m[0] - uy * 0.35, m[1] + ux * 0.35)), TT((m[0] + uy * 0.35, m[1] - ux * 0.35))], fill=(0, 0, 0))
for r in P:
    if r[17] == 'VP':
        X, Y = TT((float(r[5]), float(r[6]))); d.ellipse([X - 13, Y - 13, X + 13, Y + 13], fill=(255, 200, 0), outline=(0, 0, 0), width=2)
    if r[17] == 'VM':
        X, Y = TT((float(r[5]), float(r[6]))); d.ellipse([X - 13, Y - 13, X + 13, Y + 13], fill=(0, 200, 0), outline=(0, 0, 0), width=2)
for r in B:
    X, Y = TT((float(r[2]), float(r[3]))); s = float(r[6]) / 2 * ppm; s = max(s, 10)
    col = (255, 0, 255) if r[7] == 'ISO' else (210, 0, 0)
    (d.ellipse if r[0] == 'PV' else d.rectangle)([X - s, Y - s, X + s, Y + s], outline=col, width=6)
FG = ImageFont.truetype('arialbd.ttf', 150); F = ImageFont.truetype('arialbd.ttf', 70); Fs = ImageFont.truetype('arialbd.ttf', 52)
xs = [-30, 15, 60, 105]; ys = [65, 20, -25, -70, -112]
for xx in xs: d.line([TT((xx, y1)), TT((xx, y0))], fill=(255, 120, 0), width=10)
for yy in ys: d.line([TT((x0, yy)), TT((x1, yy))], fill=(255, 120, 0), width=10)
for r_ in range(4):
    for c_ in range(3):
        X, Y = TT((xs[c_], ys[r_])); d.text((X + 30, Y + 20), '%s%d' % ('ABC'[c_], r_ + 1), fill=(255, 120, 0), font=FG)
for o in outs:
    X, Y = TT(nodes[o]['p']); d.text((X - 170, Y + 20), 'LANÇAMENTO', fill=(0, 90, 255), font=Fs)
hdr = Image.new('RGB', (bg.width, 330), 'white'); h = ImageDraw.Draw(hdr)
h.text((40, 30), 'DRENAGEM PLUVIAL v2 CORRIGIDA (R02) - feixes separados, mergulhos e pés de prumada', fill='black', font=F)
h.text((40, 130), 'AZUL = tubo (espessura = DN) | ROXO = ramal interno | VERMELHO = declividade imposta pelas cotas das caixas (relatório) | seta = sentido', fill='black', font=Fs)
h.text((40, 210), 'AMARELO = pé de prumada/subida (joelho + vertical) | VERDE = mergulho na chegada à caixa | quadrado = CA | círculo = PV | MAGENTA = caixa sem tubo', fill='black', font=Fs)
page = Image.new('RGB', (bg.width, bg.height + 330), 'white'); page.paste(hdr, (0, 0)); page.paste(bg, (0, 330))
fn = W_ + 'p/v2arq/pagina1_R02.png'; os.makedirs(os.path.dirname(fn), exist_ok=True); page.save(fn, optimize=True)
o = pymupdf.open(); w, hh = page.size; p = o.new_page(width=w * 72 / 300, height=hh * 72 / 300); p.insert_image(p.rect, filename=fn)
o.save(sys.argv[1], deflate=True); print(page.size, os.path.getsize(sys.argv[1]) // 1024, 'KB')
page.crop((300, 330 + 2500, 300 + 1800, 330 + 2500 + 1300)).save(W_ + 'p/v2arq/zoom_R02.png')
