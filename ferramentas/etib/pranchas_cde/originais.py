# -*- coding: utf-8 -*-
"""CDE das pranchas (19/10/2026): versão ORIGINAL (Drive da construtora) de cada folha do escopo.
As folhas que têm versão modificada ficam marcadas 'em revisão' (vão ser refeitas no padrão de campo).
Item: (escola, sub, folha, rev_original, fonte, rev_modificada)  fonte = PDF ou ('PLOT', dwg); rev_modificada '' = sem revisão."""
import os
P = r'D:\Projeto Modelagem'
# MODELO (valores fictícios). Uma constante por pasta de origem das folhas da escola.
EXE = P + r'\ETIB-<ESCOLA>\PROJETO_ORIGINAL'
CTR = '<CTR>'          # prefixo do contrato no nome das folhas (ex.: '99-999')

def T(x): return ('PLOT', x)   # folha que só existe em DWG: plotar (plotar.py)
L = [
 ('ETIB-<ESCOLA>', 'IMP', 'AGF-001 Água fria', 'R02', rf'{EXE}\AGF\{CTR}-EXE-XXX-ETIB-IMP-PE-AGF-001-HIG-R02.pdf', 'R03'),
 ('ETIB-<ESCOLA>', 'IMP', 'ESG-001 Esgoto', 'R01', rf'{EXE}\ESG\{CTR}-EXE-XXX-ETIB-IMP-PE-ESG-001-HIG-R01.pdf', ''),
 ('ETIB-<ESCOLA>', 'IMP', 'ELE-001 Elétrica', 'R00', T(rf'{EXE}\ELE\{CTR}-EXE-XXX-ETIB-IMP-PE-ELE-001-ELG-R00.dwg'), ''),
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
