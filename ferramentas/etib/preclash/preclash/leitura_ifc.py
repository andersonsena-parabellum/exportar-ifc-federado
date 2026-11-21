# -*- coding: utf-8 -*-
"""Leitura de IFC para o preclash: o modelo vem do Revit (exportação IFC dos RVT da escola) ou de um IFC de entrega já
feito pela ferramenta, e vira elementos (eixo + diâmetro) e caixas (prismas) para o clash, o estudo de cotas e as conexões.
  - tubos/eletrodutos (IfcPipeSegment, IfcCableCarrierSegment, IfcDuctSegment): eixo pelo IfcSweptDiskSolid (polilinha),
    pela extrusão de perfil circular (exportação do Revit) ou, sem isso, pelo eixo principal da malha (PCA);
  - caixas, PVs, abrigos, quadros, válvulas, reservatórios, equipamentos (o resto, com geometria): prisma pelo menor
    retângulo que envolve a planta (ou cilindro, se a planta for redonda), do ponto mais baixo ao mais alto;
  - conexões (IfcPipeFitting, IfcCableCarrierFitting…): ficam de fora (a ferramenta gera as conexões dela, conexoes.py);
  - terreno (IfcGeographicElement, IfcSite com geometria, proxy "Sólido topográfico"): terreno_npz() grava o .npz.
Coordenadas: UTM pela IfcMapConversion do arquivo (ou pela origem passada), cota absoluta, em metros.
Disciplina: Pset PRECLASH 'disciplina' (IFC da ferramenta) ou, no IFC do Revit, pelo nome do sistema/tipo (DISC_PADRAO)."""
import re, collections
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.placement as up, ifcopenshell.util.unit as uu
from . import modelo as md

GRAVIDADE = ('ESG', 'DRE', 'AP')
SEGMENTOS = ('IfcPipeSegment', 'IfcCableCarrierSegment', 'IfcDuctSegment', 'IfcFlowSegment')
CONEXOES = ('IfcPipeFitting', 'IfcCableCarrierFitting', 'IfcDuctFitting', 'IfcFlowFitting')
TERRENO = ('IfcGeographicElement',)
IGNORAR = ('IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcSpace', 'IfcOpeningElement', 'IfcAnnotation', 'IfcGrid', 'IfcVirtualElement')
# nome do sistema / tipo / família no IFC do Revit -> disciplina do clash (a primeira que casar vale)
DISC_PADRAO = [(r'sdai|alarme|detec', 'SDAI'), (r'cftv|dados|telecom|l[oó]gica', 'CFTV'), (r'inc[eê]nd|hidrant|pci|sprink|incendio', 'HID'),
               (r'pluvial|drenag|[aá]guas? pluv|\bap\b|\bdre\b', 'DRE'), (r'esgoto|sanit|\besg\b|cinza|negra|ventila', 'ESG'),
               (r'[aá]gua fria|alimenta|re[uú]so|\baf\b|\bagf\b|abastec|recalque|hidr[aá]ul', 'AF'),
               (r'el[eé]tric|eletrodut|condu[ií]te?|ilumina|for[cç]a|\bele\b|\bel\b', 'ELE')]


def _mapa(f):
    """(E0, N0, H0, a, b, escala): UTM = (E0, N0) + escala·R·(x, y); z + H0. Sem IfcMapConversion: tudo zero (coordenadas já UTM)."""
    m = f.by_type('IfcMapConversion')
    if not m: return 0.0, 0.0, 0.0, 1.0, 0.0, 1.0
    m = m[0]; a = m.XAxisAbscissa if m.XAxisAbscissa is not None else 1.0; b = m.XAxisOrdinate if m.XAxisOrdinate is not None else 0.0
    n = np.hypot(a, b) or 1.0
    return float(m.Eastings), float(m.Northings), float(m.OrthogonalHeight or 0.0), a / n, b / n, float(m.Scale or 1.0)


