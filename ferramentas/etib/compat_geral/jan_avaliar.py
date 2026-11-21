# -*- coding: utf-8 -*-
"""Avalia uma solução (json) com as caixas de ELE/SDAI na profundidade que os eletrodutos exigem (jan_caixas_prof).
Uso: jan_avaliar.py <solucao.json> [geo] [saida.csv] -> imprime o quadro e as colisões que sobram nas redes móveis."""
import sys, os, json, collections, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, jan_resumo as JR, jan_caixas_prof as CP, motor as mt
sys.stdout.reconfigure(encoding='utf-8')


def avaliar(mods, g=None, ajusta=True, ignorar_ids=()):
    SEG, MESH = JD.carregar(g=g, est='daniel')
    if mods:
        for s in SEG:
            m = mods['seg'].get(s['id'])
            if m and s['id'] not in ignorar_ids: off = np.array([*m['dxy'], -m['dz']]); s['a'] = s['a0'] + off; s['b'] = s['b0'] + off
        for M in MESH:
            m = mods['mesh'].get(M['id'])
            if m and M['id'] not in ignorar_ids: off = np.array([*m.get('dxy', [0, 0]), -m.get('dz', 0)]); M['tri'] = M['tri'] + off; M['lo'] = M['lo'] + off; M['hi'] = M['hi'] + off
    JD.agrupar_caixas(SEG, MESH)
    n = CP.ajustar(SEG, MESH) if ajusta else 0
    IDX = mt.Indice(SEG, MESH); P = {}
    def add(A, B, gg, pt):
        k = tuple(sorted((A['id'], B['id'])))
        if k not in P or gg < P[k][2]: P[k] = (A, B, gg, pt)
    for i, A in enumerate(SEG):
        for t, j, gg, pt in mt.avaliar_seg(i, IDX): add(A, SEG[j] if t == 'S' else MESH[j], gg, pt)
    for j, M in enumerate(MESH):
        if M['disc'] == 'EST': continue
        for t, k, gg, pt in mt.avaliar_mesh(j, IDX):
            if t == 'M': add(M, MESH[k], gg, pt)
    return n, JR.agrupar(list(P.values())), SEG, MESH


if __name__ == '__main__':
    mods = json.load(open(sys.argv[1], encoding='utf-8'))
    g = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '-' else None
    n, L, S, M = avaliar(mods, g)
    col = [r for r in L if r['sev'] == 'CRITICA']; mov = [r for r in col if not r['fixo']]
    print(f'caixas ajustadas {n} | colisões {len(col)} (a definir {len(col)-len(mov)}; redes móveis {len(mov)}) | atenção {sum(1 for r in L if r["sev"]=="ATENCAO")}')
    for r in sorted(mov, key=lambda r: r['par']): print(f"   {r['par']:9s} {r['ga']} × {r['gb']} {r['g']*100:.0f} cm ({r['pt'][0]:.1f};{r['pt'][1]:.1f}) z={r['pt'][2]:.2f}")
    if len(sys.argv) > 3: JR.gravar(L, sys.argv[3])
