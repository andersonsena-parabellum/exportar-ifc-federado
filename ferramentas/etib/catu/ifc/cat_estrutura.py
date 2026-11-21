# -*- coding: utf-8 -*-
"""Catu — fundação e estrutura as built pela forma real (disciplina EST, obstáculo do clash e referência no IFC).
Fonte: os 10 RVT FUN/ECC dos blocos novos (restaurante RST, casa de gás CDG, casa de resíduos CDR, guarita GUA, subestação SB5) lidos
no Revit em 22/10 pela forma real (FERRAMENTAS/entrada/revit/estrutura_tri.cs -> georef/work/CATU/imp/est_<BLOCO>-<FUN|ECC>_tri.csv,
triângulos em coordenadas internas do bloco), postos em UTM pela transformação do vínculo no IMP (imp_vinculos.csv).
Cota: no IMP o piso de cada bloco (nível 0 + 0,10) fica no topo do platô; com o terreno levado às cotas da base (decisão C1) o piso
vai para o terreno de entrega no centro do bloco: Δz = terreno de entrega − (nível 0 do vínculo + 0,10).
Só entra o que fica abaixo do piso (+0,10): blocos/sapatas, vigas baldrame e o arranque dos pilares (a malha é cortada no piso).
Os blocos de salas, o teatro e os vestiários são existentes/reforma e não têm RVT de estrutura."""
import csv, os, re
import numpy as np
from preclash import modelo as md

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp'
PISO = 0.10
NOMES = {'RST': 'restaurante', 'CDG': 'abrigo CDG', 'CDR': 'casa de resíduos', 'GUA': 'guarita', 'SB5': 'subestação'}


def _vinculos():
    V = {}
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_vinculos.csv'), encoding='utf-8'), delimiter=';'):
        o = np.array(list(map(float, r['origem'].split(',')))); bx = np.array(list(map(float, r['bx'].split(','))))
        V[r['tipo']] = (o, float(np.arctan2(bx[1], bx[0])))
    return V


def _arquivo(bloco, tipo, V):
    return next(k for k in V if f'ETIB-{bloco}-PE-{tipo}-001' in k or (bloco == 'RST' and f'ETIB-RST-PE-{tipo}-001' in k))


def contornos():
    """face externa dos blocos novos pela estrutura as built: fecho convexo da seção dos pilares (face do pilar = face da parede),
    em planta (UTM). Vai junto com o contorno da SIT na regra "só rede externa"."""
    from shapely.geometry import MultiPoint
    V = _vinculos(); out = []
    for bloco in ('RST', 'CDG', 'CDR', 'GUA', 'SB5'):
        fn = os.path.join(IMP, f'est_{bloco}-FUN_tri.csv')
        if not os.path.exists(fn): continue
        o, th = V[_arquivo(bloco, 'FUN', V)]; cs, sn = np.cos(th), np.sin(th)
        P = [(float(r[k + 'x']), float(r[k + 'y'])) for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';')
             if r['categoria'] == 'pilar' for k in 'abc']
        if not P: continue
        P = np.array(P); Q = np.column_stack([o[0] + cs * P[:, 0] - sn * P[:, 1], o[1] + sn * P[:, 0] + cs * P[:, 1]])
        out.append((NOMES[bloco], MultiPoint([tuple(q) for q in Q]).convex_hull))
    return out


def estrutura(ter_entrega, ter_imp, log=print):
    V = _vinculos(); C = []; vistos = {}
    for bloco in ('RST', 'CDG', 'CDR', 'GUA', 'SB5'):
        pecas = {}
        for tipo in ('FUN', 'ECC'):
            fn = os.path.join(IMP, f'est_{bloco}-{tipo}_tri.csv')
            if not os.path.exists(fn): continue
            o, th = V[_arquivo(bloco, tipo, V)]
            for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
                if r['categoria'] == 'laje/piso': continue
                if vistos.setdefault((bloco, r['id']), tipo) != tipo: continue          # pilar repetido no FUN e no ECC
                T = np.array([[float(r[k + c]) for c in 'xyz'] for k in 'abc'])
                pecas.setdefault(r['id'], [r['categoria'], r['tipo'], o, th, []])[4].append(T)
        if not pecas: continue
        o, th = next(iter(pecas.values()))[2:4]
        cs, sn = np.cos(th), np.sin(th)
        utm = lambda P, o=o: np.column_stack([o[0] + cs * P[:, 0] - sn * P[:, 1], o[1] + sn * P[:, 0] + cs * P[:, 1], o[2] + P[:, 2]])
        cen = utm(np.vstack([np.vstack(v[4]).reshape(-1, 3) for v in pecas.values()]).mean(0)[None])[0]
        dz = float(ter_entrega.z([cen[:2]])[0] - (o[2] + PISO))
        if not np.isfinite(dz): dz = 0.0
        n = 0
        for pid, (cat, tp, o_, th_, Ts) in pecas.items():
            T = np.array(Ts)
            if T[:, :, 2].min() >= PISO - 0.01: continue                      # acima do piso: não interessa às redes externas
            T[:, :, 2] = np.minimum(T[:, :, 2], PISO)                          # corta o pilar no piso
            mn, mx = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
            if mx[2] - mn[2] < 0.02: continue
            c = utm(((mn + mx) / 2)[None])[0]
            M = utm(T.reshape(-1, 3)).reshape(-1, 3, 3); M[:, :, 2] += dz
            cod = {'fundacao': 'FUN', 'pilar': 'PIL', 'viga': 'VIG'}.get(cat, cat[:3].upper())
            C.append(md.caixa_retangular(f'EST:{bloco}:{cod}:{pid}', 'EST', f'EST-{bloco}', c[0], c[1], mx[0] - mn[0], mx[1] - mn[1], th,
                                         o[2] + mn[2] + dz, o[2] + mx[2] + dz, nome=f'{NOMES[bloco]} {cat} {pid}', tipo=tp, bloco=bloco,
                                         equipamento=True, situacao='executado', malha=M,
                                         classe_ifc={'FUN': 'IfcFooting', 'PIL': 'IfcColumn', 'VIG': 'IfcBeam'}.get(cod, 'IfcBuildingElementProxy'),
                                         cota=f'as built do bloco ({NOMES[bloco]}), nível 0 com o platô do terreno de entrega (Δz {dz:+.2f} m sobre o IMP)'))
            n += 1
        log(f'  estrutura {bloco} ({NOMES[bloco]}): {n} peças abaixo do piso, Δz {dz:+.2f} m')
    return C
