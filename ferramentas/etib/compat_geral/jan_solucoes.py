# -*- coding: utf-8 -*-
"""Jandaíra — teste de soluções numa cópia da geometria (os RVTs não mudam).
Redes com cota de premissa (INC, SDAI, AF, ELE) só podem DESCER e, depois, desviar em planta; caixas de ELE/SDAI/AF podem mudar de lugar.
DRE, ESG e estruturas ficam fixos (gravidade e terceiros): o que sobrar entre eles é "a definir pelo projetista".
Custo por segmento: conflitos (colisão 100; folga<10 cm 5; folga<20 cm 1; fundação/pilar 100; viga 20; piso/parede 0)
 + peso × dz × comprimento × 0,5 + 10 × |Δdz| com vizinhos da mesma corrida + água potável acima de ESG/DRE/INC (40).
Saída: RELATORIOS/compat_R01/solucao_R01.json + solucao_R01_trechos.csv. Uso: jan_solucoes.py [est=daniel|0]"""
import sys, os, json, math, csv, collections, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor as mt, jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
EST = sys.argv[1] if len(sys.argv) > 1 else 'daniel'
SAIDA = os.path.dirname(JD.G)
SEG, MESH = JD.carregar(est=None if EST == '0' else EST)
JD.agrupar_caixas(SEG, MESH)
PESO = {'INC': 1.0, 'SDAI': float(os.environ.get('JAN_PESO_SDAI', '1.2')), 'ELE': 1.3, 'AF': 1.3}
DZMAX = {'INC': 0.60, 'SDAI': 0.80, 'ELE': 0.60, 'AF': 0.80}
ORDEM = ['INC', 'SDAI', 'ELE', 'AF']
CAND = np.round(np.arange(0, 1.2001, 0.05), 2)
# cenário: recobrimento mínimo da elétrica (NBR 5410), ex.: JAN_ELE_RECOB=0.70 -> descida mínima por trecho
ELE_RECOB = float(os.environ.get('JAN_ELE_RECOB', '0'))
SUF = os.environ.get('JAN_SUFIXO', '')
DZMIN = {}
AGUA = float(os.environ.get('JAN_AGUA', '150'))   # água potável abaixo de ESG/DRE/INC: pior que uma colisão (NBR 5626)


def movel(s):
    if s['disc'] not in PESO: return False
    a, b = s['a0'], s['b0']; L = np.linalg.norm(b[:2] - a[:2])
    if max(a[2], b[2]) > -0.15: return False            # trecho acima do terreno (barrilete, subidas)
    return L > 0.05 and abs(b[2] - a[2]) < 0.5 * L       # horizontais/inclinados; verticais acompanham


def potavel(s): return s['disc'] == 'AF' and ('Alimenta' in s['sis'] or 'Pot' in s['sis'])


def dist_ps(p, a, b):
    d = b - a; L2 = d @ d
    t = 0.0 if L2 < 1e-12 else float(np.clip((p - a) @ d / L2, 0, 1))
    return float(np.linalg.norm(p - (a + d * t)))


# conexões/acessórios das redes móveis acompanham o trecho mais próximo (não entram no custo)
anexo = {}
movs = [i for i, s in enumerate(SEG) if s['disc'] in PESO]
for j, M in enumerate(MESH):
    if M['disc'] in PESO and M['cat'].startswith(('Conex', 'Acess')):
        c = (M['lo'] + M['hi']) / 2
        best = min(((dist_ps(c, SEG[i]['a0'], SEG[i]['b0']), i) for i in movs if SEG[i]['fonte'] == M['fonte']), default=(9, None))
        if best[0] < 0.4: anexo[j] = best[1]
IGN = set(anexo)
IDX = mt.Indice(SEG, MESH)

viz = collections.defaultdict(set); pontas = collections.defaultdict(list)
for i, s in enumerate(SEG):
    for p in (s['a0'], s['b0']): pontas[(s['disc'], round(p[0] / 0.05), round(p[1] / 0.05))].append(i)
for ids in pontas.values():
    for i in ids: viz[i] |= set(ids) - {i}


