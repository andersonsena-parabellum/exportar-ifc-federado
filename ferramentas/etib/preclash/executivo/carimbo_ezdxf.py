# -*- coding: utf-8 -*-
"""Aplica o arquivo de comandos do carimbo da construtora as built (carqg_<folha>.txt, o mesmo que o carimbo_qg/aplicar.lsp lê no
accoreconsole) com ezdxf, sem AutoCAD. Comandos: DEL h | ATT TAG valor [largura] | INS layout x y escala caminho |
LN x1 y1 x2 y2 | TX x y h alinh estilo texto (ver aplicar.lsp).

O bloco CARIMBO_QG_ASBUILT vem do CARIMBO_QG_ASBUILT.dwg (convertido pela ODA) e entra como definição de bloco na prancha,
com os atributos preenchidos; as logos ficam como imagem pelo nome, ao lado do DWG, como no AutoCAD.

Uso: python carimbo_ezdxf.py <prancha.dwg|dxf> <carqg.txt> <saida.dwg|dxf>"""
import os, re, sys
import ezdxf
from ezdxf import xref
from ezdxf.enums import TextEntityAlignment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from revisao_ezdxf import ler, oda
import tempfile

NOME = 'CARIMBO_QG_ASBUILT'
ALINH = {(0, 2): TextEntityAlignment.MIDDLE_LEFT, (1, 2): TextEntityAlignment.MIDDLE_CENTER}


def txt(s):
    """\\U+XXXX (como o AutoCAD lê) -> caractere."""
    return re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)


def bloco(doc, caminho):
    if NOME in doc.blocks: return doc.blocks[NOME]
    src = ler(caminho)
    blk = doc.blocks.new(NOME, base_point=src.header.get('$INSBASE', (0, 0, 0)))   # -INSERT de um DWG usa o INSBASE dele
    ld = xref.Loader(src, doc, conflict_policy=xref.ConflictPolicy.KEEP)
    ld.load_modelspace(blk); ld.execute()
    blk.block_record.dxf.units = 4
    return blk


def aplicar(doc, cmd_txt):
    vals, lay, n_del, faltou = {}, None, 0, []
    for ln in open(cmd_txt, encoding='utf-8-sig').read().splitlines():
        if not ln.strip(): continue
        c = ln.split('\t')
        if c[0] == 'DEL':
            e = doc.entitydb.get(c[1].upper())
            if e is None or not e.is_alive: faltou.append(c[1]); continue
            dono = doc.layouts.get_layout_by_key(e.dxf.owner)
            (dono or doc.modelspace()).delete_entity(e); n_del += 1
        elif c[0] == 'ATT':
            vals[c[1]] = (txt(c[2]), float(c[3]) if len(c) > 3 and c[3] else None)
        elif c[0] == 'INS':
            lay = doc.layouts.get(c[1]); x, y, s = map(float, c[2:5])
            bloco(doc, c[5])
            ins = lay.add_blockref(NOME, (x, y), dxfattribs={'xscale': s, 'yscale': s, 'layer': 'ARQ_TXT' if 'ARQ_TXT' in doc.layers else '0'})
            ins.add_auto_attribs({k: v[0] for k, v in vals.items()})
            for a in ins.attribs:
                v = vals.get(a.dxf.tag)
                if v and v[1]: a.dxf.width = v[1]
        elif c[0] == 'LN':
            lay.add_line((float(c[1]), float(c[2])), (float(c[3]), float(c[4])), dxfattribs={'layer': 'ARQ_TXT'})
        elif c[0] == 'TX':
            x, y, h = float(c[1]), float(c[2]), float(c[3])
            t = lay.add_text(txt(c[6]), height=h, dxfattribs={'layer': 'ARQ_TXT', 'style': c[5] if c[5] in doc.styles else 'Standard'})
            t.set_placement((x, y), align=ALINH[(int(c[4]), 2)])
        else:
            raise ValueError(f'comando desconhecido: {c[0]}')
    doc.set_raster_variables(frame=2)            # IMAGEFRAME 2: contorno das imagens não plota
    return n_del, faltou


def carimbar(prancha, cmd_txt, saida):
    doc = ler(prancha)
    n, faltou = aplicar(doc, cmd_txt)
    if saida.lower().endswith('.dwg'):
        tmp = os.path.join(tempfile.mkdtemp(), os.path.splitext(os.path.basename(saida))[0] + '.dxf')
        doc.saveas(tmp); oda(tmp, saida)
    else:
        doc.saveas(saida)
    print(f'CARQG (ezdxf): {n} apagados -> {saida}' + (f'; handles não achados: {faltou}' if faltou else ''))


if __name__ == '__main__':
    carimbar(*sys.argv[1:4])
