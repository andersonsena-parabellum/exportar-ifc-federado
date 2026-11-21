# -*- coding: utf-8 -*-
"""ETIB Catu — fase 3 das redes por gravidade, sem Revit, com as opções recomendadas do checkpoint da fase 2:
  - DRE: as 5 caixas com CF incompatível com a profundidade do próprio rótulo passam a CF = CT − profundidade
    (PVP-01, PVP-13, CA-17, CA-25, CA-08); CF de montante/jusante dos trechos refeitos com elas.
  - ESG e DRE: vale a cota das caixas (CF a CF) quando o i do rótulo não fecha (dúvidas 2 e 6).
  - ESG-26 (CF sobe 0,14 m) fica como no projeto e vira item (não se corrige em silêncio).
  - drenos Ø40 de ar-condicionado ficam como classe 'dreno' (sistema interno, fora do clash externo).
Saída: ETIB-CATU/RELATORIOS/FASE3_COTAS_2026-10-18/CAT_fase3_{DRE,ESG}_{trechos,caixas}.csv (mesmas colunas da fase 2)."""
import csv, os
REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
OUT = os.path.join(REL, 'FASE3_COTAS_2026-10-18')

def ler(fn):
    with open(fn, encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter=';'))

def grava(fn, rows):
    with open(fn, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=';'); w.writeheader(); w.writerows(rows)

for disc in ('DRE', 'ESG'):
    C = ler(os.path.join(REL, f'{disc}_fase2_caixas_2026-10-18.csv'))
    T = ler(os.path.join(REL, f'{disc}_fase2_trechos_2026-10-18.csv'))
    cf = {}
    for c in C:
        c['CF_projeto'] = c['CF']; c['ajuste_fase3'] = ''
        try:
            ct, f_, pr = float(c['CT']), float(c['CF']), float(c['prof_rotulo'])
            if disc == 'DRE' and abs(ct - f_ - pr) > 0.02:
                c['CF'] = f'{ct - pr:.2f}'; c['ajuste_fase3'] = f'CF = CT − profundidade do rótulo ({ct:.2f} − {pr:.2f}); no projeto {f_:.2f}'
        except (TypeError, ValueError):
            pass
        cf[c['caixa']] = c['CF']
    for t in T:
        for lado, col in (('de', 'CF_montante'), ('para', 'CF_jusante')):
            if t[lado] in cf and cf[t[lado]] not in ('', None) and t[col] not in ('', None) and t[col] != cf[t[lado]]:
                t['obs'] = (t['obs'] + ' | ' if t['obs'] else '') + f'{col} {t[col]} -> {cf[t[lado]]} (fase 3)'; t[col] = cf[t[lado]]
        try:
            a, b, L = float(t['CF_montante']), float(t['CF_jusante']), float(t['L_m'])
            t['i_pelas_CF_pct'] = f'{(a - b) / L * 100:.2f}'
        except (TypeError, ValueError):
            pass
    grava(os.path.join(OUT, f'CAT_fase3_{disc}_caixas.csv'), C); grava(os.path.join(OUT, f'CAT_fase3_{disc}_trechos.csv'), T)
    print(disc, 'caixas ajustadas:', [(c['caixa'], c['CF_projeto'], c['CF']) for c in C if c['ajuste_fase3']],
          '| CF ainda sobe:', [t['trecho'] for t in T if t['i_pelas_CF_pct'] not in ('', None) and float(t['i_pelas_CF_pct']) < 0])
