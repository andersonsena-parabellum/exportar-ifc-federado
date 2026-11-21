# -*- coding: utf-8 -*-
"""Cópia de entrega do IFC final da Jandaíra (R03, FINAL5): tira as propriedades de trabalho que não vão
para a construtora (ângulo real, deflexão na junta, marcação de conexão fora de 45°/90° — ficam só no
registro interno, EXECUTIVO_R03_IFC\\conferencia\\JAN_R03_conexoes_fora_45-90_INTERNO.csv) e o jargão
"(obstáculo)" no nome do grupo da estrutura. Grava com os nomes da lista mestra (JDI_IMP_*_R03.ifc).
Uso:  ..\\..\\.venv\\Scripts\\python.exe -X utf8 jan_ifc_entrega.py"""
import os, ifcopenshell

ORIG = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R03_FINAL5\ENTREGA_IFC_R03'
DEST = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\_revisao_qualidade\03_IFC'
NOMES = {
    'JAN_R03_HIDRO.ifc': 'JDI_IMP_HIDRO_R03.ifc',
    'JAN_R03_ELE.ifc': 'JDI_IMP_ELETRICA_R03.ifc',
    'JAN_R03_PCIP.ifc': 'JDI_IMP_PCI_R03.ifc',
    'JAN_R03_EST_asbuilt.ifc': 'JDI_IMP_ESTRUTURA-ASBUILT_R03.ifc',
    'JAN_R03_TERRENO.ifc': 'JDI_IMP_TERRENO_R03.ifc',
    'JAN_R03_FEDERADO.ifc': 'JDI_IMP_FEDERADO_R03.ifc',
}
TIRAR = {'fora_do_comercial', 'angulo_real', 'deflexao_junta_graus'}
TROCAR_NOME = {'Estrutura as built (obstáculo) — caixas': 'Estrutura as built'}

os.makedirs(DEST, exist_ok=True)
for o, d in NOMES.items():
    f = ifcopenshell.open(os.path.join(ORIG, o))
    n_prop = n_nome = 0
    for ps in f.by_type('IfcPropertySet'):
        props = list(ps.HasProperties or [])
        fica = [p for p in props if p.Name not in TIRAR]
        if len(fica) != len(props):
            ps.HasProperties = fica
            for p in props:
                if p.Name in TIRAR and not f.get_inverse(p):
                    f.remove(p)
                    n_prop += 1
    for el in f.by_type('IfcRoot'):
        nm = getattr(el, 'Name', None)
        if nm in TROCAR_NOME:
            el.Name = TROCAR_NOME[nm]
            n_nome += 1
    f.write(os.path.join(DEST, d))
    print(f'{d}: {n_prop} propriedades tiradas, {n_nome} nomes trocados')
