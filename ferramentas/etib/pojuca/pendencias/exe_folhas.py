# -*- coding: utf-8 -*-
"""Pojuca — folhas da página de pendências: DXF da cópia original (EXECUTIVO_2026-10-26/_copias, mesmas coordenadas da revisada) e o
PDF da revisão nova (ou da origem plotada, se a folha não mudou)."""
import os

_I, _C = '24-049-PJC-CTO-ETIB-IMP-PE-', '24-049-PJC-CTO-ETIB-CPS-PE-'
F = {'AF-001': (_I + 'AF-001-AFR-R00', 'R02'), 'ESG-001': (_I + 'ESG-001-HIG-R00', 'R01'), 'DRE-001': (_I + 'DRE-001-DRG-R00', 'R01'),
     'EL-001': (_I + 'EL-001-ELG-R00', 'R02'), 'EL-002': (_I + 'EL-002-ELG-R00', 'R02'), 'IC-001': (_I + 'IC-001-INC-R01', 'R03'),
     'CPS-EL-001': (_C + 'EL-001-ELG-R01', 'R03')}


def folhas(exe):
    out = {}
    for k, (orig, rn) in F.items():
        pdf = f'{exe}/PDF/{orig[:-3]}{rn}.pdf'
        if not os.path.exists(pdf): pdf = f'{exe}/_origem_plotada/{orig}.pdf'
        out[k] = dict(dxf=f'{exe}/_copias/{orig}.dxf', pdf=pdf, chave=k)
    return out
