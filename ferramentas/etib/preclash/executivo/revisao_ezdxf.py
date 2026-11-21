# -*- coding: utf-8 -*-
"""Aplica o arquivo de comandos da revisão (_cmd_<folha>.txt, o mesmo que o revisao.lsp lê no accoreconsole) com ezdxf,
sem AutoCAD: DWG da cópia -> DXF (ODA File Converter) -> comandos -> DXF -> DWG 2018 (ODA). Os handles das entidades
são os do DWG original (a ODA preserva), então o plano do asbuilt.py vale igual.

Comandos (um por linha, campos separados por TAB), mesmo significado do revisao.lsp:
  LAYER nome cor tipo | PL layer fechado x y ... | TX layer x y h rot texto | MT layer x y h largura texto | CLOUD layer x y r
  DEL h | PLC h fechado x y ... | REPL h x y ... | MV h dx dy | VTX h k x y | TXC h x y rot texto
  RT h x y ang | CPR h bx by nx ny ang | ST h texto | LT h tipo

Uso: python revisao_ezdxf.py <copia.dwg|dxf> <_cmd.txt> <saida.dwg|dxf>"""
import os, sys, math, shutil, subprocess, tempfile
import ezdxf
from ezdxf.math import Matrix44

ODA = shutil.which('ODAFileConverter') or 'ODAFileConverter'


def oda(origem, destino, versao='ACAD2018'):
    """converte um arquivo DWG<->DXF pela ODA File Converter (precisa de xvfb-run no Linux)."""
    ext = 'DXF' if destino.lower().endswith('.dxf') else 'DWG'
    with tempfile.TemporaryDirectory() as ent, tempfile.TemporaryDirectory() as sai:
        shutil.copy2(origem, os.path.join(ent, os.path.basename(origem)))
        cmd = [ODA, ent, sai, versao, ext, '0', '1', '*.' + os.path.splitext(origem)[1][1:].upper()]
        if os.name != 'nt' and shutil.which('xvfb-run'): cmd = ['xvfb-run', '-a'] + cmd
        subprocess.run(cmd, capture_output=True, timeout=900)
        feitos = [f for f in os.listdir(sai) if f.lower().endswith('.' + ext.lower())]
        if not feitos: raise RuntimeError(f'ODA não converteu {origem}')
        shutil.copy2(os.path.join(sai, feitos[0]), destino)
    return destino


def ler(caminho):
    if caminho.lower().endswith('.dwg'):
        tmp = os.path.join(tempfile.mkdtemp(), os.path.splitext(os.path.basename(caminho))[0] + '.dxf')
        caminho = oda(caminho, tmp)
    return ezdxf.readfile(caminho)


