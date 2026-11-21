# -*- coding: utf-8 -*-
"""BP4: o vínculo do BP4 no IMP as built está ~2,3 km fora da obra (o RVT não carrega na máquina). Posiciona as fundações
do BP4 por ajuste (só translação; a rotação 127,96° do vínculo é a mesma das outras edificações) dos pilares sobre as
linhas de arquitetura: busca em grade + ICP ponto-segmento. Grava imp/bp4_ajuste.json (dE, dN) para o est_sat.py."""
import os, sys, csv, json
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import sat_comum as sc               # noqa: E402
from esg_sat import arq_sit          # noqa: E402


class Grade:
    def __init__(self, S, cel=2.0):
        self.S = S; self.cel = cel; self.g = {}
        for i, (a, b) in enumerate(S):
            x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(np.floor(x0 / cel)), int(np.floor(x1 / cel)) + 1):
                for gy in range(int(np.floor(y0 / cel)), int(np.floor(y1 / cel)) + 1):
                    self.g.setdefault((gx, gy), []).append(i)

    def dist(self, P):
        out = np.full(len(P), 9.0)
        for k, p in enumerate(P):
            gx, gy = int(np.floor(p[0] / self.cel)), int(np.floor(p[1] / self.cel)); ids = set()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1): ids.update(self.g.get((gx + dx, gy + dy), ()))
            if not ids: continue
            S = self.S[list(ids)]; a = S[:, 0]; ab = S[:, 1] - a
            t = np.clip(((p - a) * ab).sum(1) / ((ab ** 2).sum(1) + 1e-12), 0, 1); q = a + ab * t[:, None]
            out[k] = np.hypot(*(q - p).T).min()
        return out


def base_in():
    E = sc.carrega('IN'); S = []
    for d in E:
        if d['tipo'] in ('PL', 'LINE') and 'ARQ' in d['layer'].upper() and sc.na_obra(d['pts']).all():
            p = d['pts'][:, :2]; S += [(p[i], p[i + 1]) for i in range(len(p) - 1)]
    return np.array(S)


def main():
    R = list(csv.DictReader(open(os.path.join(sc.REL, 'SAT_fase2_estrutura.csv'), encoding='utf-8-sig'), delimiter=';'))
    P = np.array([[float(r['E']), float(r['N'])] for r in R if r['bloco'] == 'BP4' and 'Pilar' in r['categoria']])
    print('pilares BP4', len(P))
    res = {}
    for nome, S in (('SIT', np.array(arq_sit())), ('IN (base ELE/PCI)', base_in())):
        G = Grade(S)
        # área das edificações no platô +236 (centro aproximado do BP4 pela SIT)
        alvo = np.array([545985.0, 8716205.0]); d0 = alvo - P.mean(0)
        best = None
        for dx in np.arange(-40, 40.1, 2.0):
            for dy in np.arange(-40, 40.1, 2.0):
                t = d0 + [dx, dy]; s = np.mean(np.minimum(G.dist(P[::4] + t), 2.0))
                if best is None or s < best[0]: best = (s, t)
        t = best[1]
        for passo in (0.5, 0.1, 0.02):
            for _ in range(30):
                cand = [(np.mean(np.minimum(G.dist(P + t + [ex, ey]), 1.0)), (ex, ey)) for ex in (-passo, 0, passo) for ey in (-passo, 0, passo)]
                s, (ex, ey) = min(cand)
                if ex == 0 and ey == 0: break
                t = t + [ex, ey]
        d = G.dist(P + t)
        res[nome] = {'dE': float(t[0]), 'dN': float(t[1]), 'mediana_m': float(np.median(d)), 'p90_m': float(np.percentile(d, 90))}
        print(nome, res[nome])
    melhor = min(res, key=lambda k: res[k]['mediana_m'])
    out = dict(res[melhor], base=melhor, todas=res, obs='translação aplicada às peças do BP4 (vínculo do IMP fora da obra)')
    json.dump(out, open(os.path.join(AQUI, 'bp4_ajuste.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('adotado', melhor, out['dE'], out['dN'])


if __name__ == '__main__':
    main()
