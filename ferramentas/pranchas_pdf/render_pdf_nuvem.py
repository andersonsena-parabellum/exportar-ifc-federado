import sys, time, os, ezdxf
ezdxf.options.support_dirs=[os.path.abspath('fontes'),'/usr/share/librecad/fonts']
import ezdxf.fonts.fonts as F
F.font_manager.build(folders=[os.path.abspath('fontes')], support_dirs=True)
from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf as pmb, layout, config
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, LineweightPolicy, BackgroundPolicy
src, out = sys.argv[1], sys.argv[2]
t=time.time(); doc=ezdxf.readfile(src); t_read=time.time()-t
# logos: aponta as imagens para a pasta local
logos={'GOV':'logos/CARIMBO_QG_logo_GOVBA.png','conder':'logos/CARIMBO_QG_logo_CONDER.png','QG':'logos/CARIMBO_QG_logo_QG.png'}
for d in doc.objects.query('IMAGEDEF'):
    fn=d.dxf.filename
    base=os.path.join(os.path.abspath('prancha/logos'), fn.replace('\\','/').split('/')[-1])
    if os.path.exists(base): d.dxf.filename=base; continue
    for k,v in logos.items():
        if k.lower() in fn.lower(): d.dxf.filename=os.path.abspath(os.path.join(os.path.dirname(src),v)); break
for o in doc.objects.query('RASTERVARIABLES'): o.dxf.frame=0
# o AutoCAD só quebra a linha do MTEXT quando passa da largura com uma folga pequena
# (medido: não quebra a 1,006x nem a 1,012x [escola C ESG CT/CF], quebra a 1,19x); o ezdxf quebra no limite exato
# só em rótulo curto (até 30 caracteres por parágrafo): em nota longa e justificada a folga alarga o bloco
# inteiro e invade o carimbo (escola C ESG, notas da LEGENDA)
for e in doc.entitydb.values():
    if e.dxftype()=='MTEXT' and e.dxf.get('width',0) and max(map(len, e.plain_text().split('\n')))<=30: e.dxf.width=e.dxf.width*1.08
# máscaras (WIPEOUT) dos blocos vão para o fundo do bloco, como o AutoCAD desenha pela ordem de exibição
for blk in doc.blocks:
    ws=[e for e in blk if e.dxftype()=='WIPEOUT']
    if ws and len(blk)>len(ws):
        es=blk.entity_space
        for w in ws: es.remove(w); es.entities.insert(0, w)
for blk in doc.blocks:
    for im in blk.query('IMAGE'): im.dxf.flags = im.dxf.flags & ~4
for im in doc.entitydb.values():
    pass
# espaçamento de parágrafo do AutoCAD (\pxsm1.5;) que o ezdxf ignora: vira o fator de entrelinha do MTEXT
import re
_rx=re.compile(r'(\\p[^;]*?),?sm([0-9.]+)([^;]*;)')
def _entrelinha(es):
    # tira só o "smN" do comando de parágrafo; recuo (i, l), tabulação (t) e
    # justificado (qj) continuam valendo
    for m in es.query('MTEXT'):
        g=_rx.search(m.text)
        if g:
            m.dxf.line_spacing_factor=float(g.group(2))
            m.text=_rx.sub(lambda h: h.group(1)+h.group(3), m.text).replace('\\px;','')
for blk in doc.blocks: _entrelinha(blk)
# ponto (_DotSmall/_Dot) na ponta do MLEADER: o AutoCAD plota com cerca de metade do diâmetro que o ezdxf
# desenha (medido na ESG-001 da escola C: 0,9 contra 1,9 com seta 3,0)
for _m in doc.entitydb.values():
    if _m.dxftype()=='MULTILEADER':
        _b=doc.entitydb.get(_m.dxf.get('arrow_head_handle'))
        if _b is not None and _b.dxf.get('name','').upper() in ('_DOTSMALL','_DOT'):
            _m.context.arrow_head_size*=0.47; _m.dxf.arrow_head_size=_m.context.arrow_head_size
# layout da prancha: LAY (padrão '01'); se não houver, a única folha do arquivo (ex.: 'Layout1' da EL-002 da escola C)
_lays=[n for n in doc.layouts.names() if n!='Model']
psp=doc.layouts.get(os.environ.get('LAY','01') if os.environ.get('LAY','01') in _lays else _lays[0])
# cinza 252 como o DWG To PDF do AutoCAD imprime (medido na ESG-001 da escola C)
import ezdxf.colors as _c
_c.DXF_DEFAULT_COLORS[252]=0x989898
for _e in doc.entitydb.values():
    if _e.dxftype()=='MTEXT' and '\\~' in _e.text: _e.text=_e.text.replace('\\~',' ')
