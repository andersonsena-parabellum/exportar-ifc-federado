# -*- coding: utf-8 -*-
"""Jandaíra — publica no CDE as folhas refeitas (EXECUTIVO_R02/PDF), conforme FERRAMENTAS/pranchas_cde/LEIA-ME.md:
  1) PDF novo em PRANCHAS/ETIB-JANDAIRA/ e em G:/Meu Drive/ETIB_PRANCHAS_CDE/ETIB-JANDAIRA/, com o nome oficial da folha;
     a versão anterior vai para _SUPERADAS/ nas duas;
  2) linhas da Jandaíra no PRANCHAS_INDICE.md passam a "Modificada" com a revisão nova (o índice é relido antes de gravar).
Os IDs do Drive (pranchas_json.py, MODIFICADAS) e a publicação do pranchas.json ficam para depois da sincronização do Drive.
Uso: python -X utf8 jan_cde.py"""
import os, re, glob, shutil, json
OUT = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02\PDF'
DESTINOS = [r'D:\Projeto Modelagem\PRANCHAS\ETIB-JANDAIRA', r'G:\Meu Drive\ETIB_PRANCHAS_CDE\ETIB-JANDAIRA']
INDICE = r'D:\Projeto Modelagem\PRANCHAS\PRANCHAS_INDICE.md'
FOLHAS = {  # código no índice -> (prefixo do arquivo, revisão anterior, revisão nova)
    'Implantação: AF-001': ('24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG', 'R01', 'R02'),
    'Implantação: DRE-001': ('24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG', 'R00', 'R01'),
    'Implantação: EL-001': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG', 'R01', 'R02'),
    'Implantação: EL-002': ('24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG', 'R01', 'R02'),
    'Implantação: IN-001': ('24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING', 'R03', 'R04'),
    'Campo society: DRE-001': ('24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG', 'R01', 'R02'),
}
reg = []
for chave, (pre, ant, nov) in FOLHAS.items():
    src = glob.glob(os.path.join(OUT, f'{pre}-{nov}_*.pdf'))
    if len(src) != 1: raise SystemExit(f'{chave}: PDF novo não achado ({src})')
    nome = f'{pre}-{nov}.pdf'
    for d in DESTINOS:
        os.makedirs(os.path.join(d, '_SUPERADAS'), exist_ok=True)
        velho = os.path.join(d, f'{pre}-{ant}.pdf')
        if os.path.exists(velho): shutil.move(velho, os.path.join(d, '_SUPERADAS', os.path.basename(velho)))
        shutil.copy2(src[0], os.path.join(d, nome))
    reg.append((chave, pre, ant, nov, nome))
    print(chave, '->', nome)
# índice: relido agora, só as linhas da Jandaíra mudam
s = open(INDICE, encoding='utf-8').read()
i0 = s.index('## Jandaíra'); i1 = s.find('\n## ', i0 + 5); i1 = len(s) if i1 < 0 else i1
sec = s[i0:i1]
for chave, pre, ant, nov, nome in reg:
    pad = re.compile(r'^\| ' + re.escape(chave) + r'([^|]*)\| [^|]*\| [^|]*\| [^\n]*$', re.M)
    m = pad.search(sec)
    if not m: raise SystemExit(f'linha do índice não achada: {chave}')
    sec = sec[:m.start()] + f'| {chave}{m.group(1)}| Modificada | {nov} | [{nome}](/mnt/project-files/{nome}) |' + sec[m.end():]
s = s[:i0] + sec + s[i1:]
if '**Modificada**' not in s:
    s = s.replace('Até a nova versão entrar aqui, vale a original listada.\n',
                  'Até a nova versão entrar aqui, vale a original listada.\n- **Modificada**: a folha já refeita com as mudanças da compatibilização, na revisão seguinte '
                  '(linha nova no quadro de revisões do carimbo). É a que vale; a anterior fica em `_SUPERADAS\\`.\n')
s = re.sub(r'^Atualizado em [\d/]+\.', 'Atualizado em 19/10/2026.', s, flags=re.M)
open(INDICE, 'w', encoding='utf-8').write(s)
json.dump(reg, open(os.path.join(OUT, '..', 'JAN_cde.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('índice atualizado')
