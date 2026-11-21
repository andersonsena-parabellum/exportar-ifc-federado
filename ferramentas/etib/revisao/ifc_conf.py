# -*- coding: utf-8 -*-
"""Conferência independente dos IFC de entrega (itens B, C e D do CHECKLIST.md).
Lê os IFC por disciplina como chegam ao cliente (não o JSON da ferramenta): tubos e eletrodutos pelo eixo (IfcSweptDiskSolid,
extrusão circular ou malha), conexões pelas pernas, caixas/equipamentos pelo prisma da malha, estrutura pela MALHA REAL
(não a caixa envolvente) e o terreno pelo IfcGeographicElement.
Uso direto: python -X utf8 ifc_conf.py <pasta ou arquivos .ifc> [--sigla JAN]  (o revisar.py chama as funções)."""
import os, sys, re, math, collections
import numpy as np
from rev_comum import PRECLASH, coord, Revisao
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue
from preclash import leitura_ifc as LI, clash as CL, modelo as MD
from preclash.terreno import Terreno

AGUA = {'AF', 'HID'}; ELET = {'ELE', 'SDAI', 'CFTV'}; GRAV = {'ESG', 'DRE', 'AP'}; PRESS = AGUA | ELET
SEG_NORMA = {**{d: 'IfcPipeSegment' for d in AGUA | GRAV}, **{d: 'IfcCableCarrierSegment' for d in ELET}}
FIT_NORMA = {**{d: 'IfcPipeFitting' for d in AGUA | GRAV}, **{d: 'IfcCableCarrierFitting' for d in ELET}}
EST_CLASSES = ('IfcColumn', 'IfcBeam', 'IfcFooting', 'IfcSlab', 'IfcWall', 'IfcPile', 'IfcMember', 'IfcPlate', 'IfcStair', 'IfcRamp', 'IfcRoof')
SIST_PRED = {'AF': ('DOMESTICCOLDWATER', 'WATERSUPPLY'), 'ESG': ('SEWAGE', 'WASTEWATER', 'DRAINAGE'), 'DRE': ('STORMWATER', 'RAINWATER', 'DRAINAGE'),
             'AP': ('STORMWATER', 'RAINWATER'), 'HID': ('FIREPROTECTION',), 'SDAI': ('FIREPROTECTION', 'SIGNAL', 'SECURITY', 'ELECTRICAL'),
             'ELE': ('ELECTRICAL', 'LIGHTING', 'POWERGENERATION'), 'CFTV': ('DATA', 'SECURITY', 'COMMUNICATION')}
ANG_COMERCIAL = (45.0, 90.0, 135.0)   # Anderson, 21/10/2026: peças comerciais são 90° e 45° (135° = 90° + 45°); tês e junções à parte
# deflexão sem peça (°): eletroduto enterrado de elétrica e alarme é flexível (PVC corrugado/PEAD) e faz curva de até 30° no próprio tubo
FLEX = {'ELE': 30.0, 'SDAI': 30.0, 'CFTV': 30.0}
MATERIAL_LEGENDA = {d: r'flex|corrugad|PEAD' for d in ('ELE', 'SDAI', 'CFTV')}   # eletroduto enterrado é flexível (Anderson, 21/10/2026)
RX_MAT_REVIT = re.compile(r'param[eé]tric|padr[aã]o|default|gen[eé]ric|\bDN\b|:\s|tipo \d', re.I)
FLEX_PADRAO = 5.0                      # junta dos tubos rígidos (preclash\conexoes.py 'flexivel')
RX_DIAM = re.compile(r'^(NominalDiameter|OuterDiameter|InnerDiameter|Diameter|Di[aâ]metro.*|DN|DE)$', re.I)
RX_FORA_ESCOPO = re.compile(r'\b(ETE|EEE|GLP|g[aá]s|CFTV|dados|l[oó]gica|solar|fotovolt|conten[cç][aã]o)\b', re.I)


# ------------------------------------------------------------------------------------------------ leitura
def _itens(items):
    for it in items:
        if it.is_a('IfcMappedItem'):
            yield from _itens(it.MappingSource.MappedRepresentation.Items)
        else:
            yield it


def diretrizes(p, u):
    """[(P (n,3) em metros, coordenadas do projeto já com o placement), DE)] de cada IfcSweptDiskSolid do corpo."""
    out = []
    if not p.Representation: return out
    M = LI._matriz(p, u)
    for rep in p.Representation.Representations:
        if rep.RepresentationIdentifier not in (None, 'Body'): continue
        for it in _itens(rep.Items):
            if not it.is_a('IfcSweptDiskSolid'): continue
            d = it.Directrix
            if d.is_a('IfcPolyline'): P = np.array([q.Coordinates for q in d.Points], float)
            elif d.is_a('IfcIndexedPolyCurve'): P = np.array(d.Points.CoordList, float)
            else: continue
            if P.shape[1] == 2: P = np.column_stack([P, np.zeros(len(P))])
            P = P * u
            out.append(((M[:3, :3] @ P.T).T + M[:3, 3], 2 * float(it.Radius) * u))
    return out


def _juntar(pecas, tol=0.002):
    """encadeia as diretrizes de um tubo (o exportador grava um IfcSweptDiskSolid por segmento reto) numa polilinha só;
    pedaço que não encosta em nenhuma ponta entra pela ponta mais próxima (a folga aparece no C2 como antes)."""
    pecas = [np.asarray(p, float) for p in pecas if len(p) >= 2]
    if len(pecas) == 1: return pecas[0]
    cad = pecas.pop(0)
    while pecas:
        melhor = None
        for i, q in enumerate(pecas):
            for inv in (False, True):
                qq = q[::-1] if inv else q
                for lado, d in (('fim', np.linalg.norm(qq[0] - cad[-1])), ('ini', np.linalg.norm(qq[-1] - cad[0]))):
                    if melhor is None or d < melhor[0]: melhor = (d, i, qq, lado)
        d, i, qq, lado = melhor; pecas.pop(i)
        if lado == 'fim': cad = np.vstack([cad, qq[1:] if d < tol else qq])
        else: cad = np.vstack([qq[:-1] if d < tol else qq, cad])
    return cad


def _sistemas(f):
    """id do produto -> (nome, classe, PredefinedType) do sistema (o 1º; IfcDistributionSystem tem preferência)."""
    out = {}
    for s in f.by_type('IfcSystem'):
        for r in s.IsGroupedBy or []:
            for o in r.RelatedObjects:
                atual = out.get(o.id())
                if atual is None or (atual[1] != 'IfcDistributionSystem' and s.is_a('IfcDistributionSystem')):
                    out[o.id()] = (s.Name or '', s.is_a(), getattr(s, 'PredefinedType', None))
    return out


def _diam_padrao(p):
    """(tem diâmetro em Pset padrão do IFC, valor achado em qualquer Pset)."""
    padrao, valor = False, None
    for nome, props in ue.get_psets(p).items():
        for k, v in props.items():
            if k == 'id' or v in (None, ''): continue
            if RX_DIAM.match(k) or k in ('DE_mm', 'DN_mm'):
                valor = valor or v
                if nome.startswith('Pset_') or nome.startswith('Qto_'): padrao = True
    return padrao, valor


