# -*- coding: utf-8 -*-
"""Miniaturas ANTES | DEPOIS de cada folha alterada, para o Anderson olhar no celular junto com o "pronto para envio"
(PDCA A3, 22/10/2026; regra em AGENTS.md > Pranchas > Prévia).
Para cada PDF revisado acha a revisão de origem (mesma regra da Revisão de qualidade: _SUPERADAS do CDE, depois PROJETO_ORIGINAL),
compara a área de desenho das duas folhas e grava <saida>/<folha>_antes_depois.jpg: a folha inteira antes e depois, lado a lado, com as regiões que
mudaram em vermelho, e embaixo os recortes ampliados dessas regiões (até 4). A coluna da direita (legendas, notas e carimbo) fica fora da comparação.
Uso: ..\\..\\.venv\\Scripts\\python.exe -X utf8 miniaturas.py <pasta ou PDF revisado> --origem <pasta> [<pasta> ...] [--saida PASTA]
     (ou rever.py --miniaturas <pasta> --origem ...)"""
import os, sys, glob, argparse
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
import pdf_conf as PC
from rev_comum import folha

LARG = 1600            # px da imagem final (cabe no celular deitado e dá para ampliar)
VERM = (214, 40, 30)


def _fonte(t):
    for f in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf'):
        try: return ImageFont.truetype(f, t)
        except OSError: pass
    return ImageFont.load_default()


def _render(pdf, dpi, clip=None):
    p = pymupdf.open(pdf)[0]
    pix = p.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), clip=clip, alpha=False)
    return Image.frombytes('RGB', (pix.width, pix.height), pix.samples), p


def _engrossa(X, n):
    Y = X.copy()
    for _ in range(n):
        Z = Y.copy(); Z[1:] |= Y[:-1]; Z[:-1] |= Y[1:]; Z[:, 1:] |= Y[:, :-1]; Z[:, :-1] |= Y[:, 1:]; Y = Z
    return Y


