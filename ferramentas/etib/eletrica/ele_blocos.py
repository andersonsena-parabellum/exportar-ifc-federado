"""Contorno das edificações (face externa) a partir dos vínculos estruturais (work/estrut_pegadas.csv, gerado por revit_pegadas_estrut.cs).
Por bloco: pilares (todos os níveis) + vigas do nível mais baixo (baldrame) + paredes e lajes da fundação.
Cada elemento vira o fecho convexo dos seus vértices em planta; união com fechamento de 0,30 m; buracos preenchidos.
Saída: work/blocos.json  [{bloco, coords}] e RELATORIOS/ELE_fase4_contorno_blocos_<data>.png"""
import json, collections
from shapely.geometry import MultiPoint, Polygon, mapping
from shapely.ops import unary_union
from PIL import Image, ImageDraw, ImageFont
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
E = collections.defaultdict(list)
for l in open(W + 'estrut_pegadas.csv', encoding='utf-8'):
    b, nm, cat, i, z0, z1, pts = l.rstrip('\n').split(';', 6)
    P = [tuple(map(float, q.split(','))) for q in pts.split()]
    E[b].append(dict(arq=nm.split('-')[7], cat=cat.replace('OST_', ''), z0=float(z0), z1=float(z1), P=P))
blocos = []
for b, els in sorted(E.items()):
    fr = [e for e in els if e['cat'] == 'StructuralFraming']
    zb = min(e['z1'] for e in fr) if fr else None
    sel = [e for e in els if e['cat'] == 'StructuralColumns'
           or (e['cat'] == 'StructuralFraming' and e['z1'] <= zb + 0.6)
           or (e['arq'] == 'FUN' and e['cat'] in ('Walls', 'Floors'))]
    hulls = [MultiPoint(e['P']).convex_hull for e in sel if len(e['P']) >= 3]
    U = unary_union([h.buffer(0.30, join_style=2) for h in hulls]).buffer(-0.30, join_style=2)
    geoms = U.geoms if hasattr(U, 'geoms') else [U]
    for g in geoms:
        if g.area < 2: continue
        blocos.append(dict(bloco=b, coords=[list(c) for c in Polygon(g.exterior).exterior.coords], area=round(Polygon(g.exterior).area, 1), n_elem=len(sel)))
json.dump(blocos, open(W + 'blocos.json', 'w'), indent=0)
for o in blocos: print(o['bloco'], o['area'], 'm2', o['n_elem'], 'elementos')

# imagem: blocos + redes
X0, Y0, X1, Y1, S = -40, -120, 115, 75, 8
img = Image.new('RGB', (int((X1 - X0) * S), int((Y1 - Y0) * S)), 'white'); d = ImageDraw.Draw(img)
f = lambda p: ((p[0] - X0) * S, (Y1 - p[1]) * S)
try: fn = ImageFont.truetype('arial.ttf', 22)
except Exception: fn = None
for o in blocos:
    d.polygon([f(p) for p in o['coords']], fill=(225, 225, 225), outline=(0, 0, 0))
    c = Polygon(o['coords']).centroid; d.text(f((c.x, c.y)), o['bloco'], fill=(0, 0, 0), font=fn)
COR = {'EL1': (220, 0, 0), 'EL2': (230, 150, 0), 'CF1': (0, 140, 0), 'CF2': (0, 0, 220)}
for t, cor in COR.items():
    N = json.load(open(W + f'cotas_{t}.json'))
    for p in N['pieces']: d.line([f(q) for q in p['pts']], fill=cor, width=2)
    for bx in N['boxes']:
        x, y = f(bx['c']); d.rectangle([x - 3, y - 3, x + 3, y + 3], outline=cor)
img.save('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase4_contorno_blocos_2026-10-15.png')
print('png ok')