def ler(arquivos, log=print):
    """Devolve dict: seg, fit, cx (caixas e equipamentos), est (malhas), terreno (V,F), arquivos (resumo por arquivo)."""
    st = ifcopenshell.geom.settings(); st.set('use-world-coords', True)
    R = dict(seg=[], fit=[], cx=[], est=[], ter=[], arquivos={}, proxies=[])
    for fn in arquivos:
        f = ifcopenshell.open(fn); cv = LI.Conversor(f); u = cv.u; sis = _sistemas(f)
        base = os.path.basename(fn)
        mc = f.by_type('IfcMapConversion'); crs = f.by_type('IfcProjectedCRS')
        R['arquivos'][base] = dict(schema=f.schema, mapa=bool(mc), crs=[c.Name for c in crs],
                                   origem=(float(mc[0].Eastings), float(mc[0].Northings), float(mc[0].OrthogonalHeight or 0)) if mc else None,
                                   classes=collections.Counter(), sistemas=[(s.is_a(), s.Name, getattr(s, 'PredefinedType', None)) for s in f.by_type('IfcSystem')],
                                   n_material=len(f.by_type('IfcRelAssociatesMaterial')),
                                   psets={ps.Name or '' for ps in f.by_type('IfcPropertySet')})
        malha = {}
        # tubos e conexões em disco varrido são lidos pelo eixo: não triangular (o OCC trava em alguns IfcCableSegment)
        so_disco = [p for p in f.by_type('IfcProduct') if p.Representation and
                    all(i.is_a('IfcSweptDiskSolid') for rep in p.Representation.Representations
                        if rep.RepresentationIdentifier in (None, 'Body') for i in _itens(rep.Items))
                    and any(rep.RepresentationIdentifier in (None, 'Body') for rep in p.Representation.Representations)]
        it = ifcopenshell.geom.iterator(st, f, 4, exclude=so_disco) if so_disco else ifcopenshell.geom.iterator(st, f, 4)
        if it.initialize():
            while True:
                sh = it.get()
                malha[sh.id] = (np.array(sh.geometry.verts).reshape(-1, 3), np.array(sh.geometry.faces, int).reshape(-1, 3))
                if not it.next(): break
        for p in f.by_type('IfcProduct'):
            k = p.is_a()
            if k in LI.IGNORAR or not p.Representation: continue
            R['arquivos'][base]['classes'][(k, getattr(p, 'PredefinedType', None))] += 1
            ps = LI._psets(p); s_ = sis.get(p.id(), ('', None, None))
            disc = ps.get('disciplina') or LI.disciplina(p, ps, s_[0])
            mat = ue.get_material(p)
            dpad, dval = _diam_padrao(p)
            reg = dict(arq=base, guid=p.GlobalId, classe=k, pred=getattr(p, 'PredefinedType', None), nome=p.Name or '',
                       otype=getattr(p, 'ObjectType', None), tag=getattr(p, 'Tag', None), disc=disc,
                       trecho=str(ps.get('trecho') or ps.get('marca') or ps.get('Marca') or p.Name or ''),
                       sist=s_, material=(mat.is_a() + ':' + str(getattr(mat, 'Name', '') or '')) if mat else None,
                       mat_txt=ps.get('material'), diam_padrao=dpad, diam=dval, ps=ps)
            V = F = None
            if p.id() in malha:
                V, F = malha[p.id()]; V = cv.utm(V)
            if k == 'IfcGeographicElement' or (V is not None and 'topogr' in str(ps.get('categoria_revit', '')).lower()):
                if V is not None: R['ter'].append((V, F))
                continue
            if k == 'IfcBuildingElementProxy' and (re.search(r'conflit|clash|CR[IÍ]TICA|ATEN', reg['nome'] + str(p.Description or ''), re.I)
                                                    or 'gravidade' in ps):
                R['proxies'].append(dict(reg, marcador=True)); continue
            if any(p.is_a(c) for c in EST_CLASSES) or disc == 'EST':
                if V is not None: R['est'].append(dict(reg, V=V, F=F, lo=V.min(0), hi=V.max(0)))
                continue
            norma = str(ps.get('classe_ifc_norma') or '')
            eh_conexao = not p.is_a('IfcJunctionBox') and (      # caixa de passagem herda de IfcFlowFitting, mas é caixa
                any(p.is_a(c) for c in LI.CONEXOES) or 'Fitting' in norma or
                re.search(r'CURVA|DERIVA|CONEX|JUN[CÇ]', str(reg['otype'] or ''), re.I) is not None)
            if any(p.is_a(c) for c in LI.SEGMENTOS) and not eh_conexao:
                dz = diretrizes(p, u)
                if dz:
                    P = _juntar([x[0] for x in dz]); de = max(x[1] for x in dz)   # um disco varrido por segmento reto: juntar todos
                    P = cv.utm(P)
                else:
                    r = LI.eixo_direto(p, u)
                    if r is not None:
                        P, de = r; P = cv.utm(P)
                    elif V is not None:
                        P, de = LI.eixo_pca(V)                       # V já está em UTM
                    else:
                        continue
                if 'DE_mm' in ps:
                    try: de = float(ps['DE_mm']) / 1000
                    except (TypeError, ValueError): pass
                P = np.array([P[0]] + [q for a, q in zip(P[:-1], P[1:]) if np.linalg.norm(q - a) > 1e-4])
                if len(P) < 2: continue
                R['seg'].append(dict(reg, P=P, de=de, L=float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))))
                continue
            if eh_conexao:
                dz = diretrizes(p, u); de = None
                if 'DE_mm' in ps:
                    try: de = float(ps['DE_mm']) / 1000
                    except (TypeError, ValueError): pass
                pernas = [cv.utm(P) for P, _ in dz]
                if pernas:
                    if len(pernas) == 1 and len(pernas[0]) >= 3:
                        c = pernas[0][len(pernas[0]) // 2]               # curva: [ponta, vértice, ponta]
                    else:                                                # junção: o ponto comum às pernas
                        T = np.vstack(pernas)
                        sc = [max(np.min(np.linalg.norm(Q - c, axis=1)) for Q in pernas) for c in T]
                        c = T[int(np.argmin(sc))]
                    dirs = []; portas = []
                    for Q in pernas:
                        for e in (Q[0], Q[-1]):
                            v = e - c; n = np.linalg.norm(v)
                            if n > 1e-3: dirs.append(v / n); portas.append(e)
                    if de is None: de = dz[0][1] / 1.2
                elif V is not None:
                    c = V.mean(0); dirs = []; portas = []
                    if de is None: de = float(np.ptp(V, axis=0).min())
                else: continue
                lo_, hi_ = (V.min(0), V.max(0)) if (V is not None and not pernas) else (None, None)
                R['fit'].append(dict(reg, c=c, dirs=dirs, portas=portas, de=de or 0.05, lo=lo_, hi=hi_))
                continue
            if V is None: continue
            cx_, cy_, lx, ly, rot, ac = LI.retangulo_minimo(V[:, :2])
            zb, zt = float(V[:, 2].min()), float(V[:, 2].max())
            if abs(lx - ly) < 0.08 * max(lx, ly) and ac < 0.85 * lx * ly:       # planta redonda (PV, poço): cilindro
                c = MD.caixa(f'{disc}:{reg["nome"]}#{p.id()}', disc or '?', disc or '?', 'c', cx_, cy_, (lx + ly) / 4, zb, zt)
            else:
                c = MD.caixa_retangular(f'{disc}:{reg["nome"]}#{p.id()}', disc or '?', disc or '?', cx_, cy_, lx, ly, rot, zb, zt)
            tipo = str(ps.get('tipo') or '').lower()
            # caixa (câmara) em qualquer perfil: classe de câmara, caixa de passagem, ou terminal/válvula que a norma diz ser câmara
            camara = (k in ('IfcDistributionChamberElement', 'IfcJunctionBox') or norma.startswith('IfcDistributionChamberElement')
                      or (k in ('IfcWasteTerminal', 'IfcInterceptor', 'IfcValve') and
                          re.search(r'CAIXA|PO[CÇ]O|GULLY|GREASE|INSPE', f'{reg["otype"] or ""} {reg["pred"] or ""}', re.I) is not None)
                      or (k == 'IfcTank' and 'enterrad' in tipo))
            c.update(reg=reg, camara=camara, equip=not camara, ct=ps.get('CT'), oca=_forma_caixa(p, u) if camara else None)
            R['cx'].append(c)
            if k == 'IfcBuildingElementProxy': R['proxies'].append(dict(reg, marcador=False))
        log(f'  {base}: {sum(R["arquivos"][base]["classes"].values())} produtos')
    return R


def _forma_caixa(p, u):
    """lê o corpo da caixa: sólidos extrudados (perfil e altura) — para conferir fundo, parede oca e tampa."""
    out = []
    if not p.Representation: return out
    for rep in p.Representation.Representations:
        if rep.RepresentationIdentifier not in (None, 'Body'): continue
        for it in _itens(rep.Items):
            if not it.is_a('IfcExtrudedAreaSolid'): continue
            pf = it.SweptArea; z0 = float(it.Position.Location.Coordinates[2]) * u if it.Position else 0.0
            parede = float(pf.WallThickness) * u if hasattr(pf, 'WallThickness') and pf.WallThickness else None
            out.append(dict(perfil=pf.is_a(), parede=parede, h=float(it.Depth) * u, z0=z0))
    return out


def _pset_nomes(R, arq):
    return R['arquivos'][arq].get('psets', set())


def terreno(R, cache):
    """Terreno das faces de cima das malhas do IfcGeographicElement -> Terreno (TIN)."""
    if not R['ter']: return None
    VV, FF, n = [], [], 0
    for V, F in R['ter']:
        nz = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])[:, 2]
        F = F[nz > 1e-9]; VV.append(V); FF.append(F + n); n += len(V)
    V = np.vstack(VV); F = np.vstack(FF)
    Vk, inv = np.unique(V.round(3), axis=0, return_inverse=True); F = inv.reshape(-1)[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    np.savez_compressed(cache, pts=Vk, tri=F)
    return Terreno(cache)


# ------------------------------------------------------------------------------------------------ geometria
def _dist_pt_tri(P, A, B, C):
    """distância (n,m) de pontos P (n,3) a triângulos (m,3) — ponto mais próximo (Ericson 5.1.5), vetorizado."""
    p = P[:, None, :]; a, b, c = A[None], B[None], C[None]
    ab, ac, ap = b - a, c - a, p - a
    d1 = (ab * ap).sum(-1); d2 = (ac * ap).sum(-1)
    bp = p - b; d3 = (ab * bp).sum(-1); d4 = (ac * bp).sum(-1)
    cp = p - c; d5 = (ab * cp).sum(-1); d6 = (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) > 1e-18, va + vb + vc, 1e-18)
    v = vb / den; w = vc / den
    Q = a + ab * v[..., None] + ac * w[..., None]
    # regiões de vértice/aresta
    m = (d1 <= 0) & (d2 <= 0); Q = np.where(m[..., None], a, Q)
    m = (d3 >= 0) & (d4 <= d3); Q = np.where(m[..., None], b, Q)
    m = (d6 >= 0) & (d5 <= d6); Q = np.where(m[..., None], c, Q)
    t = d1 / np.where(np.abs(d1 - d3) > 1e-18, d1 - d3, 1e-18)
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0) & ~((d1 <= 0) & (d2 <= 0)); Q = np.where(m[..., None], a + ab * t[..., None], Q)
    t = d2 / np.where(np.abs(d2 - d6) > 1e-18, d2 - d6, 1e-18)
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0) & ~((d1 <= 0) & (d2 <= 0)); Q = np.where(m[..., None], a + ac * t[..., None], Q)
    t = (d4 - d3) / np.where(np.abs((d4 - d3) + (d5 - d6)) > 1e-18, (d4 - d3) + (d5 - d6), 1e-18)
    m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); Q = np.where(m[..., None], b + (c - b) * t[..., None], Q)
    return np.linalg.norm(p - Q, axis=-1)


def _dentro(P, A, B, C):
    """número de voltas (ângulo sólido) de pontos P em relação à malha fechada: |w| > 0,5 = dentro."""
    a = A[None] - P[:, None]; b = B[None] - P[:, None]; c = C[None] - P[:, None]
    la, lb, lc = (np.linalg.norm(x, axis=-1) for x in (a, b, c))
    num = (a * np.cross(b, c)).sum(-1)
    den = la * lb * lc + (a * b).sum(-1) * lc + (a * c).sum(-1) * lb + (b * c).sum(-1) * la
    w = np.arctan2(num, den).sum(1) * 2 / (4 * np.pi)
    return np.abs(w) > 0.5


