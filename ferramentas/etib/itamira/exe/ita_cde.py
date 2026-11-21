# -*- coding: utf-8 -*-
"""Aporá Itamira — publica no CDE a DRE-001 R01 do envio de 23/10/2026 (FERRAMENTAS/pranchas_cde/LEIA-ME.md, passos 1 e 4, como
satiro/exe/sat_cde.py): PDF novo em PRANCHAS/ETIB-APORA-ITAMIRA e em G:/Meu Drive/ETIB_PRANCHAS_CDE/ETIB-APORA-ITAMIRA, a R00 vai para
_SUPERADAS nas duas, e a linha da folha no PRANCHAS_INDICE.md (local e Drive) passa a "Modificada".
Uso: python -X utf8 ita_cde.py"""
import os, shutil, re

PDF = r'D:\Projeto Modelagem\ETIB-APORA-ITAMIRA\RELATORIOS\EXECUTIVO_2026-10-24\PDF'
CDE = [r'D:\Projeto Modelagem\PRANCHAS', r'G:\Meu Drive\ETIB_PRANCHAS_CDE']
ESC = 'ETIB-APORA-ITAMIRA'
FOLHAS = {'Implantação: DRE-001 Drenagem': ('24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R00', '24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R01'),
          'Implantação: EL-001 Elétrica': ('24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R00', '24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R01')}
INTRO = ('Intervenção = campo society + pista. O Drive não traz AF, ESG nem PCI da implantação. Compatibilização entregue em 22/10/2026; '
         'em 23/10/2026 a DRE-001 passou à R01, com a drenagem do campo desenhada conforme executada (as built); em 24/10/2026 a EL-001 passou à R01, com a alimentação do quadro do campo executado.')


def indice(fn):
    s = open(fn, encoding='utf-8').read()
    a = s.index('## Aporá (Itamira)'); b = s.index('\n## ', a + 5)
    bloco = s[a:b]
    bloco = re.sub(r'^Intervenção = campo society.*$', INTRO, bloco, count=1, flags=re.M)
    for rot, (_, novo) in FOLHAS.items():
        linha = f'| {rot} | Modificada | {novo[-3:]} | [{novo}.pdf](/mnt/project-files/{novo}.pdf) |'
        bloco, n = re.subn(r'^\| ' + re.escape(rot) + r' \|.*$', linha, bloco, flags=re.M)
        assert n == 1, rot
    s = s[:a] + bloco + s[b:]
    s = re.sub(r'^Atualizado em \d\d/\d\d/\d{4}\.', 'Atualizado em 24/10/2026.', s, count=1, flags=re.M)
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
