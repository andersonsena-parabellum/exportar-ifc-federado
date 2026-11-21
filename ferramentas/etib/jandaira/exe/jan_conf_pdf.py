# -*- coding: utf-8 -*-
"""Conferência das pranchas no PDF (20/10/2026, pedido do Anderson + Revisão de qualidade): por folha, quantas notas "PROF."
há, se alguma se repete no mesmo lugar (3+ iguais a menos de 60 pt) e se alguma nota cobre outro texto da folha (inclusive o
da arquitetura, que vem de bloco). Uso: python -X utf8 jan_conf_pdf.py <pasta ou pdf> ..."""
import os, sys, glob, collections
import numpy as np
import pymupdf as fitz
sys.stdout.reconfigure(encoding='utf-8')


def conferir(fn):
    pg = fitz.open(fn)[0]; W = pg.get_text('words')
    linhas = collections.defaultdict(list)
    for w in W: linhas[(w[5], w[6])].append(w)
    notas, outros = [], []
    for k, ws in linhas.items():
        txt = ' '.join(w[4] for w in ws); r = fitz.Rect(min(w[0] for w in ws), min(w[1] for w in ws), max(w[2] for w in ws), max(w[3] for w in ws))
        (notas if txt.startswith('PROF.') else outros).append((txt, r, ws))
    # palavras a palavra para os "outros" (a linha inteira de um MTEXT pode ser larga)
    palavras = [(w[4], fitz.Rect(w[:4])) for _, _, ws in outros for w in ws]
    cobre = []
    for t, r, _ in notas:
        rr = fitz.Rect(r.x0 + 0.3, r.y0 + 0.3, r.x1 - 0.3, r.y1 - 0.3)
        # sobreposição de verdade: a faixa comum tem mais da metade da altura do menor (linhas empilhadas com folga não contam)
        hit = [p for p, q in palavras if rr.intersects(q) and (rr & q).height > 0.5 * min(rr.height, q.height)
               and (rr & q).get_area() > 0.25 * min(rr.get_area(), q.get_area())]
        if hit: cobre.append((t, hit[:4]))
    P = np.array([((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2) for _, r, _ in notas]) if notas else np.zeros((0, 2))
    rep = 0
    for i, (t, _, _) in enumerate(notas):
        d = np.hypot(*(P - P[i]).T); iguais = [j for j in np.nonzero(d < 60)[0] if notas[j][0] == t]
        rep = max(rep, len(iguais))
    print(f'{os.path.basename(fn)[20:-4]}: {len(notas)} notas; maior repetição local {rep}; {len(cobre)} nota(s) sobre texto')
    for t, h in cobre: print('    ', t, '×', h)


for a in sys.argv[1:]:
    for fn in ([a] if a.endswith('.pdf') else sorted(glob.glob(os.path.join(a, '*.pdf')))): conferir(fn)
