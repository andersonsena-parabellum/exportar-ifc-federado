# -*- coding: utf-8 -*-
"""Jandaíra — IFC4 de entrega (método da pré-compatibilização: IFC por disciplina + federado), feito a partir da geometria exportada
dos modelos JAN-* revisados (RELATORIOS/compat_R01/geo_exec), sem abrir o Revit.
 - coordenadas = UTM SIRGAS 2000 / 24S − origem dos modelos JAN, cota absoluta (IfcMapConversion, EPSG 31984), como o preclash;
 - tubos e eletrodutos = IfcSweptDiskSolid no eixo; caixas, conexões, quadros, canaletas e estrutura = malha triangulada da exportação;
 - terreno = sólidos topográficos e pisos do IMP as built;
 - federado = tudo + estrutura de referência + marcadores das colisões que continuam (compat_R01/itens_pontos_R01.csv).
Uso: python -X utf8 jan_ifc.py [pasta_saida]"""
import sys, os, csv, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\preclash")
import jan_dados as JD
from preclash.export_ifc import Ifc
import ifcopenshell, ifcopenshell.guid
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"; G = os.path.join(C, 'geo_exec')
SAIDA = sys.argv[1] if len(sys.argv) > 1 else r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R01_2026-10-19"
os.makedirs(SAIDA, exist_ok=True)
ESCOLA = 'ETIB Jandaíra'; EPSG = 31984
R, o = JD.tf_compart(JD.meta('ELE', G))
U = lambda P: (np.atleast_2d(np.asarray(P, float)) - o) @ R          # interno (m) -> E, N, cota
ORIGEM = tuple(float(v) for v in U([0, 0, -147.0])[0])               # origem dos modelos JAN em planta, cota 0
DISC_IFC = {'AF': 'AF', 'ESG': 'ESG', 'DRE': 'DRE', 'ELE': 'ELE', 'INC': 'HID', 'SDAI': 'SDAI'}
NOMES = {'AF': 'Água fria (alimentação e reúso)', 'ESG': 'Esgoto', 'DRE': 'Drenagem pluvial', 'ELE': 'Elétrica enterrada', 'HID': 'Hidrantes (PCI)', 'SDAI': 'Alarme SDAI (PCI)'}
ENTREGA = {'HIDRO': ('AF', 'ESG', 'DRE'), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}


class IfcJan(Ifc):
    def malha(self, tri, nome, desc, classe, cor, pset, grupo, pred=None, transp=0.0):
        V = U(tri.reshape(-1, 3)); Vk, inv = np.unique(V.round(4), axis=0, return_inverse=True)
        F = inv.reshape(-1, 3); F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        if len(F) == 0: return None
        pl = self.f.createIfcCartesianPointList3D([tuple(float(round(v, 4)) for v in (q - self.o)) for q in Vk])
        item = self.f.createIfcTriangulatedFaceSet(pl, None, None, [tuple(int(i) + 1 for i in t) for t in F], None)
        return self._produto(classe, nome, desc, item, 'Tessellation', cor, pset, grupo, pred, transp)


SEG, MESH = JD.carregar(g=G, est='daniel'); JD.agrupar_caixas(SEG, MESH)
for s in SEG: s['dI'] = DISC_IFC.get(s['disc'])
for m in MESH: m['dI'] = DISC_IFC.get(m['disc'])


def pset_seg(s):
    d = {'disciplina': s['dI'], 'marca': s['trecho'], 'categoria_revit': s['cat'], 'tipo': s['tipo'], 'sistema': s['sis'], 'DE_mm': s['de'] * 1000,
         'cota_eixo_a': float(U(s['a'])[0][2]), 'cota_eixo_b': float(U(s['b'])[0][2]), 'comentarios': s.get('desc') or None,
         'alterado_R01': 'sim' if 'R01 18/10' in (s.get('desc') or '') else None, 'modelo_origem': 'JAN-' + {'AF': 'AGF', 'HID': 'PCI', 'SDAI': 'PCI'}.get(s['dI'], s['dI'])}
    return d


def classe_mesh(m):
    c = m['cat']
    if m['dI'] == 'ELE' and c.startswith('Equip'): return ('IfcElectricDistributionBoard', 'DISTRIBUTIONBOARD') if 'QD' in str(m.get('grupo', '')) else ('IfcDistributionChamberElement', 'INSPECTIONCHAMBER')
    if c.startswith('Conex') and m['dI'] in ('ELE', 'SDAI'): return ('IfcCableCarrierFitting', None)
    if c.startswith('Conex'): return ('IfcPipeFitting', None)
    if c.startswith('Acess'): return ('IfcValve', None) if m['dI'] in ('AF', 'HID') else ('IfcPipeFitting', None)
    if c in ('Modelos genéricos', 'Peças hidrossanitárias'): return ('IfcDistributionChamberElement', 'INSPECTIONCHAMBER')
    return ('IfcBuildingElementProxy', None)


