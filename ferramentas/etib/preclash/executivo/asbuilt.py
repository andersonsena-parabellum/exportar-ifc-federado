# -*- coding: utf-8 -*-
"""Planejamento da revisão no padrão de EXECUTIVO FINAL (as built), sobre a própria prancha:
  - contorno: o trecho antigo da rede sai da prancha e o traçado novo entra na MESMA entidade/layer/tipo de linha/cor
    (polilinha: troca dos vértices; linha: apaga e redesenha com as propriedades dela); tags de diâmetro e de fluxo
    (textos e blocos junto do trecho) acompanham o deslocamento;
  - caixa deslocada: o bloco/contorno da caixa e o texto dela andam; as pontas das linhas que chegam nela acompanham;
  - mergulho: nota curta de profundidade no estilo do texto mais próximo da prancha (sem nuvem, sem referência a revisão).
Lê as entidades do DXF da cópia (handles iguais aos do DWG) e devolve os comandos de revisao.lsp."""
import re
import sys
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf')
import dxfgeo  # noqa: E402


def br(v, d=2):
    return f'{v:.{d}f}'.replace('.', ',')


def _limpo(s):
    """conteúdo de TEXT/MTEXT sem os códigos de formatação."""
    return re.sub(r'\\[A-Za-z][^;\\]*;|[{}]', '', str(s))


def entidades(fn_dxf, arcos=False, blocos=False):
    """entidades do espaço do modelo com handle: linhas/polilinhas (pts), textos e blocos (p).
    arcos=True: ARC também, como polilinha (pts) com typ 'ARC' — só para a nota não cair em cima da curva e achar a etiqueta
    do trecho; o Plano não edita arco (contorno e caixa usam só LINE/LWPOLYLINE).
    blocos=True: textos de dentro dos blocos (arquitetura inserida como bloco: "DEP. DE UTENSÍLIOS" na DRE-001 da escola A),
    typ 'BTXT', só para a nota não cair em cima deles (não servem de molde nem de etiqueta)."""
    _, model = dxfgeo.parse(fn_dxf)
    out = []
    if blocos:
        for i, t in enumerate(dxfgeo.load(fn_dxf)['texts']):
            # de dentro de bloco (path) ou atributo de bloco do modelo ("AP 150 mm" da coluna pluvial, "#10" do circuito)
            if (not t['path'] and t['typ'] != 'ATTRIB') or not str(t['t']).strip(): continue
            out.append({'h': f'BTXT{i}', 'typ': 'BTXT', 'lay': t['lay'], 'p': np.array(t['p'][:2], float), 'alt': float(t['h']),
                        'rot': float(np.radians(t['rot'])), 'txt': t['t'], 'anexo': t.get('anexo', 7), 'mtext': t['typ'] == 'MTEXT'})
    for typ, data in model:
        d = dxfgeo._first(data)
        if str(d.get(67, '0')).strip() == '1' or 5 not in d: continue
        e = {'h': str(d[5]).strip(), 'typ': typ, 'lay': d.get(8, '')}
        if typ in ('ARC', 'CIRCLE'):                      # círculo: marcador "AP 150 mm" da coluna pluvial, poço, poste
            if not arcos: continue
            c = np.array([float(d[10]), float(d[20])]); r = float(d[40]); e['typ'] = 'ARC'
            a0, a1 = (np.radians(float(d.get(50, 0))), np.radians(float(d.get(51, 360)))) if typ == 'ARC' else (0.0, 2 * np.pi)
            if a1 <= a0: a1 += 2 * np.pi
            t = np.linspace(a0, a1, int(min(200, max(8, r * (a1 - a0) / 0.5))) + 1)
            e['pts'] = np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])
        elif typ == 'LINE':
            e['pts'] = np.array([[float(d[10]), float(d[20])], [float(d[11]), float(d[21])]])
        elif typ == 'LWPOLYLINE':
            xs = [float(v) for c, v in data if c == 10]; ys = [float(v) for c, v in data if c == 20]
            if len(xs) < 2: continue
            e['pts'] = np.column_stack([xs, ys]); e['fechada'] = bool(int(d.get(70, 0)) & 1)
        elif typ in ('TEXT', 'MTEXT'):
            e['p'] = np.array([float(d[10]), float(d[20])]); e['alt'] = float(d.get(40, 0)); e['rot'] = float(d.get(50, 0))
            e['txt'] = d.get(1, ''); e['anexo'] = int(d.get(71, 7)) if typ == 'MTEXT' else 7
            if typ == 'MTEXT' and 11 in d and 21 in d:      # direção do MTEXT (vetor) manda na rotação
                e['rot'] = float(np.arctan2(float(d[21]), float(d[11])))
        elif typ == 'INSERT':
            e['p'] = np.array([float(d[10]), float(d[20])]); e['nome'] = d.get(2, '')
        elif typ == 'HATCH':
            # preenchimento (ex.: ponta da seta de fluxo): anda junto como as tags; posição = centro do contorno
            xs = [float(v) for c, v in data if c == 10][1:]; ys = [float(v) for c, v in data if c == 20][1:]
            if not xs: continue
            e['p'] = np.array([np.mean(xs), np.mean(ys)]); e['contorno'] = np.column_stack([xs, ys]); e['nome'] = ''
        else:
            continue
        out.append(e)
    return out


