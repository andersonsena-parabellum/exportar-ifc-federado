# -*- coding: utf-8 -*-
"""Leitor de DXF ASCII (sem ezdxf) com expansão recursiva de blocos, para georreferenciar e extrair redes.

O DXF sai do accoreconsole (dxfout.scr, rápido). Cada primitiva vira um registro com:
  tipo (LINE, PL, MLINE, CIRCLE, ARC, TEXT, INSERT, POINT), layer efetivo (o "0" herda o da inserção), caminho de blocos,
  pontos em WCS (numpy N×3), 'raiz' (handle da entidade de nível superior que contém a primitiva) e extras (r, texto, altura, rot, nome do bloco, fechada).
Transformações completas em 3D (OCS/extrusão, escala, rotação, ponto base), como o AutoCAD.

Uso como módulo:  from dxf_ler import ler;  prims = ler(r'...\\x.dxf', profundidade=8)
CLI:  python -I dxf_ler.py <x.dxf> <saida.tsv> [--ins]   (--ins: só INSERT e TEXT)
"""
import sys, math, re, pickle, os
import numpy as np

TIPOS = {'LINE', 'LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'ARC', 'TEXT', 'MTEXT', 'ATTRIB', 'INSERT', 'POINT', 'SPLINE', 'MLINE'}


def _pares(fn):
    with open(fn, encoding='utf-8', errors='replace') as f:
        while True:
            c = f.readline()
            if not c:
                return
            v = f.readline()
            yield int(c), v.rstrip('\r\n')


def _entidades(it):
    """Agrupa os pares em entidades [(tipo, [(codigo, valor), ...]), ...] até ENDSEC."""
    atual = None
    for c, v in it:
        if c == 0:
            if atual is not None:
                yield atual
            if v == 'ENDSEC':
                return
            atual = (v, [])
        elif atual is not None:
            atual[1].append((c, v))
    if atual is not None:
        yield atual


def _ler_secoes(fn):
    blocos, ents, header = {}, [], {}
    it = _pares(fn)
    for c, v in it:
        if c == 0 and v == 'SECTION':
            c2, nome = next(it)
            if nome == 'HEADER':
                var = None
                for c3, v3 in it:
                    if c3 == 0 and v3 == 'ENDSEC':
                        break
                    if c3 == 9:
                        var = v3; header[var] = []
                    elif var:
                        header[var].append((c3, v3))
            elif nome == 'BLOCKS':
                atual = None
                for tipo, cod in _entidades(it):
                    if tipo == 'BLOCK':
                        d = dict(cod)
                        atual = {'nome': d.get(2, ''), 'base': (float(d.get(10, 0)), float(d.get(20, 0)), float(d.get(30, 0))),
                                 'flags': int(d.get(70, 0)), 'ents': []}
                    elif tipo == 'ENDBLK':
                        if atual:
                            blocos[atual['nome']] = atual
                        atual = None
                    elif atual is not None:
                        atual['ents'].append((tipo, cod))
            elif nome == 'ENTITIES':
                ents = list(_entidades(it))
    return header, blocos, ents


def _ocs(n):
    """Matriz 3×3 OCS→WCS (algoritmo do eixo arbitrário)."""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    if abs(n[0]) < 1 / 64 and abs(n[1]) < 1 / 64:
        ax = np.cross([0, 1, 0], n)
    else:
        ax = np.cross([0, 0, 1], n)
    ax /= np.linalg.norm(ax); ay = np.cross(n, ax)
    return np.column_stack([ax, ay, n])


def _m4(R3=None, t=None):
    M = np.eye(4)
    if R3 is not None: M[:3, :3] = R3
    if t is not None: M[:3, 3] = t
    return M


def _get(cod, c, default=None, conv=float):
    for k, v in cod:
        if k == c:
            return conv(v)
    return default


def _all(cod, c, conv=float):
    return [conv(v) for k, v in cod if k == c]


def _ext(cod):
    x, y, z = _get(cod, 210, 0.0), _get(cod, 220, 0.0), _get(cod, 230, 1.0)
    return None if (abs(x) < 1e-12 and abs(y) < 1e-12 and z > 0) else (x, y, z)


def _limpa_mtext(s):
    s = re.sub(r'\\[ACFHQTWcfp][^;]*;', '', s)
    s = s.replace('\\P', ' ').replace('{', '').replace('}', '').replace('\\~', ' ')
    s = re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s


def _u(s):
    return re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)