def z_no_ponto(s, pt):
    d = s['b'] - s['a']; L2 = d[0] ** 2 + d[1] ** 2
    t = 0.5 if L2 < 1e-9 else np.clip(((pt[0] - s['a'][0]) * d[0] + (pt[1] - s['a'][1]) * d[1]) / L2, 0, 1)
    return s['a'][2] + d[2] * t


def custo_lista(A, lst):
    c = 0.0
    for k, j, g, pt in lst:
        if k == 'M' and j in IGN: continue
        B = SEG[j] if k == 'S' else MESH[j]
        if B['disc'] == 'EST':
            if B['cat'] in ('Pisos', 'Paredes'): continue
            if g < mt.TOL: c += 20 if B['cat'] == 'Quadro estrutural' else 100
            elif g < 0.10: c += 2
            continue
        c += 100 if g < mt.TOL else (5 if g < 0.10 else 1)
        if k == 'S':
            if potavel(A) and B['disc'] in ('ESG', 'DRE', 'INC') and z_no_ponto(A, pt) < z_no_ponto(B, pt): c += AGUA
            if potavel(B) and A['disc'] in ('ESG', 'DRE', 'INC') and z_no_ponto(B, pt) < z_no_ponto(A, pt): c += AGUA
    return c


def custo(i):
    s = SEG[i]; lst = mt.avaliar_seg(i, IDX); L = float(np.linalg.norm(s['b0'] - s['a0']))
    dx, dy = s.get('dxy', (0.0, 0.0))
    c = custo_lista(s, lst) + PESO[s['disc']] * (s['dz'] * L * 0.5 + math.hypot(dx, dy) * L * 0.3)
    c += sum(10 * abs(s['dz'] - SEG[j]['dz']) + 10 * math.hypot(dx - SEG[j].get('dxy', (0, 0))[0], dy - SEG[j].get('dxy', (0, 0))[1]) for j in viz[i] if movel(SEG[j]))
    return c, lst


alvo = [i for i, s in enumerate(SEG) if movel(s)]
if ELE_RECOB:
    TT = JD.Terreno(); DZMAX['ELE'] = 1.0
    for i in alvo:
        s = SEG[i]
        if s['disc'] != 'ELE': continue
        cov = min(TT.z(*(s['a0'] + (s['b0'] - s['a0']) * t)[:2]) - ((s['a0'] + (s['b0'] - s['a0']) * t)[2] + s['de'] / 2) for t in np.linspace(0, 1, 5))
        if not np.isnan(cov) and cov < ELE_RECOB:
            DZMIN[i] = float(np.ceil((ELE_RECOB - cov) / 0.05 - 1e-6) * 0.05); mt.mover(i, DZMIN[i], IDX)
    print(f'cenário ELE recobrimento {ELE_RECOB:.2f} m: {len(DZMIN)} trechos descem de saída (máx {max(DZMIN.values(), default=0):.2f} m)')
FIXA = set()
if os.environ.get('JAN_INC_DANIEL'):
    # hidrantes nas profundidades do relatório PCI R00 (1,30 / 1,20 / 1,10 m a partir da cota 147,00), fixas
    import jan_teste_daniel as TD
    for i in alvo:
        if SEG[i]['trecho'] in TD.PROF: dz = round(TD.PROF[SEG[i]['trecho']] - 0.85, 2); DZMIN[i] = dz; mt.mover(i, dz, IDX); FIXA.add(i)
    print(f'hidrantes nas profundidades do Daniel: {len(FIXA)} trechos fixos')
conf0 = {i for i in alvo if mt.avaliar_seg(i, IDX)}
print(f'trechos móveis {len(alvo)} | com folga<20 cm hoje {len(conf0)} | anexos {len(anexo)} | {time.time()-t0:.0f}s')
# fase 1: descer
for passe in range(4):
    nm = 0
    for i in sorted(alvo, key=lambda i: (ORDEM.index(SEG[i]['disc']), SEG[i]['trecho'])):
        s = SEG[i]
        if (os.environ.get('JAN_ELE_FIXO') and s['disc'] == 'ELE') or i in FIXA or (i not in conf0 and s['dz'] == DZMIN.get(i, 0) and not any(SEG[j]['dz'] for j in viz[i])): continue
        atual = s['dz']; best = (custo(i)[0], atual)
        for dz in CAND:
            if dz > DZMAX[s['disc']] + 1e-9 or dz < DZMIN.get(i, 0) - 1e-9 or abs(dz - atual) < 1e-9: continue
            mt.mover(i, dz, IDX); c, _ = custo(i)
            if c < best[0] - 0.5: best = (c, dz)
        mt.mover(i, best[1], IDX)
        if abs(best[1] - atual) > 1e-9: nm += 1
    print(f'fase 1, passe {passe+1}: {nm} trechos mudaram | {time.time()-t0:.0f}s')
    if not nm: break


