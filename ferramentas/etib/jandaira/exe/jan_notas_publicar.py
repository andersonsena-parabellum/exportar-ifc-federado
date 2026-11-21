# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026): depois do jan_notas_r03.py, troca as pranchas corrigidas (mesmo nome e revisão) na pasta de envio do
Drive e no CDE (PRANCHAS/ETIB-JANDAIRA e ETIB_PRANCHAS_CDE no Drive), sobrescrevendo no lugar (o Drive mantém o mesmo ID).
A versão anterior de cada uma já está em EXECUTIVO_R03_IFC/_copias/entregue_notas-repetidas/.
Uso: python -X utf8 jan_notas_publicar.py [AF-001 EL-001 ...]"""
import os, sys, shutil, hashlib
sys.stdout.reconfigure(encoding='utf-8')
R3 = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'
ENV = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-JANDAIRA_2026-10-20'
CDE = [r'D:\Projeto Modelagem\PRANCHAS\ETIB-JANDAIRA', r'G:\Meu Drive\ETIB_PRANCHAS_CDE\ETIB-JANDAIRA']
FINAL = {'AF-001': '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03', 'EL-001': '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R03',
         'EL-002': '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R03', 'IN-001': '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R05',
         'CPS-EL-001': '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R03'}
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
for k in [x for x in sys.argv[1:]] or ['AF-001', 'EL-001', 'EL-002', 'IN-001']:
    n = FINAL[k]; pdf = os.path.join(R3, 'PDF_QG', n + '.pdf'); dwg = os.path.join(R3, n + '.dwg')
    pares = [(pdf, os.path.join(ENV, '01_PRANCHAS_PDF', n + '.pdf')), (dwg, os.path.join(ENV, '02_PRANCHAS_DWG', n + '.dwg'))] + \
            [(pdf, os.path.join(d, n + '.pdf')) for d in CDE]
    for a, b in pares:
        if not os.path.exists(b): print('  (destino não existia)', b)
        shutil.copyfile(a, b)
        print(k, '->', b, 'OK' if md5(a) == md5(b) else 'DIFERENTE')
