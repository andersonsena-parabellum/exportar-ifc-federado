# -*- coding: utf-8 -*-
"""Jandaíra — mudanças do R01 no formato do executivo/rever.py (padrão de executivo final), em coordenadas INTERNAS dos modelos JAN
(o adaptador escolas/jandaira.py dá TRANSF_DWG = DWG -> interno, então o rever.py desenha direto na prancha).
Compara compat_R01/geo (modelos do Daniel) com geo_exec (modelos revisados):
  contorno        elemento com traçado em planta diferente (desvios da elétrica, linhas da água fria deslocadas e tubos que esticaram)
  caixa deslocada caixas da elétrica e do alarme em posição nova
  mergulho        trecho mais fundo que o original (mergulho local da elétrica e do reúso; hidrantes e alarme inteiros mais fundos)
Grava ETIB-JANDAIRA/RELATORIOS/EXECUTIVO_R02/JAN_mudancas.json ({'mudancas': [...]})."""
import sys, os, re, json, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"; OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02"
os.makedirs(OUT, exist_ok=True)
SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None); JD.agrupar_caixas(SH, MH)
SX, MX = JD.carregar(g=os.path.join(C, 'geo_exec'), est=None); JD.agrupar_caixas(SX, MX)
T = JD.Terreno(g=os.path.join(C, 'geo'))
H = {s['id']: s for s in SH}
FOLHA = {'EL-001': 'EL-001', 'EL-002': 'EL-002', 'AF': 'AF-001', 'INC': 'IN-001', 'SDAI': 'IN-001'}
mud = []


def folha_ele(s):
    d = s.get('desc') or ''
    if 'Fonte: EL-002' in d: return 'EL-002'
    if 'Fonte: EL-001' in d: return 'EL-001'
    return None


def prof_topo(pts, de):
    v = [T.z(p[0], p[1]) - (p[2] + de / 2) for p in pts]; v = [x for x in v if not np.isnan(x)]
    return float(max(v)) if v else None


def cadeia(segs):
    """ordena pedaços contíguos numa polilinha (xy)."""
    segs = list(segs)
    if not segs: return []
    P = [segs[0]['a'][:2], segs[0]['b'][:2]]; usados = {0}
    while len(usados) < len(segs):
        ok = False
        for i, s in enumerate(segs):
            if i in usados: continue
            for a, b in ((s['a'][:2], s['b'][:2]), (s['b'][:2], s['a'][:2])):
                if np.linalg.norm(a - P[-1]) < 0.02: P.append(b); usados.add(i); ok = True; break
                if np.linalg.norm(b - P[0]) < 0.02: P.insert(0, a); usados.add(i); ok = True; break
            if ok: break
        if not ok: break
    return [p.tolist() for p in P]


# ------------------------------------------------ ELÉTRICA: pedaços por elemento de origem (marca sem o sufixo .mN/.dN)
raiz = lambda t: re.sub(r'\.(m|d)\d+$', '', t)
gx = collections.defaultdict(list)
for s in SX:
    if s['disc'] == 'ELE': gx[raiz(s['trecho'])].append(s)
gh = collections.defaultdict(list)
for s in SH:
    if s['disc'] == 'ELE': gh[s['trecho']].append(s)
DESV = {'ELE-I-01': ['ELE-I-01'], 'ELE-I-13': ['ELE-I-13'], 'ELE-I-28.1': ['ELE-I-28.1'], 'ELE-I-31.8': ['ELE-I-31.8', 'ELE-I-31.9', 'ELE-I-31.10', 'ELE-I-31.11']}
em_desvio = {m for v in DESV.values() for m in v}
for k, mks in DESV.items():
    ant = cadeia([s for m in mks for s in gh.get(m, [])]); nov = cadeia([s for m in mks for s in gx.get(m, [])])
    f = folha_ele(gh[mks[0]][0])
    if ant and nov: mud.append(dict(tipo='contorno', disc='ELE', folha=f, trecho=k, elemento=k, antigo=ant, novo=nov, E=float(np.mean([p[0] for p in nov])), N=float(np.mean([p[1] for p in nov]))))
