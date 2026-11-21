# -*- coding: utf-8 -*-
"""Pojuca — fundação e estrutura as built pela forma real (disciplina EST, obstáculo do clash e referência no IFC).
Fonte: os 16 RVT FUN/ECC/EMT dos blocos (BP2, CDG, CDR, GUA, QDC, SB5, TRT, VST) lidos no Revit em 22/10 pela forma real
(FERRAMENTAS/entrada/revit/estrutura_tri.cs -> georef/work/POJUCA/imp/est_<BLOCO>-<FUN|ECC|EMT>_tri.csv, triângulos em coordenadas
internas do arquivo). Os vínculos da Pojuca são aninhados (FUN/ECC dentro do ARQ, ARQ dentro do IMP) e o BP2 tem o vínculo do ARQ
fora do lugar, então a posição sai do imp_estrutura.csv de 19/10 (imp_pojuca_fundacoes_locais.cs: as mesmas peças já em UTM,
centro e giro da caixa): por arquivo, giro + translação em planta e Δz ajustados pelos centros das peças em comum (mínimos quadrados).
Só entra o que fica abaixo do piso do bloco (+0,10 sobre o nível 0): blocos/sapatas, vigas baldrame e o arranque dos pilares (a
malha é cortada no piso). Estacas saem (abaixo dos blocos, fora do alcance das redes).
Uso como módulo (estrutura(), contornos()) ou direto para conferir o ajuste."""
import csv, os
import numpy as np

IMP = r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\POJUCA\imp'
PISO = 0.10
BLOCOS = {'BP2': 'bloco pedagógico', 'CDG': 'casa de gás', 'CDR': 'casa de resíduos', 'GUA': 'guarita', 'QDC': 'quadra coberta',
          'SB5': 'subestação', 'TRT': 'teatro', 'VST': 'vestiários'}


def _arquivos():
    """{(bloco, tipo): nome do RVT} pelos arquivos lidos."""
    out = {}
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_estrutura.csv'), encoding='utf-8'), delimiter=';'):
        a = r['arquivo']; b = a.split('-ETIB-')[1].split('-')[0]; t = a.split('-PE-')[1].split('-')[0]
        out[(b, t)] = a
    return out


def _tri(bloco, tipo):
    fn = os.path.join(IMP, f'est_{bloco}-{tipo}_tri.csv')
    if not os.path.exists(fn): return {}
    pecas = {}
    for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
        T = [[float(r[k + c]) for c in 'xyz'] for k in 'abc']
        pecas.setdefault(r['id'], [r['categoria'], r['tipo'], []])[2].append(T)
    return {k: (c, t, np.array(v)) for k, (c, t, v) in pecas.items()}


_TR = {}


def transformacao(bloco, tipo, pecas):
    """local -> UTM: (th, t(2), dz, resíduo máx em planta, n peças)."""
    if (bloco, tipo) in _TR: return _TR[(bloco, tipo)]
    arq = _arquivos().get((bloco, tipo))
    ref = {}
    for r in csv.DictReader(open(os.path.join(IMP, 'imp_estrutura.csv'), encoding='utf-8'), delimiter=';'):
        if r['arquivo'] == arq: ref[r['id']] = (float(r['E']), float(r['N']), float(r['zb']), float(r['zt']))
    A, B, dz = [], [], []
    for pid, (cat, tp, T) in pecas.items():
        if pid not in ref: continue
        P = T.reshape(-1, 3); mn, mx = P.min(0), P.max(0)
        A.append(((mn + mx) / 2)[:2]); B.append(ref[pid][:2]); dz.append(ref[pid][2] - mn[2])
    A, B, dz = np.array(A), np.array(B), np.array(dz)
    ok = np.ones(len(A), bool)
    for _ in range(4):                       # peças cuja caixa no IMP não bate (viga inclinada, pilar repetido) saem do ajuste
        ca, cb = A[ok].mean(0), B[ok].mean(0)
        H = (A[ok] - ca).T @ (B[ok] - cb); U, S, Vt = np.linalg.svd(H); R = Vt.T @ U.T
        if np.linalg.det(R) < 0: Vt[-1] *= -1; R = Vt.T @ U.T
        t = cb - R @ ca; res = np.hypot(*((A @ R.T + t) - B).T)
        novo = res < max(0.05, 3 * np.median(res[ok]))
        if (novo == ok).all(): break
        ok = novo
    out = (float(np.arctan2(R[1, 0], R[0, 0])), t, float(np.median(dz[ok])), float(res[ok].max()), int(ok.sum()))
    if tipo != 'FUN' and out[3] > 0.10:      # o ECC/EMT usa as mesmas coordenadas do FUN do bloco (CDG, GUA, QDC...): fica a planta do FUN
        f = _tri(bloco, 'FUN')
        if f:
            th, tf = transformacao(bloco, 'FUN', f)[:2]; c, s = np.cos(th), np.sin(th); Rf = np.array([[c, -s], [s, c]])
            rf = np.hypot(*((A @ Rf.T + tf) - B).T); okf = rf < 0.10
            out = (th, tf, float(np.median(dz[okf])) if okf.any() else out[2], float(np.percentile(rf, 90)), int(okf.sum()))
    _TR[(bloco, tipo)] = out
    return out


