# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 2 da macrodrenagem (DRE-001-DRG-R02_GEO, já em UTM): galeria dupla Ø1200 mm
("REDE FUTURA SE NECESSÁRIO - NÃO EDIFICAR NESSA FAIXA"), GI das pontas e alas; drenagem existente da rua (TOP).
O DRE-002 é só a bacia de contribuição (39,30 ha) e curvas: não tem rede para modelar.
Uso: python -I -X utf8 dre_sat.py
"""
import sys, os, re, csv, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from rede_lib import unit


def main():
    E = sc.carrega('DRE1')
    tubos = [d['pts'][:, :2] for d in E if d['layer'] == 'DRE-TUBOS' and d['tipo'] in ('PL', 'LINE')]
    longos = [p for p in tubos if np.hypot(*np.diff(p, axis=0).T).sum() > 50]
    u = unit(longos[0][-1] - longos[0][0]); n = np.array([-u[1], u[0]])
    a0 = longos[0][0]
    off = sorted(((p[0] - a0) @ n, p) for p in longos)
    print('paredes (offset m):', [round(o, 3) for o, _ in off])
    # pares: (0, 1,20) e (1,69, 2,89) -> dois tubos Ø1200
    pares = [(off[0], off[1]), (off[2], off[3])]
    txt = [d for d in E if d['tipo'] == 'TEXT' and d['layer'] == 'DRE-TEXTOS']
    gis = [(d['pts'][0, :2], sc.num(d['texto'])) for d in txt if d['texto'].strip().upper().startswith('GI')]
    trechos = []
    for k, ((oa, pa), (ob_, pb)) in enumerate(pares):
        # eixo = média das paredes, estendido pelas cabeças (pedaços curtos colineares até as alas)
        P0 = (pa[0] + pb[0]) / 2; P1 = (pa[-1] + pb[-1]) / 2
        cab = [p for p in tubos if 2 < np.hypot(*np.diff(p, axis=0).T).sum() < 12 and abs(abs(unit(p[-1] - p[0]) @ u) - 1) < 0.01]
        ext = [P0, P1]
        for p in cab:
            for q in p:
                t = (q - P0) @ u; lat = abs((q - P0) @ n)
                if lat < 1.5: ext.append(P0 + u * t)
        ts = [(q - P0) @ u for q in ext]
        A, B = P0 + u * min(ts), P0 + u * max(ts)
        # GI: texto mais próximo de cada ponta
        gA = min(gis, key=lambda g: np.linalg.norm(g[0] - A)); gB = min(gis, key=lambda g: np.linalg.norm(g[0] - B))
        L = float(np.linalg.norm(B - A))
        if gA[1] < gB[1]: A, B, gA, gB = B, A, gB, gA     # sentido: do GI maior para o menor
        trechos.append({'trecho': f'DRE-G{k+1}', 'descricao': 'galeria Ø1200 mm (rede futura, se necessário)', 'DN_mm': 1200, 'L_m': round(L, 2),
                        'GI_montante': gA[1], 'GI_jusante': gB[1], 'i_pct': round((gA[1] - gB[1]) / L * 100, 2),
                        'E_ini': round(float(A[0]), 3), 'N_ini': round(float(A[1]), 3), 'E_fim': round(float(B[0]), 3), 'N_fim': round(float(B[1]), 3),
                        'obs': 'GI das pontas pelos textos da prancha; texto "REDE FUTURA SE NECESSÁRIO - NÃO EDIFICAR NESSA FAIXA"',
                        'pts': [A.tolist(), B.tolist()]})
    with open(os.path.join(sc.REL, 'SAT_fase2_DRE_galeria.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        cols = [c for c in trechos[0] if c != 'pts']
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows([{c: t[c] for c in cols} for t in trechos])
    json.dump({'trechos': trechos}, open(os.path.join(sc.WRK, 'dre_rede.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for t in trechos: print(t['trecho'], t['L_m'], 'GI', t['GI_montante'], '->', t['GI_jusante'], 'i', t['i_pct'], '%', (t['E_ini'], t['N_ini']), '->', (t['E_fim'], t['N_fim']))


if __name__ == '__main__':
    main()