class Leitor:
    def __init__(self, fn, profundidade=8, so_ins=False, excl=None):
        self.header, self.blocos, self.ents = _ler_secoes(fn)
        self.prof = profundidade; self.so_ins = so_ins
        self.excl = [re.compile('^' + re.escape(p).replace('\\*', '.*') + '$', re.I) for p in (excl or [])]
        self.out = []
        self.raiz = ''

    def _excluido(self, lay):
        return any(r.match(lay) for r in self.excl)

    def _pts(self, M, P):
        P = np.atleast_2d(np.asarray(P, float))
        return P @ M[:3, :3].T + M[:3, 3]

    def _emit(self, tipo, lay, path, pts, **kw):
        d = {'tipo': tipo, 'layer': lay, 'path': path, 'pts': pts, 'raiz': self.raiz}
        d.update(kw); self.out.append(d)

    def processa(self, lista, M, play, path, depth):
        i = 0
        n = len(lista)
        while i < n:
            tipo, cod = lista[i]
            i += 1
            if depth == 0:
                self.raiz = _get(cod, 5, '', str)
            if tipo == 'POLYLINE':
                verts = []
                while i < n and lista[i][0] in ('VERTEX', 'SEQEND'):
                    if lista[i][0] == 'VERTEX':
                        verts.append(lista[i][1])
                    i += 1
                    if lista[i - 1][0] == 'SEQEND':
                        break
                self._ent(tipo, cod, M, play, path, depth, verts=verts)
                continue
            if tipo == 'INSERT':
                atts = []
                if _get(cod, 66, 0, int) == 1:
                    while i < n and lista[i][0] in ('ATTRIB', 'SEQEND'):
                        if lista[i][0] == 'ATTRIB':
                            atts.append(lista[i][1])
                        i += 1
                        if lista[i - 1][0] == 'SEQEND':
                            break
                self._ent(tipo, cod, M, play, path, depth, atts=atts)
                continue
            if tipo in TIPOS:
                self._ent(tipo, cod, M, play, path, depth)

    def _ent(self, tipo, cod, M, play, path, depth, verts=None, atts=None):
        lay = _u(_get(cod, 8, '0', str))
        if depth == 0 and self.excl and self._excluido(lay):
            return
        if lay == '0' and play:
            lay = play
        ext = _ext(cod)
        Mo = M if ext is None else M @ _m4(_ocs(ext))
        so = self.so_ins
        if tipo == 'LINE' and not so:
            p = [[_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)], [_get(cod, 11, 0.), _get(cod, 21, 0.), _get(cod, 31, 0.)]]
            self._emit('LINE', lay, path, self._pts(M, p))
        elif tipo == 'LWPOLYLINE' and not so:
            xs, ys = _all(cod, 10), _all(cod, 20); el = _get(cod, 38, 0.)
            if xs:
                p = np.column_stack([xs, ys, np.full(len(xs), el)])
                self._emit('PL', lay, path, self._pts(Mo, p), fechada=bool(_get(cod, 70, 0, int) & 1))
        elif tipo == 'POLYLINE' and not so:
            fl = _get(cod, 70, 0, int)
            vv = [v for v in verts if not (_get(v, 70, 0, int) & (16 | 128))]
            if vv:
                p = [[_get(v, 10, 0.), _get(v, 20, 0.), _get(v, 30, 0.)] for v in vv]
                self._emit('PL', lay, path, self._pts(M if fl & 8 else Mo, p), fechada=bool(fl & 1))
        elif tipo == 'MLINE' and not so:
            xs, ys, zs = _all(cod, 11), _all(cod, 21), _all(cod, 31)
            if xs:
                self._emit('MLINE', lay, path, self._pts(M, np.column_stack([xs, ys, zs if len(zs) == len(xs) else np.zeros(len(xs))])),
                           escala=_get(cod, 40, 1.0), estilo=_get(cod, 2, '', str), fechada=bool(_get(cod, 71, 0, int) & 2))
        elif tipo == 'SPLINE' and not so:
            xs, ys, zs = _all(cod, 11), _all(cod, 21), _all(cod, 31)
            if not xs:
                xs, ys, zs = _all(cod, 10), _all(cod, 20), _all(cod, 30)
            if xs:
                self._emit('PL', lay, path, self._pts(M, np.column_stack([xs, ys, zs if len(zs) == len(xs) else np.zeros(len(xs))])), fechada=False, spline=True)
        elif tipo in ('CIRCLE', 'ARC') and not so:
            c = [_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)]
            r = _get(cod, 40, 0.)
            esc = math.sqrt(abs(np.linalg.det(Mo[:2, :2]))) if abs(np.linalg.det(Mo[:2, :2])) > 1e-12 else 1.0
            kw = {'r': r * esc}
            if tipo == 'ARC':
                a0, a1 = _get(cod, 50, 0.), _get(cod, 51, 0.)
                kw['a'] = (a0, a1)
                # pontas do arco em WCS
                pa = [[c[0] + r * math.cos(math.radians(a0)), c[1] + r * math.sin(math.radians(a0)), c[2]],
                      [c[0] + r * math.cos(math.radians(a1)), c[1] + r * math.sin(math.radians(a1)), c[2]]]
                kw['pontas'] = self._pts(Mo, pa)
            self._emit(tipo, lay, path, self._pts(Mo, [c]), **kw)
        elif tipo == 'POINT' and not so:
            self._emit('POINT', lay, path, self._pts(M, [[_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)]]))
        elif tipo in ('TEXT', 'MTEXT', 'ATTRIB'):
            if tipo == 'MTEXT':
                txt = _limpa_mtext(''.join(_all(cod, 3, str)) + _get(cod, 1, '', str))
                p = self._pts(M, [[_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)]])
                dx, dy = _get(cod, 11, None), _get(cod, 21, None)
                rot = math.degrees(math.atan2(dy, dx)) if dx is not None else math.degrees(_get(cod, 50, 0.))
            else:
                txt = _u(_get(cod, 1, '', str))
                # TEXT alinhado usa o 2º ponto (11) quando 72/73 ≠ 0
                al = _get(cod, 72, 0, int) or _get(cod, 73, 0, int)
                q = [_get(cod, 11, 0.), _get(cod, 21, 0.), _get(cod, 31, 0.)] if al else [_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)]
                p = self._pts(Mo, [q]); rot = _get(cod, 50, 0.)
            ang_m = math.degrees(math.atan2(Mo[1, 0], Mo[0, 0]))
            self._emit('TEXT', lay, path, p, texto=txt, h=_get(cod, 40, 0.), rot=(rot + ang_m) % 360, tag=_get(cod, 2, '', str) if tipo == 'ATTRIB' else '')
        elif tipo == 'INSERT':
            nome = _u(_get(cod, 2, '', str))
            b = self.blocos.get(_get(cod, 2, '', str))
            if b is None:
                return
            P = [_get(cod, 10, 0.), _get(cod, 20, 0.), _get(cod, 30, 0.)]
            sx, sy, sz = _get(cod, 41, 1.), _get(cod, 42, 1.), _get(cod, 43, 1.)
            th = math.radians(_get(cod, 50, 0.))
            nc, nr = _get(cod, 70, 1, int) or 1, _get(cod, 71, 1, int) or 1
            dc, dr = _get(cod, 44, 0.), _get(cod, 45, 0.)
            Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
            for ic in range(nc):
                for ir in range(nr):
                    off = Rz @ np.array([ic * dc, ir * dr, 0.])
                    Mi = Mo @ _m4(None, np.array(P) + off) @ _m4(Rz) @ _m4(np.diag([sx, sy, sz])) @ _m4(None, -np.array(b['base']))
                    pw = self._pts(Mi, [b['base']])
                    rot = math.degrees(math.atan2(Mi[1, 0], Mi[0, 0]))
                    esc = math.sqrt(abs(np.linalg.det(Mi[:2, :2])))
                    espelho = np.linalg.det(Mi[:2, :2]) < 0
                    self._emit('INSERT', lay, path, pw, nome=nome, rot=rot, s=esc, espelho=bool(espelho), M=Mi)
                    if depth < self.prof and not (b['flags'] & 4):
                        self.processa(b['ents'], Mi, lay, (path + '|' if path else '') + nome, depth + 1)
            for a in atts or []:
                self._ent('ATTRIB', a, M, play, path, depth)

    def roda(self):
        self.processa(self.ents, np.eye(4), None, '', 0)
        return self.out


