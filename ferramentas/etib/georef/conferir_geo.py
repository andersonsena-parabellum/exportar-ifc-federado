# -*- coding: utf-8 -*-
"""Confere os DWGs gerados (relidos do DXF exportado de cada _GEO/_REF), todos em UTM:
  1. arquitetura de cada disciplina × arquitetura do SIT_GEO (mesmos blocos, devem coincidir);
  2. topografia embutida (NOVA TOPOGRAFIA) × levantamento TOP_REF;
  3. estações C1/C2 do TOP_REF × coordenadas da prancha;
  4. TER-IMP_REF: blocos de arquitetura × SIT_GEO (registro do deslocamento da terraplanagem);
  5. rede da disciplina dentro da área do levantamento.
Gera CSV de resumo e um PNG por disciplina (rede sobre arquitetura + levantamento) e um geral.
Uso: python -I -X utf8 conferir_geo.py
"""
import sys, os, csv, math, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler
from icp_pts import Grade
from casar_blocos import casar, resumo

DX = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\dxf_geo'
REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
P = '24-049-CAU-RNV-ETIB-'
F = {'SIT': 'IMP-PE-URB-001-SIT-R02_GEO', 'SIT_REF': 'IMP-PE-URB-001-SIT-R02_REF', 'TOP': 'IMP-PE-TOP-001-PLT-R00_REF',
     'TER': 'TER-IMP-001-R00_REF', 'AF': 'IMP-PE-AGF-001-R02_GEO', 'ESG': 'IMP-PE-ESG-001-HIG-R02_GEO',
     'DRE': 'IMP-PE-DRE-001-DRG-R02_GEO', 'INC': 'IMP-PE-INC-001-ING-R03_GEO', 'EL1': 'IMP-PE-EL-001-ELG-R05_GEO',
     'EL2': 'IMP-PE-EL-002-ELG-R02_GEO'}
REDE = {  # layers da rede de cada disciplina (para o mapa e a extensão)
    'AF': ('AF-Condutos', 'AL-Condutos', 'AF-Condutos Reúso'), 'ESG': ('TQ-Condutos', 'TQ-Condutos Gordura', 'TQ-Caixa de alvenaria'),
    'DRE': ('AP-Condutos', 'AP-Caixa de alvenaria'), 'INC': ('HI-Condutos (Alimentador e Sub-Ramal)', '0. F_PCI - Detecção e Alarme', '0. F_PCI - Parede TRRF'),
    'EL1': ('02. F_ELETRODUTO PISO', '0. F_CAIXA-CONDULETE'), 'EL2': ('02. F_ELETRODUTO PISO',)}
C1 = (567744.9586, 8634679.9890); C2 = (567712.0314, 8634683.6492)
CENTRO = np.array([567721.3, 8634654.9]); RAIO = 400.0


def f(tag): return os.path.join(DX, P + F[tag] + '.dxf')


def verts(prims, cond):
    v = [d['pts'][:, :2] for d in prims if d['tipo'] in ('LINE', 'PL') and cond(d)]
    if not v: return np.zeros((0, 2))
    V = np.unique(np.round(np.vstack(v), 4), axis=0)
    return V[np.hypot(*(V - CENTRO).T) < RAIO]


def eh_arq(d):
    return d['layer'].upper().replace('-', '_').startswith('ARQ') and 'NOVA TOPOGRAFIA' not in d['path']


def segs(prims, cond):
    out = []
    for d in prims:
        if d['tipo'] in ('LINE', 'PL') and cond(d):
            p = d['pts'][:, :2]
            if np.hypot(*(p - CENTRO).T).max() < RAIO:
                out.extend(zip(p[:-1], p[1:]))
    return out


