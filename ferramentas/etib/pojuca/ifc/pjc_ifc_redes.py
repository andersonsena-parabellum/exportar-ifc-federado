# -*- coding: utf-8 -*-
"""Pojuca — o que o IFC as built da implantação (24-049-PJC-CTO-ETIB-IMP-PE-001-MOD-R00.ifc, 592 MB, Drive da construtora, 12/05)
traz de tubulação: lê só os IfcFlowSegment/IfcFlowFitting/IfcFlowTerminal/IfcFlowController/IfcDistributionFlowElement (sem carregar o
arquivo inteiro, que não cabe na RAM livre), resolve o posicionamento e a geometria (pontos) de cada um em coordenadas do arquivo,
leva ao UTM pelo IfcMapConversion/ponto de levantamento (ou pelo ProjectPosition do IMP) e grava um CSV: tipo, nome, sistema,
eixo (pontos extremos pela direção principal), diâmetro aparente, cota e se fica dentro de prédio.
Uso: .venv/Scripts/python.exe -X utf8 pojuca/ifc/pjc_ifc_redes.py"""
import os, re, csv, sys, math
import numpy as np

IFC = r'D:\Projeto Modelagem\ETIB-POJUCA\REFERENCIAS_RVT\IFC\24-049-PJC-CTO-ETIB-IMP-PE-001-MOD-R00.ifc'
OUT = r'D:\Projeto Modelagem\FERRAMENTAS\pojuca\ifc\PJC_ifc_asbuilt_redes.csv'
TIPOS = ('IFCFLOWSEGMENT', 'IFCFLOWFITTING', 'IFCFLOWTERMINAL', 'IFCFLOWCONTROLLER', 'IFCDISTRIBUTIONFLOWELEMENT')
RX = re.compile(r'^#(\d+)=([A-Z0-9]+)\((.*)\);\s*$')
REF = re.compile(r'#(\d+)')
NAO_SEGUIR = {'IFCOWNERHISTORY', 'IFCPRESENTATIONLAYERASSIGNMENT', 'IFCSTYLEDITEM', 'IFCGEOMETRICREPRESENTATIONSUBCONTEXT',
              'IFCGEOMETRICREPRESENTATIONCONTEXT', 'IFCSURFACESTYLE'}


def _scan(ids):
    """lê as linhas com estes ids."""
    out = {}
    with open(IFC, 'r', encoding='latin-1', errors='replace') as f:
        for ln in f:
            if not ln.startswith('#'): continue
            k = ln.find('=')
            try: i = int(ln[1:k])
            except ValueError: continue
            if i in ids:
                m = RX.match(ln.strip())
                if m: out[i] = (m.group(2), m.group(3))
    return out


def main():
    L = {}; sementes = []; rels = []
    with open(IFC, 'r', encoding='latin-1', errors='replace') as f:
        for ln in f:
            if not ln.startswith('#'): continue
            m = RX.match(ln.strip())
            if not m: continue
            t = m.group(2)
            if t in TIPOS:
                i = int(m.group(1)); L[i] = (t, m.group(3)); sementes.append(i)
            elif t in ('IFCRELASSIGNSTOGROUP', 'IFCSITE', 'IFCMAPCONVERSION', 'IFCPROJECTEDCRS', 'IFCBUILDING'):
                L[int(m.group(1))] = (t, m.group(3))
                if t == 'IFCRELASSIGNSTOGROUP': rels.append(int(m.group(1)))
    print(len(sementes), 'elementos de tubulação')
    falta = set()
    for i in sementes:
        a = L[i][1]; refs = [int(x) for x in REF.findall(a)]
        falta |= set(refs[1:])                         # tira o owner history (primeiro)
    for i in [k for k, v in L.items() if v[0] in ('IFCSITE', 'IFCBUILDING')]:
        falta |= set(int(x) for x in REF.findall(L[i][1])[1:])
    rodada = 0
    while falta:
        rodada += 1
        novo = _scan(falta - set(L)); L.update(novo); prox = set()
        for i, (t, a) in novo.items():
            if t in NAO_SEGUIR: continue
            prox |= set(int(x) for x in REF.findall(a))
        falta = prox - set(L)
        print(f'  passada {rodada}: +{len(novo)} linhas, faltam {len(falta)}')
    import json
    json.dump({str(k): v for k, v in L.items()}, open(OUT.replace('.csv', '_linhas.json'), 'w'), ensure_ascii=False)
    print('linhas guardadas', len(L))


if __name__ == '__main__':
    main()
