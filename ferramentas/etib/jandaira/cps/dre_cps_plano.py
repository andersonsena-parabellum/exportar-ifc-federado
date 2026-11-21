# -*- coding: utf-8 -*-
"""Fase E (R01) — drenagem do campo 50x30 (CPS DRE-001 R01) ligada à rede externa do JAN-DRE. Monta no interno, testa o clash e grava
compat_R01/cps_dre_instrucoes.tsv para FERRAMENTAS/jandaira/faseE_cps_dre.cs.

Compatibilização adotada (o CPS não fecha com a rede da implantação):
 - espinha e drenos em espinha de peixe no traçado do CPS, mas descarregando a OESTE na CX-43 (como a drenagem de hoje): o CPS manda
   para leste, onde a implantação não tem rede;
 - saídas das canaletas ligadas às caixas existentes do coletor do perímetro (CX-40/41/42 ao norte, CX-14/16/19 ao sul), no lugar das
   caixas de areia do CPS, que ficariam além do coletor: os 6 ramais de hoje só encurtam até a canaleta do campo 50x30;
 - 1 % em tudo; ponta alta dos drenos com eixo 0,25 m abaixo do campo (cota 146,75); CX-43 aprofundada e DRE-060 refeito a 1 %
   (chega na PI-01 1 cm acima do fundo);
 - sai a espinha de peixe do campo 45x25 (DRE-001..011, 014, 015, 016, 022) e o DRE-040 (V20 -> CX-43).
Coordenadas do campo: origem no centro do campo do CPS (interno 90,952 / 114,112), x ao longo (leste +), y transversal (norte +)."""
import sys, os, json, math, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"
CI = np.array([90.952, 114.112]); A = math.radians(-5.3818); R = np.array([[math.cos(A), -math.sin(A)], [math.sin(A), math.cos(A)]])
I = lambda p: R @ np.asarray(p, float) + CI                    # campo -> interno (xy)
F = lambda p: R.T @ (np.asarray(p[:2], float) - CI)           # interno -> campo
I_SLOPE, Z_TOPO, DN_ESP, DN_DR = 0.01, -0.25, 0.150, 0.100
rede = json.load(open(os.path.join(C, 'cps_dre_rede.json'), encoding='utf-8'))
SEG, MESH = JD.carregar(g=os.path.join(C, 'geo_exec'), est='daniel'); JD.agrupar_caixas(SEG, MESH)
por_marca = {s['trecho']: s for s in SEG if s['disc'] == 'DRE'}
SAI = ['DRE-%03d' % k for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 22, 40)]
# --- espinha (junções dos drenos) e drenos
dr = [e for e in rede['eixos'] if e['larg'] < 0.12]
jun = sorted({round(e['b'][0], 1) for e in dr})                 # x das junções na espinha (ponta b de cada dreno)
x_ini, x_fim = max(jun), -23.566                                # espinha corre de leste (ponta alta) para oeste
y_esp = -0.08
def z_esp(x): return z0 - I_SLOPE * (x_ini - x)
# ponta alta: dreno que chega na junção mais a leste começa na cota Z_TOPO
L_leste = max(np.linalg.norm(np.subtract(e['b'], e['a'])) for e in dr if round(e['b'][0], 1) == x_ini)
z0 = Z_TOPO - I_SLOPE * L_leste
novos = []
xs = sorted(set(jun) | {x_fim}, reverse=True)
for k in range(len(xs) - 1):
    novos.append(dict(tipo='PVCR150', marca='DRE-CPS-E%02d' % (k + 1), a=[*I((xs[k], y_esp)), z_esp(xs[k])], b=[*I((xs[k + 1], y_esp)), z_esp(xs[k + 1])], de=DN_ESP))