for mk, ss in gx.items():
    if mk in em_desvio or mk not in gh: continue
    o = gh[mk][0]; z0 = min(min(s['a0'][2], s['b0'][2]) for s in gh[mk]); f = folha_ele(o)
    fundos = [s for s in ss if min(s['a'][2], s['b'][2]) < z0 - 0.05]
    if not fundos or not f: continue
    pts = [p for s in fundos for p in (s['a'], s['b'])]; P = cadeia(fundos) or [s['a'][:2].tolist() for s in fundos]
    pt = prof_topo(pts, o['de']); L = sum(np.linalg.norm(s['b'][:2] - s['a'][:2]) for s in fundos)
    c = np.mean(np.array(P), 0)
    mud.append(dict(tipo='mergulho', disc='ELE', folha=f, trecho=mk, elemento=mk, planta=P, prof_topo=round(pt, 2), extensao=float(L), E=float(c[0]), N=float(c[1]),
                    eixo=float(147 + min(min(s['a'][2], s['b'][2]) for s in fundos))))
# caixas da elétrica e do alarme em posição nova
def centro(M, g):
    E = [m for m in M if m.get('grupo') == g]
    return ((E[0]['glo'] + E[0]['ghi']) / 2) if E else None
for g in sorted({m['grupo'] for m in MX if m['disc'] in ('ELE', 'SDAI') and str(m.get('grupo', '')).startswith('CX-')}):
    a, b = centro(MH, g), centro(MX, g)
    if a is None or b is None or np.linalg.norm(b[:2] - a[:2]) < 0.05: continue
    disc = 'SDAI' if 'SDAI' in g else 'ELE'
    f = 'IN-001' if disc == 'SDAI' else ('EL-002' if g.startswith('CX-I') else 'EL-001')
    mud.append(dict(tipo='caixa deslocada', disc=disc, folha=f, trecho=g, elemento=g, de=a[:2].tolist(), E=float(b[0]), N=float(b[1]), lado=0.8 if disc == 'ELE' else 0.5, lado_y=0.8 if disc == 'ELE' else 0.5, rot=0.0))

# ------------------------------------------------ ÁGUA FRIA: traçado (tubos que mudaram em planta) e mergulhos (.gN)
for s in SX:
    if s['disc'] != 'AF' or re.search(r'\.g\d+$', s['trecho']): continue
    o = H.get(s['id'])
    if o is None: continue
    if max(np.linalg.norm(s['a'][:2] - o['a0'][:2]), np.linalg.norm(s['b'][:2] - o['b0'][:2])) < 0.03: continue
    # tubo com mergulho: o traçado novo é a cadeia dele + pedaços .g (mesma planta)
    pec = [s] + [x for x in SX if x['disc'] == 'AF' and re.sub(r'\.g\d+$', '', x['trecho']) == s['trecho'] and x is not s]
    nov = cadeia(pec) if len(pec) > 1 else [s['a'][:2].tolist(), s['b'][:2].tolist()]
    mud.append(dict(tipo='contorno', disc='AF', folha='AF-001', trecho=s['trecho'], elemento=s['trecho'], antigo=[o['a0'][:2].tolist(), o['b0'][:2].tolist()], novo=nov,
                    E=float((s['a'][0] + s['b'][0]) / 2), N=float((s['a'][1] + s['b'][1]) / 2)))
# trechos deslocados em sequência viram um contorno só (na prancha um tubo cobre às vezes dois trechos do modelo, ex.: AL-21 + AL-22);
# só se o nó liga exatamente dois trechos deslocados (tê fica separado: a ponta do ramal é tratada à parte)
def _deslocado(m):
    A, B = np.array(m['antigo']), np.array(m['novo'])
    d = lambda p: min(np.abs(np.cross(A[1] - A[0], p - A[0])) / max(1e-9, np.linalg.norm(A[1] - A[0])), 9e9)
    return np.mean([d(p) for p in (B[0], B[-1], (B[0] + B[-1]) / 2)]) > 0.3
cont = [m for m in mud if m['disc'] == 'AF' and m['tipo'] == 'contorno' and _deslocado(m)]
pt = lambda m, k: (np.array(m['antigo'][k]), np.array(m['novo'][k]))
liga = collections.defaultdict(list)                    # (i, ponta) -> [(j, ponta)]
for i, m in enumerate(cont):
    for j, n in enumerate(cont):
        if j <= i: continue
        for ki in (0, -1):
            for kj in (0, -1):
                (ai, bi), (aj, bj) = pt(m, ki), pt(n, kj)
                if np.linalg.norm(ai - aj) < 0.1 and np.linalg.norm(bi - bj) < 0.1: liga[(i, ki)].append((j, kj)); liga[(j, kj)].append((i, ki))
usado, cadeias = set(), []
for i in range(len(cont)):
    if i in usado: continue
    # anda até uma ponta livre e monta a cadeia a partir dela
    cur, k = i, 0
    for _ in range(len(cont)):
        nx = liga.get((cur, k), [])
        if len(nx) != 1 or nx[0][0] == i: break
        cur, k = nx[0][0], (-1 if nx[0][1] == 0 else 0)
    cad, kin = [], k
    while cur is not None and cur not in usado:
        usado.add(cur); cad.append((cur, kin))
        out = -1 if kin == 0 else 0; nx = liga.get((cur, out), [])
        if len(nx) == 1 and nx[0][0] not in usado: cur, kin = nx[0]
        else: cur = None
    cadeias.append(cad)
