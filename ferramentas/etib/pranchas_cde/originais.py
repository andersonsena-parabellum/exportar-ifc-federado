# -*- coding: utf-8 -*-
"""CDE das pranchas (19/10/2026): versão ORIGINAL (Drive da construtora) de cada folha do escopo.
As folhas que têm versão modificada ficam marcadas 'em revisão' (vão ser refeitas no padrão de campo).
Item: (escola, sub, folha, rev_original, fonte, rev_modificada)  fonte = PDF ou ('PLOT', dwg); rev_modificada '' = sem revisão."""
import os
P = r'D:\Projeto Modelagem'
ALH = P + r'\ETIB-ALAGOINHAS\4 - IMPLANTAÇÃO-20261008T151806Z-1-001\4 - IMPLANTAÇÃO'
BA2 = P + r'\ETIB-ALAGOINHAS\PROJETO_ORIGINAL\BA2'
ITA = P + r'\ETIB-APORA-ITAMIRA\PROJETO_ORIGINAL'
AUR = P + r'\ETIB-APORA-PROF-AUREA\PROJETO_ORIGINAL'
CAT = P + r'\ETIB-CATU\PROJETO_ORIGINAL\IMP'
JAN = P + r'\ETIB-JANDAIRA\PROJETO_ORIGINAL'
PJC = P + r'\ETIB-POJUCA\PROJETO_ORIGINAL'
SAT = P + r'\ETIB-SATIRO-DIAS\PROJETO_ORIGINAL'
ONN = P + r'\ETIB-OLINDINA\PROJETO_ORIGINAL\IMP'
a = '24-049-ALH-SLJ-ETIB-IMP-PE'; b = '24-049-ALH-SLJ-ETIB-BA2-PE'
def T(x): return ('PLOT', x)
L = [
 ('ETIB-ALAGOINHAS', 'IMP', 'AGF-001 Água fria', 'R06', rf'{ALH}\9 - REDE DE ÁGUA\{a}-AGF-001-R06.pdf', 'R07'),
 ('ETIB-ALAGOINHAS', 'IMP', 'ESG-001 Esgoto', 'R06', rf'{ALH}\10 - REDE DE ESGOTO\{a}-ESG-001-HIG-R06.pdf', 'R07'),
 ('ETIB-ALAGOINHAS', 'IMP', 'DRE-001 Drenagem', 'R04', rf'{ALH}\8 - DRENAGEM\{a}-DRE-001-DRG-R04.pdf', 'R05'),
 ('ETIB-ALAGOINHAS', 'IMP', 'EL-001 Elétrica', 'R07', rf'{ALH}\12 - REDE ELÉTRICA E ILUMINAÇÃO\PDF\{a}-EL-001-ELG-R07.pdf', 'R08'),
 ('ETIB-ALAGOINHAS', 'IMP', 'EL-002 Elétrica', 'R05', rf'{ALH}\12 - REDE ELÉTRICA E ILUMINAÇÃO\PDF\{a}-EL-002-ELG-R05.pdf', 'R06'),
 ('ETIB-ALAGOINHAS', 'IMP', 'IN-001 Incêndio', 'R05', rf'{ALH}\14 - COMBATE A INCÊNDIO\{a}-IN-001-ING-R05.pdf', 'R06'),
 ('ETIB-ALAGOINHAS', 'BA2', 'AF-001 Água fria', 'R01', rf'{BA2}\01_AF\{b}-AF-001-AFR-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'AF-002 Água fria (isométrico)', 'R01', rf'{BA2}\01_AF\{b}-AF-002-ISO-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'ESG-001 Esgoto', 'R01', rf'{BA2}\02_ESG\{b}-ESG-001-HIG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'ESG-002 Esgoto', 'R01', rf'{BA2}\02_ESG\{b}-ESG-002-HIG-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'ESG-003 Esgoto', 'R01', rf'{BA2}\02_ESG\{b}-ESG-003-HIG-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'DRE-001 Drenagem (cobertura)', 'R00', rf'{BA2}\03_DRE\{b}-DRE-001-COB-R00.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'DRE-002 Drenagem (pavimento)', 'R00', rf'{BA2}\03_DRE\{b}-DRE-002-PLB-R00.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-001 Elétrica', 'R01', rf'{BA2}\04_ELE\{b}-EL-001-ELG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-002 Elétrica', 'R01', rf'{BA2}\04_ELE\{b}-EL-002-ELG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-003 Elétrica', 'R03', rf'{BA2}\04_ELE\{b}-EL-003-ELG-R03.pdf', 'R04'),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-004 Elétrica', 'R03', rf'{BA2}\04_ELE\{b}-EL-004-ELG-R03.pdf', 'R04'),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-005 Elétrica', 'R02', rf'{BA2}\04_ELE\{b}-EL-005-ELG-R02.pdf', 'R03'),
 ('ETIB-ALAGOINHAS', 'BA2', 'EL-006 Elétrica', 'R01', rf'{BA2}\04_ELE\{b}-EL-006-ELG-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-001 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-001-ING-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-002 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-002-ING-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-003 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-003-ING-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-004 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-004-ING-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-005 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-005-ING-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-006 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-006-ING-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'IN-007 Incêndio', 'R01', rf'{BA2}\05_PCI\{b}-IN-007-ING-R01.pdf', ''),
 ('ETIB-ALAGOINHAS', 'BA2', 'AR-001 Climatização', 'R01', rf'{BA2}\06_CLI\{b}-AR-001-ELG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'AR-002 Climatização', 'R01', rf'{BA2}\06_CLI\{b}-AR-002-ELG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'AR-003 Climatização', 'R01', rf'{BA2}\06_CLI\{b}-AR-003-ELG-R01.pdf', 'R02'),
 ('ETIB-ALAGOINHAS', 'BA2', 'AR-004 Climatização', 'R01', rf'{BA2}\06_CLI\{b}-AR-004-ELG-R01.pdf', ''),

 ('ETIB-APORA-ITAMIRA', 'IMP', 'DRE-001 Drenagem', 'R00', T(rf'{ITA}\IMP\03_DRE\24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R00.dwg'), ''),  # 22/10: entrega sem alteração de folha
 ('ETIB-APORA-ITAMIRA', 'IMP', 'EL-001 Elétrica', 'R00', T(rf'{ITA}\IMP\04_ELE\24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R00.dwg'), ''),  # 22/10: entrega sem alteração de folha
 ('ETIB-APORA-ITAMIRA', 'CPS', 'DRE-001 Drenagem do campo', 'R01', rf'{ITA}\CPS\03_DRE\24-049-APR-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.pdf', ''),
 ('ETIB-APORA-ITAMIRA', 'CPS', 'EL-001 Elétrica do campo', 'R01', rf'{ITA}\CPS\04_ELE\24-049-APR-CTO-ETIB-CPS-PE-EL-001-ELG-R01.pdf', ''),
 ('ETIB-APORA-ITAMIRA', 'CPS', 'IN-001 Incêndio do campo', 'R01', rf'{ITA}\CPS\05_PCI\24-049-APR-CTO-ETIB-CPS-PE-IN-001-ING-R01.pdf', ''),
 ('ETIB-APORA-ITAMIRA', 'CPS', 'IN-002 Incêndio do campo', 'R01', rf'{ITA}\CPS\05_PCI\24-049-APR-CTO-ETIB-CPS-PE-IN-002-ING-R01.pdf', ''),

 ('ETIB-APORA-PROF-AUREA', 'IMP', 'AF-002 Drenagem', 'R00', T(rf'{AUR}\IMP\03_DRE\24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R00.dwg'), 'R01'),
 ('ETIB-APORA-PROF-AUREA', 'IMP', 'EL-001 Elétrica', 'R00', T(rf'{AUR}\IMP\04_ELE\24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg'), 'R01'),
 ('ETIB-APORA-PROF-AUREA', 'IMP', 'IN-001 Incêndio', 'R00', T(rf'{AUR}\IMP\05_PCI\24-049-APR-CTO-ETIB-IMP-PE-IN-001-ING-R00.dwg'), None),

 ('ETIB-CATU', 'IMP', 'AGF-001 Água fria', 'R02', rf'{CAT}\01_AF\24-049-CAU-RNV-ETIB-IMP-PE-AGF-001-R02.pdf', 'R03'),
 ('ETIB-CATU', 'IMP', 'ESG-001 Esgoto', 'R02', rf'{CAT}\02_ESG\24-049-CAU-RNV-ETIB-IMP-PE-ESG-001-HIG-R02.pdf', ''),
 ('ETIB-CATU', 'IMP', 'DRE-001 Drenagem', 'R02', rf'{CAT}\03_DRE\24-049-CAU-RNV-ETIB-IMP-PE-DRE-001-DRG-R02.pdf', ''),
 ('ETIB-CATU', 'IMP', 'DRE-002 Drenagem', 'R00', rf'{CAT}\03_DRE\24-049-CAU-RNV-ETIB-IMP-PE-DRE-002-DRG-R00.pdf', ''),
 ('ETIB-CATU', 'IMP', 'DRE-003 Drenagem', 'R00', rf'{CAT}\03_DRE\24-049-CAU-RNV-ETIB-IMP-PE-DRE-003-DRG-R00.pdf', ''),
 ('ETIB-CATU', 'IMP', 'EL-001 Elétrica', 'R05', rf'{CAT}\04_ELE\24-049-CAU-RNV-ETIB-IMP-PE-EL-001-ELG-R05.pdf', 'R06'),
 ('ETIB-CATU', 'IMP', 'EL-002 Elétrica', 'R02', rf'{CAT}\04_ELE\24-049-CAU-RNV-ETIB-IMP-PE-EL-002-ELG-R02.pdf', 'R03'),
 ('ETIB-CATU', 'IMP', 'INC-001 Incêndio', 'R03', rf'{CAT}\05_PCI\24-049-CAU-RNV-ETIB-IMP-PE-INC-001-ING-R03.pdf', 'R04'),

 ('ETIB-JANDAIRA', 'IMP', 'AF-001 Água fria', 'R01', T(rf'{JAN}\IMP\01_AF\24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R01.dwg'), 'R01 + REV-R01'),
 ('ETIB-JANDAIRA', 'IMP', 'ESG-001 Esgoto', 'R01', T(rf'{JAN}\IMP\02_ESG\24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R01.dwg'), ''),
 ('ETIB-JANDAIRA', 'IMP', 'DRE-001 Drenagem', 'R00', T(rf'{JAN}\IMP\03_DRE\24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg'), 'R00 + REV-R01'),
 ('ETIB-JANDAIRA', 'IMP', 'EL-001 Elétrica', 'R01', T(rf'{JAN}\IMP\04_ELE\24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R01.dwg'), 'R01 + REV-R01'),
 ('ETIB-JANDAIRA', 'IMP', 'EL-002 Elétrica', 'R01', T(rf'{JAN}\IMP\04_ELE\24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R01.dwg'), 'R01 + REV-R01'),
 ('ETIB-JANDAIRA', 'IMP', 'IN-001 Incêndio', 'R03', rf'{JAN}\IMP\05_PCI\24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R03.pdf', 'R03 + REV-R01'),
 ('ETIB-JANDAIRA', 'CPS', 'DRE-001 Drenagem do campo', 'R01', rf'{JAN}\CPS\03_DRE\24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.pdf', 'R01 + REV-R01'),
 ('ETIB-JANDAIRA', 'CPS', 'EL-001 Elétrica do campo', 'R01', rf'{JAN}\CPS\04_ELE\24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R01.pdf', ''),
 ('ETIB-JANDAIRA', 'CPS', 'IN-001 Incêndio do campo', 'R01', rf'{JAN}\CPS\05_PCI\24-049-JDI-CTO-ETIB-CPS-PE-IN-001-ING-R01.pdf', ''),
 ('ETIB-JANDAIRA', 'CPS', 'IN-002 Incêndio do campo', 'R00', rf'{JAN}\CPS\05_PCI\24-049-JDI-CTO-ETIB-CPS-PE-IN-002-ING-R00.pdf', ''),

 ('ETIB-POJUCA', 'IMP', 'AF-001 Água fria', 'R00', T(rf'{PJC}\IMP\01_AF\24-049-PJC-CTO-ETIB-IMP-PE-AF-001-AFR-R00.dwg'), 'R01'),
 ('ETIB-POJUCA', 'IMP', 'ESG-001 Esgoto', 'R00', T(rf'{PJC}\IMP\02_ESG\24-049-PJC-CTO-ETIB-IMP-PE-ESG-001-HIG-R00.dwg'), ''),
 ('ETIB-POJUCA', 'IMP', 'DRE-001 Drenagem', 'R00', T(rf'{PJC}\IMP\03_DRE\24-049-PJC-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg'), ''),
 ('ETIB-POJUCA', 'IMP', 'EL-001 Elétrica', 'R00', T(rf'{PJC}\IMP\04_ELE\24-049-PJC-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg'), 'R01'),
 ('ETIB-POJUCA', 'IMP', 'EL-002 Elétrica', 'R00', T(rf'{PJC}\IMP\04_ELE\24-049-PJC-CTO-ETIB-IMP-PE-EL-002-ELG-R00.dwg'), 'R01'),
 ('ETIB-POJUCA', 'IMP', 'IC-001 Incêndio', 'R01', rf'{PJC}\IMP\05_PCI\24-049-PJC-CTO-ETIB-IMP-PE-IC-001-INC-R01.pdf', 'R02'),
 ('ETIB-POJUCA', 'IMP', 'IN-001 Incêndio', 'R00', T(rf'{PJC}\IMP\05_PCI\24-049-PJC-CTO-ETIB-IMP-PE-IN-001-ING-R00.dwg'), ''),
 ('ETIB-POJUCA', 'CPS', 'DRE-001 Drenagem do campo', 'R01', T(rf'{PJC}\CPS\03_DRE\24-049-PJC-CTO-ETIB-CPS-PE-DRE-001-DRG-R01.dwg'), ''),
 ('ETIB-POJUCA', 'CPS', 'EL-001 Elétrica do campo', 'R01', T(rf'{PJC}\CPS\04_ELE\24-049-PJC-CTO-ETIB-CPS-PE-EL-001-ELG-R01.dwg'), 'R02'),
 ('ETIB-POJUCA', 'CPS', 'EL-002 Elétrica do campo', 'R00', rf'{PJC}\CPS\04_ELE\24-049-PJC-CTO-ETIB-CPS-PE-EL-002-ELG-R00.pdf', ''),
 ('ETIB-POJUCA', 'CPS', 'IN-001 Incêndio do campo', 'R01', rf'{PJC}\CPS\05_PCI\24-049-PJC-CTO-ETIB-CPS-PE-IN-001-ING-R01.pdf', ''),
 ('ETIB-POJUCA', 'CPS', 'IN-002 Incêndio do campo', 'R01', rf'{PJC}\CPS\05_PCI\24-049-PJC-CTO-ETIB-CPS-PE-IN-002-DGE-R01.pdf', ''),

 ('ETIB-SATIRO-DIAS', 'IMP', 'AF-001 Água fria', 'R00', T(rf'{SAT}\IMP\01_AF\24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00.dwg'), 'R01'),
 ('ETIB-SATIRO-DIAS', 'IMP', 'ESG-001 Esgoto', 'R00', T(rf'{SAT}\IMP\02_ESG\24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00.dwg'), 'R01'),
 ('ETIB-SATIRO-DIAS', 'IMP', 'DRE-001 Drenagem', 'R02', rf'{SAT}\IMP\03_DRE\24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02.pdf', ''),
 ('ETIB-SATIRO-DIAS', 'IMP', 'DRE-002 Drenagem', 'R02', rf'{SAT}\IMP\03_DRE\24-049-STK-XXX-ETIB-IMP-PE-DRE-002-DRG-R02.pdf', ''),
 ('ETIB-SATIRO-DIAS', 'IMP', 'EL-001 Elétrica', 'R01', rf'{SAT}\IMP\04_ELE\24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01.pdf', 'R02'),
 ('ETIB-SATIRO-DIAS', 'IMP', 'EL-002 Elétrica', 'R01', rf'{SAT}\IMP\04_ELE\24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R01.pdf', 'R02'),
 ('ETIB-SATIRO-DIAS', 'IMP', 'IN-001 Incêndio', 'R03', rf'{SAT}\IMP\05_PCI\24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03.pdf', 'R04'),
 ('ETIB-SATIRO-DIAS', 'CPS', 'DRE-001 Drenagem do campo', 'R01', rf'{SAT}\CPS\03_DRE\24-049-STK-XXX-ETIB-CPS-PE-DRE-001-DRG-R01.pdf', ''),
 ('ETIB-SATIRO-DIAS', 'CPS', 'ELE-001 Elétrica do campo', 'R00', rf'{SAT}\CPS\04_ELE\24-049-STK-XXX-CP1-CPS-PE-ELE-001-ELG-R00.pdf', 'R01'),
 ('ETIB-SATIRO-DIAS', 'CPS', 'ELE-002 Elétrica do campo', 'R00', rf'{SAT}\CPS\04_ELE\24-049-STK-XXX-CP1-CPS-PE-ELE-002-ELG-R00.pdf', ''),
 ('ETIB-SATIRO-DIAS', 'CPS', 'IN-001 Incêndio do campo', 'R01', rf'{SAT}\CPS\05_PCI\24-049-STK-XXX-ETIB-CPS-PE-IN-001-ING-R01.pdf', ''),
 ('ETIB-SATIRO-DIAS', 'CPS', 'IN-002 Incêndio do campo', 'R01', rf'{SAT}\CPS\05_PCI\24-049-STK-XXX-ETIB-CPS-PE-IN-002-ING-R01.pdf', ''),
 # Olindina (no contrato desde 21/10/2026): pranchas R00 só em DWG, plotadas em A0 pela thread da escola
 ('ETIB-OLINDINA', 'IMP', 'AF-001 Água fria', 'R00', T(rf'{ONN}\01_AF\24-049-ONN-CTO-ETIB-IMP-PE-AF-001-AFR-R00.dwg'), ''),
 ('ETIB-OLINDINA', 'IMP', 'ESG-001 Esgoto e pluvial', 'R00', T(rf'{ONN}\02_ESG\24-049-ONN-CTO-ETIB-IMP-PE-ESG-001-HIG-R00.dwg'), ''),
 ('ETIB-OLINDINA', 'IMP', 'DRE-001 Drenagem', 'R00', T(rf'{ONN}\03_DRE\24-049-ONN-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dwg'), ''),
 ('ETIB-OLINDINA', 'IMP', 'EL-001 Elétrica', 'R00', T(rf'{ONN}\04_ELE\24-049-ONN-CTO-ETIB-IMP-PE-EL-001-ELG-R00.dwg'), ''),
 ('ETIB-OLINDINA', 'IMP', 'IN-001 Incêndio', 'R00', T(rf'{ONN}\05_PCI\24-049-ONN-CTO-ETIB-IMP-PE-IN-001-ING-R00.dwg'), ''),
]

if __name__ == '__main__':
    import collections
    tot = collections.Counter(); falta = []; plot = []; dwg = 0
    for e, s, f, r, x, m in L:
        p = x[1] if isinstance(x, tuple) else x
        if not os.path.exists(p): falta.append(p); continue
        if isinstance(x, tuple): plot.append(p); dwg += os.path.getsize(p)
        else: tot[e] += os.path.getsize(p)
    for e in tot: print(f'{e:24s} {tot[e]/1e6:7.1f} MB')
    print('PDF prontos:', round(sum(tot.values()) / 1e6, 1), 'MB;', len(L), 'folhas;', sum(1 for i in L if i[5]), 'em revisão')
    print('a plotar:', len(plot), 'DWG somando', round(dwg / 1e6, 1), 'MB')
    print('FALTANDO:', *falta, sep='\n  ')
