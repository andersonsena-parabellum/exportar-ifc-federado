# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — pasta de envio (mesma estrutura da Olindina, olindina/exe/onn_envio.py), montada em RELATORIOS/ENVIO_2026-10-23;
cópia para G:/Meu Drive/ETIB_ENVIOS/ETIB-APORA-PROF-AUREA_2026-10-23 com --drive (depois do checklist APROVADO):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo), 03_IFC (cópia de entrega sem as propriedades de trabalho, nomes AUR_IMP_*)
  e LEIA-ME.txt.
Uso: .venv/Scripts/python.exe -X utf8 aurea/exe/aur_envio.py [--drive]"""
import os, sys, shutil, glob
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe')
from onn_envio import limpar

REL = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS'
EXE = os.path.join(REL, 'EXECUTIVO_2026-10-23'); IFC = os.path.join(REL, 'ENTREGA_IFC_2026-10-23')
OUT = os.path.join(REL, 'ENVIO_2026-10-23')
DRIVE = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-APORA-PROF-AUREA_2026-10-23'
PRANCHAS = ['24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R01', '24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R01']
NOMES = {'AUR_IMP_HIDRO_R01.ifc': 'AUR_IMP_HIDRO_R01.ifc', 'AUR_IMP_ELE_R01.ifc': 'AUR_IMP_ELETRICA_R01.ifc',
         'AUR_IMP_PCIP_R01.ifc': 'AUR_IMP_PCI_R01.ifc', 'AUR_IMP_EST_R01.ifc': 'AUR_IMP_FUNDACAO_QUADRA_R01.ifc',
         'AUR_TERRENO_R01.ifc': 'AUR_IMP_TERRENO_R01.ifc', 'AUR_FEDERADO_R01.ifc': 'AUR_IMP_FEDERADO_R01.ifc'}

LEIA = """ETIB APORÁ PROF. ÁUREA (24-049-APR) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO
Envio de 23/10/2026

CONTEÚDO
01_PRANCHAS_PDF   Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG   As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC            Modelos IFC por disciplina, fundação da quadra, terreno e federado (SIRGAS 2000 / UTM 24S, EPSG 31984)

PRANCHAS
  AF-002   Drenagem pluvial da quadra ........... R01
  EL-001   Elétrica (alimentação da quadra e da casa de bombas) ... R01
Cada folha está no carimbo padrão QG as built, com a linha nova no quadro de revisões. A IN-001 (incêndio) não mudou.

MODELOS IFC
  AUR_IMP_HIDRO_R01.ifc ................ drenagem pluvial (quadra executada e ligação até a rede geral)
  AUR_IMP_ELETRICA_R01.ifc ............. elétrica enterrada (QGBT existente -> QDLT da quadra e QDLT da casa de bombas)
  AUR_IMP_PCI_R01.ifc .................. hidrante e laço do alarme de incêndio junto da quadra
  AUR_IMP_FUNDACAO_QUADRA_R01.ifc ...... sapatas da quadra (referência, QDC-FUN-001/002 R01 nos pilares do as built)
  AUR_IMP_TERRENO_R01.ifc .............. terreno acabado (as built, nas cotas da terraplanagem e das caixas da drenagem)
  AUR_IMP_FEDERADO_R01.ifc ............. todas as disciplinas juntas
Cada peça está na classe IFC do que ela é (tubo, conexão, eletroduto, caixa de passagem, caixa de areia, poço de visita, quadro,
sapata), com material, diâmetro e sistema. Material conforme a legenda das pranchas: pluvial em PVC Série Reforçada nos Ø150,
Série Normal nos Ø200 e Vinilfort nos Ø250; elétrica e alarme em eletroduto PEAD corrugado flexível; hidrante em PEAD 2.1/2".

ESCOPO
Redes externas da implantação com projeto no acervo do contrato: drenagem pluvial (AF-002-HIG, que é a drenagem da quadra),
elétrica (EL-001) e incêndio (IN-001). A drenagem em volta da quadra já está executada: o modelo traz a rede executada (caixas de
areia, coletores e ramais das descidas), nas posições e cotas do as built, com a propriedade "situacao" = executado. Do AF-002 entra
como novo a ligação da quadra à rede: CA-04 -> PVP-01, CA-10 -> PVP-02, PVP-02 -> PVP-01, PVP-01 a PVP-06 e o lançamento.

PRINCIPAIS ALTERAÇÕES
- AF-002: cota de tampa 188,00 nas caixas de areia do lado leste da quadra (CA-06 a CA-10, antes 190,00) e nos PVP-01 e PVP-02
  (antes 189,00), que é a cota do platô da quadra na terraplanagem e a das caixas executadas. A profundidade de cada caixa não
  muda: a cota de fundo desce o mesmo.
- AF-002: o trecho CA-10 -> PVP-02 (Ø250) passa a i = 0,67 %, para chegar no fundo do PVP-02 com a cota nova.
- EL-001: caixa de passagem 80x80 junto da quadra, a leste (a que recebe os dois circuitos), deslocada 0,78 m na direção da quadra:
  estava sobre o coletor executado da drenagem. Os eletrodutos acompanham.
- Elétrica a 0,70 m de profundidade (NBR 5410; o EL-001 não informa). Os eletrodutos do banco que chega à caixa junto da quadra
  e o ramal da casa de bombas ficam a 0,80 m (nota "PROF. 0,80 m" na EL-001), para passar 0,20 m abaixo da drenagem executada
  da quadra. Hidrante e alarme a 0,50 m (nota do IN-001).
- CA-04 (caixa de areia já executada): o fundo, a 187,39 no as built, desce até 187,11, a cota de fundo do AF-002, para receber a
  saída para o PVP-01 (Ø200) com a declividade do projeto. A prancha já traz CF 187,11 nessa caixa; o serviço é rebaixar o fundo
  da caixa existente em 0,28 m.

PENDÊNCIAS
1. A drenagem executada em volta da quadra difere do AF-002: as caixas de areia do lado leste estão cerca de 1,3 m mais para
   fora (a 2,1 m da linha de pilares) e a última delas 3,5 m ao norte da CA-10 do projeto, onde o coletor executado termina. O
   modelo traz o executado; a prancha não foi redesenhada (só as cotas acima).
2. Hidrante: o trecho do IN-001 "vem das instalações existentes, compatibilizar in loco"; o ponto de ligação na rede existente
   não está desenhado.
3. Lançamento da drenagem na rede geral existente: posição e cota sem cadastro.
4. Pé das descidas da cobertura da quadra (executado): no modelo, a saída de cada uma das 10 descidas junto dos pilares passa pelo
   pedestal da sapata (sapatas pelo projeto de fundação da quadra, QDC-FUN-001/002 R01, nos pilares do as built). Rede e
   fundação já executadas; registrado para conferência em campo.
"""


def main():
    p1, p2, p3 = (os.path.join(OUT, x) for x in ('01_PRANCHAS_PDF', '02_PRANCHAS_DWG', '03_IFC'))
    for d in (p1, p2, p3): os.makedirs(d, exist_ok=True)
    for d in (p1, p2, p3):
        for x in glob.glob(os.path.join(d, '*.*')):
            if not x.endswith('desktop.ini'): os.remove(x)
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
