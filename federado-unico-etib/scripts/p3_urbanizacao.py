# -*- coding: utf-8 -*-
"""Passo 3 — urbanização a partir do RVT da implantação da construtora (exportado em IFC, normalmente em UTM absoluto).
Ficam: platôs, piso tátil, guarda-corpos, rampas e paredes que não repetem a divisa. Saem: o terreno do RVT (vale o as built),
tubulação, muro/gradil a menos de "distancia_divisa" da divisa do passo 2, tudo que cruza uma área de "excluir_areas" (exceto lajes),
o que está fora do lote (casas vizinhas desenhadas como paredes genéricas). Cota: soma "dz" (conferir com p0_cota_rvt.py).
Os platôs passam por baixo dos módulos (no RVT os módulos são vínculos): a projeção dos pisos dos módulos sai deles (senão piso duplo).
Uso: python p3_urbanizacao.py escola.json   (depois de p1 e p2)  -> trabalho/urb/<SIGLA>_URB_RVT.ifc"""
import os, sys, numpy as np, shapely, ifcopenshell, ifcopenshell.api
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg):
    U_ = cfg['urbanizacao_rvt']; O = ef.origem(cfg); s = ef.ajustes_geom()
    divisa = ifcopenshell.open(ef.saida_urb(cfg, 'DIVISA'))
    peg_div = [ef.pegada(e, s=s) for e in divisa.by_type('IfcWall') + divisa.by_type('IfcRailing')]
    DIV = unary_union(peg_div).buffer(U_.get('distancia_divisa', 1.5))
    LOTE = MultiPoint(np.vstack([np.array(p.exterior.coords) for p in peg_div])).convex_hull.buffer(1.0)
    AREAS = [(a['nome'], Polygon(a['poligono'])) for a in U_.get('excluir_areas', [])]
    f = ifcopenshell.open(ef.caminho(cfg, U_['arquivo'])); n0 = len(f.by_type('IfcProduct'))
    ef.transformar(f, ef.matriz(U_.get('posicao', {}), cfg))   # primeiro a posição: daqui em diante tudo em coordenadas do projeto
    sai = {'terreno': 0, 'divisa': 0, 'instalação': 0, 'fora do lote': 0, **{n: 0 for n, _ in AREAS}}
    def motivo(e):
        if e.is_a('IfcGeographicElement'): return 'terreno'
        if any(e.is_a(c) for c in ('IfcFlowSegment', 'IfcFlowFitting', 'IfcDistributionPort')): return 'instalação'
        if not e.Representation or e.is_a('IfcSpatialStructureElement'): return None
        try: p = ef.pegada(e, s=s)
        except RuntimeError: return None
        if any(e.is_a(c) for c in ('IfcWall', 'IfcMember', 'IfcPlate', 'IfcDoor', 'IfcCurtainWall')):
            q = p if p.area > 1e-6 else p.buffer(0.05)
            if DIV.contains(q) or q.intersection(DIV).area > 0.8 * q.area: return 'divisa'
        if e.is_a('IfcSlab'): return None
        for n, A in AREAS:
            if p.intersects(A): return n
        if not LOTE.contains(p.centroid): return 'fora do lote'
        return None
    for i in [e.id() for e in f.by_type('IfcProduct')]:
        try: e = f.by_id(i)
        except RuntimeError: continue
        k = motivo(e)
        if k: ifcopenshell.api.run('root.remove_product', f, product=e); sai[k] += 1
    # platôs: tira a projeção dos pisos dos módulos e refaz como extrusão (platô é plano)
    mods = [ef.saida_modulo(cfg, m) for m in cfg['modulos']] + [fn for fn, x in ef.estruturas_rvt(cfg)]
    PM = ef.pisos_dos_modulos(mods, U_.get('cota_max_piso_modulo', cfg['cota']['piso_max'])).buffer(0.02)
    ctx = [c for c in f.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier == 'Body'][0]
    def perfil(pg):
        pts = lambda r: f.createIfcPolyline([f.createIfcCartesianPoint((float(x), float(y))) for x, y in list(r.coords)])
        if pg.interiors: return f.createIfcArbitraryProfileDefWithVoids('AREA', None, pts(pg.exterior), [pts(r) for r in pg.interiors])
        return f.createIfcArbitraryClosedProfileDef('AREA', None, pts(pg.exterior))
    recortes = {}
    for e in list(f.by_type('IfcSlab')):
        if not e.Representation: continue
        try: P, z0, z1 = ef.topo(e, s)
        except RuntimeError: continue
        if P.intersection(PM).area < 0.5: continue
        R = P.difference(PM); R = [g for g in getattr(R, 'geoms', [R]) if g.area > 0.5]
        if not R: ifcopenshell.api.run('root.remove_product', f, product=e); recortes[e.Name] = 0; continue
        pos = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., float(z0))))
        sol = [f.createIfcExtrudedAreaSolid(perfil(shapely.geometry.polygon.orient(g.simplify(0.005))), pos, f.createIfcDirection((0., 0., 1.)), float(z1 - z0)) for g in R]
        e.ObjectPlacement = f.createIfcLocalPlacement(None, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., 0.))))
        e.Representation = f.createIfcProductDefinitionShape(None, None, [f.createIfcShapeRepresentation(ctx, 'Body', 'SweptSolid', sol)])
        recortes[e.Name] = round(sum(g.area for g in R), 1)
    print('platôs recortados nos pisos dos módulos (m² que ficam):', recortes)
    for e in f.by_type('IfcElement'):
        ef.dados(f, e, {'disciplina': 'ARQ', 'sistema': 'ARQ-URB', 'modulo': 'URB', 'origem': U_.get('origem', U_['arquivo'])})
    ef.georef(f, cfg); n_a = ef.graus_para_rad(f)
    out = ef.saida_urb(cfg, 'URB_RVT'); f.write(out)
    print(out, 'produtos', n0, '->', len(ifcopenshell.open(out).by_type('IfcProduct')), 'tirados', sai, 'ângulos', n_a)

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]))
