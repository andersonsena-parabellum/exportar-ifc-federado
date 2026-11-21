# -*- coding: utf-8 -*-
"""Plota o DWG da contenção transformado (UTM) sobre o SIT_REF, para conferir o georreferenciamento (PIL)."""
import sys, json, math, re
import numpy as np
from PIL import Image, ImageDraw

CNT = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work\dump_CNT_local.tsv"
SIT = r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\dump_SIT.tsv"
T = json.load(open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\CAD_GEORREFERENCIADO\transformacao_CNT_local_para_UTM.json", encoding='utf-8'))
out = sys.argv[1]
bbox = [float(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else None   # xmin,ymin,xmax,ymax (UTM)
W = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
a = math.radians(T['rigid']['rot_deg']); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]); t = np.array(T['rigid']['t'])
NUM = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')


def segs(fn, tf=False, skip=()):
    res = []
    for ln in open(fn, encoding='cp1252', errors='replace'):
        p = ln.rstrip('\n').split('\t')
        if len(p) < 4 or p[0] not in ('LINE', 'LWPOLYLINE') or p[1] in skip: continue
        v = np.array([(float(x), float(y)) for x, y in NUM.findall(p[3])])
        if len(v) < 2 or np.abs(v).max() > 1e7: continue
        if tf:
            if np.abs(v).max() > 1000: continue
            v = (R @ v.T).T + t
        res.append((p[1], v))
    return res

sit = segs(SIT, skip=() if 'piso' in out else ('09-PISO',))
cnt = segs(CNT, tf=True)
if not bbox:
    allp = np.vstack([v for _, v in sit])
    bbox = [*np.percentile(allp, 1, axis=0), *np.percentile(allp, 99, axis=0)]
H = int(W * (bbox[3] - bbox[1]) / (bbox[2] - bbox[0]))
s = W / (bbox[2] - bbox[0])
img = Image.new('RGB', (W, H), 'white'); dr = ImageDraw.Draw(img)
P = lambda v: [((x - bbox[0]) * s, (bbox[3] - y) * s) for x, y in v]
for lay, v in sit:
    dr.line(P(v), fill=(120, 125, 140) if lay == 'ARQ_BASE' else ((215, 215, 215) if lay.startswith('ARQ_DEMOL') else ((150, 200, 160) if lay == '09-PISO' else (165, 170, 185))), width=1)
cols = {'ARQ_BASE': (229, 57, 53), '0': (21, 101, 192), 'AUX_01': (46, 125, 50), 'CONGELA': (255, 143, 0), 'TOP-ESCADA': (142, 36, 170)}
for lay, v in cnt:
    dr.line(P(v), fill=cols.get(lay, (80, 80, 80)), width=1 if lay == 'ARQ_BASE' else 2)
# contorno dos blocos lido das estruturas vinculadas no Revit (interno → UTM), em preto grosso
for b in json.load(open(r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\blocos.json", encoding='cp1252')):
    v = [(x + 561500.0, y + 8658000.0) for x, y in b['coords']]
    dr.line(P(v + v[:1]), fill=(0, 0, 0), width=3)
dr.text((10, 10), 'CNT: ARQ_BASE vermelho / layer 0 azul / AUX_01 verde / CONGELA laranja / TOP-ESCADA roxo   SIT_REF: cinza', fill='black')
dr.text((10, 24), f'bbox UTM {bbox[0]:.1f},{bbox[1]:.1f} .. {bbox[2]:.1f},{bbox[3]:.1f}   escala {s:.2f} px/m', fill='black')
img.save(out); print('ok', out, W, H)

