# -*- coding: utf-8 -*-
"""Passo 7 — prévias para conferir a olho e mandar no pacote (04_PREVIA): planta geral e por módulo (cor por disciplina),
vista 3D geral e vista 3D do maior módulo sem cobertura nem forro. Só conferência: não substitui abrir no Revit.
Precisa de memória (~7 GB num federado de 200 MB). A geometria fica em cache (<arquivo>.geom.pkl); depois de criar o cache o script se reinicia
sozinho para desenhar só a partir dele (o IFC aberto no mesmo processo estoura a memória na vista 3D).
Uso: python p7_previas.py escola.json saida/<SIGLA>_FEDERADO-UNICO_<REV>.ifc pasta_das_figuras"""
import os, sys, gc, pickle, collections, numpy as np, ifcopenshell, ifcopenshell.util.element as ue, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.patches as mp
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

COR_DISC = {'DRE': '#1f77b4', 'AP': '#1f77b4', 'ESG': '#8c564b', 'AF': '#17becf', 'AGF': '#17becf', 'ELE': '#ff7f0e', 'SDAI': '#d62728', 'HID': '#e377c2', 'PCI': '#e377c2', 'EST': '#555555', 'ARQ': '#c8a165'}

def geometria(fn):
    pk = fn + '.geom.pkl'
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(fn): return pickle.load(open(pk, 'rb'))
    f = ifcopenshell.open(fn); G = []
    for e, v, t in ef.formas(f):
        ps = ue.get_psets(e).get('Dados_ETIB', {})
        G.append((e.is_a(), e.Name or '', ps.get('modulo', 'SITE'), ps.get('disciplina', 'EST'), v.astype(np.float32), t.astype(np.int32)))
    pickle.dump(G, open(pk, 'wb')); return G

def cor3d(cls, nome, mod, disc):
    if cls == 'IfcGeographicElement': return ('#7fb069', 1) if 'lote' in nome else ('#cfcfc4', .35)
    if cls == 'IfcWindow': return '#8fbce6', 1
    if disc not in ('ARQ', 'EST', 'TER', '?') or cls in ('IfcPipeSegment', 'IfcPipeFitting', 'IfcCableSegment', 'IfcJunctionBox', 'IfcWasteTerminal'): return '#2b6cb0', 1
    if mod == 'URB': return '#b0aca4', 1
    if cls in ('IfcColumn', 'IfcBeam', 'IfcFooting') or disc == 'EST': return '#7a7a7a', 1
    if cls in ('IfcWall', 'IfcWallStandardCase', 'IfcCurtainWall'): return '#c08a50', 1
    if cls in ('IfcSlab', 'IfcCovering'): return '#eadfc8', 1
    return '#d8b98a', 1

def vista3d(G, nome, xl, yl, elev, azim, ocultar, titulo):
    sel = [g for g in G if not ocultar(g)]
    c = lambda g: g[4].mean(0)
    sel = [g for g in sel if xl[0] <= c(g)[0] <= xl[1] and yl[0] <= c(g)[1] <= yl[1]]
    if not sel: return
    z = np.concatenate([g[4][:, 2] for g in sel if g[0] != 'IfcGeographicElement'] or [np.array([0., 1.])]); zl = (float(np.percentile(z, 1)) - 3, float(z.max()) + 3)
    fg = plt.figure(figsize=(16, 10)); ax = fg.add_subplot(111, projection='3d', computed_zorder=False)
    el, az = np.radians(elev), np.radians(azim); vis = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    sel.sort(key=lambda g: (g[0] != 'IfcGeographicElement', float(c(g) @ vis)))   # terreno primeiro, depois do mais longe ao mais perto
    for cls, nm, mod, disc, v, t in sel:
        cc, a = cor3d(cls, nm, mod, disc); ax.add_collection3d(Poly3DCollection(v[t], facecolor=cc, edgecolor='none', alpha=a, linewidths=0))
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_zlim(*zl); ax.set_box_aspect((xl[1] - xl[0], yl[1] - yl[0], zl[1] - zl[0]))
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); plt.title(titulo); plt.tight_layout(); plt.savefig(nome, dpi=110); plt.close(fg); del sel, ax, fg; gc.collect(); print(nome)

