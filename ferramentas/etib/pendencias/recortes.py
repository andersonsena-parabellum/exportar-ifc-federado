# -*- coding: utf-8 -*-
"""Página de pendências: recorte da PRANCHA do projetista em cada ficha, centrado no ponto e marcado no círculo vermelho, com os códigos
citados no texto da ficha escritos ao lado dos elementos (a prancha original não traz "DRN-164" ou "CX03": checklist F3).
Generalizado de exemplo/pendencias/sat_recortes.py (escola C) e ETIB-<ESCOLA>/RELATORIOS/fonte_pendencias_R03/recortes_prancha.py.
Caminho UTM -> DWG pela transformação do georreferenciamento (rot_deg, t do JSON) e DWG -> PDF por textos iguais e únicos no DXF da
folha e no PDF (semelhança com RANSAC)."""
import os, sys, re, math, json
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import asbuilt as ab

JANELA = 26.0           # m de largura do recorte (padrão); as fichas podem pedir mais com 'raio'
VERM = (214, 40, 30)
AZUL = (20, 70, 170)


def _fonte(t):
    for f in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf'):
        try: return ImageFont.truetype(f, t)
        except OSError: pass
    return ImageFont.load_default()


def similar(P, Q):
    mp, mq = P.mean(0), Q.mean(0); X, Y = P - mp, Q - mq
    U, S, Vt = np.linalg.svd(Y.T @ X); D = np.eye(2)
    if np.linalg.det(U @ Vt) < 0: D[1, 1] = -1
    R = U @ D @ Vt; s = np.trace(np.diag(S) @ D) / (X ** 2).sum()
    return s, R, mq - s * R @ mp


def calibrar(dxf, pdf, log=print):
    """(documento com a página sem giro, função DXF -> ponto do PDF). Pares = textos que aparecem uma vez só nos dois."""
    E = ab.entidades(dxf, blocos=True)
    Pl = ab.Plano.__new__(ab.Plano); dx = {}
    for e in E:
        if e['typ'] not in ('TEXT', 'MTEXT', 'BTXT'): continue
        s = ab._limpo(e.get('txt', '')).strip()
        if not re.fullmatch(r'[A-Za-z0-9\-\.,/=%]{3,}', s) or not re.search(r'\d', s): continue
        a, tw, th, p0 = Pl._ret_texto(e)
        u = np.array([math.cos(a), math.sin(a)]); v = np.array([-u[1], u[0]])
        dx.setdefault(s, []).append(p0 + u * tw / 2 + v * th / 2)
    doc = pymupdf.open(pdf); pg = doc[0]; doc.rot0 = pg.rotation; pg.set_rotation(0)
    pw = {}
    for w in pg.get_text('words'): pw.setdefault(w[4].strip(), []).append(np.array([(w[0] + w[2]) / 2, (w[1] + w[3]) / 2]))
    pares = [(dx[s][0], pw[s][0]) for s in dx if len(dx[s]) == 1 and len(pw.get(s, [])) == 1]
    if len(pares) < 4:
        # folha com poucas etiquetas numéricas (escola E, 23/10/2026): casa a linha inteira de texto (ex.: "Muro h=3,15",
        # "FUNDO DE CASA"), sem exigir dígito, entre o DXF e as linhas do PDF
        norm = lambda s: re.sub(r'\s+', ' ', s).strip().upper()
        dl = {}
        for e in E:
            if e['typ'] not in ('TEXT', 'MTEXT', 'BTXT'): continue
            s = norm(ab._limpo(e.get('txt', '')).replace('\\P', ' '))
            if len(s) < 3 or not re.search(r'[A-Z0-9]', s): continue
            a, tw, th, p0 = Pl._ret_texto(e)
            u = np.array([math.cos(a), math.sin(a)]); v = np.array([-u[1], u[0]])
            dl.setdefault(s, []).append(p0 + u * tw / 2 + v * th / 2)
        pl = {}
        for b in pg.get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                s = norm(' '.join(sp['text'] for sp in ln['spans']))
                if s: x0, y0, x1, y1 = ln['bbox']; pl.setdefault(s, []).append(np.array([(x0 + x1) / 2, (y0 + y1) / 2]))
        pares += [(dl[s][0], pl[s][0]) for s in dl if len(dl[s]) == 1 and len(pl.get(s, [])) == 1 and s not in dx]
    if len(pares) < 4: raise RuntimeError(f'{os.path.basename(pdf)}: só {len(pares)} textos em comum entre o DXF e o PDF')
    P = np.array([p for p, _ in pares]); Q = np.array([q for _, q in pares]) * np.array([1, -1])
    rng = np.random.default_rng(0); melhor = None
    for _ in range(3000):
        i = rng.choice(len(P), 2, replace=False); s, R, t = similar(P[i], Q[i])
        if not (0.5 < s < 50): continue
        ok = np.linalg.norm((s * (R @ P.T)).T + t - Q, axis=1) < 4.0
        if melhor is None or ok.sum() > melhor[0]: melhor = (ok.sum(), ok)
    ok = melhor[1]; s, R, t = similar(P[ok], Q[ok])
    r = np.linalg.norm((s * (R @ P[ok].T)).T + t - Q[ok], axis=1)
    log(f'  {os.path.basename(pdf)}: {len(pares)} pares de texto, {ok.sum()} usados, escala {s:.3f} pt/m, resíduo mediano {np.median(r):.1f} pt')
    return doc, lambda D: (s * (R @ np.atleast_2d(D).T)).T * np.array([1, -1]) + t * np.array([1, -1])


