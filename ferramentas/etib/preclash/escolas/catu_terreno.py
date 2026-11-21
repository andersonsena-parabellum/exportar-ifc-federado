# -*- coding: utf-8 -*-
"""ETIB Catu — congela o TERRENO PROVISÓRIO da pré-compatibilização em escolas/dados/catu_terreno.npz.
Pontos (E, N, z), em UTM do levantamento:
  1. projeto: CT das caixas do ESG e da DRE (fase 3), níveis escritos na SIT R02 (+78,25 a +84,50) e as linhas 3D do platô do
     restaurante na terraplanagem TER-IMP R00, trazidas 1,9157 m para oeste (a arquitetura do TER está deslocada do SIT);
  2. existente: pontos cotados e curvas do TOP-001, fora de 3 m de qualquer ponto de projeto.
A parte sul (campo/quadra) fica fora do levantamento: ali o terreno vem só das CT das caixas e dos níveis da SIT.
Provisório até o terreno do IMP as built. Linhas da arquitetura (SIT, blocos) vão em 'arq' para o passo de desvio.
Só LÊ os dados da thread da escola (FERRAMENTAS/georef: DXF dos _GEO/_REF e os CSV da fase 3).
Uso: .venv/Scripts/python.exe -X utf8 preclash/escolas/catu_terreno.py
"""
import os, sys, re, csv
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from catu_comum import carrega, num      # noqa: E402

F3 = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\FASE3_COTAS_2026-10-18'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'catu_terreno.npz')
DX_TER = -1.9157                       # TER R00 -> posição do SIT R02 / disciplinas
CAIXA = (567600.0, 8634530.0, 567820.0, 8634730.0)


def dentro(P): return (P[:, 0] > CAIXA[0]) & (P[:, 0] < CAIXA[2]) & (P[:, 1] > CAIXA[1]) & (P[:, 1] < CAIXA[3])


def main():
    proj = []
    for disc in ('DRE', 'ESG'):
        with open(os.path.join(F3, f'CAT_fase3_{disc}_caixas.csv'), encoding='utf-8-sig') as f:
            for r in csv.DictReader(f, delimiter=';'):
                if r['CT'] not in ('', None): proj.append((float(r['E']), float(r['N']), float(r['CT'])))
    n_cx = len(proj)
    S = carrega('SIT')
    for d in S:
        if d['tipo'] == 'TEXT':
            m = re.fullmatch(r'\+\s*(\d{2}[.,]\d{2})', d['texto'].strip())
            if m: proj.append((d['pts'][0, 0], d['pts'][0, 1], float(m.group(1).replace(',', '.'))))
    n_sit = len(proj) - n_cx
    R = carrega('TER')
    for d in R:
        if d['layer'] == 'Q-PLATO' and d['tipo'] in ('LINE', 'PL'):
            for p in d['pts']:
                if p[2] > 50: proj.append((p[0] + DX_TER, p[1], p[2]))
    n_ter = len(proj) - n_cx - n_sit
    proj = np.array(proj)
    T = carrega('TOP')
    ex = []
    for d in T:
        if d['tipo'] == 'POINT' and d['layer'] == 'TOP-COTAS': ex.append(d['pts'][0])
        if d['tipo'] == 'PL' and d['layer'] == 'CurvasTG': ex.extend(d['pts'][::2])
    ex = np.array(ex); ex = ex[dentro(ex) & (ex[:, 2] > 50)]
    # existente perto (< 3 m) de ponto de projeto sai: o projeto manda
    keep = np.array([np.min(np.hypot(*(proj[:, :2] - p[:2]).T)) > 3.0 for p in ex])
    Y = np.vstack([proj, ex[keep]])
    Y = Y[np.unique(np.round(Y[:, :2], 2), axis=0, return_index=True)[1]]
    # arquitetura dos blocos (SIT R02 _GEO) para o desvio em planta
    arq = []
    for d in S:
        if d['tipo'] in ('LINE', 'PL') and d['path'].startswith('BLOCO') and 'PAGINA' not in d['path']:
            p = d['pts'][:, :2]
            for a, b in zip(p[:-1], p[1:]):
                if np.linalg.norm(b - a) > 0.3 and dentro(np.vstack([a, b])).all(): arq.append((a, b))
    arq = np.array(arq, float)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, pts=Y, arq=arq,
                        fonte=np.array('provisório: CT das caixas ESG/DRE + níveis da SIT R02 + platô do TER-IMP R00 (−1,92 m em E) + TOP-001 fora de 3 m; até o IMP as built'))
    print('gravado', OUT, f'| pontos {len(Y)} (CT de caixas {n_cx}, níveis SIT {n_sit}, TER {n_ter}, existentes {int(keep.sum())}) | linhas SIT {len(arq)}')
    print('  z', round(float(Y[:, 2].min()), 2), '..', round(float(Y[:, 2].max()), 2))


if __name__ == '__main__':
    main()