def regioes(antes, depois, dpi=36, blk=12, nmax=6, larg_max=160):
    """regiões que mudaram (em pontos da página girada, page.rect), da maior para a menor.
    Compara presença de traço, não tom: um traço só conta como mudança se não houver traço na outra folha a ~2 mm. Assim a diferença de
    plotagem (CTB, espessura, retícula da revisão de origem plotada pelo projetista) não vira região alterada."""
    pa = pymupdf.open(antes)[0]; pb = pymupdf.open(depois)[0]
    def tinta(p):
        pix = p.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), colorspace=pymupdf.csGRAY, alpha=False)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    A, B = tinta(pa), tinta(pb)
    h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1]); A, B = A[:h, :w], B[:h, :w]
    # traço bem visível (< 200) de um lado sem nenhum vestígio (< 254) do outro a ~2 mm: a linha clarinha da plotagem do projetista conta
    D = ((A < 200) & ~_engrossa(B < 254, 3)) | ((B < 200) & ~_engrossa(A < 254, 3))
    # fora a coluna da direita (legendas, notas e carimbo): a prévia é do desenho. O pixmap e o clip estão na página já girada (page.rect).
    s = dpi / 72; Wp, Hp = pb.rect.width, pb.rect.height
    D[:, int((Wp - PC.COLUNA_W * PC.MM) * s):] = False
    Hh, Ww = h // blk, w // blk
    M = D[:Hh * blk, :Ww * blk].reshape(Hh, blk, Ww, blk).sum(axis=(1, 3)) > 3
    # agrupa blocos vizinhos; grupo maior que larg_max mm (mudança espalhada) é dividido em janelas desse tamanho
    vis = np.zeros_like(M); grupos = []; jan = max(1, int(larg_max * PC.MM * s / blk))
    for i, j in zip(*np.nonzero(M)):
        if vis[i, j]: continue
        pilha = [(i, j)]; vis[i, j] = True; cel = []
        while pilha:
            a_, b_ = pilha.pop(); cel.append((a_, b_))
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    x, y = a_ + da, b_ + db
                    if 0 <= x < Hh and 0 <= y < Ww and M[x, y] and not vis[x, y]: vis[x, y] = True; pilha.append((x, y))
        por = {}
        for a_, b_ in cel: por.setdefault((a_ // jan, b_ // jan), []).append((a_, b_))
        for c2 in por.values():
            I = [c[0] for c in c2]; J = [c[1] for c in c2]
            grupos.append((len(c2), pymupdf.Rect(min(J) * blk / s, min(I) * blk / s, (max(J) + 1) * blk / s, (max(I) + 1) * blk / s)))
    grupos.sort(key=lambda g: -g[0])
    out = []
    for n, r in grupos:
        r = r + (-20 * PC.MM, -20 * PC.MM, 20 * PC.MM, 20 * PC.MM)        # margem de 20 mm em volta
        if r.width < 120 * PC.MM: r = pymupdf.Rect(r.x0 - (120 * PC.MM - r.width) / 2, r.y0, r.x1 + (120 * PC.MM - r.width) / 2, r.y1)
        if r.height < 80 * PC.MM: r = pymupdf.Rect(r.x0, r.y0 - (80 * PC.MM - r.height) / 2, r.x1, r.y1 + (80 * PC.MM - r.height) / 2)
        if any((pymupdf.Rect(r) & o).get_area() > 0.5 * min(r.get_area(), o.get_area()) for o in out): continue
        out.append(r & pb.rect)
        if len(out) >= nmax: break
    return out, len(grupos)


def miniatura(antes, depois, saida):
    """grava a imagem antes | depois de uma folha; devolve o caminho e o número de regiões alteradas."""
    f = folha(depois); nome = (f['curto'] + f' R{f["rev"]:02d}') if f else os.path.basename(depois)
    fa = folha(antes); nome_a = (fa['curto'] + f' R{fa["rev"]:02d}') if fa else os.path.basename(antes)
    regs, n = regioes(antes, depois)
    meia = (LARG - 30) // 2
    pb = pymupdf.open(depois)[0]
    dpi = 72 * meia / max(pb.rect.width, pb.rect.height)
    ia, pa_ = _render(antes, dpi); ib, pb_ = _render(depois, dpi)
    # marca as regiões nas duas folhas inteiras
    for im in (ia, ib):
        dr = ImageDraw.Draw(im)
        for k, r in enumerate(regs):
            q = r * (dpi / 72)
            dr.rectangle([q.x0, q.y0, q.x1, q.y1], outline=VERM, width=3)
            dr.text((q.x0 + 4, q.y0 + 2), str(k + 1), fill=VERM, font=_fonte(22))
    # recortes ampliados lado a lado
    linhas = []
    for k, r in enumerate(regs):
        z = 72 * meia / max(r.width, r.height)
        a, _ = _render(antes, z, r); b, _ = _render(depois, z, r)
        linhas.append((k + 1, a, b))
    alt_top = max(ia.height, ib.height)
    H = 70 + alt_top + sum(30 + max(a.height, b.height) + 10 for _, a, b in linhas) + 20
    out = Image.new('RGB', (LARG, H), 'white'); dr = ImageDraw.Draw(out)
    dr.text((10, 10), f'{nome}  ·  {n} região(ões) alterada(s)' + (f', {len(regs)} ampliada(s)' if regs else ''), fill='black', font=_fonte(28))
    dr.text((10, 44), f'ANTES ({nome_a})', fill=(90, 90, 90), font=_fonte(20)); dr.text((meia + 30, 44), f'DEPOIS ({nome})', fill=(90, 90, 90), font=_fonte(20))
    out.paste(ia, (10, 70)); out.paste(ib, (meia + 20, 70))
    y = 70 + alt_top + 10
    for k, a, b in linhas:
        dr.text((10, y + 4), f'{k}  antes', fill=VERM, font=_fonte(20)); dr.text((meia + 20, y + 4), f'{k}  depois', fill=VERM, font=_fonte(20))
        y += 30; out.paste(a, (10, y)); out.paste(b, (meia + 20, y))
        dr.rectangle([10, y, 10 + a.width, y + a.height], outline=(200, 200, 200)); dr.rectangle([meia + 20, y, meia + 20 + b.width, y + b.height], outline=(200, 200, 200))
        y += max(a.height, b.height) + 10
    os.makedirs(saida, exist_ok=True)
    fn = os.path.join(saida, (f['stem'] if f else os.path.splitext(os.path.basename(depois))[0]) + '_antes_depois.jpg')
    out.save(fn, quality=82, optimize=True)
    return fn, n


def gerar(alvo, origens, saida=None, log=print):
    """todas as folhas revisadas da pasta (ou um PDF); folha sem origem é avisada e fica de fora."""
    pdfs = sorted(glob.glob(os.path.join(alvo, '*.pdf'))) if os.path.isdir(alvo) else [alvo]
    saida = saida or os.path.join(os.path.dirname(pdfs[0]) if pdfs else alvo, '_miniaturas')
    feitos = []
    for x in pdfs:
        o = PC.origem_da_folha(x, origens)
        if not o: log(f'  {os.path.basename(x)}: sem revisão de origem, fica sem miniatura'); continue
        fn, n = miniatura(o, x, saida); feitos.append(fn)
        log(f'  {os.path.basename(fn)}: {n} região(ões) alterada(s) em relação a {os.path.basename(o)}')
    return feitos


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('alvo'); ap.add_argument('--origem', nargs='+', required=True); ap.add_argument('--saida')
    a = ap.parse_args()
    gerar(a.alvo, a.origem, a.saida)
