# -*- coding: utf-8 -*-
"""ETIB Catu: calcula a transformação de cada DWG para UTM (SIRGAS 2000 / 24S), grava os JSON em CAD_GEORREFERENCIADO
e prepara as listas de limpeza das cópias _REF (SIT, TOP, TER-IMP).

Cadeia: disciplina (local) --[blocos de arquitetura casados com o SIT]--> SIT --[NOVA TOPOGRAFIA do SIT × TOP]--> UTM.
O TOP (levantamento) e a terraplanagem já estão em UTM verdadeiro (estações C1/C2 batem com a prancha).

Uso: python -I georef_catu.py
"""
import sys, os, json, math, collections, datetime
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef')
from dxf_ler import ler
from icp_pts import icp, ang, Grade
from casar_blocos import casar, resumo

DXF = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\dxf'
OUT = r'D:\Projeto Modelagem\ETIB-CATU\CAD_GEORREFERENCIADO'
WRK = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU'
P = '24-049-CAU-RNV-ETIB-'
ARQ = {  # tag: (arquivo sem extensão, pasta de origem)
    'SIT': ('IMP-PE-URB-001-SIT-R02', '00_BASE'), 'TOP': ('IMP-PE-TOP-001-PLT-R00', '00_BASE'),
    'TER-IMP': ('TER-IMP-001-R00', '00_BASE'), 'TER-LIMP': ('TER-LIMP-002-R00', '00_BASE'), 'TER-MOV': ('TER-MOV-003-R00', '00_BASE'),
    'AF': ('IMP-PE-AGF-001-R02', '01_AF'), 'ESG': ('IMP-PE-ESG-001-HIG-R02', '02_ESG'), 'DRE': ('IMP-PE-DRE-001-DRG-R02', '03_DRE'),
    'EL1': ('IMP-PE-EL-001-ELG-R05', '04_ELE'), 'EL2': ('IMP-PE-EL-002-ELG-R02', '04_ELE'), 'INC': ('IMP-PE-INC-001-ING-R03', '05_PCI'),
}
ORIGEM_REVIT = (567700.0, 8634650.0, 0.0)   # proposta: ponto UTM redondo no centro da obra
RAIO = 1500.0                               # entidades além disso do centro da obra = carimbo/legenda/lixo


def dxf(tag): return os.path.join(DXF, P + ARQ[tag][0] + '.dxf')


def verts(prims, cond):
    v = [d['pts'][:, :2] for d in prims if d['tipo'] in ('LINE', 'PL') and cond(d)]
    return np.unique(np.round(np.vstack(v), 4), axis=0) if v else np.zeros((0, 2))


def so_translacao(A, B, t0, tol=(1.0, 0.1, 0.01, 0.002)):
    """ICP só com translação (rotação fixa 0). Devolve t, n pares, resíduo médio e máximo."""
    t = np.array(t0, float)
    G = Grade(B, 0.5)
    for d in tol:
        for _ in range(4):
            dist, j = G.query(A + t)
            m = dist < d
            t = (B[j[m]] - A[m]).mean(0)
    dist, j = G.query(A + t)
    m = dist < tol[-1]
    return t, int(m.sum()), float(dist[m].mean()), float(dist[m].max())