# %%nnn (código do caractere) que o ezdxf não traduz; ∅ não existe na Arial (o AutoCAD troca por Ø)
_rx_cod=re.compile(r'%%(\d{3})')
for _e in doc.entitydb.values():
    _t=_e.dxftype()
    if _t in ('TEXT','ATTRIB','ATTDEF'):
        if '%%' in _e.dxf.text or '∅' in _e.dxf.text: _e.dxf.text=_rx_cod.sub(lambda g: chr(int(g.group(1))), _e.dxf.text).replace('∅','Ø')
    elif _t=='MTEXT' and ('%%' in _e.text or '∅' in _e.text):
        _e.text=_rx_cod.sub(lambda g: chr(int(g.group(1))), _e.text).replace('∅','Ø')
# marcadores de lista do AutoCAD ({\fSymbol...;·^I}): a fonte Symbol não existe aqui e o
# caractere vira um quadrado fora de lugar; troca pelo marcador Unicode, mantendo o TAB
_rx_sym=re.compile(r'\{\\fSymbol[^;]*;([^{}\\]*)\}')
_sym={'·':'•','Æ':'∅','°':'°','±':'±','´':'×'}
for _e in doc.entitydb.values():
    if _e.dxftype()=='MTEXT' and '\\fSymbol' in _e.text:
        _e.text=_rx_sym.sub(lambda g: ''.join(_sym.get(c,c) for c in g.group(1)), _e.text)
# export_mode: respeita camadas "não plotar" (Defpoints etc.) como o -PLOT do AutoCAD
# bloco inserido em camada congelada ou "não plotar" some inteiro no AutoCAD, mesmo
# com o conteúdo em outras camadas (ex.: base de arquitetura inserida na Defpoints);
# o ezdxf só olha a camada de cada objeto de dentro
from ezdxf.entities import Insert as _Insert
from ezdxf.addons.drawing.properties import layer_key as _lk
# MLEADER com dogleg de comprimento 0 dentro de bloco (DRE-001 da escola A): o ezdxf
# divide por zero ao transformar; o AutoCAD desenha sem o dogleg, então zera e segue
import ezdxf.entities.mleader as _ml
_ml_tr = _ml.LeaderData.transform
def _ml_transform(self, wcs):
    if self.dogleg_length == 0 or self.dogleg_vector.is_null:
        self.last_leader_point = wcs.m.transform(self.last_leader_point)
        self.breaks = list(wcs.m.transform_vertices(self.breaks))
        for ll in self.lines: ll.transform(wcs)
        return
    _ml_tr(self, wcs)
_ml.LeaderData.transform = _ml_transform
class RenderContextQG(RenderContext):
    def resolve_visible(self, entity, *, resolved_layer=None):
        if isinstance(entity, _Insert) and not entity.dxf.invisible and entity.doc:
            nome=self.resolve_layer(entity); lay=entity.doc.layers.get(nome)
            if lay is not None:
                if lay.is_frozen() or (self.export_mode and not lay.dxf.plot): return False
                lp=self.layers.get(_lk(nome))
                if lp is not None and not lp.is_visible and lay.is_on(): return False
        return super().resolve_visible(entity, resolved_layer=resolved_layer)
ctx=RenderContextQG(doc, ctb=os.environ.get("CTB",""), export_mode=True); ctx.set_current_layout(psp)
cfg=Configuration(color_policy=ColorPolicy.COLOR,
                  lineweight_policy=LineweightPolicy.ABSOLUTE, background_policy=BackgroundPolicy.WHITE)
be=pmb.PyMuPdfBackend()
# tracejado do model space visto na viewport: o ezdxf divide o padrão pela escala da
# viewport, o que deixa os traços pequenos demais. Como o AutoCAD plota:
#   PSLTSCALE 1 -> padrão fixo no papel; PSLTSCALE 0 -> padrão em unidades do modelo.
# Medido na escola D: EL (1:200, PSLTSCALE 1) e ESG/DRE (1:100, PSLTSCALE 0)
import ezdxf.addons.drawing.pipeline as _pl
_psl = psp.dxf_layout.dxf.get('layout_flags', doc.header.get('$PSLTSCALE', 1)) & 1
_pl.RenderPipeline2d.get_vp_ltype_scale = (lambda self: 1.0) if _psl else (lambda self: self.current_vp_scale)
# o PyMuPDF junta todo o desenho num só "shape" e a junção fica quadrática em pranchas
# grandes (5 min na escola D); grava o shape na página a cada 2000 objetos
def _em_lotes(nome):
    orig=getattr(pmb.PyMuPdfRenderBackend, nome)
    def f(self, shape, *a, **k):
        orig(self, shape, *a, **k)
        self._n_lote=getattr(self,'_n_lote',0)+1
        if self._n_lote>=2000:
            shape.commit(); self.content_shape=self.page.new_shape(); self._n_lote=0
    setattr(pmb.PyMuPdfRenderBackend, nome, f)
for _n in ('finish_line','finish_filling'): _em_lotes(_n)
class FrontendQG(Frontend):
    def draw_image_entity(self, entity, properties):
        # o AutoCAD não plota a moldura da imagem (IMAGEFRAME 0/2)
        orig=self.pipeline.draw_solid_lines
        self.pipeline.draw_solid_lines=lambda *a, **k: None
        try: super().draw_image_entity(entity, properties)
        finally: self.pipeline.draw_solid_lines=orig
    def draw_wipeout_entity(self, entity, properties):
        # WIPEOUTFRAME 1 (mostra e plota a borda): muitos símbolos de tomada são só a
        # borda da máscara; o ezdxf desenha a máscara sem a borda
        import copy
        from ezdxf.path import from_vertices
        borda=copy.copy(properties)
        super().draw_wipeout_entity(entity, properties)
        if _moldura_wipeout==1:
            self.pipeline.draw_path(from_vertices(entity.boundary_path_wcs(), close=True), borda)
