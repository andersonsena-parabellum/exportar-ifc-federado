# -*- coding: utf-8 -*-
"""Jandaíra — Fase C (água fria), regra "mexer o mínimo" (usuário, 18/10/2026), sobre compat_R01/geo_exec (PCI e ELE já revisados):
 - reúso (AR, não potável): MERGULHO local por baixo do obstáculo (10 cm de folga, rampas a 45° para usar as curvas de 45°), eixo até 1,60 m do terreno;
 - potável (AL/AFP): não pode passar por baixo de esgoto/drenagem/incêndio → onde bate em caixa, poço ou tubo dessas redes, o TUBO É DESLOCADO em planta
   (paralelo, 0,3–1,5 m, o lado que dá menos conflito); o resto fica como está.
Saída: compat_R01/af_plano.json (mergulhos e deslocamentos por id) + resumo."""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, motor as mt
sys.stdout.reconfigure(encoding='utf-8')
D = os.path.dirname(JD.G); GX = os.path.join(D, 'geo_exec')
FOLGA_V, FOLGA_H, RAMPA, PROF_MAX = 0.10, 0.15, 1.0, 1.60
SEG, MESH = JD.carregar(g=GX, est='daniel'); JD.agrupar_caixas(SEG, MESH)
T = JD.Terreno(g=GX)


def potavel(s): return 'Alimenta' in s['sis'] or 'Pot' in s['sis']


# reúso que corre em cima do coletor de esgoto (mergulhar por baixo dos poços bate no próprio coletor): desloca como a potável
DESLOCAR = {'AR-16'}
def desloca(s): return potavel(s) or s['trecho'] in DESLOCAR


def horizontal(s):
    L = np.linalg.norm(s['b0'][:2] - s['a0'][:2]); return L > 0.3 and abs(s['b0'][2] - s['a0'][2]) < 0.5 * L and max(s['a0'][2], s['b0'][2]) < -0.15


AF = [i for i, s in enumerate(SEG) if s['disc'] == 'AF' and horizontal(s)]
# conexões/acessórios da AF não entram no custo (acompanham os tubos)
IGN = {j for j, M in enumerate(MESH) if M['disc'] == 'AF' and M['cat'].startswith(('Conex', 'Acess'))}
IDX = mt.Indice(SEG, MESH)


def conflitos(i, folga=mt.TOL):
    out = []
    for t, j, g, pt in mt.avaliar_seg(i, IDX, 0.20):
        if t == 'M' and j in IGN: continue
        B = SEG[j] if t == 'S' else MESH[j]
        if B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes', 'Quadro estrutural'): continue
        out.append((t, j, g, pt, B))
    return out


def custo(i):
    s = SEG[i]; c = 0.0
    for t, j, g, pt, B in conflitos(i):
        c += 100 if g < mt.TOL else (3 if g < 0.10 else 1)
        if t == 'S' and potavel(s) and B['disc'] in ('ESG', 'DRE', 'INC'):
            d = s['b'] - s['a']; L2 = d[0] ** 2 + d[1] ** 2
            u = 0.5 if L2 < 1e-9 else np.clip(((pt[0] - s['a'][0]) * d[0] + (pt[1] - s['a'][1]) * d[1]) / L2, 0, 1)
            e = B['b'] - B['a']; L3 = e[0] ** 2 + e[1] ** 2
            v = 0.5 if L3 < 1e-9 else np.clip(((pt[0] - B['a'][0]) * e[0] + (pt[1] - B['a'][1]) * e[1]) / L3, 0, 1)
            if s['a'][2] + d[2] * u < B['a'][2] + e[2] * v: c += 150
    dx, dy = s.get('dxy', (0.0, 0.0)); return c + 5 * math.hypot(dx, dy)


# 1) potável: deslocamento paralelo para quem colide
desloc = {}
SO_MERG = bool(os.environ.get('JAN_AF_SO_MERGULHO'))   # linhas já deslocadas no Revit (jan_af_grupos.py): só mergulhos
for i in ([] if SO_MERG else AF):
    s = SEG[i]
    if not desloca(s) or not any(g < mt.TOL for t, j, g, pt, B in conflitos(i)): continue
    u = (s['b0'] - s['a0'])[:2]; u /= np.linalg.norm(u); n = np.array([-u[1], u[0]])
    best = (custo(i), (0.0, 0.0))
    for o in (0.3, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0):
        for sg in (1, -1):
            d = (float(n[0] * o * sg), float(n[1] * o * sg)); mt.mover(i, 0.0, IDX, d); c = custo(i)
            if c < best[0] - 0.5: best = (c, d)
    mt.mover(i, 0.0, IDX, best[1])
    if best[1] != (0.0, 0.0): desloc[s['id']] = dict(trecho=s['trecho'], dxy=best[1])
print('potável deslocada:', {v['trecho']: round(math.hypot(*v['dxy']), 1) for v in desloc.values()})

