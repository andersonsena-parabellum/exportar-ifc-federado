# -*- coding: utf-8 -*-
"""Alagoinhas — pasta de envio R03 em RASCUNHO, montada localmente com o que já está fechado (mesma estrutura da Jandaíra):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo), 03_IFC (implantação: cópia de entrega sem as propriedades de trabalho,
  nomes ALH_IMP_*), 04_BA2_MODELAGEM (instalações internas do BA2, só modelagem) e LEIA-ME.txt.
Não sobe para o Drive nem para o CDE. Refazer depois das decisões das 25 fichas (página de pendências) e da revisão de qualidade.
Uso: python -X utf8 alh_envio.py"""
import os, shutil, glob
import ifcopenshell

REL = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS'
EXE = os.path.join(REL, 'EXECUTIVO_R03'); IFC = os.path.join(REL, 'ENTREGA_IFC_R03')
OUT = os.path.join(REL, 'ENVIO_R03_2026-10-22')
PRANCHAS = ['24-049-ALH-SLJ-ETIB-IMP-PE-AGF-001-R07', '24-049-ALH-SLJ-ETIB-IMP-PE-ESG-001-HIG-R07',
            '24-049-ALH-SLJ-ETIB-IMP-PE-DRE-001-DRG-R05', '24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R08',
            '24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R06', '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R06']
NOMES = {'ALH_IMP_HIDRO_R03.ifc': 'ALH_IMP_HIDRO_R03.ifc', 'ALH_IMP_ELE_R03.ifc': 'ALH_IMP_ELETRICA_R03.ifc',
         'ALH_IMP_PCIP_R03.ifc': 'ALH_IMP_PCI_R03.ifc', 'ALH_TERRENO_R03.ifc': 'ALH_IMP_TERRENO_R03.ifc',
         'ALH_FEDERADO_R03.ifc': 'ALH_IMP_FEDERADO_R03.ifc'}
NOMES_BA2 = {'ALH_BA2_HIDRO_R03.ifc': 'ALH_BA2_HIDRO_R03.ifc', 'ALH_BA2_ELE_R03.ifc': 'ALH_BA2_ELETRICA_R03.ifc',
             'ALH_BA2_CLI_R03.ifc': 'ALH_BA2_CLIMATIZACAO_R03.ifc', 'ALH_BA2_PCIP_R03.ifc': 'ALH_BA2_PCI_R03.ifc'}
# propriedades de trabalho que ficam só no registro interno (mesmo critério da entrega final da Jandaíra, 21/10)
TIRAR = {'fora_do_comercial', 'angulo_real', 'deflexao_junta_graus'}


def limpar(src, dst):
    f = ifcopenshell.open(src); n = 0
    for ps in f.by_type('IfcPropertySet'):
        props = list(ps.HasProperties or [])
        fica = [p for p in props if p.Name not in TIRAR]
        if len(fica) != len(props):
            ps.HasProperties = fica
            for p in props:
                if p.Name in TIRAR and not f.get_inverse(p): f.remove(p); n += 1
    f.write(dst)
    return n


