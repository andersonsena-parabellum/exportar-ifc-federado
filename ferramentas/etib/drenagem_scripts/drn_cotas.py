import sys, math, pickle, collections, re, csv
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
W = 'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
E, segs, mlines, arrows, P = pickle.load(open(CACHE, 'rb'))
nodes, edges, boxes, segs3 = pickle.load(open(W + 'topo.pkl', 'rb'))
T = [e for e in E if e[0] == 'MTEXT' and e[1] == 'TQ-Textos conduto']
def val(s):
    m = re.search(r'([\d.]+)', s.split(':')[-1]); return float(m.group(1)) if m else None
CT = [(t[3], val(t[5])) for t in T if t[5].startswith('CT')]
CF = [(t[3], val(t[5])) for t in T if t[5].startswith('CF')]
DP = [(t[3], float(re.sub(r'[()]', '', t[5]))) for t in T if re.fullmatch(r'\(\s*[\d.]+\)', t[5])]
CE = [(t[3], val(t[5])) for t in T if t[5].startswith('CE')]
CS = [(t[3], val(t[5])) for t in T if t[5].startswith('CS')]
print('CT', len(CT), 'CF', len(CF), 'prof', len(DP), 'CE', len(CE), 'CS', len(CS))
trip = []
usedF = set(); usedD = set()
for p, ct in CT:
    bf = min(((math.dist(p, q[0]), k) for k, q in enumerate(CF) if k not in usedF), default=None)
    if not bf or bf[0] > 0.6: continue
    usedF.add(bf[1]); cf = CF[bf[1]]
    bd = min(((math.dist(p, q[0]), k) for k, q in enumerate(DP) if k not in usedD), default=None)
    prof = None
    if bd and bd[0] < 4.0:
        usedD.add(bd[1]); prof = DP[bd[1]][1]
    trip.append({'pos': p, 'ct': ct, 'cf': cf[1], 'prof': prof})
print('triplas', len(trip), 'com prof', sum(1 for t in trip if t['prof'] is not None))
bad = [t for t in trip if t['prof'] is not None and abs((t['ct'] - t['cf']) - t['prof']) > 0.011]
print('triplas inconsistentes (CT-CF != prof):', len(bad))
# triplas -> caixas (guloso por distancia)
bx = [(i, b) for i, b in enumerate(boxes)]
pairs = sorted(((math.dist(t['pos'], b['c']), ti, i) for ti, t in enumerate(trip) for i, b in bx))
tu = set(); bu = set(); assign = {}
for d, ti, i in pairs:
    if ti in tu or i in bu or d > 9: continue
    tu.add(ti); bu.add(i); assign[i] = (ti, d)
print('caixas com cota', len(assign), 'de', len(boxes), ' dist max', round(max(d for ti, d in assign.values()), 1) if assign else None)
far = [(i, round(d, 1)) for i, (ti, d) in assign.items() if d > 5]; print('triplas longe (>5 m):', far[:20])
print('triplas sem caixa', len(trip) - len(tu))
for ti, t in enumerate(trip):
    if ti not in tu: print('  sem caixa:', (round(t['pos'][0]-561000, 1), round(t['pos'][1]-8657000, 1)), t['ct'], t['cf'], t['prof'])
print('caixas sem cota:', [(i, (round(b['c'][0]-561000,1), round(b['c'][1]-8657000,1))) for i, b in enumerate(boxes) if i not in assign])
pickle.dump((trip, assign, CE, CS), open(W + 'cotas.pkl', 'wb'))