# 2) reúso: mergulhos por baixo do que ainda colide
mergulhos = collections.defaultdict(list); sem = []
for i in AF:
    s = SEG[i]
    a, b = s['a'], s['b']; L = np.linalg.norm(b[:2] - a[:2]); u = (b[:2] - a[:2]) / L
    for t, j, g, pt, B in conflitos(i):
        if g >= mt.TOL: continue
        if potavel(s) and B['disc'] not in ('ELE', 'SDAI'): continue   # potável só mergulha sob elétrica/alarme
        if t == 'S':
            e = B['b'] - B['a']; L3 = e[0] ** 2 + e[1] ** 2
            v = 0.5 if L3 < 1e-9 else np.clip(((pt[0] - B['a'][0]) * e[0] + (pt[1] - B['a'][1]) * e[1]) / L3, 0, 1)
            fundo = B['a'][2] + e[2] * v - B['de'] / 2; r = B['de'] / 2
            sc = float(np.dot(pt[:2] - a[:2], u)); s1, s2 = sc - r - FOLGA_H - s['de'] / 2, sc + r + FOLGA_H + s['de'] / 2
        else:
            lo = B.get('glo') if B.get('glo') is not None else B['lo']; hi = B.get('ghi') if B.get('ghi') is not None else B['hi']
            fundo = lo[2]; cs = [np.dot(np.array([x, y]) - a[:2], u) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])]
            s1, s2 = min(cs) - FOLGA_H - s['de'] / 2, max(cs) + FOLGA_H + s['de'] / 2
        zq = fundo - FOLGA_V - s['de'] / 2; zt = T.z(pt[0], pt[1])
        if not np.isnan(zt) and zq < zt - PROF_MAX: sem.append((s['trecho'], B.get('grupo', B.get('trecho')), round(zt - zq, 2))); continue
        mergulhos[s['id']].append((max(0.0, s1), min(L, s2), zq))
print('reúso com mergulho:', {SEG[i]['trecho']: len(mergulhos[SEG[i]['id']]) for i in AF if SEG[i]['id'] in mergulhos})
print('sem solução por profundidade:', sem)


def vertices(s, dips):
    """polilinha (x, y, z) do tubo com os mergulhos (rampas 1:RAMPA), de a até b."""
    a, b = s['a'], s['b']; L = np.linalg.norm(b[:2] - a[:2]); z0a, z0b = a[2], b[2]
    ts = np.unique(np.concatenate([np.arange(0, L, 0.02), [L]]))
    zb = z0a + (z0b - z0a) * ts / L; z = zb.copy()
    for s1, s2, zq in dips:
        z = np.minimum(z, zq + np.maximum(0, np.maximum(s1 - ts, ts - s2)) / RAMPA)
    # pontos de quebra = onde a inclinação muda
    k = [0] + [m for m in range(1, len(ts) - 1) if abs((z[m + 1] - z[m]) - (z[m] - z[m - 1])) > 1e-6] + [len(ts) - 1]
    return [[float(a[0] + (b[0] - a[0]) * ts[m] / L), float(a[1] + (b[1] - a[1]) * ts[m] / L), float(z[m])] for m in k]


plano = dict(deslocados=desloc, mergulhos={}, sem_solucao=sem)
for i in AF:
    s = SEG[i]
    if s['id'] in mergulhos: plano['mergulhos'][s['id']] = dict(trecho=s['trecho'], vertices=vertices(s, mergulhos[s['id']]))
json.dump(plano, open(os.path.join(D, 'af_plano.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
# avaliação: aplica (deslocados já estão no índice; mergulhos viram sub-segmentos)
S2 = []
for i, s in enumerate(SEG):
    if s['id'] in plano['mergulhos']:
        V = plano['mergulhos'][s['id']]['vertices']
        for m in range(len(V) - 1):
            d = dict(s); d.update(id=f"{s['id']}~{m}", a=np.array(V[m]), b=np.array(V[m + 1]), a0=np.array(V[m]), b0=np.array(V[m + 1])); S2.append(d)
    else: S2.append(s)
IDX2 = mt.Indice(S2, MESH); res = []
for i, s in enumerate(S2):
    if s['disc'] != 'AF': continue
    for t, j, g, pt in mt.avaliar_seg(i, IDX2):
        if t == 'M' and j in IGN: continue
        B = S2[j] if t == 'S' else MESH[j]
        if B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes', 'Quadro estrutural'): continue
        if g < mt.TOL: res.append((s['trecho'], B['disc'], B.get('grupo', B.get('trecho')), round(g * 100, 1)))
print('colisões da água fria que sobram:', len(set(res)))
for r in sorted(set(res)): print('  ', r)
import pickle; pickle.dump((S2, MESH), open(os.path.join(D, 'af_plano_geo.pkl'), 'wb'))
