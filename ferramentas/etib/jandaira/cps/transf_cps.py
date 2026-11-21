# -*- coding: utf-8 -*-
"""Transformações local do campo (pranchas CPS) -> UTM e -> interno dos modelos JAN, e grava os JSON em CAD_GEORREFERENCIADO.
Premissa (18/10/2026): campo 50x30 do CPS R01 centrado no piso do campo do IMP as built (interno 90,952 / 114,112),
eixo longo no ângulo do campo da SIT R03 (UTM 25,7107°; interno -5,3818°). Sentido decidido pelo QDLT-CAMPO (4,3 m do modelado;
girado 180° cairia a 66 m)."""
import sys, json, math, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"; CAD = r"D:\Projeto Modelagem\ETIB-JANDAIRA\CAD_GEORREFERENCIADO"
C_INT = np.array([90.952, 114.112]); ANG_INT = -5.3818; ANG_UTM = 25.7107
C_UTM = JD.para_compart(np.array([[C_INT[0], C_INT[1], 0.0]]))[0][:2]
C0 = {'DRE-001-DRG-R01': (27.150, 17.150), 'EL-001-ELG-R01': (43.983, 58.077), 'IN-001-ING-R01': (22.387, 16.050)}
def rot(a): t = math.radians(a); return np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
out = {}
for k, c0 in C0.items():
    c0 = np.array(c0); t_utm = C_UTM - rot(ANG_UTM) @ c0; t_int = C_INT - rot(ANG_INT) @ c0
    d = dict(arquivo='24-049-JDI-CTO-ETIB-CPS-PE-' + k, regra='UTM = R(rot_utm) · p_local + t_utm (rotação em torno de 0,0); interno JAN = R(rot_int) · p_local + t_int',
             rot_utm_graus=ANG_UTM, t_utm=[round(float(v), 6) for v in t_utm], rot_int_graus=ANG_INT, t_int=[round(float(v), 6) for v in t_int],
             centro_campo_local=c0.tolist(), centro_campo_utm=[round(float(v), 4) for v in C_UTM], centro_campo_interno=C_INT.tolist(),
             premissa='campo 50x30 do CPS centrado no piso do campo do IMP as built, no ângulo da SIT R03; precisão estimada ±1 m (sem o as built do campo)',
             data='2026-10-18')
    json.dump(d, open(CAD + r'\transformacao_CPS_%s_local_para_UTM.json' % k, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    out[k] = d; print(k, 'rot %.4f  t_utm %s  t_int %s' % (ANG_UTM, d['t_utm'], d['t_int']))
# conferência: o centro local vai para o centro UTM; e UTM -> interno bate com t_int
R, o = JD.tf_compart(JD.meta('ELE', G))
for k, d in out.items():
    p = np.array(d['centro_campo_local']) + np.array([10.0, 3.0])
    u = rot(ANG_UTM) @ p + np.array(d['t_utm']); i1 = np.array([u[0], u[1], 0.0]) @ R.T + o; i2 = rot(ANG_INT) @ p + np.array(d['t_int'])
    print('  conferência %s: |interno pela UTM - interno direto| = %.4f m' % (k, np.linalg.norm(i1[:2] - i2)))