def main(cfg, fn, pasta):
    os.makedirs(pasta, exist_ok=True); base = os.path.join(pasta, os.path.splitext(os.path.basename(fn))[0])
    if not (os.path.exists(fn + '.geom.pkl') and os.path.getmtime(fn + '.geom.pkl') > os.path.getmtime(fn)):
        geometria(fn); print('cache de geometria criado; reiniciando para desenhar', flush=True)
        os.execv(sys.executable, [sys.executable, '-u'] + sys.argv)
    G = geometria(fn); print('formas', len(G))
    caixa = collections.defaultdict(list)
    for cls, nm, mod, disc, v, t in G:
        if mod not in ('SITE', 'IMP', 'URB') and cls != 'IfcGeographicElement': caixa[mod].append(v[:, :2])
    caixa = {k: (np.vstack(v).min(0), np.vstack(v).max(0)) for k, v in caixa.items()}
    lote = [g for g in G if g[0] == 'IfcGeographicElement' and 'lote' in g[1]]
    L = np.vstack([g[4][:, :2] for g in lote]) if lote else np.vstack([b for a in caixa.values() for b in a])
    lo, hi = L.min(0) - 5, L.max(0) + 5
    # planta: geral + um quadro por módulo
    VIS = [('Planta geral', (lo[0], lo[1], hi[0], hi[1]))] + [(k, (a[0] - 6, a[1] - 6, b[0] + 6, b[1] + 6)) for k, (a, b) in sorted(caixa.items())]
    nc = 3; nl = int(np.ceil((len(VIS) + 1) / nc)); fig, axs = plt.subplots(nl, nc, figsize=(10 * nc, 10 * nl)); axs = np.ravel(axs)
    PL = sorted([(disc if disc in COR_DISC else 'ARQ' if disc == 'ARQ' else 'EST', v[t][:, :, :2], float(v[:, 2].max())) for cls, nm, mod, disc, v, t in G if cls != 'IfcGeographicElement'], key=lambda p: p[2])
    for a, (titulo, (x0, y0, x1, y1)) in zip(axs, VIS):
        for d, tri, _ in PL:
            c = tri.reshape(-1, 2).mean(0)
            if x0 - 5 < c[0] < x1 + 5 and y0 - 5 < c[1] < y1 + 5:
                a.add_collection(PolyCollection(tri, facecolors=COR_DISC.get(d, 'k'), edgecolors='none', alpha=0.5 if d in ('EST', 'ARQ') else 0.9))
        a.set_xlim(x0, x1); a.set_ylim(y0, y1); a.set_aspect('equal'); a.set_title(titulo, fontsize=16); a.grid(alpha=.2)
    for a in axs[len(VIS):]: a.axis('off')
    axs[-1].legend(handles=[mp.Patch(color=c, label=l) for l, c in [('Arquitetura', COR_DISC['ARQ']), ('Estrutura', COR_DISC['EST']), ('Drenagem/pluvial', COR_DISC['DRE']), ('Esgoto', COR_DISC['ESG']),
                   ('Água fria', COR_DISC['AF']), ('Elétrica', COR_DISC['ELE']), ('SDAI', COR_DISC['SDAI']), ('Hidrantes', COR_DISC['HID'])]], loc='center', fontsize=18)
    plt.tight_layout(); plt.savefig(base + '_planta.png', dpi=60); plt.close(fig); print(base + '_planta.png')
    del PL, fig, axs; gc.collect()
    # 3D geral (com cobertura) e o maior módulo sem cobertura/forro
    vista3d(G, base + '_3d_geral.png', (lo[0] - 10, hi[0] + 10), (lo[1] - 10, hi[1] + 10), 38, -120, lambda g: g[0] == 'IfcFooting',
            f"{cfg['escola']} — vista geral (terreno do lote em verde, arquitetura em bege, urbanização em cinza claro, redes em azul)")
    if caixa:
        k = max(caixa, key=lambda k: np.prod(caixa[k][1] - caixa[k][0])); (a, b) = caixa[k]
        zpiso = cfg['cota']['piso_max']
        ocultar = lambda g: g[0] in ('IfcFooting', 'IfcRoof', 'IfcCovering') or (g[0] == 'IfcGeographicElement' and 'lote' not in g[1]) or \
                            (g[2] == k and g[0] in ('IfcSlab', 'IfcMember', 'IfcPlate') and g[4][:, 2].min() > zpiso)
        vista3d(G, base + f'_3d_{k.lower()}.png', (a[0] - 6, b[0] + 6), (a[1] - 6, b[1] + 6), 45, -130, ocultar, f"{cfg['escola']} — {k} sem cobertura e sem forro")

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]), sys.argv[2], sys.argv[3])
