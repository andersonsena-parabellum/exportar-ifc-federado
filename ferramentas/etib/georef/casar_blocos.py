# -*- coding: utf-8 -*-
"""Casa blocos de mesmo nome entre um DWG (DXF) de disciplina e a base, e estima a transformação rígida 2D.

Para cada nome de bloco que aparece UMA vez em cada desenho (em qualquer profundidade, mesma escala, sem espelho),
a matriz da inserção nos dois dá uma transformação candidata  T = M_base · M_disc⁻¹.  Os candidatos se agrupam
(rotação ± 0,01°, translação ± 5 cm); o grupo maior é a transformação. Blocos redefinidos entre os desenhos caem
em grupos isolados e são listados para conferência.

Uso: python -I casar_blocos.py <disc.dxf> <base.dxf>
"""
import sys, math, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler


def poses(prims):
    d = collections.defaultdict(list)
    for p in prims:
        if p['tipo'] == 'INSERT' and not p['nome'].startswith('*'):
            d[p['nome']].append(p)
    return d


def candidatos(A, B):
    out = []
    for nome in set(A) & set(B):
        if len(A[nome]) != 1 or len(B[nome]) != 1:
            continue
        a, b = A[nome][0], B[nome][0]
        if a['espelho'] != b['espelho'] or abs(a['s'] - b['s']) > 1e-4 * max(1, a['s']) or a['s'] < 1e-6:
            continue
        T = b['M'] @ np.linalg.inv(a['M'])
        R = T[:2, :2]
        if abs(np.linalg.det(R) - 1) > 1e-4:
            continue
        out.append({'nome': nome, 'rot': math.degrees(math.atan2(R[1, 0], R[0, 0])), 'tx': T[0, 3], 'ty': T[1, 3],
                    'tz': T[2, 3], 'a': a, 'b': b, 'T': T})
    return out


def agrupar(cands, tol_ang=0.01, tol_t=0.05):
    grupos = []
    for c in sorted(cands, key=lambda c: c['nome']):
        for g in grupos:
            r = g[0]
            if abs((c['rot'] - r['rot'] + 180) % 360 - 180) < tol_ang and math.hypot(c['tx'] - r['tx'], c['ty'] - r['ty']) < tol_t:
                g.append(c)
                break
        else:
            grupos.append([c])
    return sorted(grupos, key=len, reverse=True)


def resumo(g):
    rot = float(np.mean([c['rot'] for c in g]))
    tx = float(np.mean([c['tx'] for c in g])); ty = float(np.mean([c['ty'] for c in g]))
    disp = max(math.hypot(c['tx'] - tx, c['ty'] - ty) for c in g)
    return rot, tx, ty, disp


def casar(fa, fb, imprime=True):
    A, B = poses(ler(fa)), poses(ler(fb))
    grupos = agrupar(candidatos(A, B))
    if imprime:
        print(f'{fa.split(chr(92))[-1]}  ×  {fb.split(chr(92))[-1]}: {sum(map(len, grupos))} blocos em comum (únicos nos dois)')
        for g in grupos[:8]:
            rot, tx, ty, disp = resumo(g)
            print(f'  grupo n={len(g):3d}  rot={rot:+.8f}°  t=({tx:.4f}, {ty:.4f})  dispersão {disp*1000:.2f} mm  ex.: ' +
                  ', '.join(c['nome'][:28] for c in g[:5]))
    return grupos


if __name__ == '__main__':
    casar(sys.argv[1], sys.argv[2])
