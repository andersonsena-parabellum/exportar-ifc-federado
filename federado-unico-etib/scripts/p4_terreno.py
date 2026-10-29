# -*- coding: utf-8 -*-
"""Passo 4 — terreno recortado no lote e pisos externos.
Terreno: a malha as built (a mesma das redes) é cortada no contorno do lote: "Terreno — lote" (verde, opaco) e
"Terreno — entorno" (transparente). Corte por triângulo, cota pelo plano do próprio triângulo: o terreno das redes não muda.
Pisos externos: lote − gramado − pegada construída (módulos e estrutura) − áreas excluídas − platôs e bases (passos 2 e 3);
laje de 10 cm acompanhando o terreno (topo 3 cm acima).
Uso: python p4_terreno.py escola.json   (depois de p1, p2 e p3)  -> trabalho/urb/<SIGLA>_TERRENO.ifc e <SIGLA>_PISOS.ifc"""
import os, sys, numpy as np, ezdxf, shapely, ifcopenshell, ifcopenshell.api
from ezdxf import path as zp
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg):
    C = cfg['terreno']; O = ef.origem(cfg); TOPO, ESP = C.get('piso_topo', 0.03), C.get('piso_espessura', 0.10)
    T = ifcopenshell.open(ef.caminho(cfg, cfg['terreno_asbuilt']))
    TV, TF, k = [], [], 0
    for e, v, t in ef.formas(T, T.by_type('IfcGeographicElement')): TV.append(v); TF.append(t + k); k += len(v)
    TV, TF = np.vstack(TV), np.vstack(TF)
    # ---------- hachuras da pavimentação ----------
    d = ezdxf.readfile(ef.caminho(cfg, C['dxf'])); jan = C.get('janela_local')   # [xmin, ymin, xmax, ymax]: ignora cópias da planta fora da implantação
    def contornos(e):
        out = []
        for sp in zp.make_path(e).sub_paths():
            P = np.array([(v.x, v.y) for v in sp.flattening(0.03)]) - O
            if len(P) > 3 and (not jan or (P[:, 0].min() > jan[0] and P[:, 1].min() > jan[1] and P[:, 0].max() < jan[2] and P[:, 1].max() < jan[3])):
                out.append(Polygon(P).buffer(0))
        return [p for p in out if p.area > 0.01]
    def par_impar(ps):
        r = Polygon()
        for p in ps: r = r.symmetric_difference(p)
        return r.buffer(0)
    H = [(e.dxf.layer, e.dxf.pattern_name, contornos(e)) for e in d.modelspace().query('HATCH')]
    def maior(camada, padrao=None):
        return [ps for l, pt, ps in H if l == camada and (padrao is None or pt == padrao) and ps]
    LOTE = Polygon(max((p for ps in maior(C['lote']['camada']) for p in ps), key=lambda p: p.area).exterior)
    g = C.get('gramado'); GRAMA = par_impar(max(maior(g['camada'], g.get('padrao')), key=lambda ps: max(p.area for p in ps))) if g else Polygon()
    EXC = []
    for x in C.get('excluir', []):
        if 'circulo' in x: EXC.append(Point(*x['circulo'][:2]).buffer(x['circulo'][2]))
        elif 'poligono' in x: EXC.append(Polygon(x['poligono']))
        elif 'hachura_maior' in x: EXC.append(Polygon(max((p for ps in maior(x['hachura_maior']) for p in ps), key=lambda p: p.area).exterior).buffer(x.get('folga', 0.)))
    construido = [ef.saida_modulo(cfg, m) for m in cfg['modulos']] + [ef.caminho(cfg, e['arquivo']) for e in cfg.get('estrutura', [])]
    PEG = ef.pegada_construida(construido, cfg['cota']['pegada_acima_de'])
    bases = []
    for fn in (ef.saida_urb(cfg, 'URB_RVT'), ef.saida_urb(cfg, 'DIVISA')):
        if not os.path.exists(fn): continue
        u = ifcopenshell.open(fn)
        for e, v, t in ef.formas(u, u.by_type('IfcSlab')):
            bases.append(unary_union([Polygon(v[q, :2]) for q in t if Polygon(v[q, :2]).area > 1e-6]))
    PISO = LOTE.difference(GRAMA.buffer(0.02)).difference(PEG.buffer(0.05)).difference(unary_union(EXC + [Polygon()])).difference(unary_union(bases + [Polygon()]).buffer(0.05))
    PISO = PISO.buffer(-0.05, join_style=2).buffer(0.05, join_style=2)
    PISOS = sorted([p for p in getattr(PISO, 'geoms', [PISO]) if p.geom_type == 'Polygon' and p.area > 2.0], key=lambda p: -p.area)
    print('lote', round(LOTE.area, 1), 'gramado', round(GRAMA.intersection(LOTE).area, 1), 'construído', round(PEG.area, 1), 'pisos', len(PISOS), round(sum(p.area for p in PISOS), 1), 'm²')
    # ---------- corte da malha ----------
    def cortar(reg):
        pr = prep(reg); out = []
        for f3 in TF:
            P = TV[f3]; t = Polygon(P[:, :2])
            if t.area < 1e-8 or not pr.intersects(t): continue
            if pr.contains(t): out.append(P); continue
            n = np.cross(P[1] - P[0], P[2] - P[0])
            if abs(n[2]) < 1e-12: continue
            z = lambda x, y: P[0, 2] - (n[0] * (x - P[0, 0]) + n[1] * (y - P[0, 1])) / n[2]
            for q in getattr(t.intersection(reg), 'geoms', [t.intersection(reg)]):
                if q.geom_type != 'Polygon' or q.area < 1e-6: continue
                for tr in shapely.constrained_delaunay_triangles(q).geoms:
                    c = np.array(tr.exterior.coords)[:3]; out.append(np.c_[c, [z(x, y) for x, y in c]])
        return out
    def malha(f, tris, est, fechada=False):
        pts, idx, kk = [], [], {}
        for t in tris:
            ii = []
            for p in t:
                c = tuple(np.round(p, 4))
                if c not in kk: kk[c] = len(pts) + 1; pts.append(tuple(float(x) for x in c))
                ii.append(kk[c])
            if len(set(ii)) == 3: idx.append(ii)
        fs = f.createIfcTriangulatedFaceSet(f.createIfcCartesianPointList3D(pts), None, fechada, idx, None)
        f.createIfcStyledItem(fs, [est], None); return fs
    def laje(tris):
        top = [np.c_[t[:, :2], t[:, 2] + TOPO] for t in tris]
        for t in top:
            if np.cross(t[1] - t[0], t[2] - t[0])[2] < 0: t[[1, 2]] = t[[2, 1]]
        bot = [np.c_[t[:, :2], t[:, 2] - ESP][[0, 2, 1]] for t in top]
        ar = {}
        for t in top:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ka, kb = tuple(np.round(t[a], 4)), tuple(np.round(t[b], 4)); ar[(ka, kb)] = ar.get((ka, kb), 0) + 1
        lado = []
        for (ka, kb) in ar:
            if (kb, ka) in ar: continue
            A, B = np.array(ka), np.array(kb); A2, B2 = A - [0, 0, ESP], B - [0, 0, ESP]
            lado += [np.array([B, A, A2]), np.array([B, A2, B2])]
        return top + bot + lado
    # ---------- terreno ----------
    ft, bt, st = ef.novo_ifc(cfg, f"{cfg['escola']} terreno")
    E_LOTE, E_ENT = ef.estilo(ft, 'TERRENO_LOTE', (0.47, 0.62, 0.33)), ef.estilo(ft, 'TERRENO_ENTORNO', (0.62, 0.55, 0.42), 0.5)
    ORIG = ft.createIfcAxis2Placement3D(ft.createIfcCartesianPoint((0., 0., 0.)))
    CX = Polygon([(TV[:, 0].min() - 1, TV[:, 1].min() - 1), (TV[:, 0].max() + 1, TV[:, 1].min() - 1), (TV[:, 0].max() + 1, TV[:, 1].max() + 1), (TV[:, 0].min() - 1, TV[:, 1].max() + 1)])
    els = []
    for nome, desc, reg, est in (('Terreno — lote', 'Terreno dentro da divisa do lote', LOTE, E_LOTE), ('Terreno — entorno', 'Terreno fora da divisa do lote', CX.difference(LOTE), E_ENT)):
        tr = cortar(reg); e = ifcopenshell.api.run('root.create_entity', ft, ifc_class='IfcGeographicElement', name=nome, predefined_type='TERRAIN')
        e.Description = desc; e.ObjectPlacement = ft.createIfcLocalPlacement(st.ObjectPlacement, ORIG)
        e.Representation = ft.createIfcProductDefinitionShape(None, None, [ft.createIfcShapeRepresentation(bt, 'Body', 'Tessellation', [malha(ft, tr, est)])])
        ef.dados(ft, e, dict(disciplina='TER', sistema='TERRENO', modulo='SITE', origem=C.get('origem', 'Terreno as built cortado no lote')))
        els.append(e); print(nome, len(tr), 'triângulos')
    ifcopenshell.api.run('spatial.assign_container', ft, products=els, relating_structure=st)
    ft.write(ef.saida_urb(cfg, 'TERRENO'))
    # ---------- pisos ----------
    fp, bp, sp = ef.novo_ifc(cfg, f"{cfg['escola']} pisos externos")
    E_PISO = ef.estilo(fp, 'PISO_EXTERNO', (0.74, 0.72, 0.68)); ORIG = fp.createIfcAxis2Placement3D(fp.createIfcCartesianPoint((0., 0., 0.)))
    els = []
    for i, p in enumerate(PISOS, 1):
        tr = laje(cortar(p))
        e = ifcopenshell.api.run('root.create_entity', fp, ifc_class='IfcSlab', name=f'Piso externo P-{i:02d}', predefined_type='FLOOR')
        e.ObjectType = 'Passeio / piso externo'; e.ObjectPlacement = fp.createIfcLocalPlacement(sp.ObjectPlacement, ORIG)
        e.Representation = fp.createIfcProductDefinitionShape(None, None, [fp.createIfcShapeRepresentation(bp, 'Body', 'Tessellation', [malha(fp, tr, E_PISO, True)])])
        ef.dados(fp, e, dict(disciplina='ARQ', sistema='ARQ-URB', modulo='URB', area_m2=round(p.area, 1), espessura_m=ESP, espessura_adotada=True,
                             origem=C.get('origem_pisos', 'Planta de pavimentação (lote menos gramado e edificações), sobre o terreno as built')))
        els.append(e)
    if els: ifcopenshell.api.run('spatial.assign_container', fp, products=els, relating_structure=sp)
    fp.write(ef.saida_urb(cfg, 'PISOS')); print('pisos gravados', len(els))

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]))