class Conversor:
    def __init__(self, f, origem=None):
        self.u = uu.calculate_unit_scale(f)                       # unidade do arquivo -> metro
        if origem is not None:
            self.E0, self.N0, self.H0 = (float(v) for v in origem); self.a, self.b, self.s = 1.0, 0.0, 1.0
        else:
            self.E0, self.N0, self.H0, self.a, self.b, self.s = _mapa(f)
            self.E0 *= 1.0; self.N0 *= 1.0                         # a IfcMapConversion já está em metros (unidade do CRS)

    def utm(self, P):
        """P (n,3) em metros, coordenadas do projeto -> E, N, cota."""
        P = np.atleast_2d(np.asarray(P, float))
        x, y = P[:, 0] * self.s, P[:, 1] * self.s
        return np.column_stack([self.E0 + self.a * x - self.b * y, self.N0 + self.b * x + self.a * y, P[:, 2] + self.H0])


def _psets(p):
    d = {}
    for k, v in ue.get_psets(p).items():
        for kk, vv in v.items():
            if kk != 'id': d.setdefault(kk, vv)
    return d


def _sistemas(f):
    out = {}
    for s in f.by_type('IfcSystem') + f.by_type('IfcDistributionSystem'):
        for r in s.IsGroupedBy or []:
            for o in r.RelatedObjects: out.setdefault(o.id(), s.Name or '')
    return out


def disciplina(p, ps, sistema, regras_disc=DISC_PADRAO):
    if ps.get('disciplina'): return str(ps['disciplina'])
    txt = ' '.join(str(x) for x in (sistema, ps.get('System Name'), ps.get('Nome do sistema'), ps.get('Classificação do sistema'), ps.get('sistema'),
                                     ps.get('Tipo de sistema'), ps.get('Reference'), p.Name, getattr(p, 'ObjectType', None)) if x).lower()
    for rx, d in regras_disc:
        if re.search(rx, txt): return d
    if p.is_a('IfcCableCarrierSegment') or p.is_a('IfcCableCarrierFitting') or p.is_a('IfcElectricDistributionBoard'): return 'ELE'
    return None


def _matriz(p, u):
    M = np.array(up.get_local_placement(p.ObjectPlacement), float) if p.ObjectPlacement else np.eye(4)
    M[:3, 3] *= u
    return M


def _pos3(pl, u):
    """IfcAxis2Placement3D -> matriz 4x4 (metros)."""
    M = np.array(up.get_axis2placement(pl), float); M[:3, 3] *= u
    return M


def eixo_direto(p, u):
    """eixo pela representação: IfcSweptDiskSolid (polilinha) ou extrusão de perfil circular. None se não der."""
    if not p.Representation: return None
    for rep in p.Representation.Representations:
        for it in rep.Items:
            while it.is_a('IfcMappedItem'):
                it = it.MappingSource.MappedRepresentation.Items[0]   # (o caso comum do Revit: um item só)
            if it.is_a('IfcSweptDiskSolid') and it.Directrix.is_a('IfcPolyline'):
                # um ou vários discos varridos (a ferramenta grava um por segmento reto): junta as polilinhas em ordem
                P = []
                for it2 in rep.Items:
                    if it2.is_a('IfcSweptDiskSolid') and it2.Directrix.is_a('IfcPolyline'):
                        Q = [q.Coordinates for q in it2.Directrix.Points]
                        P += Q[1:] if P and np.allclose(P[-1], Q[0]) else Q
                P = np.array(P, float) * u
                if P.shape[1] == 2: P = np.column_stack([P, np.zeros(len(P))])
                M = _matriz(p, u)
                return (M[:3, :3] @ P.T).T + M[:3, 3], 2 * float(it.Radius) * u
            if it.is_a('IfcExtrudedAreaSolid') and (it.SweptArea.is_a('IfcCircleProfileDef') or it.SweptArea.is_a('IfcCircleHollowProfileDef')):
                M = _matriz(p, u) @ (_pos3(it.Position, u) if it.Position else np.eye(4))
                d = np.array(it.ExtrudedDirection.DirectionRatios, float); d /= np.linalg.norm(d)
                c0 = np.zeros(3) if it.SweptArea.Position is None else np.r_[np.array(it.SweptArea.Position.Location.Coordinates, float) * u, 0][:3]
                P = np.array([c0, c0 + d * float(it.Depth) * u])
                return (M[:3, :3] @ P.T).T + M[:3, 3], 2 * float(it.SweptArea.Radius) * u
    return None


