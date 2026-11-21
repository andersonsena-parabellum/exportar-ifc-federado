# -*- coding: utf-8 -*-
"""ETIB Catu — fundação e estrutura as built como obstáculo (disciplina EST) do preclash (19/10/2026).
Fonte: RVT FUN/ECC dos blocos em REFERENCIAS_RVT, lidos no Revit (fun_catu_ler.cs -> work/CATU/imp/fun_<BLOCO>-<FUN|ECC>.csv,
caixa envolvente em coordenadas internas do bloco) e posicionados pela transformação do vínculo no IMP (imp_vinculos.csv).
Cota: o IMP as built tem os platôs acima do terreno do projeto (até 5 m); para ficar coerente com as redes, o nível 0 de cada
bloco vai para o terreno do projeto no contorno do bloco (Δz por bloco, registrado). Só entra o que fica abaixo do piso
(+0,10 m): sapatas/blocos, arranques de pilar e vigas baldrame."""
import os, csv, glob, re
import numpy as np
from preclash import modelo as md

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp'


def _vinculos():
    V = {}
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_vinculos.csv'), encoding='utf-8'), delimiter=';'):
        o = np.array(list(map(float, r['origem'].split(',')))); bx = np.array(list(map(float, r['bx'].split(','))))
        V[r['tipo']] = (o, float(np.arctan2(bx[1], bx[0])))
    return V


def estrutura(ter):
    V = _vinculos(); C, reg = [], []
    por_bloco = {}
    for fn in sorted(glob.glob(os.path.join(IMP, 'fun_*-*.csv'))):
        if fn.endswith('_log.txt'): continue
        for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
            if r['arquivo'] not in V: continue
            por_bloco.setdefault(re.search(r'ETIB-([A-Z0-9]+)-PE', r['arquivo']).group(1), []).append(r)
    for bloco, R in por_bloco.items():
        els = []
        for r in R:
            o, th = V[r['arquivo']]; cs, sn = np.cos(th), np.sin(th)
            mn = np.array([float(r['bbminx']), float(r['bbminy']), float(r['bbminz'])]); mx = np.array([float(r['bbmaxx']), float(r['bbmaxy']), float(r['bbmaxz'])])
            c = (mn + mx) / 2; E = o[0] + cs * c[0] - sn * c[1]; N = o[1] + sn * c[0] + cs * c[1]
            els.append((r, E, N, mx[0] - mn[0], mx[1] - mn[1], th, o[2] + mn[2], o[2] + mx[2], o[2]))
        P = np.array([[e[1], e[2]] for e in els])
        zt = ter.z(P); z0 = els[0][8]
        dz = float(np.nanmedian(zt) - z0) if not np.isnan(zt).all() else 0.0
        n = 0
        for r, E, N, lx, ly, th, zb, ztop, zpiso in els:
            if zb > zpiso + 0.10: continue                                   # acima do piso: não interessa ao clash das redes externas
            zt2 = min(ztop, zpiso + 0.10)
            if lx < 0.05 or ly < 0.05 or zt2 - zb < 0.02: continue
            cat = r['categoria'].lower()
            cod = 'FUN' if 'funda' in cat else 'PIL' if 'pilar' in cat else 'VIG' if 'quadro' in cat else 'PAR' if 'parede' in cat else 'LAJ'
            C.append(md.caixa_retangular(f'EST:{bloco}:{cod}:{r["id"]}', 'EST', f'EST-{bloco}', E, N, lx, ly, th, zb + dz, zt2 + dz,
                                         nome=f'{bloco} {r["categoria"]} {r["id"]}', tipo=r['tipo'], familia=r['familia'], bloco=bloco,
                                         cota=f'as built do bloco, nível 0 no terreno do projeto (Δz {dz:+.2f} m sobre o IMP)'))
            n += 1
        reg.append((bloco, n, dz))
    return C, reg
