# -*- coding: utf-8 -*-
"""Exporta o modelo da pré-compatibilização em IFC4 georreferenciado (IfcMapConversion + IfcProjectedCRS EPSG).
Coordenadas do arquivo = UTM − origem do projeto (a mesma dos RVTs), cota absoluta. Um IfcSystem por disciplina.
Tubos = IfcSweptDiskSolid sobre o eixo (com os mergulhos verticais); caixas = prismas; terreno = malha triangulada;
conflitos = esferas vermelhas/laranja (IfcBuildingElementProxy) com o Pset do conflito.
Classes (dono do projeto, 20/10/2026: "um dos princípios do BIM é a informação"): perfil 'revit' (padrão) usa a classe que o Revit 2025
importa na categoria certa; perfil 'norma' usa a classe pura do IFC4. A classe da norma vai sempre no Pset PRECLASH
('classe_ifc_norma'). Teste no Revit 2025 (Abrir IFC, 20/10/2026) — a categoria sai só da classe, PredefinedType e tipo não mudam:
  IfcPipeSegment -> Tubulação · IfcPipeFitting -> Conexões de tubo · IfcCableCarrierSegment -> Bandejas de cabos (!) ·
  IfcCableCarrierFitting -> Conexões da bandeja de cabos (!) · IfcCableSegment -> Conduítes · IfcCableFitting -> Modelos genéricos ·
  IfcDistributionChamberElement -> Modelos genéricos (!) · IfcJunctionBox -> Dispositivos elétricos · IfcWasteTerminal e
  IfcInterceptor -> Equipamento hidráulico · IfcValve e IfcFlowMeter -> Acessórios do tubo · IfcFireSuppressionTerminal -> Sprinklers ·
  IfcTank -> Equipamento especial · IfcPump -> Equipamento mecânico · IfcElectricDistributionBoard -> Equipamento elétrico ·
  IfcLightFixture -> Luminárias · IfcAlarm -> Modelos genéricos. Nenhuma classe vira 'Conexões de conduíte'.
Sistemas: IfcDistributionSystem com o PredefinedType do sistema (DOMESTICCOLDWATER, SEWAGE, STORMWATER, FIREPROTECTION, ELECTRICAL…)."""
import time
import numpy as np
import ifcopenshell
import ifcopenshell.guid

COR = {'AF': (0.10, 0.45, 0.95), 'ESG': (0.55, 0.35, 0.15), 'AP': (0.10, 0.75, 0.75), 'DRE': (0.15, 0.55, 0.30),
       'ELE': (0.95, 0.75, 0.05), 'HID': (0.90, 0.10, 0.10), 'SDAI': (0.85, 0.30, 0.75), 'TERRENO': (0.55, 0.50, 0.40),
       'CRÍTICA': (1.0, 0.0, 0.0), 'ATENÇÃO': (1.0, 0.55, 0.0), 'TAMPA': (0.42, 0.42, 0.40)}
CLASSE = {'AF': 'IfcPipeSegment', 'ESG': 'IfcPipeSegment', 'AP': 'IfcPipeSegment', 'DRE': 'IfcPipeSegment',
          'HID': 'IfcPipeSegment', 'ELE': 'IfcCableCarrierSegment', 'SDAI': 'IfcCableCarrierSegment', 'CFTV': 'IfcCableCarrierSegment'}
ELETRICAS = ('ELE', 'SDAI', 'CFTV')
SISTEMA = {'AF': 'DOMESTICCOLDWATER', 'ESG': 'SEWAGE', 'AP': 'STORMWATER', 'DRE': 'STORMWATER', 'HID': 'FIREPROTECTION',
           'ELE': 'ELECTRICAL', 'SDAI': 'FIREPROTECTION', 'CFTV': 'SECURITY', 'CLI': 'AIRCONDITIONING'}
PERFIL_PADRAO = 'revit'