def eixo_pca(V):
    """eixo de um tubo reto a partir da malha: direção principal, pontas pela projeção, diâmetro pela maior distância ao eixo."""
    c = V.mean(0); W = V - c
    _, _, vt = np.linalg.svd(W, full_matrices=False); d = vt[0]
    t = W @ d; r = np.linalg.norm(W - np.outer(t, d), axis=1)
    return np.array([c + d * t.min(), c + d * t.max()]), 2 * float(np.percentile(r, 98))


def retangulo_minimo(XY):
    """menor retângulo que envolve os pontos 2D: (cx, cy, lx, ly, rot)."""
    from matplotlib.path import Path  # noqa: F401  (só para garantir o matplotlib; o casco vem abaixo)
    P = np.unique(np.round(XY, 4), axis=0)
    if len(P) < 3:
        c = P.mean(0); return c[0], c[1], 0.05, 0.05, 0.0
    # casco convexo (monotone chain)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in P[::-1]:
        while len(hi) >= 2 and cr(hi[-2], hi[-1], q) <= 0: hi.pop()
        hi.append(q)
    H = np.array(lo[:-1] + hi[:-1])
    best = None
    for a, b in zip(H, np.roll(H, -1, 0)):
        ang = np.arctan2(b[1] - a[1], b[0] - a[0]); cs, sn = np.cos(ang), np.sin(ang)
        Q = H @ np.array([[cs, -sn], [sn, cs]])
        lx, ly = np.ptp(Q[:, 0]), np.ptp(Q[:, 1])
        if best is None or lx * ly < best[0]:
            cq = np.array([Q[:, 0].min() + lx / 2, Q[:, 1].min() + ly / 2])
            best = (lx * ly, cq @ np.array([[cs, sn], [-sn, cs]]), lx, ly, ang)
    _, c, lx, ly, ang = best
    area_casco = 0.5 * abs(np.dot(H[:, 0], np.roll(H[:, 1], -1)) - np.dot(H[:, 1], np.roll(H[:, 0], -1)))
    return float(c[0]), float(c[1]), float(max(lx, 0.02)), float(max(ly, 0.02)), float(ang), area_casco


