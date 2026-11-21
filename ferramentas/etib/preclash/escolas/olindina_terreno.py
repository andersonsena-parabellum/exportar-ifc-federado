# -*- coding: utf-8 -*-
"""Olindina — terreno PROVISÓRIO do preclash (escolas/dados/olindina_terreno_provisorio.npz), até ler o IMP as built no Revit.
Cotas da base: CT das caixas das pranchas (ESG-001: 168,00 / 168,30) e as cotas de piso acabado da SIT R01 (texto no layer 0:
168,00 / 168,15 / 168,30). Grade de 1 m na caixa da obra, interpolação pelo inverso da distância (os 8 pontos mais próximos).
Uso: .venv/Scripts/python.exe -X utf8 preclash/escolas/olindina_terreno.py"""
import os, sys, re, csv
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import casar  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, 'dados', 'olindina_terreno_provisorio.npz')
F2 = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS\FASE2_REDES_2026-10-21'
SIT = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\dxf_geo\24-049-ONN-CTO-ETIB-IMP-PE-URB-001-SIT-R01_GEO.dxf'
CAIXA = (573860.0, 8743220.0, 573970.0, 8743355.0)


def pontos_base():
    P = []
    for fn in ('ONN_fase2_AP_caixas.csv', 'ONN_fase2_ESG_caixas.csv'):
        for r in csv.DictReader(open(os.path.join(F2, fn), encoding='utf-8-sig'), delimiter=';'):
            P.append((float(r['E']), float(r['N']), float(r['CT'])))
    g = casar.cache_load(SIT)
    for t in g['texts']:
        s = re.sub(r'\\[A-Za-z][^;]*;|[{}]', '', t['t']).strip()
        if t['lay'] == '0' and re.fullmatch(r'16[5-9],\d\d', s):
            P.append((t['p'][0], t['p'][1], float(s.replace(',', '.'))))
    return np.array(P)


def main():
    B = pontos_base()
    xs = np.arange(CAIXA[0], CAIXA[2] + 0.01, 1.0); ys = np.arange(CAIXA[1], CAIXA[3] + 0.01, 1.0)
    X, Y = np.meshgrid(xs, ys); Q = np.column_stack([X.ravel(), Y.ravel()])
    d = np.hypot(Q[:, None, 0] - B[None, :, 0], Q[:, None, 1] - B[None, :, 1])
    k = np.argsort(d, axis=1)[:, :8]; dk = np.take_along_axis(d, k, 1) + 0.5; w = 1 / dk ** 2
    Z = (w * B[k, 2]).sum(1) / w.sum(1)
    pts = np.column_stack([Q, Z])
    np.savez_compressed(OUT, pts=pts, fonte=np.array('PROVISÓRIO: CT das caixas (ESG-001) + cotas de piso da SIT R01, grade 1 m (IDW)'))
    print('gravado', OUT, '| pontos base', len(B), '| z', round(Z.min(), 2), '–', round(Z.max(), 2))


if __name__ == '__main__':
    main()
