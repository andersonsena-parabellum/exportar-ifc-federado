# -*- coding: utf-8 -*-
"""Jandaíra — busca de posição livre para os últimos conflitos, sobre o estado final da rodada (PRECLASH_R02/JAN.json, cenário AD):
  poste:   a base (0,40 x 0,40 x 0,80 m) num raio de até 3 m, sem tocar tubo/caixa de DRE, ESG, água, PCI e estrutura (a elétrica do
           próprio poste se acomoda);
  caixa:   caixa de passagem num raio de até 3 m, com o fundo da rodada, sem tocar o que não é da disciplina dela;
  junção:  nó de tubos por gravidade (sem caixa) num raio de até 2,5 m: os tubos que chegam nele andam a ponta (cota igual).
Imprime o menor deslocamento livre (dE, dN) de cada alvo. Uso: python busca_posicao.py"""
import sys, json, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.stdout.reconfigure(encoding='utf-8')
from preclash import clash as cl, modelo as md
PRE = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02'
J = json.load(open(PRE + r'\JAN.json', encoding='utf-8')); O = (631578.10, 8721003.57); zr = J['zref']; CEN = 'AD'
E = []
for e in J['elementos']:
    if CEN not in e['cen']: continue
    P = np.array((e['sol'] or {}).get(CEN) or e['p'], float); P[:, 0] += O[0]; P[:, 1] += O[1]; P[:, 2] += zr
    E.append(md.elemento(e['id'], e['disc'], e['rede'], e['trecho'], 'gravidade' if e['disc'] in ('DRE', 'ESG') else 'pressao', e['de'], P,
                         de_ate=e['info'].get('de_ate', '')))
C = []
for c in J['caixas']:
    q = dict(c); mv = (c.get('mv') or {}).get(CEN)
    if mv: q['x'], q['y'] = mv
    C.append(dict(id=c['id'], disc=c['disc'], rede=c['disc'], forma=c['f'], E=q['x'] + O[0], N=q['y'] + O[1], meia=c['m'], zb=c['zb'] + zr, zt=c['zt'] + zr,
                  mx=c.get('mx'), my=c.get('my'), rot=c.get('rot', 0.0), info={'tipo': c.get('tipo')}))
R = {'folga': 0.05}
cxid = {c['id']: c for c in C}


def conflitos(cx, ignorar_disc=(), ignorar_ids=()):
    lo = np.array([cx['E'], cx['N']])
    els = [e for e in E if e['disc'] not in ignorar_disc and e['id'] not in ignorar_ids and np.all(e['pts'][:, :2].max(0) >= lo - 4) and np.all(e['pts'][:, :2].min(0) <= lo + 4)]
    out = [x for x in cl.detectar(els, [cx], R) if not x['ligacao'] and x['folga'] < 0.05]
    for o in C:
        if o['id'] == cx['id'] or o['disc'] in ignorar_disc or o['id'] in ignorar_ids or abs(o['E'] - cx['E']) > 4 or abs(o['N'] - cx['N']) > 4: continue
        if cl.folga_caixas(cx, o)[0] < 0.05: out.append(o['id'])
    return out


def busca(cx, rmax, **kw):
    for r in np.arange(0.1, rmax + 1e-6, 0.1):
        for a in np.radians(np.arange(0, 360, 15)):
            c2 = dict(cx, E=cx['E'] + r * math.cos(a), N=cx['N'] + r * math.sin(a))
            if not conflitos(c2, **kw): return (round(r * math.cos(a), 3), round(r * math.sin(a), 3))
    return None


# postes e caixas
for alvo, kw in (('EQ:5245088', dict(ignorar_disc=('ELE',))),):
    c = cxid[alvo]; print(alvo, 'agora:', conflitos(c, **kw)[:5]); print('  livre em', busca(c, 3.0, **kw))
for nome in ('ELE:CX-F10', 'ELE:CX-I33'):
    c = cxid[nome]
    print(nome, 'agora:', [x if isinstance(x, str) else x['a'] for x in conflitos(c, ignorar_disc=('ELE',))][:5])
    print('  livre em', busca(c, 3.0, ignorar_disc=('ELE',)))

# junções sem caixa
G = [e for e in E if e['tipo'] == 'gravidade']
EST = [c for c in C if c['disc'] == 'EST']


def juncao(p, rmax=2.5):
    ligs = [(e, k) for e in G for k in (0, -1) if np.hypot(*(e['pts'][k, :2] - p)) < 0.12]
    def ruins(v):
        out = []
        for e, k in ligs:
            P = e['pts'].copy(); P[k, :2] += v; e2 = dict(e, pts_sol=P)
            lo = P[:, :2].min(0); hi = P[:, :2].max(0)
            cx = [c for c in C if c['disc'] in ('EST',) and lo[0] - 3 < c['E'] < hi[0] + 3 and lo[1] - 3 < c['N'] < hi[1] + 3]
            out += [x for x in cl.detectar([e2], cx, R) if not x['ligacao'] and x['folga'] < 0.03]
        return out
    print('  junção', np.round(p, 2), [e['info'].get('de_ate') + ' ' + e['trecho'] for e, _ in ligs], 'agora', len(ruins(np.zeros(2))))
    for r in np.arange(0.1, rmax + 1e-6, 0.1):
        for a in np.radians(np.arange(0, 360, 15)):
            v = np.array([r * math.cos(a), r * math.sin(a)])
            if not ruins(v): return v.round(3).tolist()
    return None


for nome, p in (('BP4 DRE-133/126', (631582.58, 8721101.37)), ('DRE-061.1 fim', None), ('DRE-032 início', None)):
    if p is None:
        tr = nome.split()[0]; e = next(x for x in G if x['trecho'] == tr)
        p = e['pts'][-1, :2] if 'fim' in nome else e['pts'][0, :2]
    print(nome, '->', juncao(np.array(p, float)))
