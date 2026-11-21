# -*- coding: utf-8 -*-
"""ETIB Catu — terreno a partir do IFC do IMP renivelado (REFERENCIAS_RVT/IMP/IFC/24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.ifc).
Lê a geometria (IfcOpenShell, coordenadas do mundo), confere a posição em UTM contra o IMP lido no Revit (imp_topo.csv),
rasteriza a face de cima (pisos por cima do terreno) a 1 m e grava escolas/dados/catu_terreno_imp.npz (pts + tri da grade + linhas
da SIT), o terreno que o preclash da Catu passa a usar. Confere contra a superfície-alvo (projetos de base) e as CT das caixas.
Uso: .venv/Scripts/python.exe -X utf8 georef/imp_catu_ifc_terreno.py"""
import os, sys, csv, collections
import numpy as np
import ifcopenshell, ifcopenshell.geom
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import imp_catu_terreno as it            # noqa: E402
from preclash.terreno import Terreno     # noqa: E402

IFC = r'D:\Projeto Modelagem\ETIB-CATU\REFERENCIAS_RVT\IMP\IFC\24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.ifc'
OUT = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\catu_terreno_imp.npz'
PROV = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\catu_terreno.npz'
BOX = (567600.0, 8634520.0, 567820.0, 8634730.0)


def triangulos():
    f = ifcopenshell.open(IFC)
    st = ifcopenshell.geom.settings(); st.set('use-world-coords', True)
    por = collections.defaultdict(list); n = collections.Counter()
    for el in f.by_type('IfcProduct'):
        if not el.Representation or el.is_a() in ('IfcSite', 'IfcSpace', 'IfcOpeningElement', 'IfcAnnotation'): continue
        try: sh = ifcopenshell.geom.create_shape(st, el)
        except Exception: continue
        V = np.array(sh.geometry.verts).reshape(-1, 3); Fa = np.array(sh.geometry.faces).reshape(-1, 3)
        por[el.is_a()].append(V[Fa]); n[el.is_a()] += 1
    mc = f.by_type('IfcMapConversion')
    return {k: np.vstack(v) for k, v in por.items()}, n, (mc[0] if mc else None)


def main():
    T, n, mc = triangulos()
    print('elementos', dict(n)); print('IfcMapConversion', (mc.Eastings, mc.Northings, mc.OrthogonalHeight) if mc else None)
    todos = np.vstack(list(T.values()))
    ref = np.vstack([q[2] for q in it.ler(os.path.join(it.IMP, 'imp_topo.csv'))])
    off = np.zeros(3)
    if abs(np.median(todos[:, :, 0]) - np.median(ref[:, 0])) > 50:          # IFC em coordenadas locais: soma a conversão
        off = np.array([mc.Eastings, mc.Northings, mc.OrthogonalHeight]) if mc else np.array([np.median(ref[:, 0]) - np.median(todos[:, :, 0]), np.median(ref[:, 1]) - np.median(todos[:, :, 1]), 0])
    T = {k: v + off for k, v in T.items()}
    print('extensão UTM', np.vstack(list(T.values())).reshape(-1, 3).min(0).round(2), np.vstack(list(T.values())).reshape(-1, 3).max(0).round(2), '| deslocamento aplicado', off)
    xs = np.arange(BOX[0], BOX[2] + 0.01, 1.0); ys = np.arange(BOX[1], BOX[3] + 0.01, 1.0); X, Y = np.meshgrid(xs, ys)
    def topo(tris):
        nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); L = np.linalg.norm(nrm, axis=1)
        return tris[(L > 1e-9) & (nrm[:, 2] / np.maximum(L, 1e-12) > 0.2)]
    terr = [v for k, v in T.items() if k in ('IfcGeographicElement', 'IfcSite', 'IfcBuildingElementProxy')]
    pis = [v for k, v in T.items() if k == 'IfcSlab']
    Zt = it.raster(topo(np.vstack(terr)), X, Y) if terr else np.full(X.shape, np.nan)
    Zp = it.raster(topo(np.vstack(pis)), X, Y) if pis else np.full(X.shape, np.nan)
    Z = np.where(np.isnan(Zp), Zt, Zp)
    print('cobertura', round((~np.isnan(Z)).mean() * 100), '%')
    # conferência contra o alvo (projetos de base) e as CT
    A = Terreno(PROV).z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    d = (Zt - A)[~np.isnan(Zt) & ~np.isnan(A)]
    print(f'terreno IFC − alvo (área do alvo): mediana {np.median(d):+.3f}  p5 {np.percentile(d, 5):+.3f}  p95 {np.percentile(d, 95):+.3f}  |d|<5cm {np.mean(np.abs(d) < 0.05) * 100:.0f}%')
    F3 = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\FASE3_COTAS_2026-10-18'
    for disc in ('ESG', 'DRE'):
        R = [r for r in csv.DictReader(open(os.path.join(F3, f'CAT_fase3_{disc}_caixas.csv'), encoding='utf-8-sig'), delimiter=';') if r['CT']]
        P = np.array([[float(r['E']), float(r['N'])] for r in R]); ct = np.array([float(r['CT']) for r in R])
        fx = ((P[:, 0] - xs[0])).round().astype(int); fy = ((P[:, 1] - ys[0])).round().astype(int)
        z = Z[fy, fx]; ok = ~np.isnan(z)
        print(f'  {disc}: superfície IFC − CT nas caixas: mediana {np.median(z[ok] - ct[ok]):+.2f}  máx |d| {np.abs(z[ok] - ct[ok]).max():.2f} ({ok.sum()} caixas)')
    # grade -> pts + tri para o preclash
    idx = -np.ones(Z.shape, int); ok = ~np.isnan(Z); idx[ok] = np.arange(ok.sum())
    pts = np.column_stack([X[ok], Y[ok], Z[ok]]); tri = []
    for j in range(Z.shape[0] - 1):
        for i in range(Z.shape[1] - 1):
            a, b, c, dd = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if a >= 0 and b >= 0 and c >= 0: tri.append((a, b, c))
            if a >= 0 and c >= 0 and dd >= 0: tri.append((a, c, dd))
    arq = np.load(PROV)['arq']
    np.savez_compressed(OUT, pts=pts, tri=np.array(tri, int), arq=arq,
                        fonte=np.array('IMP as built renivelado na cota dos projetos de base (IFC 24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.ifc)'))
    print('gravado', OUT, len(pts), 'pontos', len(tri), 'triângulos')


if __name__ == '__main__':
    main()
