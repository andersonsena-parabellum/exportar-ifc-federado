# -*- coding: utf-8 -*-
"""Alagoinhas — conjunto de entrega IFC R03 (implantação + bloco BA2), a partir das rodadas do preclash:
  implantação: ETIB-ALAGOINHAS/RELATORIOS/PRECLASH_IMP_R03 (adaptador escolas/alagoinhas.py, sigla ALI)
  bloco BA2:   ETIB-ALAGOINHAS/RELATORIOS/PRECLASH_BA2_R03 (adaptador escolas/alagoinhas_ba2.py, sigla ALH)
Saída: ETIB-ALAGOINHAS/RELATORIOS/ENTREGA_IFC_R03/
  ALH_IMP_HIDRO / _ELE / _PCIP, ALH_EST_asbuilt (referência), ALH_TERRENO e ALH_FEDERADO (_R03.ifc). Só rede externa (21/10).
- A estrutura as built do BA2 sai só no IFC do BA2 (a da implantação traz os outros blocos); no clash da implantação ela entra.
- Terreno: o do IMP as built levado às cotas das caixas de esgoto e drenagem das pranchas (o mesmo das redes).
- Federado: a soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (as pendências declaradas).
Uso: python -X utf8 alh_entrega.py"""
import os, sys, csv, glob, shutil, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import ifcopenshell, ifcopenshell.guid
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno

BASE = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS'
IMP = os.path.join(BASE, 'PRECLASH_IMP_R03'); BA2 = os.path.join(BASE, 'PRECLASH_BA2_R03')
OUT = os.environ.get('ALH_ENTREGA') or os.path.join(BASE, 'ENTREGA_IFC_R03')
ORIGEM = (561500.0, 8658000.0, 0.0); EPSG = 31984
REV = 'R03'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-ALAGOINHAS')
TER = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\alagoinhas_terreno.npz'
CAIXA = (561470.0, 8657865.0, 561610.0, 8658070.0)


def copiar(fonte, destino, filtro=None):
    """copia os produtos (não espaciais) de um IFC para outro objeto Ifc (export_ifc), com estilos, Psets, material e sistemas."""
    src = ifcopenshell.open(fonte); f = destino.f
    novos = []
    for p in src.by_type('IfcProduct'):
        if p.is_a('IfcSpatialStructureElement') or p.Representation is None: continue
        if filtro and not filtro(p): continue
        q = f.add(p); q.ObjectPlacement = f.createIfcLocalPlacement(destino.site_pl, destino.wcs); novos.append((p, q))
    mapa = {p.id(): q for p, q in novos}
    itens = {it.id() for p, _ in novos for r in p.Representation.Representations for it in r.Items}
    for si in src.by_type('IfcStyledItem'):
        if si.Item is not None and si.Item.id() in itens: f.add(si)
    for rel in src.by_type('IfcRelDefinesByProperties'):
        objs = [mapa[o.id()] for o in rel.RelatedObjects if o.id() in mapa]
        if objs: f.createIfcRelDefinesByProperties(ifcopenshell.guid.new(), None, rel.Name, None, objs, f.add(rel.RelatingPropertyDefinition))
    for rel in src.by_type('IfcRelAssociatesMaterial'):
        objs = [mapa[o.id()] for o in rel.RelatedObjects if o.id() in mapa]
        if objs: f.createIfcRelAssociatesMaterial(ifcopenshell.guid.new(), None, None, None, objs, f.add(rel.RelatingMaterial))
    for rel in src.by_type('IfcRelAssignsToGroup'):
        objs = [mapa[o.id()] for o in rel.RelatedObjects if o.id() in mapa]
        if objs:
            g = rel.RelatingGroup
            s = (f.createIfcDistributionSystem(ifcopenshell.guid.new(), None, g.Name, None, None, None, g.PredefinedType) if g.is_a('IfcDistributionSystem')
                 else f.createIfcSystem(ifcopenshell.guid.new(), None, g.Name, None, None))
            f.createIfcRelAssignsToGroup(ifcopenshell.guid.new(), None, None, None, objs, None, s)
    destino.contidos += [q for _, q in novos]
    return len(novos)