def classe_tubo(e, perfil=PERFIL_PADRAO):
    """(classe, PredefinedType, ObjectType, classe da norma) do trecho."""
    if e['disc'] in ELETRICAS:
        norma = 'IfcCableCarrierSegment.CONDUITSEGMENT'
        if perfil == 'revit': return 'IfcCableSegment', 'USERDEFINED', 'ELETRODUTO', norma
        return 'IfcCableCarrierSegment', 'CONDUITSEGMENT', None, norma
    pred = 'CULVERT' if e['de'] > 0.8 else 'RIGIDSEGMENT'
    return CLASSE.get(e['disc'], 'IfcPipeSegment'), pred, None, 'IfcPipeSegment.' + pred


def classe_conexao(pc, perfil=PERFIL_PADRAO):
    if pc['disc'] in ELETRICAS:
        norma = 'IfcCableCarrierFitting.' + ('BEND' if pc['tipo'] == 'curva' else 'TEE')
        if perfil == 'revit':
            return 'IfcCableSegment', 'USERDEFINED', 'CURVA DE ELETRODUTO' if pc['tipo'] == 'curva' else 'DERIVAÇÃO DE ELETRODUTO', norma
        return 'IfcCableCarrierFitting', norma.split('.')[1], None, norma
    pred = 'BEND' if pc['tipo'] == 'curva' else 'JUNCTION'
    return 'IfcPipeFitting', pred, None, 'IfcPipeFitting.' + pred


PRED = {'IfcLightFixture': 'POINTSOURCE', 'IfcElectricDistributionBoard': 'DISTRIBUTIONBOARD', 'IfcFlowMeter': 'ENERGYMETER',
        'IfcFireSuppressionTerminal': 'FIREHYDRANT', 'IfcUnitaryControlElement': 'ALARMPANEL', 'IfcTank': 'STORAGE', 'IfcValve': 'FAUCET',
        'IfcUnitaryEquipment': 'SPLITSYSTEM', 'IfcColumn': 'COLUMN', 'IfcBeam': 'BEAM', 'IfcFooting': 'PAD_FOOTING', 'IfcPump': 'ENDSUCTION'}

# Pset de entrega (Revisão de qualidade, 20/10/2026: nada de processo interno no IFC entregue): nome neutro, sem os campos de
# trabalho e sem texto que cite ferramenta, pessoa ou etapa interna. Os campos internos continuam nos CSV da rodada.
PSET_NOME = 'Dados_ETIB'
PSET_FORA = {'origem_cota', 'grupo_estudo', 'eixo_min_projeto', 'eixo_max_projeto', 'desvio_em_planta', 'pendente', 'mergulhos', 'dz_min',
             'eixo_min_solucao', 'tipo_rede', 'trechos', 'A', 'B', 'cota_estimada', 'GI_mont', 'GI_jus', 'sub', 'id', 'arquivo',
             'guid', 'modelo_origem', 'alterado_R01', 'comentarios', 'equipamento', 'malha'}
PSET_NOMES = {'recobrimento_estudo': 'recobrimento_m', 'rede': 'sistema', 'trecho': 'identificacao', 'DE_mm': 'diametro_externo_mm',
              'DN_mm': 'diametro_nominal_mm', 'CT': 'cota_tampa', 'fundo': 'cota_fundo', 'folga_m': 'folga_m'}
# nomes da equipe que não podem aparecer no IFC entregue: variável de ambiente ETIB_NOMES_EQUIPE (separados por vírgula)
PSET_PROIBIDO = tuple(n.strip().lower() for n in __import__('os').environ.get('ETIB_NOMES_EQUIPE', '').split(',') if n.strip()) + ('preclash', 'pré-compat', 'pre-compat', 'estudo', 'premissa', 'ajuste do terreno', 'thread', 'claude', 'obstáculo')
MATERIAL_CAIXA = {'c': 'Concreto pré-moldado', 'r': 'Alvenaria / concreto', 'q': 'Alvenaria / concreto'}


