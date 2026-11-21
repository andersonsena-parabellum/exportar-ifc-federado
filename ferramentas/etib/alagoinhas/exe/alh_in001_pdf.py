# -*- coding: utf-8 -*-
"""Alagoinhas — IN-001 (hidrantes + SDAI) R06 no padrão de executivo final, sobre o PDF R05 do projetista: o DWG dele não abre no
console (ErrorStatus 53 ao abrir, "not a valid drawing" ao inserir), então a prancha não passa pelo rever.py.
Sobre o PDF: nota "PROF. x,xx m" por trecho (uma por trecho, agrupadas como no rever.py), traçado novo dos contornos curtos na cor e
espessura da rede (o trecho antigo sai, coberto de branco), caixa de passagem do SDAI deslocada (símbolo e nome andam), linha 06 no
quadro de revisões e códigos da folha em R06. PDF -> coordenadas: calibração do 19/10 (imp_pci_pdf.py), refinada sobre a tinta vermelha.
Uso: python -X utf8 alh_in001_pdf.py"""
import os, sys, json, math
import numpy as np
import pymupdf
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\ALAGOINHAS_IMP\scripts')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import imp_pci_pdf as IP
import asbuilt as ab

REL = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS'
MUD = os.path.join(REL, r'PRECLASH_IMP_R03\ALI_mudancas_UTM.json')
OUT = os.path.join(REL, r'EXECUTIVO_R03\PDF\24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R06.pdf')
O = np.array([561500.0, 8658000.0])
COR = {'HID': ((1.0, 0.0, 0.0), 0.57), 'SDAI': ((0.0, 0.0, 0.0), 0.85)}
FS = 7.9


def pdf(P_utm):
    return IP.pdf_de_int(np.atleast_2d(np.asarray(P_utm, float))[:, :2] - O)


def ocupados(pg):
    out = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip(): out.append(pymupdf.Rect(s['bbox']))
    return out


def lugar(ocup, p, n, w, h):
    for k in range(12):
        for sg in (1, -1):
            q = p + sg * n * (6 + 4 * k)
            R = pymupdf.Rect(q[0] - w / 2, q[1] - h / 2, q[0] + w / 2, q[1] + h / 2)
            if all(not R.intersects(o) for o in ocup): return R
    return pymupdf.Rect(p[0] - w / 2, p[1] - h / 2 - 8, p[0] + w / 2, p[1] + h / 2 - 8)


def main():
    M = [m for m in json.load(open(MUD, encoding='utf-8'))['mudancas'] if m.get('folha') == 'IN-001']
    doc = pymupdf.open(IP.SRC); pg = doc[0]
    IP.conferir(pg)
    ocup = ocupados(pg); n_ct = n_cx = n_nt = 0
    for m in M:
        if m['tipo'] != 'contorno': continue
        A_, B_ = pdf(m['antigo']), pdf(m['novo']); cor, w = COR.get(m['disc'], COR['HID'])
        # trecho que mudou: do primeiro ao último vértice do novo que não está sobre o antigo
        fora = [i for i, q in enumerate(np.asarray(m['novo'])) if np.min(np.hypot(*(np.asarray(m['antigo']) - q).T)) > 0.05]
        if not fora: continue
        i0, i1 = max(0, fora[0] - 1), min(len(B_) - 1, fora[-1] + 1)
        a0, a1 = B_[i0], B_[i1]
        sh = pg.new_shape(); sh.draw_line(tuple(a0), tuple(a1)); sh.finish(color=(1, 1, 1), width=w + 2.0); sh.commit()
        sh = pg.new_shape(); sh.draw_polyline([tuple(q) for q in B_[i0:i1 + 1]]); sh.finish(color=cor, width=w); sh.commit()
        n_ct += 1
    for m in M:
        if m['tipo'] != 'caixa deslocada': continue
        p0, p1 = pdf([m['de']])[0], pdf([(m['E'], m['N'])])[0]; lado = max(m['lado'], m['lado_y']) * IP.ptm
        R0 = pymupdf.Rect(p0[0] - lado / 2 - 1.5, p0[1] - lado / 2 - 1.5, p0[0] + lado / 2 + 1.5, p0[1] + lado / 2 + 1.5)
        pg.draw_rect(R0, color=None, fill=(1, 1, 1), overlay=True)
        sh = pg.new_shape(); sh.draw_line(tuple(p0), tuple(p1)); sh.finish(color=COR['SDAI'][0], width=COR['SDAI'][1]); sh.commit()
        R1 = pymupdf.Rect(p1[0] - lado / 2, p1[1] - lado / 2, p1[0] + lado / 2, p1[1] + lado / 2)
        pg.draw_rect(R1, color=COR['SDAI'][0], fill=(1, 1, 1), width=COR['SDAI'][1], overlay=True)
        # nome da caixa anda junto
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    if s['text'].strip() == m['trecho'] and np.hypot(*(np.array(s['origin']) - p0)) < 40:
                        Rt = pymupdf.Rect(s['bbox']); pg.draw_rect(Rt + (-0.3, -0.3, 0.3, 0.3), color=None, fill=(1, 1, 1), overlay=True)
                        o = np.array(s['origin']) + (p1 - p0); pg.insert_text(tuple(o), s['text'], fontsize=s['size'], fontname='helv', color=(0, 0, 0))
        n_cx += 1
    for g in ab.agrupar_notas([m for m in M if m['tipo'] == 'mergulho']):
        P = pdf(g['P']); L = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
        if L[-1] < 1e-6: continue
        s = L[-1] / 2; k = min(int(np.searchsorted(L, s)), len(P) - 1); k = max(k, 1)
        a, b = P[k - 1], P[k]; t = (s - L[k - 1]) / max(L[k] - L[k - 1], 1e-9); p = a + (b - a) * t
        u = (b - a) / max(np.hypot(*(b - a)), 1e-9); n = np.array([-u[1], u[0]])
        txt = g['texto']; w = pymupdf.get_text_length(txt, fontname='helv', fontsize=FS); h = FS * 1.2
        R = lugar(ocup, p, n, w, h); ocup.append(R)
        pg.insert_text((R.x0, R.y1 - 0.25 * FS), txt, fontsize=FS, fontname='helv', color=(0, 0, 0))
        n_nt += 1
    # carimbo do projetista: linha 06 no quadro de revisões e códigos em R06 (posições medidas no R05, imp_pci_pdf.py)
    yb = 1934.7 + 2.6 - 14.45; fs = 1.842 * IP.MM * 1.3
    for x, t in ((2853.0, '06'), (2880.7, 'OUT/2026'), (2938.3, 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'), (3296.9, 'POPULUS')):
        pg.insert_text((x, yb), t, fontsize=fs, fontname='helv', color=(0, 0, 0))
    ok1 = IP.troca_ultimo_digito(pg, pymupdf.Rect(3300, 2222, 3336, 2276), '6')
    ok2 = IP.troca_span(pg, '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05', '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R06')
    ok3 = IP.troca_texto(pg, pymupdf.Rect(3140, 2337, 3336.5, 2351.5), '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R06.DWG', limiar=200)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT, garbage=3, deflate=True)
    print(f'IN-001 R06: {n_nt} notas, {n_ct} contornos, {n_cx} caixas; carimbo {ok1} {ok2} {ok3} -> {OUT}')


if __name__ == '__main__':
    main()
