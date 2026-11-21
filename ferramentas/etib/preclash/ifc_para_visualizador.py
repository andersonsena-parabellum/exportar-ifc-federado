# -*- coding: utf-8 -*-
"""Monta o <SIGLA>.json do visualizador único a partir de um IFC federado (ex.: a Jandaíra, modelada no Revit e exportada
no formato do preclash por FERRAMENTAS\\jandaira\\jan_ifc.py), sem rodar o clash.
  - tubos e eletrodutos (IfcSweptDiskSolid) viram 'elementos' (eixo + diâmetro), como no preclash;
  - caixas, conexões, registros, quadros, equipamentos e estrutura viram 'malhas' (triângulos, em cm);
  - IfcGeographicElement vira o terreno; proxies com Pset PRECLASH 'folga' viram as esferas de conflito.
Uso: ..\\.venv\\Scripts\\python.exe -X utf8 ifc_para_visualizador.py <federado.ifc> <SIGLA> "<Escola>" <saida.json> ["<nome da situação>"]"""
import sys, json, collections
import numpy as np
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement as up
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from preclash.export_ifc import COR

fn, sigla, escola, saida = sys.argv[1:5]
situacao = sys.argv[5] if len(sys.argv) > 5 else 'Modelo de entrega'
f = ifcopenshell.open(fn)
mc = f.by_type('IfcMapConversion')[0]
NOMES = {'AF': 'Água fria / reúso', 'ESG': 'Esgoto', 'AP': 'Pluvial', 'DRE': 'Drenagem', 'ELE': 'Elétrica enterrada',
         'HID': 'Hidrantes (PCI)', 'SDAI': 'SDAI (PCI)', 'CLI': 'Climatização', 'EST': 'Estrutura as built (referência)', 'ARQ': 'Pisos e paredes (referência)'}
COR = dict(COR, EST=(0.62, 0.62, 0.60), ARQ=(0.78, 0.76, 0.70), CLI=(0.30, 0.65, 0.95))
hexc = lambda c: '#%02x%02x%02x' % tuple(int(255 * x) for x in c)


def pset(p):
    return ue.get_psets(p).get('PRECLASH', {})


def disc_de(p, ps):
    d = ps.get('disciplina')
    if d: return d
    cat = (ps.get('categoria_revit') or '').lower()
    if 'estrutura' in cat or 'pilar' in cat or 'funda' in cat: return 'EST'
    return 'ARQ'


# ---------------------------------------------------------------- tubos (eixo)
elementos, feitos = [], set()
for p in f.by_type('IfcPipeSegment') + f.by_type('IfcCableCarrierSegment') + f.by_type('IfcCableSegment'):
    rep = p.Representation and p.Representation.Representations[0]
    if not rep or not rep.Items or not rep.Items[0].is_a('IfcSweptDiskSolid'): continue
    sd = rep.Items[0]; P = []
    for it in rep.Items:                       # um disco varrido por segmento (exportador de 20/10/2026) ou uma polilinha só
        if not it.is_a('IfcSweptDiskSolid'): continue
        cur = it.Directrix
        if cur.is_a('IfcPolyline'): Q = [pt.Coordinates for pt in cur.Points]
        elif cur.is_a('IfcIndexedPolyCurve'): Q = list(cur.Points.CoordList)
        else: continue
        P += Q[1:] if P and np.allclose(P[-1], Q[0]) else Q
    if len(P) < 2: continue
    P = np.array(P, float)
    M = up.get_local_placement(p.ObjectPlacement)
    P = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
    ps = pset(p)
    elementos.append({'id': p.GlobalId, 'disc': disc_de(p, ps), 'rede': ps.get('sistema') or ps.get('modelo_origem') or '', 'trecho': ps.get('marca') or p.Name,
                      'de': 2 * float(sd.Radius), 'p': P, 'info': {k: v for k, v in ps.items() if k not in ('id',) and v not in (None, '')}})
    feitos.add(p.id())
print('tubos', len(elementos))

