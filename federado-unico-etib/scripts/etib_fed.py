# -*- coding: utf-8 -*-
"""Biblioteca comum do federado único ETIB (skill federado-unico-etib).
Tudo em coordenadas do PROJETO: X = E - e0, Y = N - n0, Z = cota absoluta (m), com a georreferência da escola no IfcMapConversion."""
import os, sys, json, math, multiprocessing, numpy as np
import ifcopenshell, ifcopenshell.api, ifcopenshell.geom, ifcopenshell.guid, ifcopenshell.util.element as ue, ifcopenshell.util.placement as up
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union

TIRAR_PROPS = {'fora_do_comercial', 'angulo_real', 'deflexao_junta_graus'}   # propriedades de trabalho: nunca no IFC entregue


# ---------- configuração ----------
def carregar(caminho_cfg):
    """lê o JSON da escola; 'raiz' (absoluta ou relativa ao JSON) é a pasta de trabalho do federado da escola"""
    cfg = json.load(open(caminho_cfg, encoding='utf-8'))
    cfg['_raiz'] = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(caminho_cfg)), cfg.get('raiz', '.')))
    cfg['_saidas'] = os.path.join(cfg['_raiz'], cfg.get('pasta_saidas', '.'))   # trabalho/, saida/ e envio/ ficam aqui
    return cfg

def caminho(cfg, p):
    return p if os.path.isabs(p) else os.path.join(cfg['_raiz'], p)

def pasta(cfg, *sub):
    d = os.path.normpath(os.path.join(cfg['_saidas'], *sub)); os.makedirs(d, exist_ok=True); return d

def saida_modulo(cfg, mod): return os.path.join(pasta(cfg, 'trabalho', 'modulos'), f"{cfg['sigla']}_ARQ_{mod}.ifc")
def saida_estrutura(cfg, i, x): return os.path.join(pasta(cfg, 'trabalho', 'estrutura'), f"{cfg['sigla']}_EST_{x['modulo']}_{i:02d}.ifc")
def estruturas_rvt(cfg): return [(saida_estrutura(cfg, i, x), x) for i, x in enumerate(cfg.get('estrutura_rvt', []))]
def saida_urb(cfg, nome): return os.path.join(pasta(cfg, 'trabalho', 'urb'), f"{cfg['sigla']}_{nome}.ifc")

def origem(cfg):
    g = cfg['georref']; return np.array((float(g['e0']), float(g['n0'])))


# ---------- georreferência e unidades ----------
def georef(f, cfg):
    """uma só georreferência para todos os arquivos (o MergeProjects aplica SetFalseOrigin em arquivo diferente ou sem ela)"""
    g = cfg['georref']
    for m in list(f.by_type('IfcMapConversion')) + list(f.by_type('IfcProjectedCRS')): f.remove(m)
    for c in f.by_type('IfcGeometricRepresentationContext'):
        if c.is_a('IfcGeometricRepresentationSubContext'): continue
        c.TrueNorth = f.createIfcDirection((0., 1.))
        crs = f.createIfcProjectedCRS(g['epsg'], g.get('nome', g['epsg']), g.get('datum', 'SIRGAS2000'), None, 'UTM', g.get('zona'), None)
        f.createIfcMapConversion(c, crs, float(g['e0']), float(g['n0']), 0., 1., 0., 1.)

def graus_para_rad(f):
    """arquivos em GRAU passam para RADIANO (o MergeProjects só converte comprimento: sem isso arcos e giros deformam)"""
    ua = f.by_type('IfcProject')[0].UnitsInContext
    ang = [u for u in ua.Units if getattr(u, 'UnitType', None) == 'PLANEANGLEUNIT']
    if not ang or ang[0].is_a('IfcSIUnit'): return 0
    k = math.pi / 180; n = 0
    for t in f.by_type('IfcTrimmedCurve'):
        if not t.BasisCurve.is_a('IfcConic'): continue
        for a in ('Trim1', 'Trim2'):
            setattr(t, a, [f.createIfcParameterValue(x.wrappedValue * k) if x.is_a('IfcParameterValue') else x for x in getattr(t, a)])
        n += 1
    for r in f.by_type('IfcRevolvedAreaSolid'): r.Angle = r.Angle * k; n += 1
    for p in f.by_type('IfcPropertySingleValue'):
        if p.NominalValue is not None and p.NominalValue.is_a('IfcPlaneAngleMeasure'): p.NominalValue = f.createIfcPlaneAngleMeasure(p.NominalValue.wrappedValue * k); n += 1
    ua.Units = [u for u in ua.Units if u not in ang] + [f.createIfcSIUnit(None, 'PLANEANGLEUNIT', None, 'RADIAN')]
    return n

