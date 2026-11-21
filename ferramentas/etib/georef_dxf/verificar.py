# -*- coding: utf-8 -*-
"""Verifica (e refina por ICP) a transformação disciplina -> UTM sobre a arquitetura da base.

Uso: python -I verificar.py <disc.dxf> <prefixo_caminho_arq> <dth_graus> <tx> <ty> <base.dxf> <base_dx> <base_dy> [--saida json]
  prefixo_caminho_arq: caminho do bloco de arquitetura na disciplina (ex.: ">ARQ_BASE"); "*" = todos os segmentos
  base_dx/base_dy: translação que leva a base ao UTM (SIT R06: -339.473 0)
Imprime aderência antes/depois do ICP e a transformação refinada.
"""
import sys
import os
import json
import math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar  # noqa: E402
import numpy as np  # noqa: E402

a = sys.argv
disc, pref, dth, tx, ty, base, bdx, bdy = a[1], a[2], float(a[3]), float(a[4]), float(a[5]), a[6], float(a[7]), float(a[8])
saida = a[a.index('--saida') + 1] if '--saida' in a else None
escala1 = '--todas-escalas' not in a

A = casar.cache_load(disc)
B = casar.cache_load(base)

ign = ('CARIMBO', 'FORMATO', 'TOP', 'TEXTO', 'TXT', 'Q-', 'DI-', 'PRO_', 'COTA', 'carimbo', 'NIVEIS', 'NÍVEIS')


def f_disc(s):
    if pref != '*' and not s['path'].startswith(pref):
        return False
    return not any(k in s['lay'] for k in ign)


# só as instâncias de topo do bloco de arquitetura com escala 1 (cópias reduzidas = detalhes da prancha)
raizes = None
if pref != '*':
    nome = pref.split('>')[1]
    raizes = {k for k, i in enumerate(A['inserts']) if i['path'] == '' and i['name'] == nome and (not escala1 or abs(i['s'] - 1) < 1e-6)}
    print('  instâncias usadas de %s: %s' % (nome, sorted(raizes)))
    f_old = f_disc
    f_disc = lambda s: s['root'] in raizes and f_old(s)  # noqa: E731

pa = casar.amostrar(A, f_disc, passo=0.20)
if len(pa) > 40000:
    pa = pa[np.random.default_rng(1).choice(len(pa), 40000, replace=False)]
S = casar.segmentos(B, lambda s: not any(k in s['lay'] for k in ign), d=(bdx, bdy))
print('pontos disciplina %d, segmentos base %d' % (len(pa), len(S)))
G = casar.GradeSeg(S)
T0 = (math.radians(dth), tx, ty)
ad0, ds0 = casar.aderencia_seg(pa, G, T0)
print('antes do ICP : ' + '  '.join('%4.0f mm: %5.1f%%' % (k*1000, v*100) for k, v in ad0.items()))
T1, n = casar.icp_seg(pa, G, T0)
ad1, ds1 = casar.aderencia_seg(pa, G, T1)
print('depois do ICP: ' + '  '.join('%4.0f mm: %5.1f%%' % (k*1000, v*100) for k, v in ad1.items()) + '  (pares %d)' % n)
dd = math.degrees(T1[0]) - dth
print('T0: dθ=%.10f° t=(%.4f, %.4f)' % (dth, tx, ty))
print('T1: dθ=%.10f° t=(%.4f, %.4f)   Δθ=%.6f° (%.1f mm em 100 m)' % (math.degrees(T1[0]), T1[1], T1[2], dd, abs(math.radians(dd))*100000))
# deslocamento do ICP medido no centro da arquitetura da disciplina
c = pa.mean(0)
q0 = casar.aplicar(T0, [c])[0]
q1 = casar.aplicar(T1, [c])[0]
print('diferença T1-T0 no centroide: %.1f mm (dx %.1f, dy %.1f)' % (np.hypot(*(q1 - q0))*1000, (q1-q0)[0]*1000, (q1-q0)[1]*1000))
in5 = ds1 <= 0.02
if in5.sum():
    print('RMS dos pontos a < 2 cm: %.1f mm' % (math.sqrt(np.mean(ds1[in5]**2))*1000))
if saida:
    json.dump({'disc': os.path.basename(disc), 'base': os.path.basename(base), 'base_dx': bdx, 'base_dy': bdy,
               'T_blocos': {'rot_deg': dth, 't': [tx, ty]},
               'T_icp': {'rot_deg': math.degrees(T1[0]), 't': [T1[1], T1[2]]},
               'aderencia_blocos': ad0, 'aderencia_icp': ad1}, open(saida, 'w', encoding='utf-8'), indent=1)