def folga_malha(P, r, est):
    """menor folga (m) de um eixo amostrado P (n,3) com raio r à malha da peça (negativa = dentro). Devolve (folga, ponto)."""
    V, F = est['V'], est['F']
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    best = (9.0, None)
    for k in range(0, len(P), 200):
        Q = P[k:k + 200]
        d = _dist_pt_tri(Q, A, B, C).min(1)
        perto = d < r + 0.30
        if not perto.any(): continue
        sgn = np.where(_dentro(Q[perto], A, B, C), -1.0, 1.0)
        f = sgn * d[perto] - r
        j = int(np.argmin(f))
        if f[j] < best[0]: best = (float(f[j]), Q[perto][j])
    return best


def pecas(seg):
    """lista de (a, b, r, índice do elemento) de todos os pedaços retos."""
    out = []
    for i, s in enumerate(seg):
        for a, b in zip(s['P'][:-1], s['P'][1:]):
            if np.linalg.norm(b - a) > 1e-6: out.append((a, b, s['de'] / 2, i))
    return out


def _desvio(u, v):
    return math.degrees(math.acos(float(np.clip(np.dot(u, v), -1, 1))))


def _ang_peca(f):
    """ângulo nominal da peça (Pset angulo_comercial ou "Curva 22.5°" no nome); None se não houver."""
    v = f['ps'].get('angulo_comercial')
    if v not in (None, ''):
        try: return float(str(v).replace(',', '.'))
        except ValueError: pass
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*°', f['nome'] or '')
    return float(m.group(1).replace(',', '.')) if m else None


def _msg_angulo(d, f, ang):
    a = _ang_peca(f)
    if a is not None and not _comercial(a, 0.5):
        return f'{d}: {f["nome"]} num vértice de {ang:.1f}°: peça de {a:g}° fora das comerciais (45° e 90°)'
    return f'{d}: conexão desalinhada: {f["nome"]} num vértice de {ang:.1f}° (as pernas não seguem os tubos; peça comercial só de 45° e 90°)'


RX_FLEXIVEL = re.compile(r'PEAD|corrugad|flex', re.I)


def _flexivel(d, *regs):
    """eletroduto de elétrica/alarme ou tubo em material flexível (PEAD, corrugado): curva de até 30° no próprio tubo."""
    return d in FLEX or any(RX_FLEXIVEL.search(str(r['ps'].get('material') or r.get('material') or '')) for r in regs)


def _juncao(f):
    return (f['pred'] in ('JUNCTION', 'TEE', 'CROSS') or len(f.get('dirs') or []) >= 3
            or re.search(r'jun[cç]|\bt[eê]\b|deriva', f'{f["nome"]} {f.get("otype") or ""}', re.I) is not None)


def _curva(rv, d, f, ang, flex, arq, local, q):
    """mudança de direção com peça: devolve 1 se virou pendência. Peça com 'curvatura_no_tubo' em material flexível completa o ângulo no tubo
    (até 30°); peça marcada 'fora_do_comercial' em tubo rígido fica como observação (opção b provisória, decisão do Anderson pendente)."""
    if _comercial(ang) or _juncao(f): return 0                # tês e junções são peças comerciais (coordenação, 21/10/2026)
    a = _ang_peca(f)
    if flex and str(f['ps'].get('curvatura_no_tubo', '')).lower() == 'sim' and a is not None and abs(a - ang) <= 30.0:
        return 0
    if str(f['ps'].get('fora_do_comercial', '')).lower() == 'sim':
        rv.add('C6', 'OBSERVACAO', arq, local, _msg_angulo(d, f, ang) + ' — marcada "fora_do_comercial" pela entrega; aceita provisoriamente (opção b), decisão do Anderson pendente',
               'C6 ângulo da rede = 45° ou 90°', E=q[0], N=q[1])
        return 0
    rv.add('C6', 'PENDENCIA', arq, local, _msg_angulo(d, f, ang), 'C6 ângulo da rede = 45° ou 90°', E=q[0], N=q[1])
    return 1


def _comercial(ang, tol=3.0):                                 # mesma tolerância do preclash\conexoes.py ('tol': 3°)
    return min(abs(ang - c) for c in ANG_COMERCIAL) <= tol


def dist_planta(c, x, y):
    """distância em planta do ponto à caixa (negativa dentro): cilindro pelo raio, prisma girado pelos lados."""
    if c['forma'] == 'c':
        return float(math.hypot(x - c['E'], y - c['N']) - c['meia'])
    qx, qy = MD.planta_local(c, x, y)
    return float(max(qx, qy)) if (qx <= 0 and qy <= 0) else float(math.hypot(max(qx, 0), max(qy, 0)))


def caixa_no_ponto(cxs, q, folga_planta=0.10, folga_z=0.30):
    """caixas/equipamentos que contêm o ponto q (com folga)."""
    out = []
    for c in cxs:
        if dist_planta(c, q[0], q[1]) <= folga_planta and c['zb'] - folga_z <= q[2] <= c['zt'] + folga_z: out.append(c)
    return out


def _local(seg_ou_nome, q, cxs):
    """texto curto de localização: trecho + caixa mais próxima."""
    nome = seg_ou_nome if isinstance(seg_ou_nome, str) else (seg_ou_nome.get('trecho') or seg_ou_nome.get('nome'))
    perto = ''
    if cxs:
        d = [(math.hypot(c['E'] - q[0], c['N'] - q[1]), c) for c in cxs if c['reg']['classe'] == 'IfcDistributionChamberElement']
        if d:
            dm, c = min(d, key=lambda x: x[0])
            if dm < 25: perto = f', a {dm:.1f} m da {c["reg"]["nome"].split(":")[-1]}'
    return f'{nome}{perto}'


# ------------------------------------------------------------------------------------------------ B: informação
# Perfis de classe IFC (Anderson aprovou o 'revit' em 20/10/2026, 19h28). Revit 2025 decide a categoria só pela classe:
# IfcCableCarrierSegment/Fitting -> bandeja de cabos, IfcDistributionChamberElement/IfcCableFitting/IfcBuildingElementProxy -> modelo genérico.
# A classe da norma fica no Pset (classe_ifc_norma): não reprovar por ela.
PERFIS = {
    'revit': dict(
        seg={**{d: ('IfcPipeSegment',) for d in AGUA | GRAV}, **{d: ('IfcCableSegment',) for d in ELET}},
        fit={**{d: ('IfcPipeFitting',) for d in AGUA | GRAV}, **{d: ('IfcCableSegment',) for d in ELET}},
        cx={**{d: ('IfcJunctionBox',) for d in ELET}, **{d: ('IfcWasteTerminal', 'IfcInterceptor') for d in GRAV},
            **{d: ('IfcValve', 'IfcWasteTerminal', 'IfcInterceptor', 'IfcFlowMeter', 'IfcFireSuppressionTerminal') for d in AGUA}},
        proibidas={'IfcCableCarrierSegment': 'vira "bandeja de cabos" no Revit', 'IfcCableCarrierFitting': 'vira "conexão de bandeja de cabos" no Revit',
                   'IfcDistributionChamberElement': 'vira "modelo genérico" no Revit', 'IfcCableFitting': 'vira "modelo genérico" no Revit',
                   'IfcBuildingElementProxy': 'vira "modelo genérico" no Revit'},
        aviso={'IfcAlarm': 'vira "modelo genérico" no Revit'}),
    'norma': dict(
        seg={**{d: ('IfcPipeSegment',) for d in AGUA | GRAV}, **{d: ('IfcCableCarrierSegment',) for d in ELET}},
        fit={**{d: ('IfcPipeFitting',) for d in AGUA | GRAV}, **{d: ('IfcCableCarrierFitting',) for d in ELET}},
        cx={**{d: ('IfcJunctionBox', 'IfcDistributionChamberElement') for d in ELET}, **{d: ('IfcDistributionChamberElement', 'IfcInterceptor') for d in GRAV | AGUA}},
        proibidas={'IfcBuildingElementProxy': 'modelo genérico'}, aviso={}),
}
RX_CA_BL = re.compile(r'areia|boca de lobo|\bBL\b|BL-|grelha|ralo', re.I)


BARRILETE = ()      # prefixos de trecho do barrilete da escola (entregas.py: 'barrilete'), ex.: ('PCI-AF-',) na Jandaíra


def _barrilete(r):
    """tubo do barrilete/casa de bombas (acima do piso, fora do estudo de cota da rede enterrada)."""
    if BARRILETE and str(r.get('trecho') or r.get('nome') or '').startswith(tuple(BARRILETE)): return True
    return re.search(r'barrilete|casa de bombas', ' '.join(str(v) for v in r['ps'].values()), re.I) is not None


def _tem(ps, *chaves):
    return any(ps.get(k) not in (None, '') for k in chaves)