def colide_fixo(i):
    for k, j, g, pt in mt.avaliar_seg(i, IDX):
        if g >= mt.TOL or (k == 'M' and j in IGN): continue
        B = SEG[j] if k == 'S' else MESH[j]
        if B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes', 'Quadro estrutural'): continue
        if B['disc'] in ('DRE', 'ESG', 'EST') or k == 'M': return True
    return False


# fase 2: desvio em planta para quem ainda colide com caixa/poço/fundação ou rede por gravidade
SO_PROF = bool(os.environ.get('JAN_SO_PROF'))   # cenário "só profundidade": sem desvio em planta nem caixa em posição nova
# lista restrita: só estes trechos (marca) e caixas (grupo) podem mudar em planta; o resto fica só com profundidade
RESTR = set(x.strip() for x in os.environ.get('JAN_TRACADO', '').split(',') if x.strip())
RDISC = set(x.strip() for x in os.environ.get('JAN_TRACADO_DISC', '').split(',') if x.strip())   # disciplinas que podem mudar traçado
def pode_tracado(disc, nome): return not (RESTR or RDISC) or nome in RESTR or disc in RDISC
alvo2 = [] if SO_PROF else [i for i in alvo if colide_fixo(i) and pode_tracado(SEG[i]['disc'], SEG[i]['trecho'])]
nm = 0
for i in sorted(alvo2, key=lambda i: ORDEM.index(SEG[i]['disc'])):
    if i in FIXA: continue
    s = SEG[i]; u = (s['b0'] - s['a0'])[:2]; u = u / (np.linalg.norm(u) + 1e-12); n = np.array([-u[1], u[0]])
    dz0 = s['dz']; best = (custo(i)[0], dz0, (0.0, 0.0))
    for o in (0.3, 0.6, 0.9, 1.2, 1.5):
        for sg in (1, -1):
            dxy = (float(n[0] * o * sg), float(n[1] * o * sg))
            for dz in sorted({dz0, max(DZMIN.get(i, 0.0), dz0 - 0.1), dz0 + 0.1}):
                if dz > DZMAX[s['disc']] + 1e-9: continue
                mt.mover(i, dz, IDX, dxy); c, _ = custo(i)
                if c < best[0] - 0.5: best = (c, dz, dxy)
    mt.mover(i, best[1], IDX, best[2])
    if best[2] != (0.0, 0.0): nm += 1
print(f'fase 2: {len(alvo2)} trechos ainda colidindo; {nm} desvios em planta | {time.time()-t0:.0f}s')

# fase 3: caixas de ELE/SDAI/AF que colidem mudam de lugar (o grupo inteiro de peças)
MOV_CX = {'ELE', 'SDAI', 'AF'}
grupos = collections.defaultdict(list)
for j, M in enumerate(MESH):
    if M['disc'] in MOV_CX and 'glo' in M and j not in IGN: grupos[(M['fonte'], M['grupo'])].append(j)


def custo_grupo(js):
    c = 0.0
    for j in js:
        for k, i, g, pt in mt.avaliar_mesh(j, IDX):
            B = SEG[i] if k == 'S' else MESH[i]
            if (k == 'M' and (i in IGN or i in js)) or (B['disc'] == 'EST' and B['cat'] in ('Pisos', 'Paredes')): continue
            if k == 'S' and B['disc'] == MESH[j]['disc']: continue   # eletroduto da própria caixa
            c += 100 if g < mt.TOL else (5 if g < 0.10 else 1)
    d = MESH[js[0]].get('dxy', (0.0, 0.0)); return c + 3 * math.hypot(*d)


