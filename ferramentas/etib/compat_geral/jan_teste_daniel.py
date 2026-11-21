# -*- coding: utf-8 -*-
"""Testa as soluções do relatório PCI R00 do Daniel numa cópia da geometria (nada muda nos RVTs).
INC: eixo a 1,30 m (AH-01..04), 1,20 m (AH-05/06/07/09), 1,10 m (AH-08), medidos como ele mede (cota 147,00 − z).
SDAI: variante A = só aprofundar? não; variante do relatório = deslocar a espinha 1,4 m e subir para 0,65 m (aproximação)."""
import sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, jan_clash as JC, jan_pci_conf as PC, motor
sys.stdout.reconfigure(encoding='utf-8')
PROF = {'PCI-AH-01': 1.30, 'PCI-AH-02': 1.30, 'PCI-AH-03': 1.30, 'PCI-AH-04': 1.30, 'PCI-AH-05': 1.20, 'PCI-AH-06': 1.20,
        'PCI-AH-07': 1.20, 'PCI-AH-08': 1.10, 'PCI-AH-09': 1.20}


def mods_inc(SEG, MESH):
    m = {'seg': {}, 'mesh': {}}
    for s in SEG:
        if s['trecho'] in PROF: m['seg'][s['id']] = {'dz': PROF[s['trecho']] - 0.85}
    # conexões de aço/tês enterrados no nível −0,85 acompanham o trecho mais próximo
    hs = [s for s in SEG if s['trecho'] in PROF]
    for M in MESH:
        if M['fonte'] == 'PCI' and M['cat'].startswith('Conex') and M['hi'][2] < -0.5:
            c = (M['lo'] + M['hi']) / 2
            d, t = min((float(np.linalg.norm(c - (s['a0'] + (s['b0'] - s['a0']) * np.clip((c - s['a0']) @ (s['b0'] - s['a0']) / max((s['b0'] - s['a0']) @ (s['b0'] - s['a0']), 1e-12), 0, 1)))), s['trecho']) for s in hs)
            if d < 0.5: m['mesh'][M['id']] = {'dz': PROF[t] - 0.85}
    return m


if __name__ == '__main__':
    SEG, MESH = JD.carregar(est=None)
    m = mods_inc(SEG, MESH)
    variantes = {'hoje': None, 'INC descida (Daniel)': m}
    for nome, mods in variantes.items():
        S, Mh, P = JC.rodar('0', mods)
        JD.agrupar_caixas(S, Mh)
        G = PC.pares_agrupados(P)
        c = collections.Counter()
        for (da, ga, db, gb), (g, pt, A, B) in G.items():
            if db in ('INC', 'SDAI'): continue
            c[(da, db, 'COL' if g < motor.TOL else 'FOLGA')] += 1
        print('==', nome, dict(sorted(c.items())))
        if mods:
            for (da, ga, db, gb), (g, pt, A, B) in sorted(G.items(), key=lambda kv: kv[1][0]):
                if da == 'INC' and db not in ('SDAI',): print(f'   {ga:12s} × {db:4s} {gb[:30]:30s} {g*100:6.1f} cm z={pt[2]:.2f}')