def conferir_informacao(rv, R, epsg=None, origem=None, perfil='revit', materiais=None):
    P = PERFIS[perfil]
    for arq, a in R['arquivos'].items():
        if not a['mapa'] or not a['crs']:
            rv.add('B1', 'PENDENCIA', arq, '-', 'sem IfcMapConversion/IfcProjectedCRS (não georreferenciado)', 'B1 georreferência')
        elif epsg and not any(str(epsg) in c for c in a['crs']):
            rv.add('B1', 'PENDENCIA', arq, '-', f'CRS {a["crs"]} diferente do EPSG:{epsg} da escola', 'B1 georreferência')
        elif origem and a['origem'] and math.hypot(a['origem'][0] - origem[0], a['origem'][1] - origem[1]) > 0.5:
            rv.add('B1', 'OBSERVACAO', arq, '-', f'origem da IfcMapConversion {a["origem"][:2]} diferente da origem registrada {origem[:2]}', 'B1 georreferência')
        else:
            rv.ev('B1', f'{arq}: {a["crs"][0]}, origem E {a["origem"][0]:.2f} / N {a["origem"][1]:.2f} / z {a["origem"][2]:.2f}')
    redes = [('segmento', s) for s in R['seg']] + [('conexão', f) for f in R['fit']] + [('caixa', c['reg']) for c in R['cx'] if c['camara']] \
        + [('equipamento', c['reg']) for c in R['cx'] if not c['camara']]
    # B2 classes do perfil
    erros = collections.defaultdict(list)
    for tipo, r in redes:
        d, k = r['disc'], r['classe']
        if k in P['proibidas']:
            erros[(r['arq'], f'{tipo} como {k} ({P["proibidas"][k]})')].append(r['trecho'] or r['nome'])
        elif tipo == 'segmento' and d in P['seg'] and k not in P['seg'][d]:
            erros[(r['arq'], f'{d}: segmento como {k} (perfil {perfil}: {"/".join(P["seg"][d])})')].append(r['trecho'])
        elif tipo == 'conexão' and d in P['fit'] and k not in P['fit'][d]:
            erros[(r['arq'], f'{d}: conexão como {k} (perfil {perfil}: {"/".join(P["fit"][d])})')].append(r['nome'])
        elif tipo == 'caixa' and d in P['cx'] and k not in P['cx'][d] and k != 'IfcTank':
            erros[(r['arq'], f'{d}: caixa como {k} (perfil {perfil}: {"/".join(P["cx"][d])})')].append(r['nome'])
    for (arq, msg), nomes in erros.items():
        rv.add('B2', 'PENDENCIA', arq, f'{len(nomes)} elementos (ex.: {", ".join(map(str, nomes[:3]))})', msg, f'B2 classe IFC (perfil {perfil})')
    avisos = collections.Counter((r['arq'], r['classe']) for t, r in redes if r['classe'] in P['aviso'])
    for (arq, k), n in avisos.items():
        rv.add('B2', 'OBSERVACAO', arq, f'{n} × {k}', f'{k} {P["aviso"][k]}', f'B2 classe IFC (perfil {perfil})')
    for arq, a in R['arquivos'].items():
        rv.ev('B2', f'{arq}: ' + ', '.join(f'{k}{"/" + p if p else ""} {n}' for (k, p), n in a['classes'].most_common(8)))
    sem_norma = [r for t, r in redes if t != 'equipamento' and not r['ps'].get('classe_ifc_norma')]
    if sem_norma and perfil == 'revit':
        rv.add('B2', 'OBSERVACAO', sem_norma[0]['arq'], f'{len(sem_norma)} elementos', 'classe da norma não gravada no Pset (classe_ifc_norma)', 'B2 classe da norma no Pset')
    # B3 PredefinedType (USERDEFINED com ObjectType vale)
    sem = collections.defaultdict(list)
    for tipo, r in redes:
        if r['pred'] in (None, 'NOTDEFINED') or (r['pred'] == 'USERDEFINED' and not r['otype']):
            sem[(r['arq'], r['classe'])].append(r['nome'])
    for (arq, k), nomes in sem.items():
        rv.add('B3', 'OBSERVACAO', arq, f'{len(nomes)} × {k} (ex.: {nomes[0]})', f'{k} sem PredefinedType (NOTDEFINED) ou USERDEFINED sem ObjectType', 'B3 tipo predefinido')
    # B4 material, B5 diâmetro, B6 sistema, B7 nome, B10 recobrimento do estudo
    testes = (
        ('B4', 'PENDENCIA', lambda t, r: t == 'segmento' and not (r['material'] or _tem(r['ps'], 'material', 'Material')), 'sem material'),
        ('B4', 'OBSERVACAO', lambda t, r: t in ('conexão', 'caixa') and not (r['material'] or _tem(r['ps'], 'material', 'Material')), 'sem material'),
        ('B5', 'PENDENCIA', lambda t, r: t in ('segmento', 'conexão') and not (r['diam'] or _tem(r['ps'], 'DN_mm', 'DE_mm', 'diametro', 'NominalDiameter')),
         'sem diâmetro'),
        ('B6', 'PENDENCIA', lambda t, r: not r['sist'][0], 'fora de qualquer sistema'),
        ('B6', 'PENDENCIA', lambda t, r: r['sist'][0] and r['sist'][1] != 'IfcDistributionSystem', 'sistema genérico (IfcSystem), não IfcDistributionSystem'),
        ('B6', 'PENDENCIA', lambda t, r: r['sist'][1] == 'IfcDistributionSystem' and r['disc'] in SIST_PRED and r['sist'][2] not in SIST_PRED[r['disc']],
         'IfcDistributionSystem com PredefinedType incompatível com a disciplina'),
        ('B7', 'PENDENCIA', lambda t, r: t != 'equipamento' and (not r['nome'] or re.fullmatch(r'[0-9A-Za-z_$]{22}', r['nome'] or '')), 'sem nome/código do projeto'),
        ('B10', 'PENDENCIA', lambda t, r: t == 'segmento' and r['disc'] in PRESS and not _tem(r['ps'], 'recobrimento_estudo', 'recobrimento_m') and not _barrilete(r),
         'pressurizada sem recobrimento_estudo no Pset'),
    )
    for item, nivel, teste, msg in testes:
        falhas = collections.defaultdict(list)
        for t, r in redes:
            try:
                if teste(t, r): falhas[(r['arq'], t)].append(r)
            except Exception:
                pass
        for (arq, t), rs in falhas.items():
            ex = ', '.join(sorted({str(r['trecho'] or r['nome']) for r in rs})[:3])
            rv.add(item, nivel, arq, f'{len(rs)} {t}(s) (ex.: {ex})', f'{t}: {msg}', f'{item} informação BIM')
    seg = [r for t, r in redes if t == 'segmento']
    # material pela legenda/memorial (Anderson, 21/10/2026), não pelo tipo de família do Revit
    regras_mat = dict(MATERIAL_LEGENDA, **(materiais or {}))
    errado = collections.defaultdict(list); suspeito = collections.defaultdict(list); por_disc = collections.defaultdict(collections.Counter)
    for r in seg:
        m = str(r['ps'].get('material') or r['material'] or '')
        if not m: continue
        por_disc[r['disc']][m] += 1
        if _barrilete(r): continue
        rx = regras_mat.get(r['disc'])
        if rx and not re.search(rx, m, re.I): errado[(r['arq'], r['disc'], m)].append(r)
        elif RX_MAT_REVIT.search(m): suspeito[(r['arq'], r['disc'], m)].append(r)
    for (arq, d, m), rs in errado.items():
        rv.add('B4', 'PENDENCIA', arq, f'{len(rs)} segmento(s) (ex.: {", ".join(sorted({str(r["trecho"]) for r in rs})[:3])})',
               f'{d}: material "{m}" diferente da legenda/memorial (esperado /{regras_mat[d]}/)', 'B4 material pela legenda/memorial')
    for (arq, d, m), rs in suspeito.items():
        rv.add('B4', 'OBSERVACAO', arq, f'{len(rs)} segmento(s)', f'{d}: material "{m}" parece tipo de família do Revit; conferir na legenda/memorial',
               'B4 material pela legenda/memorial')
    for d, c in sorted(por_disc.items()):
        rv.ev('B4', f'{d}: ' + '; '.join(f'{m} ({n})' for m, n in c.most_common(4)) + ' — conferir com a legenda da prancha e o memorial')
    rv.ev('B4', f'{sum(1 for r in seg if r["material"] or _tem(r["ps"], "material"))} de {len(seg)} segmentos com material '
                f'({sum(1 for r in seg if r["material"])} por IfcRelAssociatesMaterial, o que ajuda visualizadores neutros)')
    rv.ev('B5', f'{sum(1 for t, r in redes if t in ("segmento", "conexão") and (r["diam"] or _tem(r["ps"], "DN_mm", "DE_mm")))} de '
                f'{sum(1 for t, _ in redes if t in ("segmento", "conexão"))} segmentos/conexões com diâmetro')
    sis = sorted({(a, s, str(pp)) for arq, aa in R['arquivos'].items() for (a, s, pp) in aa['sistemas']})
    rv.ev('B6', 'sistemas: ' + '; '.join(f'{s} ({a}{" " + pp if pp != "None" else ""})' for a, s, pp in sis[:10]))
    rv.ev('B7', f'{sum(1 for t, r in redes if r["nome"])} de {len(redes)} peças com nome')
    press = [r for r in seg if r['disc'] in PRESS and not _barrilete(r)]
    rv.ev('B10', f'{sum(1 for r in press if _tem(r["ps"], "recobrimento_estudo", "recobrimento_m"))} de {len(press)} trechos pressurizados com recobrimento (recobrimento_estudo/recobrimento_m)')
    # B11 caixas ocas e B12 furo de passagem
    n_ok = n_ver = 0
    for c in R['cx']:
        if not c['camara'] or c['reg']['classe'] == 'IfcTank': continue
        r = c['reg']; ps = r['ps']; h = c['zt'] - c['zb']
        menor = 2 * c['meia'] if c['forma'] == 'c' else 2 * min(c.get('mx', c['meia']), c.get('my', c['meia']))
        if h < 0.30 or menor < 0.30: continue                    # caixa rasa/pequena pode ser maciça
        n_ver += 1
        oca = c.get('oca') or []
        ocos = [s for s in oca if 'Hollow' in s['perfil']]
        cheios = sorted([s for s in oca if 'Hollow' not in s['perfil']], key=lambda s: s['z0'])
        falta = []
        if not ocos: falta.append('paredes ocas')
        else:
            w = ocos[0]['parede']; circ = 'Circle' in ocos[0]['perfil']
            if circ and (w is None or abs(w - 0.08) > 0.005): falta.append(f'anel {w} m (0,08)')
            if not circ and (w is None or w > 0.105 or (menor >= 0.60 and abs(w - 0.10) > 0.005)): falta.append(f'parede {w} m (0,10)')
        if len(cheios) < 2: falta.append('fundo e tampa')
        else:
            if abs(cheios[0]['h'] - 0.10) > 0.005: falta.append(f'fundo {cheios[0]["h"]:.3f} m (0,10)')
            if abs(cheios[-1]['h'] - 0.05) > 0.005: falta.append(f'tampa {cheios[-1]["h"]:.3f} m (0,05)')
        if not _tem(ps, 'dimensao_interna'): falta.append('dimensão interna no Pset')
        if not _tem(ps, 'profundidade_util'): falta.append('profundidade útil no Pset')
        if r['disc'] in ('DRE', 'AP') and RX_CA_BL.search(f'{r["nome"]} {ps.get("tipo") or ""} {r["otype"] or ""}') \
                and 'grelha' not in str(ps.get('tampa') or '').lower():
            falta.append('grelha de FoFo (caixa de areia/boca de lobo)')
        if falta:
            rv.add('B11', 'PENDENCIA', r['arq'], f'{r["nome"]} — {coord(c["E"], c["N"])}', 'caixa: ' + ', '.join(falta), 'B11 caixa oca no padrão', E=c['E'], N=c['N'])
        else:
            n_ok += 1
    rv.ev('B11', f'{n_ok} de {n_ver} caixas (≥ 0,30 m) ocas no padrão (fundo 0,10, parede 0,10 ou anel 0,08, tampa 0,05, Pset com dimensão interna e profundidade útil)')
    if n_ver:
        rv.add('B12', 'OBSERVACAO', 'IFC', f'{n_ver} caixas', 'caixas sem furo de passagem dos tubos (a ferramenta ainda não faz; não reprova)', 'B12 furo de passagem')
    rv.ev('B13', 'abrir o federado no Revit 2025 (Abrir IFC, vista 3D na Fase 3) e num visualizador neutro: conferência do analista')
    # D9 escopo
    for t, r in redes:
        txt = f'{r["nome"]} {r["sist"][0]} {r.get("otype") or ""}'
        if RX_FORA_ESCOPO.search(txt):
            rv.add('D9', 'PENDENCIA', r['arq'], str(r['trecho'] or r['nome']), f'elemento fora do escopo do contrato: "{txt.strip()[:60]}"', 'D9 escopo')
    processo_interno(rv, R, redes)


