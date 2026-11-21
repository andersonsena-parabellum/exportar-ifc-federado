# -*- coding: utf-8 -*-
"""Aporá Itamira — pasta de envio (mesma estrutura da Olindina, olindina/exe/onn_envio.py), montada em RELATORIOS/ENVIO_2026-10-24;
cópia para G:/Meu Drive/ETIB_ENVIOS/ETIB-APORA-ITAMIRA_2026-10-24 com --drive (depois do checklist APROVADO):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo): DRE-001 R01, redesenhada pela drenagem executada do campo (decisão I2,
  23/10/2026; exe/ita_dre_asbuilt.py), e EL-001 R01 com a alimentação do quadro do campo executado (decisão I1, 24/10/2026;
  exe/ita_el_r01.py); 03_IFC R02 (cópia de entrega sem as propriedades de trabalho, nomes ITA_IMP_*) e LEIA-ME.txt.
Uso: .venv/Scripts/python.exe -X utf8 itamira/exe/ita_envio.py [--drive]"""
import os, sys, shutil, glob
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe')
from onn_envio import limpar

REL = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA\RELATORIOS'
IFC = os.path.join(REL, 'ENTREGA_IFC_2026-10-24')
EXE = os.path.join(REL, 'EXECUTIVO_2026-10-24')
OUT = os.path.join(REL, 'ENVIO_2026-10-24')
DRIVE = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-APORA-ITAMIRA_2026-10-24'
PRANCHAS = ['24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R01', '24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R01']
NOMES = {'ITA_IMP_HIDRO_R02.ifc': 'ITA_IMP_HIDRO_R02.ifc', 'ITA_IMP_ELE_R02.ifc': 'ITA_IMP_ELETRICA_R02.ifc',
         'ITA_TERRENO_R02.ifc': 'ITA_IMP_TERRENO_R02.ifc', 'ITA_FEDERADO_R02.ifc': 'ITA_IMP_FEDERADO_R02.ifc'}

LEIA = """ETIB APORÁ ITAMIRA (24-049-APR-ITA) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO E DO CAMPO SOCIETY
Envio de 24/10/2026 (substitui os de 22 e 23/10/2026)

CONTEÚDO
01_PRANCHAS_PDF   Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG   As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC            Modelos IFC por disciplina, terreno e federado (SIRGAS 2000 / UTM 24S, EPSG 31984)

PRANCHAS
  24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R01 ... a rede de drenagem do campo society está desenhada conforme executada (as built
      da construtora): coletores em tubo PVC liso Ø150, drenos em tubo PVC corrugado perfurado Ø100, calhas semicirculares de
      concreto, 7 caixas de areia com cota de tampa (CT) e de fundo (CF) e ralos. A rede da R00, que não foi executada, saiu da
      folha. A calha de concreto entrou na legenda.
  24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R01 .... a alimentação do QDLT-CAMPO vai até o quadro do campo executado (QD1, no canto sul do
      campo): eletroduto Ø 2" da CX-02 por dentro dos muros NE e SE do campo, a 0,80 m deles, com caixas 60x60 cm nas mudanças
      de direção (cerca de 122 m). Saíram o trecho que passava sob o reservatório executado, a caixa intermediária e o quadro na
      posição do projeto. O QD1 fica logo abaixo do limite da folha (chamada "SEGUE PARA O QDLT-CAMPO" na borda).
Eletrodutos da implantação com o topo a 0,70 m do terreno (NBR 5410; o EL-001 não informa a profundidade).

MODELOS IFC
  ITA_IMP_HIDRO_R02.ifc ................ drenagem do campo society (executada) e reservatório existente
  ITA_IMP_ELETRICA_R02.ifc ............. elétrica enterrada da implantação (EL-001 R01) e do campo society (executada)
  ITA_IMP_TERRENO_R02.ifc .............. terreno acabado (as built)
  ITA_IMP_FEDERADO_R02.ifc ............. todas as disciplinas juntas
Cada peça está na classe IFC do que ela é (tubo, conexão, eletroduto, caixa de passagem, caixa de areia, quadro, poste,
reservatório), com material, diâmetro e sistema. Material conforme a legenda das pranchas e o as built: eletroduto PVC corrugado
flexível; drenos em tubo PVC corrugado perfurado; coletores em tubo PVC liso; calhas semicirculares de concreto. As redes e os
equipamentos já executados (drenagem e iluminação do campo, quadros, gerador, reservatório) estão no modelo com a propriedade
"situacao" = executado, nas posições e cotas do as built, as mesmas da DRE-001 R01.

ESCOPO
Redes externas, da face das edificações para fora. Na implantação da Itamira só há projeto de drenagem (DRE-001) e de
elétrica (EL-001). O incêndio do campo (IN-001 e IN-002) é sinalização e iluminação de emergência, sem rede enterrada.

PENDÊNCIAS
1. Água fria, esgoto e incêndio (hidrante e SDAI) da implantação: não há projeto no acervo do contrato. Solicitados à
   construtora, ou a confirmação de que a obra não tem essas redes.
2. Elétrica: confirmar com a construtora se a alimentação do QD1 já foi executada. Se foi, o traçado executado substitui o da
   EL-001 R01 no modelo e na prancha.
3. Drenagem: as 7 saídas da drenagem do campo terminam logo depois do muro (pontas de tubo PVC liso, como no as built). O ponto
   de deságue ou de ligação delas e o cadastro das redes existentes junto da escola foram solicitados à construtora.
4. No as built do campo, junto do ralo do canto sul, o eletroduto da iluminação encosta no tubo de drenagem que chega ao ralo
   (3 cm de sobreposição nas cotas do as built): conferir em campo.
"""


def main():
    p1, p2, p3 = (os.path.join(OUT, x) for x in ('01_PRANCHAS_PDF', '02_PRANCHAS_DWG', '03_IFC'))
    for p in (p1, p2, p3):
        os.makedirs(p, exist_ok=True)
        for x in glob.glob(os.path.join(p, '*')): os.remove(x)
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
