# -*- coding: utf-8 -*-
"""ETIB Olindina (ONN) — fase 2: redes externas extraídas dos DWG R00 (21/10/2026), em UTM SIRGAS 2000 / 24S.

O projeto da Olindina é a ampliação do bloco BA5 (5 salas) e as ligações dele às redes existentes da escola. As pranchas
desenham as redes novas e, como referência, as redes existentes onde as novas se ligam (layer "Tubulação existente", com
CT/CF das caixas). As duas entram: as novas são a rede do projeto; as existentes entram como obstáculo e saem no IFC
marcadas como existentes (cadastro da prancha).

Fontes (coordenadas locais, lidas do DXF das cópias em FERRAMENTAS/georef/work/OLINDINA/dxf; geometria conferida no desenho):
  ESG-001 = DRE-001 (mesmo arquivo): pluvial do BA5 (AP-*), esgoto do BA5 (TQ-*) e as redes existentes de esgoto (CE/PVE)
           e pluvial (CA/PVP); transformação rot 0, t = (574033.1579; 8743129.589).
  AF-001: ramal novo PVC 32 mm do BA5 e rede existente PVC 60 mm (mesma transformação).
  EL-001: alimentador QGBT -> QDLT do BA5, eletroduto Ø3" com 5 caixas 80x80 (já em UTM).
  IN-001: ramal novo de hidrante PEAD 2.1/2" (rot 0, t = (573528.43577; 8743203.63527)). O SDAI não tem rede externa (só legenda).
Saída: ETIB-OLINDINA/RELATORIOS/FASE2_REDES_2026-10-21/ONN_fase2_*.csv
Uso: .venv/Scripts/python.exe -X utf8 olindina/rede/onn_fase2.py"""
import os, csv, math
import numpy as np

OUT = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS\FASE2_REDES_2026-10-21'
T_AF = (574033.1579, 8743129.589)
T_IN = (573528.4357723719, 8743203.6352746593)


def utm(p, t=T_AF):
    return (round(p[0] + t[0], 3), round(p[1] + t[1], 3))


# ------------------------------------------------------------------ caixas (centro local; CT/CF das etiquetas da prancha)
# novas do pluvial do BA5 (símbolo "CA" sem número na prancha: numeradas de montante para jusante)
CAIXAS_AP = [  # caixa, tipo, x, y, CT, CF, lado, obs
    ('CA-01', 'CA', -145.925, 146.049, 168.00, 167.40, 0.60, ''),
    ('CA-02', 'CA', -131.527, 131.787, 168.00, 167.21, 0.60, ''),
    ('CA-03', 'CA', -125.286, 125.605, 168.00, 167.13, 0.60, ''),
    ('CA-04', 'CA', -112.710, 113.240, 168.00, 166.96, 0.60, ''),
    ('CA-05', 'CA', -106.970, 119.030, 168.00, 166.89, 0.60, ''),
    # a etiqueta diz CF 166,91 e profundidade 1,19 m; 168,00 − 1,19 = 166,81 é o que fecha com a declividade de 1 % vinda da CA-05
    ('CA-06', 'CA', -100.830, 125.230, 168.00, 166.81, 0.60, 'prancha: CF 166,91 e profundidade (01.19); adotado 166,81 (profundidade e i = 1 %)'),
]
# existentes (cadastro na prancha)
CAIXAS_EXIST = [
    ('CA-30', 'CA', 'AP', -103.915, 181.786, 168.00, 167.40, 0.60),
    ('CA-31', 'CA', 'AP', -116.512, 169.161, 168.00, 167.23, 0.60),
    ('CA-32', 'CA', 'AP', -130.615, 154.469, 168.00, 167.03, 0.60),
    ('PVP-33', 'PVP', 'AP', -121.765, 145.030, 168.00, 166.91, 0.40),
    ('PVP-34', 'PVP', 'AP', -115.805, 139.058, 168.00, 166.83, 0.40),
    ('PVP-35', 'PVP', 'AP', -107.452, 130.742, 168.00, 166.27, 0.40),
    ('PVP-36', 'PVP', 'AP', -95.888, 118.227, 168.00, 166.11, 0.40),
    ('CE-25', 'CE', 'ESG', -105.387, 176.544, 168.30, 167.72, 0.60),
    ('CE-24', 'CE', 'ESG', -114.293, 167.473, 168.30, 167.60, 0.60),
    ('CE-23', 'CE', 'ESG', -124.057, 158.198, 168.30, 167.47, 0.60),
    ('CE-22', 'CE', 'ESG', -127.992, 153.660, 168.00, 167.42, 0.60),
    ('CE-21', 'CE', 'ESG', -117.390, 141.988, 168.00, 167.27, 0.60),
    ('PVE-20', 'PVE', 'ESG', -108.362, 133.176, 168.00, 167.00, 0.40),
    ('PVE-15', 'PVE', 'ESG', -97.083, 127.140, 168.00, 166.87, 0.40),
]
POS = {c[0]: (c[2], c[3]) for c in CAIXAS_AP}
POS.update({c[0]: (c[3], c[4]) for c in CAIXAS_EXIST})
CF = {c[0]: c[5] for c in CAIXAS_AP}
CF.update({c[0]: c[6] for c in CAIXAS_EXIST})

