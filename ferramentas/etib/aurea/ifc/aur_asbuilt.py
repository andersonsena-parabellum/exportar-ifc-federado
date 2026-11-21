# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — redes da quadra JÁ EXECUTADAS, lidas do IFC as built do IMP (24-049-APR-CTO-ETIB-IMP-PE-001-MOD-R00.ifc,
que traz o modelo de instalações da quadra, QDC-PE-BIM-INST): drenagem (descidas, ramais, caixas de areia e coletor), aterramento do
SPDA (cabo de cobre nu e caixas de inspeção) e as subidas do hidrante (tubo de aço) e da elétrica (eletroduto) na quadra.
Coordenadas: as do IMP (sistema da SIT) -> UTM com o giro e o deslocamento da quadra (aur_terreno_imp.imp_utm) e a cota DZ_IMP.
Grava aurea/ifc/AUR_asbuilt_trechos.csv (eixo pelo eixo principal da malha) e AUR_asbuilt_caixas.csv (prisma da malha), e o mapa
AUR_asbuilt_mapa.png com o AF-002 por cima. Só o que está abaixo de 0,30 m acima do piso (o resto é cobertura e quadro).
Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_asbuilt.py"""
import csv, json, os, sys, collections
import numpy as np
import ifcopenshell, ifcopenshell.geom as G
import ifcopenshell.util.element as UE
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from aur_terreno_imp import imp_utm, DZ_IMP     # noqa: E402
from preclash.leitura_ifc import eixo_pca, retangulo_minimo     # noqa: E402

IFC = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\REFERENCIAS_RVT\IFC\24-049-APR-CTO-ETIB-IMP-PE-001-MOD-R00.ifc'
AQUI = os.path.dirname(os.path.abspath(__file__))
Z_MAX = 189.30          # cota do IMP (piso 189,00 + 0,30): acima disso é cobertura, pilar, quadro

# tipo (família do Revit) -> (disciplina, categoria)
TIPOS = [('Tubo PVC rígido Série R', ('DRE', 'tubo')), ('Tubo PVC ponta-bolsa', ('DRE', 'tubo')), ('Caixa de areia', ('DRE', 'caixa de areia')),
         ('Ralos pluviais', ('DRE', 'ralo')), ('Calha', ('DRE', 'calha')), ('Cabo de cobre', ('SPDA', 'cabo de cobre nu')),
         ('Caixa de inspeção', ('SPDA', 'caixa de inspeção')), ('Tubo aço carbono', ('HID', 'tubo de aço')),
         ('Eletroduto', ('ELE', 'eletroduto')), ('Alvenaria - piso', ('ELE', 'passagem no piso')), ('Hidrante', ('HID', 'hidrante'))]


def classe(tipo):
    for k, v in TIPOS:
        if k.lower() in (tipo or '').lower(): return v
    return None, None


def main():
    f = ifcopenshell.open(IFC); s = G.settings(); s.set(s.USE_WORLD_COORDS, True)
    T, C, ign = [], [], collections.Counter()
    vistos = set()
    for e in f.by_type('IfcProduct'):
        if not any(e.is_a(k) for k in ('IfcFlowSegment', 'IfcFlowTerminal', 'IfcFlowFitting', 'IfcFlowController', 'IfcDistributionFlowElement')): continue
        tp = UE.get_type(e); tipo = tp.Name if tp else (e.Name or '')
        disc, cat = classe(tipo)
        try: sh = G.create_shape(s, e)
        except Exception: ign['sem geometria'] += 1; continue
        V0 = np.array(sh.geometry.verts).reshape(-1, 3)
        if V0[:, 2].min() > Z_MAX: ign['acima do piso'] += 1; continue
        if disc is None: ign[f'{e.is_a()} {tipo}'] += 1; continue
        chave = (tipo, tuple(np.round(V0.mean(0), 2)))      # o IFC traz a quadra duas vezes (vínculo duplicado no IMP)
        if chave in vistos: ign['duplicado'] += 1; continue
        vistos.add(chave)
        V = imp_utm(V0); V[:, 2] += DZ_IMP
        if e.is_a('IfcFlowSegment'):
            P, de = eixo_pca(V)
            T.append(dict(id=f'AB-{len(T) + 1:03d}', guid=e.GlobalId, disc=disc, categoria=cat, tipo=tipo, de=round(float(de), 3),
                          E0=P[0][0], N0=P[0][1], z0=P[0][2], E1=P[-1][0], N1=P[-1][1], z1=P[-1][2]))
        elif e.is_a('IfcFlowFitting') and cat not in ('caixa de inspeção', 'passagem no piso'):
            ign[f'conexão {tipo}'] += 1
        else:
            cx, cy, lx, ly, rot, ac = retangulo_minimo(V[:, :2])
            C.append(dict(id=f'ABC-{len(C) + 1:03d}', guid=e.GlobalId, disc=disc, categoria=cat, tipo=tipo, E=cx, N=cy, lx=lx, ly=ly,
                          rot_graus=float(np.degrees(rot)), zb=float(V[:, 2].min()), zt=float(V[:, 2].max())))
    for nome, L in (('AUR_asbuilt_trechos.csv', T), ('AUR_asbuilt_caixas.csv', C)):
        with open(os.path.join(AQUI, nome), 'w', encoding='utf-8-sig', newline='') as fo:
            w = csv.DictWriter(fo, list(L[0].keys()), delimiter=';'); w.writeheader()
            for r in L: w.writerow({k: (f'{v:.3f}' if isinstance(v, float) else v) for k, v in r.items()})
    print('trechos', collections.Counter((r['disc'], r['categoria']) for r in T))
    print('caixas', collections.Counter((r['disc'], r['categoria']) for r in C))
    print('ignorados', dict(ign))
    mapa(T, C)


def mapa(T, C):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    F2 = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS\GEORREF_E_REDES_2026-10-18'
    fig, ax = plt.subplots(figsize=(13, 15))
    for r in csv.DictReader(open(os.path.join(F2, 'revit', 'dre_tubos_B.csv'), encoding='utf-8-sig'), delimiter=';'):
        ax.plot([float(r['x0_utm']), float(r['x1_utm'])], [float(r['y0_utm']), float(r['y1_utm'])], '-', color='0.7', lw=2)
    for r in csv.DictReader(open(os.path.join(F2, 'revit', 'dre_caixas_B.csv'), encoding='utf-8-sig'), delimiter=';'):
        ax.plot(float(r['x_utm']), float(r['y_utm']), 's', color='0.6', ms=8); ax.text(float(r['x_utm']), float(r['y_utm']), r['id'], fontsize=7, color='0.4')
    cor = {'DRE': 'b', 'SPDA': 'orange', 'HID': 'r', 'ELE': 'g'}
    for r in T:
        ax.plot([r['E0'], r['E1']], [r['N0'], r['N1']], '-', color=cor[r['disc']], lw=1)
        ax.text((r['E0'] + r['E1']) / 2, (r['N0'] + r['N1']) / 2, f"{min(r['z0'], r['z1']):.2f}", fontsize=5, color=cor[r['disc']])
    for r in C:
        ax.plot(r['E'], r['N'], 'o', color=cor[r['disc']], ms=4); ax.text(r['E'], r['N'], f" {r['categoria'][:6]} {r['zb']:.2f}", fontsize=5)
    est = json.load(open(os.path.join(AQUI, 'aur_estrutura.json'), encoding='utf-8'))['pecas']
    for p in est: ax.plot(p['x'], p['y'], 'ks', ms=5)
    ax.set_aspect('equal'); ax.grid(lw=0.3); ax.set_xlim(600030, 600090); ax.set_ylim(8711270, 8711405)
    fig.savefig(os.path.join(AQUI, 'AUR_asbuilt_mapa.png'), dpi=110)


if __name__ == '__main__':
    main()
