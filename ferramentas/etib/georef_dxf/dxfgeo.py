# -*- coding: utf-8 -*-
"""Leitor mínimo de DXF ASCII (saída do DXFOUT do accoreconsole) que expande os blocos (aninhados)
e devolve a geometria do espaço do modelo em coordenadas do desenho.

Primitivas devolvidas (listas de dicts):
  segs   : {'lay','path','p':[(x,y,z),...],'closed'}   LINE, LWPOLYLINE, POLYLINE 2D/3D (bulge ignorado)
  circles: {'lay','path','c':(x,y),'r'}                CIRCLE e ARC (ARC também em segs, como corda aproximada)
  texts  : {'lay','path','p':(x,y,z),'h','rot','t'}   TEXT, MTEXT, ATTRIB
  inserts: {'lay','path','name','p':(x,y,z),'rot','s','mir'}  pose no mundo de toda inserção (qualquer nível)
  points : {'lay','path','p':(x,y,z)}
Uso como módulo: g = load(caminho_dxf) ; ou CLI: python -I dxfgeo.py arquivo.dxf (resumo).
"""
import math
import sys
import collections


def _pairs(fn):
    with open(fn, 'r', encoding='utf-8', errors='replace') as f:
        while True:
            c = f.readline()
            if not c:
                return
            v = f.readline()
            yield int(c), v.rstrip('\r\n')


def _entities(pairs):
    """Agrupa pares em entidades (tipo, [(code, val), ...]) dentro de uma seção."""
    cur = None
    for c, v in pairs:
        if c == 0:
            if cur is not None:
                yield cur
            if v == 'ENDSEC':
                return
            cur = (v, [])
        elif cur is not None:
            cur[1].append((c, v))
    if cur is not None:
        yield cur


def parse(fn):
    blocks = {}          # nome -> {'base':(x,y), 'flags':int, 'ents':[...]}
    model = []
    it = _pairs(fn)
    for c, v in it:
        if c == 0 and v == 'SECTION':
            c2, name = next(it)
            if name == 'BLOCKS':
                cur = None
                for typ, data in _entities(it):
                    if typ == 'BLOCK':
                        d = _first(data)
                        cur = {'name': d.get(2, ''), 'base': (float(d.get(10, 0)), float(d.get(20, 0))),
                               'flags': int(d.get(70, 0)), 'ents': []}
                    elif typ == 'ENDBLK':
                        if cur is not None:
                            blocks[cur['name']] = cur
                        cur = None
                    elif cur is not None:
                        cur['ents'].append((typ, data))
            elif name == 'ENTITIES':
                for typ, data in _entities(it):
                    model.append((typ, data))
    return blocks, model


# afim 2D (a b c d e f): x' = a x + b y + c ; y' = d x + e y + f ; mais z0 (deslocamento em z)
I = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def mul(m, n):
    return (m[0]*n[0] + m[1]*n[3], m[0]*n[1] + m[1]*n[4], m[0]*n[2] + m[1]*n[5] + m[2],
            m[3]*n[0] + m[4]*n[3], m[3]*n[1] + m[4]*n[4], m[3]*n[2] + m[4]*n[5] + m[5])


def ap(m, x, y):
    return (m[0]*x + m[1]*y + m[2], m[3]*x + m[4]*y + m[5])


