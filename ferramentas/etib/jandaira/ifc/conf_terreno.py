# diferença entre a CT das pranchas (DRE/ESG) e o terreno do IMP (modelo) em cada caixa
import os, sys, json, numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\compat_geral'); import jan_dados as JD
sys.stdout.reconfigure(encoding='utf-8')
C = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01'
R = json.load(open(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02\rotulos_gravidade.json', encoding='utf-8'))
SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None); JD.agrupar_caixas(SH, MH)
T = JD.Terreno(g=os.path.join(C, 'geo'))
print('interno (0,0,0) -> compart', JD.para_compart(np.array([[0.0, 0, 0]]), g=os.path.join(C, 'geo')).round(3))
for disc in ('DRE', 'ESG'):
    d = []
    for n, v in R[disc].items():
        if not v.get('CT'): continue
        Mg = [M for M in MH if M.get('grupo') == n and M['disc'] == disc]
        if not Mg: continue
        c = (Mg[0]['glo'] + Mg[0]['ghi']) / 2; zt = 147 + T.z(c[0], c[1])
        cts = sorted({x[0] for x in v['CT']})
        d.append((n, cts, round(zt, 2), round(cts[0] - zt, 2), round(147 + Mg[0]['ghi'][2], 2)))
    dd = np.array([x[3] for x in d if not np.isnan(x[3])])
    print(disc, len(d), 'CT − terreno IMP: mediana %+.2f, p10 %+.2f, p90 %+.2f, min %+.2f, max %+.2f' % (np.median(dd), np.percentile(dd, 10), np.percentile(dd, 90), dd.min(), dd.max()))
    for x in sorted(d, key=lambda x: x[3]): print('   ', x)
