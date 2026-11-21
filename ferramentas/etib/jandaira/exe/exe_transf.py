# -*- coding: utf-8 -*-
"""Pranchas executivas revisadas (R01) — posição de cada DWG de projeto em relação aos modelos JAN (interno, m).
1) grosso: retângulo do campo 45x25 da base de arquitetura do DWG casado com o da SIT R03 (UTM);
2) fino: ICP 2D (rotação + translação) entre os eixos dos tubos/eletrodutos do modelo de HOJE (antes do R01) e as linhas do DWG.
Grava ETIB-JANDAIRA/RELATORIOS/EXECUTIVO_R01/transformacoes_dwg_interno.json: interno = R(rot) · p_dwg + t."""
import sys, os, json, math, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf"); sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\jandaira\cps")
import dxfgeo, casar, jan_dados as JD, retangulos
sys.stdout.reconfigure(encoding='utf-8')
DX = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-"
OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R01"; os.makedirs(OUT, exist_ok=True)
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"
DWGS = {'EL-001': ('IMP-PE-EL-001-ELG-R01', ('ELE',), 'EL-001'), 'EL-002': ('IMP-PE-EL-002-ELG-R01', ('ELE',), 'EL-002'),
        'AF-001': ('IMP-PE-AF-001-HIG-R01', ('AGF',), None), 'IN-001': ('IMP-PE-IN-001-ING-R03', ('PCI',), None), 'DRE-001': ('IMP-PE-DRE-001-DRG-R00', ('DRE',), None)}
Rc, oc = JD.tf_compart(JD.meta('ELE', G))
u2i = lambda P: np.c_[P, np.zeros(len(P))] @ Rc.T + oc
C_SIT = u2i(np.array([[631596.346, 8721147.338]]))[0][:2]
p2 = u2i(np.array([[631596.346 + math.cos(math.radians(25.7107)), 8721147.338 + math.sin(math.radians(25.7107))]]))[0][:2]
ANG_SIT = math.degrees(math.atan2(p2[1] - C_SIT[1], p2[0] - C_SIT[0]))
rot = lambda a: np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
res = {}
for k, (arq, discs, fonte) in DWGS.items():
    g = dxfgeo.load(DX + arq + '.dxf')
    R = [r for r in retangulos.retangulos(g, 44.9, 45.1) if abs(r['b'] - 25.0) < 0.02]
    if not R: print(k, 'sem campo 45x25 na base'); continue
    r0 = R[0]; cands = []
    for flip in (0.0, 180.0):
        a = math.radians(ANG_SIT - r0['ang'] + flip); t = C_SIT - rot(a) @ r0['c']; cands.append((a, t))
    S, _ = JD.carregar(g=G, est=None, discs=discs)
    if fonte: S = [s for s in S if ('Fonte: ' + fonte) in (s.get('desc') or '')]
    S = [s for s in S if np.linalg.norm(s['b'][:2] - s['a'][:2]) > 0.5 and abs(s['b'][2] - s['a'][2]) < 0.5 * np.linalg.norm(s['b'][:2] - s['a'][:2])]
    M = np.array([s['a'][:2] + (s['b'][:2] - s['a'][:2]) * u for s in S for u in np.linspace(0, 1, max(2, int(np.linalg.norm(s['b'][:2] - s['a'][:2]) / 0.5)))])
    GS = casar.GradeSeg(casar.segmentos(g, lambda s: True, max_seg=300.0)); melhor = None
    for a, t in cands:
        # semente: interno -> DWG é o inverso de (DWG -> interno = R(a) p + t)
        Ri = rot(-a); ti = -Ri @ t; T0 = (-a, ti[0], ti[1])
        T, n = casar.icp_seg(M, GS, T0, raios=(3.0, 1.0, 0.4, 0.15, 0.05, 0.02), it_por_raio=6)
        ad, d = casar.aderencia_seg(M, GS, T)
        q = (ad[0.05], float(np.median(d[np.isfinite(d)])) if np.isfinite(d).any() else 9.9)
        if melhor is None or q[0] > melhor[2][0]: melhor = (T, n, q)
    T, n, q = melhor; a_id = T[0]; t_id = np.array(T[1:])          # interno -> DWG
    a = -a_id; t = -rot(a) @ t_id                                   # DWG -> interno
    res[k] = dict(arquivo='24-049-JDI-CTO-ETIB-' + arq, rot_graus=math.degrees(a), t=t.tolist(), regra='interno = R(rot) · p_dwg + t (m); dwg = R(rot_inv) · p_interno + t_inv',
                  rot_inv_graus=math.degrees(a_id), t_inv=t_id.tolist(),
                  aderencia_5cm=round(float(q[0]), 3), mediana_m=round(float(q[1]), 4), pontos_modelo=len(M))
    print('%-8s rot %9.4f°  t %s  modelo a < 5 cm do DWG: %.0f%%  mediana %.3f m  (%d pts)' % (k, math.degrees(a), np.round(t, 3), 100 * q[0], q[1], len(M)))
json.dump(res, open(os.path.join(OUT, 'transformacoes_dwg_interno.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
