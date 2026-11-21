# -*- coding: utf-8 -*-
"""Compara duas rodadas do preclash da Jandaíra trecho a trecho (JAN.json): cota do eixo das pressurizadas e da gravidade.
Serve para provar que uma rodada só de IFC (classes, peças) não mexeu em rede nenhuma.
Uso: python -X utf8 comparar_rodadas.py <pasta_ref> <pasta_nova> [tol_m]"""
import os, sys, json, csv, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ref, nova = sys.argv[1], sys.argv[2]; tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02


def carregar(p):
    J = json.load(open(os.path.join(p, 'JAN.json'), encoding='utf-8'))
    out = {}
    for e in J['elementos']:
        if 'AD' not in e.get('cen', ['AD']): continue
        P = np.array((e.get('sol') or {}).get('AD') or e['p'], float)
        out[e['id']] = (e, P)
    return out, J


A, JA = carregar(ref); B, JB = carregar(nova)
so_a = sorted(set(A) - set(B)); so_b = sorted(set(B) - set(A))
dif = []
for k in sorted(set(A) & set(B)):
    (ea, Pa), (eb, Pb) = A[k], B[k]
    # z do eixo nova interpolado nos pontos (planta) da referência, pelo ponto mais próximo de cada segmento
    def z_em(P, q):
        best = (1e9, None)
        for a, b in zip(P[:-1], P[1:]):
            d = b[:2] - a[:2]; L2 = d @ d
            t = 0.0 if L2 < 1e-12 else float(np.clip((q[:2] - a[:2]) @ d / L2, 0, 1)); p = a + (b - a) * t
            dd = float(np.hypot(*(p[:2] - q[:2])))
            if dd < best[0]: best = (dd, p[2])
        return best
    m = 0.0
    for q in Pa:
        dd, z = z_em(Pb, q)
        if dd < 0.05: m = max(m, abs(z - q[2]))
    if m > tol: dif.append((k, ea['disc'], ea['trecho'], round(m, 3)))
print(f'elementos: ref {len(A)}, nova {len(B)}; só na ref {len(so_a)}, só na nova {len(so_b)}; com Δz > {tol} m: {len(dif)}')
print('  só na ref (amostra):', so_a[:12])
print('  só na nova (amostra):', so_b[:12])
for x in sorted(dif, key=lambda x: -x[3])[:40]: print('  Δz', x)
print('  por disciplina:', collections.Counter(x[1] for x in dif))
for p in (ref, nova):
    fn = os.path.join(p, 'JAN_preclash_AD_conflitos_depois.csv')
    if os.path.exists(fn):
        R = list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';'))
        ch = [k for k in R[0].keys() if 'sever' in k.lower() or 'classe' in k.lower() or 'nivel' in k.lower()] if R else []
        print(os.path.basename(p), 'conflitos depois:', len(R), collections.Counter(r[ch[0]] for r in R) if ch else '')
