# -*- coding: utf-8 -*-
"""Teste de soluções (R02): profundidades recomendadas para as redes cuja cota é premissa (só podem DESCER).
Ordem de preferência do usuário: incêndio e água fria primeiro, depois SDAI, dados/CFTV, elétrica. DRN/ESG/EST/CNT fixos.
Custo por segmento: conflitos (colisão 100; folga<10 cm 5; folga<20 cm 1; fundação/pilar 100; viga 20; laje/parede/IMP 0)
 + peso_disciplina × dz × comprimento × 0,5 + 10 × |Δdz| com vizinhos da mesma corrida + regras (água acima de esgoto/DRN/INC).
Saída: RELATORIOS/compat_R02/solucao_dz.json (dz por id) + resumo."""
import sys, json, math, collections, time
import numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral")
import motor as mt
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
GEO = sys.argv[1] if len(sys.argv) > 1 else mt.G
SEG, MESH = mt.carregar(GEO); IDX = mt.Indice(SEG, MESH)
print('geometria:', GEO)
PESO = {'INC': 1.0, 'AF': 1.2, 'SDAI': 1.5, 'TEL': 2.0, 'ELE': 3.0}
DZMAX = {'INC': 1.0, 'AF': 0.8, 'SDAI': 0.8, 'TEL': 0.6, 'ELE': 0.6}
ORDEM = ['INC', 'AF', 'SDAI', 'TEL', 'ELE']
CAND = np.round(np.arange(0, 1.0001, 0.05), 2)

# vizinhos na mesma corrida (mesma disciplina, ponta comum em planta)
viz = collections.defaultdict(set)
pontas = collections.defaultdict(list)
for i, s in enumerate(SEG):
    for p in (s['a0'], s['b0']): pontas[(s['disc'], round(p[0], 2), round(p[1], 2))].append(i)
for k, ids in pontas.items():
    for i in ids:
        for j in ids:
            if i != j: viz[i].add(j)


def custo_conf(i, lst):
    A = SEG[i]; c = 0.0
    for k, j, g, pt in lst:
        B = SEG[j] if k == 'S' else MESH[j]
        if B['disc'] in ('IMP',): continue
        if B['disc'] == 'EST':
            if B['cat'] in ('Pisos', 'Paredes'): continue
            if g < mt.TOL: c += 20 if B['cat'] == 'Quadro estrutural' else 100
            elif g < 0.10: c += 2
            continue
        if g < mt.TOL: c += 100
        elif g < 0.10: c += 5
        else: c += 1
        # regras de posição relativa (no cruzamento): água potável acima de esgoto, drenagem e incêndio
        if k == 'S' and A['disc'] == 'AF' and B['disc'] in ('ESG', 'DRN', 'INC'):
            if A['a'][2] + (A['b'][2] - A['a'][2]) * 0.5 < pt[2] - 0.01 and pt[2] > min(B['a'][2], B['b'][2]) - 0.5:
                za = np.interp(0, [0, 1], [A['a'][2], A['b'][2]])
        if k == 'S' and B['disc'] == 'AF' and A['disc'] in ('ESG', 'DRN', 'INC'):
            pass
    return c


def z_no_ponto(s, pt):
    d = s['b'] - s['a']; L2 = d[0] ** 2 + d[1] ** 2
    t = 0.5 if L2 < 1e-9 else np.clip(((pt[0] - s['a'][0]) * d[0] + (pt[1] - s['a'][1]) * d[1]) / L2, 0, 1)
    return s['a'][2] + d[2] * t


def regra_agua(i, lst):
    """penaliza água fria abaixo de esgoto/drenagem/incêndio nos cruzamentos (folga<0,20)."""
    A = SEG[i]; c = 0.0
    for k, j, g, pt in lst:
        if k != 'S': continue
        B = SEG[j]
        if A['disc'] == 'AF' and B['disc'] in ('ESG', 'DRN', 'INC') and z_no_ponto(A, pt) < z_no_ponto(B, pt): c += 40
        if B['disc'] == 'AF' and A['disc'] in ('ESG', 'DRN', 'INC') and z_no_ponto(B, pt) < z_no_ponto(A, pt): c += 40
    return c