def unidade_comprimento(f):
    u = [u for u in f.by_type('IfcProject')[0].UnitsInContext.Units if getattr(u, 'UnitType', None) == 'LENGTHUNIT']
    return (u[0].Prefix or '') + u[0].Name if u else '?'

def novo_ifc(cfg, nome):
    """arquivo IFC4 novo com unidades SI EXPLÍCITAS (unit.assign_unit sem argumento cria milímetro), contexto Body, georreferência e site"""
    f = ifcopenshell.api.run('project.create_file', version='IFC4')
    proj = ifcopenshell.api.run('root.create_entity', f, ifc_class='IfcProject', name=nome)
    U = [ifcopenshell.api.run('unit.add_si_unit', f, unit_type=t) for t in ('LENGTHUNIT', 'AREAUNIT', 'VOLUMEUNIT', 'PLANEANGLEUNIT')]
    ifcopenshell.api.run('unit.assign_unit', f, units=U)
    model = ifcopenshell.api.run('context.add_context', f, context_type='Model')
    body = ifcopenshell.api.run('context.add_context', f, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW', parent=model)
    georef(f, cfg)
    site = ifcopenshell.api.run('root.create_entity', f, ifc_class='IfcSite', name=f"ETIB {cfg['escola']}")
    ifcopenshell.api.run('aggregate.assign_object', f, products=[site], relating_object=proj)
    site.ObjectPlacement = f.createIfcLocalPlacement(None, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., 0.))))
    return f, body, site

def estilo(f, nome, rgb, transp=0.):
    return f.createIfcSurfaceStyle(nome, 'BOTH', [f.createIfcSurfaceStyleRendering(f.createIfcColourRgb(None, *rgb), transp, None, None, None, None, None, None, 'NOTDEFINED')])

def dados(f, e, props):
    ps = ifcopenshell.api.run('pset.add_pset', f, product=e, name='Dados_ETIB')
    ifcopenshell.api.run('pset.edit_pset', f, pset=ps, properties=props)


# ---------- posição ----------
def matriz(t, cfg):
    """t = {"giro_graus", "e", "n", "dz"} (origem do arquivo em UTM; arquivo já em UTM absoluto: e = n = 0 e giro 0)
    ou {"giro_graus", "x", "y", "dz"} (translação já em coordenadas do projeto). Giro em torno da origem do arquivo."""
    a = math.radians(t.get('giro_graus', 0.)); M = np.eye(4); M[:2, :2] = [[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]
    if 'x' in t: M[:3, 3] = [t['x'], t['y'], t.get('dz', 0.)]
    else: o = origem(cfg); M[:3, 3] = [t.get('e', 0.) - o[0], t.get('n', 0.) - o[1], t.get('dz', 0.)]
    return M

def transformar(f, M):
    """aplica M às placements raiz (as filhas acompanham); a translação de M está em metro e vai para a unidade do arquivo"""
    import ifcopenshell.util.unit as uu
    M = M.copy(); M[:3, 3] /= uu.calculate_unit_scale(f)
    for lp in f.by_type('IfcLocalPlacement'):
        if lp.PlacementRelTo is not None: continue
        X = M @ up.get_axis2placement(lp.RelativePlacement)
        lp.RelativePlacement = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint(tuple(float(x) for x in X[:3, 3])),
            f.createIfcDirection(tuple(float(x) for x in X[:3, 2])), f.createIfcDirection(tuple(float(x) for x in X[:3, 0])))


# ---------- geometria ----------
def ajustes_geom(mundo=True):
    s = ifcopenshell.geom.settings(); s.set('use-world-coords', mundo); return s

def formas(f, elementos=None, excluir=('IfcSpace', 'IfcOpeningElement', 'IfcAnnotation', 'IfcDistributionPort')):
    """gera (elemento, vértices Nx3, faces Mx3) em coordenadas do mundo, com vários processos"""
    s = ajustes_geom()
    it = ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), include=elementos) if elementos is not None else \
         ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), exclude=list(excluir))
    if not it.initialize(): return
    while True:
        sh = it.get(); v = np.array(sh.geometry.verts).reshape(-1, 3); t = np.array(sh.geometry.faces).reshape(-1, 3)
        if len(t): yield f.by_id(sh.id), v, t
        if not it.next(): break

def pegada(e, desloc=(0., 0.), s=None):
    v = np.array(ifcopenshell.geom.create_shape(s or ajustes_geom(), e).geometry.verts).reshape(-1, 3)
    return MultiPoint(v[:, :2] - np.asarray(desloc)).convex_hull

