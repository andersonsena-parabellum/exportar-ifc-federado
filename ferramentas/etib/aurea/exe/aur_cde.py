# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — publica no CDE as pranchas revisadas do envio (FERRAMENTAS/pranchas_cde/LEIA-ME.md, passos 1 e 4; mesmo
esquema do satiro/exe/sat_cde.py): PDF novo em PRANCHAS/ETIB-APORA-PROF-AUREA e em G:/Meu Drive/ETIB_PRANCHAS_CDE/ETIB-APORA-PROF-AUREA,
a anterior vai para _SUPERADAS nas duas, e o bloco da Áurea no PRANCHAS_INDICE.md (local e Drive) é reescrito: AF-002 e EL-001
"Modificada" R01, IN-001 "Original" R00 (não mudou). Regra A4 (Anderson, 22/10/2026): o CDE sai no mesmo passo do envio.
Uso: python -X utf8 aur_cde.py"""
import os, shutil, re

PDF = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\ENVIO_2026-10-23\01_PRANCHAS_PDF'
CDE = [r'D:\Projeto Modelagem\PRANCHAS', r'G:\Meu Drive\ETIB_PRANCHAS_CDE']
ESC = 'ETIB-APORA-PROF-AUREA'
# linha do índice -> (anterior no CDE, revisada)
FOLHAS = {'Implantação: AF-002 Drenagem': ('24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R00', '24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R01'),
          'Implantação: EL-001 Elétrica': ('24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R00', '24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R01')}
SEM_MUDANCA = {'Implantação: IN-001 Incêndio': '24-049-APR-CTO-ETIB-IMP-PE-IN-001-ING-R00'}
OBS = ('Compatibilização entregue em 23/10/2026. A lista mestra da construtora traz na implantação só a drenagem da quadra '
       '(folha AF-002), a elétrica e o incêndio.')


def indice(fn):
    s = open(fn, encoding='utf-8').read()
    a = s.index('## Aporá (Prof. Áurea)'); b = s.index('\n## ', a + 5)
    bloco = s[a:b]
    bloco = re.sub(r'^Drive incompleto.*$', OBS, bloco, count=1, flags=re.M)
    for rot, (_, novo) in FOLHAS.items():
        linha = f'| {rot} | Modificada | {novo[-3:]} | [{novo}.pdf](/mnt/project-files/{novo}.pdf) |'
        bloco, n = re.subn(r'^\| ' + re.escape(rot) + r' \|.*$', linha, bloco, flags=re.M)
        assert n == 1, rot
    for rot, nome in SEM_MUDANCA.items():
        linha = f'| {rot} | Original | {nome[-3:]} (PDF plotado do DWG) | [{nome}.pdf](/mnt/project-files/{nome}.pdf) |'
        bloco, n = re.subn(r'^\| ' + re.escape(rot) + r' \|.*$', linha, bloco, flags=re.M)
        assert n == 1, rot
    s = s[:a] + bloco + s[b:]
    s = re.sub(r'^Atualizado em \d\d/\d\d/\d{4}\.', 'Atualizado em 23/10/2026.', s, count=1, flags=re.M)
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
