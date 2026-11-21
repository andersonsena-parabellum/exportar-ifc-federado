# -*- coding: utf-8 -*-
"""ETIB Catu — pós-processamento dos IFC de entrega do preclash (19/10/2026): troca a classe IFC dos equipamentos e da
estrutura (o preclash exporta toda caixa como IfcDistributionChamberElement) e grava o IMP as built como terreno à parte.
  EQ:HID:H-xx -> IfcFireSuppressionTerminal FIREHYDRANT | EQ:HID:ABR- -> IfcFireSuppressionTerminal HOSEREEL
  EQ:HID:RECALQUE -> IfcFireSuppressionTerminal BREECHINGINLET | EQ:HID:CB -> IfcBuildingElementProxy (casa de bombas)
  EQ:ELE:QGBT / QD -> IfcElectricDistributionBoard | EQ:ELE:EL2-POSTE -> IfcLightFixture | EQ:ELE:BASE- -> IfcFooting PAD_FOOTING
  EQ:SDAI:CENTRAL -> IfcUnitaryControlElement ALARMPANEL | EQ:AF:RG- -> IfcValve ISOLATING | EQ:DRE:CAN- -> IfcPipeSegment GUTTER
  EST:<bloco>:<id> -> IfcFooting / IfcColumn / IfcBeam pela categoria do Revit
Uso: .venv/Scripts/python.exe -X utf8 georef/catu_ifc_pos.py <pasta PRECLASH> <cenário>"""
import os, sys, glob, collections
import numpy as np
import ifcopenshell, ifcopenshell.api, ifcopenshell.guid


def classe(nome, desc):
    n = nome or ''
    if n.startswith('EQ:HID:ABR-'): return 'IfcFireSuppressionTerminal', 'HOSEREEL'
    if n.startswith('EQ:HID:RECALQUE'): return 'IfcFireSuppressionTerminal', 'BREECHINGINLET'
    if n.startswith('EQ:HID:CB'): return 'IfcBuildingElementProxy', 'USERDEFINED'
    if n.startswith('EQ:HID:'): return 'IfcFireSuppressionTerminal', 'FIREHYDRANT'
    if n.startswith('EQ:ELE:BASE-'): return 'IfcFooting', 'PAD_FOOTING'
    if n.startswith('EQ:ELE:EL2-POSTE'): return 'IfcLightFixture', 'POINTSOURCE'
    if n.startswith('EQ:ELE:'): return 'IfcElectricDistributionBoard', 'SWITCHBOARD' if 'QGBT' in n else 'DISTRIBUTIONBOARD'
    if n.startswith('EQ:SDAI:CENTRAL'): return 'IfcUnitaryControlElement', 'ALARMPANEL'
    if n.startswith('EQ:AF:'): return 'IfcValve', 'ISOLATING'
    if n.startswith('EQ:DRE:CAN-'): return 'IfcPipeSegment', 'GUTTER'
    if n.startswith('EST:'):
        cod = n.split(':')[2] if n.count(':') >= 3 else ''
        return {'FUN': ('IfcFooting', 'PAD_FOOTING'), 'PIL': ('IfcColumn', 'COLUMN'), 'VIG': ('IfcBeam', 'BEAM'), 'PAR': ('IfcWall', 'SOLIDWALL'),
                'LAJ': ('IfcSlab', 'BASESLAB')}.get(cod, ('IfcBuildingElementProxy', 'NOTDEFINED'))
    return None, None


def processar(fn):
    f = ifcopenshell.open(fn); n = collections.Counter()
    for el in list(f.by_type('IfcProduct')):
        c, pred = classe(el.Name, el.Description)
        if not c: continue
        if el.is_a(c):
            if hasattr(el, 'PredefinedType') and pred: el.PredefinedType = pred
            continue
        novo = ifcopenshell.api.run('root.reassign_class', f, product=el, ifc_class=c, predefined_type=pred)
        n[c] += 1
    f.write(fn)
    return n


def terreno_imp(pasta, cen, passo=2):
    """IMP as built (work/CATU/imp/imp_raster_1m.npz) como IFC de terreno à parte, para comparar com o terreno do projeto."""
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
    from preclash.export_ifc import Ifc
    D = np.load(r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp\imp_raster_1m.npz')
    X, Y, Z = D['X'][::passo, ::passo], D['Y'][::passo, ::passo], D['Z'][::passo, ::passo]
    idx = -np.ones(Z.shape, int); ok = ~np.isnan(Z); idx[ok] = np.arange(ok.sum())
    V = np.column_stack([X[ok], Y[ok], Z[ok]]); F = []
    for j in range(Z.shape[0] - 1):
        for i in range(Z.shape[1] - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if a >= 0 and b >= 0 and c >= 0: F.append((a, b, c))
            if a >= 0 and c >= 0 and d >= 0: F.append((a, c, d))
    f = Ifc('ETIB Catu — terreno do IMP as built (comparação; platôs 1,6 a 5,1 m acima do projeto)', (567700.0, 8634650.0, 0.0), 31984)
    f.terreno(V, np.array(F, int), nome='Terreno IMP as built')
    fn = os.path.join(pasta, f'IFC_POR_DISCIPLINA_{cen}', 'CAT_TERRENO_IMP_asbuilt.ifc'); f.salvar(fn)
    print(os.path.basename(fn), f'{os.path.getsize(fn) / 1e6:.2f} MB')


def main(pasta, cen):
    alvos = [os.path.join(pasta, f'CAT_preclash_{s}.ifc') for s in ('projeto', f'solucao_{cen}')] + glob.glob(os.path.join(pasta, f'IFC_POR_DISCIPLINA_{cen}', '*.ifc'))
    for fn in alvos:
        if os.path.exists(fn): print(os.path.basename(fn), dict(processar(fn)), flush=True)
    terreno_imp(pasta, cen)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