def redes(f, discs):
    n = collections.Counter()
    for s in SEG:
        if s['dI'] not in discs: continue
        e = dict(id=str(s['id']), trecho=s['trecho'], disc=s['dI'], de=max(s['de'], 0.02))
        if f.tubo(e, U([s['a'], s['b']]), pset_seg(s), NOMES[s['dI']]): n['tubos'] += 1
    for m in MESH:
        if m['dI'] not in discs: continue
        cl, pred = classe_mesh(m)
        ps = {'disciplina': m['dI'], 'marca': m.get('grupo') or m['trecho'], 'familia': m['nome'], 'categoria_revit': m['cat'], 'comentarios': m.get('desc') or None,
              'alterado_R01': 'sim' if 'R01 18/10' in (m.get('desc') or '') else None}
        if f.malha(m['tri'], str(m['id']), m['nome'][:60], cl, m['dI'], ps, NOMES[m['dI']] + ' — peças', pred, 0.2 if cl == 'IfcDistributionChamberElement' else 0.0): n['peças'] += 1
    return n


def terreno(f):
    imp = [os.path.join(G, x) for x in os.listdir(G) if x.startswith('IMP') and x.endswith('_mesh.tsv')][0]; n = 0
    for l in open(imp, encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 9 or not r[8] or r[2] not in ('Sólido topográfico', 'Pisos'): continue
        tri = np.array(r[8].split(','), dtype=float).reshape(-1, 3, 3)
        if f.malha(tri, 'IMP:' + r[1], r[3][:60], 'IfcGeographicElement', 'TERRENO', {'origem': 'IMP as built (24-049-JDI-CTO-ETIB-IMP-R00)', 'categoria_revit': r[2]}, None, 'TERRAIN', 0.5): n += 1
    return n


def estrutura(f):
    n = 0
    for m in MESH:
        if m['disc'] != 'EST': continue
        if f.malha(m['tri'], m['id'], m['trecho'][:60], 'IfcBuildingElementProxy', 'EST', {'origem': 'estrutura as built (referência)', 'bloco': m['bloco'], 'categoria_revit': m['cat'], 'arquivo': m['desc']}, 'Estrutura as built (referência)', None, 0.6): n += 1
    return n


def conflitos(f):
    n = 0
    for r in csv.DictReader(open(os.path.join(C, 'itens_pontos_R01.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['depois'] != 'colide': continue
        E, N, z = U([float(r['x']), float(r['y']), float(r['z'])])[0]; n += 1
        f.conflito(dict(E=E, N=N, z=z, gravidade='CRÍTICA'), 'C%03d' % n, {'item': r['item'], 'A': '%s %s' % (r['disc_a'], r['elem_a']), 'B': '%s %s' % (r['disc_b'], r['elem_b']),
                   'folga_cm': float(r['folga_depois_cm'] or r['folga_cm']), 'situacao': 'esperada' if 'AB-01' in r['elem_a'] + r['elem_b'] else 'a definir pelo projetista'})
    return n


COR_EST = (0.60, 0.62, 0.68)
import preclash.export_ifc as XI
XI.COR.setdefault('EST', COR_EST)
print('origem dos IFC (E, N, cota):', [round(v, 3) for v in ORIGEM])
for grupo, discs in ENTREGA.items():
    f = IfcJan(f'{ESCOLA} — {grupo} — compatibilizado (R01)', ORIGEM, EPSG, autor='Populus — compatibilização R01 (modelos JAN revisados)')
    n = redes(f, discs); fn = os.path.join(SAIDA, f'JAN_{grupo}_compatibilizado_R01.ifc'); f.salvar(fn)
    print(f'  {os.path.basename(fn)}: {dict(n)}  {os.path.getsize(fn) / 1e6:.1f} MB')
f = IfcJan(f'{ESCOLA} — terreno (IMP as built)', ORIGEM, EPSG); n = terreno(f); fn = os.path.join(SAIDA, 'JAN_TERRENO_IMP.ifc'); f.salvar(fn)
print(f'  {os.path.basename(fn)}: {n} malhas  {os.path.getsize(fn) / 1e6:.1f} MB')
f = IfcJan(f'{ESCOLA} — estrutura as built (referência)', ORIGEM, EPSG); n = estrutura(f); fn = os.path.join(SAIDA, 'JAN_ESTRUTURA_referencia.ifc'); f.salvar(fn)
print(f'  {os.path.basename(fn)}: {n} peças  {os.path.getsize(fn) / 1e6:.1f} MB')
f = IfcJan(f'{ESCOLA} — federado R01 (redes compatibilizadas + terreno + estrutura + colisões que continuam)', ORIGEM, EPSG, autor='Populus — compatibilização R01')
tot = collections.Counter()
for discs in ENTREGA.values(): tot.update(redes(f, discs))
tot['terreno'] = terreno(f); tot['estrutura'] = estrutura(f); tot['conflitos'] = conflitos(f)
fn = os.path.join(SAIDA, 'JAN_FEDERADO_R01.ifc'); f.salvar(fn)
print(f'  {os.path.basename(fn)}: {dict(tot)}  {os.path.getsize(fn) / 1e6:.1f} MB')