def processo_interno(rv, R, redes):
    """B9: nome de ferramenta ou de pessoa = pendência; jargão de trabalho (estudo, ajuste, premissa, obstáculo) = observação."""
    graves = re.compile(r'preclash|pr[eé]-?compat|clash|daniel|claude|anderson', re.I)
    leves = re.compile(r'obst[aá]culo|\bestudo\b|\bajuste\b|premissa', re.I)
    for nivel, rx in (('PENDENCIA', graves), ('OBSERVACAO', leves)):
        proc = collections.defaultdict(lambda: collections.Counter())
        for t, r in redes + [('estrutura', e) for e in R['est']]:
            for k, v in r['ps'].items():
                if k == 'recobrimento_estudo' or k == 'grupo_estudo': continue      # nome de propriedade pedido pelo Anderson
                if rx.search(str(v)) and not (nivel == 'OBSERVACAO' and graves.search(str(v))): proc[r['arq']][f'{k}: {str(v)[:45]}'] += 1
            if rx.search(r['sist'][0] or '') and not (nivel == 'OBSERVACAO' and graves.search(r['sist'][0])): proc[r['arq']][f'sistema "{r["sist"][0]}"'] += 1
        for arq in R['arquivos']:
            for nome_ps in {n for n in _pset_nomes(R, arq) if rx.search(n)}:
                proc[arq][f'Pset "{nome_ps}"'] += 1
        for arq, c in proc.items():
            rv.add('B9', nivel, arq, f'{sum(c.values())} ocorrências',
                   ('nome de ferramenta/pessoa no IFC de entrega: ' if nivel == 'PENDENCIA' else 'jargão de trabalho no IFC de entrega: ')
                   + '; '.join(f'{k} ({v}×)' for k, v in c.most_common(4)), 'B9 IFC sem processo interno')
        if not proc and nivel == 'PENDENCIA': rv.ev('B9', 'nenhum nome de ferramenta ou pessoa nos Psets e sistemas')


