"""work/modelo_<TAG>.json -> work/revit_conduits.tsv e work/revit_caixas.tsv (entrada do C# de criação no Revit). Unidades: m."""
import json
W = 'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
DWG = {'EL1': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R07', 'EL2': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R05',
       'CF1': '24-049-ALH-SLJ-ETIB-IMP-PE-CF-001-ELG-R05', 'CF2': '24-049-ALH-SLJ-ETIB-IMP-PE-CF-002-ELG-R04'}
cl = lambda s: str(s).replace('\t', ' ').replace('\n', ' ').strip()
with open(W + 'revit_conduits.tsv', 'w', encoding='utf-8') as f, open(W + 'revit_caixas.tsv', 'w', encoding='utf-8') as g:
    n = m = 0
    for tag in ['EL1', 'EL2', 'CF1', 'CF2']:
        M = json.load(open(W + f'modelo_{tag}.json'))
        for c in M['conduits']:
            de = c['de_mm'] / 1000
            for k, s in enumerate(c['segs']):
                a, b = s['a'], s['b']
                f.write('\t'.join(cl(x) for x in [tag, c['trecho'], k + 1, c['tipo'], f"{c['nominal_pol'] / 12:.10f}",
                        f'{a[0]:.4f}', f'{a[1]:.4f}', f'{a[2]:.4f}', f'{b[0]:.4f}', f'{b[1]:.4f}', f'{b[2]:.4f}',
                        c['disc'], c['desc'], c['coment'] or '-', f"{s['cov_min']:.3f}", f"{c['cov_req']:.2f}",
                        f'{a[2] + de / 2:.3f}', f'{b[2] + de / 2:.3f}', f"{s['terr_a']:.3f}", f"{s['terr_b']:.3f}",
                        c['origem'], c['obs'] or '-', c['ini'], c['fim']]) + '\n'); n += 1
        for b in M['boxes']:
            g.write('\t'.join(cl(x) for x in [tag, b['id'], f"{b['c'][0]:.4f}", f"{b['c'][1]:.4f}", b['dim'][0], b['dim'][1], f"{b['ang']:.6f}",
                    f"{b['ct']:.3f}", f"{b['cf']:.3f}", f"{b['prof']:.3f}", b['fonte'], b['n'], b['obs'] or '-', M['rede'], DWG[tag]]) + '\n'); m += 1
print('segmentos', n, 'caixas', m)
