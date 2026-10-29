# -*- coding: utf-8 -*-
"""Passo 1 — arquitetura de cada módulo, pronta para a junção.
Fonte "rvt": IFC exportado do RVT de arquitetura da construtora. Fonte "padrao": IFC do modelo padrão ETIB (IFC2X3 vira IFC4).
Para cada módulo: tira instalações, portas de conexão, fundações e o que a configuração mandar; posiciona (giro + translação);
grava Dados_ETIB; simplifica malhas pesadas; georreferência da escola; ângulos em radiano.
Uso: python p1_modulos.py escola.json [MÓDULO ...]   -> trabalho/modulos/<SIGLA>_ARQ_<MÓDULO>.ifc"""
import os, sys, tempfile, ifcopenshell, ifcopenshell.api, ifcopenshell.util.element as ue, ifcpatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

SAI = ['IfcDistributionPort', 'IfcGrid', 'IfcFooting', 'IfcFlowSegment', 'IfcFlowFitting', 'IfcFlowController', 'IfcDistributionControlElement']
EST = ('IfcBeam', 'IfcColumn')
PROXY_SAI = ['HID_', 'TEXTO DO MODELO', 'GÁS', 'LOGO']   # terminando em "_": começa com; senão: contém

def main(cfg, so=()):
    for mod, m in cfg['modulos'].items():
        if so and mod not in so: continue
        f = ifcopenshell.open(ef.caminho(cfg, m['arquivo'])); n0 = len(f.by_type('IfcProduct'))
        sai = tuple(SAI + m.get('excluir_classes_extra', []))
        manter = [x.upper() for x in m.get('manter_nomes_com', [])]          # ex.: ["CALHA"] = calhas da cobertura ficam
        proxy = [x.upper() for x in m.get('excluir_proxy_nomes', PROXY_SAI)]
        def tira(e):
            nome = (e.Name or '').upper()
            if any(e.is_a(c) for c in sai) and not any(k in nome for k in manter): return True
            if not m.get('manter_estrutura', True) and any(e.is_a(c) for c in EST): return True
            return e.is_a('IfcBuildingElementProxy') and any(nome.startswith(p) if p.endswith('_') else p in nome for p in proxy)
        n_t = ef.remover(f, tira)
        # traves e outros objetos que o padrão grava como IfcSite solto somem no federado: viram proxy no site do arquivo
        raiz = [s for s in f.by_type('IfcSite') if ue.get_aggregate(s)]
        for s in [s for s in f.by_type('IfcSite') if s.Representation and not ue.get_aggregate(s)] if raiz else []:
            p = ifcopenshell.api.run('root.reassign_class', f, product=s, ifc_class='IfcBuildingElementProxy')
            ifcopenshell.api.run('spatial.assign_container', f, products=[p], relating_structure=raiz[0])
        ef.transformar(f, ef.matriz(m['posicao'], cfg))
        for e in f.by_type('IfcElement') + f.by_type('IfcSpace'):
            ef.dados(f, e, {'disciplina': 'ARQ', 'sistema': f'ARQ-{mod}', 'modulo': mod, 'origem': m.get('origem', m['arquivo'])})
        if f.schema != 'IFC4':
            tmp = os.path.join(tempfile.mkdtemp(), 'x.ifc'); f.write(tmp)
            f = ifcpatch.execute({'input': tmp, 'file': ifcopenshell.open(tmp), 'recipe': 'Migrate', 'arguments': ['IFC4']})
        n_s = ef.simplificar(f); ef.georef(f, cfg); n_a = ef.graus_para_rad(f)
        out = ef.saida_modulo(cfg, mod); f.write(out) if hasattr(f, 'write') else ifcpatch.write(f, out)
        g = ifcopenshell.open(out)
        print(f'{mod}: {n0} -> {len(g.by_type("IfcProduct"))} produtos (tirados {n_t}, simplificados {n_s}, ângulos convertidos {n_a}, unidade {ef.unidade_comprimento(g)})', flush=True)

def estruturas(cfg, so=()):
    """estrutura dos RVT da construtora (ECC, FUN, EMT de cada módulo), cada arquivo na posição do próprio vínculo:
    tira portas de conexão e eixos, posiciona, grava Dados_ETIB (disciplina EST, sistema EST-<MÓD>), georreferência e radiano"""
    for out, x in ef.estruturas_rvt(cfg):
        if so and x['modulo'] not in so and 'EST' not in so: continue
        f = ifcopenshell.open(ef.caminho(cfg, x['arquivo'])); n0 = len(f.by_type('IfcProduct'))
        n_t = ef.remover(f, lambda e: any(e.is_a(c) for c in ('IfcDistributionPort', 'IfcGrid', 'IfcFlowSegment', 'IfcFlowFitting')))
        ef.transformar(f, ef.matriz(x['posicao'], cfg))
        for e in f.by_type('IfcElement'):
            ef.dados(f, e, {'disciplina': 'EST', 'sistema': f"EST-{x['modulo']}", 'modulo': x['modulo'], 'origem': x.get('origem', x['arquivo'])})
        ef.georef(f, cfg); n_a = ef.graus_para_rad(f); f.write(out)
        print(f"EST {x['modulo']} {os.path.basename(x['arquivo'])}: {n0} produtos (tirados {n_t}, ângulos convertidos {n_a}, unidade {ef.unidade_comprimento(f)})", flush=True)

if __name__ == '__main__':
    c = ef.carregar(sys.argv[1]); so = set(sys.argv[2:])
    if so != {'EST'}: main(c, so)
    estruturas(c, so)