def custo(i):
    s = SEG[i]; lst = mt.avaliar_seg(i, IDX)
    L = float(np.linalg.norm(s['b0'] - s['a0']))
    c = custo_conf(i, lst) + regra_agua(i, lst) + PESO[s['disc']] * s['dz'] * L * 0.5
    c += sum(10 * abs(s['dz'] - SEG[j]['dz']) for j in viz[i])
    return c, lst

base = {}
for i, s in enumerate(SEG):
    lst = mt.avaliar_seg(i, IDX); base[i] = lst
conflitantes = {i for i, l in base.items() if l}
print(f'segmentos {len(SEG)} | com folga<20 cm: {len(conflitantes)} | {time.time()-t0:.0f}s')

mudou = True; passe = 0
while mudou and passe < 4:
    mudou = False; passe += 1; nm = 0
    alvo = sorted([i for i in range(len(SEG)) if SEG[i]['disc'] in PESO and (i in conflitantes or SEG[i]['dz'] > 0)],
                  key=lambda i: (ORDEM.index(SEG[i]['disc']), SEG[i]['trecho']))
    for i in alvo:
        s = SEG[i]; atual = s['dz']; best = (custo(i)[0], atual)
        for dz in CAND:
            if dz > DZMAX[s['disc']] or abs(dz - atual) < 1e-9: continue
            mt.mover(i, dz, IDX); c, _ = custo(i)
            # o movimento também muda o custo dos vizinhos de corrida (degrau): já incluído em custo(i)
            if c < best[0] - 0.5: best = (c, dz)
        mt.mover(i, best[1], IDX)
        if abs(best[1] - atual) > 1e-9: mudou = True; nm += 1
    print(f'passe {passe}: {nm} segmentos mudaram | {time.time()-t0:.0f}s')

# ---------------- fase 2: desvio em planta (caixas, PVs, sapata do muro) para quem ainda colide
def custo2(i):
    c, lst = custo(i); s = SEG[i]; L = float(np.linalg.norm(s['b0'] - s['a0']))
    dx, dy = s.get('dxy', (0.0, 0.0)); off = math.hypot(dx, dy)
    c += PESO[s['disc']] * off * L * 0.3
    c += sum(10 * math.hypot(dx - SEG[j].get('dxy', (0, 0))[0], dy - SEG[j].get('dxy', (0, 0))[1]) for j in viz[i])
    return c, lst
OFF = [0.3, 0.6, 0.9, 1.2, 1.5, 2.0]
alvo2 = []
for i, s in enumerate(SEG):
    if s['disc'] not in PESO: continue
    lst = mt.avaliar_seg(i, IDX)
    if any(g < mt.TOL and (((MESH[j]['disc'] != 'IMP') and not (MESH[j]['disc'] == 'EST' and MESH[j]['cat'] in ('Pisos', 'Paredes', 'Quadro estrutural'))) if k == 'M' else SEG[j]['disc'] not in PESO) for k, j, g, pt in lst): alvo2.append(i)
print(f'fase 2: {len(alvo2)} segmentos ainda colidindo com caixas/PV/sapata ou rede por gravidade')
nm = 0
for i in sorted(alvo2, key=lambda i: ORDEM.index(SEG[i]['disc'])):
    s = SEG[i]; u = (s['b0'] - s['a0'])[:2]; u = u / (np.linalg.norm(u) + 1e-12); n = np.array([-u[1], u[0]])
    dz0 = s['dz']; best = (custo2(i)[0], dz0, (0.0, 0.0))
    for o in OFF:
        for sg in (1, -1):
            dxy = (float(n[0] * o * sg), float(n[1] * o * sg))
            for dz in sorted({dz0, max(0, dz0 - 0.1), dz0 + 0.1, dz0 + 0.2}):
                if dz > DZMAX[s['disc']]: continue
                mt.mover(i, dz, IDX, dxy); c, _ = custo2(i)
                if c < best[0] - 0.5: best = (c, dz, dxy)
    mt.mover(i, best[1], IDX, best[2])
    if best[2] != (0.0, 0.0): nm += 1