def classe_caixa(c, perfil=PERFIL_PADRAO, completo=False):
    """classe IFC da 'caixa': a do info['classe_ifc'] (equipamento), estrutura (EST) por tipo, senão pela disciplina e pelo tipo
    da caixa. completo=True devolve (classe, PredefinedType, ObjectType, classe da norma)."""
    def r(k, pred, ot=None, norma=None):
        return (k, pred, ot, norma or f'{k}.{pred}') if completo else (k, pred)
    if c['info'].get('classe_ifc'):
        k = c['info']['classe_ifc']; return r(k, c['info'].get('pred') or PRED.get(k, 'NOTDEFINED'))
    if c['disc'] == 'EST':
        t = str(c['info'].get('tipo', '')).lower()
        if 'pilar' in t or 'column' in t: return r('IfcColumn', 'COLUMN')
        if 'viga' in t or 'quadro' in t or 'beam' in t: return r('IfcBeam', 'BEAM')
        return r('IfcFooting', 'PAD_FOOTING')
    t = (str(c['info'].get('tipo', '')) + ' ' + str(c['info'].get('nome', c['id']))).lower()
    camara = 'IfcDistributionChamberElement.' + ('MANHOLE' if c['forma'] == 'c' or 'pv' in t or 'poço' in t else 'INSPECTIONCHAMBER')
    if c['disc'] in ELETRICAS:                       # caixa de passagem: IfcJunctionBox é a classe certa nas duas leituras
        return r('IfcJunctionBox', 'DATA' if c['disc'] == 'CFTV' else 'POWER', None, 'IfcJunctionBox')
    if perfil != 'revit':
        k, pred = camara.split('.'); return r(k, pred, None, camara)
    if c['disc'] in ('ESG', 'DRE', 'AP'):
        if 'gordura' in t: return r('IfcInterceptor', 'GREASE', None, 'IfcInterceptor.GREASE')
        if any(s in t for s in ('areia', 'boca de lobo', 'bl-', 'grelha', 'ralo', 'canaleta')): return r('IfcWasteTerminal', 'GULLYSUMP', None, camara)
        return r('IfcWasteTerminal', 'USERDEFINED', 'POÇO DE VISITA' if camara.endswith('MANHOLE') else 'CAIXA DE INSPEÇÃO', camara)
    if c['disc'] == 'HID':
        if 'abrigo' in t or 'hidrante' in t: return r('IfcFireSuppressionTerminal', 'FIREHYDRANT', None, 'IfcFireSuppressionTerminal.FIREHYDRANT')
        return r('IfcValve', 'USERDEFINED', 'CAIXA DE REGISTRO', camara)
    if c['disc'] == 'AF':
        if 'hidr' in t and 'metro' in t: return r('IfcFlowMeter', 'WATERMETER', None, 'IfcFlowMeter.WATERMETER')
        return r('IfcValve', 'USERDEFINED', 'CAIXA DE REGISTRO', camara)
    k, pred = camara.split('.'); return r(k, pred, None, camara)


