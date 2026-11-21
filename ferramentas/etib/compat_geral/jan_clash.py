# -*- coding: utf-8 -*-
"""Clash da Jandaíra (todas × todas) com o motor.py, sobre a geometria de jan_dados.py.
Uso: jan_clash.py [saida.csv] [est=daniel|compart|0] [mods.json opcional: {"seg": {id: {"dz": m, "dxy": [dx,dy]}}, "mesh": {...}}]
Folga = menor valor por PAR DE ELEMENTOS. Colisão: folga < −2 mm; folga curta: < 0,20 m."""
import sys, os, json, csv, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor, jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')


def rodar(est='daniel', mods=None, folga=0.20, discs=JD.DISCS, filtro=None):
    SEG, MESH = JD.carregar(est=None if est in ('0', '', None) else est, discs=discs)
    if mods:
        for i, s in enumerate(SEG):
            m = mods.get('seg', {}).get(s['id'])
            if m: s['a'] = s['a0'] + np.array([*m.get('dxy', [0, 0]), -m.get('dz', 0.0)]); s['b'] = s['b0'] + np.array([*m.get('dxy', [0, 0]), -m.get('dz', 0.0)])
        for M in MESH:
            m = mods.get('mesh', {}).get(M['id'])
            if m:
                off = np.array([*m.get('dxy', [0, 0]), -m.get('dz', 0.0)]); M['tri'] = M['tri'] + off; M['lo'] = M['lo'] + off; M['hi'] = M['hi'] + off
    IDX = motor.Indice(SEG, MESH)
    pares = {}
    def add(A, B, g, pt):
        k = tuple(sorted((A['id'], B['id'])))
        if k not in pares or g < pares[k][2]: pares[k] = (A, B, g, pt)
    for i, A in enumerate(SEG):
        if filtro and not filtro(A): continue
        for t, j, g, pt in motor.avaliar_seg(i, IDX, folga):
            add(A, SEG[j] if t == 'S' else MESH[j], g, pt)
    for j, M in enumerate(MESH):
        if M['disc'] == 'EST': continue
        if filtro and not filtro(M): continue
        for t, k, g, pt in motor.avaliar_mesh(j, IDX, folga):
            if t == 'M': add(M, MESH[k], g, pt)
    return SEG, MESH, list(pares.values())


def nome(E):
    if E['k'] == 'S': return '%s %s Ø%s' % (E['tipo'][:30], E['trecho'], E['dn'])
    return '%s %s' % (E['trecho'][:30], E['nome'].split(' : ')[0][:40])


def gravar(pares, saida):
    with open(saida, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['disc_a', 'id_a', 'elem_a', 'disc_b', 'id_b', 'elem_b', 'folga_m', 'gravidade', 'x', 'y', 'z', 'E', 'N', 'cota'])
        for A, B, g, pt in sorted(pares, key=lambda p: (p[0]['disc'], p[1]['disc'], p[2])):
            if A['disc'] > B['disc']: A, B = B, A
            sev = 'CRITICA' if g < motor.TOL else 'ATENCAO'
            e = JD.para_compart(np.array([pt]))[0]
            w.writerow([A['disc'], A['id'], nome(A), B['disc'], B['id'], nome(B), '%.3f' % g, sev, '%.2f' % pt[0], '%.2f' % pt[1], '%.3f' % pt[2], '%.2f' % e[0], '%.2f' % e[1], '%.3f' % e[2]])


if __name__ == '__main__':
    t0 = time.time()
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(JD.G), 'pontos_clash_hoje.csv')
    est = sys.argv[2] if len(sys.argv) > 2 else 'daniel'
    mods = json.load(open(sys.argv[3], encoding='utf-8')) if len(sys.argv) > 3 else None
    SEG, MESH, P = rodar(est, mods)
    gravar(P, saida)
    import collections
    c = collections.Counter()
    for A, B, g, pt in P:
        k = '×'.join(sorted((A['disc'], B['disc']))); c[(k, 'col' if g < motor.TOL else 'folga')] += 1
    print(f'segmentos {len(SEG)} | sólidos {len(MESH)} | pares {len(P)} | {time.time()-t0:.0f}s')
    for k in sorted({k for k, _ in c}): print(f'  {k:12s} colisões {c[(k, "col")]:4d}  folgas<20cm {c[(k, "folga")]:4d}')
