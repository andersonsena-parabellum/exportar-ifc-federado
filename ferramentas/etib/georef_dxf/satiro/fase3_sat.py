# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — fase 3 (cotas) sem Revit, sobre um TERRENO PROVISÓRIO:
  platôs da terraplanagem (TER-001-PLT R00: +236,00 e +233,00, polígonos Q-PLATO) e, fora deles, o terreno existente
  (pontos e curvas da topografia TOP-001 e do DRE-002), com a borda dos platôs entrando na triangulação (taludes).
Redes que seguem o terreno (AF, PCI hidrante, SDAI, elétrica): algoritmo da skill (amostra 0,5 m, Douglas-Peucker 0,20 m / 2 m,
abaixa os nós até o recobrimento mínimo; nó compartilhado fica com a cota mais baixa).
Redes por gravidade (esgoto, pluvial, campo, galeria): cotas do projeto; aqui só a checagem contra o terreno provisório.
O terreno definitivo é o do IMP as built (Revit): refazer a fase 3 sobre ele quando o Revit estiver livre.
Uso: python -I -X utf8 fase3_sat.py
"""
import sys, os, re, csv, json, math, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from esg_sat import arq_sit

REL3 = sc.REL.replace('FASE2_REDES', 'FASE3_COTAS')
os.makedirs(REL3, exist_ok=True)
W = sc.WRK
ld = lambda n: json.load(open(os.path.join(W, n), encoding='utf-8'))

# ---------------------------------------------------------------- premissas
COBR = {'AF': 0.30, 'HID': 0.50, 'SDAI': 0.50, 'ELE': 0.70}
FONTE = {'AF': 'premissa de modelagem (o projeto não dá cota): 0,30 m sob passeio/grama',
         'HID': 'nota 5 do PCI: termoplásticos enterrados a 0,50 m', 'SDAI': 'nota 5 do PCI (eletroduto PEAD): 0,50 m',
         'ELE': 'NBR 5410, decisão da ETIB Alagoinhas: 0,70 m (1,00 m sob veículos)'}
DE_PVC = {20: 20, 25: 25, 32: 32, 40: 40, 50: 50, 60: 60, 75: 75, 85: 85, 110: 110}
DE_POL = {'3/4"': 25, '1"': 33, '1.1/4"': 42, '1/1.4"': 42, '1.1/2"': 48, '2"': 60, '2.1/2"': 75, '3"': 90, '4"': 110, '5"': 140, 'ø80': 90, 'ø75': 75}


def poli(p, poly):
    x, y = p[..., 0], p[..., 1]; xs, ys = poly[:, 0], poly[:, 1]; res = np.zeros(x.shape, bool); j = len(poly) - 1
    for i in range(len(poly)):
        c = ((ys[i] > y) != (ys[j] > y)) & (x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i] + 1e-300) + xs[i]); res ^= c; j = i
    return res


class Terreno:
    def __init__(self):
        T = sc.carrega('TER')
        pl = [d for d in T if d['layer'] == 'Q-PLATO' and d['tipo'] == 'PL' and d.get('fechada') and len(d['pts']) >= 4]
        tx = [d for d in T if d['tipo'] == 'TEXT' and d['layer'] == 'Elevações de ponto']
        self.plat = []
        for d in pl:
            P = d['pts'][:, :2]
            dentro = [sc.num(t['texto']) for t in tx if poli(t['pts'][0, :2], P)]
            if dentro: self.plat.append((P, float(np.median(dentro))))
        print('platôs:', [(round(z, 2), round(0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], 1)) - np.dot(P[:, 1], np.roll(P[:, 0], 1))))) for P, z in self.plat])
        pts = []
        for tag in ('TOP', 'DRE2'):
            E = sc.carrega(tag)
            for d in E:
                if not sc.na_obra(d['pts'], (545700, 8715950, 546250, 8716400)).all(): continue
                if d['tipo'] == 'POINT' and d['pts'][0, 2] > 200: pts.append(d['pts'][0])
                if d['tipo'] in ('PL', 'LINE') and d['layer'] in ('CURVAS', 'CurvasTG', 'T-HM-CURVA_MESTRA', 'T-HM-CURVA_INTERMEDIARIA') and d['pts'][0, 2] > 200:
                    pts.extend(d['pts'][::2])
        X = np.array(pts)
        fora = np.ones(len(X), bool)
        # faixa entre os platôs (vale natural da "faixa non aedificandi"): sai o terreno existente, vale o talude
        # interpolado entre as bordas dos platôs (premissa até termos o terreno final do IMP)
        V = np.vstack([P for P, z in self.plat]); hull = self._casca(V)
        fora &= ~poli(X[:, :2], hull)
        for P, z in self.plat:
            # existentes até 2 m dentro/fora da borda saem (talude começa na borda do platô)
            fora &= ~poli(X[:, :2], P)
            seg_d = np.min([np.hypot(*(X[:, :2] - q).T) for q in self._dens(P, 2.0)], axis=0)
            fora &= seg_d > 2.0
        bord = np.vstack([np.column_stack([self._dens(P, 1.0), np.full(len(self._dens(P, 1.0)), z)]) for P, z in self.plat])
        Y = np.vstack([X[fora], bord])
        Y = Y[np.unique(np.round(Y[:, :2], 2), axis=0, return_index=True)[1]]
        self.tri = mtri.Triangulation(Y[:, 0], Y[:, 1])
        self.f = mtri.LinearTriInterpolator(self.tri, Y[:, 2])
        self.Y = Y
        print('pontos do terreno existente usados:', int(fora.sum()), '| borda dos platôs:', len(bord))

    @staticmethod
    def _casca(P):
        P = sorted(map(tuple, np.round(P, 4)))
        cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lo, hi = [], []
        for p in P:
            while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
            lo.append(p)
        for p in reversed(P):
            while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
            hi.append(p)
        return np.array(lo[:-1] + hi[:-1])

    @staticmethod
    def _dens(P, passo):
        Q = np.vstack([P, P[:1]]); out = []
        for a, b in zip(Q[:-1], Q[1:]):
            k = max(1, int(np.linalg.norm(b - a) / passo))
            out.extend(a + (b - a) * t for t in np.arange(k) / k)
        return np.array(out)

    def z(self, p):
        p = np.atleast_2d(p)[:, :2]
        z = np.array(self.f(p[:, 0], p[:, 1]).filled(np.nan), float)
        for P, zp in self.plat:
            z[poli(p, P)] = zp
        return z


class TerrenoIMP:
    """Terreno acabado do IMP as built (lido no Revit em 19/10/2026; imp/imp_terreno.py -> imp/imp_raster_1m.npz):
    pisos +233/+236 > subdivisões > platôs > terreno. Mesma interface do Terreno provisório (z, plat, Y, tri)."""
    fonte = 'IMP as built (sólidos topográficos + pisos do Revit), grade de 1 m'

    def __init__(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imp'))
        import imp_terreno as itr
        D = np.load(itr.OUT); X, Y, Z = D['X'], D['Y'], D['Z']
        self.f = itr.interp(itr.OUT)
        self.plat = []
        idx = -np.ones(Z.shape, int); ok = ~np.isnan(Z); idx[ok] = np.arange(ok.sum())
        self.Y = np.column_stack([X[ok], Y[ok], Z[ok]])
        a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
        t1 = np.column_stack([a.ravel(), b.ravel(), c.ravel()]); t2 = np.column_stack([a.ravel(), c.ravel(), d.ravel()])
        T = np.vstack([t1, t2]); T = T[(T >= 0).all(1)]
        self.tri = mtri.Triangulation(self.Y[:, 0], self.Y[:, 1], T)
        print('terreno do IMP:', len(self.Y), 'pontos,', len(T), 'triângulos')

    def z(self, p):
        return self.f(np.atleast_2d(p)[:, :2])


def de_de(sis, rot):
    if sis == 'AF':
        try: return DE_PVC.get(int(float(rot)), float(rot))
        except (TypeError, ValueError): return 32.0
    for k, v in DE_POL.items():
        if k in (rot or ''): return float(v)
    return {'HID': 75.0, 'SDAI': 33.0, 'ELE': 60.0}[sis]


def pressurizadas(ter):
    redes = []
    af = ld('af_rede.json')
    for t in af['trechos']: redes.append(('AF', t['trecho'], t['rede'], t['pts'], de_de('AF', t.get('DN_adotado'))))
    pci = ld('pci_rede.json')
    for sis in ('HID', 'SDAI'):
        for t in pci[sis]['trechos']: redes.append((sis, t['trecho'], 'hidrante PEAD' if sis == 'HID' else 'SDAI', t['pts'], de_de(sis, t.get('rotulo'))))
    ele = ld('ele_rede.json')
    for k in ('EL1', 'EL2', 'CPS_EL1'):
        for t in ele[k]['trechos']: redes.append(('ELE', t['trecho'], t['folha'], t['pts'], de_de('ELE', t.get('diametro'))))
    key = lambda p: (round(float(p[0]), 2), round(float(p[1]), 2))
    zreq_no = {}
    pernas = []
    for sis, nome, rede, pts, de in redes:
        cob = COBR[sis]
        P = [np.asarray(p[:2], float) for p in pts]
        # amostras ao longo do trecho
        S, Q = [0.0], [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            L = np.linalg.norm(b - a); k = max(1, int(L / 0.5))
            for j in range(1, k + 1): Q.append(a + (b - a) * j / k); S.append(S[-1] + L / k)
        S = np.array(S); Q = np.array(Q)
        zt = ter.z(Q)
        if np.isnan(zt).any(): zt = np.where(np.isnan(zt), np.nanmin(zt), zt)
        zr = zt - cob - de / 2000.0           # cota máxima do eixo
        # Douglas-Peucker sobre o perfil exigido (desvio 0,20 m, trecho mínimo 2 m) + vértices do traçado
        quebras = {0, len(S) - 1}
        vert = {int(np.argmin(np.abs(S - s))) for s in np.cumsum([0] + [np.linalg.norm(b - a) for a, b in zip(P[:-1], P[1:])])}
        quebras |= vert
        def dp(i0, i1):
            if i1 <= i0 + 1: return
            line = zr[i0] + (zr[i1] - zr[i0]) * (S[i0 + 1:i1] - S[i0]) / (S[i1] - S[i0] + 1e-12)
            dev = line - zr[i0 + 1:i1]; k = int(np.argmax(dev)) + i0 + 1
            if dev.max() > 0.20 and S[k] - S[i0] >= 2.0 and S[i1] - S[k] >= 2.0:
                quebras.add(k); dp(i0, k); dp(k, i1)
        qs = sorted(quebras)
        for i0, i1 in zip(qs[:-1], qs[1:]): dp(i0, i1)
        qs = sorted(quebras)
        z_no = {i: zr[i] for i in qs}
        # abaixa até nenhum ponto intermediário ficar acima do exigido
        for _ in range(50):
            ok = True
            for i0, i1 in zip(qs[:-1], qs[1:]):
                if i1 - i0 < 2: continue
                line = z_no[i0] + (z_no[i1] - z_no[i0]) * (S[i0:i1 + 1] - S[i0]) / (S[i1] - S[i0] + 1e-12)
                exc = line - zr[i0:i1 + 1]
                if exc.max() > 0.001:
                    z_no[i0] -= exc.max(); z_no[i1] -= exc.max(); ok = False
            if ok: break
        for i in (qs[0], qs[-1]):
            k_ = key(Q[i]); zreq_no[k_] = min(zreq_no.get(k_, 9e9), z_no[i])
        pernas.append({'sis': sis, 'trecho': nome, 'rede': rede, 'de': de, 'cob': cob, 'S': S, 'Q': Q, 'zt': zt, 'qs': qs, 'z_no': z_no})
    # nós compartilhados: a cota mais baixa vale para todos os trechos que chegam ali
    linhas = []
    for pe in pernas:
        qs, z_no, Q = pe['qs'], pe['z_no'], pe['Q']
        for i in (qs[0], qs[-1]):
            z_no[i] = min(z_no[i], zreq_no[key(Q[i])])
        for n_, (i0, i1) in enumerate(zip(qs[:-1], qs[1:])):
            line = z_no[i0] + (z_no[i1] - z_no[i0]) * (pe['S'][i0:i1 + 1] - pe['S'][i0]) / (pe['S'][i1] - pe['S'][i0] + 1e-12)
            cob_real = pe['zt'][i0:i1 + 1] - (line + pe['de'] / 2000.0)
            L = pe['S'][i1] - pe['S'][i0]
            linhas.append({'sistema': pe['sis'], 'trecho': pe['trecho'], 'perna': n_ + 1, 'rede': pe['rede'], 'DE_mm': pe['de'], 'L_m': round(L, 2),
                           'E_ini': round(float(Q[i0][0]), 3), 'N_ini': round(float(Q[i0][1]), 3), 'E_fim': round(float(Q[i1][0]), 3), 'N_fim': round(float(Q[i1][1]), 3),
                           'terreno_ini': round(float(pe['zt'][i0]), 3), 'terreno_fim': round(float(pe['zt'][i1]), 3),
                           'eixo_ini': round(float(z_no[i0]), 3), 'eixo_fim': round(float(z_no[i1]), 3),
                           'inclinacao_pct': round(float((z_no[i1] - z_no[i0]) / L * 100), 2) if L > 0 else 0,
                           'recobrimento_exigido': pe['cob'], 'recobrimento_min_real': round(float(cob_real.min()), 3),
                           'recobrimento_max_real': round(float(cob_real.max()), 3)})
    cols = list(linhas[0].keys())
    with open(os.path.join(REL3, 'SAT_fase3_pressurizadas_cotas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows(linhas)
    return linhas


def gravidade(ter):
    out = []
    for arq, rede in (('esg_rede.json', 'ESG'), ('ap_rede.json', 'AP'), ('cps_dre_rede.json', 'CPS-DRE')):
        J = ld(arq)
        cx = {c['id']: c for c in J.get('caixas', J.get('nos', []))}
        for t in J['trechos']:
            if t.get('classe', '').startswith('calha'): continue
            a, b = np.asarray(t['pts'][0][:2]), np.asarray(t['pts'][-1][:2])
            za, zb = ter.z(np.vstack([a, b]))
            dn = float(t['DN_mm'] or 100) / 1000
            cfa, cfb = t.get('CF_montante'), t.get('CF_jusante')
            obs = []
            # topo do tubo nas pontas (geratriz inferior = CF da caixa; sem CF, usa a declividade do rótulo a partir da ponta com CF)
            i = (t.get('i_rotulo_pct') or 1.0) / 100.0
            est = ''
            if cfa is None and cfb is not None: cfa = cfb + i * t['L_m']; est = 'montante'
            if cfb is None and cfa is not None: cfb = cfa - i * t['L_m']; est = 'jusante'
            ra = rb = None
            if cfa is not None: ra = za - (cfa + dn)
            if cfb is not None: rb = zb - (cfb + dn)
            for r_, lado in ((ra, 'montante'), (rb, 'jusante')):
                if r_ is not None and r_ < 0: obs.append(f'tubo acima do terreno no {lado} ({r_:.2f} m)')
                elif r_ is not None and r_ < 0.30: obs.append(f'recobrimento baixo no {lado} ({r_:.2f} m)')
            out.append({'rede': rede, 'trecho': t['trecho'], 'de': t['de'], 'para': t['para'], 'L_m': t['L_m'], 'DN_mm': t['DN_mm'],
                        'terreno_mont': round(float(za), 3), 'terreno_jus': round(float(zb), 3),
                        'GI_mont': round(cfa, 3) if cfa is not None else None, 'GI_jus': round(cfb, 3) if cfb is not None else None,
                        'recobrimento_mont': round(float(ra), 3) if ra is not None else None, 'recobrimento_jus': round(float(rb), 3) if rb is not None else None,
                        'i_rotulo_pct': t.get('i_rotulo_pct'), 'i_pelas_CF_pct': t.get('i_pelas_CF_pct'), 'GI_estimado_pela_declividade': est,
                        'obs_fase2': t.get('obs', ''), 'obs_fase3': ' | '.join(obs)})
    dre = ld('dre_rede.json')
    for t in dre['trechos']:
        a, b = np.asarray(t['pts'][0]), np.asarray(t['pts'][1])
        ss = np.linspace(0, 1, 126); Q = a + (b - a) * ss[:, None]; zt = ter.z(Q)
        gi = t['GI_montante'] + (t['GI_jusante'] - t['GI_montante']) * ss
        cob = zt - (gi + 1.2 + 0.10)                 # parede de ~10 cm (premissa)
        L = t['L_m']; meio = (ss * L > 5) & (ss * L < L - 5)
        obs = [f'soleira {t["GI_montante"] - zt[0]:+.2f} m em relação ao terreno na entrada (montante)',
               f'soleira {t["GI_jusante"] - zt[-1]:+.2f} m em relação ao terreno na saída (jusante)',
               f'recobrimento no corpo (fora 5 m das pontas): {cob[meio].min():.2f} a {cob[meio].max():.2f} m']
        if cob[meio].min() < 0.60: obs.append('recobrimento < 0,60 m no corpo da galeria')
        out.append({'rede': 'DRE galeria', 'trecho': t['trecho'], 'de': 'GI %.2f' % t['GI_montante'], 'para': 'GI %.2f' % t['GI_jusante'], 'L_m': t['L_m'], 'DN_mm': 1200,
                    'terreno_mont': round(float(zt[0]), 3), 'terreno_jus': round(float(zt[-1]), 3), 'GI_mont': t['GI_montante'], 'GI_jus': t['GI_jusante'],
                    'recobrimento_mont': round(float(cob[0]), 3), 'recobrimento_jus': round(float(cob[-1]), 3), 'i_rotulo_pct': t['i_pct'], 'i_pelas_CF_pct': t['i_pct'],
                    'GI_estimado_pela_declividade': '', 'obs_fase2': 'rede futura, se necessário', 'obs_fase3': ' | '.join(obs)})
    cols = list(out[0].keys())
    with open(os.path.join(REL3, 'SAT_fase3_gravidade_checagem.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows(out)
    return out


def mapa_terreno(ter):
    fig, ax = plt.subplots(figsize=(15, 13))
    xs = np.linspace(545840, 546070, 230); ys = np.linspace(8716080, 8716290, 210)
    X, Y = np.meshgrid(xs, ys); Z = ter.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    cs = ax.contourf(X, Y, Z, levels=np.arange(224, 241, 0.5), cmap='terrain'); plt.colorbar(cs, ax=ax, label='cota (m)')
    ax.contour(X, Y, Z, levels=np.arange(224, 241, 1.0), colors='k', linewidths=0.3)
    ax.add_collection(LineCollection(arq_sit(), colors='0.25', linewidths=0.2, alpha=0.5))
    for P, z in ter.plat: ax.plot(*np.vstack([P, P[:1]]).T, 'r-', lw=1.5); ax.text(*P.mean(0), f'PLATÔ +{z:.2f}', color='r', fontsize=11, ha='center')
    ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain')
    ax.set_title('ETIB Sátiro Dias — terreno provisório da fase 3: platôs da terraplanagem + terreno existente (TOP/DRE-002) fora deles')
    fig.savefig(os.path.join(REL3, 'SAT_fase3_terreno_provisorio.png'), dpi=100, bbox_inches='tight'); plt.close(fig)


def main():
    # 19/10/2026: o terreno do IMP as built substitui o provisório (SAT_TERRENO=provisorio volta ao antigo)
    if os.environ.get('SAT_TERRENO') == 'provisorio':
        ter = Terreno(); mapa_terreno(ter)
    else:
        ter = TerrenoIMP()
    L = pressurizadas(ter)
    G = gravidade(ter)
    por = collections.defaultdict(list)
    for l in L: por[l['sistema']].append(l)
    for s, ls in por.items():
        print(f"{s}: {len(ls)} pernas, recobrimento real mín {min(l['recobrimento_min_real'] for l in ls):.2f} (exigido {COBR[s]:.2f}), "
              f"eixo {min(min(l['eixo_ini'], l['eixo_fim']) for l in ls):.2f}–{max(max(l['eixo_ini'], l['eixo_fim']) for l in ls):.2f}")
    for g in G:
        if g['obs_fase3']: print(' ', g['rede'], g['trecho'], g['de'], '->', g['para'], '|', g['obs_fase3'])


if __name__ == '__main__':
    main()
