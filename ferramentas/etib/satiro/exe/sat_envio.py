# -*- coding: utf-8 -*-
"""Sátiro Dias — pasta de envio (mesma estrutura da Jandaíra e de Alagoinhas), montada em RELATORIOS/ENVIO_2026-10-22 e copiada
para G:/Meu Drive/ETIB_ENVIOS/ETIB-SATIRO-DIAS_2026-10-22 (pedido do Anderson, 22/10/2026):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo), 03_IFC (cópia de entrega sem as propriedades de trabalho, nomes STK_IMP_*),
  04_PENDENCIAS (recorte da prancha de cada ponto do projetista) e LEIA-ME.txt.
Uso: python -X utf8 sat_envio.py [--drive]"""
import os, sys, shutil, glob
import ifcopenshell

REL = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS'
EXE = os.path.join(REL, 'EXECUTIVO_2026-10-21'); IFC = os.path.join(REL, 'ENTREGA_IFC_2026-10-21')
PEN = r'D:\Projeto Modelagem\FERRAMENTAS\satiro\pendencias\img'
OUT = os.path.join(REL, 'ENVIO_2026-10-22')
DRIVE = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-SATIRO-DIAS_2026-10-22'
PRANCHAS = ['24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R01', '24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R01',
            '24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R02', '24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R02',
            '24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R04', '24-049-STK-XXX-ETIB-CPS-PE-ELE-001-ELG-R01']
NOMES = {'STK_IMP_HIDRO_R01.ifc': 'STK_IMP_HIDRO_R01.ifc', 'STK_IMP_ELE_R01.ifc': 'STK_IMP_ELETRICA_R01.ifc',
         'STK_IMP_PCIP_R01.ifc': 'STK_IMP_PCI_R01.ifc', 'STK_TERRENO_R01.ifc': 'STK_IMP_TERRENO_R01.ifc',
         'STK_FEDERADO_R01.ifc': 'STK_IMP_FEDERADO_R01.ifc'}
# propriedades de trabalho que ficam só no registro interno (mesmo critério da Jandaíra e de Alagoinhas)
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


# imagens das pendências: o recorte da prancha de cada ficha da página de pendências (índice da ficha -> nome no envio)
PEND = [('00', '1_galeria_DRE-001')]