def ler(fn, profundidade=8, so_ins=False, excl=None, cache=True):
    pk = fn + ('.ins' if so_ins else '') + '.v3.pkl'
    if cache and not excl and os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(fn):
        return pickle.load(open(pk, 'rb'))
    out = Leitor(fn, profundidade, so_ins, excl).roda()
    if cache and not excl:
        pickle.dump(out, open(pk, 'wb'))
    return out


def header(fn):
    return _ler_secoes(fn)[0]


def fmt(p):
    return ';'.join(f'{x:.4f},{y:.4f},{z:.4f}' for x, y, z in p)


if __name__ == '__main__':
    so = '--ins' in sys.argv
    prims = ler(sys.argv[1], so_ins=so)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        for d in prims:
            extra = ''
            if d['tipo'] == 'TEXT': extra = f" h={d['h']:.3f} rot={d['rot']:.4f} {d['texto']}"
            elif d['tipo'] == 'INSERT': extra = f" rot={d['rot']:.6f} s={d['s']:.4f} {d['nome']}"
            elif d['tipo'] in ('CIRCLE', 'ARC'): extra = f" r={d['r']:.4f}"
            elif d['tipo'] == 'PL': extra = f" c={int(d.get('fechada', False))}"
            f.write(f"{d['tipo']}\t{d['layer']}\t{d['path']}\t{fmt(d['pts'])}{extra}\n")
    print(len(prims), 'primitivas')