cx43 = [M for M in MESH if M.get('grupo') == 'CX-43'][0]; c43 = ((cx43['glo'] + cx43['ghi']) / 2)[:2]
L43 = np.linalg.norm(c43 - I((x_fim, y_esp))); z43 = z_esp(x_fim) - I_SLOPE * L43
novos.append(dict(tipo='PVCR150', marca='DRE-CPS-E%02d' % len(xs), a=[*I((x_fim, y_esp)), z_esp(x_fim)], b=[*c43, z43], de=DN_ESP))
for n, e in enumerate(sorted(dr, key=lambda e: (e['b'][0], e['a'][1]))):
    Lb = np.linalg.norm(np.subtract(e['b'], e['a'])); xb = round(e['b'][0], 1); zj = z_esp(xb)
    novos.append(dict(tipo='PVCDR100', marca='DRE-CPS-D%02d' % (n + 1), a=[*I(e['a']), zj + I_SLOPE * Lb], b=[*I((e['b'][0], y_esp)), zj], de=DN_DR))
# --- CX-43 mais funda e DRE-060 a 1 % até a PI-01
d60 = por_marca['DRE-060']; L60 = np.linalg.norm(d60['b'][:2] - d60['a'][:2]); z60b = z43 - I_SLOPE * L60
pi = [M for M in MESH if M.get('grupo') == 'PI-01'][0]
mod = [dict(marca='DRE-060', id=d60['id'], a=[*d60['a'][:2], z43], b=[*d60['b'][:2], z60b])]
fundo43 = z43 - DN_ESP / 2
# --- ramais das canaletas: encurtar até a canaleta do campo 50x30 (y = +-16,97), mantendo a chegada na caixa e 1 %
Y_CAN = 16.97
for mk in ('DRE-018', 'DRE-053', 'DRE-079', 'DRE-031', 'DRE-058', 'DRE-084'):
    s = por_marca[mk]; pa, pb = F(s['a']), F(s['b']); lado = np.sign(pa[1])
    t = (lado * Y_CAN - pa[1]) / (pb[1] - pa[1]); na = pa + (pb - pa) * t; Ln = np.linalg.norm(pb - na)
    mod.append(dict(marca=mk, id=s['id'], a=[*I(na), s['b'][2] + I_SLOPE * Ln], b=s['b'].tolist()))
# --- canaletas (54 x 0,50, 0,30 de fundo) nos lados longos
can = [dict(marca='DRE-CPS-CAN-N', c=I((0, 16.75)).tolist(), y=16.75), dict(marca='DRE-CPS-CAN-S', c=I((0, -16.75)).tolist(), y=-16.75)]
print('espinha: %d trechos, %.1f m, eixo de %.3f a %.3f (CX-43); drenos: %d, %.1f m; ponta alta mais rasa %.3f' % (
    len(xs), sum(np.linalg.norm(np.subtract(n['b'][:2], n['a'][:2])) for n in novos if n['tipo'] == 'PVCR150'), z0, z43,
    sum(1 for n in novos if n['tipo'] == 'PVCDR100'), sum(np.linalg.norm(np.subtract(n['b'][:2], n['a'][:2])) for n in novos if n['tipo'] == 'PVCDR100'),
    max(n['a'][2] for n in novos if n['tipo'] == 'PVCDR100')))
print('CX-43: fundo %.3f (hoje %.3f) | DRE-060 chega na PI-01 com eixo %.3f, geratriz inferior %.3f (fundo da PI-01 %.3f)' % (fundo43, cx43['glo'][2], z60b, z60b - DN_ESP / 2, pi['glo'][2]))
for m in mod[1:]: print('  ramal %s: começa em %.3f (hoje %.3f), L %.1f m' % (m['marca'], m['a'][2], por_marca[m['marca']]['a'][2], np.linalg.norm(np.subtract(m['b'][:2], m['a'][:2]))))
# ===== teste: aplica na geometria e roda o clash das peças novas/alteradas
base = dict(k='S', disc='DRE', fonte='DRE', cat='Tubulação', tipo='', sis='Pluvial', dn='', dz=0.0)
S2 = [s for s in SEG if not (s['disc'] == 'DRE' and s['trecho'] in SAI)]
idm = {m['id']: m for m in mod}
for s in S2:
    if s['id'] in idm: m = idm[s['id']]; s['a'] = np.array(m['a']); s['b'] = np.array(m['b']); s['teste'] = True
