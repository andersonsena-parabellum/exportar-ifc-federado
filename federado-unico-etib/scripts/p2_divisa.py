# -*- coding: utf-8 -*-
"""Passo 2 — divisa do lote (muro e gradil) e reservatórios, a partir da planta de situação em DXF (UTM).
Muro e gradil: cada trecho é um PAR de polilinhas (as duas faces), dado pelo handle no DXF (ver CONFIG.md); o pé de cada pedaço
(até 5 m) fica na cota do terreno as built. Reservatórios: blocos cujo nome começa com o prefixo da configuração (círculo do tanque).
Alturas não cotadas na situação são adotadas e vão para o LEIA-ME.
Uso: python p2_divisa.py escola.json   -> trabalho/urb/<SIGLA>_DIVISA.ifc"""
import os, sys, numpy as np, ezdxf, ifcopenshell, ifcopenshell.api, ifcopenshell.geom
from scipy.interpolate import LinearNDInterpolator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg):
    D = cfg['divisa']; O = ef.origem(cfg); H = D.get('alturas', {})
    H_MURO, H_GRADIL, H_MURETA = H.get('muro', 2.20), H.get('gradil', 2.00), H.get('mureta', 0.40)
    H_RES, H_BASE, PASSO = H.get('reservatorio', 2.40), H.get('base_reservatorio', 0.15), D.get('passo', 5.0)
    T = ifcopenshell.open(ef.caminho(cfg, cfg['terreno_asbuilt']))
    TV = np.vstack([v for e, v, t in ef.formas(T, T.by_type('IfcGeographicElement'))])
    ZT = LinearNDInterpolator(TV[:, :2], TV[:, 2])
    def zt(p): z = ZT(p[0], p[1]); return float(z) if np.isfinite(z) else float(np.median(TV[:, 2]))
    d = ezdxf.readfile(ef.caminho(cfg, D['dxf']))
    def pl(h, nmax=None): P = np.array([v[:2] for v in d.entitydb[h].get_points('xy')]) - O; return P[:nmax] if nmax else P
    par = lambda t: (pl(t['a'], t.get('a_max_pontos')), pl(t['b'], t.get('b_max_pontos')))
    f, body, site = ef.novo_ifc(cfg, f"{cfg['escola']} divisa e reservatórios")
    ORIG = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., 0.)))
    E_MURO, E_GRAD = ef.estilo(f, 'MURO', (0.80, 0.78, 0.74)), ef.estilo(f, 'GRADIL', (0.25, 0.30, 0.35), 0.5)
    E_RES, E_BASE = ef.estilo(f, 'RESERVATORIO', (0.15, 0.35, 0.60)), ef.estilo(f, 'CONCRETO', (0.70, 0.70, 0.70))
    def ext(prof, z0, h, est):
        sol = f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0., 0., float(z0)))), f.createIfcDirection((0., 0., 1.)), float(h))
        f.createIfcStyledItem(sol, [est], None); return sol
    def poli(pts): P = [f.createIfcCartesianPoint((float(x), float(y))) for x, y in pts]; return f.createIfcArbitraryClosedProfileDef('AREA', None, f.createIfcPolyline(P + [P[0]]))
    def elemento(cls, nome, sols, props, tipo=None):
        e = ifcopenshell.api.run('root.create_entity', f, ifc_class=cls, name=nome, predefined_type=tipo)
        e.ObjectPlacement = f.createIfcLocalPlacement(site.ObjectPlacement, ORIG)
        e.Representation = f.createIfcProductDefinitionShape(None, None, [f.createIfcShapeRepresentation(body, 'Body', 'SweptSolid', sols)])
        ef.dados(f, e, dict(disciplina='ARQ', sistema='ARQ-URB', modulo='URB', origem=D.get('origem', D['dxf']), **props)); return e
    def trechos(a, b):
        n = min(len(a), len(b)); a, b = a[:n], b[:n]; out = []
        for i in range(n - 1):
            k = max(1, int(np.ceil(np.linalg.norm(a[i + 1] - a[i]) / PASSO)))
            for j in range(k):
                t0, t1 = j / k, (j + 1) / k
                q = [a[i] + (a[i + 1] - a[i]) * t0, a[i] + (a[i + 1] - a[i]) * t1, b[i] + (b[i + 1] - b[i]) * t1, b[i] + (b[i + 1] - b[i]) * t0]
                out.append((q, min(zt(p) for p in q)))
        return out
    els = []; n = 0
    for t in D.get('muros', []):
        for q, z in trechos(*par(t)):
            n += 1; els.append(elemento('IfcWall', f'Muro da divisa M-{n:03d}', [ext(poli(q), z, H_MURO, E_MURO)], dict(altura_m=H_MURO, altura_adotada=True), 'STANDARD'))
    n = 0
    for t in D.get('gradis', []):
        for q, z in trechos(*par(t)):
            n += 1
            u = (q[1] - q[0]) / np.linalg.norm(q[1] - q[0]); v = np.array([-u[1], u[0]]) * 0.025
            e0, e1 = (q[0] + q[3]) / 2, (q[1] + q[2]) / 2; tela = [e0 + v, e1 + v, e1 - v, e0 - v]
            els.append(elemento('IfcWall', f'Mureta do gradil G-{n:03d}', [ext(poli(q), z, H_MURETA, E_MURO)], dict(altura_m=H_MURETA, altura_adotada=True), 'STANDARD'))
            els.append(elemento('IfcRailing', f'Gradil G-{n:03d}', [ext(poli(tela), z + H_MURETA, H_GRADIL, E_GRAD)], dict(altura_m=H_GRADIL, altura_adotada=True), 'FENCE'))
    R = D.get('reservatorios'); n = 0
    for e in (d.modelspace().query('INSERT') if R else []):
        if not e.dxf.name.startswith(R['bloco_prefixo']): continue
        circ = [x for x in e.virtual_entities() if x.dxftype() == 'CIRCLE' and x.dxf.radius > R.get('raio_min', 1.0)]
        if not circ: continue
        c = np.array((circ[0].dxf.center.x, circ[0].dxf.center.y)) - O; r = max(x.dxf.radius for x in circ); z = zt(c); n += 1
        base = f.createIfcRectangleProfileDef('AREA', None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint(tuple(map(float, c))), None), 2 * r + 0.4, 2 * r + 0.4)
        els.append(elemento('IfcSlab', f'Base do reservatório R-{n:02d}', [ext(base, z, H_BASE, E_BASE)], dict(espessura_m=H_BASE, altura_adotada=True), 'BASESLAB'))
        cil = f.createIfcCircleProfileDef('AREA', None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint(tuple(map(float, c))), None), float(r))
        els.append(elemento('IfcTank', f"Reservatório R-{n:02d} ({R.get('descricao', 'reservatório')})", [ext(cil, z + H_BASE, H_RES, E_RES)],
                            dict(volume_l=R.get('volume_l', 0), diametro_m=round(2 * r, 2), altura_m=H_RES, altura_adotada=True), 'STORAGE'))
    ifcopenshell.api.run('spatial.assign_container', f, products=els, relating_structure=site)
    out = ef.saida_urb(cfg, 'DIVISA'); f.write(out)
    print(out, len(els), 'elementos', {c: sum(1 for x in els if x.is_a(c)) for c in ('IfcWall', 'IfcRailing', 'IfcTank')})

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]))
