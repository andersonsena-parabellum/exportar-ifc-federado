# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — publica no CDE as 8 folhas refeitas a partir do modelo IFC (EXECUTIVO_R02_IFC/PDF),
conforme FERRAMENTAS/pranchas_cde/LEIA-ME.md:
  - as 6 folhas que já tinham saído na tarde de 19/10 mantêm a revisão (o pacote ainda não tinha sido entregue): o PDF é
    sobrescrito no lugar (o Drive mantém o mesmo ID) e a versão da tarde vai para _SUPERADAS/ com o sufixo _versao-19-10-tarde;
  - ESG-001 R02 e CPS EL-001 R02 entram pela primeira vez: a original vai para _SUPERADAS/;
  - PRANCHAS_INDICE.md: linhas da Jandaíra em "Modificada" com a revisão nova (relido antes de gravar).
Uso: python -X utf8 jan_cde_ifc.py"""
import os, re, glob, shutil, json
OUT = os.path.join(os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC', 'PDF')
DESTINOS = [r'D:\Projeto Modelagem\PRANCHAS\ETIB-JANDAIRA', r'G:\Meu Drive\ETIB_PRANCHAS_CDE\ETIB-JANDAIRA']
INDICE = r'D:\Projeto Modelagem\PRANCHAS\PRANCHAS_INDICE.md'
FOLHAS = {  # código no índice -> (prefixo do arquivo, revisão anterior, revisão nova)
    'Implantação: AF-001': ('24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG', 'R01', 'R02'),
    'Implantação: ESG-001': ('24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG', 'R01', 'R02'),
    'Implantação: DRE-001': ('24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG', 'R00', 'R01'),
    'Implantação: EL-001': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG', 'R01', 'R02'),
    'Implantação: EL-002': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG', 'R01', 'R02'),
    'Implantação: IN-001': ('24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING', 'R03', 'R04'),
    'Campo society: DRE-001': ('24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG', 'R01', 'R02'),
    'Campo society: EL-001': ('24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG', 'R01', 'R02'),
}
LIB = json.loads(os.environ.get('JAN_LIB', '{}') or '{}')     # nome do PDF -> caminho na biblioteca do projeto (se o upload ganhou sufixo)
reg = []
for chave, (pre, ant, nov) in FOLHAS.items():
    src = glob.glob(os.path.join(OUT, f'{pre}-{nov}_*.pdf'))
    if len(src) != 1: print(f'{chave}: PDF novo não achado ({src}), fica como está'); continue
    nome = f'{pre}-{nov}.pdf'
    for d in DESTINOS:
        os.makedirs(os.path.join(d, '_SUPERADAS'), exist_ok=True)
        atual = os.path.join(d, nome)
        if os.path.exists(atual): shutil.copy2(atual, os.path.join(d, '_SUPERADAS', f'{pre}-{nov}_versao-19-10-tarde.pdf'))
        velho = os.path.join(d, f'{pre}-{ant}.pdf')
        if os.path.exists(velho): shutil.move(velho, os.path.join(d, '_SUPERADAS', os.path.basename(velho)))
        shutil.copyfile(src[0], atual)            # sobrescreve o conteúdo no lugar: o arquivo do Drive continua o mesmo
    reg.append((chave, pre, ant, nov, nome))
    print(chave, '->', nome)
s = open(INDICE, encoding='utf-8').read()
i0 = s.index('## Jandaíra'); i1 = s.find('\n## ', i0 + 5); i1 = len(s) if i1 < 0 else i1
sec = s[i0:i1]
for chave, pre, ant, nov, nome in reg:
    pad = re.compile(r'^\| ' + re.escape(chave) + r'([^|]*)\| [^|]*\| [^|]*\| [^\n]*$', re.M)
    m = pad.search(sec)
    if not m: raise SystemExit(f'linha do índice não achada: {chave}')
    sec = sec[:m.start()] + f'| {chave}{m.group(1)}| Modificada | {nov} | [{nome}](/mnt/project-files/{LIB.get(nome, nome)}) |' + sec[m.end():]
s = s[:i0] + sec + s[i1:]
s = re.sub(r'^Atualizado em [\d/]+\.', 'Atualizado em 19/10/2026.', s, flags=re.M)
open(INDICE, 'w', encoding='utf-8').write(s)
json.dump(reg, open(os.path.join(OUT, '..', 'JAN_cde.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('índice atualizado')
