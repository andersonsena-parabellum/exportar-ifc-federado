# -*- coding: utf-8 -*-
"""Lista as conexões marcadas 'fora_do_comercial' no IFC de entrega (observação da R03 da Jandaíra).
Uso:  ..\\..\\.venv\\Scripts\\python.exe -X utf8 jan_conexoes_fora.py <HIDRO.ifc> <saida.csv>"""
import sys, csv
import ifcopenshell, ifcopenshell.util.element as ue, ifcopenshell.util.placement as up

fn, saida = sys.argv[1], sys.argv[2]
f = ifcopenshell.open(fn)
# origem do IFC (mapa) para voltar a UTM
mc = f.by_type('IfcMapConversion')
E0, N0 = (mc[0].Eastings, mc[0].Northings) if mc else (0.0, 0.0)
rot = 0.0
if mc and mc[0].XAxisAbscissa is not None:
    import math
    rot = math.atan2(mc[0].XAxisOrdinate, mc[0].XAxisAbscissa)
import math
import numpy as np, ifcopenshell.geom as ig
CFG = ig.settings(); CFG.set(CFG.USE_WORLD_COORDS, True)
def verts(el):
    sh = ig.create_shape(CFG, el)
    return np.array(sh.geometry.verts).reshape(-1, 3)
def centro(el):
    V = verts(el)
    return (V.min(0) + V.max(0)) / 2
SEG = []
for sg in f.by_type('IfcPipeSegment'):
    try:
        SEG.append((sg.Name, verts(sg)))
    except Exception:
        pass
def vizinhos(p, r=0.6):
    out = []
    for nome, V in SEG:
        if np.min(np.linalg.norm(V - p, axis=1)) < r and nome not in out:
            out.append(nome)
    return out
linhas = []
for el in f.by_type('IfcPipeFitting'):
    ps = ue.get_psets(el)
    flag = any(v.get('fora_do_comercial') == 'sim' for v in ps.values())
    if not flag:
        continue
    props = {}
    for nome, v in ps.items():
        for k, x in v.items():
            if k != 'id':
                props[f'{nome}.{k}'] = x
    v = centro(el)
    x, y, z = v
    c, s = math.cos(rot), math.sin(rot)
    E, N = E0 + x * c - y * s, N0 + x * s + y * c
    viz = vizinhos(np.array(v))
    linhas.append({'trechos': ' / '.join(viz), 'peca': el.Name, 'tipo': el.PredefinedType, 'E': round(E, 2), 'N': round(N, 2), 'cota': round(z, 2), **props})
chaves = []
for l in linhas:
    for k in l:
        if k not in chaves:
            chaves.append(k)
with open(saida, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, chaves, delimiter=';')
    w.writeheader()
    w.writerows(linhas)
print(len(linhas), 'conexões;', 'campos:', chaves)
for l in linhas:
    print({k: l[k] for k in list(l)[:5]}, {k: v for k, v in l.items() if 'ngulo' in k or 'diam' in k.lower() or 'sistema' in k.lower() or 'rede' in k.lower()})