movidas = []
for key, js in ([] if SO_PROF else [kv for kv in grupos.items() if pode_tracado(MESH[kv[1][0]]['disc'], kv[0][1])]):
    c0 = custo_grupo(js)
    if c0 < 100: continue
    best = (c0, (0.0, 0.0))
    for o in (0.5, 1.0, 1.5, 2.0):
        for ang in range(0, 360, 45):
            d = (o * math.cos(math.radians(ang)), o * math.sin(math.radians(ang)))
            for j in js: mt.mover_mesh(j, d, IDX)
            c = custo_grupo(js)
            if c < best[0] - 0.5: best = (c, d)
    for j in js: mt.mover_mesh(j, best[1], IDX)
    if best[1] != (0.0, 0.0): movidas.append((key, best[1], c0, best[0]))
print(f'fase 3: {len(movidas)} caixas em posição nova | {time.time()-t0:.0f}s')

# anexos acompanham
for j, i in anexo.items():
    s = SEG[i]
    if s['dz'] or s.get('dxy', (0, 0)) != (0, 0):
        M = MESH[j]; off = np.array([*s.get('dxy', (0.0, 0.0)), -s['dz']])
        M['tri'] = M['tri'] + off; M['lo'] = M['lo'] + off; M['hi'] = M['hi'] + off

sol = {'seg': {s['id']: {'dz': s['dz'], 'dxy': list(s.get('dxy', (0.0, 0.0)))} for s in SEG if s['dz'] or s.get('dxy', (0, 0)) != (0, 0)},
       'mesh': {}}
for (f, g), d, c0, c1 in movidas:
    for j in grupos[(f, g)]: sol['mesh'][MESH[j]['id']] = {'dxy': list(d)}
for j, i in anexo.items():
    s = SEG[i]
    if s['dz'] or s.get('dxy', (0, 0)) != (0, 0): sol['mesh'][MESH[j]['id']] = {'dz': s['dz'], 'dxy': list(s.get('dxy', (0.0, 0.0)))}
json.dump(sol, open(os.path.join(SAIDA, 'solucao_R01' + SUF + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
T = JD.Terreno()
with open(os.path.join(SAIDA, 'solucao_R01' + SUF + '_trechos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['disc', 'trecho', 'id', 'DN', 'comprimento_m', 'desce_m', 'desvio_m', 'eixo_hoje_cota', 'eixo_novo_cota', 'recobr_hoje_m', 'recobr_novo_m'])
    for s in sorted(SEG, key=lambda s: (s['disc'], s['trecho'])):
        if not (s['dz'] or s.get('dxy', (0, 0)) != (0, 0)): continue
        m = (s['a0'] + s['b0']) / 2; zt = T.z(m[0], m[1]); L = np.linalg.norm(s['b0'] - s['a0'])
        w.writerow([s['disc'], s['trecho'], s['id'], s['dn'], '%.1f' % L, '%.2f' % s['dz'], '%.2f' % math.hypot(*s.get('dxy', (0, 0))),
                    '%.2f' % (147 + m[2]), '%.2f' % (147 + m[2] - s['dz']), '%.2f' % (zt - m[2] - s['de'] / 2), '%.2f' % (zt - m[2] + s['dz'] - s['de'] / 2)])
    for (fn, g), d, c0, c1 in movidas: w.writerow([fn, g, 'caixa', '', '', '', '%.1f' % math.hypot(*d), '', '', '', ''])
print('resumo por disciplina:')
for d in ORDEM:
    ss = [s for s in SEG if s['disc'] == d and s['dz'] > 0]
    sx = [s for s in SEG if s['disc'] == d and s.get('dxy', (0, 0)) != (0, 0)]
    if ss or sx:
        L = sum(np.linalg.norm(s['b0'] - s['a0']) for s in ss)
        print(f'  {d}: {len(ss)} trechos mais fundos ({L:.0f} m, descida média {np.mean([s["dz"] for s in ss]) if ss else 0:.2f} m, máx {max([s["dz"] for s in ss], default=0):.2f}) | {len(sx)} desvios')
for (f, g), d, c0, c1 in movidas: print(f'  caixa {f} {g}: mover {math.hypot(*d):.1f} m (custo {c0:.0f} -> {c1:.0f})')