print(f'fase 2: {nm} desvios em planta | {time.time()-t0:.0f}s')

# ---------------- fase 3: caixas das redes móveis (ELE, TEL, SDAI, AF) colidindo -> mudar a caixa de lugar
MOV_CX = {'ELE', 'TEL', 'SDAI', 'AF'}
def custo_mesh(j):
    c = 0.0
    for k, i, g, pt in mt.avaliar_mesh(j, IDX):
        B = SEG[i] if k == 'S' else MESH[i]
        if B['disc'] == 'IMP' or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
        c += 100 if g < mt.TOL else (5 if g < 0.10 else 1)
    dx, dy = MESH[j].get('dxy', (0.0, 0.0)); return c + 3 * math.hypot(dx, dy)
alvo3 = [j for j, M in enumerate(MESH) if M['disc'] in MOV_CX and M['cat'] == 'Modelos genéricos'
         and any(g < mt.TOL and not ((SEG[i] if k == 'S' else MESH[i])['disc'] == 'IMP') for k, i, g, pt in mt.avaliar_mesh(j, IDX))]
print(f'fase 3: {len(alvo3)} caixas colidindo')
for j in alvo3:
    best = (custo_mesh(j), (0.0, 0.0))
    for o in (0.5, 1.0, 1.5, 2.0):
        for ang in range(0, 360, 45):
            d = (o * math.cos(math.radians(ang)), o * math.sin(math.radians(ang)))
            mt.mover_mesh(j, d, IDX); c = custo_mesh(j)
            if c < best[0] - 0.5: best = (c, d)
    mt.mover_mesh(j, best[1], IDX)
    if best[1] != (0.0, 0.0): print(f"   caixa {MESH[j]['disc']} {MESH[j]['trecho']}: mover {math.hypot(*best[1]):.1f} m")

sol = {SEG[i]['id']: {'dz': SEG[i]['dz'], 'dxy': list(SEG[i].get('dxy', (0.0, 0.0)))} for i in range(len(SEG)) if SEG[i]['dz'] > 0 or SEG[i].get('dxy', (0, 0)) != (0.0, 0.0)}
solm = {M['id']: {'dxy': list(M['dxy'])} for M in MESH if M.get('dxy', (0, 0)) != (0.0, 0.0)}
json.dump({'seg': sol, 'mesh': solm}, open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\solucao_dz.json", 'w', encoding='utf-8'), indent=0)
for i, s in enumerate(SEG):
    if s.get('dxy', (0, 0)) != (0.0, 0.0): print(f"   desvio {s['disc']:5s} {s['trecho']:16s} {math.hypot(*s['dxy']):.2f} m  dz {s['dz']:.2f}  L={np.linalg.norm(s['b0']-s['a0']):.1f}")
por = collections.defaultdict(list)
for i, s in enumerate(SEG):
    if s['dz'] > 0: por[(s['disc'], s['trecho'].split('.')[0])].append((s['dz'], float(np.linalg.norm(s['b0'] - s['a0']))))
print('segmentos aprofundados:', len(sol))
for k in sorted(por, key=lambda k: (ORDEM.index(k[0]), k[1])):
    v = por[k]; print(f'   {k[0]:5s} {k[1]:14s} n={len(v):3d}  dz {min(d for d,_ in v):.2f}..{max(d for d,_ in v):.2f}  L={sum(l for _,l in v):6.1f} m')
