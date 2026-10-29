# -*- coding: utf-8 -*-
"""Passo 0 — antes de usar o RVT da implantação: em que cota ele está? Compara o terreno do RVT (IfcGeographicElement do IFC exportado,
em UTM absoluto) com o terreno as built da escola (o mesmo das redes) nos mesmos pontos em planta.
Se a diferença é quase constante (p5 e p95 perto da mediana), o RVT está na cota de projeto: use dz = -mediana em "urbanizacao_rvt.posicao".
Na Jandaíra deu mediana -0,566 m (p5 -0,66 / p95 -0,46): dz = 0,565.
Uso: python p0_cota_rvt.py escola.json arquivo_do_rvt.ifc"""
import os, sys, numpy as np, ifcopenshell
from scipy.interpolate import LinearNDInterpolator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

cfg = ef.carregar(sys.argv[1]); O = ef.origem(cfg)
T = ifcopenshell.open(ef.caminho(cfg, cfg['terreno_asbuilt'])); TV = np.vstack([v for e, v, t in ef.formas(T, T.by_type('IfcGeographicElement'))])
R = ifcopenshell.open(sys.argv[2]); RV = [v for e, v, t in ef.formas(R, R.by_type('IfcGeographicElement'))]
if not RV: sys.exit('o IFC do RVT não tem terreno (IfcGeographicElement): exporte com a topografia visível')
RV = np.vstack(RV); RV[:, :2] -= O if np.abs(RV[:, :2]).max() > 1e5 else 0   # UTM absoluto -> projeto
z = LinearNDInterpolator(TV[:, :2], TV[:, 2])(RV[:, 0], RV[:, 1]); ok = np.isfinite(z)
d = RV[ok, 2] - z[ok]
print(f'pontos comparados {ok.sum()} de {len(RV)}')
print(f'RVT − as built: mediana {np.median(d):+.3f} m, p5 {np.percentile(d, 5):+.3f}, p95 {np.percentile(d, 95):+.3f}')
print(f'sugestão: "posicao": {{"dz": {-np.median(d):.3f}}}' if abs(np.median(d)) > 0.05 else 'RVT na mesma cota do as built: dz = 0')
