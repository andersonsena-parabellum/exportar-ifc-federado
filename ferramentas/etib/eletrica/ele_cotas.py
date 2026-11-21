"""Cotas dos eletrodutos enterrados (premissa NBR 5410 decidida pelo usuário em 15/10/2026):
topo do eletroduto = terreno as built (IMP) - recobrimento; EL: 0,70 m (1,00 m na área de veículos V1); CF: 0,60 m.
Cada pedaço (caixa a caixa) é independente: Douglas-Peucker 0,20 m / trecho mínimo 2 m + iteração até nenhum ponto raso.
Caixa: topo = terreno; fundo = eletroduto mais fundo que chega nela - DE/2 - 0,10 m.
Saída: work/cotas_<TAG>.json e RELATORIOS/ELE_fase2_trechos_<data>.csv"""
import json, csv, math, collections
import numpy as np
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
V1 = [(-22, 33), (17, 33), (18, 36.6), (86.5, 46.3), (87.2, 47.5), (92, 70), (-22, 70)]
EPS, MINL = 0.20, 2.0
def inpoly(p, poly):
    x, y = p; c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def cover(tag, p): return (1.00 if inpoly(p, V1) else 0.70) if tag.startswith('EL') else 0.60

S = collections.defaultdict(list); ZB = {}
for r in csv.DictReader(open(W + 'amostras_z.csv'), delimiter=';'):
    if r['peca'].startswith('CX'): ZB[(r['tag'], int(r['peca'][2:]))] = float(r['zt'])
    else: S[(r['tag'], int(r['peca']))].append((float(r['s']), float(r['x']), float(r['y']), float(r['zt'])))

def dp(s, z, i0, i1, out):
    if i1 <= i0 + 1: return
    line = z[i0] + (z[i1] - z[i0]) * (s[i0 + 1:i1] - s[i0]) / (s[i1] - s[i0])
    dev = np.abs(z[i0 + 1:i1] - line); k = int(np.argmax(dev)) + i0 + 1
    if dev.max() > EPS and s[k] - s[i0] >= MINL and s[i1] - s[k] >= MINL:
        dp(s, z, i0, k, out); out.append(k); dp(s, z, k, i1, out)

linhas = []
for tag in ['EL1', 'EL2', 'CF1', 'CF2']:
    N = json.load(open(W + f'pecas_{tag}.json'))
    for i, p in enumerate(N['pieces']):
        sm = sorted(S[(tag, i)]); de = p['de_mm'] / 1000
        s = np.array([q[0] for q in sm]); zr = np.array([q[3] - cover(tag, (q[1], q[2])) - de / 2 for q in sm])
        ks = []; dp(s, zr, 0, len(s) - 1, ks); idx = [0] + sorted(ks) + [len(s) - 1]
        Z = {k: zr[k] for k in idx}
        for it in range(200):
            ch = False
            for a, b in zip(idx, idx[1:]):
                za, zb = Z[a], Z[b]; viol, tv = 0, 0
                for k in range(a, b + 1):
                    u = (s[k] - s[a]) / (s[b] - s[a]) if s[b] > s[a] else 0
                    v = za + (zb - za) * u - zr[k]
                    if v > viol: viol, tv = v, u
                if viol > 1e-4:
                    if tv < 0.5: Z[a] -= viol / max(1 - tv, 1e-6)
                    else: Z[b] -= viol / max(tv, 1e-6)
                    ch = True
            if not ch: break
        legs = []
        for a, b in zip(idx, idx[1:]):
            cov = [sm[k][3] - (Z[a] + (Z[b] - Z[a]) * ((s[k] - s[a]) / (s[b] - s[a]) if s[b] > s[a] else 0) + de / 2) for k in range(a, b + 1)]
            legs.append(dict(a=[sm[a][1], sm[a][2], float(Z[a])], b=[sm[b][1], sm[b][2], float(Z[b])], cov_min=float(min(cov)), cov_max=float(max(cov))))
        p['legs'] = legs; p['cov_req'] = cover(tag, (sm[0][1], sm[0][2])); p['cov_min'] = min(l['cov_min'] for l in legs); p['cov_max'] = max(l['cov_max'] for l in legs)
        p['z_ini'], p['z_fim'] = legs[0]['a'][2], legs[-1]['b'][2]
    # caixas
    for j, b in enumerate(N['boxes']):
        zt = ZB[(N['tag'], j)]; fundos = []
        for p in N['pieces']:
            de = p['de_mm'] / 1000
            if p['cx_ini'] == j: fundos.append(p['z_ini'] - de / 2)
            if p['cx_fim'] == j: fundos.append(p['z_fim'] - de / 2)
        b['ct'] = zt; b['cf'] = (min(fundos) - 0.10) if fundos else zt - cover(tag, b['c']) - 0.15; b['prof'] = b['ct'] - b['cf']
        b['n_eletrodutos'] = len(fundos)
    json.dump(N, open(W + f'cotas_{tag}.json', 'w'), indent=0, ensure_ascii=False)
    for i, p in enumerate(N['pieces']):
        linhas.append([N['rede'], f'{tag}-{i:03d}', p['pol'] + '"', p['de_mm'], f"{p['L']:.1f}", len(p['legs']), p['rot']['texto'], p['rot']['contexto'][:80], p['rot']['origem'],
                       f"{p['cov_req']:.2f}", f"{p['cov_min']:.2f}", f"{p['cov_max']:.2f}",
                       'caixa' if p['cx_ini'] is not None else 'ponta', 'caixa' if p['cx_fim'] is not None else 'ponta'])
    L = sum(p['L'] for p in N['pieces']); nl = sum(len(p['legs']) for p in N['pieces'])
    print(f"{tag}: {len(N['pieces'])} pedaços -> {nl} trechos retos, {L:.0f} m | recobrimento mín {min(p['cov_min'] for p in N['pieces']):.2f} máx {max(p['cov_max'] for p in N['pieces']):.2f} | caixas: prof. {min(b['prof'] for b in N['boxes']):.2f}–{max(b['prof'] for b in N['boxes']):.2f} m")
with open('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase2_trechos_2026-10-15.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['rede', 'trecho', 'Ø', 'DE_mm', 'comp_m', 'n_quebras+1', 'rótulo', 'circuito/contexto', 'origem do Ø', 'recobr_exigido', 'recobr_min', 'recobr_max', 'início', 'fim'])
    w.writerows(linhas)
print('csv ok')