MX = (-1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def _first(data):
    d = {}
    for c, v in data:
        d.setdefault(c, v)
    return d


def _mir(d):
    return float(d.get(230, 1.0)) < 0


def _vals(data, code):
    return [float(v) for c, v in data if c == code]


def _flatten(blocks, ents, M, z0, path, lay0, out, depth, skip_layers, root=-1):
    i = 0
    n = len(ents)
    while i < n:
        typ, data = ents[i]
        i += 1
        d = _first(data)
        if d.get(67, '0').strip() == '1':          # espaço do papel
            continue
        lay = d.get(8, '0')
        if lay0 is not None and lay == '0':
            lay = lay0
        if skip_layers and lay in skip_layers:
            if typ == 'POLYLINE' or (typ == 'INSERT' and d.get(66, '0').strip() == '1'):
                while i < n and ents[i][0] != 'SEQEND':
                    i += 1
                i += 1
            continue
        mo = mul(M, MX) if _mir(d) else M
        if typ == 'LINE':
            p1 = ap(M, float(d[10]), float(d[20])); p2 = ap(M, float(d[11]), float(d[21]))
            out['segs'].append({'lay': lay, 'path': path, 'root': root, 'p': [(p1[0], p1[1], z0 + float(d.get(30, 0))), (p2[0], p2[1], z0 + float(d.get(31, 0)))], 'closed': False, 'typ': 'LINE'})
        elif typ == 'LWPOLYLINE':
            xs, ys = _vals(data, 10), _vals(data, 20)
            z = z0 + float(d.get(38, 0))
            pts = [ap(mo, x, y) + (z,) for x, y in zip(xs, ys)]
            out['segs'].append({'lay': lay, 'path': path, 'root': root, 'p': pts, 'closed': bool(int(d.get(70, 0)) & 1), 'typ': 'PL'})
        elif typ == 'POLYLINE':
            fl = int(d.get(70, 0))
            pts = []
            while i < n and ents[i][0] == 'VERTEX':
                vd = _first(ents[i][1]); i += 1
                if int(vd.get(70, 0)) & 16:       # vértice de controle de spline
                    continue
                mm = M if fl & 8 else mo
                xy = ap(mm, float(vd.get(10, 0)), float(vd.get(20, 0)))
                pts.append(xy + (z0 + float(vd.get(30, 0)),))
            if i < n and ents[i][0] == 'SEQEND':
                i += 1
            if not fl & (16 | 64) and pts:
                out['segs'].append({'lay': lay, 'path': path, 'root': root, 'p': pts, 'closed': bool(fl & 1), 'typ': 'PL3' if fl & 8 else 'PL'})
        elif typ in ('CIRCLE', 'ARC'):
            cx, cy, r = float(d[10]), float(d[20]), float(d[40])
            sc = math.sqrt(abs(mo[0]*mo[4] - mo[1]*mo[3]))
            c = ap(mo, cx, cy)
            out['circles'].append({'lay': lay, 'path': path, 'root': root, 'c': c, 'r': r*sc, 'typ': typ, 'z': z0 + float(d.get(30, 0))})
            if typ == 'ARC':
                a1, a2 = math.radians(float(d[50])), math.radians(float(d[51]))
                if a2 < a1:
                    a2 += 2*math.pi
                k = max(2, int((a2 - a1) / math.radians(10)) + 1)
                pts = [ap(mo, cx + r*math.cos(a1 + (a2-a1)*j/k), cy + r*math.sin(a1 + (a2-a1)*j/k)) + (z0,) for j in range(k+1)]
                out['segs'].append({'lay': lay, 'path': path, 'root': root, 'p': pts, 'closed': False, 'typ': 'ARC'})
        elif typ in ('TEXT', 'MTEXT', 'ATTRIB'):
            t = ''.join(v for c, v in data if c == 3) + d.get(1, '')
            mm = M if typ == 'MTEXT' else mo
            xy = ap(mm, float(d.get(10, 0)), float(d.get(20, 0)))
            rot = float(d.get(50, 0))
            if typ == 'MTEXT' and 11 in d:
                rot = math.degrees(math.atan2(float(d.get(21, 0)), float(d[11])))
            rw = math.degrees(math.atan2(mm[3]*math.cos(math.radians(rot)) + mm[4]*math.sin(math.radians(rot)),
                                         mm[0]*math.cos(math.radians(rot)) + mm[1]*math.sin(math.radians(rot))))
            sc = math.sqrt(abs(mm[0]*mm[4] - mm[1]*mm[3]))
            out['texts'].append({'lay': lay, 'path': path, 'root': root, 'p': xy + (z0 + float(d.get(30, 0)),), 'h': float(d.get(40, 0))*sc, 'rot': rw, 't': t, 'typ': typ, 'anexo': int(d.get(71, 7)) if typ == 'MTEXT' else 7})
        elif typ == 'POINT':
            xy = ap(M, float(d.get(10, 0)), float(d.get(20, 0)))
            out['points'].append({'lay': lay, 'path': path, 'root': root, 'p': xy + (z0 + float(d.get(30, 0)),)})
        elif typ == 'INSERT':
            name = d.get(2, '')
            att = []
            if d.get(66, '0').strip() == '1':
                while i < n and ents[i][0] != 'SEQEND':
                    att.append(ents[i]); i += 1
                i += 1
            b = blocks.get(name)
            px, py, pz = float(d.get(10, 0)), float(d.get(20, 0)), float(d.get(30, 0))
            rot = math.radians(float(d.get(50, 0)))
            sx, sy = float(d.get(41, 1)), float(d.get(42, 1))
            ncol, nrow = int(d.get(70, 1)) or 1, int(d.get(71, 1)) or 1
            dcol, drow = float(d.get(44, 0)), float(d.get(45, 0))
            for ic in range(ncol):
                for ir in range(nrow):
                    ox = px + math.cos(rot)*ic*dcol - math.sin(rot)*ir*drow
                    oy = py + math.sin(rot)*ic*dcol + math.cos(rot)*ir*drow
                    bp = b['base'] if b else (0.0, 0.0)
                    Mi = mul((math.cos(rot), -math.sin(rot), ox, math.sin(rot), math.cos(rot), oy),
                             (sx, 0.0, -sx*bp[0], 0.0, sy, -sy*bp[1]))
                    Mw = mul(mo, Mi)
                    w = ap(mo, ox, oy)
                    det = Mw[0]*Mw[4] - Mw[1]*Mw[3]
                    rid = root if depth > 0 else len(out['inserts'])
                    out['inserts'].append({'lay': lay, 'path': path, 'root': root, 'name': name, 'p': w + (z0 + pz,),
                                           'rot': math.degrees(math.atan2(Mw[3], Mw[0])), 's': math.sqrt(abs(det)),
                                           'mir': det < 0, 'M': Mw})
                    if b and depth < 12:
                        _flatten(blocks, b['ents'], Mw, z0 + pz, path + '>' + name, lay, out, depth + 1, skip_layers, rid)
            if att:
                _flatten(blocks, att, M, z0, path, lay0, out, depth, skip_layers, root)


def load(fn, skip_layers=None):
    blocks, model = parse(fn)
    out = {'segs': [], 'circles': [], 'texts': [], 'inserts': [], 'points': [], 'blocks': blocks}
    _flatten(blocks, model, I, 0.0, '', None, out, 0, set(skip_layers or []))
    return out


if __name__ == '__main__':
    g = load(sys.argv[1])
    print({k: len(v) for k, v in g.items()})
    lays = collections.Counter(s['lay'] for s in g['segs'])
    print('segs por layer:', lays.most_common(25))
    tops = collections.Counter((s['path'].split('>') + ['', ''])[1] for s in g['segs'])
    print('segs por bloco de topo:', tops.most_common(15))
