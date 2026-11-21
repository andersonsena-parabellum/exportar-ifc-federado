# -*- coding: utf-8 -*-
"""ETIB Catu — ajustes em planta feitos ANTES do preclash (cenário B do adaptador escolas/catu.py).
O clash do preclash não testa caixa × caixa, e trecho por gravidade que termina numa caixa de outra rede conta como ligação;
por isso as caixas do SDAI e da elétrica desenhadas em cima de PV/CA/CE (ex.: CX-09 e EL2-CX04 no PVP-05) não aparecem
como conflito, só os eletrodutos que saem delas. Aqui:
  1. caixas de rede pressurizada (SDAI, ELE) que encostam (< folga) em caixa ou tubo por gravidade de outra rede andam
     o mínimo em planta (busca polar até 3 m); os eletrodutos que chegam nela acompanham (ponta move, cota refeita);
  2. nós de rede pressurizada (tê, ponta) dentro de caixa de outra rede (ex.: tê da AF na CE-01) andam o mínimo do mesmo jeito.
Aceite: a caixa/nó e os trechos ligados a ela ficam a ≥ folga de toda caixa de outra rede e de todo tubo por gravidade;
cruzamento com tubo pressurizado fica para a solução de profundidade do preclash. Cada ajuste sai com nota para a planta.
Não altera a ferramenta; só usa preclash.clash e preclash.leitura."""
import numpy as np
from preclash import clash as cl
from preclash import leitura as lt

f2 = lambda v: f'{v:.2f}'.replace('.', ',')
DIRS = np.radians(np.arange(0, 360, 22.5))
RAIOS = np.arange(0.10, 3.0 + 1e-6, 0.10)
PERTO = 2.0          # só o pedaço dos trechos a menos disso do ponto movido entra no teste (o resto fica para o preclash)


def _sq_gap(a, b):
    if a['zt'] <= b['zb'] + 0.01 or b['zt'] <= a['zb'] + 0.01: return 9.0          # só encostar na cota não conta
    return max(abs(a['E'] - b['E']), abs(a['N'] - b['N'])) - _meia(a) - _meia(b)


def _amostra_2d(P2, z, passo=0.10):
    """amostra a polilinha 2D com a cota z interpolada pelo comprimento (aproximação durante a busca; vetorizado)."""
    S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P2, axis=0).T))]); L = max(S[-1], 1e-9)
    s = np.unique(np.concatenate([np.arange(0, L, passo), S]))
    return np.column_stack([np.interp(s, S, P2[:, 0]), np.interp(s, S, P2[:, 1]), np.interp(s / L, np.linspace(0, 1, len(z)), z)])


def _meia(c):
    return max(c['mx'], c['my']) if c.get('forma') == 'r' else c['meia']


def _perto(Q, c, m):
    h = _meia(c) + m
    return (Q[:, 0].min() <= c['E'] + h and Q[:, 0].max() >= c['E'] - h and Q[:, 1].min() <= c['N'] + h and Q[:, 1].max() >= c['N'] - h)


