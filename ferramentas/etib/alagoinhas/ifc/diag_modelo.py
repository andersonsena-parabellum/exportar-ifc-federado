# -*- coding: utf-8 -*-
import sys, collections, numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
import alh_modelo as AM
E, C, T = AM.montar(log=lambda *a: None)
for e in E:
    if not np.isfinite(e['pts']).all():
        z = T.z(e['pts'][:, :2]); print('NaN', e['id'], e['disc'], len(e['pts']), 'sem terreno', int((~np.isfinite(z)).sum()), e['pts'][0, :2] - AM.O[:2])
cnt = collections.Counter(c['id'] for c in C)
for k, n in cnt.items():
    if n > 1: print('repetido', k, n, [(round(c['E'] - AM.O[0], 2), round(c['N'] - AM.O[1], 2), c['info'].get('tipo')) for c in C if c['id'] == k])
