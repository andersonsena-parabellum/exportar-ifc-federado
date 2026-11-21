# -*- coding: utf-8 -*-
"""Olindina — terreno do IMP as built (lido no Revit em 22/10/2026 por olindina/revit/onn_imp_ler.cs, triângulos em UTM em
FERRAMENTAS/georef/work/OLINDINA/imp/imp_topo.csv) -> escolas/dados/olindina_terreno_imp.npz.
Superfície = faces de cima do sólido topográfico 503886 "TERRENO + GRAMA" (o platô da escola em 168,00 e os taludes até 161),
com os sólidos 504678 e 505725 (168,22: o BA5 e o pátio entre os prédios existentes, que são vazios no 503886) por cima.
Ficam de fora as subdivisões 503905/504033 (pavimento da rua, a sudoeste, longe das redes).
Uso: .venv/Scripts/python.exe -X utf8 olindina/ifc/onn_terreno_imp.py"""
import csv, os, sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\satiro\imp')
import imp_terreno_lib as it          # noqa: E402

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\imp\imp_topo.csv'
OUT = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\olindina_terreno_imp.npz'
IDS = ('503886', '504678', '505725')
CAIXA = (573840.0, 8743200.0, 573990.0, 8743370.0)
PASSO = 0.5


def main():
    T = []
    for r in csv.DictReader(open(IMP, encoding='utf-8'), delimiter=';'):
        if r['id'] in IDS and float(r['nz']) > 0.05:
            T.append([list(map(float, r[k].split(','))) for k in 'abc'])
    # os triângulos do Revit não formam uma triangulação válida em planta (faces sobrepostas nas bordas): face de cima numa grade
    # de 0,50 m (o maior z), e a grade vira a malha
    T = np.array(T)
    xs = np.arange(CAIXA[0], CAIXA[2] + 1e-6, PASSO); ys = np.arange(CAIXA[1], CAIXA[3] + 1e-6, PASSO); X, Y = np.meshgrid(xs, ys)
    Z = it.raster(list(T), X, Y)
    ok = ~np.isnan(Z); idx = -np.ones(Z.shape, int); idx[ok] = np.arange(ok.sum())
    Vk = np.column_stack([X[ok], Y[ok], Z[ok]])
    F = []
    for j in range(Z.shape[0] - 1):
        for i in range(Z.shape[1] - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if min(a, b, c, d) < 0: continue
            F += [(a, b, c), (a, c, d)]
    F = np.array(F)
    np.savez_compressed(OUT, pts=Vk, tri=F, fonte=np.array('IMP as built (Revit, 22/10/2026): sólidos topográficos TERRENO + GRAMA e platôs dos prédios'))
    print('gravado', OUT, '| vértices', len(Vk), '| triângulos', len(F), '| z', Vk[:, 2].min().round(2), '–', Vk[:, 2].max().round(2))


if __name__ == '__main__':
    main()
