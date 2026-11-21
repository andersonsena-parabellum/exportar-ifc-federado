# -*- coding: utf-8 -*-
"""Drenagem do JAN-DRE na região do campo: tubos (nós, DN, cotas, material) e caixas, para separar campo 45x25 × rede externa."""
import sys, re, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
S, M = JD.carregar(g=r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo_exec", est=None, discs=('DRE',)); JD.agrupar_caixas(S, M)
C = np.array([90.952, 114.112]); t = np.radians(5.3818); Rl = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
loc = lambda p: Rl @ (np.asarray(p[:2]) - C)   # coordenadas do campo (x ao longo, y transversal)
for s in sorted(S, key=lambda s: s['trecho']):
    a, b = loc(s['a']), loc(s['b'])
    if max(abs(a[0]), abs(b[0])) > 42 or max(abs(a[1]), abs(b[1])) > 26: continue
    m = re.search(r'\|\s*(\S+)\s*->\s*(\S+)', s['desc'] or ''); mat = (s['desc'] or '').split('|')[0].strip()
    print('%-9s %-14s %-12s L%5.1f  a(%6.1f,%6.1f) z%6.2f  b(%6.1f,%6.1f) z%6.2f  id %s' % (s['trecho'], mat[:14], (m.group(1) + '>' + m.group(2)) if m else '', np.linalg.norm(s['b'][:2] - s['a'][:2]), *a, s['a'][2], *b, s['b'][2], s['id']))
vis = set()
for E in M:
    if E.get('glo') is None or E['grupo'] in vis: continue
    c = loc((E['glo'] + E['ghi']) / 2)
    if abs(c[0]) > 42 or abs(c[1]) > 26: continue
    vis.add(E['grupo']); print('CAIXA %-12s %-30s (%6.1f,%6.1f) topo %.2f fundo %.2f  dim %s' % (E['grupo'], E['nome'][:30], *c, E['ghi'][2], E['glo'][2], (E['ghi'] - E['glo'])[:2].round(2)))
