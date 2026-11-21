# -*- coding: utf-8 -*-
"""Checagens de terreno das redes por gravidade (cotas de PROJETO), contra o IMP as built:
 - caixas/PV de ESG e DRN: tampa (topo do sólido) × terreno no centro -> exposta (> +0,05) ou soterrada (< −0,05)
 - tubos de ESG e DRN: topo do tubo acima do terreno (amostras a cada 0,5 m), fora de blocos
Primeiro gera os pontos que ainda não têm terreno amostrado (work/amostras_extra.csv) para ler no Revit."""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral")
import motor as mt
from terreno import zt
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral\work"; os.makedirs(W, exist_ok=True)
SEG, MESH = mt.carregar()
blocos = json.load(open(r"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\blocos.json", encoding='cp1252'))
def dentro_bloco(x, y):
    for b in blocos:
        c = b['coords']; n = len(c); ins = False
        for i in range(n):
            x1, y1 = c[i]; x2, y2 = c[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: ins = not ins
        if ins: return b['bloco']
    return None
modo = sys.argv[1] if len(sys.argv) > 1 else 'gerar'
pts = []
for M in MESH:
    if M['disc'] in ('ESG', 'DRN') and M['cat'] in ('Modelos genéricos', 'Acessórios do tubo'):
        c = (M['lo'] + M['hi']) / 2; pts.append(('CX', M['disc'], M['trecho'] or M['id'], c[0], c[1], M['hi'][2], M['lo'][2]))
for s in SEG:
    if s['disc'] not in ('ESG', 'DRN'): continue
    L = np.linalg.norm((s['b'] - s['a'])[:2])
    if L < 0.05: continue
    for f in np.linspace(0, 1, max(2, int(L / 0.5) + 1)):
        q = s['a'] + (s['b'] - s['a']) * f
        pts.append(('TB', s['disc'], s['trecho'], q[0], q[1], q[2] + s['de'] / 2, q[2]))
if modo == 'gerar':
    with open(W + r"\amostras_extra.csv", 'w', encoding='utf-8') as f:
        for i, p in enumerate(pts): f.write(f"{i};{p[3]:.3f};{p[4]:.3f}\n")
    print('pontos para amostrar no Revit:', len(pts)); sys.exit()
# modo avaliar: work/amostras_extra_z.csv (id;x;y;z) já lido do Revit
Z = {}
for l in open(W + r"\amostras_extra_z.csv", encoding='utf-8'):
    q = l.strip().split(';')
    if len(q) >= 4 and q[3] != 'nan': Z[int(q[0])] = float(q[3])
cx = []; tb = collections.defaultdict(list)
for i, p in enumerate(pts):
    if i not in Z: continue
    t = Z[i]
    if p[0] == 'CX':
        d = p[5] - t
        if abs(d) > 0.05: cx.append((p[1], p[2], round(p[3], 2), round(p[4], 2), round(p[5], 3), round(t, 3), round(d, 3), round(t - p[6], 2), dentro_bloco(p[3], p[4]) or ''))
    else:
        if p[5] > t + 0.01 and not dentro_bloco(p[3], p[4]): tb[(p[1], p[2])].append((p[3], p[4], p[5] - t))
with open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\terreno_caixas.csv", 'w', encoding='utf-8-sig') as f:
    f.write('disciplina;caixa;x;y;tampa_projeto;terreno_IMP;diferenca_m;profundidade_ate_fundo;bloco\n')
    for r in sorted(cx, key=lambda r: -abs(r[6])): f.write(';'.join(map(str, r)) + '\n')
with open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\terreno_tubos.csv", 'w', encoding='utf-8-sig') as f:
    f.write('disciplina;trecho;x;y;topo_acima_do_terreno_max_m;comprimento_aprox_m\n')
    for (d, t), v in sorted(tb.items(), key=lambda kv: -max(x[2] for x in kv[1])):
        k = max(v, key=lambda x: x[2]); f.write(f"{d};{t};{k[0]:.2f};{k[1]:.2f};{k[2]:.3f};{0.5*len(v):.1f}\n")
e = [r for r in cx if r[6] > 0.05]; s_ = [r for r in cx if r[6] < -0.05]
print(f'caixas expostas (tampa > terreno+5 cm): {len(e)} | soterradas: {len(s_)} | tubos com topo acima do terreno: {len(tb)} trechos')
for d in ('ESG', 'DRN'):
    print(d, 'expostas', sum(1 for r in e if r[0] == d), 'máx', max([r[6] for r in e if r[0] == d] or [0]), '| soterradas', sum(1 for r in s_ if r[0] == d), 'mín', min([r[6] for r in s_ if r[0] == d] or [0]),
          '| tubos acima', sum(1 for k in tb if k[0] == d))