# ------------------------------------------------------------------ trechos por gravidade (eixo local; nó = caixa ou ponto)
# (trecho, de, para, [pontos intermediários], DN, material da etiqueta, i %, classe, situação)
#   pontos "Pn" = início do ramal na face do BA5 (prumada pluvial / saída de esgoto); "Nn" = mudança de direção sem caixa
PONTOS = {'P1': (-146.338, 148.889), 'P2': (-129.667, 133.437), 'P3': (-123.598, 127.417), 'P4': (-112.307, 116.225),
          'P5': (-104.485, 124.132), 'P6': (-137.153, 156.343), 'P7': (-124.194, 143.669),
          'D1': (-123.774, 126.873), 'D2': (-135.354, 138.345), 'D3': (-136.005, 138.989), 'D4': (-109.942, 117.509), 'D5': (-107.337, 120.139),
          'N1': (-112.931, 115.438), 'N2': (-103.152, 125.443), 'N3': (-135.959, 136.495), 'N4': (-135.952, 137.703), 'N5': (-136.610, 137.080),
          'N6': (-136.600, 138.371), 'N7': (-108.876, 117.520), 'N8': (-103.256, 125.372),
          'S-TQ': (-121.578, 137.507),
          'EP-ini': (-92.362, 192.819), 'EP-fim': (-98.677, 115.214), 'EE-ini': (-92.535, 189.943)}
