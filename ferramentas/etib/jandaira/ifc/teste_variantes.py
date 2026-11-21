# teste rápido de variantes do estudo de cota (sem IFC/HTML): cenário A + resolver, conta os críticos por par de disciplinas.
# uso: python teste_variantes.py '{"AR": 0.90}'   (JAN_COB_REDE)
import os, sys, copy, collections, time
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
if len(sys.argv) > 1: os.environ['JAN_COB_REDE'] = sys.argv[1]
import importlib
from preclash import clash as cl, solver as sv, estudo as etd, desvio as dsv
t0 = time.time()
S = importlib.import_module('escolas.jandaira')
D = S.carregar(); ter = D['terreno']; R = S.REGRAS
E = [copy.deepcopy(e) for e in D['elementos']]; C = copy.deepcopy(D['caixas'])
log = (lambda *a: None) if os.environ.get('MUDO') else print
est = etd.estudar(E, C, R, ter, log=log)
final, pend, alertas = sv.resolver(E, C, R, ter)
dv = dsv.aplicar(E, C, pend, R, ter, log=lambda *a: None)
final, pend, alertas = sv.resolver(E, C, R, ter)
ids = {e['id']: e for e in E}; cx = {c['id']: c for c in C}
d = lambda k: (ids[k]['disc'] if k in ids else cx[k]['disc'])
crit = [c for c in final if c['gravidade'] == 'CRÍTICA' and not c['ligacao']]
print('críticos', len(crit), dict(collections.Counter(tuple(sorted((d(c['a']), d(c['b'])))) for c in crit)), f'{time.time() - t0:.0f} s')
for g in est:
    if g['disc'] in ('AF', 'HID'): print('  ', g['grupo'], g['cob'], g['colisoes'])
