# -*- coding: utf-8 -*-
"""Passo 5 — junta tudo num só IFC4: IfcProject > IfcSite (terreno) > uma IfcBuilding por módulo (+ Implantação e URB).
Fontes: redes externas compatibilizadas (Implantação), estrutura as built (separada por módulo pelo "sistema" do Dados_ETIB),
arquitetura dos módulos (p1), divisa e reservatórios (p2), urbanização do RVT (p3), terreno e pisos externos (p4).
Tira as propriedades de trabalho e os "Grupo de modelos" do Revit; limpeza final (relações vazias, GUID repetido...).
A junção (ifcpatch MergeProjects) é a parte demorada: com FED_CACHE=arquivo.ifc ela é gravada e reaproveitada na próxima
rodada (apagar o cache quando qualquer fonte mudar).
Uso: python p5_montar.py escola.json R00   -> saida/<SIGLA>_FEDERADO-UNICO_<REV>.ifc"""
import os, sys, collections, tempfile, ifcopenshell, ifcopenshell.api, ifcopenshell.guid, ifcopenshell.util.element as ue, ifcpatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg, REV):
    sig = cfg['sigla']; OUT = ef.pasta(cfg, 'saida')
    EDIF = {'IMP': cfg.get('nome_implantacao', 'Implantação — redes externas'), **{k: m['nome'] for k, m in cfg['modulos'].items()},
            **{k: n for k, n in cfg.get('edificacoes_extra', {}).items()}, 'URB': cfg.get('nome_urbanizacao', 'URB — Urbanização: divisa, reservatórios, platôs, pisos externos e piso tátil')}
    FONTES = [(ef.caminho(cfg, x), 'IMP', 'Implantação', None) for x in cfg['redes']]
    FONTES += [(ef.caminho(cfg, x['arquivo']), x.get('modulo', 'EST'), x.get('prefixo', 'Módulos'), x) for x in cfg.get('estrutura', [])]
    FONTES += [(fn, x['modulo'], x['modulo'], None) for fn, x in ef.estruturas_rvt(cfg)]   # estrutura dos RVT (p1)
    FONTES += [(ef.saida_urb(cfg, 'TERRENO'), 'SITE', '', None)]
    FONTES += [(ef.saida_modulo(cfg, k), k, k, None) for k in cfg['modulos']]
    FONTES += [(ef.saida_urb(cfg, n), 'URB', 'URB', None) for n in ('DIVISA', 'PISOS', 'URB_RVT') if os.path.exists(ef.saida_urb(cfg, n))]
    falta = [fn for fn, *_ in FONTES if not os.path.exists(fn)]
    if falta: sys.exit('faltam fontes: ' + ', '.join(falta))
    # ---------- 1. cópias filtradas ----------
    tmp = tempfile.mkdtemp(); prep = []; MOD = {}; VISTOS = set()
    for fn, mod, pref, est in FONTES:
        f = ifcopenshell.open(fn); n_t = n_p = 0
        if est:   # estrutura: sistemas que vêm de outro arquivo saem; o resto vai para o módulo do sistema
            n_t = ef.remover(f, lambda e: e.is_a('IfcElement') and ue.get_psets(e).get('Dados_ETIB', {}).get('sistema') in est.get('excluir_sistemas', []))
        for ps in f.by_type('IfcPropertySet'):
            hp = list(ps.HasProperties or []); fica = [p for p in hp if p.Name not in ef.TIRAR_PROPS]
            if len(fica) != len(hp):
                ps.HasProperties = fica; n_p += len(hp) - len(fica)
                for p in hp:
                    if p.Name in ef.TIRAR_PROPS and not f.get_inverse(p): f.remove(p)
        for e in f.by_type('IfcRoot'):   # GUID já usado por outra fonte (módulos padrão copiados do mesmo modelo): GUID novo, senão o módulo se confunde
            if e.GlobalId in VISTOS: e.GlobalId = ifcopenshell.guid.new()
            VISTOS.add(e.GlobalId)
        for e in f.by_type('IfcElement') + f.by_type('IfcSpace'):
            sis = ue.get_psets(e).get('Dados_ETIB', {}).get('sistema')
            MOD[e.GlobalId] = 'SITE' if mod == 'SITE' else (est.get('modulo_por_sistema', {}).get(sis, est.get('modulo_outros', 'IMP')) if mod == 'EST' else mod)
            if mod == 'SITE' and not e.Name: e.Name = 'Terreno'
        for g in list(f.by_type('IfcGroup')):        # grupos de modelo do Revit (organização interna do RVT) saem; os elementos ficam
            if g.is_a() == 'IfcGroup' and any(k in (g.Name or '') for k in ('Grupo de modelos', 'Model Group')):
                for r in list(g.IsGroupedBy or []): f.remove(r)
                f.remove(g)
        for g in f.by_type('IfcGroup'):              # sistemas com o prefixo do módulo, sem repetir nome entre arquivos
            if pref and g.Name and not g.Name.startswith(pref): g.Name = f'{pref} — {g.Name}'
        for g in list(f.by_type('IfcGroup')):
            if not any(r.RelatedObjects for r in (g.IsGroupedBy or [])): ifcopenshell.api.run('root.remove_product', f, product=g)
        lp = ef.limpar(f)   # relações vazias e psets soltos saem aqui, no arquivo pequeno (no federado cada remove leva segundos)
        out = os.path.join(tmp, f'{len(prep):02d}_' + os.path.basename(fn)); f.write(out); prep.append(out)
        print(os.path.basename(fn), 'tirados', n_t, 'props de trabalho', n_p, 'limpeza', lp, 'ficam', len(f.by_type('IfcElement')), 'unidade', ef.unidade_comprimento(f), flush=True)
    # ---------- 2. junção ----------
    CACHE = os.environ.get('FED_CACHE')
    if CACHE and os.path.exists(CACHE): base = ifcopenshell.open(CACHE); print('junção reaproveitada', CACHE)
    else:
        base = ifcpatch.execute({'input': prep[0], 'file': ifcopenshell.open(prep[0]), 'recipe': 'MergeProjects', 'arguments': [prep[1:]]})
        if CACHE: base.write(CACHE)
    print('junção pronta', len(base.by_type('IfcElement')), 'elementos', flush=True)
    # ---------- 3. árvore: um site, uma edificação por módulo ----------
    proj = base.by_type('IfcProject')[0]; proj.Name = f"ETIB {cfg['escola']} — modelo federado único"; proj.Description = f"{cfg.get('contrato', '')} — {REV}".strip(' —')
    sites = base.by_type('IfcSite'); site = sites[0]; site.Name = f"ETIB {cfg['escola']}"; site.LongName = cfg.get('nome_completo')
    for s_ in sites[1:]:
        for r in list(s_.ContainsElements or []): r.RelatingStructure = site
        for r in list(s_.Decomposes or []):
            r.RelatedObjects = [o for o in r.RelatedObjects if o != s_]
            if not r.RelatedObjects: base.remove(r)
        base.remove(s_)
    for ss in base.by_type('IfcBuilding') + base.by_type('IfcBuildingStorey'):   # edificações/pavimentos de origem saem (a posição fica)
        for r in list(ss.ContainsElements or []): r.RelatingStructure = site
        for r in list(ss.IsDecomposedBy or []): base.remove(r)
        for r in list(ss.Decomposes or []):
            r.RelatedObjects = [o for o in r.RelatedObjects if o != ss]
            if not r.RelatedObjects: base.remove(r)
        base.remove(ss)
    edif = {}
    for k, nome in EDIF.items():
        b = ifcopenshell.api.run('root.create_entity', base, ifc_class='IfcBuilding', name=nome)
        b.ObjectPlacement = base.createIfcLocalPlacement(site.ObjectPlacement, base.createIfcAxis2Placement3D(base.createIfcCartesianPoint((0., 0., 0.))))
        ifcopenshell.api.run('aggregate.assign_object', base, products=[b], relating_object=site); edif[k] = b
    porm = collections.defaultdict(list)
    for e in base.by_type('IfcElement'):
        k = MOD.get(e.GlobalId, 'IMP')
        if k != 'SITE': porm[k].append(e)
    # contenção feita direto: o spatial.assign_container mexe na placement de cada elemento e leva HORAS no arquivo grande
    for k, els in porm.items():
        if k not in edif: sys.exit(f'módulo {k} sem edificação: confira "modulo_por_sistema"/"edificacoes_extra"')
        sel = {e.id() for e in els}; rels = {r for e in els for r in (e.ContainedInStructure or [])}
        for r in rels: r.RelatedElements = [o for o in r.RelatedElements if o.id() not in sel]
        base.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), None, None, None, els, edif[k])
        for e in els:
            ps = ue.get_pset(e, 'Dados_ETIB')
            if not ps: continue
            pset = base.by_id(ps['id']); pr = [x for x in pset.HasProperties if x.Name == 'modulo']
            if pr: pr[0].NominalValue = base.createIfcLabel(k)
            else: pset.HasProperties = list(pset.HasProperties) + [base.createIfcPropertySingleValue('modulo', None, base.createIfcLabel(k), None)]
    esp = collections.defaultdict(list)
    for sp in base.by_type('IfcSpace'): esp[MOD.get(sp.GlobalId, 'IMP')].append(sp)
    for k, sps in esp.items():
        for sp in sps:
            for r in list(sp.Decomposes or []):
                r.RelatedObjects = [o for o in r.RelatedObjects if o != sp]
                if not r.RelatedObjects: base.remove(r)
        ifcopenshell.api.run('aggregate.assign_object', base, products=sps, relating_object=edif.get(k, site))
    for k in [k for k in edif if k not in porm and k not in esp]:   # edificação vazia sai
        for r in list(edif[k].Decomposes or []): r.RelatedObjects = [o for o in r.RelatedObjects if o != edif[k]]
        base.remove(edif[k]); print('edificação vazia retirada:', k)
    for r in list(base.by_type('IfcRelContainedInSpatialStructure')):
        if not r.RelatedElements: base.remove(r)
    ua = proj.UnitsInContext                             # unidades: só a do projeto
    base.batch()
    for u in list(base.by_type('IfcUnitAssignment')):
        if u != ua: base.remove(u)
    base.unbatch(); base.batch()
    for u in list(base.by_type('IfcNamedUnit')) + list(base.by_type('IfcDerivedUnit')) + list(base.by_type('IfcMonetaryUnit')):
        if not base.get_inverse(u): base.remove(u)
    base.unbatch()
    print('limpeza', ef.limpar(base, soltos=False), flush=True)
    nome = f'{sig}_FEDERADO-UNICO_{REV}.ifc'; base.header.file_name.name = nome
    fn = os.path.join(OUT, nome); base.write(fn)
    print('gravado', fn, round(os.path.getsize(fn) / 1e6, 1), 'MB')
    print({k: len(v) for k, v in porm.items()}, 'espaços', {k: len(v) for k, v in esp.items()})

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else 'R00')
