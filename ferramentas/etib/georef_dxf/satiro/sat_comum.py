# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — funções comuns da fase 2 (extração das redes) sobre os *_GEO em UTM.
Lê os DXF dos _GEO com o leitor da Catu (FERRAMENTAS\georef\dxf_ler.py) e reaproveita rede_lib/gravidade_lib/linha_lib.
Os DXF dos _GEO saem do accoreconsole (DXFOUT) e ficam em DXF_DIR; o cache .pkl fica ao lado."""
import sys, os, re, pickle
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler  # noqa: E402

DXF_DIR = os.environ.get('SAT_DXF', r'C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\b28e7087-be02-4c86-8417-721af249be58\scratchpad\work\geo')
REL = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS\FASE2_REDES_2026-10-18'
WRK = os.path.join(DXF_DIR, 'rede')
os.makedirs(REL, exist_ok=True); os.makedirs(WRK, exist_ok=True)
P = '24-049-STK-XXX-'
F = {'SIT': 'ETIB-IMP-PE-URB-002-SIT-R06_GEO', 'PAV': 'ETIB-IMP-PE-URB-001-PAV-R07_GEO', 'TOP': 'ETIB-IMP-PE-TOP-001-PLT-R00_GEO',
     'TER': 'ETIB-IMP-PE-TER-001-PLT-R00_GEO', 'AF': 'ETIB-IMP-PE-AF-001-HIG-R00_GEO', 'ESG': 'ETIB-IMP-PE-ESG-001-HIG-R00_GEO',
     'DRE1': 'ETIB-IMP-PE-DRE-001-DRG-R02_GEO', 'DRE2': 'ETIB-IMP-PE-DRE-002-DRG-R02_GEO', 'IN': 'ETIB-IMP-PE-IN-001-ING-R03_GEO',
     'EL1': 'ETIB-IMP-PE-EL-001-ELG-R01_GEO', 'EL2': 'ETIB-IMP-PE-EL-002-ELG-R01_GEO', 'CPS_DRE': 'ETIB-CPS-PE-DRE-001-DRG-R01_GEO',
     'CPS_EL1': 'CP1-CPS-PE-ELE-001-ELG-R00_GEO', 'CPS_EL2': 'CP1-CPS-PE-ELE-002-ELG-R00_GEO', 'CPS_IN': 'ETIB-CPS-PE-IN-001-ING-R01_GEO'}
# área da obra (lote + rua), em UTM; tudo fora é carimbo, legenda, detalhe ou papel
OBRA = (545790.0, 8716030.0, 546130.0, 8716320.0)


def carrega(tag):
    fn = os.path.join(DXF_DIR, P + F[tag] + '.dxf')
    pk = fn + '.ler.pkl'
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(fn):
        return pickle.load(open(pk, 'rb'))
    E = ler(fn)
    pickle.dump(E, open(pk, 'wb'))
    return E


def na_obra(p, box=OBRA):
    p = np.atleast_2d(p)[:, :2]
    return (p[:, 0] > box[0]) & (p[:, 0] < box[2]) & (p[:, 1] > box[1]) & (p[:, 1] < box[3])


def num(s):
    s = s.replace(',', '.')
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    return float(m.group()) if m else None