def topo(e, s=None):
    """projeção da face de cima de uma laje plana, cota de baixo e cota de cima"""
    g = ifcopenshell.geom.create_shape(s or ajustes_geom(), e).geometry
    v = np.array(g.verts).reshape(-1, 3); t = np.array(g.faces).reshape(-1, 3); zt = v[:, 2].max()
    ps = [Polygon(v[tr][:, :2]) for tr in t if np.all(v[tr][:, 2] > zt - 0.01)]
    return unary_union([p.buffer(0.001) for p in ps if p.area > 1e-6]), v[:, 2].min(), zt

def pisos_dos_modulos(arquivos, z_max):
    """projeção dos pisos dos módulos (lajes com topo abaixo de z_max): é o que sai dos platôs, para não haver piso duplo"""
    out = []
    for fn in arquivos:
        a = ifcopenshell.open(fn); s = ajustes_geom()
        for e in a.by_type('IfcSlab'):
            if not e.Representation: continue
            try: P, z0, z1 = topo(e, s)
            except RuntimeError: continue
            if z1 < z_max: out.append(P)
    return unary_union(out)

def pegada_construida(arquivos, z_ref):
    """pegada de tudo o que está acima de z_ref (sem fundação, vão e espaço): é o que sai dos pisos externos"""
    tris = []
    # mobiliário, louças, portas e janelas ficam dentro do prédio: não mudam a pegada e pesam (bloco RF3 de Alagoinhas: 13 milhões de triângulos)
    fora = ('IfcSpace', 'IfcOpeningElement', 'IfcAnnotation', 'IfcDistributionPort', 'IfcFurniture', 'IfcFurnishingElement', 'IfcSystemFurnitureElement',
            'IfcDoor', 'IfcWindow', 'IfcFlowTerminal', 'IfcSanitaryTerminal', 'IfcBuildingElementPart', 'IfcCovering')
    prisma = ('IfcWall', 'IfcColumn', 'IfcBeam', 'IfcMember', 'IfcRailing', 'IfcPlate', 'IfcCurtainWall')   # em planta é o fecho convexo (rápido)
    for fn in arquivos:
        f = ifcopenshell.open(fn)
        for e, v, t in formas(f, excluir=fora):
            if e.is_a('IfcFooting') or v[:, 2].max() <= z_ref: continue
            if any(e.is_a(c) for c in prisma): tris.append(MultiPoint(v[:, :2]).convex_hull.buffer(0.05)); continue
            T = [Polygon(x) for x in v[t][:, :, :2] if abs((x[1][0] - x[0][0]) * (x[2][1] - x[0][1]) - (x[1][1] - x[0][1]) * (x[2][0] - x[0][0])) > 1e-6]
            if T: tris.append(uniao(T).buffer(0.05))
    return uniao(tris).buffer(0.3).buffer(-0.3)

def uniao(geoms):
    """união robusta: malha de triângulos às vezes quebra a topologia do GEOS; com precisão fixa de 1 mm não quebra"""
    import shapely
    try: return unary_union(geoms)
    except shapely.errors.GEOSException: return shapely.union_all([shapely.set_precision(g, 0.001) for g in geoms], grid_size=0.001)


# ---------- remoção e limpeza ----------
def remover(f, criterio):
    """remove os produtos em que criterio(e) é verdadeiro; devolve quantos"""
    n = 0
    for i in [e.id() for e in f.by_type('IfcProduct')]:
        try: e = f.by_id(i)
        except RuntimeError: continue
        if criterio(e): ifcopenshell.api.run('root.remove_product', f, product=e); n += 1
    return n

