# -*- coding: utf-8 -*-
"""ICP rígido de uma região da base da disciplina (_GEO, em UTM) sobre a referência.
Uso: python -I icp_regiao.py <disc_GEO.dxf> <prefixo> <ref.dxf> <cx> <cy> <rmin> <rmax>
Usa só os pontos da base da disciplina a uma distância entre rmin e rmax de (cx,cy)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
a = sys.argv
disc, pref, ref = a[1], a[2], a[3]
cx, cy, rmin, rmax = map(float, a[4:8])
ign = ('CARIMBO', 'carimbo', 'FORMATO', 'Q-TABELA', 'TEXTO', 'TXT', 'COTA', 'DI-')
A = casar.cache_load(disc); B = casar.cache_load(ref)
pa = casar.amostrar(A, lambda s: s['path'].startswith(pref) and not any(k in s['lay'] for k in ign), passo=0.25)
r = np.hypot(pa[:, 0] - cx, pa[:, 1] - cy)
pa = pa[(r >= rmin) & (r <= rmax)]
if len(pa) > 30000:
    pa = pa[np.random.default_rng(2).choice(len(pa), 30000, replace=False)]
# coordenadas relativas ao centro para a rotação ficar bem condicionada
c0 = np.array([cx, cy])
S = casar.segmentos(B, lambda s: not any(k in s['lay'] for k in ign))
G = casar.GradeSeg(S - np.array([cx, cy, cx, cy]))
P = pa - c0
ad0, _ = casar.aderencia_seg(P, G, (0.0, 0.0, 0.0))
T, n = casar.icp_seg(P, G, (0.0, 0.0, 0.0), raios=(2.0, 1.0, 0.5, 0.25, 0.10, 0.05, 0.02))
ad1, _ = casar.aderencia_seg(P, G, T)
print('pontos %d (anel %.0f–%.0f m em torno de %.1f, %.1f)' % (len(P), rmin, rmax, cx, cy))
print('aderência antes : ' + '  '.join('%4.0f mm %4.0f%%' % (k*1000, v*100) for k, v in ad0.items()))
print('aderência depois: ' + '  '.join('%4.0f mm %4.0f%%' % (k*1000, v*100) for k, v in ad1.items()) + '  (pares %d)' % n)
print('correção sobre a transformação atual: rot %.6f° em torno do centro, t=(%.1f, %.1f) mm' % (math.degrees(T[0]), T[1]*1000, T[2]*1000))
