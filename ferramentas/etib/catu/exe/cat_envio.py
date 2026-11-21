# -*- coding: utf-8 -*-
"""Catu — pasta de envio (mesma estrutura da Prof. Áurea, aurea/exe/aur_envio.py), montada em RELATORIOS/ENVIO_2026-10-25;
cópia para G:/Meu Drive/ETIB_ENVIOS/ETIB-CATU_2026-10-25 com --drive (depois do checklist APROVADO):
  01_PRANCHAS_PDF, 02_PRANCHAS_DWG (+ logos do carimbo), 03_IFC (cópia de entrega sem as propriedades de trabalho, nomes CAT_IMP_*)
  e LEIA-ME.txt.
Uso: .venv/Scripts/python.exe -X utf8 catu/exe/cat_envio.py [--drive]"""
import os, sys, shutil, glob
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe')
from onn_envio import limpar

REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
EXE = os.path.join(REL, 'EXECUTIVO_2026-10-25'); IFC = os.path.join(REL, 'ENTREGA_IFC_2026-10-25')
OUT = os.path.join(REL, 'ENVIO_2026-10-25')
DRIVE = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-CATU_2026-10-25'
PRANCHAS = ['24-049-CAU-RNV-ETIB-IMP-PE-AGF-001-R03', '24-049-CAU-RNV-ETIB-IMP-PE-ESG-001-HIG-R03', '24-049-CAU-RNV-ETIB-IMP-PE-DRE-001-DRG-R03',
            '24-049-CAU-RNV-ETIB-IMP-PE-EL-001-ELG-R06', '24-049-CAU-RNV-ETIB-IMP-PE-EL-002-ELG-R03', '24-049-CAU-RNV-ETIB-IMP-PE-INC-001-ING-R04']
NOMES = {'CAT_IMP_HIDRO_R01.ifc': 'CAT_IMP_HIDRO_R01.ifc', 'CAT_IMP_ELE_R01.ifc': 'CAT_IMP_ELETRICA_R01.ifc',
         'CAT_IMP_PCIP_R01.ifc': 'CAT_IMP_PCI_R01.ifc', 'CAT_IMP_EST_R01.ifc': 'CAT_IMP_ESTRUTURA_R01.ifc',
         'CAT_TERRENO_R01.ifc': 'CAT_IMP_TERRENO_R01.ifc', 'CAT_FEDERADO_R01.ifc': 'CAT_IMP_FEDERADO_R01.ifc'}