POS.update(PONTOS)
TRECHOS = [
    # pluvial novo do BA5 (ESG-001: "PVCR 150 mm i=1%", "PVC 200 mm i=1%", drenos "PVC 40 mm i=1%")
    ('AP-01', 'P1', 'CA-01', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-02', 'CA-01', 'CA-02', 150, 'PVCR', 1.0, 'coletor', 'novo'),
    ('AP-03', 'P2', 'CA-02', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-04', 'CA-02', 'CA-03', 200, 'PVC', 1.0, 'coletor', 'novo'),
    ('AP-05', 'P3', 'CA-03', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-06', 'D1', 'CA-03', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-07', 'CA-03', 'CA-04', 200, 'PVC', 1.0, 'coletor', 'novo'),
    ('AP-08', 'P4', 'N1', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-09', 'N1', 'CA-04', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-10', 'CA-04', 'CA-05', 200, 'PVC', 1.0, 'coletor', 'novo'),
    ('AP-11', 'D4', 'N7', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-12', 'N7', 'CA-05', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-13', 'D5', 'CA-05', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-14', 'CA-05', 'CA-06', 200, 'PVC', 1.0, 'coletor', 'novo'),
    ('AP-15', 'P5', 'N8', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-16', 'N8', 'N2', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-17', 'N2', 'CA-06', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-18', 'CA-06', 'PVP-36', 200, 'PVC', 1.0, 'coletor', 'novo'),
    ('AP-19', 'P6', 'CA-32', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-20', 'P7', 'PVP-33', 150, 'PVCR', 1.0, 'ramal', 'novo'),
    ('AP-21', 'D2', 'N4', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-22', 'N4', 'N3', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-23', 'D3', 'N6', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-24', 'N6', 'N5', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-25', 'N5', 'N3', 40, 'PVC', 1.0, 'dreno', 'novo'),
    ('AP-26', 'N3', 'CA-02', 40, 'PVC', 1.0, 'dreno', 'novo'),
    # esgoto novo do BA5 ("PVC 100 mm i=1%"; liga na CE-21 existente)
    ('TQ-01', 'S-TQ', 'CE-21', 100, 'PVC', 1.0, 'ramal', 'novo'),
    # pluvial existente (cadastro da prancha)
    ('APE-01', 'EP-ini', 'CA-30', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-02', 'CA-30', 'CA-31', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-03', 'CA-31', 'CA-32', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-04', 'CA-32', 'PVP-33', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-05', 'PVP-33', 'PVP-34', 250, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-06', 'PVP-34', 'PVP-35', 250, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-07', 'PVP-35', 'PVP-36', 300, 'PVC', 1.0, 'coletor', 'existente'),
    ('APE-08', 'PVP-36', 'EP-fim', 300, 'PVC', 1.0, 'coletor', 'existente'),
    # esgoto existente
    ('ESE-01', 'EE-ini', 'CE-25', 100, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-02', 'CE-25', 'CE-24', 100, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-03', 'CE-24', 'CE-23', 100, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-04', 'CE-23', 'CE-22', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-05', 'CE-22', 'CE-21', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-06', 'CE-21', 'PVE-20', 150, 'PVC', 1.0, 'coletor', 'existente'),
    ('ESE-07', 'PVE-20', 'PVE-15', 150, 'PVC', 1.0, 'coletor', 'existente'),
]
# CF na ponta onde a prancha não dá a caixa: ramal que chega em caixa entra pelo fundo dela (CF da caixa) e sobe a 1 % para montante
CF_PONTA = {}

# ------------------------------------------------------------------ pressurizadas (planta; a cota sai do estudo de cota no adaptador)
PRESS = [  # sistema, trecho, de_no, para_no, DE_mm, material, situação, [pontos UTM], obs
    ('AF', 'AF-01', 'AFE-T1', 'BA5', 32, 'Tubo PVC soldável marrom', 'novo',
     [utm((-118.032, 139.052)), utm((-120.071, 137.009))], 'ALIMENTAÇÃO BLOCO 5 SALAS (tê na rede existente PVC 60 mm)'),
    ('AF', 'AFE-01', 'RES', 'AFE-T2', 60, 'Tubo PVC soldável marrom', 'existente',
     [utm((-88.871, 109.889)), utm((-118.032, 139.052)), utm((-133.736, 154.756)), utm((-125.077, 163.415))], 'VEM DO RESERVATÓRIO'),
    ('AF', 'AFE-02', 'AFE-T2', 'AFE-T3', 60, 'Tubo PVC soldável marrom', 'existente',
     [utm((-125.077, 163.415)), utm((-109.451, 179.041))], ''),
    ('AF', 'AFE-03', 'AFE-T2', 'RG-10', 40, 'Tubo PVC soldável marrom', 'existente',
     [utm((-125.077, 163.415)), utm((-122.341, 160.679)), utm((-122.123, 160.473))], 'registro 1.1/4" (RG 10)'),
    ('AF', 'AFE-04', 'AFE-T3', 'RG-11', 32, 'Tubo PVC soldável marrom', 'existente',
     [utm((-109.451, 179.041)), utm((-106.138, 175.728)), utm((-105.923, 175.519))], 'registro 1" (RG 11)'),
    ('ELE', 'ELE-01', 'QGBT', 'CP-01', 90, 'Eletroduto PVC corrugado flexível', 'novo',
     [(573954.190, 8743344.074), (573948.081, 8743338.093)], 'alimentador QGBT -> QDLT do BA5: Ø3", 3#95(95)[50]'),
    ('ELE', 'ELE-02', 'CP-01', 'CP-02', 90, 'Eletroduto PVC corrugado flexível', 'novo', [(573948.081, 8743338.093), (573926.988, 8743316.760)], ''),
    ('ELE', 'ELE-03', 'CP-02', 'CP-03', 90, 'Eletroduto PVC corrugado flexível', 'novo', [(573926.988, 8743316.760), (573905.896, 8743295.427)], ''),
    ('ELE', 'ELE-04', 'CP-03', 'CP-04', 90, 'Eletroduto PVC corrugado flexível', 'novo', [(573905.896, 8743295.427), (573898.952, 8743288.496)], ''),
    ('ELE', 'ELE-05', 'CP-04', 'CP-05', 90, 'Eletroduto PVC corrugado flexível', 'novo', [(573898.952, 8743288.496), (573909.415, 8743278.131)], ''),
    ('ELE', 'ELE-06', 'CP-05', 'QDLT', 90, 'Eletroduto PVC corrugado flexível', 'novo', [(573909.415, 8743278.131), (573906.478, 8743275.105)], 'chega no QDLT do BA5'),
    ('HID', 'HID-01', 'HIDE', 'BA5', 75, 'Tubo PEAD', 'novo',
     [utm((399.333, 55.801), T_IN), utm((395.124, 51.593), T_IN)], 'VEM DAS INSTALAÇÕES EXISTENTES (compatibilizar in loco) -> segue para as instalações internas do BA5'),
]
CAIXAS_ELE = [('CP-01', 573948.081, 8743338.093), ('CP-02', 573926.988, 8743316.760), ('CP-03', 573905.896, 8743295.427),
              ('CP-04', 573898.952, 8743288.496), ('CP-05', 573909.415, 8743278.131)]


def escrever(fn, campos, linhas):
    with open(os.path.join(OUT, fn), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(campos); w.writerows(linhas)


def main():
    os.makedirs(OUT, exist_ok=True)
    disc_no = {c[0]: 'AP' for c in CAIXAS_AP}; disc_no.update({c[0]: c[2] for c in CAIXAS_EXIST})
    # gravidade
    for disc, filtro in (('AP', lambda t: t[0].startswith('AP')), ('ESG', lambda t: t[0].startswith(('TQ', 'ESE')))):
        linhas = []
        for t in TRECHOS:
            if disc == 'AP' and t[0].startswith('APE'): pass
            elif not filtro(t): continue
            nome, de, para, dn, mat, i, classe, sit = t
            a, b = np.array(POS[de]), np.array(POS[para]); L = float(np.hypot(*(b - a)))
            # sem CF numa ponta, a leitura usa a CF da outra + a declividade da etiqueta (ramal entra pelo fundo da caixa)
            cfm, cfj = CF.get(de), CF.get(para)
            if sit == 'novo' and cfm is not None and para in CF and not (para in POS and any(c[0] == para for c in CAIXAS_AP)):
                cfj = None                                  # rede nova chegando em PV existente: i = 1 % e queda dentro do PV
            linhas.append([nome, de, para, round(L, 2), dn, mat, i, cfm if cfm is not None else '', cfj if cfj is not None else '',
                           classe, sit, *utm(a), *utm(b), ''])
        escrever(f'ONN_fase2_{disc}_trechos.csv', ['trecho', 'de', 'para', 'L_m', 'DN_mm', 'material', 'i_rotulo_pct', 'CF_montante',
                                                   'CF_jusante', 'classe', 'situacao', 'E_ini', 'N_ini', 'E_fim', 'N_fim', 'obs'], linhas)
    cx = [[c[0], c[1], *utm((c[2], c[3])), c[6], c[4], c[5], round(c[4] - c[5], 2), 'novo', c[7]] for c in CAIXAS_AP]
    cx += [[c[0], c[1], *utm((c[3], c[4])), c[7], c[5], c[6], round(c[5] - c[6], 2), 'existente', ''] for c in CAIXAS_EXIST if c[2] == 'AP']
    escrever('ONN_fase2_AP_caixas.csv', ['caixa', 'tipo', 'E', 'N', 'lado_ou_raio_m', 'CT', 'CF', 'prof', 'situacao', 'obs'], cx)
    cx = [[c[0], c[1], *utm((c[3], c[4])), c[7], c[5], c[6], round(c[5] - c[6], 2), 'existente', ''] for c in CAIXAS_EXIST if c[2] == 'ESG']
    escrever('ONN_fase2_ESG_caixas.csv', ['caixa', 'tipo', 'E', 'N', 'lado_ou_raio_m', 'CT', 'CF', 'prof', 'situacao', 'obs'], cx)
    # pressurizadas
    linhas = []
    for sis, tr, de, para, d, mat, sit, P, obs in PRESS:
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(P[:-1], P[1:]))
        linhas.append([sis, tr, de, para, d, mat, sit, round(L, 2), ' '.join(f'{x:.3f},{y:.3f}' for x, y in P), obs])
    escrever('ONN_fase2_pressurizadas.csv', ['sistema', 'trecho', 'de', 'para', 'DE_mm', 'material', 'situacao', 'L_m', 'vertices_UTM', 'obs'], linhas)
    escrever('ONN_fase2_ELE_caixas.csv', ['no', 'tipo', 'E', 'N', 'lado_m'], [[n, 'CP 80x80', e, nn, 0.80] for n, e, nn in CAIXAS_ELE])
    print('gravado em', OUT)


if __name__ == '__main__':
    main()
