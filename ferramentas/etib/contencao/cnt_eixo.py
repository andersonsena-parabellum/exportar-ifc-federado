# -*- coding: utf-8 -*-
"""Face frontal do muro (planta do DWG CNT-001) -> UTM -> coordenadas internas do Revit.
Gera work/cnt_face.json (segmentos A–D) e work/amostras_cnt.csv (pontos para amostrar o terreno do IMP
de um lado e do outro do muro). Offset positivo = lado sul (faixa de material drenante = lado do aterro, a confirmar)."""
import json, math
import numpy as np

W = r"D:\Projeto Modelagem\FERRAMENTAS\contencao\work"
T = json.load(open(r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\CAD_GEORREFERENCIADO\transformacao_CNT_local_para_UTM.json", encoding='utf-8'))
a = math.radians(T['rigid']['rot_deg']); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]); t = np.array(T['rigid']['t'])
ORIG = np.array([561500.0, 8658000.0])   # origem interna do Revit (sem rotação)

# vértices da face (linhas 1806F, 18071, 18084, 18098 do layer 0, DWG local) e seções (cortes A–D da planta)
face_local = [(-22.5841, 144.0143), (30.4654, 138.5518), (69.7576, 134.5059), (89.4535, 132.4778), (94.5375, 131.9543)]
secoes = ['A', 'B', 'C', 'D']
SEC = {  # memória de cálculo + cortes do DWG (m)
    'A': {'H': 2.50, 'topo': 0.40, 'base': 0.90, 'degraus': 5, 'sap_L': 1.90, 'sap_H': 0.50, 'ponta': 0.75, 'talao': 0.25},
    'B': {'H': 2.00, 'topo': 0.525, 'base': 0.90, 'degraus': 4, 'sap_L': 1.70, 'sap_H': 0.50, 'ponta': 0.55, 'talao': 0.25},
    'C': {'H': 1.50, 'topo': 0.65, 'base': 0.90, 'degraus': 3, 'sap_L': 1.50, 'sap_H': 0.50, 'ponta': 0.35, 'talao': 0.25},
    'D': {'H': 1.00, 'topo': 0.775, 'base': 0.90, 'degraus': 2, 'sap_L': 0.0, 'sap_H': 0.0, 'ponta': 0.0, 'talao': 0.0},
}
P = [(R @ np.array(p)) + t - ORIG for p in face_local]
segs = []
est0 = 0.0
for i, s in enumerate(secoes):
    p0, p1 = P[i], P[i + 1]
    L = float(np.linalg.norm(p1 - p0)); u = (p1 - p0) / L
    n_sul = np.array([u[1], -u[0]])          # direita de quem anda de oeste p/ leste = sul
    segs.append({'secao': s, 'p0': p0.round(4).tolist(), 'p1': p1.round(4).tolist(), 'L': round(L, 3),
                 'u': u.round(6).tolist(), 'n_sul': n_sul.round(6).tolist(), 'est0': round(est0, 3), **SEC[s]})
    est0 += L
json.dump({'origem_interna_utm': ORIG.tolist(), 'transformacao': T['rigid'], 'segmentos': segs,
           'nota': 'p0/p1 = face frontal (vertical) do muro em coordenadas internas (m); a pedra fica do lado sul (n_sul)'},
          open(W + r"\cnt_face.json", 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('comprimentos', [(s['secao'], s['L']) for s in segs], 'total', round(est0, 2))

OFFS = [-6.0, -3.0, -1.5, -0.5, 0.45, 1.5, 3.0, 6.0]
with open(W + r"\amostras_cnt.csv", 'w', encoding='utf-8') as f:
    k = 0
    for s in segs:
        p0 = np.array(s['p0']); u = np.array(s['u']); n = np.array(s['n_sul'])
        nstep = int(s['L'] // 1.0)
        for j in range(nstep + 1):
            d = min(j * 1.0, s['L'])
            for o in OFFS:
                q = p0 + u * d + n * o
                f.write(f"{k};{s['secao']};{s['est0'] + d:.3f};{o};{q[0]:.4f};{q[1]:.4f}\n"); k += 1
print('amostras', k)
