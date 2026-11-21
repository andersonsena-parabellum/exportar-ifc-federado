# -*- coding: utf-8 -*-
"""Jandaíra: leitura da geometria exportada por exportar_jan.py, no sistema INTERNO comum dos modelos JAN-* do Daniel
(origem interna = E 631578,10 / N 8721003,57 / cota 147,00, ângulo 0,5427 rad; ver *_meta.json).
Monta as listas SEG/MESH no formato do motor.py (Indice, avaliar_seg, avaliar_mesh) e o terreno do IMP.
Estruturas (EST_*): posicionadas pela transformação do vínculo nos modelos do Daniel (modo='daniel')
ou pelas coordenadas compartilhadas de cada arquivo (modo='compart')."""
import os, json, math, collections
import numpy as np

G = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo"
DISCS = ('AGF', 'ESG', 'DRE', 'ELE', 'PCI')


def meta(tag, g=None):
    g = g or G
    return json.load(open(os.path.join(g, tag + '_meta.json'), encoding='utf-8'))


def tf_compart(m):
    """compartilhado -> interno do arquivo (ProjectLocation.GetTotalTransform). Devolve (R 3x3, o)."""
    bx = np.array(m['tot']['bx']); by = np.array(m['tot']['by']); bz = np.cross(bx, by)
    return np.column_stack([bx, by, bz]), np.array(m['tot']['o'])


def tf_link(l):
    bx = np.array(l['bx'], float); bx /= np.linalg.norm(bx); by = np.array([-bx[1], bx[0], 0.0])
    return np.column_stack([bx, by, [0, 0, 1]]), np.array(l['o'], float)


def disc_seg(f, r):
    if f == 'AGF': return 'AF'
    if f == 'PCI': return 'SDAI' if r[2].startswith('Condu') else 'INC'
    return f


def disc_mesh(f, r):
    if f == 'AGF': return 'AF'
    if f == 'PCI':
        t = (r[3] + ' ' + r[4] + ' ' + r[5] + ' ' + r[6]).upper()
        return 'SDAI' if ('SDAI' in t or 'ALARME' in t or r[2].startswith('Condu') or 'Dispositivos de alarme' in r[2]) else 'INC'
    return f


def carregar(g=None, est='daniel', host='ELE', discs=DISCS):
    g = g or G
    SEG, MESH = [], []
    for f in discs:
        p = os.path.join(g, f + '_segs.tsv')
        if os.path.exists(p):
            for l in open(p, encoding='utf-8'):
                r = l.rstrip('\n').split('\t')
                if len(r) < 13: continue
                a = np.array(list(map(float, r[7:10]))); b = np.array(list(map(float, r[10:13])))
                if np.linalg.norm(b - a) < 1e-4: continue
                SEG.append(dict(k='S', disc=disc_seg(f, r), fonte=f, id=r[1], cat=r[2], tipo=r[3], sis=r[4], trecho=r[14] or r[4] or r[1], de=float(r[6]),
                                dn=r[13], desc=r[15] if len(r) > 15 else '', a=a, b=b, a0=a.copy(), b0=b.copy(), dz=0.0))
        p = os.path.join(g, f + '_mesh.tsv')
        if os.path.exists(p):
            for l in open(p, encoding='utf-8'):
                r = l.rstrip('\n').split('\t')
                if len(r) < 9 or not r[8]: continue
                v = np.array(r[8].split(','), dtype=float).reshape(-1, 3, 3)
                MESH.append(dict(k='M', disc=disc_mesh(f, r), fonte=f, id=r[1], cat=r[2], nome=r[3], trecho=r[4] or r[3], desc=r[5], tri=v,
                                 lo=v.reshape(-1, 3).min(0), hi=v.reshape(-1, 3).max(0), bloco=''))
    if est:
        MESH += carregar_est(g, est, host)
    return SEG, MESH


def mapa_links(host='ELE', g=None):
    g = g or G
    """nome do arquivo de estrutura -> transformação do vínculo no modelo do Daniel."""
    out = {}
    for l in meta(host, g)['links']:
        nome = l['nome'].split('.rvt')[0]
        out[nome] = tf_link(l)
    return out


def carregar_est(g=None, modo='daniel', host='ELE', zmax=None):
    g = g or G
    Rh, oh = tf_compart(meta(host, g))
    links = mapa_links(host, g)
    out = []
    for f in sorted(os.listdir(g)):
        if not (f.startswith('EST_') and f.endswith('_mesh.tsv')): continue
        tag = f[:-9]; m = meta(tag, g); nome = m['titulo'].split('__', 1)[-1]
        if modo == 'daniel':
            if nome not in links:
                # ECC/EMT não foram vinculados pelo Daniel; usam o mesmo sistema interno do FUN do bloco (pilares sobre as fundações: Δ ≤ 0,3 m)
                irmao = nome.replace('-ECC-', '-FUN-').replace('-EMT-', '-FUN-')
                if irmao not in links: continue
                R, o = links[irmao]
            else:
                R, o = links[nome]
        else:   # compartilhado: interno do arquivo -> compart -> interno do host
            Rl, ol = tf_compart(m)
            R = Rh @ Rl.T; o = oh - R @ ol
        bloco = tag.split('_')[1]
        for l in open(os.path.join(g, f), encoding='utf-8'):
            r = l.rstrip('\n').split('\t')
            if len(r) < 9 or not r[8]: continue
            v = np.array(r[8].split(','), dtype=float).reshape(-1, 3)
            v = (v @ R.T + o).reshape(-1, 3, 3)
            lo = v.reshape(-1, 3).min(0); hi = v.reshape(-1, 3).max(0)
            if zmax is not None and lo[2] > zmax: continue
            out.append(dict(k='M', disc='EST', fonte=tag, id=tag + ':' + r[1], cat=r[2], nome=r[3], trecho=bloco + ' ' + r[3].split(' : ')[0], desc=nome,
                            tri=v, lo=lo, hi=hi, bloco=bloco))
    return out


