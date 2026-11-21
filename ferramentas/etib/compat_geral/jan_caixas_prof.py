# -*- coding: utf-8 -*-
"""Ajusta a PROFUNDIDADE das caixas de ELE e SDAI (sem mudar a posição) ao eletroduto mais fundo que chega nelas:
fundo = (fundo do eletroduto mais fundo) − 0,10 m; o topo fica no terreno. Uso: avaliar um cenário "só profundidade"."""
import numpy as np


def ajustar(SEG, MESH, discs=('ELE', 'SDAI'), folga=0.10, margem=0.15):
    n = 0
    grupos = {}
    for M in MESH:
        if M['disc'] in discs and 'glo' in M and M['cat'].startswith('Equip'): grupos.setdefault((M['fonte'], M['grupo']), []).append(M)
    for (f, g), L in grupos.items():
        lo = np.min([M['lo'] for M in L], 0); hi = np.max([M['hi'] for M in L], 0)
        fundos = []
        for s in SEG:
            if s['disc'] != L[0]['disc'] or s['fonte'] != f: continue
            for p in (s['a'], s['b']):
                if lo[0] - margem <= p[0] <= hi[0] + margem and lo[1] - margem <= p[1] <= hi[1] + margem: fundos.append(p[2] - s['de'] / 2)
        if not fundos: continue
        novo = min(fundos) - folga; top = hi[2]; velho = lo[2]
        if abs(novo - velho) < 0.01 or top - novo < 0.2: continue
        k = (top - novo) / (top - velho)
        for M in L:
            T = M['tri'].copy(); T[..., 2] = top - (top - T[..., 2]) * k
            M['tri'] = T; M['lo'] = T.reshape(-1, 3).min(0); M['hi'] = T.reshape(-1, 3).max(0); M.pop('samp', None)
        n += 1
    return n
