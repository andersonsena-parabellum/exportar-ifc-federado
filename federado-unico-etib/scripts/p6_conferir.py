# -*- coding: utf-8 -*-
"""Passo 6 — conferência do federado antes de entregar. Para no primeiro problema? Não: lista tudo e termina com APROVADO ou REPROVADO.
Confere: esquema IFC4 válido (0 erros), 1 site, edificações e contagem, elemento sem edificação, sem Dados_ETIB, propriedade de
trabalho, GUID repetido, grupos, e a geometria: caixa e cotas por módulo (arquitetura × estrutura no mesmo lugar), elementos com
tamanho ou cota fora do razoável e elementos com representação que não geram sólido.
Uso: python p6_conferir.py escola.json saida/<SIGLA>_FEDERADO-UNICO_<REV>.ifc  -> imprime e grava <arquivo>.conferencia.txt"""
import os, sys, collections, io, contextlib, numpy as np, ifcopenshell, ifcopenshell.validate, ifcopenshell.util.element as ue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg, fn):
    m = ifcopenshell.open(fn); prob = []
    print('esquema', m.schema, '| sites', [s.Name for s in m.by_type('IfcSite')], '| unidade', ef.unidade_comprimento(m))
    if m.schema != 'IFC4': prob.append('esquema não é IFC4')
    if len(m.by_type('IfcSite')) != 1: prob.append('mais de um site')
    for mc in m.by_type('IfcMapConversion'): print('georreferência', mc.Eastings, mc.Northings, mc.TargetCRS.Name)
    print('edificações:')
    for b in m.by_type('IfcBuilding'): print('  ', b.Name, sum(len(r.RelatedElements) for r in b.ContainsElements))
    semc = [e for e in m.by_type('IfcElement') if not e.ContainedInStructure]
    print('elementos sem edificação', len(semc));  prob += ['elementos sem edificação'] if semc else []
    print('elementos por classe', collections.Counter(e.is_a() for e in m.by_type('IfcElement')).most_common(25))
    c = collections.Counter(p.Name for ps in m.by_type('IfcPropertySet') for p in ps.HasProperties)
    trab = {k: c[k] for k in ef.TIRAR_PROPS if c[k]}; print('propriedades de trabalho', trab); prob += ['propriedade de trabalho'] if trab else []
    dup = sum(1 for v in collections.Counter(e.GlobalId for e in m.by_type('IfcRoot')).values() if v > 1); print('GUID repetidos', dup); prob += ['GUID repetido'] if dup else []
    sem = collections.Counter(e.is_a() for e in m.by_type('IfcElement') if 'Dados_ETIB' not in ue.get_psets(e)); print('sem Dados_ETIB', dict(sem)); prob += ['sem Dados_ETIB'] if sem else []
    print('grupos', len(m.by_type('IfcGroup')), sorted(g.Name for g in m.by_type('IfcGroup'))[:30])
    h = ifcopenshell.validate.json_logger(); ifcopenshell.validate.validate(m, h)
    st = collections.Counter((x.get('type') or '') + ':' + str(x.get('attribute') or x.get('message'))[:90] for x in h.statements)
    print('validação', sum(st.values())); [print('   ', k, v) for k, v in st.most_common(15)]; prob += ['validação IFC4'] if st else []
    # ---------- geometria ----------
    zmin, zmax = cfg['cota']['min'], cfg['cota']['max']
    els = [e for e in m.by_type('IfcElement') if not e.is_a('IfcOpeningElement')]; B = {}
    for e, v, t in ef.formas(m, els): B[e.id()] = (v.min(0), v.max(0))
    grupos = collections.defaultdict(list); ruins = []
    for e in els:
        if e.id() not in B: continue
        lo, hi = B[e.id()]; ps = ue.get_psets(e).get('Dados_ETIB', {}); mod = ps.get('modulo', '?'); d = ps.get('disciplina', '?')
        tipo = 'ARQ' if d == 'ARQ' else 'EST' if d in ('EST', '?') or e.is_a() in ('IfcColumn', 'IfcBeam', 'IfcFooting') else 'TER' if d == 'TER' else 'INST'
        grupos[(mod, tipo)].append((lo, hi)); tam = hi - lo
        if not e.is_a('IfcGeographicElement') and (tam[:2].max() > cfg['cota'].get('tamanho_max', 120) or lo[2] < zmin or hi[2] > zmax or tam.max() < 0.005):
            ruins.append((mod, e.is_a(), (e.Name or '')[:40], lo.round(1).tolist(), hi.round(1).tolist()))
    print('módulo  tipo     n   caixa x            caixa y            z              | ARQ × EST (distância dos centros)')
    cx = {}
    for (mod, t), v in sorted(grupos.items()):
        lo = np.array([a for a, b in v]).min(0); hi = np.array([b for a, b in v]).max(0); cx[(mod, t)] = (lo[:2] + hi[:2]) / 2
        print(f'  {mod:5s} {t:4s} {len(v):6d}  {lo[0]:7.1f}..{hi[0]:7.1f}  {lo[1]:7.1f}..{hi[1]:7.1f}  {lo[2]:6.2f}..{hi[2]:6.2f}')
    for mod in sorted({k[0] for k in cx}):
        if (mod, 'ARQ') in cx and (mod, 'EST') in cx:
            dd = float(np.linalg.norm(cx[(mod, 'ARQ')] - cx[(mod, 'EST')])); print(f'  {mod}: arquitetura × estrutura {dd:.1f} m')
            if dd > cfg['cota'].get('arq_est_max', 3.0): prob.append(f'{mod}: arquitetura longe da estrutura ({dd:.1f} m)')
    print(f'fora do razoável (maior que {cfg["cota"].get("tamanho_max", 120)} m, cota fora de {zmin}..{zmax}, sem tamanho):', len(ruins))
    for r in ruins[:25]: print('   ', r)
    semg = [e for e in els if e.id() not in B and e.Representation and not e.IsDecomposedBy]
    print('com representação e sem geometria:', len(semg), collections.Counter(e.is_a() for e in semg).most_common(6)); prob += ['elemento sem geometria'] if semg else []
    print('\nRESULTADO:', 'APROVADO' if not prob else 'REPROVADO — ' + '; '.join(prob))
    print('(os "fora do razoável" são para olhar um a um: estaca funda e platô grande podem estar certos)')
    return not prob

if __name__ == '__main__':
    buf = io.StringIO()
    class T:
        def write(self, s): sys.__stdout__.write(s); buf.write(s)
        def flush(self): sys.__stdout__.flush()
    with contextlib.redirect_stdout(T()): ok = main(ef.carregar(sys.argv[1]), sys.argv[2])
    open(sys.argv[2] + '.conferencia.txt', 'w', encoding='utf-8').write(buf.getvalue())
    sys.exit(0 if ok else 1)
