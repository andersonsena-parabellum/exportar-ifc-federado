# -*- coding: utf-8 -*-
"""Corrige a sobreposição CX-F08 × CX-I01 (guarita), deixada pela fase B: procura a posição mais perto da original da CX-F08 em que ela
não encosta na CX-I01 nem colide com outra rede, levando as pontas dos eletrodutos que chegam nela."""
import sys, os, json, itertools, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"
S, M = JD.carregar(g=os.path.join(C, 'geo_exec'), est='daniel'); JD.agrupar_caixas(S, M)
SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None, discs=('ELE',))
f08 = [m for m in M if m['id'] == '5247215'] ; i01 = [m for m in M if m['id'] == '5247220']
lo8 = np.min([m['lo'] for m in f08], 0); hi8 = np.max([m['hi'] for m in f08], 0); c8 = (lo8 + hi8) / 2
lo1 = np.min([m['lo'] for m in i01], 0); hi1 = np.max([m['hi'] for m in i01], 0); c1 = (lo1 + hi1) / 2
c8h = [((m['lo'] + m['hi']) / 2) for m in MH if m['id'] == '5247215'][0]
print('CX-F08 hoje', c8h.round(2), 'depois', c8.round(2), 'meia', ((hi8 - lo8) / 2).round(2), '| CX-I01 depois', c1.round(2), 'meia', ((hi1 - lo1) / 2).round(2))
pontas = [(i, k) for i, s in enumerate(S) if s['disc'] == 'ELE' for k in ('a', 'b') if np.all(np.abs(s[k][:2] - c8[:2]) <= (hi8 - lo8)[:2] / 2 + 0.2)]
print('pontas de eletroduto na CX-F08:', [(S[i]['trecho'], k) for i, k in pontas])
base = {j: (M[j]['tri'].copy(), M[j]['lo'].copy(), M[j]['hi'].copy()) for j, m in enumerate(M) if m['id'] == '5247215'}
basep = {(i, k): S[i][k].copy() for i, k in pontas}
melhor = []
for dx, dy in itertools.product(np.arange(-1.5, 1.51, 0.25), repeat=2):
    alvo = c8h[:2] + np.array([dx, dy]); v = alvo - c8[:2]
    if np.all(np.abs(alvo - c1[:2]) < (hi1 - lo1)[:2] / 2 + (hi8 - lo8)[:2] / 2 + 0.05): continue      # encosta na CX-I01
    for j, (t, l, h) in base.items():
        T = t.copy(); T[..., 0] += v[0]; T[..., 1] += v[1]; M[j]['tri'] = T; M[j]['lo'] = l + [v[0], v[1], 0]; M[j]['hi'] = h + [v[0], v[1], 0]; M[j].pop('samp', None)
    for (i, k), p in basep.items(): S[i][k] = p + np.array([v[0], v[1], 0])
    IDX = mt.Indice(S, M); col = 0; fol = 0
    for j in base:
        for t, kk, g, pt in mt.avaliar_mesh(j, IDX, 0.20):
            B = S[kk] if t == 'S' else M[kk]
            if (B['disc'] == 'ELE' and t == 'S') or B['id'] == '5247215' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
            if g < -0.002: col += 1
            else: fol += 1
    for (i, k) in pontas:
        for t, kk, g, pt in mt.avaliar_seg(i, IDX, 0.20):
            B = S[kk] if t == 'S' else M[kk]
            if B['disc'] == 'ELE' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
            if g < -0.002: col += 1
    melhor.append((col, round(float(np.hypot(dx, dy)), 2), fol, round(float(dx), 2), round(float(dy), 2), alvo.round(3).tolist()))
melhor.sort()
for m in melhor[:8]: print(m)
json.dump(dict(id='5247215', alvo=melhor[0][5], desloc_depois=(np.array(melhor[0][5]) - c8[:2]).round(4).tolist(), pontas=[(S[i]['id'], k) for i, k in pontas]),
          open(os.path.join(C, 'cx_f08_corrige.json'), 'w', encoding='utf-8'), indent=1)