class Revisao:
    def __init__(self, doc):
        self.doc, self.msp, self.db = doc, doc.modelspace(), doc.entitydb
        self.n, self.faltou = 0, []

    # ------------------------------------------------------------------ apoio
    def ent(self, h):
        e = self.db.get(h.upper())
        if e is None or not e.is_alive: self.faltou.append(h); return None
        return e

    def layout_de(self, e):
        dono = e.dxf.get('owner')
        lay = self.doc.layouts.get_layout_by_key(dono) if dono else None
        if lay is None:
            for b in self.doc.blocks:
                if b.block_record_handle == dono: return b
        return lay or self.msp

    def estilo(self):
        if 'R01' not in self.doc.styles:
            self.doc.styles.add('R01', font='arial.ttf').dxf.last_height = 0.3

    def tipo_linha(self, nome):
        if nome in self.doc.linetypes or nome.lower() in ('continuous', 'bylayer', 'byblock'): return True
        from ezdxf.tools.standards import linetypes
        for n, desc, padrao in linetypes():
            if n.upper() == nome.upper():
                self.doc.linetypes.add(nome, pattern=padrao, description=desc); return True
        return False

    @staticmethod
    def pares(xy):
        v = [float(x) for x in xy]
        return [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]

    @staticmethod
    def props_bl(d, chaves):
        """propriedades do molde + ByLayer no que ele não declara (como o r01:props_bl)."""
        a = {}
        for k in chaves:
            if d.hasattr(k): a[k] = d.get(k)
        if 'linetype' in chaves and not d.hasattr('linetype'): a['linetype'] = 'BYLAYER'
        if 'color' in chaves and not d.hasattr('color') and not d.hasattr('true_color'): a['color'] = 256
        if 'lineweight' in chaves and not d.hasattr('lineweight'): a['lineweight'] = -1
        return a

    # ------------------------------------------------------------------ comandos
    def LAYER(self, nm, cor, lt):
        if lt != 'Continuous': self.tipo_linha(lt)
        if nm not in self.doc.layers:
            self.doc.layers.add(nm, color=int(cor), linetype=lt if lt in self.doc.linetypes else 'Continuous', lineweight=35)

    def PL(self, lay, fech, *xy):
        p = self.msp.add_lwpolyline(self.pares(xy), close=fech == '1', dxfattribs={'layer': lay, 'const_width': 0.0})
        p.dxf.flags |= 128

    def CLOUD(self, lay, x, y, r):
        x, y, r = float(x), float(y), float(r)
        pts = [(x + r * math.cos(2 * math.pi * i / 12), y + r * math.sin(2 * math.pi * i / 12), 0, 0, 0.55) for i in range(12)]
        self.msp.add_lwpolyline(pts, format='xyseb', close=True, dxfattribs={'layer': lay, 'const_width': 0.0})

    def TX(self, lay, x, y, h, rt, txt):
        self.estilo()
        self.msp.add_text(txt, dxfattribs={'layer': lay, 'insert': (float(x), float(y)), 'height': float(h), 'rotation': math.degrees(float(rt)) % 360, 'style': 'R01'})

    def MT(self, lay, x, y, h, w, txt):
        self.estilo()
        self.msp.add_mtext(txt, dxfattribs={'layer': lay, 'insert': (float(x), float(y)), 'char_height': float(h), 'width': float(w),
                                            'attachment_point': 1, 'style': 'R01'})

    def DEL(self, h):
        e = self.ent(h)
        if e: self.layout_de(e).delete_entity(e)

    def PLC(self, h, fech, *xy):
        e = self.ent(h)
        if not e: return
        a = self.props_bl(e.dxf, ('layer', 'linetype', 'color', 'lineweight', 'ltscale', 'true_color'))
        a['const_width'] = e.dxf.get('const_width', 0.0) if e.dxftype() == 'LWPOLYLINE' else 0.0
        p = self.msp.add_lwpolyline(self.pares(xy), close=fech == '1', dxfattribs=a)
        p.dxf.flags |= 128

    def REPL(self, h, *xy):
        e = self.ent(h)
        if not e: return
        pts = self.pares(xy)
        if e.dxftype() == 'LWPOLYLINE':
            e.set_points(pts, format='xy')            # sem bulge nem largura por vértice, como o r01:repl
            e.dxf.discard('extrusion')
        elif e.dxftype() == 'LINE' and len(pts) >= 2:
            e.dxf.start, e.dxf.end = (*pts[0], 0), (*pts[-1], 0)

    def MV(self, h, dx, dy):
        e = self.ent(h)
        if e: e.translate(float(dx), float(dy), 0)

    def VTX(self, h, k, x, y):
        e = self.ent(h)
        if not e: return
        k, x, y = int(k), float(x), float(y)
        if e.dxftype() == 'LINE':
            if k == 0: e.dxf.start = (x, y, e.dxf.start.z)
            else: e.dxf.end = (x, y, e.dxf.end.z)
        elif e.dxftype() == 'LWPOLYLINE':
            v = list(e.get_points('xyseb'))
            if k < 0: k = len(v) - 1
            v[k] = (x, y) + tuple(v[k][2:])
            e.set_points(v, format='xyseb')

    def TXC(self, h, x, y, rt, txt):
        e = self.ent(h)
        if not e: return
        a = self.props_bl(e.dxf, ('layer', 'color', 'true_color'))
        alt = e.dxf.get('height') if e.dxftype() == 'TEXT' else e.dxf.get('char_height')
        a.update(insert=(float(x), float(y)), height=alt, rotation=math.degrees(float(rt)) % 360)   # grupo 50 do entmake = radianos
        if e.dxf.hasattr('style'): a['style'] = e.dxf.style
        if e.dxftype() == 'TEXT' and e.dxf.hasattr('width'): a['width'] = e.dxf.width
        self.msp.add_text(txt, dxfattribs=a)

    @staticmethod
    def _giro(x, y, graus):
        return Matrix44.chain(Matrix44.translate(-x, -y, 0), Matrix44.z_rotate(math.radians(graus)), Matrix44.translate(x, y, 0))

    def RT(self, h, x, y, a):
        e = self.ent(h)
        if e: e.transform(self._giro(float(x), float(y), float(a)))

    def CPR(self, h, bx, by, nx, ny, a):
        e = self.ent(h)
        if not e: return
        c = e.copy(); self.layout_de(e).add_entity(c)
        c.translate(float(nx) - float(bx), float(ny) - float(by), 0)
        if float(a) != 0.0: c.transform(self._giro(float(nx), float(ny), float(a)))

    def ST(self, h, txt):
        e = self.ent(h)
        if not e: return
        if e.dxftype() == 'MTEXT': e.text = txt
        else: e.dxf.text = txt

    def LT(self, h, tipo):
        e = self.ent(h)
        if not e: return
        self.tipo_linha(tipo); e.dxf.linetype = tipo
        if e.dxftype() == 'LWPOLYLINE': e.dxf.flags |= 128

    def aplicar(self, cmd_txt):
        for ln in open(cmd_txt, encoding='utf-8-sig').read().splitlines():
            if not ln.strip(): continue
            c = ln.split('\t')
            f = getattr(self, c[0], None)
            if f is None: raise ValueError(f'comando desconhecido: {c[0]}')
            f(*c[1:]); self.n += 1
        return self


def revisar(copia, cmd_txt, saida):
    doc = ler(copia)
    R = Revisao(doc).aplicar(cmd_txt)
    if saida.lower().endswith('.dwg'):
        tmp = os.path.join(tempfile.mkdtemp(), os.path.splitext(os.path.basename(saida))[0] + '.dxf')
        doc.saveas(tmp); oda(tmp, saida)
    else:
        doc.saveas(saida)
    print(f'REVR01 (ezdxf): {R.n} linhas -> {saida}' + (f'; handles não achados: {R.faltou}' if R.faltou else ''))
    return R


if __name__ == '__main__':
    revisar(*sys.argv[1:4])