# ------------------------------------------------------------------------------------------------ C: continuidade e conexões
def conferir_continuidade(rv, R, tol=0.02):
    seg, fit, cxs = R['seg'], R['fit'], R['cx']
    est_lo = np.array([e['lo'] for e in R['est']]) if R['est'] else np.zeros((0, 3))
    est_hi = np.array([e['hi'] for e in R['est']]) if R['est'] else np.zeros((0, 3))

    def perto_edificacao(q, d=1.0):
        if not len(est_lo): return False
        return bool(np.any(np.all((q[:2] >= est_lo[:, :2] - d) & (q[:2] <= est_hi[:, :2] + d), axis=1)))

    discs = sorted({s['disc'] for s in seg if s['disc']})
    n_ponta = n_folga = n_meio = n_curto = n_sobre = n_semcx = n_ang = n_desal = n_solta = n_dup = n_junc = 0
    for d in discs:
        S = [s for s in seg if s['disc'] == d]; Fd = [f for f in fit if f['disc'] == d]
        Fc = np.array([f['c'] for f in Fd]) if Fd else np.zeros((0, 3))
        # pontas -> nós
        pts = []; own = []
        for i, s in enumerate(S):
            pts += [s['P'][0], s['P'][-1]]; own += [(i, 0), (i, -1)]
        pts = np.array(pts); n = len(pts)
        pai = list(range(n))

        def raiz(a):
            while pai[a] != a: pai[a] = pai[pai[a]]; a = pai[a]
            return a
        for a in range(n):
            dd = np.linalg.norm(pts[a + 1:] - pts[a], axis=1)
            for b in np.nonzero(dd < tol)[0] + a + 1: pai[raiz(a)] = raiz(int(b))
        nos = collections.defaultdict(list)
        for a in range(n): nos[raiz(a)].append(a)
        # todos os vértices (para conexão no lugar) e pedaços (para "ligação no meio")
        verts = np.vstack([s['P'] for s in S]); pcs = [(a, b, i) for i, s in enumerate(S) for a, b in zip(s['P'][:-1], s['P'][1:])]
        A = np.array([p[0] for p in pcs]); B = np.array([p[1] for p in pcs]); Ii = np.array([p[2] for p in pcs])

        def direcao(i, ponta):
            P = S[i]['P']
            v = (P[1] - P[0]) if ponta == 0 else (P[-2] - P[-1])
            return v / max(np.linalg.norm(v), 1e-9)               # sai do nó para dentro do tubo

        def fitting_em(q, raio):
            if not len(Fc): return []
            k = np.nonzero(np.linalg.norm(Fc - q, axis=1) <= raio)[0]
            return [Fd[j] for j in k]

        ja = set()
        for raiz_, membros in nos.items():
            q = pts[membros].mean(0); deg = len(membros)
            cx = caixa_no_ponto(cxs, q)
            if cx: continue                                          # nó dentro de caixa/equipamento: sem peça
            elems = [own[m] for m in membros]
            if deg == 1:
                i, pt = elems[0]
                # ponta no meio de outro tubo da mesma disciplina?
                d_, C1, _ = CL.dist_seg_seg(np.repeat(q[None], len(A), 0), np.repeat(q[None], len(A), 0), A, B)
                d_[Ii == i] = 9
                fo = (fitting_em(q, max(0.05, 2 * S[i]['de']))
                      or [f for f in Fd if any(np.linalg.norm(pt - q) <= 0.01 for pt in (f.get('portas') or []))])
                outras = np.linalg.norm(pts - q, axis=1); outras[membros] = 9
                if fo:
                    continue                                         # termina numa conexão (junção/curva com o outro lado)
                if outras.min() < 0.30:
                    chave = tuple(np.round((q + pts[int(np.argmin(outras))]) / 2, 1))
                    if chave in ja: continue
                    ja.add(chave)
                    m_ = int(np.argmin(outras)); o_ = S[own[m_][0]]
                    P_ = S[i]['P']
                    if float(CL.dist_seg_seg(np.repeat(pts[m_][None], len(P_) - 1, 0), np.repeat(pts[m_][None], len(P_) - 1, 0), P_[:-1], P_[1:])[0].min()) <= 0.01:
                        continue                                     # a outra ponta nasce no próprio tubo (ramal na vertical dele)
                    if np.hypot(*(pts[m_][:2] - q[:2])) < 0.03 and outras.min() <= o_['de'] / 2 - S[i]['de'] / 2 + 0.005:
                        # ramal que entra no tubo maior abaixo/acima do eixo, dentro do diâmetro dele (cotas das pranchas): ligado
                        rv.add('C2', 'OBSERVACAO', S[i]['arq'], _local(S[i], q, cxs) + ' — ' + coord(*q[:2]),
                               f'{d}: ramal Ø{S[i]["de"] * 1000:.0f} chega {outras.min() * 100:.1f} cm fora do eixo do tubo Ø{o_["de"] * 1000:.0f}, dentro do diâmetro dele (cotas das pranchas)',
                               'C2 peças encostadas, sem folga', E=q[0], N=q[1])
                        continue
                    n_folga += 1
                    rv.add('C2', 'PENDENCIA', S[i]['arq'], _local(S[i], q, cxs) + ' — ' + coord(*q[:2]),
                           f'{d}: folga de {outras.min() * 100:.1f} cm entre duas peças da mesma rede (pontas não se encontram)', 'C2 peças encostadas, sem folga',
                           E=q[0], N=q[1])
                elif d_.min() < 0.03:
                    n_meio += 1
                    rv.add('C2', 'PENDENCIA', S[i]['arq'], _local(S[i], q, cxs) + ' — ' + coord(*q[:2]),
                           f'{d}: tubo chega no meio de outro tubo sem junção', 'C2/C6 ligação só com conexão (junção)', E=q[0], N=q[1])
                elif any(c['equip'] and dist_planta(c, q[0], q[1]) <= 0.30 for c in cxs):
                    rv.ev('C1', f'{d} {S[i]["trecho"]}: ponta sob equipamento (sobe para quadro/abrigo/bomba) {coord(*q[:2])}')
                elif perto_edificacao(q):
                    rv.ev('C1', f'{d} {S[i]["trecho"]}: ponta junto da estrutura da edificação (segue para o predial) {coord(*q[:2])}')
                else:
                    n_ponta += 1
                    rv.add('C1', 'OBSERVACAO', S[i]['arq'], _local(S[i], q, cxs) + ' — ' + coord(*q[:2]),
                           f'{d}: ponta sem destino no modelo (nem caixa, conexão, tubo, equipamento ou estrutura); conferir na prancha se entra em edificação',
                           'C1 rede contínua de caixa a caixa', E=q[0], N=q[1])
                continue
            dirs = [direcao(i, pt) for i, pt in elems]
            fo = fitting_em(q, 0.02)
            if deg == 2:
                ang = 180 - _desvio(dirs[0], dirs[1])
                flex = _flexivel(d, *[S[i] for i, _ in elems])
                if ang <= (30.0 if flex else FLEX.get(d, FLEX_PADRAO)): continue
                if not fo:
                    perto = fitting_em(q, 0.30)
                    n_semcx += 1
                    rv.add('C6', 'PENDENCIA', S[elems[0][0]]['arq'], _local(S[elems[0][0]], q, cxs) + ' — ' + coord(*q[:2]),
                           f'{d}: mudança de direção de {ang:.1f}° sem conexão no vértice' + (f' (há conexão a {np.linalg.norm(perto[0]["c"] - q) * 100:.0f} cm: desalinhada)' if perto else ''),
                           'C6 conexão comercial em toda mudança de direção', E=q[0], N=q[1])
                else:
                    n_ang += _curva(rv, d, fo[0], ang, flex, fo[0]['arq'], _local(S[elems[0][0]], q, cxs) + ' — ' + coord(*q[:2]), q)
            else:
                junc = [f for f in fo if (f['pred'] in ('JUNCTION', 'TEE', 'CROSS', 'OBSTRUCTION') or len(f['dirs']) >= 3)]
                if not junc:
                    n_junc += 1
                    rv.add('C6', 'PENDENCIA', S[elems[0][0]]['arq'], _local(S[elems[0][0]], q, cxs) + ' — ' + coord(*q[:2]),
                           f'{d}: {deg} tubos se encontram fora de caixa sem junção (tê)', 'C6 nó com 3+ tubos = junção', E=q[0], N=q[1])
        # vértices internos (curva dentro do próprio elemento)
        for i, s in enumerate(S):
            P = s['P']
            for k in range(1, len(P) - 1):
                u = P[k] - P[k - 1]; v = P[k + 1] - P[k]
                if np.linalg.norm(u) < 1e-6 or np.linalg.norm(v) < 1e-6: continue
                ang = _desvio(u / np.linalg.norm(u), v / np.linalg.norm(v))
                flex = _flexivel(d, s)
                if ang <= (30.0 if flex else FLEX.get(d, FLEX_PADRAO)) or caixa_no_ponto(cxs, P[k]): continue
                fo = fitting_em(P[k], 0.02)
                if not fo:
                    n_semcx += 1
                    rv.add('C6', 'PENDENCIA', s['arq'], _local(s, P[k], cxs) + ' — ' + coord(*P[k][:2]),
                           f'{d}: curva de {ang:.1f}° no meio do tubo sem conexão', 'C6 conexão comercial em toda mudança de direção', E=P[k][0], N=P[k][1])
                else:
                    n_ang += _curva(rv, d, fo[0], ang, flex, s['arq'], _local(s, P[k], cxs) + ' — ' + coord(*P[k][:2]), P[k])
        # C5 conexões: no lugar, alinhadas, sem duplicata
        for j, f in enumerate(Fd):
            dmin = float(np.min(np.linalg.norm(verts - f['c'], axis=1))) if len(verts) else 9
            if dmin > 0.30:
                n_solta += 1
                rv.add('C5', 'PENDENCIA', f['arq'], f'{f["nome"]} ({f["ps"].get("trechos", "")[:40]}) — {coord(*f["c"][:2])}',
                       f'{d}: conexão solta, a {dmin:.2f} m do tubo mais próximo', 'C5 conexão no vértice da rede', E=f['c'][0], N=f['c'][1])
            elif dmin > 0.01 and len(f.get('portas') or []) >= 2 and all(
                    float(np.min(np.linalg.norm(verts - q, axis=1))) <= 0.01 for q in f['portas']):
                pass                                                 # conexão por porta (tubo termina na boca da peça, como no Revit)
            elif dmin > 0.01 and f.get('lo') is not None and sum(
                    1 for q in pts if np.all(q >= f['lo'] - 0.01) and np.all(q <= f['hi'] + 0.01)) >= 2:
                pass                                                 # peça em malha (conexão do Revit): duas pontas de tubo dentro dela
            elif dmin > 0.01 and len(A) and float(CL.dist_seg_seg(np.repeat(f['c'][None], len(A), 0), np.repeat(f['c'][None], len(A), 0), A, B)[0].min()) <= 0.01:
                pass                                                 # tê/junção sobre o eixo de um tubo contínuo
            elif dmin > 0.01:
                n_desal += 1
                rv.add('C5', 'PENDENCIA', f['arq'], f'{f["nome"]} ({f["ps"].get("trechos", "")[:40]}) — {coord(*f["c"][:2])}',
                       f'{d}: conexão deslocada {dmin * 100:.1f} cm do vértice dos tubos', 'C5 conexão no vértice da rede', E=f['c'][0], N=f['c'][1])
            else:
                # pernas alinhadas com os tubos que chegam no vértice
                k = np.nonzero(np.linalg.norm(verts - f['c'], axis=1) <= 0.01)[0]
                tdirs = []
                for s in S:
                    for m in range(len(s['P'])):
                        # inclui a ponta do outro lado de uma folga (a folga é C2) e o ramal que entra no tubo maior fora do eixo, dentro do
                        # diâmetro dele (junção Ø280 com o ramal Ø40 10 cm abaixo do eixo)
                        if np.linalg.norm(s['P'][m] - f['c']) <= max(0.10, f['de'] / 2 - s['de'] / 2 + 0.005) and np.hypot(*(s['P'][m][:2] - f['c'][:2])) <= 0.10:
                            for nb in (m - 1, m + 1):
                                if 0 <= nb < len(s['P']):
                                    v = s['P'][nb] - s['P'][m]; tdirs.append(v / max(np.linalg.norm(v), 1e-9))
                # tubo contínuo que passa pela peça (tê/junção no meio dele): as duas direções dele também valem
                if len(A):
                    dd_, _, _ = CL.dist_seg_seg(np.repeat(f['c'][None], len(A), 0), np.repeat(f['c'][None], len(A), 0), A, B)
                    for j_ in np.nonzero(dd_ <= max(0.01, f['de'] / 2))[0]:
                        u_ = B[j_] - A[j_]; nu = np.linalg.norm(u_)
                        if nu > 1e-6 and min(np.linalg.norm(A[j_] - f['c']), np.linalg.norm(B[j_] - f['c'])) > 0.05:
                            tdirs += [u_ / nu, -u_ / nu]
                for v in f['dirs']:
                    if tdirs and min(_desvio(v, t) for t in tdirs) > 3:
                        n_desal += 1
                        rv.add('C5', 'PENDENCIA', f['arq'], f'{f["nome"]} — {coord(*f["c"][:2])}',
                               f'{d}: perna da conexão desalinhada {min(_desvio(v, t) for t in tdirs):.0f}° do tubo', 'C5 conexão alinhada com os tubos',
                               E=f['c'][0], N=f['c'][1])
                        break
            for g in Fd[j + 1:]:
                if np.linalg.norm(g['c'] - f['c']) < 0.5 * max(f['de'], g['de']):
                    n_dup += 1
                    rv.add('C4', 'PENDENCIA', f['arq'], f'{f["nome"]} × {g["nome"]} — {coord(*f["c"][:2])}',
                           f'{d}: duas conexões sobrepostas no mesmo ponto', 'C4 sem peças sobrepostas', E=f['c'][0], N=f['c'][1])
        # C3 segmentos curtos
        for s in S:
            Lmin = max(0.10, 3.0 * s['de'])
            if s['L'] >= Lmin: continue
            if _barrilete(s):
                rv.ev('C3', f'{d} {s["trecho"]}: niple de {s["L"] * 100:.0f} cm no barrilete (entre válvulas/conexões, acima do piso)'); continue
            a_cx = caixa_no_ponto(cxs, s['P'][0]); b_cx = caixa_no_ponto(cxs, s['P'][-1])
            if a_cx and b_cx: continue
            n_curto += 1
            q = s['P'].mean(0)
            rv.add('C3', 'PENDENCIA', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{d}: pedaço de tubo de {s["L"] * 100:.0f} cm (menor que a conexão, mín. {Lmin * 100:.0f} cm)', 'C3 sem segmento menor que a conexão',
                   E=q[0], N=q[1])
        # C4 tubos sobrepostos (colineares)
        for k in range(len(A)):
            u = B[k] - A[k]; Lu = np.linalg.norm(u); u = u / Lu
            lo = np.minimum(A[k], B[k]) - 0.01; hi = np.maximum(A[k], B[k]) + 0.01
            cand = np.nonzero(np.all(np.minimum(A, B) <= hi, 1) & np.all(np.maximum(A, B) >= lo, 1) & (np.arange(len(A)) > k))[0]
            for m in cand:
                v = B[m] - A[m]; Lv = np.linalg.norm(v)
                if Lv < 1e-6 or abs(np.dot(u, v / Lv)) < 0.9995: continue
                dd, _, _ = CL.dist_seg_seg(A[k][None], B[k][None], A[m][None], B[m][None])
                if dd[0] > 0.005: continue
                ta = sorted([0.0, Lu]); tb = sorted([np.dot(A[m] - A[k], u), np.dot(B[m] - A[k], u)])
                sob = min(ta[1], tb[1]) - max(ta[0], tb[0])
                if sob > 0.02:
                    n_sobre += 1; q = A[k] + u * (max(ta[0], tb[0]) + sob / 2)
                    rv.add('C4', 'PENDENCIA', S[Ii[k]]['arq'], f'{S[Ii[k]]["trecho"]} × {S[Ii[m]]["trecho"]} — {coord(*q[:2])}',
                           f'{d}: dois tubos sobrepostos em {sob * 100:.0f} cm', 'C4 sem peças sobrepostas', E=q[0], N=q[1])
        rv.ev('C1', f'{d}: {len(S)} segmentos, {len(Fd)} conexões, {len(nos)} pontas/nós')
    rv.ev('C2', f'{n_folga} folgas entre peças, {n_meio} ligações no meio do tubo')
    rv.ev('C3', f'{n_curto} segmentos menores que a conexão')
    rv.ev('C4', f'{n_sobre} tubos sobrepostos, {n_dup} conexões duplicadas')
    rv.ev('C5', f'{n_solta} conexões soltas, {n_desal} deslocadas/desalinhadas')
    rv.ev('C6', f'{n_semcx} mudanças de direção sem conexão, {n_ang} fora do ângulo comercial, {n_junc} nós sem junção')
    rv.ev('C1', f'{n_ponta} pontas soltas')