for cad in cadeias:
    if len(cad) < 2: continue
    A, B, nomes = [], [], []
    for idx, kin in cad:
        m = cont[idx]; a, b = list(m['antigo']), list(m['novo'])
        if kin == -1: a, b = a[::-1], b[::-1]
        A += a if not A else a[1:]; B += b if not B else b[1:]; nomes.append(m['elemento'])
    for idx, _ in cad: mud.remove(cont[idx])
    mud.append(dict(tipo='contorno', disc='AF', folha='AF-001', trecho=' + '.join(nomes), elemento=' + '.join(nomes), antigo=A, novo=B,
                    E=float(np.mean([p[0] for p in B])), N=float(np.mean([p[1] for p in B]))))
    print('contorno em sequência:', ' + '.join(nomes))
ga = collections.defaultdict(list)
for s in SX:
    if s['disc'] == 'AF' and re.search(r'\.g\d+$', s['trecho']): ga[re.sub(r'\.g\d+$', '', s['trecho'])].append(s)
for mk, ss in ga.items():
    z0 = min(min(s['a0'][2], s['b0'][2]) for s in SH if s['trecho'] == mk)
    fundos = [s for s in ss if min(s['a'][2], s['b'][2]) < z0 - 0.05]
    # um mergulho por grupo contíguo
    grupos = []
    for s in sorted(fundos, key=lambda s: (s['a'][0], s['a'][1])):
        for g in grupos:
            if any(np.linalg.norm(s['a'][:2] - x['b'][:2]) < 0.05 or np.linalg.norm(s['b'][:2] - x['a'][:2]) < 0.05 for x in g): g.append(s); break
        else: grupos.append([s])
    for g in grupos:
        pts = [p for s in g for p in (s['a'], s['b'])]; P = cadeia(g); c = np.mean(np.array(P), 0)
        mud.append(dict(tipo='mergulho', disc='AF', folha='AF-001', trecho=mk, elemento=mk, planta=P, prof_topo=round(prof_topo(pts, g[0]['de']), 2),
                        extensao=float(sum(np.linalg.norm(s['b'][:2] - s['a'][:2]) for s in g)), E=float(c[0]), N=float(c[1]), eixo=float(147 + min(p[2] for p in pts))))

# ------------------------------------------------ INCÊNDIO: hidrantes e alarme mais fundos (trecho inteiro)
gi = collections.defaultdict(list)
for s in SX:
    if s['disc'] in ('INC', 'SDAI') and np.linalg.norm(s['b'][:2] - s['a'][:2]) > 0.3 and abs(s['b'][2] - s['a'][2]) < 0.3:
        gi[re.sub(r'\.d\d+$', '', s['trecho'])].append(s)
for mk, ss in gi.items():
    hs = [s for s in SH if s['trecho'] == mk]
    if not hs: continue
    z0 = min(min(s['a0'][2], s['b0'][2]) for s in hs); z1 = min(min(s['a'][2], s['b'][2]) for s in ss)
    if z1 > z0 - 0.05: continue
    pts = [p for s in ss for p in (s['a'], s['b'])]; P = cadeia(ss) or [ss[0]['a'][:2].tolist(), ss[0]['b'][:2].tolist()]; c = np.mean(np.array(P), 0)
    mud.append(dict(tipo='mergulho', disc=ss[0]['disc'], folha='IN-001', trecho=mk, elemento=mk, planta=P, prof_topo=round(prof_topo(pts, ss[0]['de']), 2),
                    extensao=float(sum(np.linalg.norm(s['b'][:2] - s['a'][:2]) for s in ss)), E=float(c[0]), N=float(c[1]), eixo=float(147 + z1)))
for m in mud:
    if m['tipo'] == 'mergulho': m['nota'] = 'PROF. %s m' % ('%.2f' % m['prof_topo']).replace('.', ',')
json.dump({'mudancas': mud, 'coordenadas': 'internas dos modelos JAN (m)'}, open(os.path.join(OUT, 'JAN_mudancas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
cont = collections.Counter((m['folha'], m['tipo']) for m in mud)
for k in sorted(cont): print(k, cont[k])
print('maior profundidade nas notas: %.2f m' % max(m['prof_topo'] for m in mud if m['tipo'] == 'mergulho'))