def ler(arquivos, origem=None, mapa_disc=None, cob_min=None, so_disc=None, log=print):
    """arquivos: um ou vários IFC (ex.: um por disciplina). Devolve dict(elementos, caixas, ignorados, conexoes_existentes).
    mapa_disc: lista [(regex, disciplina)] para os nomes de sistema do Revit (padrão DISC_PADRAO).
    cob_min: {disciplina: recobrimento mínimo} das redes pressurizadas (vai para o elemento)."""
    if isinstance(arquivos, str): arquivos = [arquivos]
    st = ifcopenshell.geom.settings(); st.set('use-world-coords', True)
    elementos, caixas, ign = [], [], collections.Counter(); nconex = collections.Counter()
    vistos = set()
    for fn in arquivos:
        f = ifcopenshell.open(fn); cv = Conversor(f, origem); sis = _sistemas(f); u = cv.u
        base = fn.replace('\\', '/').rsplit('/', 1)[-1].rsplit('.', 1)[0]
        malha = {}
        it = ifcopenshell.geom.iterator(st, f, 4)
        if it.initialize():
            while True:
                sh = it.get()
                malha[sh.id] = (np.array(sh.geometry.verts).reshape(-1, 3), np.array(sh.geometry.faces, int).reshape(-1, 3))
                if not it.next(): break
        for p in f.by_type('IfcProduct'):
            if p.is_a() in IGNORAR or not p.Representation: continue
            if any(p.is_a(c) for c in CONEXOES): nconex[p.is_a()] += 1; continue
            if any(p.is_a(c) for c in TERRENO): continue
            ps = _psets(p); s_ = sis.get(p.id(), '')
            if 'Sólido topográfico' in str(ps.get('categoria_revit', '')) or 'Topography' in str(ps.get('categoria_revit', '')): continue
            disc = disciplina(p, ps, s_, mapa_disc or DISC_PADRAO)
            if disc is None: ign[p.is_a()] += 1; continue
            if so_disc and disc not in so_disc: continue
            marca = str(ps.get('marca') or ps.get('Marca') or ps.get('Mark') or p.Name or p.GlobalId)
            chave = (p.GlobalId, base)
            if chave in vistos: continue
            vistos.add(chave)
            if any(p.is_a(c) for c in SEGMENTOS):
                r = eixo_direto(p, u)
                if r is None:
                    if p.id() not in malha: ign['sem geometria'] += 1; continue
                    r = eixo_pca(malha[p.id()][0])
                P, de = r
                P = cv.utm(P)
                if de <= 0 or np.linalg.norm(P[-1] - P[0]) < 1e-3: ign['tubo degenerado'] += 1; continue
                tipo = 'gravidade' if disc in GRAVIDADE else 'pressao'
                rede = str(ps.get('rede') or ps.get('sistema') or s_ or disc)
                elementos.append(md.elemento(f'{disc}:{marca}#{p.id()}', disc, rede, marca, tipo, de, P,
                                             cob_min=(cob_min or {}).get(disc), ifc=p.is_a(), guid=p.GlobalId, arquivo=base,
                                             cota='modelo (IFC)', material=str(ps.get('tipo') or getattr(p, 'ObjectType', '') or '')))
            else:
                if p.id() not in malha: ign['sem geometria'] += 1; continue
                V = cv.utm(malha[p.id()][0])
                cx_, cy_, lx, ly, rot, ac = retangulo_minimo(V[:, :2])
                zb, zt = float(V[:, 2].min()), float(V[:, 2].max())
                redondo = abs(lx - ly) < 0.08 * max(lx, ly) and ac < 0.85 * lx * ly
                info = dict(nome=marca, tipo=str(ps.get('familia') or getattr(p, 'ObjectType', '') or p.Name or ''), classe_ifc=p.is_a() if p.is_a() != 'IfcDistributionChamberElement' else None,
                            cota='modelo (IFC)', guid=p.GlobalId, arquivo=base, equipamento='sim' if p.is_a() != 'IfcDistributionChamberElement' else None)
                info = {k: v for k, v in info.items() if v is not None}
                rede = str(ps.get('rede') or ps.get('sistema') or s_ or disc)
                if redondo:
                    caixas.append(md.caixa(f'{disc}:{marca}#{p.id()}', disc, rede, 'c', cx_, cy_, (lx + ly) / 4, zb, zt, **info))
                else:
                    caixas.append(md.caixa_retangular(f'{disc}:{marca}#{p.id()}', disc, rede, cx_, cy_, lx, ly, rot, zb, zt, **info))
        log(f'  {base}: {sum(1 for e in elementos if e["info"]["arquivo"] == base)} trechos, {sum(1 for c in caixas if c["info"]["arquivo"] == base)} caixas/equipamentos')
    if ign: log(f'  ignorados: {dict(ign)}')
    return {'elementos': elementos, 'caixas': caixas, 'ignorados': dict(ign), 'conexoes_existentes': dict(nconex)}


def terreno_npz(arquivos, saida, origem=None, so_topo=True, fonte=''):
    """grava o .npz do terreno (pts + tri) com as faces de cima dos sólidos topográficos/pisos do IFC."""
    if isinstance(arquivos, str): arquivos = [arquivos]
    st = ifcopenshell.geom.settings(); st.set('use-world-coords', True)
    VV, FF, n = [], [], 0
    for fn in arquivos:
        f = ifcopenshell.open(fn); cv = Conversor(f, origem)
        alvo = {p.id() for p in f.by_type('IfcProduct') if any(p.is_a(c) for c in TERRENO)
                or 'Sólido topográfico' in str(_psets(p).get('categoria_revit', '')) or (p.is_a('IfcSite') and p.Representation)}
        it = ifcopenshell.geom.iterator(st, f, 4)
        if not it.initialize(): continue
        while True:
            sh = it.get()
            if sh.id in alvo:
                V = cv.utm(np.array(sh.geometry.verts).reshape(-1, 3)); F = np.array(sh.geometry.faces, int).reshape(-1, 3)
                if so_topo:
                    nz = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])[:, 2]
                    F = F[nz > 1e-9]
                VV.append(V); FF.append(F + n); n += len(V)
            if not it.next(): break
    V = np.vstack(VV); F = np.vstack(FF)
    Vk, inv = np.unique(V.round(3), axis=0, return_inverse=True)
    F = inv.reshape(-1)[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    # mesmo (E, N) com duas cotas (sólidos sobrepostos): fica a de cima
    np.savez_compressed(saida, pts=Vk, tri=F, fonte=fonte or 'IFC: ' + ', '.join(a.replace('\\', '/').rsplit('/', 1)[-1] for a in arquivos))
    return len(Vk), len(F)
