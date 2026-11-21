# -*- coding: utf-8 -*-
"""ETIB Catu — superfície-alvo para renivelar o IMP as built na cota dos projetos de base (19/10/2026, pedido do Anderson).
Alvo = o terreno do projeto já usado nas redes (escolas/dados/catu_terreno.npz): CT das caixas ESG/DRE, níveis da SIT R02,
platôs do TER-IMP R00 (−1,92 m em E) e TOP-001 fora das áreas de projeto.
Grava em work/CATU/imp/:
  alvo_raster.txt   grade de 1 m do alvo (UTM, cota absoluta) para o C# renivelar os vértices dos Toposolids;
  ajuste_pisos.txt  PISO <id> <dz> e PAREDE <id> <dz> (m): cada piso/muro do IMP anda em bloco até o alvo (mediana);
  ajuste_previa.csv o que muda em cada elemento (antes, alvo, Δz).
Uso: .venv/Scripts/python.exe -X utf8 georef/imp_catu_alvo.py"""
import os, sys, csv, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno          # noqa: E402

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp'
TER = r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\catu_terreno.npz'
BOX = (567600.0, 8634520.0, 567820.0, 8634730.0)


def ler_tri(fn):
    g = collections.defaultdict(list)
    for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
        if float(r['nz']) <= 0.2: continue
        g[r['id']].extend(list(map(float, r[k].split(','))) for k in ('a', 'b', 'c'))
    return {k: np.array(v) for k, v in g.items()}


def main():
    ter = Terreno(TER)
    xs = np.arange(BOX[0], BOX[2] + 0.01, 1.0); ys = np.arange(BOX[1], BOX[3] + 0.01, 1.0)
    X, Y = np.meshgrid(xs, ys); Z = ter.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    with open(os.path.join(IMP, 'alvo_raster.txt'), 'w', encoding='ascii') as f:
        f.write(f'{xs[0]:.3f} {ys[0]:.3f} 1.0 {len(xs)} {len(ys)}\n')
        for row in Z: f.write(' '.join('nan' if np.isnan(z) else f'{z:.3f}' for z in row) + '\n')
    linhas, prev = [], []
    for tag, fn in (('PISO', 'imp_pisos.csv'), ('TOPO', 'imp_topo.csv')):
        for k, P in ler_tri(os.path.join(IMP, fn)).items():
            za = ter.z(P[:, :2]); ok = ~np.isnan(za)
            if not ok.any(): continue
            dz = float(np.median(za[ok] - P[ok, 2]))
            prev.append({'tipo': tag, 'id': k, 'z_imp_min': P[:, 2].min(), 'z_imp_max': P[:, 2].max(), 'z_alvo_med': float(np.median(za[ok])),
                         'dz_mediano': dz, 'dz_min': float((za[ok] - P[ok, 2]).min()), 'dz_max': float((za[ok] - P[ok, 2]).max()), 'pontos': int(ok.sum())})
            if tag == 'PISO': linhas.append(f'PISO {k} {dz:.4f}')
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_paredes.csv'), encoding='utf-8'), delimiter=';'):
        a = np.array(list(map(float, r['p0'].split(',')))); b = np.array(list(map(float, r['p1'].split(','))))
        Q = np.array([a + (b - a) * t for t in np.linspace(0, 1, 9)])
        za = ter.z(Q[:, :2]); ok = ~np.isnan(za)
        if not ok.any(): continue
        # muro: anda com o terreno do pé dele (base do muro no IMP = zmin)
        dz = float(np.median(za[ok]) - float(r['zmin']) - 0.0) if float(r['espessura']) >= 0.4 else float(np.median(za[ok] - Q[ok, 2]))
        linhas.append(f'PAREDE {r["id"]} {dz:.4f}')
        prev.append({'tipo': 'PAREDE', 'id': r['id'], 'z_imp_min': float(r['zmin']), 'z_imp_max': float(r['zmax']), 'z_alvo_med': float(np.median(za[ok])),
                     'dz_mediano': dz, 'dz_min': dz, 'dz_max': dz, 'pontos': int(ok.sum())})
    open(os.path.join(IMP, 'ajuste_pisos.txt'), 'w', encoding='ascii').write('\n'.join(linhas) + '\n')
    with open(os.path.join(IMP, 'ajuste_previa.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(prev[0].keys()), delimiter=';'); w.writeheader()
        for p in prev: w.writerow({k: (f'{v:.3f}'.replace('.', ',') if isinstance(v, float) else v) for k, v in p.items()})
    for p in prev: print(p['tipo'], p['id'], f"IMP {p['z_imp_min']:.2f}-{p['z_imp_max']:.2f} -> alvo {p['z_alvo_med']:.2f}  dz {p['dz_mediano']:+.2f} ({p['dz_min']:+.2f}..{p['dz_max']:+.2f})")


if __name__ == '__main__':
    main()