for n in novos:
    d = dict(base); d.update(id=n['marca'], trecho=n['marca'], grupo=n['marca'], de=n['de'], desc='CPS', a=np.array(n['a']), b=np.array(n['b']), teste=True); d['a0'] = d['a'].copy(); d['b0'] = d['b'].copy(); S2.append(d)
def caixa(c, u, comp, larg, z0_, z1_):
    u = np.array([*u]); u = u / np.linalg.norm(u); v = np.array([-u[1], u[0]]); c = np.array(c)
    P = [c + su * u * comp / 2 + sv * v * larg / 2 for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    V = [np.array([*p, z0_]) for p in P] + [np.array([*p, z1_]) for p in P]
    Fc = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[V[i] for i in f] for f in Fc])
M2 = list(MESH); ux = R @ np.array([1.0, 0.0])
for cn in can:
    tri = caixa(cn['c'], ux, 54.0, 0.50, -0.30, 0.0); M2.append(dict(k='M', disc='DRE', fonte='DRE', id=cn['marca'], cat='Modelos genéricos', nome='Canaleta', trecho=cn['marca'], grupo=cn['marca'], desc='CPS', tri=tri, lo=tri.reshape(-1, 3).min(0), hi=tri.reshape(-1, 3).max(0), bloco='', teste=True))
for M in M2:
    if M.get('grupo') == 'CX-43':
        T = M['tri'].copy(); T[..., 2] = np.where(T[..., 2] < cx43['glo'][2] + 0.05, fundo43, T[..., 2]); M['tri'] = T; M['lo'] = T.reshape(-1, 3).min(0); M['glo'] = np.array([*cx43['glo'][:2], fundo43]); M.pop('samp', None); M['teste'] = True
IDX = mt.Indice(S2, M2); res = set()
ign = lambda B: (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')) or (B['disc'] == 'DRE' and (B['cat'].startswith(('Conex', 'Acess')) or B.get('grupo') in ('CX-43', 'PI-01', 'CX-40', 'CX-41', 'CX-42', 'CX-14', 'CX-16', 'CX-19')))
for i, s in enumerate(S2):
    if not s.get('teste'): continue
    for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
        B = S2[j] if t == 'S' else M2[j]
        if B.get('teste') and B['disc'] == 'DRE' or ign(B): continue
        res.add((s['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt[:2], 1))))
for j, M in enumerate(M2):
    if not M.get('teste'): continue
    for t, k, g, pt in mt.avaliar_mesh(j, IDX, 0.20):
        B = S2[k] if t == 'S' else M2[k]
        if (B.get('teste') and B['disc'] == 'DRE') or ign(B) or (B['disc'] == 'DRE' and B.get('trecho') in ('DRE-060',)): continue
        res.add((M['grupo'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1), tuple(np.round(pt[:2], 1))))
res = sorted(res, key=lambda r: r[3])
print('clash das peças novas/alteradas: %d colisões, %d folgas < 20 cm' % (sum(1 for r in res if r[3] < -0.2), sum(1 for r in res if r[3] >= -0.2)))
for r in res: print('  ', r)
# ===== instruções para o Revit
L = []
for mk in SAI: L.append('\t'.join(['DEL', por_marca[mk]['id'], mk]))
for m in mod: L.append('\t'.join(['MOD', m['id'], m['marca']] + ['%.4f' % v for v in (*m['a'], *m['b'])]))
for n in novos: L.append('\t'.join(['NEW', n['tipo'], n['marca']] + ['%.4f' % v for v in (*n['a'], *n['b'])]))
L.append('\t'.join(['CX', 'CX-43', '%.4f' % fundo43]))
for cn in can: L.append('\t'.join(['CAN', cn['marca'], '%.4f' % cn['c'][0], '%.4f' % cn['c'][1], '%.6f' % ux[0], '%.6f' % ux[1]]))
open(os.path.join(C, 'cps_dre_instrucoes.tsv'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('instruções:', len(L), 'linhas')