class Ifc:
    def __init__(self, nome, origem, epsg, autor='Pré-compatibilização (preclash)', perfil=None):
        self.perfil = perfil or PERFIL_PADRAO; self.disc_grupo = {}
        self.f = f = ifcopenshell.file(schema='IFC4')
        self.o = np.array(origem, float)
        m = f.createIfcSIUnit(None, 'LENGTHUNIT', None, 'METRE')
        a = f.createIfcSIUnit(None, 'PLANEANGLEUNIT', None, 'RADIAN')
        units = f.createIfcUnitAssignment([m, a])
        self.wcs = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None)
        self.ctx = f.createIfcGeometricRepresentationContext(None, 'Model', 3, 1e-5, self.wcs, f.createIfcDirection((0.0, 1.0)))
        self.body = f.createIfcGeometricRepresentationSubContext('Body', 'Model', None, None, None, None, self.ctx, None, 'MODEL_VIEW', None)
        self.proj = f.createIfcProject(ifcopenshell.guid.new(), None, nome, autor, None, None, None, [self.ctx], units)
        crs = f.createIfcProjectedCRS(f'EPSG:{epsg}', 'SIRGAS 2000 / UTM zona 24S' if epsg == 31984 else None, 'SIRGAS2000', None, 'UTM',
                                      '24S' if epsg == 31984 else None, m)
        f.createIfcMapConversion(self.ctx, crs, float(self.o[0]), float(self.o[1]), float(self.o[2]), 1.0, 0.0, 1.0)
        self.site_pl = f.createIfcLocalPlacement(None, self.wcs)
        self.site = f.createIfcSite(ifcopenshell.guid.new(), None, nome, None, None, self.site_pl, None, None, 'ELEMENT', None, None, None, None, None)
        f.createIfcRelAggregates(ifcopenshell.guid.new(), None, None, None, self.proj, [self.site])
        self.contidos = []; self.grupos = {}; self.estilos = {}; self.materiais = {}; self.so_criticos = True

    def p(self, xyz):
        x, y, z = np.asarray(xyz, float) - self.o
        return self.f.createIfcCartesianPoint((float(round(x, 4)), float(round(y, 4)), float(round(z, 4))))

    def estilo(self, chave, transp=0.0):
        k = (chave, transp)
        if k not in self.estilos:
            r, g, b = COR.get(chave, (0.6, 0.6, 0.6))
            rgb = self.f.createIfcColourRgb(None, r, g, b)
            ren = self.f.createIfcSurfaceStyleRendering(rgb, transp, None, None, None, None, None, None, 'NOTDEFINED')
            self.estilos[k] = self.f.createIfcSurfaceStyle(chave, 'BOTH', [ren])
        return self.estilos[k]

    def _produto(self, classe, nome, desc, item, rep_tipo, cor, pset, grupo=None, tipo_pred=None, transp=0.0, tipo_obj=None):
        f = self.f
        f.createIfcStyledItem(item, [self.estilo(cor, transp)], None)
        rep = f.createIfcShapeRepresentation(self.body, 'Body', rep_tipo, [item])
        shp = f.createIfcProductDefinitionShape(None, None, [rep])
        pl = f.createIfcLocalPlacement(self.site_pl, self.wcs)
        kw = dict(GlobalId=ifcopenshell.guid.new(), Name=nome, Description=desc, ObjectPlacement=pl, Representation=shp)
        if tipo_pred: kw['PredefinedType'] = tipo_pred
        if tipo_obj: kw['ObjectType'] = tipo_obj
        el = f.create_entity(classe, **kw)
        self.contidos.append(el)
        if pset: self.pset(el, 'PRECLASH', pset)
        if grupo:
            self.grupos.setdefault(grupo, []).append(el); self.disc_grupo.setdefault(grupo, cor)
        return el

    def material(self, el, nome):
        if not nome: return
        self.materiais.setdefault(str(nome)[:255], []).append(el)

    def pset_padrao(self, el, nome, d):
        """Pset padrão do IFC4 (diâmetro etc.) com medidas tipadas."""
        f = self.f; props = []
        for k, (v, tipo) in d.items():
            if v is None: continue
            val = f.create_entity(tipo, float(v)) if tipo != 'IfcBoolean' else f.createIfcBoolean(bool(v))
            props.append(f.createIfcPropertySingleValue(k, None, val, None))
        if props:
            ps = f.createIfcPropertySet(ifcopenshell.guid.new(), None, nome, None, props)
            f.createIfcRelDefinesByProperties(ifcopenshell.guid.new(), None, None, None, [el], ps)

    def pset(self, el, nome, d):
        f = self.f; props = []
        if nome == 'PRECLASH':                       # Pset de entrega: nome neutro e sem campos/textos de processo
            nome = PSET_NOME
            d = {PSET_NOMES.get(k, k): v for k, v in d.items() if k not in PSET_FORA
                 and not any(s in str(v).lower() for s in PSET_PROIBIDO)}
        for k, v in d.items():
            if v is None or v == '': continue
            if isinstance(v, (float, np.floating)): val = f.createIfcReal(float(round(v, 4)))
            elif isinstance(v, (int, np.integer)) and not isinstance(v, bool): val = f.createIfcInteger(int(v))
            else: val = f.createIfcLabel(str(v)[:255])
            props.append(f.createIfcPropertySingleValue(k, None, val, None))
        if props:
            ps = f.createIfcPropertySet(ifcopenshell.guid.new(), None, nome, None, props)
            f.createIfcRelDefinesByProperties(ifcopenshell.guid.new(), None, None, None, [el], ps)

    def tubo(self, e, pts, pset, grupo):
        f = self.f
        P = [pts[0]] + [q for a, q in zip(pts[:-1], pts[1:]) if np.linalg.norm(q - a) > 1e-4]
        if len(P) < 2: return None
        # um disco varrido por segmento reto: a varredura ao longo de polilinha com ângulos minúsculos (0,1° a 1,6°, eletroduto que
        # segue o terreno) trava o OpenCascade (ELE-F-15, Revisão de qualidade 20/10/2026); peça por segmento é leve e robusta
        itens = [f.createIfcSweptDiskSolid(f.createIfcPolyline([self.p(a_), self.p(b_)]), float(e['de'] / 2), None, None, None)
                 for a_, b_ in zip(P[:-1], P[1:])]
        item = itens[0]
        classe, pred, ot, norma = classe_tubo(e, self.perfil)
        mat = e['info'].get('material') or e['info'].get('tipo_tubo')
        pset = dict(pset or {}, classe_ifc_norma=norma, material=mat)
        el = self._produto(classe, e['trecho'], e['id'], item, 'AdvancedSweptSolid', e['disc'], pset, grupo, pred, tipo_obj=ot)
        if len(itens) > 1:
            rep = el.Representation.Representations[0]; rep.Items = tuple(itens)
            for it in itens[1:]: f.createIfcStyledItem(it, [self.estilo(e['disc'])], None)
        self.material(el, mat)
        import re as _re
        _m = _re.search(r'[0-9]+(?:[.,][0-9]+)?', str(e['info'].get('DN_mm') or ''))
        dn = float(_m.group(0).replace(',', '.')) if _m else None
        if e['disc'] in ELETRICAS:
            self.pset_padrao(el, 'Pset_CableCarrierSegmentTypeConduitSegment', {'NominalWidth': (e['de'], 'IfcPositiveLengthMeasure'),
                                                                               'NominalHeight': (e['de'], 'IfcPositiveLengthMeasure')})
        else:
            self.pset_padrao(el, 'Pset_PipeSegmentTypeCommon', {'OuterDiameter': (e['de'], 'IfcPositiveLengthMeasure'),
                                                                'NominalDiameter': ((float(dn) / 1000.0) if dn else None, 'IfcPositiveLengthMeasure')})
        return el

    def caixa(self, c, grupo):
        """caixa/PV/caixa de passagem (dono do projeto, 20/10/2026: "estão muito simples, um cubo"): fundo + paredes ocas + tampa,
        por extrusão (leve). Parede 0,10 m (caixa retangular de alvenaria/concreto; PV circular = anel pré-moldado de 0,08 m),
        fundo 0,10 m, tampa 0,05 m (concreto; grelha nas caixas de drenagem de areia/boca de lobo). Equipamento, estrutura e caixa
        rasa (< 0,30 m) continuam como prisma. Dimensões externas = as do modelo (já com parede)."""
        f = self.f
        h = max(0.05, c['zt'] - c['zb'])
        ref = f.createIfcDirection((float(np.cos(c['rot'])), float(np.sin(c['rot'])), 0.0)) if c['forma'] == 'r' else None
        p2 = f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((0.0, 0.0)), None)
        circ = c['forma'] == 'c'
        R = float(c['meia']); X = float(2 * c.get('mx', c['meia'])); Y = float(2 * c.get('my', c['meia']))
        up = f.createIfcDirection((0.0, 0.0, 1.0))
        pos = lambda dz: f.createIfcAxis2Placement3D(self.p((c['E'], c['N'], c['zb'] + dz)), up if ref else None, ref)
        cheio = lambda: f.createIfcCircleProfileDef('AREA', None, p2, R) if circ else f.createIfcRectangleProfileDef('AREA', None, p2, X, Y)
        ps = {'disciplina': c['disc'], 'rede': c['rede'], 'tipo': c['info'].get('tipo'), 'CT': c['zt'], 'fundo': c['zb'], 'origem_cota': c['info'].get('cota')}
        classe, pred, ot, norma = classe_caixa(c, self.perfil, completo=True)
        ps['classe_ifc_norma'] = norma; ps['identificacao'] = c['info'].get('nome', c['id'])
        ps['DE_mm'] = c['info'].get('DE_mm'); ps['DN_mm'] = c['info'].get('DN_mm'); ps['material'] = c['info'].get('material')
        if pred == 'NOTDEFINED':                      # tipo predefinido sempre informado (Revisão de qualidade, item B3)
            pred = 'USERDEFINED'; ot = ot or str(c['info'].get('tipo') or c['info'].get('nome') or classe[3:]).upper()[:60]
        camara = norma.startswith('IfcDistributionChamberElement') or classe in ('IfcJunctionBox', 'IfcInterceptor')   # caixa de gordura também é oca (B11)
        menor = 2 * R if circ else min(X, Y)
        M = c['info'].get('malha')
        if M is not None and len(M):          # forma real (estrutura as built, equipamento): malha triangulada, não o prisma envolvente
            T = np.asarray(M, float).reshape(-1, 3)
            Vk, inv = np.unique(np.round(T - self.o, 4), axis=0, return_inverse=True)
            Fk = inv.reshape(-1, 3); Fk = Fk[(Fk[:, 0] != Fk[:, 1]) & (Fk[:, 1] != Fk[:, 2]) & (Fk[:, 0] != Fk[:, 2])]
            item = f.createIfcTriangulatedFaceSet(f.createIfcCartesianPointList3D([tuple(float(x) for x in v) for v in Vk]), None, None,
                                                  [tuple(int(i) + 1 for i in tr) for tr in Fk], None)
            el = self._produto(classe, c['info'].get('nome', c['id']), c['info'].get('tipo'), item, 'Tessellation', c['disc'], ps, grupo, pred, tipo_obj=ot)
            if c['info'].get('material'): self.material(el, c['info']['material'])
            elif c['disc'] == 'EST': self.material(el, 'Concreto armado')
            return el
        if not camara or c['info'].get('equipamento') or h < 0.30 or menor < 0.30:
            item = f.createIfcExtrudedAreaSolid(cheio(), pos(0.0), up, float(h))
            el = self._produto(classe, c['info'].get('nome', c['id']), c['info'].get('tipo'), item, 'SweptSolid', c['disc'], ps, grupo, pred,
                               transp=0.3 if camara else 0.0, tipo_obj=ot)
            if camara: self.material(el, MATERIAL_CAIXA.get(c['forma']))
            elif c['info'].get('material'): self.material(el, c['info']['material'])
            return el
        ep = 0.08 if circ else min(0.10, 0.2 * menor)
        tf, tt = 0.10, 0.05
        oco = (f.createIfcCircleHollowProfileDef('AREA', None, p2, R, ep) if circ else
               f.createIfcRectangleHollowProfileDef('AREA', None, p2, X, Y, ep, None, None))
        itens = [(f.createIfcExtrudedAreaSolid(cheio(), pos(0.0), up, tf), c['disc']),
                 (f.createIfcExtrudedAreaSolid(oco, pos(tf), up, float(h - tf - tt)), c['disc']),
                 (f.createIfcExtrudedAreaSolid(cheio(), pos(h - tt), up, tt), 'TAMPA')]
        grelha = c['disc'] in ('DRE', 'AP') and any(s in (str(c['info'].get('tipo', '')) + ' ' + str(c['info'].get('nome', ''))).lower()
                                                    for s in ('areia', 'boca de lobo', 'grelha', 'ralo', 'bl-'))
        for it, cor in itens: f.createIfcStyledItem(it, [self.estilo(cor)], None)
        rep = f.createIfcShapeRepresentation(self.body, 'Body', 'SweptSolid', [it for it, _ in itens])
        kw = dict(GlobalId=ifcopenshell.guid.new(), Name=c['info'].get('nome', c['id']), Description=c['info'].get('tipo'),
                  ObjectPlacement=f.createIfcLocalPlacement(self.site_pl, self.wcs), Representation=f.createIfcProductDefinitionShape(None, None, [rep]))
        if pred: kw['PredefinedType'] = pred
        if ot: kw['ObjectType'] = ot
        el = f.create_entity(classe, **kw)
        ps.update(parede_m=ep, fundo_m=tf, tampa=('grelha FoFo' if grelha else 'concreto') + f' {tt:.2f} m',
                  dimensao_interna=(f'Ø{2 * (R - ep):.2f} m' if circ else f'{X - 2 * ep:.2f} x {Y - 2 * ep:.2f} m'), profundidade_util=round(h - tf, 3))
        self.contidos.append(el); self.pset(el, 'PRECLASH', ps); self.material(el, MATERIAL_CAIXA.get(c['forma']))
        if grupo: self.grupos.setdefault(grupo, []).append(el); self.disc_grupo.setdefault(grupo, c['disc'])
        return el

    def conexao(self, pc, grupo):
        """peça de conexão (conexoes.py): curva = disco varrido nas duas pernas; junção = uma perna por ramal."""
        f = self.f; p = np.array([pc['E'], pc['N'], pc['z']]); r = pc['de'] / 2 * 1.2; L = max(1.5 * pc['de'], 0.06)
        # a perna da peça não passa do meio do tubo vizinho (Revisão de qualidade: "pedaço de tubo menor que a conexão")
        viz = [x for x in (pc.get('l1'), pc.get('l2'), pc.get('lmin')) if x]
        if viz: L = max(0.02, min(L, 0.45 * min(viz)))
        pernas = [(-np.array(pc['u1']), np.array(pc['u2']))] if pc['tipo'] == 'curva' else [(np.zeros(3), np.array(d)) for d in pc.get('ramais', [])]
        origens = [np.array(o) for o in pc.get('origens', [])] if pc['tipo'] != 'curva' else []
        pernas = [(a_, b_) for a_, b_ in pernas if np.linalg.norm(b_) > 0.5 and (np.linalg.norm(a_) > 0.5 or pc['tipo'] != 'curva')]
        if not pernas: return None                     # tubo de comprimento zero na ponta: peça degenerada (o OpenCascade não gera)
        itens = []
        for i_, (a, b) in enumerate(pernas):     # cada perna é um disco varrido reto (canto vivo na varredura falha no OpenCascade)
            o_ = p     # (perna saindo da ponta do tubo com queda até o nó piorou o C5: 1 -> 6; fica no nó)
            Qs = ([p + a * L, p], [p, p + b * L]) if np.linalg.norm(a) > 0 else ([o_, o_ + b * L],)
            for Q in Qs:
                itens.append(f.createIfcSweptDiskSolid(f.createIfcPolyline([self.p(q) for q in Q]), float(r), None, None, None))
        classe, pred, ot, norma = classe_conexao(pc, self.perfil)
        rot = (' + '.join(f"{x:g}°" for x in pc['combinacao']) if pc.get('combinacao') else f"{pc['comercial']:g}°") if pc['tipo'] == 'curva' else ''
        nome = (f"Curva {rot}" if pc['tipo'] == 'curva' else ('Derivação' if pc['disc'] in ELETRICAS else 'Junção')) + f" Ø{pc['de'] * 1000:.0f}"
        ps = {'disciplina': pc['disc'], 'rede': pc['rede'], 'tipo': pc['tipo'], 'angulo_real': pc['angulo'], 'angulo_comercial': pc['comercial'],
              'plano': pc['plano'], 'fora_do_comercial': 'sim' if pc['fora'] else None, 'DE_mm': pc['de'] * 1000, 'trechos': ', '.join(pc['elementos'])[:255],
              'classe_ifc_norma': norma, 'material': pc.get('material'), 'deflexao_junta_graus': pc.get('deflexao'), 'curvatura_no_tubo': 'sim' if pc.get('curvatura_no_tubo') else None,
              'pecas': (' + '.join(f'{x:g}°' for x in pc['combinacao']) + ' (duas curvas no vértice)') if pc.get('combinacao') else None}
        f.createIfcStyledItem(itens[0], [self.estilo(pc['disc'])], None)
        for it in itens[1:]: f.createIfcStyledItem(it, [self.estilo(pc['disc'])], None)
        rep = f.createIfcShapeRepresentation(self.body, 'Body', 'AdvancedSweptSolid', itens)
        el = f.create_entity(classe, GlobalId=ifcopenshell.guid.new(), Name=nome, Description=pc['plano'],
                             ObjectPlacement=f.createIfcLocalPlacement(self.site_pl, self.wcs),
                             Representation=f.createIfcProductDefinitionShape(None, None, [rep]), PredefinedType=pred, **({'ObjectType': ot} if ot else {}))
        self.contidos.append(el); self.pset(el, 'PRECLASH', ps); self.grupos.setdefault(grupo, []).append(el); self.disc_grupo.setdefault(grupo, pc['disc'])
        self.material(el, pc.get('material'))
        return el

    def terreno(self, V, F, nome='Terreno'):
        f = self.f
        pl = f.createIfcCartesianPointList3D([tuple(float(round(v, 3)) for v in (q - self.o)) for q in V])
        item = f.createIfcTriangulatedFaceSet(pl, None, None, [tuple(int(i) + 1 for i in t) for t in F], None)
        return self._produto('IfcGeographicElement', nome, 'terreno provisório', item, 'Tessellation', 'TERRENO', None, None, 'TERRAIN', transp=0.5)

    def conflito(self, c, nome, pset):
        if self.so_criticos and (c.get('gravidade') or '') != 'CRÍTICA': return None
        # esfera em malha (o importador do Revit não lê IfcSphere: "Unhandled subtype of IfcCsgSelect")
        f = self.f; r = 0.25; nv, nu = 6, 10
        V = [(0.0, 0.0, r)] + [(r * np.sin(np.pi * i / nv) * np.cos(2 * np.pi * j / nu), r * np.sin(np.pi * i / nv) * np.sin(2 * np.pi * j / nu),
                                r * np.cos(np.pi * i / nv)) for i in range(1, nv) for j in range(nu)] + [(0.0, 0.0, -r)]
        anel = lambda i, j: 2 + (i - 1) * nu + j % nu   # índice 1-based do vértice j do anel i
        F = [(1, anel(1, j), anel(1, j + 1)) for j in range(nu)]
        F += [t for i in range(1, nv - 1) for j in range(nu) for t in ((anel(i, j), anel(i + 1, j), anel(i + 1, j + 1)), (anel(i, j), anel(i + 1, j + 1), anel(i, j + 1)))]
        F += [(len(V), anel(nv - 1, j + 1), anel(nv - 1, j)) for j in range(nu)]
        x0, y0, z0 = np.array((c['E'], c['N'], c['z']), float) - self.o
        pl = f.createIfcCartesianPointList3D([(float(round(x0 + a, 4)), float(round(y0 + b, 4)), float(round(z0 + d, 4))) for a, b, d in V])
        item = f.createIfcTriangulatedFaceSet(pl, None, True, F, None)
        return self._produto('IfcBuildingElementProxy', nome, c.get('gravidade'), item, 'Tessellation', c.get('gravidade') or 'ATENÇÃO', pset, 'Conflitos', transp=0.2)

    def salvar(self, fn):
        f = self.f
        for nome, els in self.materiais.items():
            f.createIfcRelAssociatesMaterial(ifcopenshell.guid.new(), None, None, None, els, f.createIfcMaterial(nome, None, None))
        if self.contidos:
            f.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), None, None, None, self.contidos, self.site)
        for g, els in self.grupos.items():
            ps = SISTEMA.get(self.disc_grupo.get(g))
            s = (f.createIfcDistributionSystem(ifcopenshell.guid.new(), None, g, None, None, None, ps) if ps
                 else f.createIfcSystem(ifcopenshell.guid.new(), None, g, None, None))
            f.createIfcRelAssignsToGroup(ifcopenshell.guid.new(), None, None, None, els, None, s)
        f.write(fn)