def nao_ba2(p):
    import ifcopenshell.util.element as ue
    ps = {k: v for d in ue.get_psets(p).values() for k, v in d.items()}
    return str(ps.get('sistema', '')) != 'EST-BA2'


def estrutura_referencia(dst):
    """estrutura as built dos prédios só como referência (regra de 21/10: o que é interno não entra no clash)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import alh_modelo as AM
    T = Terreno(TER); C = AM.estrutura(T, log=lambda *a: None)
    f = Ifc('ETIB Alagoinhas — estrutura as built dos prédios (referência)', ORIGEM, EPSG)
    vistos = set()
    for c in C:
        if c['id'] in vistos: continue
        vistos.add(c['id']); f.caixa(c, 'Estrutura as built (referência)')
    f.salvar(dst); return len(vistos)


def terreno_com_caixas(T, arqs):
    """grade de 0,50 m (a de 2 m da ferramenta afastava a tampa das caixas do terreno até 0,2 m) com o centro e os cantos de
    cada caixa de chão como vértices: na grade pura o terreno entre dois nós ainda ficava até 9 cm fora da tampa (Revisão de
    21/10, CI-26 e PV19). Centro na cota da tampa, cantos no terreno do modelo."""
    import matplotlib.tri as mtri
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
    import ifc_conf as IC
    V, F = T.grade(CAIXA, 0.5)
    R = IC.ler(arqs, log=lambda *a: None)
    extra = []
    for c in R['cx']:
        z0 = T.z(np.array([[c['E'], c['N']]]))[0]
        if not np.isfinite(z0) or abs(c['zt'] - z0) > 0.15: continue          # reservatório, bombas, quadros: não são de chão
        extra.append((c['E'], c['N'], c['zt']))
        r = 0.6 * max(c.get('meia', 0.3), 0.3)
        for dx, dy in ((r, r), (-r, r), (-r, -r), (r, -r)):
            q = np.array([[c['E'] + dx, c['N'] + dy]]); zq = T.z(q)[0]
            if np.isfinite(zq): extra.append((q[0, 0], q[0, 1], c['zt'] + (zq - z0) * 0.5))
    if not extra: return V, F
    X = np.array(extra)
    _, k = np.unique(np.round(X[:, :2], 2), axis=0, return_index=True); X = X[np.sort(k)]
    longe = np.ones(len(V), bool)
    for x in X:
        perto = (np.abs(V[:, 0] - x[0]) < 0.20) & (np.abs(V[:, 1] - x[1]) < 0.20)
        longe &= ~(perto & (np.hypot(V[:, 0] - x[0], V[:, 1] - x[1]) < 0.20))
    V2 = np.vstack([V[longe], X])
    tri = mtri.Triangulation(V2[:, 0], V2[:, 1]).triangles
    A, B, Cc = V2[tri[:, 0], :2], V2[tri[:, 1], :2], V2[tri[:, 2], :2]
    lado = np.max([np.hypot(*(A - B).T), np.hypot(*(B - Cc).T), np.hypot(*(Cc - A).T)], axis=0)
    tri = tri[lado < 1.2]                                                    # só dentro da grade (sem tampar os vazios do terreno)
    print(f'terreno: grade 0,50 m + {len(X)} pontos de caixa')
    return V2, tri


BA2_GRUPOS = {'HIDRO': ('AF', 'AP', 'CV', 'ESG'), 'ELE': ('ELE',), 'CLI': ('CLI',), 'PCIP': ('HID', 'SDAI')}


def ba2_modelagem():
    """BA2 (Anderson, 21/10/2026): o IFC das instalações internas vai na entrega só como modelagem — sem compatibilização, sem as
    soluções do preclash e sem marcador de conflito: os elementos do modelo (ALH_preclash_projeto.ifc), sem a estrutura.
    Fica numa pasta própria, fora do federado das redes externas e da revisão de qualidade da implantação."""
    import ifcopenshell.util.element as ue
    fonte = os.path.join(BA2, 'ALH_preclash_projeto.ifc'); dst_dir = os.path.join(OUT, 'BA2_MODELAGEM'); os.makedirs(dst_dir, exist_ok=True)
    for x in glob.glob(os.path.join(dst_dir, '*.ifc')): os.remove(x)
    disc = lambda p: str({k: v for d in ue.get_psets(p).values() for k, v in d.items()}.get('disciplina', ''))
    for g, ds in BA2_GRUPOS.items():
        dst = os.path.join(dst_dir, f'ALH_BA2_{g}_{REV}.ifc')
        f = Ifc(f'ETIB Alagoinhas — bloco BA2 — {g} (modelagem das instalações internas)', ORIGEM, EPSG)
        n = copiar(fonte, f, lambda p, ds=ds: disc(p) in ds); f.salvar(dst); print(os.path.basename(dst), n, 'elementos (BA2, só modelagem)')


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    # regra de 21/10/2026 (Anderson): só rede externa. O BA2 (instalações internas do bloco) só entra com ALH_COM_BA2=1.
    pares = [('IMP', IMP, 'ALI', ('HIDRO', 'ELE', 'PCIP'))]
    if os.environ.get('ALH_COM_BA2') == '1': pares.append(('BA2', BA2, 'ALH', ('HIDRO', 'ELE', 'CLI', 'PCIP')))
    for setor, pasta, sig, grupos in pares:
        for g in grupos:
            fonte = os.path.join(pasta, 'IFC_POR_DISCIPLINA_AD', f'{sig}_{g}_compatibilizado.ifc')
            dst = os.path.join(OUT, f'ALH_{setor}_{g}_{REV}.ifc')
            f = Ifc(f'ETIB Alagoinhas — {"implantação" if setor == "IMP" else "bloco BA2"} — {g}', ORIGEM, EPSG); n = copiar(fonte, f); f.salvar(dst)
            print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    # estrutura dos prédios: fora da entrega (21/10, Anderson: o que é dos prédios, inclusive a fundação, não entra neste contrato);
    # ALH_COM_EST=1 gera o IFC de referência
    if os.environ.get('ALH_COM_EST') == '1':
        dst = os.path.join(OUT, f'ALH_EST_asbuilt_{REV}.ifc'); print(os.path.basename(dst), estrutura_referencia(dst), 'peças (referência)'); arqs.append(dst)
    T = Terreno(TER)
    V, F = terreno_com_caixas(T, arqs)
    f = Ifc('ETIB Alagoinhas — terreno', ORIGEM, EPSG); el = f.terreno(V, F, 'Terreno (IMP as built)'); el.Description = 'terreno as built nas cotas das pranchas'
    f.salvar(os.path.join(OUT, f'ALH_TERRENO_{REV}.ifc'))
    fed = Ifc('ETIB Alagoinhas — FEDERADO (redes externas da implantação)', ORIGEM, EPSG)
    n = sum(copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno (IMP as built)'); el.Description = 'terreno as built nas cotas das pranchas'
    k = 0
    for setor, pasta, sig, _ in pares[:1]:
        for r in csv.DictReader(open(os.path.join(pasta, f'{sig}_preclash_AD_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
            if r['gravidade'] != 'CRÍTICA': continue
            k += 1; f_ = lambda v: float(v.replace(',', '.'))
            c = {'E': f_(r['E']), 'N': f_(r['N']), 'z': f_(r['z']), 'gravidade': 'CRÍTICA'}
            fed.conflito(c, f'P{k:03d}', {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': f_(r['folga_m']),
                                         'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'ALH_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    ba2_modelagem()
    rv = os.path.join(REVQ, '_ifc_IMP'); os.makedirs(rv, exist_ok=True)
    for x in glob.glob(os.path.join(rv, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, rv)


if __name__ == '__main__':
    main()
