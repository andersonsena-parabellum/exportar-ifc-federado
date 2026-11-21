# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — publica no CDE as 8 pranchas da R03 com o carimbo QG as built (EXECUTIVO_R03_IFC/PDF_QG), conforme
FERRAMENTAS/pranchas_cde/LEIA-ME.md: PDF novo em PRANCHAS/ETIB-JANDAIRA/ e no Drive (ETIB_PRANCHAS_CDE/ETIB-JANDAIRA/), a revisão
anterior vai para _SUPERADAS/ nas duas; a CPS DRE-001 continua R02 (só o carimbo mudou): sobrescrita no lugar (mesmo ID no Drive),
a versão anterior em _SUPERADAS/ com sufixo _carimbo-antigo. Índice: linhas da Jandaíra (relido antes de gravar).
Uso: JAN_LIB='{"nome.pdf": "caminho na biblioteca"}' python -X utf8 jan_cde_r03.py"""
import os, re, shutil, json
SRC = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\PDF_QG'
DESTINOS = [r'D:\Projeto Modelagem\PRANCHAS\ETIB-JANDAIRA', r'G:\Meu Drive\ETIB_PRANCHAS_CDE\ETIB-JANDAIRA']
INDICE = r'D:\Projeto Modelagem\PRANCHAS\PRANCHAS_INDICE.md'
FOLHAS = {
    'Implantação: AF-001': ('24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG', 'R02', 'R03'),
    'Implantação: ESG-001': ('24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG', 'R02', 'R03'),
    'Implantação: DRE-001': ('24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG', 'R01', 'R02'),
    'Implantação: EL-001': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG', 'R02', 'R03'),
    'Implantação: EL-002': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG', 'R02', 'R03'),
    'Implantação: IN-001': ('24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING', 'R04', 'R05'),
    'Campo society: DRE-001': ('24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG', 'R02', 'R02'),
    'Campo society: EL-001': ('24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG', 'R02', 'R03'),
}
LIB = json.loads(os.environ.get('JAN_LIB', '{}') or '{}')
reg = []
for chave, (pre, ant, nov) in FOLHAS.items():
    src = os.path.join(SRC, f'{pre}-{nov}.pdf'); nome = f'{pre}-{nov}.pdf'
    if not os.path.exists(src): print(chave, ': PDF novo não achado'); continue
    for d in DESTINOS:
        os.makedirs(os.path.join(d, '_SUPERADAS'), exist_ok=True)
        atual = os.path.join(d, nome)
        if ant == nov:
            if os.path.exists(atual): shutil.copy2(atual, os.path.join(d, '_SUPERADAS', f'{pre}-{nov}_carimbo-antigo.pdf'))
        else:
            velho = os.path.join(d, f'{pre}-{ant}.pdf')
            if os.path.exists(velho): shutil.move(velho, os.path.join(d, '_SUPERADAS', os.path.basename(velho)))
        shutil.copyfile(src, atual)
    reg.append((chave, pre, ant, nov, nome)); print(chave, '->', nome)
s = open(INDICE, encoding='utf-8').read()
i0 = s.index('## Jandaíra'); i1 = s.find('\n## ', i0 + 5); i1 = len(s) if i1 < 0 else i1
sec = s[i0:i1]
for chave, pre, ant, nov, nome in reg:
    pad = re.compile(r'^\| ' + re.escape(chave) + r'([^|]*)\| [^|]*\| [^|]*\| [^\n]*$', re.M)
    m = pad.search(sec)
    if not m: raise SystemExit(f'linha do índice não achada: {chave}')
    sec = sec[:m.start()] + f'| {chave}{m.group(1)}| Modificada | {nov} | [{nome}](/mnt/project-files/{LIB.get(nome, nome)}) |' + sec[m.end():]
s = s[:i0] + sec + s[i1:]
s = re.sub(r'^Atualizado em [\d/]+\.', 'Atualizado em 20/10/2026.', s, flags=re.M)
open(INDICE, 'w', encoding='utf-8').write(s)
print('índice atualizado')