def simplificar(P, tol):
    """Douglas-Peucker 2D: tira os vértices quase alinhados (traçado limpo, sem serrilhado)."""
    if len(P) < 3: return P
    keep = np.zeros(len(P), bool); keep[[0, -1]] = True; pilha = [(0, len(P) - 1)]
    while pilha:
        i, j = pilha.pop(); a, b = P[i], P[j]; d = b - a; L = np.hypot(*d)
        if j <= i + 1: continue
        Q = P[i + 1:j]
        dist = np.abs(np.cross(d, Q - a)) / L if L > 1e-9 else np.hypot(*(Q - a).T)
        k = int(np.argmax(dist))
        if dist[k] > tol: keep[i + 1 + k] = True; pilha += [(i, i + 1 + k), (i + 1 + k, j)]
    return P[keep]


def _cum(P):
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])


def projetar(P, q):
    """(s, distância, ponto) do ponto q na polilinha P."""
    best = (1e18, 0.0, P[0]); S = _cum(P)
    for a, b, s0 in zip(P[:-1], P[1:], S[:-1]):
        d = b - a; L2 = d @ d
        t = 0.0 if L2 < 1e-12 else float(np.clip((q - a) @ d / L2, 0, 1))
        p = a + d * t; dist = float(np.hypot(*(p - q)))
        if dist < best[0]: best = (dist, s0 + t * np.sqrt(L2), p)
    return best[1], best[0], best[2]


def trecho(P, s0, s1):
    """sub-polilinha de P entre as abscissas s0 < s1."""
    S = _cum(P); s0, s1 = max(0, s0), min(S[-1], s1)
    pos = lambda s: np.array([np.interp(s, S, P[:, 0]), np.interp(s, S, P[:, 1])])
    return np.vstack([pos(s0)] + [P[i] for i in range(len(P)) if s0 < S[i] < s1] + [pos(s1)])


def _janela(A, B, tol):
    """parte de B fora de A: abscissas em B (b0, b1) e em A (a0, a1) do começo e do fim do trecho alterado."""
    SB = _cum(B); n = max(2, int(SB[-1] / 0.05))
    s = np.linspace(0, SB[-1], n)
    Q = np.column_stack([np.interp(s, SB, B[:, 0]), np.interp(s, SB, B[:, 1])])
    fora = np.array([projetar(A, q)[1] > tol for q in Q])
    if not fora.any(): return None
    i0, i1 = int(np.argmax(fora)), len(fora) - 1 - int(np.argmax(fora[::-1]))
    i0, i1 = max(0, i0 - 1), min(n - 1, i1 + 1)
    s0, s1 = s[i0], s[i1]
    # encosta nas quinas do traçado novo (começo e fim da transição), se estiverem perto
    v0 = [x for x in SB if s0 - 0.3 <= x <= s0 + 1e-9]; v1 = [x for x in SB if s1 - 1e-9 <= x <= s1 + 0.3]
    if v0: s0 = max(v0)
    if v1: s1 = min(v1)
    pB = lambda x: np.array([np.interp(x, SB, B[:, 0]), np.interp(x, SB, B[:, 1])])
    a0 = projetar(A, pB(s0))[0]; a1 = projetar(A, pB(s1))[0]
    return s0, s1, min(a0, a1), max(a0, a1)