def _utm(P, tr):
    th, t, dz = tr[:3]; c, s = np.cos(th), np.sin(th)
    return np.column_stack([t[0] + c * P[:, 0] - s * P[:, 1], t[1] + s * P[:, 0] + c * P[:, 1], P[:, 2] + dz])


def contornos():
    """face externa de cada bloco pela estrutura as built: fecho convexo da seção dos pilares e das fundações (UTM)."""
    from shapely.geometry import MultiPoint
    out = []
    for b in BLOCOS:
        P = []
        for tipo in ('FUN', 'ECC', 'EMT'):
            pec = _tri(b, tipo)
            if not pec: continue
            tr = transformacao(b, tipo, pec)
            for cat, tp, T in pec.values():
                if cat == 'pilar': P.append(_utm(T.reshape(-1, 3), tr)[:, :2])
        if P: out.append((BLOCOS[b], MultiPoint([tuple(q) for q in np.vstack(P)]).convex_hull))
    return out


def estrutura(log=print, md=None):
    if md is None:
        from preclash import modelo as md
    C = []; vistos = set()
    for b, nome in BLOCOS.items():
        n = 0
        for tipo in ('FUN', 'ECC', 'EMT'):
            pec = _tri(b, tipo)
            if not pec: continue
            tr = transformacao(b, tipo, pec)
            for pid, (cat, tp, T) in pec.items():
                if cat == 'laje/piso' or (b, pid) in vistos: continue
                if cat == 'fundacao' and tp.lower().startswith('diâmetro'): continue          # estaca
                if T[:, :, 2].min() >= PISO - 0.01: continue                                 # acima do piso
                vistos.add((b, pid))
                T = T.copy(); T[:, :, 2] = np.minimum(T[:, :, 2], PISO)
                M = _utm(T.reshape(-1, 3), tr).reshape(-1, 3, 3)
                mn, mx = M.reshape(-1, 3).min(0), M.reshape(-1, 3).max(0)
                if mx[2] - mn[2] < 0.02: continue
                Lp = T.reshape(-1, 3); lmn, lmx = Lp.min(0), Lp.max(0); c = _utm(((lmn + lmx) / 2)[None], tr)[0]
                cod = {'fundacao': 'FUN', 'pilar': 'PIL', 'viga': 'VIG'}.get(cat, cat[:3].upper())
                C.append(md.caixa_retangular(f'EST:{b}:{cod}:{pid}', 'EST', f'EST-{b}', c[0], c[1], lmx[0] - lmn[0], lmx[1] - lmn[1], tr[0],
                                             mn[2], mx[2], nome=f'{nome} {cat} {pid}', tipo=tp, bloco=b, equipamento=True,
                                             situacao='executado', malha=M,
                                             classe_ifc={'FUN': 'IfcFooting', 'PIL': 'IfcColumn', 'VIG': 'IfcBeam'}.get(cod, 'IfcBuildingElementProxy'),
                                             cota=f'as built do bloco ({nome}), posição pelo IMP as built'))
                n += 1
        log(f'  estrutura {b} ({nome}): {n} peças abaixo do piso')
    return C


if __name__ == '__main__':
    for b in BLOCOS:
        for tipo in ('FUN', 'ECC', 'EMT'):
            pec = _tri(b, tipo)
            if not pec: continue
            th, t, dz, res, n = transformacao(b, tipo, pec)
            print(f'{b}-{tipo}: {len(pec)} peças, {n} em comum, giro {np.degrees(th):.3f}°, t ({t[0]:.2f}, {t[1]:.2f}), dz {dz:.3f}, resíduo máx {res:.3f} m')