class Ajustes:
    def __init__(self, E, C, ter, cob, regras, log=None):
        self.E, self.C, self.ter, self.cob, self.folga = E, C, ter, cob, regras['folga']
        self.reg = []; self._cache = {}; self.log = log or (lambda *a: None)

    def _Q(self, e):
        k = (e['id'], id(e['pts']))
        if k not in self._cache: self._cache[k] = cl.amostra(e['pts'], 0.10)
        return self._cache[k]

    def _viz(self, rede, lo, hi, excl):
        lo = np.asarray(lo) - 2.0; hi = np.asarray(hi) + 2.0
        G = [x for x in self.E if x['rede'] != rede and x['tipo'] == 'gravidade' and x['id'] not in excl
             and np.all(x['pts'][:, :2].max(0) >= lo) and np.all(x['pts'][:, :2].min(0) <= hi)]
        Cf = [c for c in self.C if c['rede'] != rede and c['id'] not in excl and lo[0] <= c['E'] <= hi[0] and lo[1] <= c['N'] <= hi[1]]
        return G, Cf

    def _viol(self, caixa, trechos, G, Cf):
        """violações (< folga): caixa × caixa de outra rede, caixa × tubo por gravidade, trecho × caixa de outra rede."""
        n, pior = 0, 9.0
        if caixa is not None:
            for c in Cf:
                g = _sq_gap(caixa, c); pior = min(pior, g); n += g < self.folga
            for x in G:
                Q = self._Q(x)
                if not _perto(Q, caixa, x['de'] / 2 + self.folga + 0.05): continue
                s = float(np.min(cl.sd_caixa(Q, caixa))) - x['de'] / 2; pior = min(pior, s); n += s < self.folga
        for Q, de in trechos:
            for c in Cf:
                if not _perto(Q, c, de / 2 + self.folga + 0.05): continue
                s = float(np.min(cl.sd_caixa(Q, c))) - de / 2; pior = min(pior, s); n += s < self.folga
        return int(n), pior

    def _recorte(self, Q, c0):
        m = np.hypot(Q[:, 0] - c0[0], Q[:, 1] - c0[1]) < PERTO
        return Q[m] if m.any() else Q[:1]

    def _trechos_aprox(self, lig, v):
        out = []
        for e, i in lig:
            P2 = e['pts'][:, :2].copy(); c0 = P2[i].copy(); P2[i] = P2[i] + v
            out.append((self._recorte(_amostra_2d(P2, e['pts'][:, 2]), c0 + v / 2), e['de']))
        return out

    def _trechos_exatos(self, lig, v):
        res = []
        for e, i in lig:
            P2 = e['pts'][:, :2].copy(); P2[i] = P2[i] + v
            res.append(lt.perfil_por_recobrimento(P2, e['de'], self.cob[e['disc']], self.ter))
        return res

    def _buscar(self, caixa_em, lig, G, Cf):
        """menor deslocamento sem violação; devolve (v, pior_antes, pior_depois) ou (None, pior_antes, None)."""
        n0, p0 = self._viol(caixa_em(np.zeros(2)), [(self._recorte(cl.amostra(e['pts'], 0.10), e['pts'][i, :2]), e['de']) for e, i in lig], G, Cf)
        if n0 == 0: return 'ok', p0, None
        for r in RAIOS:
            cand = []
            for a in DIRS:
                v = r * np.array([np.cos(a), np.sin(a)])
                cx = caixa_em(v)
                if cx is not None and self._viol(cx, [], G, Cf)[0]: continue
                tr = self._trechos_aprox(lig, v)
                n, p = self._viol(cx, tr, G, Cf)
                if n == 0: cand.append((sum(float(np.sum(np.hypot(*np.diff(Q[:, :2], axis=0).T))) for Q, _ in tr), -p, v))
            for _, _, v in sorted(cand, key=lambda t: (t[0], t[1]))[:2]:      # confere no exato só os 2 melhores do raio
                P = self._trechos_exatos(lig, v)
                n, p = self._viol(caixa_em(v), [(self._recorte(cl.amostra(Pk, 0.05), e['pts'][i, :2] + v / 2), e['de']) for Pk, (e, i) in zip(P, lig)], G, Cf)
                if n == 0: return (v, P), p0, p
        return None, p0, None

    def _aplicar_trechos(self, lig, P, motivo):
        for (e, i), Pk in zip(lig, P):
            e['pts_original'] = e.get('pts_original', e['pts'].copy()); e['pts'] = Pk; e['pts_sol'] = Pk.copy(); e.pop('S', None)
            e.setdefault('desvio', []).append({'manual': motivo})

    # ---------- 1. caixas de SDAI/ELE em cima de caixa ou tubo por gravidade de outra rede
    def _folga_caixa(self, c):
        lig = [(e, i) for e in self.E if e['rede'] == c['rede'] for i in (0, len(e['pts']) - 1)
               if np.hypot(e['pts'][i, 0] - c['E'], e['pts'][i, 1] - c['N']) < c['meia'] + 0.6]
        pts = np.vstack([[[c['E'], c['N']]]] + [e['pts'][:, :2] for e, _ in lig])
        G, Cf = self._viz(c['rede'], pts.min(0), pts.max(0), {e['id'] for e, _ in lig} | {c['id']})
        return self._viol(c, [(self._recorte(cl.amostra(e['pts'], 0.10), e['pts'][i, :2]), e['de']) for e, i in lig], G, Cf)[1]

    def caixas(self):
        pend = [c for c in self.C if c['disc'] in ('SDAI', 'ELE') and not str(c['id']).startswith('EQ:') and c['info'].get('tipo') == 'CX']
        feitas = set()
        while True:
            cand = [(self._folga_caixa(c), c) for c in pend if c['id'] not in feitas]
            cand = [(f, c) for f, c in cand if f < self.folga]
            if not cand: break
            c = min(cand, key=lambda t: t[0])[1]; feitas.add(c['id'])
            self._uma_caixa(c)

    def _uma_caixa(self, c):
        if True:
            lig = [(e, i) for e in self.E if e['rede'] == c['rede'] for i in (0, len(e['pts']) - 1)
                   if np.hypot(e['pts'][i, 0] - c['E'], e['pts'][i, 1] - c['N']) < c['meia'] + 0.6]
            ids = {e['id'] for e, _ in lig} | {c['id']}
            pts = np.vstack([[[c['E'], c['N']]]] + [e['pts'][:, :2] for e, _ in lig])
            G, Cf = self._viz(c['rede'], pts.min(0), pts.max(0), ids)
            prof = c['zt'] - c['zb']

            def caixa_em(v, c=c, prof=prof):
                E2, N2 = c['E'] + v[0], c['N'] + v[1]
                zt = float(self.ter.z([[E2, N2]])[0]); zt = c['zt'] if np.isnan(zt) else zt
                return dict(c, E=E2, N=N2, zt=zt, zb=zt - prof)
            t0 = __import__('time').time()
            m, p0, p1 = self._buscar(caixa_em, lig, G, Cf)
            if m == 'ok': return
            nome = c['info'].get('nome', c['id'])
            self.log(f"  caixa {nome}: folga {p0:.2f} -> {'sem posição' if m is None else f'{np.hypot(*m[0]):.2f} m, folga {p1:.2f}'} ({__import__('time').time() - t0:.0f} s)")
            if m is None:
                self.reg.append({'disc': c['disc'], 'tipo': 'caixa deslocada (manual)', 'item': nome, 'status': 'sem posição livre até 3 m', 'desloc': None,
                                 'E': c['E'], 'N': c['N'], 'antes': p0, 'nota': ''})
                return
            v, P = m; c2 = caixa_em(v)
            c['E0'], c['N0'] = c.get('E0', c['E']), c.get('N0', c['N'])
            for k in ('E', 'N', 'zt', 'zb'): c[k] = c2[k]
            self._aplicar_trechos(lig, P, 'caixa ' + nome)
            d = float(np.hypot(*v)); az = (90 - np.degrees(np.arctan2(v[1], v[0]))) % 360
            tr = ', '.join(sorted({e['trecho'] for e, _ in lig}))
            self.reg.append({'disc': c['disc'], 'tipo': 'caixa deslocada (manual)', 'item': nome, 'status': 'aplicado', 'desloc': d,
                             'E': c['E0'], 'N': c['N0'], 'E_novo': c['E'], 'N_novo': c['N'], 'antes': p0, 'depois': p1, 'trechos': tr,
                             'nota': f"Deslocar a caixa {nome} {f2(d)} m para o azimute {az:.0f}° (sai de cima de caixa/tubo de outra rede); {tr} acompanham."})

    # ---------- 2. nós de rede pressurizada dentro de caixa de outra rede
    def nos(self):
        for disc in ('AF', 'HID', 'SDAI', 'ELE'):
            grupos = []
            for e in [e for e in self.E if e['disc'] == disc]:
                for i in (0, len(e['pts']) - 1):
                    q = e['pts'][i, :2]
                    g = next((g for g in grupos if g[0] == e['rede'] and np.hypot(*(g[1] - q)) < 0.15), None)
                    if g: g[2].append((e, i))
                    else: grupos.append((e['rede'], q.copy(), [(e, i)]))
            for rede, _, lig in grupos:
                xy = lig[0][0]['pts'][lig[0][1], :2]
                dentro = [c for c in self.C if c['rede'] != rede and abs(c['E'] - xy[0]) < c['meia'] + self.folga and abs(c['N'] - xy[1]) < c['meia'] + self.folga]
                if not dentro: continue
                if any(np.hypot(c['E'] - xy[0], c['N'] - xy[1]) < c['meia'] + 0.6 for c in self.C if c['rede'] == rede): continue   # já tratado no item 1
                ids = {e['id'] for e, _ in lig}
                pts = np.vstack([e['pts'][:, :2] for e, _ in lig])
                G, Cf = self._viz(rede, pts.min(0), pts.max(0), ids)
                m, p0, p1 = self._buscar(lambda v: None, lig, G, Cf)
                if m == 'ok': continue
                nome = '/'.join(sorted(e['trecho'] for e, _ in lig)); obst = ', '.join(sorted(c['info'].get('nome', c['id']) for c in dentro))
                if m is None:
                    self.reg.append({'disc': disc, 'tipo': 'nó deslocado (manual)', 'item': nome, 'status': 'sem posição livre até 3 m', 'desloc': None,
                                     'E': float(xy[0]), 'N': float(xy[1]), 'antes': p0, 'nota': ''})
                    continue
                v, P = m
                self._aplicar_trechos(lig, P, 'nó ' + nome)
                d = float(np.hypot(*v)); az = (90 - np.degrees(np.arctan2(v[1], v[0]))) % 360
                self.reg.append({'disc': disc, 'tipo': 'nó deslocado (manual)', 'item': nome, 'status': 'aplicado', 'desloc': d, 'E': float(xy[0]), 'N': float(xy[1]),
                                 'E_novo': float(xy[0] + v[0]), 'N_novo': float(xy[1] + v[1]), 'antes': p0, 'depois': p1, 'trechos': nome.replace('/', ', '),
                                 'nota': f"Deslocar o encontro de {nome.replace('/', ' e ')} {f2(d)} m para o azimute {az:.0f}°, para sair da caixa {obst}."})


def aplicar(E, C, ter, cob, regras, log=None):
    A = Ajustes(E, C, ter, cob, regras, log)
    A.caixas(); A.nos()
    return A.reg