class Plano:
    def __init__(self, ents, tol=0.06, ext=0.0, caixa_sem_simbolo=False):
        """ext: prolonga as pontas do traçado do modelo para achar a linha da prancha quando a caixa do modelo não está
        no mesmo ponto da prancha (escola A: até ~1 m); caixa_sem_simbolo: prancha que marca a caixa só com o texto
        ("Cx. 80x80 cm") no vértice do eletroduto — a caixa deslocada move o vértice e o texto."""
        self.E = ents; self.tol = tol; self.ext = ext; self.sem_simbolo = caixa_sem_simbolo; self.L = []; self.log = []
        self.linhas = [e for e in ents if 'pts' in e and e['typ'] != 'ARC']
        self.tracos = [e for e in ents if 'pts' in e]          # + arcos: só para a nota (tinta e etiqueta do trecho)
        self.textos = [e for e in ents if e['typ'] in ('TEXT', 'MTEXT')]
        self.tags = [e for e in ents if e['typ'] in ('TEXT', 'MTEXT', 'INSERT', 'HATCH')]
        self.feitos = set()

    def _xy(self, P):
        return '\t'.join(f'{x:.4f}\t{y:.4f}' for x, y in P)

    # ------------------------------------------------------------ contorno (mudança de traçado)
    def contorno(self, A, B, rotulo, raio_tag=1.5):
        A = np.asarray(A, float); B = np.asarray(B, float)
        if self.ext > 0 and np.hypot(*(A[0] - B[0])) < 1e-3 and np.hypot(*(A[-1] - B[-1])) < 1e-3:
            u0 = (A[0] - A[1]) / max(1e-9, np.hypot(*(A[0] - A[1]))); u1 = (A[-1] - A[-2]) / max(1e-9, np.hypot(*(A[-1] - A[-2])))
            p0, p1 = A[0] + u0 * self.ext, A[-1] + u1 * self.ext
            A = np.vstack([p0, A, p1]); B = np.vstack([p0, B, p1])
        j = _janela(A, B, self.tol)
        pontas_mudam = np.hypot(*(A[0] - B[0])) > self.tol or np.hypot(*(A[-1] - B[-1])) > self.tol
        if j is None and not pontas_mudam: self.log.append(f'{rotulo}: traçado igual ao original'); return
        if j is None or j[3] - j[2] < 0.02:
            self._pontas(A, B, rotulo); return
        b0, b1, a0, a1 = j
        achou = 0
        for e in self.linhas:
            if e['h'] in self.feitos: continue
            P = e['pts']
            if np.ptp(P, axis=0).max() < 0.5 and not e.get('fechada'):
                # conexão desenhada sobre o trecho (tê, luva, curva): anda inteira com o traçado
                c = P.mean(0); s, d, q = projetar(A, c)
                if d < max(self.tol, 0.25) and a0 - 0.05 <= s <= a1 + 0.05:
                    v = projetar(B, q)[2] - q
                    if np.hypot(*v) > 1e-3: self.L.append(f"MV\t{e['h']}\t{v[0]:.4f}\t{v[1]:.4f}"); self.feitos.add(e['h'])
                continue
            pr = [projetar(A, p) for p in P]
            sobre = np.array([d < self.tol for s, d, q in pr])
            if sobre.sum() < 2: continue
            sA = np.array([s for s, d, q in pr])
            # algum segmento da entidade (sobre A) cruza a janela alterada?
            seg = [(sA[i], sA[i + 1]) for i in range(len(P) - 1) if sobre[i] and sobre[i + 1]]
            if not any(min(u, v) < a1 - 1e-3 and max(u, v) > a0 + 1e-3 for u, v in seg): continue
            achou += 1; self.feitos.add(e['h'])
            u, v = float(sA[sobre].min()), float(sA[sobre].max())
            lo, hi = max(a0, u), min(a1, v)
            pA = lambda s: trecho(A, s, s + 1e-6)[0]
            m0 = b0 if lo <= a0 + 1e-6 else projetar(B, pA(lo))[0]
            m1 = b1 if hi >= a1 - 1e-6 else projetar(B, pA(hi))[0]
            meio = trecho(B, min(m0, m1), max(m0, m1))
            fwd = sA[sobre][-1] >= sA[sobre][0]
            if sobre.all():
                Q = np.vstack([trecho(A, u, lo)[:-1] if lo > u + 1e-6 else np.zeros((0, 2)), meio,
                               trecho(A, hi, v)[1:] if v > hi + 1e-6 else np.zeros((0, 2))])
                if not fwd: Q = Q[::-1]
            else:
                # polilinha que vai além da rede: mantém os vértices de fora e troca só os da janela
                mm = meio if fwd else meio[::-1]; out = []; pos = False
                dentro = [bool(sobre[i] and lo - 1e-6 <= sA[i] <= hi + 1e-6) for i in range(len(P))]
                for i, p in enumerate(P):
                    if dentro[i]:
                        if not pos: out.extend(mm); pos = True
                        continue
                    if (not pos and i > 0 and sobre[i - 1] and sobre[i]
                            and min(sA[i - 1], sA[i]) <= lo + 1e-6 and max(sA[i - 1], sA[i]) >= hi - 1e-6):
                        out.extend(mm); pos = True
                    out.append(p)
                Q = np.array(out)
            keep = [0] + [k for k in range(1, len(Q)) if np.hypot(*(Q[k] - Q[k - 1])) > 1e-4]
            Q = simplificar(Q[keep], 0.03)
            if e['typ'] == 'LWPOLYLINE':
                self.L.append(f"REPL\t{e['h']}\t" + self._xy(Q))
            else:
                self.L.append(f"PLC\t{e['h']}\t0\t" + self._xy(Q)); self.L.append(f"DEL\t{e['h']}")
        # tags (diâmetro, sentido de fluxo, rótulos) junto do trecho alterado andam com ele
        mov = 0
        for t in self.tags:
            if t['h'] in self.feitos or not achou: continue           # sem traçado achado nada anda (poste, quadro etc. ficam)
            if t['typ'] == 'INSERT' and any(k in (t.get('nome', '') + ' ' + t['lay']).upper() for k in ('POSTE', 'LUMIN', 'REFLET', 'PROJETOR', 'QUADRO')): continue
            s, d, q = projetar(A, t['p'])
            if d > raio_tag or not (a0 < s < a1): continue
            _, _, qb = projetar(B, q + (t['p'] - q) * 0)       # ponto do traçado novo mais perto do ponto antigo
            v = qb - q
            if np.hypot(*v) < 1e-3: continue
            self.L.append(f"MV\t{t['h']}\t{v[0]:.4f}\t{v[1]:.4f}"); self.feitos.add(t['h']); mov += 1
            if not hasattr(self, 'movidos'): self.movidos = {}
            self.movidos[t['h']] = v
        self.log.append(f'{rotulo}: {achou} entidade(s) do traçado alteradas, {mov} tag(s) acompanharam' + ('' if achou else ' — ATENÇÃO: traçado original não achado na prancha'))

    def _pontas(self, A, B, rotulo):
        """só a ponta mudou (tubo que estica ou encolhe até a linha vizinha deslocada): a ponta da linha da prancha vai junto,
        as conexões desenhadas na ponta andam inteiras e a linha que segue na direção em que o nó andou encolhe."""
        pontas = [(A[0], B[0], A[1] - A[0]), (A[-1], B[-1], A[-2] - A[-1])]
        pontas = [(po, pn, u / max(1e-9, np.hypot(*u))) for po, pn, u in pontas if np.hypot(*(po - pn)) > self.tol]
        n = n_s = 0
        for e in self.linhas:
            if e['h'] in self.feitos or e.get('fechada'): continue
            P = e['pts']
            for po, pn, u in pontas:
                if np.ptp(P, axis=0).max() < 0.5:                       # conexão desenhada na ponta: anda inteira
                    if np.hypot(*(P - po).T).max() < 0.35:
                        v = pn - po; self.L.append(f"MV\t{e['h']}\t{v[0]:.4f}\t{v[1]:.4f}"); self.feitos.add(e['h']); n_s += 1; break
                    continue
                mvn = (pn - po) / np.hypot(*(pn - po))
                for k, k2 in ((0, 1), (len(P) - 1, len(P) - 2)):     # tubo: a ponta que está no nó vai para o nó novo
                    w = P[k2] - P[k]; w = w / max(1e-9, np.hypot(*w))
                    # o próprio trecho (paralelo a ele) ou a linha que segue na direção em que o nó andou (encolhe)
                    if np.hypot(*(P[k] - po)) < max(self.tol, 0.10) and ((abs(np.cross(w, u)) < 0.17 and w @ u > 0) or (abs(np.cross(w, mvn)) < 0.17 and w @ mvn > 0)):
                        kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1)
                        self.L.append(f"VTX\t{e['h']}\t{kk}\t{pn[0]:.4f}\t{pn[1]:.4f}"); self.feitos.add(e['h']); n += 1
        self.log.append(f'{rotulo}: ponta do trecho acompanhou a linha vizinha ({n} tubo(s), {n_s} conexão(ões))' + ('' if n else ' — ATENÇÃO: ponta não achada na prancha'))

    # ------------------------------------------------------------ caixa deslocada
    def caixa(self, de, para, lado, rotulo):
        de = np.asarray(de, float); para = np.asarray(para, float); v = para - de; r = lado / 2 + 0.30
        poste = lambda e: any(k in (e.get('nome', '') + ' ' + e['lay']).upper() for k in ('POSTE', 'LUMIN', 'REFLET', 'PROJETOR'))
        simb = [e for e in self.E if e['h'] not in self.feitos and (
                (e['typ'] == 'INSERT' and not poste(e) and np.hypot(*(e['p'] - de)) < r) or
                (e['typ'] == 'LWPOLYLINE' and e.get('fechada') and np.hypot(*(e['pts'].mean(0) - de)) < r and np.ptp(e['pts'], axis=0).max() < 2 * lado + 0.5))]
        mv = lambda e: (self.L.append(f"MV\t{e['h']}\t{v[0]:.4f}\t{v[1]:.4f}"), self.feitos.add(e['h']))
        if not simb and self.sem_simbolo:
            # caixa marcada só pelo texto no vértice do eletroduto: o vértice anda (as linhas que chegam nele acompanham) e o texto também
            n_v = 0
            for e in self.linhas:
                if e['h'] in self.feitos or e.get('fechada'): continue
                for k, p in enumerate(e['pts']):
                    if np.hypot(*(p - de)) < 0.30:
                        q = p + v; kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1)
                        self.L.append(f"VTX\t{e['h']}\t{kk}\t{q[0]:.4f}\t{q[1]:.4f}"); n_v += 1
            if not n_v:
                self.log.append(f'{rotulo}: caixa sem símbolo e sem vértice de eletroduto na prancha (nada a mover)'); return
            for e in self.textos:
                if e['h'] not in self.feitos and str(e.get('txt', '')).strip().upper().startswith('CX') and np.hypot(*(e['p'] - de)) < lado + 0.8: mv(e)
            self.log.append(f'{rotulo}: caixa marcada só por texto; vértice do eletroduto movido ({n_v} ponta(s))'); return
        if not simb:                      # caixa não achada: não mexe em nada (conferir à mão)
            self.log.append(f'{rotulo}: caixa NÃO achada na prancha (conferir e mover à mão)'); return
        n_cx = len(simb)
        simb += [e for e in self.E if e['typ'] == 'HATCH' and e['h'] not in self.feitos and np.hypot(*(e['p'] - de)) < r]   # preenchimento da caixa
        for e in simb: mv(e)
        for e in self.textos:
            if e['h'] not in self.feitos and np.hypot(*(e['p'] - de)) < lado + 0.8: mv(e)
        n_ln = 0
        r = lado / 2 + 0.15
        for e in self.linhas:
            if e['h'] in self.feitos or e.get('fechada'): continue
            for k, p in ((0, e['pts'][0]), (-1, e['pts'][-1])):
                if np.hypot(*(p - de)) < r:
                    q = p + v; self.L.append(f"VTX\t{e['h']}\t{k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1)}\t{q[0]:.4f}\t{q[1]:.4f}"); n_ln += 1
        self.log.append(f'{rotulo}: caixa movida, {n_ln} ponta(s) de linha acompanharam')

    # ------------------------------------------------------------ nota de profundidade (mergulho)
    def _caixa_txt(self, q, ang, w, h):
        u = np.array([np.cos(ang), np.sin(ang)]); v = np.array([-u[1], u[0]])
        C = np.array([q, q + u * w, q + u * w + v * h, q + v * h])
        return C.min(0), C.max(0)

    def _ret_texto(self, tx):
        """(ângulo rad, largura, altura, canto inferior esquerdo) de um TEXT/MTEXT da prancha."""
        a = tx['rot'] if tx['typ'] in ('MTEXT', 'BTXT') else np.radians(tx['rot'])      # BTXT (texto de bloco) já vem em rad
        # MTEXT de várias linhas (\P): largura da maior linha, altura de todas (entrelinha 5/3 da altura) — o "DEP. DE\PUTENSÍLIOS"
        # da DRE-001 contava como uma linha só e a nota caiu em cima da segunda linha
        mt = tx['typ'] == 'MTEXT' or tx.get('mtext')
        lin = [_limpo(x) for x in re.split(r'\\P', str(tx.get('txt', '')))] if mt else [_limpo(tx.get('txt', ''))]
        # maiúsculas são mais largas: o "HIDRÔMETRO" da AGF-001 de escola B ia 0,6 m além do que 0,85 h por letra dava
        lmax = max(lin, key=len) if lin else ''
        fl = 1.05 if sum(c.isupper() for c in lmax) > 0.6 * max(1, sum(c.isalpha() for c in lmax)) else 0.85
        tw = max(1, len(lmax)) * tx['alt'] * fl; th = tx['alt'] * (1 + 5 / 3 * (len(lin) - 1))
        uu = np.array([np.cos(a), np.sin(a)]); vv = np.array([-uu[1], uu[0]]); k = tx.get('anexo', 7)
        p0 = tx['p'] + getattr(self, 'movidos', {}).get(tx['h'], np.zeros(2))
        p0 = p0 - uu * tw * ((k - 1) % 3) / 2 - vv * th * {0: 1.0, 1: 0.5, 2: 0.0}[(k - 1) // 3]
        return a, tw, th, p0

    def _tag_do_trecho(self, P, cand, dist=1.5, ang_max=15.0, disc=None):
        """etiqueta de diâmetro/material do próprio trecho, se houver: texto paralelo a menos de 'dist' m da linha do trecho na
        prancha e mais perto dela do que de qualquer outra linha (senão é a etiqueta da rede vizinha — ex.: o "PEAD 2.1/2"" do
        hidrante ao lado do eletroduto do alarme)."""
        S = _cum(P); amo = [np.array([np.interp(s, S, P[:, 0]), np.interp(s, S, P[:, 1])]) for s in np.linspace(0, S[-1], 7)]
        lo, hi = P.min(0) - 2.0, P.max(0) + 2.0
        perto = [e for e in self.tracos if not ((e['pts'].max(0) < lo).any() or (e['pts'].min(0) > hi).any())]
        if not perto: return None
        dm = [(np.mean([projetar(e['pts'], q)[1] for q in amo]), e) for e in perto]
        d0, propria = min(dm, key=lambda x: x[0])
        if d0 > 1.5: return None
        melhor = None
        for tx in cand:
            s = re.sub(r'\\[A-Za-z][^;\\]*;|[{}]', '', str(tx.get('txt', '')))
            if not re.search(r'Ø|ø|%%[cC]|PVC|PEAD|PPR|PEX|FoFo|\bDN\b|\d\s*mm\b|\d"', s) or 'PROF' in s.upper(): continue
            # eletroduto/alarme não usa etiqueta de tubo de água (o "PEAD 2.1/2"" do hidrante ao lado do alarme, IN-001 da escola A)
            if disc in ('ELE', 'SDAI', 'CFTV') and (re.search(r'PEAD|PVC|PPR|PEX|FOFO|\d\s*MM\b', s.upper()) or re.fullmatch(r'\s*\d+\.\d+/\d+"\s*', s)):
                continue
            a, tw, th, p0 = self._ret_texto(tx)
            uu = np.array([np.cos(a), np.sin(a)]); vv = np.array([-uu[1], uu[0]]); c = p0 + uu * tw / 2 + vv * th / 2
            if (c < P.min(0) - dist - tw).any() or (c > P.max(0) + dist + tw).any(): continue
            s_, d, _ = projetar(P, c)
            if d > dist: continue
            k = max(0, min(len(P) - 2, int(np.searchsorted(S, s_) - 1))); dv = P[k + 1] - P[k]
            dif = abs((np.degrees(np.arctan2(dv[1], dv[0]) - a) + 90) % 180 - 90)
            if dif > ang_max: continue
            d_prop = projetar(propria['pts'], c)[1]
            if d_prop > dist: continue
            if any(projetar(e['pts'], c)[1] < d_prop - 0.02 for e in self.tracos if e is not propria
                   and not ((e['pts'].max(0) < c - d_prop - 0.1).any() or (e['pts'].min(0) > c + d_prop + 0.1).any())): continue
            if melhor is None or d < melhor[0]: melhor = (d, tx)
        return melhor[1] if melhor else None

    def nota(self, P, texto, rotulo, disc=None):
        """nota curta ao lado do trecho, no estilo do texto mais próximo; procura um lugar livre (sem cobrir outro texto)."""
        P = np.asarray(P, float); S = _cum(P)
        if not self.textos: self.log.append(f'{rotulo}: prancha sem texto para copiar o estilo'); return
        c0 = np.array([np.interp(S[-1] / 2, S, P[:, 0]), np.interp(S[-1] / 2, S, P[:, 1])])
        cand = self.textos
        if getattr(self, 'alt_nota', None):           # altura de nota padrão da prancha (não copia texto miúdo de detalhe nem título)
            cand = [t for t in self.textos if self.alt_nota[0] <= t['alt'] <= self.alt_nota[1]] or self.textos
        if disc in ('ELE', 'SDAI', 'CFTV'):            # molde (layer, cor, estilo) também não vem da etiqueta do tubo de água vizinho
            agua = lambda t: re.search(r'PEAD|PVC|PPR|PEX|FOFO|\d\s*MM', _limpo(t.get('txt', '')).upper()) or re.fullmatch(r'\s*\d+\.\d+/\d+"\s*', _limpo(t.get('txt', '')))
            cand = [t for t in cand if not agua(t)] or cand
        tag = self._tag_do_trecho(P, cand, disc=disc)
        molde = tag or min(cand, key=lambda t: np.hypot(*(t['p'] - c0)) / max(0.05, min(t['alt'], 1.0)) ** 0.25)
        h = molde['alt'] if molde['alt'] > 0 else 0.25
        w = len(texto) * h * 0.85
        if not hasattr(self, 'ocupado'):
            # textos da prancha (retângulos girados) e "tinta" (pontos ao longo das linhas) para achar lugar limpo
            self.ocupado, self.notas_novas = [], []
            self._agua = []                                   # índices das etiquetas de tubo de água (PEAD, PVC, mm)
            for tx in self.textos:
                a, tw, th, p0 = self._ret_texto(tx)          # TEXT em graus, MTEXT em rad; tag que já andou com o traçado
                if re.search(r'PEAD|PVC|PPR|PEX|FOFO|\d\s*MM', _limpo(tx.get('txt', '')).upper()) or re.fullmatch(r'\s*\d+\.\d+/\d+"\s*', _limpo(tx.get('txt', ''))):
                    self._agua.append(len(self.ocupado))
                self.ocupado.append(_ret(p0, a, tw, th))
            for tx in (e for e in self.E if e['typ'] == 'BTXT'):        # texto de dentro de bloco (arquitetura)
                # retângulo conservador em volta do ponto (bloco espelhado inverte o anexo; altura real até 2x a do grupo 40:
                # o "BANCO H=0.75m" da DRE-001 saiu 0,4 m acima e à direita do que o anexo dava)
                a, tw, th, _ = self._ret_texto(tx)
                uu = np.array([np.cos(a), np.sin(a)]); vv = np.array([-uu[1], uu[0]]); hw, hh = 1.1 * tw, max(2 * th, 3 * tx['alt'])
                self.ocupado.append(_ret(tx['p'] - uu * hw - vv * hh, a, 2 * hw, 2 * hh))
            amostra = []
            for e in self.tracos:
                Q = e['pts']
                for a_, b_ in zip(Q[:-1], Q[1:]):
                    n_ = int(min(400, max(1, np.hypot(*(b_ - a_)) / 0.25)))
                    amostra.append(a_ + (b_ - a_) * (np.arange(n_ + 1)[:, None] / n_))
            self.tinta = np.vstack(amostra) if amostra else np.zeros((0, 2))
            self._grade = {}
            for i, (x, y) in enumerate(self.tinta): self._grade.setdefault((int(x // 2), int(y // 2)), []).append(i)
            oc_c = [R.mean(0) for R in self.ocupado]; self._oc_c = np.array(oc_c) if oc_c else np.zeros((0, 2))

        def custo(R):
            lo, hi = R.min(0), R.max(0)
            perto = np.where(np.hypot(*(self._oc_c - R.mean(0)).T) < w + 6)[0] if len(self._oc_c) else []
            uu = (R[1] - R[0]) / max(1e-9, np.hypot(*(R[1] - R[0]))); vv = (R[3] - R[0]) / max(1e-9, np.hypot(*(R[3] - R[0])))
            folga = lambda mg: np.array([R[0] - (uu + vv) * mg, R[1] + (uu - vv) * mg, R[2] + (uu + vv) * mg, R[3] + (vv - uu) * mg])
            # nota sobre nota também com folga de 0,4 h: duas notas paralelas a 0,03 m uma da outra leem como uma só (EL-001 de
            # escola B, "PROF. 0,70 m" encostada em "PROF. 1,65 m")
            novas = sum(1 for Q in self.notas_novas if _sobrepoe(folga(0.4 * h), Q))
            # texto da prancha: folga de 0,3 h (nota encostada no "#10" do circuito também lê mal, EL-002 da escola A)
            R1 = folga(0.3 * h)
            txt = sum(1 for i in perto if _sobrepoe(R1, self.ocupado[i]))
            if disc in ('ELE', 'SDAI', 'CFTV'):
                # nota de eletroduto/alarme longe (1 m) da etiqueta de tubo de água: "PEAD 2.1/2" / PROF. 1,05 m" lia como se o hidrante
                # estivesse a 1,05 m (IN-001 da escola A, alarme correndo junto do hidrante)
                Rf = folga(1.0); txt += sum(1 for i in perto if i in self._agua and _sobrepoe(Rf, self.ocupado[i]))
            idx = [i for cx in range(int(lo[0] // 2) - 1, int(hi[0] // 2) + 2) for cy in range(int(lo[1] // 2) - 1, int(hi[1] // 2) + 2) for i in self._grade.get((cx, cy), [])]
            # a tinta conta numa folga de 0,5 h em volta do texto: nota encostada na linha também lê mal
            R2 = folga(0.5 * h)
            tinta = int(_dentro(R2, self.tinta[idx]).sum()) if idx else 0
            # nota sobre nota nunca; sobre texto da prancha só em último caso; "tinta" (desenho por baixo) pesa pouco e tem teto
            return 1000 * novas + 20 * txt + 0.1 * min(tinta, 100), novas + txt
        melhor = None
        if tag is not None:
            # a nota entra logo abaixo (ou acima) da etiqueta do trecho (diâmetro/material), alinhada com ela: lê-se junto
            a, tw, th, p0 = self._ret_texto(tag)
            uu = np.array([np.cos(a), np.sin(a)]); vv = np.array([-uu[1], uu[0]])
            for q in (p0 - vv * th * 1.9, p0 + vv * th * 1.9, p0 - vv * th * 1.9 + uu * max(0.0, tw - w), p0 + vv * th * 1.9 + uu * max(0.0, tw - w)):   # folga de 0,9 h
                R = _ret(q, a, w, h); cst, bate = custo(R)
                if bate == 0 and (melhor is None or cst < melhor[0]): melhor = (cst, bate, q, a, R)
        junto = melhor is not None
        for frac in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9):
            if junto: break
            m = S[-1] * frac
            c = np.array([np.interp(m, S, P[:, 0]), np.interp(m, S, P[:, 1])])
            k = max(0, min(len(P) - 2, int(np.searchsorted(S, m) - 1)))
            dvec = P[k + 1] - P[k]; ang = np.arctan2(dvec[1], dvec[0])
            if ang > np.pi / 2: ang -= np.pi
            if ang < -np.pi / 2: ang += np.pi
            u = np.array([np.cos(ang), np.sin(ang)]); n = np.array([-u[1], u[0]])
            for desl in (0.0, 0.6, -0.6, 1.2, -1.2):                   # ao longo do trecho (mergulho curto: a nota pode sair para o lado)
                for off in (0.8, -1.8, 2.4, -3.4, 4.0, -5.0):         # para fora da linha (folga de 0,8 h), dos dois lados
                    q = c + n * h * off - u * w / 2 + u * w * desl
                    R = _ret(q, ang, w, h); cst, bate = custo(R)
                    cst += 0.5 * abs(desl) + 0.1 * abs(off)              # perto do trecho é melhor
                    if melhor is None or cst < melhor[0] - 1e-9: melhor = (cst, bate, q, ang, R)
            if melhor[1] == 0 and melhor[0] < 3: break
        if melhor[1] > 0:
            # trecho curto num lugar cheio (junção de 1 m entre bancos e marcadores, DRE-001 da escola A): procura em volta, até 4 m,
            # o lugar livre mais perto, com a mesma direção da nota
            _, _, _, ang_a, _ = melhor
            ang_b = ang_a + np.pi / 2 if ang_a <= 0 else ang_a - np.pi / 2          # também em pé (sempre legível)
            for r in (0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
                achou = None
                for ang0 in (ang_a, ang_b):
                    u0 = np.array([np.cos(ang0), np.sin(ang0)]); n0 = np.array([-u0[1], u0[0]])
                    for t in np.radians(np.arange(0, 360, 15)):
                        cc = c0 + r * np.array([np.cos(t), np.sin(t)])
                        q = cc - u0 * w / 2 - n0 * h / 2; R = _ret(q, ang0, w, h); cst, bate = custo(R)
                        if bate == 0 and (achou is None or cst < achou[0]): achou = (cst + 0.5 * r, 0, q, ang0, R)
                if achou: melhor = achou; break
        cst, bate, q, ang, R = melhor
        self.notas_novas.append(R)
        self.L.append(f"TXC\t{molde['h']}\t{q[0]:.4f}\t{q[1]:.4f}\t{ang:.6f}\t{texto}")
        self.log.append(f'{rotulo}: nota "{texto}"' + (f' junto da etiqueta "{_limpo(tag["txt"])}"' if junto else '')
                        + (' (encosta em outro texto: conferir)' if bate else ''))


def _ret(q, ang, w, h):
    """cantos do retângulo do texto (ponto de inserção q, ângulo em rad, largura w, altura h)."""
    u = np.array([np.cos(ang), np.sin(ang)]); v = np.array([-u[1], u[0]]); q = np.asarray(q, float)
    return np.array([q, q + u * w, q + u * w + v * h, q + v * h])


def _sobrepoe(A, B):
    """retângulos girados se cruzam? (eixos separadores)"""
    if (A[:, 0].max() < B[:, 0].min() or A[:, 0].min() > B[:, 0].max() or A[:, 1].max() < B[:, 1].min() or A[:, 1].min() > B[:, 1].max()):
        return False
    for R in (A, B):
        for i in range(2):
            e = R[i + 1] - R[i]; nrm = np.array([-e[1], e[0]])
            pa, pb = A @ nrm, B @ nrm
            if pa.max() < pb.min() or pb.max() < pa.min(): return False
    return True


def _dentro(R, pts):
    """pontos dentro do retângulo girado R."""
    if not len(pts): return np.zeros(0, bool)
    u = R[1] - R[0]; v = R[3] - R[0]; d = pts - R[0]
    a, b = d @ u / (u @ u), d @ v / (v @ v)
    return (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1)


def agrupar_mergulhos(ms, dist=10.0, familia=None):
    """um só aviso por trecho de rede: mergulhos do mesmo trecho a menos de 'dist' m viram uma nota (maior profundidade).
    familia (opcional): função elemento -> chave, para juntar trechos paralelos do mesmo banco de dutos (ex.: ELE-F-03.1 a .9)."""
    por = {}
    for m in ms: por.setdefault(familia(m['elemento']) if familia else m['elemento'], []).append(m)
    out = []
    for lst in por.values():
        lst.sort(key=lambda m: (m['planta'][0][0], m['planta'][0][1]))
        grupo = [lst[0]]
        for m in lst[1:]:
            a = np.array(grupo[-1]['planta']); b = np.array(m['planta'])
            if min(np.hypot(*(a[-1] - b[0])), np.hypot(*(a[0] - b[-1])), np.hypot(*(a.mean(0) - b.mean(0)))) < dist: grupo.append(m)
            else: out.append(grupo); grupo = [m]
        out.append(grupo)
    return out


def texto_profundidade(m):
    """nota curta usual de prancha: profundidade do topo do tubo/eletroduto em relação ao piso acabado; a mudança que traz o
    próprio texto (cota de gravidade ajustada: "GI 134,52 / 134,30") usa o dela."""
    if m.get('nota_fixa'): return m['nota_fixa']
    return f"PROF. {br(m['prof_topo'])} m"


def agrupar_notas(ms, raio=15.0, toque=0.20, colado=1.0, curto=3.0, familia=None):
    """UMA nota de profundidade por trecho (escola A, 20/10/2026: a prancha saiu com 19 "PROF. 0,90 m" no mesmo trecho, porque
    o modelo quebra a curva em pedaços de 1,4 m — ELE-F-23.1, .2… — e cada eletroduto do banco é um elemento).
    Junta os mergulhos da mesma disciplina e com o mesmo texto de nota que
      - se tocam (pedaços da mesma curva, trechos encadeados, ramais curtos na casa de bombas), ou
      - correm colados (eletrodutos do mesmo banco, a menos de 'colado' m), ou
      - são pedaços do mesmo trecho do modelo (mesmo nome sem o sufixo .N: ELE-F-22.1 e ELE-F-22.4), ou
      - são da mesma família (função opcional elemento -> chave) a menos de 4 m.
    Os pedaços encadeados viram uma polilinha (a nota fica no meio do trecho inteiro). Em cada grupo entra uma nota no trecho
    mais longo; outro trecho do grupo só ganha a sua se tiver pelo menos 'curto' m e ficar a mais de 'raio' m das notas já postas.
    Devolve [{'texto', 'P' (planta, coordenadas dos mergulhos), 'rotulo', 'n'}]."""
    ms = [m for m in ms if len(m.get('planta') or []) >= 2]
    P = [np.asarray(m['planta'], float)[:, :2] for m in ms]
    chave = [(m['disc'], texto_profundidade(m)) for m in ms]
    base = [re.sub(r'\.\d+$', '', str(m.get('trecho') or m.get('elemento') or '')) for m in ms]
    pai = list(range(len(ms)))

    def raiz(i):
        while pai[i] != i: pai[i] = pai[pai[i]]; i = pai[i]
        return i
    meio = [np.array([np.interp(_cum(Q)[-1] / 2, _cum(Q), Q[:, 0]), np.interp(_cum(Q)[-1] / 2, _cum(Q), Q[:, 1])]) for Q in P]
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            if chave[i] != chave[j]: continue
            if base[i] and base[i] == base[j]: pai[raiz(i)] = raiz(j); continue
            A, B = P[i], P[j]
            if (A.min(0) - colado > B.max(0)).any() or (B.min(0) - colado > A.max(0)).any(): continue
            toca = min(projetar(B, A[0])[1], projetar(B, A[-1])[1], projetar(A, B[0])[1], projetar(A, B[-1])[1]) < toque
            cola = projetar(B, meio[i])[1] < colado and projetar(A, meio[j])[1] < colado
            fam = familia is not None and familia(ms[i]['elemento']) == familia(ms[j]['elemento']) and np.hypot(*(meio[i] - meio[j])) < 4.0
            if toca or cola or fam: pai[raiz(i)] = raiz(j)
    grupos = {}
    for i in range(len(ms)): grupos.setdefault(raiz(i), []).append(i)
    out = []
    for idx in grupos.values():
        # nós = pontas dos pedaços (juntas a menos de 'toque'); cadeia = pedaços ligados por nós de grau 2
        nos, ponta = [], {}
        for i in idx:
            for k in (0, -1):
                q = P[i][k]; n = next((a for a, c in enumerate(nos) if np.hypot(*(c - q)) < toque), None)
                if n is None: nos.append(q); n = len(nos) - 1
                ponta[(i, k)] = n
        grau = {}
        for i in idx:
            for k in (0, -1): grau[ponta[(i, k)]] = grau.get(ponta[(i, k)], 0) + 1
        usados, cadeias = set(), []
        for i0 in sorted(idx, key=lambda i: grau[ponta[(i, 0)]] == 2 and grau[ponta[(i, -1)]] == 2):   # começa pelas pontas de cadeia
            if i0 in usados: continue
            usados.add(i0); Q = [P[i0]]; mem = [i0]
            for lado in (-1, 0):                       # estende pelo fim e depois pelo começo
                n = ponta[(i0, lado)]
                while grau.get(n, 0) == 2:
                    nx = next(((i, k) for i in idx if i not in usados for k in (0, -1) if ponta[(i, k)] == n), None)
                    if nx is None: break
                    i, k = nx; usados.add(i); mem.append(i)
                    R = P[i] if k == 0 else P[i][::-1]          # pedaço orientado saindo do nó n
                    if lado == -1: Q.append(R[1:])
                    else: Q.insert(0, R[::-1][:-1])
                    n = ponta[(i, -1 if k == 0 else 0)]
            C = np.vstack(Q); cadeias.append((float(_cum(C)[-1]), C, mem))
        cadeias.sort(key=lambda c: -c[0])
        postas = []
        for L, C, mem in cadeias:
            S = _cum(C); c = np.array([np.interp(L / 2, S, C[:, 0]), np.interp(L / 2, S, C[:, 1])])
            if postas and (L < curto or min(np.hypot(*(c - p)) for p in postas) < raio): continue
            postas.append(c)
            nomes = sorted({ms[i]['trecho'] for i in mem})
            out.append({'texto': chave[idx[0]][1], 'P': C, 'n': len(mem), 'disc': chave[idx[0]][0],
                        'rotulo': nomes[0] + (f' (+{len(nomes) - 1} trechos)' if len(nomes) > 1 else '') + (f' ({len(mem)} mergulhos)' if len(mem) > 1 else '')})
    return out