def simplificar(f, nmax=5000):
    """portas, janelas e proxies com malha pesada (palheta etc.) viram a caixa envolvente; malhas pesadas soltas saem"""
    S = ajustes_geom(False); ctx = [c for c in f.by_type('IfcGeometricRepresentationContext') if c.ContextType == 'Model' and not c.is_a('IfcGeometricRepresentationSubContext')][0]
    sub = [c for c in f.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier == 'Body'] or [ctx]
    n = 0
    for e in f.by_type('IfcDoor') + f.by_type('IfcWindow') + f.by_type('IfcBuildingElementProxy'):
        if not e.Representation or sum(1 for x in f.traverse(e.Representation) if x.is_a('IfcFace')) < nmax: continue
        v = np.array(ifcopenshell.geom.create_shape(S, e).geometry.verts).reshape(-1, 3); lo, hi = v.min(0), v.max(0)
        prof = f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2))), None),
                                              float(max(hi[0] - lo[0], 0.01)), float(max(hi[1] - lo[1], 0.01)))
        sol = f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., float(lo[2]))), None, None),
                                           f.createIfcDirection((0., 0., 1.)), float(max(hi[2] - lo[2], 0.01)))
        velha = e.Representation
        e.Representation = f.createIfcProductDefinitionShape(None, None, [f.createIfcShapeRepresentation(sub[0], 'Body', 'SweptSolid', [sol])])
        try: ue.remove_deep2(f, velha)
        except Exception: pass
        n += 1
    for r in [r for r in f.by_type('IfcShapeRepresentation') if sum(1 for x in f.traverse(r) if x.is_a('IfcFace')) >= nmax]:
        if any(i.is_a('IfcProductDefinitionShape') for i in f.get_inverse(r)): continue
        for inv in list(f.get_inverse(r)):
            if inv.is_a('IfcPresentationLayerAssignment'): inv.AssignedItems = [x for x in inv.AssignedItems if x != r]
            elif inv.is_a('IfcRepresentationMap') and not any(u.is_a('IfcMappedItem') for u in f.get_inverse(inv)):
                for t in list(f.get_inverse(inv)):
                    if t.is_a('IfcTypeProduct'): t.RepresentationMaps = [x for x in t.RepresentationMaps if x != inv] or None
                if not f.get_inverse(inv): f.remove(inv)
        if not f.get_inverse(r): ue.remove_deep2(f, r)
    return n

def tirar_pset(f, ps):
    """pset e propriedades com f.remove (o remove_deep2 é lento em arquivo grande)"""
    for pr in list(getattr(ps, 'HasProperties', None) or []):
        if len(f.get_inverse(pr)) <= 1: f.remove(pr)
    f.remove(ps)

def limpar(f, soltos=True):
    """limpeza do federado: relações vazias, psets e usos de material soltos, GUID repetido, aplicativos duplicados.
    soltos=False pula a busca de pset/forma/uso de material soltos (feita antes em cada fonte: no arquivo grande cada remove leva segundos)"""
    import collections
    n = collections.Counter()
    # em lote (batch): depois de criar entidades no arquivo grande, cada remove avulso refaz o índice inverso inteiro (segundos cada)
    f.batch()
    for r in list(f.by_type('IfcRelDefinesByProperties')):
        if not r.RelatedObjects:
            pd = r.RelatingPropertyDefinition
            for p in (pd if isinstance(pd, tuple) else [pd]):
                if p and len(f.get_inverse(p)) <= 1: tirar_pset(f, p); n['pset_solto'] += 1   # só esta relação usa o pset
            f.remove(r); n['rel_props_vazia'] += 1
    f.unbatch()
    for r in list(f.by_type('IfcProductDefinitionShape')) if soltos else []:
        if not f.get_inverse(r): ue.remove_deep2(f, r); n['forma_solta'] += 1
    for r in list(f.by_type('IfcRelAssignsToGroup')):
        if r.RelatingGroup is None or not r.RelatedObjects: f.remove(r); n['rel_grupo_vazia'] += 1
    for cls in ('IfcRelAggregates', 'IfcRelContainedInSpatialStructure', 'IfcRelDefinesByType', 'IfcRelAssociatesMaterial', 'IfcRelAssociatesClassification'):
        a = 'RelatedElements' if cls == 'IfcRelContainedInSpatialStructure' else 'RelatedObjects'
        for r in list(f.by_type(cls)):
            if not getattr(r, a): f.remove(r); n[cls + '_vazia'] += 1
    for u in (list(f.by_type('IfcMaterialProfileSetUsage')) + list(f.by_type('IfcMaterialLayerSetUsage'))) if soltos else []:
        if not f.get_inverse(u): f.remove(u); n['uso_material_solto'] += 1
    for ps in list(f.by_type('IfcPropertySet')) if soltos else []:
        if not f.get_inverse(ps): tirar_pset(f, ps); n['pset_solto'] += 1
    vistos = set()
    for e in f.by_type('IfcRoot'):
        if e.GlobalId in vistos: e.GlobalId = ifcopenshell.guid.new(); n['guid_novo'] += 1
        vistos.add(e.GlobalId)
    apps = f.by_type('IfcApplication')
    if len(apps) > 1:
        oh0 = f.by_type('IfcProject')[0].OwnerHistory; a0 = oh0.OwningApplication if oh0 else apps[0]
        for oh in f.by_type('IfcOwnerHistory'):
            oh.OwningApplication = a0
            if oh.LastModifyingApplication: oh.LastModifyingApplication = a0
        for a in apps:
            if a != a0 and not f.get_inverse(a): f.remove(a); n['aplicativo_dup'] += 1
    return dict(n)