LEIA = """ETIB ALAGOINHAS (24-049-ALH) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO
Envio de 22/10/2026

CONTEÚDO
01_PRANCHAS_PDF     Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG     As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC              Modelos IFC das redes externas, por disciplina, terreno e federado (SIRGAS 2000 / UTM 24S)
04_BA2_MODELAGEM    Modelos IFC das instalações internas do bloco BA2 (modelagem, sem compatibilização)

PRANCHAS
  AGF-001  Água fria ..................... R07
  ESG-001  Esgoto ........................ R07
  DRE-001  Drenagem ...................... R05
  EL-001   Elétrica ...................... R08
  EL-002   Elétrica (iluminação externa) . R06
  IN-001   Incêndio ...................... R06
Cada folha está no carimbo padrão QG as built, com a linha nova no quadro de revisões e o código trocado. Profundidades
indicadas como "PROF. x,xx m" = do topo do tubo/eletroduto ao terreno acabado.

MODELOS IFC (03_IFC)
  ALH_IMP_HIDRO_R03.ifc ................ água fria, esgoto e drenagem
  ALH_IMP_ELETRICA_R03.ifc ............. elétrica enterrada (BT e iluminação externa)
  ALH_IMP_PCI_R03.ifc .................. hidrantes e alarme
  ALH_IMP_TERRENO_R03.ifc .............. terreno
  ALH_IMP_FEDERADO_R03.ifc ............. todas as disciplinas juntas, com os pontos pendentes marcados
Cada peça está na classe IFC do que ela é (tubo, conexão, válvula, eletroduto, caixa de passagem, caixa de inspeção, poço de
visita, equipamento), com material, diâmetro e sistema.

BLOCO BA2 (04_BA2_MODELAGEM)
  ALH_BA2_HIDRO_R03.ifc, ALH_BA2_ELETRICA_R03.ifc, ALH_BA2_CLIMATIZACAO_R03.ifc, ALH_BA2_PCI_R03.ifc
Modelagem das instalações internas do bloco, conforme os projetos; não fazem parte da compatibilização.

ESCOPO
Compatibilização das redes externas: da face das paredes das edificações para fora. As redes ficam interrompidas na face de
cada edificação.

PRINCIPAIS ALTERAÇÕES
- Profundidade (topo do tubo): água fria de 1,10 a 1,70 m; hidrantes de 1,50 a 1,60 m; alarme de 0,60 a 1,40 m; elétrica de
  0,70 a 1,85 m, sempre acima das redes de água. A profundidade de cada trecho de elétrica e de alarme muda só nas caixas; o
  valor de cada trecho está indicado nas pranchas.
- Redes de elétrica, alarme e hidrante contornam em planta caixas de drenagem/esgoto mais fundas, sem descer no meio do
  trecho (EL-001, EL-002 e IN-001).
- Caixas de passagem de elétrica e alarme e caixas de registro de água deslocadas para sair de cima de outras redes; os
  eletrodutos e tubos acompanham.
- Esgoto e drenagem nas cotas do projeto, exceto os trechos ajustados para sair dos cruzamentos, com a geratriz inferior
  indicada na prancha ("GI montante / jusante"): DRN-167 rebaixado 0,55 m; DRN-122 rebaixado 0,10 m; DRN-374 elevado
  0,15 m; chegada do DRN-376 rebaixada 0,20 m; ESG-36 rebaixado 0,20 m; ESG-11 elevado 0,10 m.
- Caixas de esgoto e drenagem deslocadas em planta sem mudar as cotas (PV27 0,80 m, CI-13 1,00 m, CI-17, CA82 e PV20 até
  0,60 m), com os tubos acompanhando. DRN-120 desviado a 45° em volta do PVE-02 e o nó DRN-237/DRN-238 afastado da CI-15.
- Trechos de elétrica, alarme e hidrante deslocados de lado com transições a 45° para sair dos cruzamentos com a drenagem e
  o esgoto (EL1-044, EL1-067, EL2-030, SDAI S09, T01, T11).

PENDÊNCIAS
Ficam para o projetista de drenagem e esgoto (pontos marcados no federado):
1. DRN-164 × caixa de passagem CX03 do alarme: ajustar o DRN-164.
2. DRN-165 junto à base do reservatório existente: afastar o tubo da base.
3. ESG-07 × DRN-191: cruzamento sem folga entre as duas redes por gravidade, nas cotas de projeto: ajustar a cota.
"""


def main():
    p1, p2, p3, p4 = (os.path.join(OUT, x) for x in ('01_PRANCHAS_PDF', '02_PRANCHAS_DWG', '03_IFC', '04_BA2_MODELAGEM'))
    for d in (p1, p2, p3, p4):
        os.makedirs(d, exist_ok=True)
        # esvazia sem apagar a pasta (o Windows segura o desktop.ini e o rmtree falhava no meio)
        for x in glob.glob(os.path.join(d, '*')):
            if os.path.basename(x).lower() != 'desktop.ini': os.remove(x)
    for n in PRANCHAS:
        shutil.copy2(os.path.join(EXE, 'PDF', n + '.pdf'), p1)
        dwg = os.path.join(EXE, n + '.dwg')
        if os.path.exists(dwg): shutil.copy2(dwg, p2)
        else: print('sem DWG:', n)
    for lg in glob.glob(os.path.join(EXE, 'CARIMBO_QG_logo_*.png')): shutil.copy2(lg, p2)
    for o, d in NOMES.items(): print(d, limpar(os.path.join(IFC, o), os.path.join(p3, d)), 'propriedades de trabalho tiradas')
    for o, d in NOMES_BA2.items(): print(d, limpar(os.path.join(IFC, 'BA2_MODELAGEM', o), os.path.join(p4, d)), 'propriedades de trabalho tiradas')
    open(os.path.join(OUT, 'LEIA-ME.txt'), 'w', encoding='utf-8-sig').write(LEIA)
    print(OUT)


if __name__ == '__main__':
    main()