LEIA = """ETIB CATU (24-049-CAU) — COMPATIBILIZAÇÃO DAS REDES EXTERNAS DA IMPLANTAÇÃO
Envio de 25/10/2026

CONTEÚDO
01_PRANCHAS_PDF   Pranchas revisadas em PDF (A0)
02_PRANCHAS_DWG   As mesmas pranchas em DWG (os logos do carimbo são as imagens PNG da mesma pasta)
03_IFC            Modelos IFC por disciplina, estrutura de referência, terreno e federado (SIRGAS 2000 / UTM 24S, EPSG 31984)

PRANCHAS
  AGF-001   Água fria ................................ R03
  ESG-001   Esgoto ................................... R03
  DRE-001   Drenagem pluvial ......................... R03
  EL-001    Elétrica (alimentação) ................... R06
  EL-002    Elétrica (iluminação externa) ............ R03
  INC-001   Incêndio (hidrantes e alarme) ............ R04
Cada folha está no carimbo padrão QG as built, com a linha nova no quadro de revisões.

MODELOS IFC
  CAT_IMP_HIDRO_R01.ifc ................ água fria, esgoto e drenagem pluvial
  CAT_IMP_ELETRICA_R01.ifc ............. elétrica enterrada (alimentação e iluminação externa)
  CAT_IMP_PCI_R01.ifc .................. hidrantes e alarme de incêndio
  CAT_IMP_ESTRUTURA_R01.ifc ............ fundação e arranques dos blocos novos (restaurante, casa de resíduos, guarita, subestação
                                         e abrigos), pelo as built (referência)
  CAT_IMP_TERRENO_R01.ifc .............. terreno acabado
  CAT_IMP_FEDERADO_R01.ifc ............. todas as disciplinas juntas
Cada peça está na classe IFC do que ela é (tubo, conexão, eletroduto, caixa de passagem, caixa de inspeção, poço de visita,
registro, hidrante, quadro, poste, sapata), com material, diâmetro e sistema. Material conforme a legenda das pranchas: água fria
em PVC soldável marrom; esgoto em PVC Série Normal (Série Reforçada onde indicado); pluvial em PVC Série Reforçada, Vinilfort nos
trechos PVC-V e dreno corrugado perfurado nos PVC-DR; hidrante em PEAD 2.1/2"; alarme em eletroduto PEAD Ø2"; elétrica enterrada em
eletroduto PEAD corrugado flexível.

ESCOPO
Redes externas da implantação, da face da parede dos prédios para fora: água fria, esgoto, drenagem pluvial, elétrica enterrada
(alimentação e iluminação externa), hidrantes e alarme de incêndio. As redes terminam na parede de cada prédio.

TERRENO
Terreno acabado do levantamento as built da implantação, com os platôs nas cotas da implantação e das caixas de esgoto e drenagem
das pranchas: campo 78,25; restaurante e bloco ao sul dele 82,50; bloco a oeste 82,00; teatro 84,50. As tampas das caixas ficam
nesse terreno.

PROFUNDIDADES
Hidrantes com o topo a 1,75 m do terreno, numa cota só; elétrica e alarme acima da água em todo cruzamento, com a profundidade de cada trecho mudando só dentro das caixas (notas "PROF." nas pranchas, uma por trecho). Esgoto e
drenagem com as cotas das pranchas. Profundidade máxima de 2,00 m do terreno ao topo do tubo.

PRINCIPAIS ALTERAÇÕES (todas dentro dos limites combinados: caixa de passagem até 1,50 m, caixa de gravidade até 0,60 m, chegada de
tubo de gravidade até 0,20 m acima do fundo, desvio lateral de pressurizada até 2,00 m)
- EL-002: o eletroduto EL2-025 (entre a EL2-CX03 e a EL2-CX02) estava desenhado sobre o esgoto entre a CE-04 e a CE-03, passando
  pelas caixas; passa paralelo, 0,70 m a sudeste do esgoto. A EL2-CX02 foi 1,49 m para o mesmo lado e a EL2-CX03 1,03 m.
- Caixas de passagem que estavam sobre caixas de esgoto ou de drenagem, ou sobre outra rede, deslocadas com os eletrodutos:
  EL1-CX12 (0,98 m), EL1-CX13 (0,82 m), EL2-CX04 (0,72 m), EL2-CX21 (0,42 m), EL2-CX08 (0,25 m); alarme CX-12 (1,32 m), CX-09
  (0,90 m), CX-21 (0,42 m), CX-02 (0,40 m), CX-19 e CX-20 (0,20 m); caixas dos registros RG-03 (1,20 m, pelo AF-10) e RG-01 (0,15 m, pelo AF-02).
- Eletrodutos, alarme, hidrante e água fria que atravessavam poços de visita contornam o PV a 0,30 m da parede: PVP-03 (AF-06 e
  SDAI-12), PVP-05 (EL2-013 e EL2-014), PVP-09 (banco EL1-005/010/025/038), PVP-13 (EL2-008 e HID-01), PVE-07 e PVE-08 (SDAI-38 e
  SDAI-36). O EL2-008 e o SDAI-38 também contornam as sapatas da casa de resíduos.
- Hidrante H-10 recuado 0,35 m pelo próprio ramal (estava sobre o tubo de drenagem DRE-205, na borda do campo).
- Caixa de areia CA-24 deslocada 0,34 m (encostava no ESG-14), com a cota de tampa e de fundo do projeto.
- Chegadas mais altas na caixa de jusante, mantendo a declividade mínima: ESG-04 na PVE-04 (0,13 m) e ESG-15 na PVE-03 (0,20 m);
  ramais das descidas AP-6 na PVP-02 (DRE-218, 0,20 m), AP-7 na CA-13 (DRE-125, 0,20 m) e AP-17/AP-18 na PVP-05 (0,10 m). Notas
  "CHEGADA NA ..." nas pranchas ESG-001 e DRE-001.

PENDÊNCIAS
Nenhuma colisão sem solução. Ficam para a construtora (pedido de 22/10): memoriais da água fria, do esgoto e da drenagem; projeto
de pavimentação; levantamento da parte sul do terreno (campo e quadra); cotas executadas dos platôs.
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
