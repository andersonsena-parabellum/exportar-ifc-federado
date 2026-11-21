# PDF de entrega = PDF do AutoCAD (R03, conteúdo aprovado) com o carimbo trocado pelo carimbo AB R00 renderizado na nuvem
import fitz, numpy as np, json, os
import sys
ROT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
mm = 72 / 25.4; CAB, LIN = 117.6, 3.83
R = {os.path.basename(r['dwg'])[:-4]: r for r in json.load(open('/tmp/claude-0/jan/ab/relatorio.json'))}
def ink(p, clip=None, dpi=144):
    px = p.get_pixmap(clip=clip, dpi=dpi); a = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, px.n)[:, :, :3].min(axis=2) < 200
    return a, px
OUT = '/tmp/claude-0/jan/final'; os.makedirs(OUT, exist_ok=True)
NOVO = {'AF-001-HIG': 'AGF-001-HIG', 'DRE-001-DRG': 'DRE-001-DRG', 'EL-001-ELG': 'ELE-001-ELG', 'EL-002-ELG': 'ELE-002-ELG', 'IN-001-ING': 'PCI-001-ING'}
for k in ['AF-001-HIG', 'DRE-001-DRG', 'EL-001-ELG', 'EL-002-ELG', 'IN-001-ING']:
    n = f'AA-CTR-MUN-LOC-ETIB-IMP-AB-{NOVO[k]}-R00'
    A = fitz.open(f'/tmp/claude-0/jan/pdf_r03/{k}.pdf'); pa = A[0]
    C = fitz.open(f'/tmp/claude-0/jan/so/{n}.pdf'); pc = C[0]
    B = fitz.open(f'/tmp/claude-0/jan/ab_antigo/AA-CTR-MUN-LOC-ETIB-IMP-AB-{k}-R00.pdf'); pb = B[0]   # folha inteira da nuvem (1ª rodada; o carimbo fica no mesmo lugar)
    # deslocamento AutoCAD -> nuvem medido no corpo do carimbo (logos e linhas, iguais nas duas)
    a, _ = ink(pa, fitz.Rect(3370 - 200 * mm, 2383 - 60 * mm, 3370, 2383), 288); b, _ = ink(pb, fitz.Rect(3370 - 200 * mm, 2383 - 60 * mm, 3370, 2383), 288)
    h = min(a.shape[0], b.shape[0]); a, b = a[:h], b[:h]
    s, dx, dy = max(((np.roll(np.roll(a, y, 0), x, 1) & b).sum(), x, y) for x in range(-24, 25) for y in range(-24, 25))
    d = fitz.Point(dx / 4, dy / 4)            # pt (288 dpi)
    m, px = ink(pc); ys, xs = np.nonzero(m); f = 72 / 144
    rc = fitz.Rect(xs.min() * f - 1, ys.min() * f - 1, (xs.max() + 1) * f + 1, (ys.max() + 1) * f + 1)   # carimbo novo, coords da nuvem
    # o PDF só do carimbo sai com outro enquadramento: acha o carimbo na folha inteira da nuvem (pb) por correlação
    est = fitz.Point(3370 - 12.1 * mm - rc.width, 2383 - 12.2 * mm - rc.height)      # canto aproximado (medido nas prévias)
    tpl = m[int(rc.y0 / f):int(rc.y1 / f), int(rc.x0 / f):int(rc.x1 / f)]
    reg = fitz.Rect(est.x - 15 * mm, est.y - 15 * mm, est.x + rc.width + 15 * mm, est.y + rc.height + 15 * mm)
    g, _ = ink(pb, reg); H, W = tpl.shape
    sc, ox, oy = max(((g[y:y + H, x:x + W][:H, :W] & tpl[:g.shape[0] - y, :g.shape[1] - x]).sum(), x, y)
                     for x in range(0, g.shape[1] - W + 1, 2) for y in range(0, g.shape[0] - H + 1, 2))
    rb = fitz.Rect(reg.x0 + ox * f, reg.y0 + oy * f, reg.x0 + ox * f + rc.width, reg.y0 + oy * f + rc.height)   # carimbo na folha da nuvem
    print('  correlação', round(sc / tpl.sum(), 2))
    # ajuste fino direto contra o carimbo antigo do PDF do AutoCAD (linhas e logos do bloco, iguais nos dois), a 288 dpi
    t2, _ = ink(pc, rc, 288); est2 = rb - (d.x, d.y, d.x, d.y); best = None
    reg2 = fitz.Rect(est2.x0 - 4 * mm, est2.y1 - 125 * mm, est2.x1 + 4 * mm, est2.y1 + 4 * mm)
    g2, _ = ink(pa, reg2, 288); t2 = t2[-int(121 * mm * 4):, :]          # só o corpo do bloco (sem o quadro, que mudou)
    H2_, W2_ = t2.shape; y_base = g2.shape[0] - H2_
    for x in range(0, g2.shape[1] - W2_ + 1):
        for y in range(max(0, y_base - 40), min(g2.shape[0] - H2_, y_base) + 1):
            v = (g2[y:y + H2_, x:x + W2_] & t2).sum()
            if best is None or v > best[0]: best = (v, x, y)
    ra = fitz.Rect(reg2.x0 + best[1] / 4, reg2.y0 + best[2] / 4 + H2_ / 4 - rc.height, 0, 0); ra.x1 = ra.x0 + rc.width; ra.y1 = ra.y0 + rc.height
    print('  ajuste fino', round(best[0] / t2.sum(), 2), 'desvio do 1º encaixe (pt):', round(ra.x0 - est2.x0, 2), round(ra.y0 - est2.y0, 2))
    nold = R[n]['carimbos'][0]['linhas_saem']
    topo_antigo = rb.y1 - (CAB + nold * LIN + 0.8) * mm
    topo_antigo = ra.y1 - (CAB + nold * LIN + 0.8) * mm
    # linha horizontal que sobra acima do quadro antigo (topo da última linha): procura até 8 mm acima e cobre até ela
    faixa = fitz.Rect(ra.x0 + 5 * mm, topo_antigo - 8 * mm, ra.x1 - 5 * mm, topo_antigo + 1 * mm)
    hl = ink(pa, faixa, 600)[0].mean(axis=1) > 0.8
    if hl.any(): topo_antigo = min(topo_antigo, faixa.y0 + np.nonzero(hl)[0].min() * 72 / 600 - 0.5)
    # 1 pt de folga em volta do carimbo: a moldura da folha corre a 2 pt da borda dele e não pode sumir
    branco = fitz.Rect(ra.x0 + 0.8, min(ra.y0, topo_antigo), ra.x1 - 0.8, ra.y1 - 0.8)
    # moldura da folha à direita: em algumas folhas ela coincide com a borda do carimbo (AGF, ELE) e o branco não pode
    # cobri-la acima do carimbo novo; mede a moldura 160 mm acima da base, fora dos dois carimbos
    yf = ra.y1 - 160 * mm; fx = fitz.Rect(ra.x1 - 4 * mm, yf, ra.x1 + 4 * mm, yf + 1)
    pxf = pa.get_pixmap(clip=fx * dr, dpi=600) if pa.rotation == 0 else None
    seg = ink(pa, fitz.Rect(ra.x1 - 4 * mm, yf, ra.x1 + 4 * mm, yf + 0.5), 600)[0].any(axis=0)
    xs_f = [fx.x0 + c * 72 / 600 for c in np.nonzero(seg)[0]]
    if xs_f: branco.x1 = min(branco.x1, min(x for x in xs_f if x > ra.x1 - 3) - 0.15) if any(x > ra.x1 - 3 for x in xs_f) else branco.x1
    dr = pa.derotation_matrix                 # o PDF do AutoCAD vem com /Rotate 270: desenhar nas coordenadas sem rotação
    pa.draw_rect(branco * dr, color=None, fill=(1, 1, 1), overlay=True)
    pa.show_pdf_page(fitz.Rect(ra.x0 + 0.8, ra.y0 + 0.8, ra.x1 - 0.8, ra.y1 - 0.8) * dr, C, 0, clip=fitz.Rect(rc.x0 + 0.8, rc.y0 + 0.8, rc.x1 - 0.8, rc.y1 - 0.8), keep_proportion=False, rotate=ROT)
    A.save(f'{OUT}/{n}.pdf', garbage=3, deflate=True)
    print('  branco até x =', round(branco.x1, 2), '| moldura em', [round(x, 1) for x in xs_f][:1])
    print(k, 'd=', tuple(d), 'sobrep', round(s / max(1, b.sum()), 2), 'carimbo', tuple(round(v) for v in rb), 'linhas antigas', nold)
