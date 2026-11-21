# -*- coding: utf-8 -*-
"""Sátiro Dias — conferência visual das pranchas revisadas: recorte da original (CDE) | revisada no mesmo ponto UTM.
Uso: python -X utf8 sat_conferir.py FOLHA E N [janela_m] saida.png   (FOLHA: AF-001, ESG-001, EL-001, EL-002, IN-001, CPS-ELE-001)"""
import os, sys, math, json
import numpy as np, pymupdf
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\pendencias'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import sat_recortes as SR
import escolas.satiro as S
from PIL import Image
EXE = SR.EXE
REV = {'AF-001': 'R01', 'ESG-001': 'R01', 'EL-001': 'R02', 'EL-002': 'R02', 'IN-001': 'R04', 'CPS-ELE-001': 'R01'}
f, E, N = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); jan = float(sys.argv[4]) if len(sys.argv) > 5 else 14.0; out = sys.argv[-1]
dwg = S._DWG[f]; base = os.path.basename(dwg)[:-4]
dxf = os.path.join(EXE, '_copias', base + '.dxf')
nome_rev = base[:-3].replace('CP1-CPS', 'ETIB-CPS') + REV[f]
pdfs = [os.path.join(r'D:\Projeto Modelagem\PRANCHAS\ETIB-SATIRO-DIAS', base + '.pdf'), os.path.join(EXE, 'PDF', nome_rev + '.pdf')]
T = SR.TJ[dwg]; a = math.radians(T['rot_deg']); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]); t = np.array(T['t'])
q = R.T @ (np.array([E, N]) - t)
ims = []
for pdf in pdfs:
    doc, d2p = SR.calibrar(dxf, pdf); pg = doc[0]
    h = jan * 0.64; cant = d2p(np.array([q + [-jan / 2, -h / 2], q + [jan / 2, h / 2], q + [-jan / 2, h / 2], q + [jan / 2, -h / 2]]))
    lo, hi = cant.min(0), cant.max(0); rect = pymupdf.Rect(lo[0], lo[1], hi[0], hi[1]); z = 900 / rect.width
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=rect, alpha=False)
    im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    if doc.rot0: im = im.rotate(-doc.rot0, expand=True)
    ims.append(im)
W = sum(i.width for i in ims) + 10; H = max(i.height for i in ims)
o = Image.new('RGB', (W, H), 'black'); x = 0
for i in ims: o.paste(i, (x, 0)); x += i.width + 10
o.save(out)