def folhas(cfg, log=print):
    """{folha: (documento, função UTM -> ponto do PDF sem giro, nome do PDF)} das folhas da configuração."""
    TJ = None
    if cfg.get('transf_json'):
        J = json.load(open(cfg['transf_json'], encoding='utf-8'))['arquivos']
        TJ = J if isinstance(J, dict) else {a['arquivo_original']: a for a in J}
    out = {}
    for f, d in cfg['folhas'].items():
        doc, d2p = calibrar(d['dxf'], d['pdf'], log)
        if d.get('chave'):
            T = TJ[d['chave']]; a = math.radians(T['rot_deg']); t = np.array(T['t'])
            Rr = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            u2p = lambda U, Rr=Rr, t=t, d2p=d2p: d2p((Rr.T @ (np.atleast_2d(U)[:, :2] - t).T).T)
        else:
            u2p = lambda U, d2p=d2p: d2p(np.atleast_2d(U)[:, :2])
        out[f] = (doc, u2p, os.path.splitext(os.path.basename(d['pdf']))[0])
    return out


def _gira_ponto(x, y, w, h, rot):
    """ponto da imagem antes de Image.rotate(-rot, expand=True) -> depois (giro horário de rot graus, múltiplo de 90)."""
    rot %= 360
    if rot == 90: return h - 1 - y, x
    if rot == 180: return w - 1 - x, h - 1 - y
    if rot == 270: return y, w - 1 - x
    return x, y


def _rotulos(dr, pontos, W, H, tam):
    """escreve cada código numa etiqueta branca com borda azul, ligada ao elemento por uma linha; evita sobrepor as etiquetas."""
    fonte = _fonte(tam); feitas = []
    for cod, (x, y) in pontos:
        if not (0 <= x < W and 0 <= y < H): continue
        tw, th = dr.textbbox((0, 0), cod, font=fonte)[2:]
        for dx, dy in ((30, -40), (30, 30), (-tw - 40, -40), (-tw - 40, 30), (30, -90), (-tw - 40, -90), (30, 80), (-tw - 40, 80)):
            bx, by = min(max(4, x + dx), W - tw - 12), min(max(4, y + dy), H - th - 10)
            caixa = (bx - 4, by - 3, bx + tw + 4, by + th + 5)
            if not any(caixa[0] < c[2] and c[0] < caixa[2] and caixa[1] < c[3] and c[1] < caixa[3] for c in feitas): break
        feitas.append(caixa)
        cx, cy = min(max(x, caixa[0]), caixa[2]), min(max(y, caixa[1]), caixa[3])
        dr.line([(x, y), (cx, cy)], fill=AZUL, width=2)
        dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=AZUL)
        dr.rectangle(caixa, fill=(255, 255, 255), outline=AZUL, width=2)
        dr.text((bx, by), cod, fill=AZUL, font=fonte)


def recortar(ficha, k, folha_nome, F, pasta, pos_codigos):
    """grava <pasta>/NN_prancha_<folha>.jpg e devolve o nome; None se o ponto cai fora da folha.
    pos_codigos: [(código, E, N)] dos elementos citados na ficha (posição no modelo, perto do ponto)."""
    doc, u2p, _ = F; pg = doc[0]
    q = np.array([ficha['E'], ficha['N']])
    jan = max(JANELA, 2.2 * ficha.get('raio', 12))           # ficha de área grande (raio > 12 m) abre um recorte maior
    h = jan * 514 / 800
    cant = u2p(np.array([[q[0] - jan / 2, q[1] - h / 2], [q[0] + jan / 2, q[1] + h / 2], [q[0] - jan / 2, q[1] + h / 2], [q[0] + jan / 2, q[1] - h / 2]]))
    c0 = u2p(q[None])[0]; lo, hi = cant.min(0), cant.max(0)
    rect = pymupdf.Rect(lo[0], lo[1], hi[0], hi[1])
    if not rect.intersects(pg.rect): return None
    zoom = 1100 / rect.width
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False)
    im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    paraimg = lambda p: ((p[0] - rect.x0) * zoom, (p[1] - rect.y0) * zoom)
    x, y = paraimg(c0)
    cods = [(c, paraimg(u2p(np.array([[E, N]]))[0])) for c, E, N in pos_codigos]
    if doc.rot0:
        w0, h0 = im.size; im = im.rotate(-doc.rot0, expand=True)
        x, y = _gira_ponto(x, y, w0, h0, doc.rot0); cods = [(c, _gira_ponto(a, b, w0, h0, doc.rot0)) for c, (a, b) in cods]
    dr = ImageDraw.Draw(im); r = 0.06 * min(im.size)
    for j in range(4): dr.ellipse([x - r - j, y - r - j, x + r + j, y + r + j], outline=VERM)
    for a_, b_ in (((x - r * 1.6, y), (x - r * 1.1, y)), ((x + r * 1.1, y), (x + r * 1.6, y)), ((x, y - r * 1.6), (x, y - r * 1.1)), ((x, y + r * 1.1), (x, y + r * 1.6))):
        dr.line([a_, b_], fill=VERM, width=3)
    _rotulos(dr, cods, im.width, im.height, max(18, im.width // 45))
    nome = f'{k:02d}_prancha_{folha_nome}.jpg'
    im.save(os.path.join(pasta, nome), quality=85)
    return nome