LEIA = """ETIB SÁTIRO DIAS (24-049-STK) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO
Envio de 22/10/2026

CONTEÚDO
01_PRANCHAS_PDF   Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG   As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC            Modelos IFC por disciplina, terreno e federado (SIRGAS 2000 / UTM 24S, EPSG 31984)
04_PENDENCIAS     Recorte da prancha DRE-001 no ponto da galeria que aguarda definição

PRANCHAS
Implantação
  AF-001   Água fria ..................... R01
  ESG-001  Esgoto e drenagem pluvial ..... R01
  EL-001   Elétrica (iluminação externa) . R02
  EL-002   Elétrica (alimentação) ........ R02
  IN-001   Incêndio ...................... R04
Campo society
  ELE-001  Elétrica do campo ............. R01
Cada folha está no carimbo padrão QG as built, com a linha nova no quadro de revisões e o código trocado (o código da elétrica do
campo segue a lista mestra: 24-049-STK-XXX-ETIB-CPS-PE-ELE-001). Profundidades indicadas como "PROF. x,xx m" = do topo do
tubo/eletroduto ao terreno acabado. A drenagem (DRE-001, DRE-002) e a drenagem do campo não mudaram.

MODELOS IFC
  STK_IMP_HIDRO_R01.ifc ................ água fria (alimentação, distribuição e reúso), esgoto, drenagem pluvial e drenagem do campo
  STK_IMP_ELETRICA_R01.ifc ............. elétrica enterrada (alimentação, iluminação externa e campo society)
  STK_IMP_PCI_R01.ifc .................. hidrantes e alarme
  STK_IMP_TERRENO_R01.ifc .............. terreno acabado (as built, nas cotas de tampa das caixas das pranchas)
  STK_IMP_FEDERADO_R01.ifc ............. todas as disciplinas juntas, com os pontos pendentes marcados
Cada peça está na classe IFC do que ela é (tubo, conexão, eletroduto, caixa de passagem, caixa de inspeção, poço de visita,
reservatório, quadro, poste, hidrante), com material, diâmetro e sistema. Material conforme a legenda das pranchas e os
memoriais: água fria em PVC soldável marrom; esgoto em PVC Série Normal; pluvial em PVC Série Reforçada até 150 mm, Série
Normal em 200 mm e Vinilfort a partir de 250 mm; drenos em PVC corrugado perfurado; elétrica em eletroduto PVC corrugado
flexível (campo: eletroduto corrugado PEAD); hidrantes em PEAD; alarme em eletroduto PEAD.

ESCOPO
Redes externas da implantação, da face das paredes das edificações para fora. As redes ficam interrompidas na face de cada
edificação.

PRINCIPAIS ALTERAÇÕES
- Profundidade (topo do tubo): água potável 1,20 m; água de reúso 1,40 m; hidrantes 1,85 m; alarme de 0,50 a 1,45 m; elétrica
  de 0,70 a 1,85 m, sempre acima das redes de água. Nos taludes entre os platôs as redes acompanham o terreno. A profundidade
  de cada trecho de elétrica e de alarme muda só nas caixas; o valor de cada trecho está indicado nas pranchas.
- Eletrodutos de elétrica e de alarme contornam em planta caixas de esgoto e drenagem pluvial mais fundas (EL-001, EL-002 e
  IN-001), sem descer no meio do trecho; as derivações da iluminação externa ficam dentro da caixa do poste mais próximo.
- Caixas de passagem de elétrica e alarme deslocadas de 0,26 a 2,50 m para sair de cima de outras redes; os eletrodutos
  acompanham.
- Oito postes da iluminação externa deslocados de 0,26 a 1,30 m junto com a caixa da base (a base estava sobre caixa de areia
  ou tubo da drenagem pluvial).
- Torneira de jardim TJ-02 recuada 1,46 m pelo próprio ramal (estava sobre a saída da drenagem pluvial AP-018).
- Esgoto e drenagem pluvial nas cotas do projeto. Caixas deslocadas em planta, sem mudar CT nem CF (os tubos que chegam nelas
  acompanham):
  drenagem pluvial: CA-01 1,20 m para dentro do platô (estava na crista do talude, onde o terreno existente fica 0,9 m abaixo
  da CT), CA-05 0,35 m (para afastar da CI-03 do esgoto) e PVP-09 0,24 m;
  esgoto: CI-02 0,25 m (o AP-145 passava no canto dela) e PVE-09 0,14 m (o AP-110 cortava a parede do poço).
- AP-199 (drenagem pluvial) chega na CA-04 com GI 235,13, 4 cm acima do fundo, para passar por cima do ESG-026.
- ESG-014 (esgoto) sai da PVE-06 5 cm mais baixo, para passar por baixo do AP-108: fundo da PVE-06 234,25 (era 234,30) e
  declividade do ESG-014 0,67 %.

PENDÊNCIA (recorte da prancha em 04_PENDENCIAS)
1. Galeria 2 × Ø1200 da DRE-001 ("rede futura se necessário"): não incluída no modelo; aguarda definição.
"""


def sobra(pasta, vale):
    """imagem de pendência que deixou de valer (resolvida por decisão) sai da pasta."""
    for x in glob.glob(os.path.join(pasta, '04_PENDENCIAS', '*.jpg')):
        if os.path.relpath(x, pasta) not in vale: os.remove(x); print('  saiu', os.path.relpath(x, pasta))


def main():
    p1, p2, p3, p4 = (os.path.join(OUT, x) for x in ('01_PRANCHAS_PDF', '02_PRANCHAS_DWG', '03_IFC', '04_PENDENCIAS'))
    for d in (p1, p2, p3, p4): os.makedirs(d, exist_ok=True)      # por cima (a pasta sincronizada não deixa apagar)
    for n in PRANCHAS:
        shutil.copy2(os.path.join(EXE, 'PDF', n + '.pdf'), p1); shutil.copy2(os.path.join(EXE, n + '.dwg'), p2)
    for lg in glob.glob(os.path.join(EXE, 'CARIMBO_QG_logo_*.png')): shutil.copy2(lg, p2)
    for o, d in NOMES.items(): print(d, limpar(os.path.join(IFC, o), os.path.join(p3, d)), 'propriedades de trabalho tiradas')
    for k, nome in PEND:
        src = next(iter(sorted(glob.glob(os.path.join(PEN, f'{k}_prancha_*.jpg')))), None)
        if src: shutil.copy2(src, os.path.join(p4, nome + '.jpg'))
    open(os.path.join(OUT, 'LEIA-ME.txt'), 'w', encoding='utf-8-sig').write(LEIA)
    vale = {os.path.join('04_PENDENCIAS', n + '.jpg') for _, n in PEND}
    sobra(OUT, vale)
    print(OUT)
    if '--drive' in sys.argv:
        shutil.copytree(OUT, DRIVE, dirs_exist_ok=True, ignore=shutil.ignore_patterns('desktop.ini')); sobra(DRIVE, vale); print(DRIVE)


if __name__ == '__main__':
    main()