def main():
    rng = np.random.default_rng(3)
    S, T = ler(f('SIT')), ler(f('TOP'))
    linhas = []
    # base
    B_arq = verts(S, lambda d: not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO')))
    B_top = verts(T, lambda d: True)
    G_arq, G_top = Grade(B_arq, 0.5), Grade(B_top, 0.5)
    A = verts(S, lambda d: d['path'].startswith('NOVA TOPOGRAFIA'))
    d, _ = G_top.query(A)
    linhas.append(['SIT_GEO', 'NOVA TOPOGRAFIA × TOP_REF', len(A), f'{np.median(d)*1000:.2f}', f'{d.max()*1000:.2f}', f'{np.mean(d<0.001)*100:.1f}', ''])
    est = {d['texto']: d for d in T if d['tipo'] == 'TEXT'}
    ins_est = [d['pts'][0, :2] for d in T if d['tipo'] == 'INSERT' and d['nome'].upper().startswith('ESTA')]
    for nome, c in (('C1', C1), ('C2', C2)):
        dm = min(math.hypot(p[0] - c[0], p[1] - c[1]) for p in ins_est)
        linhas.append(['TOP_REF', f'estação {nome} × prancha (E {c[0]:.4f} N {c[1]:.4f})', 1, f'{dm*1000:.2f}', f'{dm*1000:.2f}', '', ''])
    # terraplanagem
    g = casar(f('TER'), f('SIT'), imprime=False)[0]
    rot, tx, ty, disp = resumo(g)
    linhas.append(['TER-IMP_REF', f'{len(g)} blocos de arquitetura × SIT_GEO: a arquitetura do TER está deslocada ({-tx:+.4f}; {-ty:+.4f}) m em relação ao SIT_GEO', len(g), f'{math.hypot(tx, ty)*1000:.1f}', '', '', 'terraplanagem R00 com os blocos 1,92 m a leste da posição do SIT R02 e das disciplinas'])
    # disciplinas
    mapas = {}
    for tag in ['AF', 'ESG', 'DRE', 'INC', 'EL1', 'EL2']:
        D = ler(f(tag))
        Aa = verts(D, eh_arq)
        As = Aa[rng.choice(len(Aa), min(6000, len(Aa)), replace=False)]
        da, _ = G_arq.query(As)
        linhas.append([tag + '_GEO', 'arquitetura × SIT_GEO', len(As), f'{np.median(da)*1000:.2f}', '', f'{np.mean(da<0.001)*100:.1f}',
                       'os vértices que não casam são de cópias/versões da arquitetura fora da implantação' if np.mean(da < 0.001) < 0.9 else ''])
        At = verts(D, lambda d: 'NOVA TOPOGRAFIA' in d['path'])
        if len(At):
            dt, _ = G_top.query(At)
            linhas.append([tag + '_GEO', 'topografia embutida × TOP_REF', len(At), f'{np.median(dt)*1000:.2f}', f'{np.percentile(dt,95)*1000:.2f}', f'{np.mean(dt<0.001)*100:.1f}', ''])
        R = np.vstack([d['pts'][:, :2] for d in D if d['tipo'] in ('LINE', 'PL', 'CIRCLE', 'INSERT') and d['layer'] in REDE[tag]] or [np.zeros((0, 2))])
        Rn = R[np.hypot(*(R - CENTRO).T) < RAIO]
        linhas.append([tag + '_GEO', 'extensão da rede (UTM)', len(Rn),
                       f'E {Rn[:,0].min():.1f}..{Rn[:,0].max():.1f}' if len(Rn) else '', f'N {Rn[:,1].min():.1f}..{Rn[:,1].max():.1f}' if len(Rn) else '', '',
                       f'{len(R)-len(Rn)} pontos da rede fora de {RAIO:.0f} m (detalhes/legenda)'])
        mapas[tag] = (segs(D, lambda d: d['layer'] in REDE[tag]), Aa)
    with open(os.path.join(REL, 'GEO_conferencia_2026-10-18.csv'), 'w', newline='', encoding='utf-8-sig') as fo:
        w = csv.writer(fo, delimiter=';')
        w.writerow(['arquivo', 'teste', 'n', 'mediana_mm (ou valor)', 'max/p95_mm (ou valor)', 'pct_<1mm', 'obs'])
        w.writerows(linhas)
    for l in linhas: print(' | '.join(str(x) for x in l))
    # mapas
    s_arq = segs(S, lambda d: not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO')) and 'PISO T' not in d['path'])
    s_top = segs(T, lambda d: d['layer'] in ('TOP-MURO', 'TOP-MEIOFIO', 'TOP-EDIFICAÇÃO', 'TOP-PASSEIO', 'TOP-CONTENÇÃO', 'TOP-ESCADA'))
    cores = {'AF': '#1f77b4', 'ESG': '#8c564b', 'DRE': '#17becf', 'INC': '#d62728', 'EL1': '#ff7f0e', 'EL2': '#bcbd22'}
    for tag, (sg, _) in list(mapas.items()) + [('GERAL', (None, None))]:
        fig, ax = plt.subplots(figsize=(16, 14))
        ax.add_collection(LineCollection(s_top, colors='#1a7f1a', linewidths=0.6, label='levantamento TOP-001 (muros, meio-fio, edificações)'))
        ax.add_collection(LineCollection(s_arq, colors='0.72', linewidths=0.22, label='SIT R02 _GEO (arquitetura)'))
        if tag == 'GERAL':
            for k, (s2, _) in mapas.items():
                ax.add_collection(LineCollection(s2, colors=cores[k], linewidths=0.7, label=k))
        else:
            ax.add_collection(LineCollection(sg, colors=cores[tag], linewidths=0.8, label=f'{tag} _GEO (rede)'))
        for nome, c in (('C1', C1), ('C2', C2)):
            ax.plot(*c, 'k^', ms=7); ax.annotate(nome, c, xytext=(4, 4), textcoords='offset points', fontsize=9)
        ax.set_xlim(567600, 567830); ax.set_ylim(8634530, 8634735)
        ax.set_aspect('equal'); ax.grid(alpha=0.25); ax.legend(loc='lower left', fontsize=9)
        ax.set_title(f'ETIB Catu — {tag} em UTM SIRGAS 2000 / 24S (E, N em m)')
        ax.ticklabel_format(useOffset=False, style='plain')
        fig.savefig(os.path.join(REL, f'GEO_{tag}_sobre_SIT_TOP_2026-10-18.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
    print('ok')


if __name__ == '__main__':
    main()
