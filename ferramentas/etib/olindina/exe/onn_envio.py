# -*- coding: utf-8 -*-
"""Olindina — pasta de envio (mesma estrutura da Sátiro, da Jandaíra e de Alagoinhas), montada em RELATORIOS/ENVIO_2026-10-22;
cópia para G:/Meu Drive/ETIB_ENVIOS/ETIB-OLINDINA_2026-10-22 só com --drive (quando o Anderson liberar):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo), 03_IFC (cópia de entrega sem as propriedades de trabalho, nomes ONN_IMP_*)
  e LEIA-ME.txt.
Uso: python -X utf8 onn_envio.py [--drive]"""
import os, sys, shutil, glob
import ifcopenshell

REL = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS'
EXE = os.path.join(REL, 'EXECUTIVO_2026-10-21'); IFC = os.path.join(REL, 'ENTREGA_IFC_2026-10-21')
OUT = os.path.join(REL, 'ENVIO_2026-10-22')
DRIVE = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-OLINDINA_2026-10-22'
PRANCHAS = ['24-049-ONN-CTO-ETIB-IMP-PE-EL-001-ELG-R01', '24-049-ONN-CTO-ETIB-IMP-PE-ESG-001-HIG-R01',
            '24-049-ONN-CTO-ETIB-IMP-PE-DRE-001-DRG-R01']
NOMES = {'ONN_IMP_HIDRO_R01.ifc': 'ONN_IMP_HIDRO_R01.ifc', 'ONN_IMP_ELE_R01.ifc': 'ONN_IMP_ELETRICA_R01.ifc',
         'ONN_IMP_PCIP_R01.ifc': 'ONN_IMP_PCI_R01.ifc', 'ONN_TERRENO_R01.ifc': 'ONN_IMP_TERRENO_R01.ifc',
         'ONN_FEDERADO_R01.ifc': 'ONN_IMP_FEDERADO_R01.ifc'}
# propriedades de trabalho que ficam só no registro interno (mesmo critério da Jandaíra, de Alagoinhas e da Sátiro)
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


LEIA = """ETIB OLINDINA (24-049-ONN) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO
Envio de 22/10/2026

CONTEÚDO
01_PRANCHAS_PDF   Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG   As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC            Modelos IFC por disciplina, terreno e federado (SIRGAS 2000 / UTM 24S, EPSG 31984)

PRANCHAS
  EL-001   Elétrica (alimentação do BA5) ........ R01
  ESG-001  Esgoto e drenagem pluvial do BA5 ..... R01
  DRE-001  Drenagem pluvial do BA5 .............. R01 (mesmo desenho do ESG-001)
Cada folha está no carimbo padrão QG as built, com a linha nova no quadro de revisões. Profundidade indicada como "PROF. x,xx m" =
do topo do eletroduto ao terreno acabado. As demais folhas da implantação (AF-001 e IN-001) não mudaram.

MODELOS IFC
  ONN_IMP_HIDRO_R01.ifc ................ água fria, esgoto e drenagem pluvial
  ONN_IMP_ELETRICA_R01.ifc ............. elétrica enterrada (alimentador QGBT -> QDLT do BA5)
  ONN_IMP_PCI_R01.ifc .................. hidrante
  ONN_IMP_TERRENO_R01.ifc .............. terreno acabado (as built, nas cotas de tampa das caixas das pranchas)
  ONN_IMP_FEDERADO_R01.ifc ............. todas as disciplinas juntas
Cada peça está na classe IFC do que ela é (tubo, conexão, eletroduto, caixa de passagem, caixa de inspeção, poço de visita), com
material, diâmetro e sistema. Material conforme a legenda das pranchas: água fria em PVC soldável marrom; esgoto em PVC Série
Normal; pluvial em PVC Série Reforçada nos Ø150 e Série Normal nos Ø200; drenos Ø40 em PVC soldável; elétrica em eletroduto PVC
corrugado flexível Ø3"; hidrante em PEAD 2.1/2".

ESCOPO
Redes externas da ampliação (bloco BA5) e as ligações dela às redes existentes, da face das paredes do BA5 para fora. As redes
de esgoto e de drenagem pluvial existentes desenhadas nas pranchas (com as cotas de tampa e de fundo indicadas) estão no modelo
como existentes (propriedade "situacao"), para conferir os cruzamentos com as redes novas. A rede de água existente desenhada no
AF-001 só como referência não entra no modelo; o ramal novo do BA5 sai dela.

PRINCIPAIS ALTERAÇÕES
- Caixa de passagem 80x80 junto ao BA5 (a última antes do QDLT) deslocada 1,90 m para sudoeste: estava sobre a rede de esgoto
  existente. Os eletrodutos acompanham.
- Eletroduto entre essa caixa e a anterior a 1,30 m de profundidade, por baixo das redes existentes de esgoto e de drenagem
  pluvial; os demais trechos do alimentador a 0,70 m.
- ESG-001 e DRE-001: na última caixa de areia do pluvial do BA5 (antes do poço PVP-36 existente), a cota de fundo indicada
  passa de 166,91 para 166,81, que é a da profundidade indicada na própria etiqueta (1,19 m) e a da declividade de 1 % da caixa
  anterior. No DRE-001 o código curto da folha passa a DRE_IMP-001.
- Esgoto e drenagem pluvial nas demais cotas do projeto; hidrante a 0,50 m (nota 5 do IN-001).

PENDÊNCIA
1. O ramal de hidrante do BA5 "vem das instalações existentes, compatibilizar in loco" (IN-001): o ponto de ligação na rede
   existente não está desenhado; o modelo traz só o ramal novo.

OBSERVAÇÃO
O esgoto do BA5 (Ø100 até a CE-21 existente) cruza a drenagem pluvial existente entre o PVP-33 e o PVP-34 com 0,14 m de folga
entre os tubos, nas cotas do projeto.
"""


def main():
    p1, p2, p3 = (os.path.join(OUT, x) for x in ('01_PRANCHAS_PDF', '02_PRANCHAS_DWG', '03_IFC'))
    for d in (p1, p2, p3): os.makedirs(d, exist_ok=True)
    for n in PRANCHAS:
        shutil.copy2(os.path.join(EXE, 'PDF', n + '.pdf'), p1); shutil.copy2(os.path.join(EXE, n + '.dwg'), p2)
    for lg in glob.glob(os.path.join(EXE, 'CARIMBO_QG_logo_*.png')): shutil.copy2(lg, p2)
    for o, d in NOMES.items(): print(d, limpar(os.path.join(IFC, o), os.path.join(p3, d)), 'propriedades de trabalho tiradas')
    open(os.path.join(OUT, 'LEIA-ME.txt'), 'w', encoding='utf-8-sig').write(LEIA)
    print(OUT)
    if '--drive' in sys.argv:
        shutil.copytree(OUT, DRIVE, dirs_exist_ok=True, ignore=shutil.ignore_patterns('desktop.ini')); print(DRIVE)


if __name__ == '__main__':
    main()
