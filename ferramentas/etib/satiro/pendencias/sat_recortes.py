# -*- coding: utf-8 -*-
"""Sátiro Dias — recorte da PRANCHA de cada disciplina no ponto de cada ficha da página de pendências (o projetista reconhece o
lugar na prancha dele), como em Alagoinhas (ETIB-ALAGOINHAS/RELATORIOS/fonte_pendencias_R03/recortes_prancha.py):
UTM -> DWG pela transformação do georreferenciamento (CAD_GEORREFERENCIADO/transformacoes_local_para_UTM.json) e DWG -> PDF por
textos iguais e únicos no DXF da folha e no PDF (semelhança com RANSAC). Folhas revisadas: o PDF da revisão nova; DRE-001 (não
revisada): o PDF original do CDE com o DXF georreferenciado. Grava img/NN_prancha_<FOLHA>.jpg e img/prancha.json.
Uso: python -X utf8 sat_recortes.py"""
import os, sys, json, re, math
import numpy as np
import pymupdf
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
import asbuilt as ab

AQUI = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(AQUI, 'img')
BASE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS'
EXE = os.path.join(BASE, r'RELATORIOS\EXECUTIVO_2026-10-21')
GEO = r'C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\b28e7087-be02-4c86-8417-721af249be58\scratchpad\work\geo'
TJ = json.load(open(os.path.join(BASE, r'CAD_GEORREFERENCIADO\transformacoes_local_para_UTM.json'), encoding='utf-8'))['arquivos']
# folha -> (DXF, PDF, chave da transformação; None = DXF já em UTM)
FOLHAS = {
    'AF-001': (EXE + r'\_copias\24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00.dxf', EXE + r'\PDF\24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R01.pdf',
               'PROJETO_ORIGINAL/IMP/01_AF/24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00.dwg'),
    'ESG-001': (EXE + r'\_copias\24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00.dxf', EXE + r'\PDF\24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R01.pdf',
                'PROJETO_ORIGINAL/IMP/02_ESG/24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00.dwg'),
    'EL-001': (EXE + r'\_copias\24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01.dxf', EXE + r'\PDF\24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R02.pdf',
               'PROJETO_ORIGINAL/IMP/04_ELE/24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01.dwg'),
    'DRE-001': (GEO + r'\24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02_GEO.dxf',
                r'D:\Projeto Modelagem\PRANCHAS\ETIB-SATIRO-DIAS\24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02.pdf', None),
}
JANELA = 26.0


def similar(P, Q):
    mp, mq = P.mean(0), Q.mean(0); X, Y = P - mp, Q - mq
    U, S, Vt = np.linalg.svd(Y.T @ X); D = np.eye(2)
    if np.linalg.det(U @ Vt) < 0: D[1, 1] = -1
    R = U @ D @ Vt; s = np.trace(np.diag(S) @ D) / (X ** 2).sum()
    return s, R, mq - s * R @ mp


def calibrar(dxf, pdf):
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
    P = np.array([p for p, _ in pares]); Q = np.array([q for _, q in pares]) * np.array([1, -1])
    rng = np.random.default_rng(0); melhor = None
    for _ in range(3000):
        i = rng.choice(len(P), 2, replace=False); s, R, t = similar(P[i], Q[i])
        if not (0.5 < s < 50): continue
        ok = np.linalg.norm((s * (R @ P.T)).T + t - Q, axis=1) < 4.0
        if melhor is None or ok.sum() > melhor[0]: melhor = (ok.sum(), ok)
    ok = melhor[1]; s, R, t = similar(P[ok], Q[ok])
    r = np.linalg.norm((s * (R @ P[ok].T)).T + t - Q[ok], axis=1)
    print(f'  {os.path.basename(pdf)}: {len(pares)} pares de texto, {ok.sum()} usados, escala {s:.3f} pt/m, resíduo mediano {np.median(r):.1f} pt')
    return doc, lambda D: (s * (R @ np.atleast_2d(D).T)).T * np.array([1, -1]) + t * np.array([1, -1])


def main():
    from PIL import Image, ImageDraw
    F = json.load(open(os.path.join(AQUI, 'fichas.json'), encoding='utf-8'))
    cal = {}
    for f, (dxf, pdf, chave) in FOLHAS.items():
        doc, d2p = calibrar(dxf, pdf)
        if chave:
            rot, t = TJ[chave]['rot_deg'], np.array(TJ[chave]['t']); a = math.radians(rot)
            Rr = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            cal[f] = (doc, lambda U, Rr=Rr, t=t, d2p=d2p: d2p((Rr.T @ (np.atleast_2d(U)[:, :2] - t).T).T))
        else:
            cal[f] = (doc, lambda U, d2p=d2p: d2p(np.atleast_2d(U)[:, :2]))
    saida = {}
    for k, c in enumerate(F):
        q = np.array([c['E'], c['N']]); saida[c['n']] = []
        for f in c['folhas']:
            doc, u2p = cal[f]; pg = doc[0]; jan = max(JANELA, 2.2 * c.get('raio', 12) if c['grupo'] == 'D' else JANELA)
            h = jan * 514 / 800
            cant = u2p(np.array([[q[0] - jan / 2, q[1] - h / 2], [q[0] + jan / 2, q[1] + h / 2], [q[0] - jan / 2, q[1] + h / 2], [q[0] + jan / 2, q[1] - h / 2]]))
            c0 = u2p(q[None])[0]; lo, hi = cant.min(0), cant.max(0)
            rect = pymupdf.Rect(lo[0], lo[1], hi[0], hi[1])
            if not rect.intersects(pg.rect): print(f'  ficha {c["n"]}: ponto fora da folha {f}'); continue
            zoom = 1100 / rect.width
            pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False)
            fn = os.path.join(OUT, f'{k:02d}_prancha_{f}.png'); pix.save(fn)
            im = Image.open(fn).convert('RGB'); dr = ImageDraw.Draw(im)
            x, y = (c0[0] - rect.x0) * zoom, (c0[1] - rect.y0) * zoom; r = 0.06 * im.width
            for j in range(4): dr.ellipse([x - r - j, y - r - j, x + r + j, y + r + j], outline=(214, 40, 30))
            for a_, b_ in (((x - r * 1.6, y), (x - r * 1.1, y)), ((x + r * 1.1, y), (x + r * 1.6, y)), ((x, y - r * 1.6), (x, y - r * 1.1)), ((x, y + r * 1.1), (x, y + r * 1.6))):
                dr.line([a_, b_], fill=(214, 40, 30), width=3)
            if doc.rot0: im = im.rotate(-doc.rot0, expand=True)
            jp = fn[:-4] + '.jpg'; im.save(jp, quality=85); os.remove(fn)
            saida[c['n']].append({'folha': f, 'arquivo': os.path.basename(jp), 'prancha': os.path.basename(FOLHAS[f][1])[:-4]})
    json.dump(saida, open(os.path.join(OUT, 'prancha.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum(len(v) for v in saida.values()), 'recortes')


if __name__ == '__main__':
    main()
