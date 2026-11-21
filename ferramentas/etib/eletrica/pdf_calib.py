"""Calibra PDF (pt) -> modelo (m, coordenadas locais do modelo) por similaridade, usando caixas (quadrados azuis no PDF
x caixas detectadas no DWG). Uso: python pdf_calib.py TAG  -> work/pdf_T_<TAG>.json"""
import sys, json, math
import numpy as np
import pymupdf as fitz
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
BASE = 'D:/Projeto Modelagem/ETIB-ALAGOINHAS/4 - IMPLANTAÇÃO-20261008T151806Z-1-001/4 - IMPLANTAÇÃO/'
PDF = {'EL1': BASE + '12 - REDE ELÉTRICA E ILUMINAÇÃO/PDF/24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R07.pdf',
       'EL2': BASE + '12 - REDE ELÉTRICA E ILUMINAÇÃO/PDF/24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R05.pdf',
       'CF1': BASE + '15 - DADOS E CFTV/PDF/24-049-ALH-SLJ-ETIB-IMP-PE-CF-001-ELG-R05.pdf',
       'CF2': BASE + '15 - DADOS E CFTV/PDF/24-049-ALH-SLJ-ETIB-IMP-PE-CF-002-ELG-R04.pdf'}

def blue_squares(page):
    """caixas = agrupamentos de segmentos azuis de 8-20 pt (4 lados + X)"""
    segs = []
    for d in page.get_drawings():
        c = d.get('color')
        if not c or not (c[2] > 0.6 and c[0] < 0.3 and c[1] < 0.5): continue
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]; L = math.dist((a.x, a.y), (b.x, b.y))
                if 7 < L < 20: segs.append(((a.x + b.x) / 2, (a.y + b.y) / 2, (a.x, a.y), (b.x, b.y)))
            elif it[0] == 're':
                r = it[1]
                if 6 < r.width < 20 and 6 < r.height < 20: segs += [((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, (r.x0, r.y0), (r.x1, r.y1))] * 4
    cl = []
    for m in segs:
        for c in cl:
            if math.dist(m[:2], c['c']) < 10:
                c['s'].append(m); c['c'] = (sum(x[0] for x in c['s']) / len(c['s']), sum(x[1] for x in c['s']) / len(c['s'])); break
        else: cl.append({'c': m[:2], 's': [m]})
    out = []
    for c in cl:
        if len(c['s']) < 4: continue
        P = [p for x in c['s'] for p in (x[2], x[3])]
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        out.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs)))
    return out

def fit(A, B):
    """similaridade A(pt)->B(m): B = s R A + t"""
    A = np.array(A); B = np.array(B); ca, cb = A.mean(0), B.mean(0)
    A0, B0 = A - ca, B - cb
    H = A0.T @ B0; U, S, Vt = np.linalg.svd(H); R = Vt.T @ U.T
    if np.linalg.det(R) < 0: Vt[1] *= -1; R = Vt.T @ U.T
    s = S.sum() / (A0 ** 2).sum(); t = cb - s * R @ ca
    return s, R, t

def green_ends(page):
    out = []
    for d in page.get_drawings():
        c = d.get('color')
        if not c or not (c[1] > 0.5 and c[0] < 0.3 and c[2] < 0.3): continue
        for it in d['items']:
            if it[0] == 'l': out += [(it[1].x, it[1].y, 0), (it[2].x, it[2].y, 0)]
    return out

def calib(tag, ancoras_modelo, modo='caixas', tol=0.6):
    page = fitz.open(PDF[tag])[0]
    src = blue_squares(page) if modo == 'caixas' else green_ends(page)
    sq = [(x, -y, w) for x, y, w in src]   # y do PDF para cima (sem reflexão no ajuste)
    M = np.array(ancoras_modelo)
    # chute: escala 1:200 = 0,0706 m/pt, eixo y invertido; busca rotação/translação por casamento iterativo
    best = None
    for th in np.radians(np.arange(-12, 12.01, 0.25)):
        R0 = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * 0.0706
        P = np.array([R0 @ np.array(q[:2]) for q in sq])
        # translação por votação: diferenças entre todos os pares
        diffs = (M[:, None, :] - P[None, :, :]).reshape(-1, 2)
        key = np.round(diffs / 0.5).astype(int)
        u, cnt = np.unique(key, axis=0, return_counts=True)
        k = cnt.argmax()
        if best is None or cnt[k] > best[0]: best = (cnt[k], th, R0, u[k] * 0.5)
    _, th, R0, t0 = best
    print('  quadrados PDF', len(sq), '| votos', best[0], '| rot inicial %.2f°' % math.degrees(th))
    # pares iniciais e refinamento
    pairs = []
    for i, q in enumerate(sq):
        p = R0 @ np.array(q[:2]) + t0
        d = np.linalg.norm(M - p, axis=1); j = d.argmin()
        if d[j] < 1.5: pairs.append((q[:2], M[j]))
    for _ in range(3):
        s, R, t = fit([a for a, b in pairs], [b for a, b in pairs])
        pairs = []
        for q in sq:
            p = s * R @ np.array(q[:2]) + t
            d = np.linalg.norm(M - p, axis=1); j = d.argmin()
            if d[j] < tol: pairs.append((q[:2], M[j]))
    s, R, t = fit([a for a, b in pairs], [b for a, b in pairs])
    res = [float(np.linalg.norm(s * R @ np.array(a) + t - b)) for a, b in pairs]
    out = dict(tag=tag, s=float(s), R=R.tolist(), t=t.tolist(), n=len(pairs), residuo_max=max(res), residuo_med=float(np.mean(res)),
               rot_deg=math.degrees(math.atan2(R[1][0], R[0][0])), quadrados_pdf=len(sq))
    json.dump(out, open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/pdf_T_{tag}.json', 'w'), indent=1)
    return out

if __name__ == '__main__':
    tag = sys.argv[1]
    X = json.load(open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/rede_{tag}.json'))
    modo = sys.argv[2] if len(sys.argv) > 2 else 'caixas'
    if modo == 'caixas': anc = [b['c'] for b in X['boxes'] if -38 < b['c'][0] < 110 and -118 < b['c'][1] < 70]
    else: anc = [r['pts'][0] for r in X['runs']] + [r['pts'][-1] for r in X['runs']]
    o = calib(tag, anc, modo, 0.6 if modo == 'caixas' else 0.08)
    print(tag, 'escala %.5f m/pt' % o['s'], 'rot %.4f°' % o['rot_deg'], 'pares %d de %d âncoras (%d quadrados no PDF)' % (o['n'], len(anc), o['quadrados_pdf']),
          'resíduo máx %.3f m, médio %.3f m' % (o['residuo_max'], o['residuo_med']))
