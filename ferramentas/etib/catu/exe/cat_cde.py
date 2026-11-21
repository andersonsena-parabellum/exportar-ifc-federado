# -*- coding: utf-8 -*-
"""Catu — publica no CDE as pranchas revisadas do envio (FERRAMENTAS/pranchas_cde/LEIA-ME.md, passos 1 e 4; mesmo esquema do
aurea/exe/aur_cde.py): PDF novo em PRANCHAS/ETIB-CATU e em G:/Meu Drive/ETIB_PRANCHAS_CDE/ETIB-CATU, a anterior vai para _SUPERADAS
nas duas, e o bloco da Catu no PRANCHAS_INDICE.md (local e Drive) é reescrito: as 6 folhas revisadas "Modificada"; DRE-002 e
DRE-003 ficam "Original" (não mudaram). Regra A4 (Anderson, 22/10/2026): o CDE sai no mesmo passo do envio.
Uso: python -X utf8 cat_cde.py"""
import os, shutil, re

PDF = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\ENVIO_2026-10-25\01_PRANCHAS_PDF'
CDE = [r'D:\Projeto Modelagem\PRANCHAS', r'G:\Meu Drive\ETIB_PRANCHAS_CDE']
ESC = 'ETIB-CATU'
_P = '24-049-CAU-RNV-ETIB-IMP-PE-'
# linha do índice -> (anterior no CDE, revisada)
FOLHAS = {'Implantação: AGF-001 Água fria': (_P + 'AGF-001-R02', _P + 'AGF-001-R03'),
          'Implantação: ESG-001 Esgoto': (_P + 'ESG-001-HIG-R02', _P + 'ESG-001-HIG-R03'),
          'Implantação: DRE-001 Drenagem': (_P + 'DRE-001-DRG-R02', _P + 'DRE-001-DRG-R03'),
          'Implantação: EL-001 Elétrica': (_P + 'EL-001-ELG-R05', _P + 'EL-001-ELG-R06'),
          'Implantação: EL-002 Elétrica': (_P + 'EL-002-ELG-R02', _P + 'EL-002-ELG-R03'),
          'Implantação: INC-001 Incêndio': (_P + 'INC-001-ING-R03', _P + 'INC-001-ING-R04')}


def indice(fn):
    s = open(fn, encoding='utf-8').read()
    a = s.index('## Catu'); b = s.index('\n## ', a + 5)
    bloco = s[a:b]
    for rot, (_, novo) in FOLHAS.items():
        linha = f'| {rot} | Modificada | {novo[-3:]} | [{novo}.pdf](/mnt/project-files/{novo}.pdf) |'
        bloco, n = re.subn(r'^\| ' + re.escape(rot) + r' \|.*$', linha, bloco, flags=re.M)
        assert n == 1, rot
    s = s[:a] + bloco + s[b:]
    s = re.sub(r'^Atualizado em \d\d/\d\d/\d{4}\.', 'Atualizado em 25/10/2026.', s, count=1, flags=re.M)
    open(fn, 'w', encoding='utf-8').write(s)


def main():
    for raiz in CDE:
        pasta = os.path.join(raiz, ESC); sup = os.path.join(pasta, '_SUPERADAS'); os.makedirs(sup, exist_ok=True)
        for velho, novo in FOLHAS.values():
            shutil.copy2(os.path.join(PDF, novo + '.pdf'), os.path.join(pasta, novo + '.pdf'))
            v = os.path.join(pasta, velho + '.pdf')
            if os.path.exists(v): shutil.move(v, os.path.join(sup, velho + '.pdf'))
            print(' ', pasta, novo)
        indice(os.path.join(raiz, 'PRANCHAS_INDICE.md'))
    print('índice atualizado nas duas cópias')


if __name__ == '__main__':
    main()