# ---------------------------------------------------------------- malhas, terreno e conflitos
s = ifcopenshell.geom.settings(); s.set('use-world-coords', True)
it = ifcopenshell.geom.iterator(s, f, 4)
malhas, terV, terF, conf = [], [], [], []
if it.initialize():
    while True:
        sh = it.get(); p = f.by_id(sh.id)
        if p.id() not in feitos:
            V = np.array(sh.geometry.verts).reshape(-1, 3); F = np.array(sh.geometry.faces, int).reshape(-1, 3)
            ps = pset(p)
            if p.is_a('IfcGeographicElement') or (p.is_a('IfcBuildingElementProxy') and 'Sólido topográfico' in str(ps.get('categoria_revit', ''))):
                terF.append(F + sum(len(v) for v in terV)); terV.append(V)
            elif 'folga' in ps or 'folga_m' in ps or 'folga_cm' in ps:
                c = V.mean(0)
                conf.append({'g': ps.get('gravidade') or 'CRÍTICA', 'x': c[0], 'y': c[1], 'z': c[2], 'a': ps.get('A', ''), 'b': ps.get('B', ''),
                             'txt': str(ps.get('descricao') or ps.get('item') or p.Name), 'det': {k: str(v) for k, v in ps.items()}})
            else:
                malhas.append({'id': p.GlobalId, 'disc': disc_de(p, ps), 'cls': p.is_a(), 'nome': ps.get('marca') or p.Name or '',
                               'V': V, 'F': F, 'info': {k: v for k, v in ps.items() if k not in ('id',) and v not in (None, '')}})
        if not it.next(): break
print('malhas', len(malhas), '| triângulos do terreno', sum(len(x) for x in terF), '| conflitos', len(conf))

TV = np.vstack(terV) if terV else np.zeros((0, 3)); TF = np.vstack(terF) if terF else np.zeros((0, 3), int)
todos = np.vstack([TV] + [m['V'] for m in malhas] + [e['p'] for e in elementos])
zref = float(np.floor(np.percentile(todos[:, 2], 1)))
lo, hi = todos[:, :2].min(0), todos[:, :2].max(0)
ctr = [float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2), float(np.median(todos[:, 2]) - zref), float(max(hi - lo))]
r3 = lambda P: [[round(float(x), 3), round(float(y), 3), round(float(z - zref), 3)] for x, y, z in P]
cm = lambda V: [int(round(v)) for v in (np.c_[V[:, :2], V[:, 2] - zref] * 100).ravel()]
discs = sorted({e['disc'] for e in elementos} | {m['disc'] for m in malhas})
dados = {
    'escola': escola, 'sigla': sigla,
    'sub': f"UTM SIRGAS 2000/24S · origem E {mc.Eastings:.0f} N {mc.Northings:.0f} · cotas absolutas (−{zref:.0f} no 3D) · lido do IFC federado {fn.split(chr(92))[-1]}",
    'zref': zref, 'centro': ctr, 'disc': {d: {'nome': NOMES.get(d, d), 'cor': hexc(COR.get(d, (.6, .6, .6)))} for d in discs},
    'elementos': [{'id': e['id'], 'disc': e['disc'], 'rede': e['rede'], 'trecho': e['trecho'], 'de': e['de'], 'p': r3(e['p']), 'sol': None,
                   'cen': ['R'], 'pend': False, 'info': e['info'], 'dv': None} for e in elementos],
    'caixas': [],
    'malhas': [{'id': m['id'], 'disc': m['disc'], 'cls': m['cls'], 'nome': m['nome'], 'v': cm(m['V']), 'f': [int(i) for i in m['F'].ravel()], 'info': m['info']} for m in malhas],
    'terreno': {'v': [round(float(x), 2) for x in np.c_[TV[:, :2], TV[:, 2] - zref].ravel()], 'f': [int(i) for i in TF.ravel()]},
    'sit': [], 'curvas': {'v': [], 'm': []},
    'estados': [{'k': 'R', 'cen': 'R', 'fase': 'antes', 'nome': situacao}],
    'conflitos': {'R': [dict(c, x=round(float(c['x']), 3), y=round(float(c['y']), 3), z=round(float(c['z'] - zref), 3)) for c in conf]},
    'solucoes': {}, 'pendentes': {}, 'desvios': {},
}
open(saida, 'w', encoding='utf-8').write(json.dumps(dados, ensure_ascii=False, separators=(',', ':'), default=str))
print('gravado', saida, f"{__import__('os').path.getsize(saida) / 1e6:.1f} MB")
