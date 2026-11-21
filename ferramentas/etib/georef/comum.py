# -*- coding: utf-8 -*-
"""Funções comuns da extração das redes de uma escola (fase 2), sobre os *_GEO em UTM. Caminhos pelas variáveis ETIB_DXF_GEO, ETIB_RELATORIOS, ETIB_WORK_REDE e ETIB_PREFIXO."""
import sys, os, math, re, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler

DX = os.environ.get('ETIB_DXF_GEO', r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\<ESCOLA>\dxf_geo')   # DXF georreferenciados da escola
REL = os.environ.get('ETIB_RELATORIOS', r'D:\Projeto Modelagem\ETIB-<ESCOLA>\RELATORIOS')
WRK = os.environ.get('ETIB_WORK_REDE', r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\<ESCOLA>\rede')
os.makedirs(WRK, exist_ok=True)
P = os.environ.get('ETIB_PREFIXO', 'AA-CTR-MUN-LOC-ETIB-')   # prefixo do nome das folhas da escola
F = {'SIT': 'IMP-PE-URB-001-SIT-R02_GEO', 'SIT_REF': 'IMP-PE-URB-001-SIT-R02_REF', 'TOP': 'IMP-PE-TOP-001-PLT-R00_REF',
     'TER': 'TER-IMP-001-R00_REF', 'AF': 'IMP-PE-AGF-001-R02_GEO', 'ESG': 'IMP-PE-ESG-001-HIG-R02_GEO',
     'DRE': 'IMP-PE-DRE-001-DRG-R02_GEO', 'INC': 'IMP-PE-INC-001-ING-R03_GEO', 'EL1': 'IMP-PE-EL-001-ELG-R05_GEO',
     'EL2': 'IMP-PE-EL-002-ELG-R02_GEO'}


def carrega(tag):
    return ler(os.path.join(DX, P + F[tag] + '.dxf'))


_lote = None
def lote():
    """Polígono do lote (bloco POLIGONAL do SIT, em UTM)."""
    global _lote
    if _lote is None:
        S = carrega('SIT')
        cand = [d for d in S if d['tipo'] == 'PL' and d['layer'] == 'PERIMETRO' and d['path'] == 'POLIGONAL']
        _lote = cand[0]['pts'][:, :2]
    return _lote


def dentro(p, poly):
    """Ponto(s) dentro do polígono (ray casting)."""
    p = np.atleast_2d(p); x, y = p[:, 0], p[:, 1]
    res = np.zeros(len(p), bool)
    xs, ys = poly[:, 0], poly[:, 1]
    j = len(poly) - 1
    for i in range(len(poly)):
        c = ((ys[i] > y) != (ys[j] > y)) & (x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i] + 1e-300) + xs[i])
        res ^= c; j = i
    return res


def dist_poly(p, poly):
    """Distância de pontos ao contorno do polígono."""
    p = np.atleast_2d(p)[:, :2]
    a = poly; b = np.roll(poly, -1, axis=0)
    best = np.full(len(p), np.inf)
    for s, e in zip(a, b):
        v = e - s; L2 = max(v @ v, 1e-12)
        t = np.clip(((p - s) @ v) / L2, 0, 1)
        q = s + t[:, None] * v
        best = np.minimum(best, np.hypot(*(p - q).T))
    return best


def na_obra(p, folga=15.0):
    """Dentro do lote ou a até `folga` m do contorno (ligações na rua)."""
    poly = lote()
    p = np.atleast_2d(p)[:, :2]
    return dentro(p, poly) | (dist_poly(p, poly) < folga)


def num(s):
    s = s.replace(',', '.')
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    return float(m.group()) if m else None