_moldura_wipeout=next((o.dxf.get('frame',0) for o in doc.objects.query('WIPEOUTVARIABLES')), 0)

t=time.time(); FrontendQG(ctx, be, config=cfg).draw_layout(psp, finalize=True); t_draw=time.time()-t
page=layout.Page(1189, 841, layout.Units.mm, margins=layout.Margins.all(0))
s=layout.Settings(fit_page=False, scale=1)
t=time.time()
# posição das coisas do papel na página do PDF: a mesma conta do get_replay do ezdxf
import copy as _copy
_rb=be.player().bbox(); _L=layout.Layout(_rb, flip_y=be._init_flip_y); _pg=_L.get_final_page(page, s)
_s2=_copy.copy(s); _s2.output_coordinate_space=pmb.get_coordinate_output_space(_pg)
_m=_L.get_placement_matrix(_pg, settings=_s2, top_origin=True)
pdf=be.get_pdf_bytes(page, settings=s)
# OLE2FRAME (tabela do Excel colada na prancha): o ezdxf não desenha. O AutoCAD plota a imagem de
# apresentação guardada no OLE (WMF no fluxo OlePres000); converte pelo LibreOffice e cola no quadro
_oles=list(psp.query('OLE2FRAME'))
if _oles:
    import olefile, struct, subprocess, tempfile, pymupdf
    _pdf=pymupdf.open(stream=pdf, filetype='pdf'); _pag=_pdf[0]; _tmp=tempfile.mkdtemp()
    for _i,_o in enumerate(_oles):
        _img=None
        try:
            _b=_o.binary_data(); _cf=olefile.OleFileIO(_b[_b.find(bytes.fromhex('d0cf11e0a1b11ae1')):])
            _nm=[x for x in _cf.listdir() if 'OlePres' in x[0]]
            if not _nm and _cf.exists('CONTENTS') and _cf.openstream('CONTENTS').read(2)==b'BM':
                # imagem colada (StaticDib: o CONTENTS é um BMP), como a foto de satélite da IN-001 da escola A
                from PIL import Image as _Im; import io as _io
                _img=os.path.join(_tmp,'ole%d.png'%_i); _Im.open(_io.BytesIO(_cf.openstream('CONTENTS').read())).convert('RGB').save(_img)
                raise StopIteration
            _p=_cf.openstream(_nm[0]).read()
            _n=struct.unpack('<I',_p[36:40])[0]; _w=os.path.join(_tmp,'ole%d.wmf'%_i); open(_w,'wb').write(_p[40:40+_n])
            subprocess.run(['soffice','--headless','--convert-to','pdf','--outdir',_tmp,_w], capture_output=True, timeout=180)
            _src=pymupdf.open(os.path.join(_tmp,'ole%d.pdf'%_i)); _sp=_src[0]
            # recorte = área com tinta (o LibreOffice põe o desenho numa folha A4 com margem)
            _px=_sp.get_pixmap(dpi=72); import numpy as _np
            _a=_np.frombuffer(_px.samples, dtype=_np.uint8).reshape(_px.height,_px.width,_px.n)[:,:,:3].min(axis=2)<250
            _ys,_xs=_np.nonzero(_a); _cl=pymupdf.Rect(_xs.min(),_ys.min(),_xs.max()+1,_ys.max()+1)
        except StopIteration: pass
        except Exception as _x:
            print('OLE', _i, 'não colado:', _x); continue
        _c=[_t.value for _t in _o.acdb_ole2frame if _t.code in (10,11)]
        (_x1,_y1),(_x2,_y2)=[(_v[0],_v[1]) for _v in _c[:2]]
        _q1=_m.transform((_x1,_y1,0)); _q2=_m.transform((_x2,_y2,0))
        _r=pymupdf.Rect(min(_q1.x,_q2.x),min(_q1.y,_q2.y),max(_q1.x,_q2.x),max(_q1.y,_q2.y))
        _pag.draw_rect(_r, color=None, fill=(1,1,1), overlay=True)   # o OLE é opaco no AutoCAD
        if _img: _pag.insert_image(_r, filename=_img, keep_proportion=False)
        else: _pag.show_pdf_page(_r, _src, 0, clip=_cl, keep_proportion=False)
        print(f'OLE {_i} colado em {tuple(round(v) for v in _r)} pt')
    pdf=_pdf.tobytes(garbage=3, deflate=True)
open(out,'wb').write(pdf); t_pdf=time.time()-t
print(f"ler {t_read:.1f}s desenhar {t_draw:.1f}s gravar {t_pdf:.1f}s -> {out} {os.path.getsize(out)//1024} KB")
