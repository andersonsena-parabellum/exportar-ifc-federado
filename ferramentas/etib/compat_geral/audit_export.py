# -*- coding: utf-8 -*-
"""Auditoria da exportação geral (R02): contagem e comprimento por disciplina/sistema, sólidos por categoria."""
import sys, collections, glob, os
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo" + "\\"
for fn in sorted(glob.glob(G + '*_segs.tsv')):
    c = collections.defaultdict(lambda: [0, 0.0, 9e9, -9e9, set()])
    for l in open(fn, encoding='utf-8'):
        r = l.rstrip('\n').split('\t')
        if len(r) < 13: continue
        a = np.array(list(map(float, r[7:10]))); b = np.array(list(map(float, r[10:13])))
        import re as _re; k = (r[2], _re.sub(r'\s*\d+$', '', r[4]) or r[3]); v = c[k]
        v[0] += 1; v[1] += float(np.linalg.norm(b - a)); v[2] = min(v[2], a[2], b[2]); v[3] = max(v[3], a[2], b[2]); v[4].add(r[6])
    print('==', os.path.basename(fn))
    for k, v in sorted(c.items()): print(f'   {k[0]:12s} {k[1][:45]:45s} n={v[0]:4d}  L={v[1]:8.1f} m  z {v[2]:.2f}..{v[3]:.2f}  DE {sorted(v[4], key=float)[:8]}')
for fn in sorted(glob.glob(G + '*_mesh.tsv')):
    c = collections.Counter(); t = 0
    for l in open(fn, encoding='utf-8'):
        r = l.split('\t', 7)
        if len(r) < 7: continue
        c[r[2]] += 1; t += int(r[6])
    print('==', os.path.basename(fn), dict(c), 'triângulos', t)
