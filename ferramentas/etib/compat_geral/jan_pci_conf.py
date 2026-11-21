# -*- coding: utf-8 -*-
"""Conferência do relatório PCI R00 do Daniel: pares INC/SDAI × demais, agrupando as peças de caixa (1 caixa = 1 elemento)."""
import sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, jan_clash as JC, motor
sys.stdout.reconfigure(encoding='utf-8')


def pares_agrupados(P, discs=('INC', 'SDAI')):
    out = {}
    for A, B, g, pt in P:
        if B['disc'] in discs and A['disc'] not in discs: A, B = B, A
        if A['disc'] not in discs: continue
        k = (A['disc'], A['grupo'], B['disc'], B['grupo'])
        if k not in out or g < out[k][0]: out[k] = (g, pt, A, B)
    return out


if __name__ == '__main__':
    est = sys.argv[1] if len(sys.argv) > 1 else '0'
    SEG, MESH, P = JC.rodar(est)
    JD.agrupar_caixas(SEG, MESH)
    G = pares_agrupados(P)
    c = collections.Counter()
    for (da, ga, db, gb), (g, pt, A, B) in sorted(G.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[1][0])):
        sev = 'COL' if g < motor.TOL else 'FOLGA'
        if db != da: c[(da, db, sev)] += 1
        print(f'{da:4s} {ga:12s} × {db:4s} {gb[:34]:34s} {g*100:7.1f} cm  {sev:5s}  xy=({pt[0]:.1f};{pt[1]:.1f}) z={pt[2]:.2f}')
    print()
    tc = tf = 0
    for (da, db, sev), n in sorted(c.items()):
        print(da, db, sev, n)
        if db not in ('INC', 'SDAI'):
            if sev == 'COL': tc += n
            else: tf += n
    print('PCI × outras disciplinas: colisões', tc, '| folgas < 20 cm', tf)