def main():
    log = []
    def pr(*a):
        s = ' '.join(str(x) for x in a); print(s); log.append(s)
    S, T = ler(dxf('SIT')), ler(dxf('TOP'))
    B_top = verts(T, lambda d: True)

    # 1) SIT -> UTM pela NOVA TOPOGRAFIA embutida no SIT R02
    A = verts(S, lambda d: d['path'].startswith('NOVA TOPOGRAFIA'))
    R, t_icp, ia, ib, dd = icp(A, B_top, R=np.eye(2), t=np.array([-0.8, 284.9]), tol=(2, 0.3, 0.05, 0.005), it=5)
    t_sit, n, rm, rx = so_translacao(A, B_top, t_icp)
    pr(f'SIT -> UTM (NOVA TOPOGRAFIA × TOP): ICP livre rot {ang(R):+.7f}°; adotado só translação t=({t_sit[0]:.4f}, {t_sit[1]:.4f}); '
       f'{n}/{len(A)} vértices, resíduo médio {rm*1000:.2f} mm, máx {rx*1000:.2f} mm')
    # pontos cotados (cópia ao lado, 200 m a leste) — só registro
    Ap = np.array([d['pts'][0, :2] for d in S if d['tipo'] == 'INSERT' and d['path'] == '' and d['layer'] == 'TOP-COTAS'])
    Bp = np.array([d['pts'][0, :2] for d in T if d['tipo'] == 'INSERT' and d['path'] == '' and d['layer'] == 'TOP-COTAS'])
    tp, npnt, rmp, _ = so_translacao(Ap, Bp, Bp.mean(0) - Ap.mean(0), tol=(30, 2, 0.1, 0.002))
    pr(f'  (cópia dos {len(Ap)} pontos cotados no SIT, 200 m a leste: TOP = SIT + ({tp[0]:.4f}, {tp[1]:.4f}), {npnt} pares — não é a posição da obra)')

    # alternativas para registro: TER (restaurante) e NOVA TOPOGRAFIA1 das disciplinas
    alt = {}
    g = casar(dxf('TER-IMP'), dxf('SIT'), imprime=False)[0]
    rot, tx, ty, disp = resumo(g); alt['TER_R00'] = [-tx, -ty]
    pr(f'  alternativa TER R00 ({len(g)} blocos, ex. BLOCO RESTAURANTE): SIT -> UTM = ({-tx:.4f}, {-ty:.4f})  Δ em relação ao adotado ({-tx - t_sit[0]:+.4f}, {-ty - t_sit[1]:+.4f})')

    # 2) disciplinas -> SIT pelos blocos de arquitetura
    res = {}
    Bs = verts(S, lambda d: not d['path'].startswith(('NOVA TOPOGRAFIA', 'SIMB_PONTO')))
    Bs = Bs[(np.abs(Bs[:, 0] - 567722) < RAIO) & (np.abs(Bs[:, 1] - 8634370) < RAIO)]
    G_sit = Grade(Bs, 0.5)
    G_top = Grade(B_top, 0.5)
    rng = np.random.default_rng(7)
    for tag in ['AF', 'ESG', 'DRE', 'INC', 'EL1', 'EL2']:
        D = ler(dxf(tag))
        grupos = casar(dxf(tag), dxf('SIT'), imprime=False)
        g = grupos[0]
        rot, tx, ty, disp = resumo(g)
        t_tot = np.array([tx, ty]) + t_sit
        # conferência 1: vértices de arquitetura da disciplina sobre o SIT (sistema do SIT)
        Aa = verts(D, lambda d: d['layer'].upper().replace('-', '_').startswith('ARQ_BASE') and 'NOVA TOPOGRAFIA' not in d['path'])
        Aa = Aa[(np.abs(Aa[:, 0] + tx - 567722) < RAIO) & (np.abs(Aa[:, 1] + ty - 8634370) < RAIO)]
        As = Aa[rng.choice(len(Aa), min(6000, len(Aa)), replace=False)]
        da, _ = G_sit.query(As + [tx, ty])
        # conferência 2: topografia embutida na disciplina (se houver) sobre o TOP, já em UTM
        At = verts(D, lambda d: 'NOVA TOPOGRAFIA' in d['path'])
        topo = None
        if len(At):
            dt, _ = G_top.query(At + t_tot)
            t_c, nc, rc, _ = so_translacao(At, B_top, t_tot)
            topo = {'mediana_mm': float(np.median(dt) * 1000), 'pct_5cm': float(np.mean(dt < 0.05) * 100),
                    'pct_20cm': float(np.mean(dt < 0.20) * 100),
                    'translacao_pela_propria_topografia': [float(t_c[0]), float(t_c[1])],
                    'delta_m': [float(t_c[0] - t_tot[0]), float(t_c[1] - t_tot[1])]}
            alt.setdefault('NOVA_TOPOGRAFIA1_disciplinas', [float(t_c[0] - tx), float(t_c[1] - ty)])
        # extensão da rede (todas as primitivas fora dos blocos de arquitetura), em UTM
        Ar = np.vstack([d['pts'][:, :2] for d in D if d['tipo'] in ('LINE', 'PL') and not d['layer'].upper().replace('-', '_').startswith(('ARQ', 'DI_', 'COTA'))
                        and not d['path'].startswith(('zw$7D57', 'zw$44A6', 'ARQ'))]) + t_tot
        Ar = Ar[(np.abs(Ar[:, 0] - 567722) < RAIO) & (np.abs(Ar[:, 1] - 8634655) < RAIO)]
        res[tag] = {
            'fonte': P + ARQ[tag][0] + '.dwg', 'pasta_origem': 'PROJETO_ORIGINAL\\IMP\\' + ARQ[tag][1],
            'saida': P + ARQ[tag][0] + '_GEO.dwg',
            'metodo': f'{len(g)} blocos de arquitetura de mesmo nome casados com o SIT R02 (pose da inserção); dispersão {disp*1000:.3f} mm',
            'blocos_exemplo': [c['nome'] for c in g[:12]],
            'local_para_SIT': {'rot_deg': rot, 't': [tx, ty]},
            'SIT_para_UTM': {'rot_deg': 0.0, 't': [float(t_sit[0]), float(t_sit[1])]},
            'rigid': {'rot_deg': 0.0, 't': [float(t_tot[0]), float(t_tot[1])],
                      'regra': 'UTM = p_local + t (rotação nula: os blocos casados têm rotação 0,0000000° em relação ao SIT)'},
            'conferencia_arquitetura_x_SIT': {'vertices_amostra': int(len(As)), 'pct_1mm': float(np.mean(da < 0.001) * 100),
                                             'pct_1cm': float(np.mean(da < 0.01) * 100)},
            'conferencia_topografia_embutida_x_TOP': topo,
            'extensao_rede_UTM': [float(Ar[:, 0].min()), float(Ar[:, 1].min()), float(Ar[:, 0].max()), float(Ar[:, 1].max())] if len(Ar) else None,
            'grupos_secundarios': [{'n': len(x), 'rot_deg': resumo(x)[0], 't': resumo(x)[1:3], 'blocos': [c['nome'] for c in x[:5]]} for x in grupos[1:4]],
        }
        pr(f'{tag}: local -> SIT t=({tx:.4f}, {ty:.4f}) rot {rot:+.7f}° [{len(g)} blocos, disp {disp*1000:.2f} mm]; '
           f'-> UTM t=({t_tot[0]:.4f}, {t_tot[1]:.4f}); arq×SIT <1 mm {np.mean(da<0.001)*100:.1f}% (<1 cm {np.mean(da<0.01)*100:.1f}%)'
           + (f'; topo embutida × TOP mediana {topo["mediana_mm"]:.0f} mm, Δ pela própria topo ({topo["delta_m"][0]:+.3f}, {topo["delta_m"][1]:+.3f}) m' if topo else ''))
        if len(grupos) > 1:
            pr(f'     grupos secundários: ' + '; '.join(f'n={len(x)} t=({resumo(x)[1]:.3f},{resumo(x)[2]:.3f}) ex. {x[0]["nome"][:30]}' for x in grupos[1:4]))

    # 3) JSON por disciplina
    hoje = datetime.date.today().isoformat()
    for tag, r in res.items():
        r.update({'escola': 'ETIB-CATU', 'data': hoje, 'sistema': 'SIRGAS 2000 / UTM 24S (MC 39° W) — o do levantamento TOP-001 (estações C1 e C2)',
                  'origem_revit_proposta': ORIGEM_REVIT})
        json.dump(r, open(os.path.join(OUT, f'transformacao_{tag}_local_para_UTM.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    base = {'escola': 'ETIB-CATU', 'data': hoje,
            'SIT_R02_para_UTM': {'rot_deg': 0.0, 't': [float(t_sit[0]), float(t_sit[1])],
                                 'metodo': f'bloco NOVA TOPOGRAFIA do SIT R02 × TOP-001 R00 ({n}/{len(A)} vértices, resíduo {rm*1000:.2f} mm)'},
            'alternativas_registradas': alt,
            'TOP_e_TER': 'já em UTM verdadeiro (estações C1 E 567744,9586 N 8634679,9890 e C2 E 567712,0314 N 8634683,6492 conferidas no DWG)',
            'origem_revit_proposta': ORIGEM_REVIT}
    json.dump(base, open(os.path.join(OUT, 'transformacao_SIT_para_UTM.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 4) listas de limpeza das cópias _REF (handles de nível superior)
    centro = {'SIT': np.array([567722.0, 8634370.0]), 'TOP': np.array([567722.0, 8634370.0]) + t_sit,
              'TER-IMP': np.array([567722.0, 8634370.0]) + t_sit}
    for tag in ['SIT', 'TOP', 'TER-IMP']:
        D = S if tag == 'SIT' else (T if tag == 'TOP' else ler(dxf(tag)))
        por_raiz = collections.defaultdict(list); info = {}
        for d in D:
            por_raiz[d['raiz']].append(d)
            if d['path'] == '' and d['raiz'] not in info:
                info[d['raiz']] = d
        apagar, explodir = [], []
        motivo = collections.Counter()
        for h, lst in por_raiz.items():
            d0 = info.get(h)
            if d0 is None: continue
            geo = [x['pts'][:, :2] for x in lst if x['tipo'] != 'INSERT']
            if not geo: continue
            Pg = np.vstack(geo); dist = np.hypot(*(Pg - centro[tag]).T)
            if np.all(dist > RAIO):
                apagar.append(h); motivo[('longe (carimbo/legenda)', d0['layer'])] += 1; continue
            if tag == 'SIT' and d0['layer'] in ('TOP-COTAS', 'CurvasTG') and np.median(Pg[:, 0]) > 567810:
                apagar.append(h); motivo[('cópia dos pontos cotados a leste', d0['layer'])] += 1; continue
            if d0['tipo'] == 'INSERT' and np.hypot(*(d0['pts'][0, :2] - centro[tag])) > RAIO and np.median(dist) < RAIO:
                explodir.append(h); motivo[('bloco com ponto base longe', d0['nome'])] += 1
        with open(os.path.join(WRK, f'ref_{tag}.txt'), 'w', encoding='ascii') as f:
            f.write(f'{centro[tag][0]:.4f} {centro[tag][1]:.4f} {RAIO:.1f}\n')
            for h in apagar: f.write(f'D {h}\n')
            for h in explodir: f.write(f'X {h}\n')
        pr(f'_REF {tag}: apagar {len(apagar)}, explodir {len(explodir)} — ' + '; '.join(f'{k[0]} [{k[1][:25]}] {v}' for k, v in motivo.most_common(12)))
    open(os.path.join(WRK, 'georef_catu_log.txt'), 'w', encoding='utf-8').write('\n'.join(log))
    return t_sit, res


if __name__ == '__main__':
    main()
