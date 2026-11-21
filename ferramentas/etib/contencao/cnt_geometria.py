# -*- coding: utf-8 -*-
"""Geometria da contenção para o Revit (DirectShape).
Premissa aprovada (16/10/2026, "como o desenho"): aterro ao sul (fora do lote); a face frontal (vertical) é a linha
do DWG; topo da sapata (A–C) / base do fuste (D) = terreno do IMP 0,5 m à frente da face (lado do lote), em trechos de
2 m com a base no MENOR terreno do trecho (fundação escalonada); topo do muro = base + H.
Perfil (cortes A–D do DWG): fuste com 0,90 m na base e degraus de 0,125 m a cada 0,50 m do lado do aterro;
sapata 0,50 m de altura, da ponta (−0,75/−0,55/−0,35) até o talão (+1,15). Barbacãs Ø100 em fileiras a 0,55/1,05/…,
espaçamento da seção, fileiras alternadas defasadas de meio espaçamento.
Saída: work/cnt_pecas.tsv  (uma linha por peça) + work/cnt_pecas_resumo.csv"""
import json, math, collections, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
F = json.load(open(W + r"\cnt_face.json", encoding='utf-8'))
ESP = {'A': 1.24, 'B': 1.13, 'C': 1.04, 'D': 0.687}
PASSO = 2.0
# terreno à frente da face (offset −0,5) a cada 1 m
TF = collections.defaultdict(list)
for l in open(W + r"\amostras_cnt_z.csv", encoding='utf-8'):
    r = l.strip().split(';')
    if len(r) >= 7 and float(r[3]) == -0.5 and r[6] != 'nan': TF[r[1]].append((float(r[2]), float(r[6])))
for k in TF: TF[k].sort()


def perfil_fuste(H):
    nb = int(round(H / 0.5)); pts = [(0.0, 0.0)]
    for b in range(nb):
        w = 0.90 - 0.125 * b
        pts += [(w, 0.5 * b), (w, 0.5 * (b + 1))]
    pts.append((0.0, H))
    return pts


linhas = []; resumo = []
for s in F['segmentos']:
    sec = s['secao']; H = s['H']; L = s['L']; est0 = s['est0']
    p0 = s['p0']; u = s['u']; n = s['n_sul']
    geo = f"{p0[0]:.4f};{p0[1]:.4f};{u[0]:.6f};{u[1]:.6f};{n[0]:.6f};{n[1]:.6f}"
    zt = [(e - est0, z) for e, z in TF[sec]]
    npc = max(1, int(math.ceil(L / PASSO - 1e-6)))
    bases = []
    for i in range(npc):
        d0 = i * L / npc; d1 = (i + 1) * L / npc
        zz = [z for d, z in zt if d0 - 0.5 <= d <= d1 + 0.5]
        z0 = math.floor(min(zz) * 100) / 100
        bases.append((d0, d1, z0))
        pid = f"CNT-{sec}-E{est0 + d0:05.1f}"
        prof = ';'.join(f"{a:.4f},{b:.4f}" for a, b in perfil_fuste(H))
        linhas.append(['MURO', sec, pid, f"{d0:.4f}", f"{d1:.4f}", f"{z0:.3f}", f"{H:.2f}", prof, geo, f"{min(zz):.3f}", f"{max(zz):.3f}"])
        if s['sap_L'] > 0:
            a0 = -s['ponta']; a1 = 0.90 + s['talao']
            prof = f"{a0:.4f},{-s['sap_H']:.4f};{a1:.4f},{-s['sap_H']:.4f};{a1:.4f},0.0000;{a0:.4f},0.0000"
            linhas.append(['SAPATA', sec, pid.replace('CNT-', 'CNT-SAP-'), f"{d0:.4f}", f"{d1:.4f}", f"{z0:.3f}", f"{s['sap_H']:.2f}", prof, geo, f"{min(zz):.3f}", f"{max(zz):.3f}"])
    # barbacãs
    nb = 0; nrow = int(round(H / 0.5)) - 1
    for k in range(1, nrow + 1):
        off = 0.0 if k % 2 == 1 else ESP[sec] / 2
        d = ESP[sec] / 2 + off
        while d <= L - 0.15:
            z0 = next(b[2] for b in bases if b[0] - 1e-9 <= d <= b[1] + 1e-9)
            zc = z0 + 0.5 * k + 0.05; w = 0.90 - 0.125 * k
            linhas.append(['BARB', sec, f"CNT-BARB-{sec}-{k}-{nb:03d}", f"{d:.4f}", f"{d:.4f}", f"{zc:.3f}", "0.10", f"-0.0200,{w + 0.02:.4f}", geo, '', ''])
            nb += 1; d += ESP[sec]
    resumo.append((sec, round(L, 2), H, npc, nb, min(b[2] for b in bases), max(b[2] for b in bases)))
with open(W + r"\cnt_pecas.tsv", 'w', encoding='utf-8') as f:
    for r in linhas: f.write('\t'.join(r) + '\n')
with open(W + r"\cnt_pecas_resumo.csv", 'w', encoding='utf-8-sig') as f:
    f.write('seção;comprimento m;H m;trechos de muro;barbacãs;base mín;base máx\n')
    for r in resumo: f.write(';'.join(map(str, r)) + '\n')
area = {'A': 2.575, 'B': 1.935, 'C': 1.6125, 'D': 0.8375}
vol = sum(area[r[0]] * r[1] for r in resumo)
print('peças', collections.Counter(r[0] for r in linhas))
for r in resumo: print('  seção', r)
print(f'volume de alvenaria de pedra (área da memória × comprimento): {vol:.1f} m³')