def para_compart(P, host='ELE', g=None):
    g = g or G
    """pontos internos (n,3) -> coordenadas compartilhadas (E, N, cota)."""
    R, o = tf_compart(meta(host, g))
    return (np.asarray(P) - o) @ R


class Terreno:
    """Superfície do terreno a partir das faces de topo do Toposolid/Topografia do IMP (malha), z(x,y) por grade."""
    def __init__(self, g=None, tag='IMP', cats=('topogr', 'Toposolid', 'Pisos'), passo=0.5):
        g = g or G; T = []
        for l in open(os.path.join(g, tag + '_mesh.tsv'), encoding='utf-8'):
            r = l.rstrip('\n').split('\t')
            if len(r) < 9 or not any(c.lower() in r[2].lower() for c in cats): continue
            v = np.array(r[8].split(','), dtype=float).reshape(-1, 3, 3)
            n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); nn = np.linalg.norm(n, axis=1) + 1e-12
            T.append(v[(n[:, 2] / nn) > 0.2])
        self.T = np.vstack(T) if T else np.zeros((0, 3, 3))
        self.lo = self.T.reshape(-1, 3).min(0) if len(self.T) else None
        self.hi = self.T.reshape(-1, 3).max(0) if len(self.T) else None
        self.passo = passo; self._grade()

    def _grade(self):
        if not len(self.T): self.Z = None; return
        p = self.passo; x0, y0 = self.lo[:2]; nx = int((self.hi[0] - x0) / p) + 2; ny = int((self.hi[1] - y0) / p) + 2
        Z = np.full((nx, ny), np.nan)
        for t in self.T:
            a, b, c = t; mn = np.minimum(np.minimum(a, b), c); mx = np.maximum(np.maximum(a, b), c)
            i0, i1 = int((mn[0] - x0) / p), int((mx[0] - x0) / p) + 1; j0, j1 = int((mn[1] - y0) / p), int((mx[1] - y0) / p) + 1
            xs = x0 + np.arange(i0, i1 + 1) * p; ys = y0 + np.arange(j0, j1 + 1) * p
            X, Y = np.meshgrid(xs, ys, indexing='ij')
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12: continue
            l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
            l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
            l3 = 1 - l1 - l2; m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            z = l1 * a[2] + l2 * b[2] + l3 * c[2]
            sub = Z[i0:i1 + 1, j0:j1 + 1]
            zz = z[:sub.shape[0], :sub.shape[1]]; mm = m[:sub.shape[0], :sub.shape[1]]
            sub[mm] = np.fmax(sub[mm], zz[mm])
        self.Z = Z; self.x0, self.y0 = x0, y0

    def z(self, x, y):
        if self.Z is None: return np.nan
        i = int(round((x - self.x0) / self.passo)); j = int(round((y - self.y0) / self.passo))
        if 0 <= i < self.Z.shape[0] and 0 <= j < self.Z.shape[1]: return self.Z[i, j]
        return np.nan


def agrupar_caixas(SEG, MESH, tol=0.05):
    """Junta as peças de uma mesma caixa/poço (DRE: tampa+alvenaria+revestimento; ESG: anel+tampa+laje...) num grupo
    e dá nome a ele: marca própria (PVE-xx, CX-F01...) ou o nó do tubo mais próximo (DRE: 'CX-38' do comentário 'CX-38 -> CX-39')."""
    import re
    rot = []   # pontas de tubo com nome de nó, por fonte
    for s in SEG:
        m = re.search(r'\|\s*([A-Z]+[\w.-]*)\s*->\s*([A-Z]+[\w.-]*)', s['desc'] or '')
        if m: rot += [(s['fonte'], m.group(1), s['a0']), (s['fonte'], m.group(2), s['b0'])]
    caixa = [M for M in MESH if M['disc'] != 'EST' and M['cat'] in ('Modelos genéricos', 'Peças hidrossanitárias', 'Equipamento elétrico')]
    pai = {id(M): id(M) for M in caixa}
    def raiz(k):
        while pai[k] != k: pai[k] = pai[pai[k]]; k = pai[k]
        return k
    for i, A in enumerate(caixa):
        for B in caixa[i + 1:]:
            if A['fonte'] != B['fonte']: continue
            if np.all(A['lo'][:2] - tol <= B['hi'][:2]) and np.all(B['lo'][:2] - tol <= A['hi'][:2]):
                pai[raiz(id(A))] = raiz(id(B))
    grupos = collections.defaultdict(list)
    for M in caixa: grupos[raiz(id(M))].append(M)
    for g in grupos.values():
        lo = np.min([M['lo'] for M in g], 0); hi = np.max([M['hi'] for M in g], 0); c = (lo + hi) / 2
        marca = next((M['trecho'] for M in g if M['trecho'] and M['trecho'] != M['nome'] and not M['trecho'].startswith(M['nome'][:10])), '')
        if not marca:
            cand = [(np.linalg.norm(p[:2] - c[:2]), n) for f, n, p in rot if f == g[0]['fonte']]
            if cand:
                d, n = min(cand)
                if d < max(1.0, np.linalg.norm(hi[:2] - lo[:2])): marca = n
        nome = marca or ('%s caixa (%.1f; %.1f)' % (g[0]['fonte'], c[0], c[1]))
        for M in g: M['grupo'] = nome; M['glo'] = lo; M['ghi'] = hi
    for M in MESH:
        M.setdefault('grupo', M['trecho'] if M['disc'] != 'EST' else M['trecho'])
    for s in SEG: s['grupo'] = s['trecho']
    return grupos