# ------------------------------------------------------------------------------------------------ D: regras de compatibilização
def conferir_regras(rv, R, T, prof_max, excecoes=(), declaradas=(), cob_min=0.30, folga=0.20, nao_reais=()):
    seg, cxs, est = R['seg'], R['cx'], R['est']
    ccam = [c for c in cxs if c['camara']]

    def isento(d, prof):
        for e in excecoes:
            if d in e.get('disc', ()) and prof <= e.get('ate', 99): return e
        return None

    # D1/D2/D3 por segmento
    maxd = collections.defaultdict(float); fundos = []; rasos = []; degraus = []; plats = 0; varia = []
    for s in seg:
        d = s['disc']
        if d not in PRESS and d not in GRAV: continue
        if _barrilete(s): continue                             # barrilete: acima do piso da casa de bombas
        r = s['de'] / 2; P = s['P']
        Q = CL.amostra(P, 0.5); z = T.z(Q[:, :2]) if T else np.full(len(Q), np.nan)
        longe = np.array([not caixa_no_ponto(cxs, q, 0.6, 1.0) for q in Q])
        ok = np.isfinite(z) & longe
        if ok.any():
            prof = z[ok] - (Q[ok, 2] + r)
            j = int(np.argmax(prof)); maxd[d] = max(maxd[d], float(prof[j]))
            if prof[j] > prof_max + 0.02:
                fundos.append((s, float(prof[j]), Q[ok][j]))
            if d in PRESS and prof.min() < cob_min - 0.02:
                k = int(np.argmin(prof)); rasos.append((s, float(prof[k]), Q[ok][k]))
            if d in PRESS and ok.sum() >= 3 and np.ptp(prof) > 0.25:
                varia.append((s, float(np.ptp(prof)), Q[ok][int(np.argmax(prof))]))
        if d in PRESS:
            for a, b in zip(P[:-1], P[1:]):
                dxy = math.hypot(*(b[:2] - a[:2])); dz = abs(b[2] - a[2])
                if dz < 0.03 or dz < dxy: continue
                m = (a + b) / 2
                if caixa_no_ponto(cxs, m, 0.15, 0.5): continue
                za, zb_ = (T.z(np.array([a[:2], b[:2]])) if T else (np.nan, np.nan))
                if np.isfinite(za) and np.isfinite(zb_) and abs((za - a[2]) - (zb_ - b[2])) <= 0.10:
                    plats += 1; continue
                degraus.append((s, dz, dxy, m))
    for s, p, q in fundos:
        e = isento(s['disc'], p)
        if e:
            rv.add('D1', 'OBSERVACAO', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{s["disc"]}: topo a {p:.2f} m (acima de {prof_max:.2f}), aceito: {e["fonte"]}', 'D1 profundidade máxima', E=q[0], N=q[1])
        elif s['disc'] in GRAV:
            rv.add('D1', 'OBSERVACAO', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{s["disc"]}: topo a {p:.2f} m (acima de {prof_max:.2f}) pela cota do projeto (gravidade)', 'D1 profundidade máxima', E=q[0], N=q[1])
        else:
            rv.add('D1', 'PENDENCIA', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{s["disc"]}: topo a {p:.2f} m de profundidade (máximo {prof_max:.2f} m)', 'D1 profundidade máxima', E=q[0], N=q[1])
    rv.ev('D1', 'maior profundidade (terreno ao topo) por disciplina: ' + ', '.join(f'{d} {v:.2f} m' for d, v in sorted(maxd.items())) + f' (máximo da escola {prof_max:.2f} m)')
    for s, p, q in rasos:
        if p < 0:
            rv.add('D2', 'PENDENCIA', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{s["disc"]}: tubo/eletroduto acima do terreno (topo {-p * 100:.0f} cm acima do terreno do IFC)', 'D2 recobrimento mínimo (rede enterrada)', E=q[0], N=q[1])
        else:
            rv.add('D2', 'OBSERVACAO', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
                   f'{s["disc"]}: recobrimento de {p:.2f} m (mínimo de referência {cob_min:.2f} m; conferir a nota do projeto)', 'D2 recobrimento mínimo', E=q[0], N=q[1])
    rv.ev('D2', f'{len(rasos)} trechos pressurizados com recobrimento < {cob_min:.2f} m longe de caixa')
    for s, dz, dxy, m in degraus:
        rv.add('D3', 'PENDENCIA', s['arq'], _local(s, m, cxs) + ' — ' + coord(*m[:2]),
               f'{s["disc"]}: degrau em Z de {dz:.2f} m em {dxy:.2f} m fora de caixa', 'D3 cota só muda na caixa', E=m[0], N=m[1])
    for s, v, q in varia:
        rv.add('D3', 'OBSERVACAO', s['arq'], _local(s, q, cxs) + ' — ' + coord(*q[:2]),
               f'{s["disc"]}: recobrimento varia {v:.2f} m ao longo do trecho (sem caixa); conferir se é mergulho', 'D3 cota só muda na caixa', E=q[0], N=q[1])
    rv.ev('D3', f'{len(degraus)} degraus fora de caixa; {plats} subidas/descidas acompanhando o terreno (transição de platô); {len(varia)} trechos com recobrimento variando > 0,25 m')
    # D4 elétrica acima da água
    PE = [(a, b, s) for s in seg if s['disc'] in ELET for a, b in zip(s['P'][:-1], s['P'][1:])]
    PA = [(a, b, s) for s in seg if s['disc'] in AGUA for a, b in zip(s['P'][:-1], s['P'][1:])]
    abaixo = 0; ncruz = 0
    if PE and PA:
        A2 = np.array([p[0] for p in PA]); B2 = np.array([p[1] for p in PA])
        lo2 = np.minimum(A2, B2)[:, :2]; hi2 = np.maximum(A2, B2)[:, :2]
        for a1, b1, s1 in PE:
            lo1 = np.minimum(a1, b1)[:2]; hi1 = np.maximum(a1, b1)[:2]
            cand = np.nonzero(np.all(lo2 <= hi1, 1) & np.all(hi2 >= lo1, 1))[0]
            if not len(cand): continue
            # cruzamento em planta: interseção dos segmentos 2D
            for k in cand:
                a2, b2 = A2[k], B2[k]
                d1 = b1[:2] - a1[:2]; d2 = b2[:2] - a2[:2]; den = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(den) < 1e-9: continue
                w = a2[:2] - a1[:2]; t = (w[0] * d2[1] - w[1] * d2[0]) / den; u_ = (w[0] * d1[1] - w[1] * d1[0]) / den
                if not (0 <= t <= 1 and 0 <= u_ <= 1): continue
                ncruz += 1
                z1 = a1[2] + t * (b1[2] - a1[2]); z2 = a2[2] + u_ * (b2[2] - a2[2]); q = a1 + t * (b1 - a1)
                if z1 < z2 and _barrilete(PA[k][2]):
                    # barrilete na cota do modelo (fora do estudo de cota): a elétrica não tem como passar por cima com o
                    # recobrimento mínimo dela; vai como observação para a decisão do Anderson (Alagoinhas, EL2-022 × AF-02)
                    s2 = PA[k][2]
                    rv.add('D4', 'OBSERVACAO', s1['arq'], f'{s1["trecho"]} × {s2["trecho"]} — {coord(*q[:2])}',
                           f'{s1["disc"]} passa {z2 - z1:.2f} m abaixo do barrilete ({s2["disc"]}, cota do modelo, fora do estudo)', 'D4 elétrica sempre acima da água', E=q[0], N=q[1])
                elif z1 < z2:
                    abaixo += 1; s2 = PA[k][2]
                    rv.add('D4', 'PENDENCIA', s1['arq'], f'{s1["trecho"]} × {s2["trecho"]} — {coord(*q[:2])}',
                           f'{s1["disc"]} passa {z2 - z1:.2f} m abaixo da água ({s2["disc"]})', 'D4 elétrica sempre acima da água', E=q[0], N=q[1])
    rv.ev('D4', f'{ncruz} cruzamentos elétrica × água em planta, {abaixo} com a elétrica por baixo')
    # D5 caixas
    pontas = [(s['P'][0], s) for s in seg] + [(s['P'][-1], s) for s in seg]
    n_fora = 0
    for c in ccam:
        nome = c['reg']['nome']
        zt_ = T.z(np.array([[c['E'], c['N']]]))[0] if T else np.nan
        if np.isfinite(zt_) and abs(c['zt'] - zt_) > 0.05:
            n_fora += 1
            rv.add('D5', 'PENDENCIA', c['reg']['arq'], f'{nome} — {coord(c["E"], c["N"])}',
                   f'tampa {"enterrada" if c["zt"] < zt_ else "sobrando"} {abs(c["zt"] - zt_) * 100:.0f} cm em relação ao terreno', 'D5 tampa no terreno (±5 cm)',
                   E=c['E'], N=c['N'])
        cheg = [(q, s) for q, s in pontas if dist_planta(c, q[0], q[1]) <= 0.10 and c['zb'] - 0.5 <= q[2] <= c['zt'] + 0.5]
        if not cheg and 'reservat' not in str(c['reg']['ps'].get('tipo', '')).lower():
            rv.add('D5', 'OBSERVACAO', c['reg']['arq'], f'{nome} — {coord(c["E"], c["N"])}', 'caixa sem nenhum tubo chegando', 'D5 caixa sem sobra', E=c['E'], N=c['N'])
        for q, s in cheg:
            fundo_tubo = q[2] - s['de'] / 2
            if fundo_tubo < c['zb'] - 0.02:
                canal = 'canaleta' in str(c['reg']['ps'].get('tipo', '')).lower() or 'CAN' in nome.upper()
                do_projeto = c['disc'] in GRAV and s['disc'] in GRAV    # gravidade: CT/CF e GI são as das pranchas (regra do projeto)
                if canal or do_projeto:
                    rv.add('D5', 'OBSERVACAO', c['reg']['arq'], f'{nome} × {s["trecho"]} — {coord(c["E"], c["N"])}',
                           f'tubo chega {(c["zb"] - fundo_tubo) * 100:.0f} cm abaixo do fundo da caixa'
                           + (' (as duas cotas vêm das pranchas: incompatibilidade do projeto original, levar ao projetista se ainda não estiver nas fichas)' if do_projeto else ''),
                           'D5 fundo da caixa abaixo do tubo mais fundo', E=c['E'], N=c['N'])
                else:
                    rv.add('D5', 'PENDENCIA', c['reg']['arq'], f'{nome} × {s["trecho"]} — {coord(c["E"], c["N"])}',
                           f'tubo chega {(c["zb"] - fundo_tubo) * 100:.0f} cm abaixo do fundo da caixa', 'D5 fundo da caixa abaixo do tubo mais fundo',
                           E=c['E'], N=c['N'])
    rv.ev('D5', f'{len(ccam)} caixas conferidas, {n_fora} com a tampa fora do terreno')
    # D8 reservatório
    tanques = [c for c in cxs if c['reg']['classe'] == 'IfcTank']
    rv.ev('D8', f'{len(tanques)} reservatório(s) IfcTank: ' + ', '.join(c['reg']['nome'] for c in tanques))
    # D6 clash independente
    clash_independente(rv, R, declaradas, folga, nao_reais)


def clash_independente(rv, R, declaradas=(), folga=0.20, nao_reais=()):
    seg, cxs, est = R['seg'], R['cx'], R['est']
    PC = pecas(seg)
    if not PC: return
    A = np.array([p[0] for p in PC]); B = np.array([p[1] for p in PC]); Rr = np.array([p[2] for p in PC]); I = np.array([p[3] for p in PC])
    D = np.array([seg[i]['disc'] or '?' for i in I])
    lo = np.minimum(A, B) - Rr[:, None] - folga; hi = np.maximum(A, B) + Rr[:, None] + folga
    crit = []; atenc = 0

    def declarada(*nomes):
        return any(any(dcl in str(n) for dcl in declaradas) for n in nomes)

    def ligacao(i, j, q):
        si, sj = seg[i], seg[j]
        if si['disc'] in GRAV and sj['disc'] in GRAV:
            for s in (si, sj):
                if min(np.linalg.norm(s['P'][0] - q), np.linalg.norm(s['P'][-1] - q)) < 0.8: return True
        return False
    feitos = set()
    for k in range(len(A)):
        cand = np.nonzero(np.all(lo <= hi[k], 1) & np.all(hi >= lo[k], 1) & (np.arange(len(A)) > k) & (D != D[k]))[0]
        if not len(cand): continue
        dd, C1, C2 = CL.dist_seg_seg(np.repeat(A[k][None], len(cand), 0), np.repeat(B[k][None], len(cand), 0), A[cand], B[cand])
        f = dd - Rr[k] - Rr[cand]
        for m, fm, c1 in zip(cand, f, C1):
            if fm >= folga: continue
            i, j = int(I[k]), int(I[m])
            if (i, j) in feitos: continue
            if ligacao(i, j, c1) or caixa_no_ponto(cxs, c1, 0.0, 0.0): continue
            feitos.add((i, j))
            if fm < -0.002: crit.append(('rede × rede', seg[i], seg[j]['trecho'], seg[j]['disc'], fm, c1))
            else: atenc += 1
    # rede × caixa de outra disciplina
    for c in cxs:
        Lo = np.array([c['E'] - c['meia'], c['N'] - c['meia'], c['zb']]); Hi = np.array([c['E'] + c['meia'], c['N'] + c['meia'], c['zt']])
        cand = np.nonzero(np.all(lo <= Hi, 1) & np.all(hi >= Lo, 1) & (D != c['disc']))[0]
        vistos = set()
        for m in cand:
            i = int(I[m])
            if i in vistos: continue
            Q = CL.amostra(np.array([A[m], B[m]]), 0.02)
            sd = CL.sd_caixa(Q, c) - Rr[m]
            j = int(np.argmin(sd))
            if sd[j] >= -0.002: continue
            s = seg[i]
            # chegada na caixa (ponta do tubo dentro dela) entre redes por gravidade = ligação
            dentro_ponta = any(dist_planta(c, q[0], q[1]) <= 0.10 for q in (s['P'][0], s['P'][-1]))
            if dentro_ponta and (s['disc'] in GRAV or c['equip']): continue
            vistos.add(i)
            crit.append(('rede × caixa', s, c['reg']['nome'], c['disc'], float(sd[j]), Q[j]))
    # rede × estrutura pela malha real
    n_est = 0
    for e in est:
        cand = np.nonzero(np.all(lo <= e['hi'], 1) & np.all(hi >= e['lo'], 1))[0]
        porseg = collections.defaultdict(list)
        for m in cand: porseg[int(I[m])].append(m)
        for i, ms in porseg.items():
            P = np.vstack([CL.amostra(np.array([A[m], B[m]]), 0.02) for m in ms])
            P = P[np.all((P >= e['lo'] - 0.5) & (P <= e['hi'] + 0.5), 1)]
            if not len(P): continue
            n_est += 1
            fm, q = folga_malha(P, seg[i]['de'] / 2, e)
            if q is not None and fm < -0.002:
                crit.append(('rede × estrutura', seg[i], e['nome'] or e['classe'], 'EST', fm, q))
    # a estrutura do IFC é a forma real ou só a caixa envolvente (prisma de 12 triângulos)?
    prisma = bool(est) and all(len(e['F']) <= 12 for e in est)
    if prisma:
        rv.add('D6', 'PENDENCIA', est[0]['arq'], f'{len(est)} peças',
               'a estrutura de referência no IFC é só a caixa envolvente (prisma) de cada peça, não a forma real (ex.: sapata cônica): '
               'quem abrir o federado vê colisões que a forma real descarta; exportar a forma real ou avisar no LEIA-ME e listar essas falsas colisões',
               'D6 clash contra a forma real da estrutura')
    n_decl = 0
    for tipo, s, outro, d2, fm, q in crit:
        base = 'caixa envolvente' if (prisma and d2 == 'EST') else 'forma real' if d2 == 'EST' else 'modelo'
        fonte_nr = next((n for n in nao_reais if n.split(':')[0] in (s['trecho'], s['nome'])), None)
        if declarada(s['trecho'], outro):
            n_decl += 1
            rv.add('D6', 'OBSERVACAO', s['arq'], f'{s["trecho"]} × {outro} — {coord(*q[:2])}',
                   f'{tipo}: {s["disc"]} × {d2} com {-fm * 100:.1f} cm de interferência na {base} (declarada nas pendências da entrega)', 'D6 clash',
                   E=q[0], N=q[1])
        elif fonte_nr and d2 == 'EST':
            rv.add('D6', 'OBSERVACAO', s['arq'], f'{s["trecho"]} × {outro} — {coord(*q[:2])}',
                   f'{tipo}: {-fm * 100:.1f} cm na {base}; pela forma real não é colisão ({fonte_nr.split(":", 1)[-1] if ":" in fonte_nr else "conferência da escola"})',
                   'D6 clash contra a forma real da estrutura', E=q[0], N=q[1])
        else:
            rv.add('D6', 'PENDENCIA', s['arq'], f'{s["trecho"]} × {outro} — {coord(*q[:2])}',
                   f'{tipo}: {s["disc"]} × {d2} com {-fm * 100:.1f} cm de interferência na {base}, não declarada', 'D6 clash (forma real)', E=q[0], N=q[1])
    rv.ev('D6', f'{len(crit)} colisões críticas ({n_decl} declaradas), {atenc} folgas curtas (< {folga:.2f} m) rede × rede; {n_est} pares tubo × peça da estrutura medidos '
                + ('na caixa envolvente (o IFC não traz a forma real)' if prisma else 'na malha do IFC'))


def conferir(rv, arquivos, sigla, cache_terreno, epsg=None, origem=None, excecoes=(), declaradas=(), so_info=False, log=print, perfil='revit'):
    from preclash import parametros as PAR
    R = ler(arquivos, log=log)
    conferir_informacao(rv, R, epsg, origem, perfil)
    if so_info: return R
    T = terreno(R, cache_terreno)
    if T is None: rv.add('D1', 'PENDENCIA', 'IFC', '-', 'sem terreno (IfcGeographicElement) nos IFC lidos', 'D terreno no IFC')
    conferir_continuidade(rv, R)
    conferir_regras(rv, R, T, PAR.prof_max(sigla), excecoes, declaradas)
    return R


if __name__ == '__main__':
    import glob, argparse
    ap = argparse.ArgumentParser(); ap.add_argument('alvo', nargs='+'); ap.add_argument('--sigla', default='XXX')
    a = ap.parse_args()
    arqs = [g for x in a.alvo for g in (glob.glob(os.path.join(x, '*.ifc')) if os.path.isdir(x) else [x])]
    arqs = [x for x in arqs if 'FEDERADO' not in os.path.basename(x).upper()]
    rv = Revisao('teste', a.sigla)
    conferir(rv, arqs, a.sigla, os.path.join(os.environ.get('TEMP', '.'), f'rev_terreno_{a.sigla}.npz'))
    for x in rv.achados: print(x.item, x.nivel, x.onde, '|', x.local, '|', x.problema)
    for k, v in rv.evidencias.items(): print(k, v)
