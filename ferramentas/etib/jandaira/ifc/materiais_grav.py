# -*- coding: utf-8 -*-
"""Material dos trechos de drenagem e esgoto para o IFC (20/10/2026, Anderson: "um dos princípios do BIM é a informação").
Fonte: a etiqueta de material do próprio trecho na prancha (PVCR, PVC, PVC-V, PVC-DR) mais perto do trecho, a menos de 3 m; sem
etiqueta, a nota de especificação da prancha pelo diâmetro (DRE-001: até 150 mm PVC Série Reforçada, 200 mm Série Normal, 250 mm
ou mais Vinilfort; drenos do campo PVC-DR corrugado perfurado; ESG-001: PVC Série Normal). Grava o resultado em cache
(IFC_R03/JAN_materiais_gravidade.json) para não reler os DWG a cada rodada."""
import os, sys, re, json, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import asbuilt as ab

REL = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS'
CACHE = os.path.join(REL, 'IFC_R03', 'JAN_materiais_gravidade.json')
COP = os.path.join(REL, 'EXECUTIVO_R03_IFC', '_copias')
PRANCHAS = {'DRE-001': os.path.join(COP, '24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R00.dxf'),
            'CPS-DRE-001': os.path.join(COP, '24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R02_ler.dxf'),
            'ESG-001': os.path.join(COP, '24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R01.dxf')}
NOME = {'PVCR': 'PVC rígido Série Reforçada (PVCR)', 'PVC-V': 'PVC Vinilfort (PVC-V)',
        'PVC-DR': 'PVC corrugado perfurado (PVC-DR), envelopado em geotêxtil e brita'}


def _etiquetas(chave, transf):
    rot, t = transf; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    out = []
    for e in ab.entidades(PRANCHAS[chave]):
        if e['typ'] not in ('TEXT', 'MTEXT'): continue
        s = ab._limpo(e['txt']).strip().upper()
        m = re.match(r'^(PVC-DR|PVC-V|PVCR|PVC)\b', s)
        if m: out.append((m.group(1), R @ e['p'] + np.array(t)))
    return out


def _por_dn(disc, trecho, dn):
    if disc == 'ESG': return 'PVC esgoto Série Normal'
    if trecho.startswith('DRE-CPS-D'): return NOME['PVC-DR']
    if dn <= 160: return NOME['PVCR']
    if dn <= 230: return 'PVC Série Normal'
    return NOME['PVC-V']


def materiais(E, transf):
    """{id: (material, fonte)} dos trechos de DRE/ESG; transf = {'DRE-001': (rot, t), ...} (S.TRANSF_DWG pelos caminhos)."""
    if os.path.exists(CACHE):
        C = json.load(open(CACHE, encoding='utf-8'))
        if all(e['id'] in C for e in E if e['disc'] in ('DRE', 'ESG')): return C
    et = {k: _etiquetas(k, transf[k]) for k in PRANCHAS}
    C = {}
    for e in E:
        if e['disc'] not in ('DRE', 'ESG'): continue
        P = np.asarray(e['pts'])[:, :2]; dn = float(e['info'].get('DN_mm') or e['de'] * 1000)
        folha = 'ESG-001' if e['disc'] == 'ESG' else ('CPS-DRE-001' if e['trecho'].startswith('DRE-CPS') else 'DRE-001')
        cand = [(ab.projetar(P, q)[1], k) for k, q in et[folha]]
        cand = [c for c in cand if c[0] < 3.0]
        if cand:
            k = min(cand)[1]
            mat = NOME.get(k) or ('PVC esgoto Série Normal' if e['disc'] == 'ESG' else 'PVC Série Normal')
            C[e['id']] = (mat, f'etiqueta "{k}" do trecho na {folha}')
        else:
            C[e['id']] = (_por_dn(e['disc'], e['trecho'], dn), f'nota de especificação da {folha} pelo diâmetro')
    json.dump(C, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return C
