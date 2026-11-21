# -*- coding: utf-8 -*-
"""Sátiro Dias — publica no CDE as pranchas revisadas do envio (FERRAMENTAS/pranchas_cde/LEIA-ME.md, passos 1 e 4; o pranchas.json não
se mexe): PDF novo em PRANCHAS/ETIB-SATIRO-DIAS e em G:/Meu Drive/ETIB_PRANCHAS_CDE/ETIB-SATIRO-DIAS, a anterior vai para _SUPERADAS
nas duas, e as linhas da Sátiro no PRANCHAS_INDICE.md (local e Drive) passam a "Modificada". Regra A4 (Anderson, 22/10/2026): o CDE sai
no mesmo passo do envio.
Uso: python -X utf8 sat_cde.py"""
import os, shutil, re

PDF = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS\EXECUTIVO_2026-10-21\PDF'
CDE = [r'D:\Projeto Modelagem\PRANCHAS', r'G:\Meu Drive\ETIB_PRANCHAS_CDE']
ESC = 'ETIB-SATIRO-DIAS'
# linha do índice -> (anterior no CDE, revisada)
FOLHAS = {'Implantação: AF-001 Água fria': ('24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00', '24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R01'),
          'Implantação: ESG-001 Esgoto': ('24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00', '24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R01'),
          'Implantação: EL-001 Elétrica': ('24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01', '24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R02'),
          'Implantação: EL-002 Elétrica': ('24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R01', '24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R02'),
          'Implantação: IN-001 Incêndio': ('24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03', '24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R04'),
          'Campo society: ELE-001 Elétrica do campo': ('24-049-STK-XXX-CP1-CPS-PE-ELE-001-ELG-R00', '24-049-STK-XXX-ETIB-CPS-PE-ELE-001-ELG-R01')}


def indice(fn):
    s = open(fn, encoding='utf-8').read()
    a = s.index('## Sátiro Dias'); b = s.index('\n## ', a + 5)
    bloco = s[a:b]
    for rot, (_, novo) in FOLHAS.items():
        rev = novo[-3:]
        linha = f'| {rot} | Modificada | {rev} | [{novo}.pdf](/mnt/project-files/{novo}.pdf) |'
        bloco, n = re.subn(r'^\| ' + re.escape(rot) + r' \|.*$', linha, bloco, flags=re.M)
        assert n == 1, rot
    s = s[:a] + bloco + s[b:]
    s = re.sub(r'^Atualizado em \d\d/\d\d/\d{4}\.', 'Atualizado em 22/10/2026.', s, count=1, flags=re.M)
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
