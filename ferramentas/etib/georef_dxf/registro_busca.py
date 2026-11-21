# -*- coding: utf-8 -*-
"""Registro de um desenho local sem blocos em comum: busca de rotação (passo fixo) + ICP ponto-segmento.
Uso: python -I registro_busca.py <disc.dxf> <regex_base_disc> <ref_GEO.dxf> <cx> <cy> <raio_ref> [--passo 2]
  regex_base_disc: casa layer ou caminho dos elementos de base (arquitetura) do desenho local
  (cx,cy): ponto aproximado do centro da mesma área no UTM; raio_ref: recorte da referência."""
import sys, os, math, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
a = sys.argv
disc, rx, ref = a[1], re.compile(a[2]), a[3]
cx, cy, rr = float(a[4]), float(a[5]), float(a[6])
passo = float(a[a.index('--passo') + 1]) if '--passo' in a else 2.0
faixa = [float(v) for v in a[a.index('--faixa') + 1].split(',')] if '--faixa' in a else [0, 360]
ign_ref = re.compile(a[a.index('--ign_ref') + 1]) if '--ign_ref' in a else None
A = casar.cache_load(disc); B = casar.cache_load(ref)
pa = casar.amostrar(A, lambda s: bool(rx.search(s['lay']) or rx.search(s['path'])), passo=0.25)
if len(pa) > 8000:
    pa = pa[np.random.default_rng(3).choice(len(pa), 8000, replace=False)]
ign = ('CARIMBO', 'carimbo', 'FORMATO', 'Q-TABELA', 'TEXTO', 'TXT', 'COTA')
S = casar.segmentos(B, lambda s: not any(k in s['lay'] for k in ign) and not (ign_ref and ign_ref.search(s['lay'])))
mid = (S[:, :2] + S[:, 2:]) / 2
S = S[np.hypot(mid[:, 0] - cx, mid[:, 1] - cy) < rr] - np.array([cx, cy, cx, cy])
G = casar.GradeSeg(S)
c_src = pa.mean(0)
P = pa - c_src
res = []
for th in np.arange(faixa[0], faixa[1], passo):
    T0 = (math.radians(th), 0.0, 0.0)
    T, n = casar.icp_seg(P, G, T0, raios=(4.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02), it_por_raio=3)
    ad, _ = casar.aderencia_seg(P, G, T, tols=(0.01, 0.05, 0.2))
    res.append((ad[0.05], ad[0.01], th, T))
res.sort(key=lambda r: -r[0])
print('pontos %d, segmentos ref %d' % (len(P), len(S)))
for a5, a1, th0, T in res[:8]:
    # transformação final local -> UTM: p_utm = R (p - c_src) + t + (cx,cy)
    R = np.array([[math.cos(T[0]), -math.sin(T[0])], [math.sin(T[0]), math.cos(T[0])]])
    t = np.array([T[1], T[2]]) - R @ c_src + np.array([cx, cy])
    print('início %5.1f° -> rot %.8f°  t=(%.6f, %.6f)  ader 5 cm %4.1f%%  1 cm %4.1f%%' % (th0, math.degrees(T[0]) % 360, t[0], t[1], a5*100, a1*100))
