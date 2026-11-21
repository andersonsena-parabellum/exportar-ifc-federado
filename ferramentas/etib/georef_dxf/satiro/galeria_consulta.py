# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — PDF de consulta à construtora sobre a galeria dupla Ø1200 do DRE-001 R02 ("rede futura se necessário").
Página 1: o que o desenho mostra + perguntas; página 2: planta em UTM com os cruzamentos; página 3: recorte da prancha original.
Uso: python -I -X utf8 galeria_consulta.py
"""
import sys, os, json, math, textwrap
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
import fitz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sat_comum as sc
from esg_sat import arq_sit
from fase3_sat import Terreno

W = sc.WRK
ld = lambda n: json.load(open(os.path.join(W, n), encoding='utf-8'))
SAIDA = os.path.join(r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS', 'SAT_Consulta_Galeria_DN1200_DRE-001-R02.pdf')
PDF_DRE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\PROJETO_ORIGINAL\IMP\03_DRE\24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02.pdf'


def br(x, n=2):
    return f'{x:,.{n}f}'.replace(',', '#').replace('.', ',').replace('#', '.')


def cruzamentos(gal):
    """Interseções do eixo de cada rede com a faixa da galeria (as duas linhas de tubos)."""
    redes = []
    af = ld('af_rede.json')
    redes += [('Água fria / reúso', t['trecho'], f"PVC Ø{t.get('DN_adotado') or ''}", t['pts']) for t in af['trechos']]
    ap = ld('ap_rede.json')
    redes += [('Pluvial (ESG-001)', t['trecho'], f"{t['material']} Ø{t['DN_mm'] or ''}", t['pts']) for t in ap['trechos'] if not t['classe'].startswith('calha')]
    esg = ld('esg_rede.json')
    redes += [('Esgoto', t['trecho'], f"Ø{t['DN_mm']}", t['pts']) for t in esg['trechos']]
    ele = ld('ele_rede.json')
    redes += [('Elétrica', t['trecho'], t['folha'], t['pts']) for k in ('EL1', 'EL2', 'CPS_EL1') for t in ele[k]['trechos']]
    pci = ld('pci_rede.json')
    redes += [('Hidrantes', t['trecho'], 'PEAD 2.1/2"', t['pts']) for t in pci['HID']['trechos']]
    redes += [('SDAI', t['trecho'], 'eletroduto', t['pts']) for t in pci['SDAI']['trechos']]
    A = np.asarray(gal[0]['pts'][0]); B = np.asarray(gal[0]['pts'][1])
    A2 = np.asarray(gal[1]['pts'][0]); B2 = np.asarray(gal[1]['pts'][1])
    out = []
    for rede, nome, desc, pts in redes:
        P = [np.asarray(p[:2], float) for p in pts]
        for a, b in zip(P[:-1], P[1:]):
            for (c, d) in ((A, B), (A2, B2)):
                r = b - a; s = d - c; den = r[0] * s[1] - r[1] * s[0]
                if abs(den) < 1e-12: continue
                t = ((c - a)[0] * s[1] - (c - a)[1] * s[0]) / den; u = ((c - a)[0] * r[1] - (c - a)[1] * r[0]) / den
                if 0 <= t <= 1 and 0 <= u <= 1:
                    q = a + t * r
                    if all(np.linalg.norm(q - o['p']) > 4.0 or o['trecho'] != nome for o in out):
                        out.append({'rede': rede, 'trecho': nome, 'desc': desc, 'p': q, 'u': u, 'gal': gal[0] if (c is A) else gal[1]})
    return out


def main():
    dre = ld('dre_rede.json')['trechos']
    ter = Terreno()
    cz = cruzamentos(dre)
    # cotas no cruzamento: topo da galeria x eixo das redes pressurizadas (fase 3, terreno provisório)
    for c in cz:
        g = c['gal']; gi = g['GI_montante'] + (g['GI_jusante'] - g['GI_montante']) * c['u']
        c['topo_gal'] = gi + 1.2 + 0.10; c['terreno'] = float(ter.z(c['p'])[0])
    import collections
    por = collections.Counter(c['rede'] for c in cz)
    with PdfPages(SAIDA) as pdf:
        # ---------------- página 1
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.text(0.05, 0.93, 'ETIB Sátiro Dias — consulta sobre a galeria dupla Ø1200 mm (DRE-001-DRG R02)', fontsize=15, weight='bold')
        g1, g2 = dre
        corpo = [
            'O que o projeto de drenagem mostra',
            f'• Duas tubulações paralelas Ø1200 mm (eixos a {br(np.linalg.norm(np.subtract(g1["pts"][0], g2["pts"][0])))} m), {br(g1["L_m"], 1)} m cada, cruzando o terreno entre o platô das',
            '  edificações (+236,00) e o da área esportiva (+233,00), com alas nas duas pontas.',
            f'• Geratriz inferior: GI = {br(g1["GI_montante"])} na entrada (lado sudeste, junto ao vestiário) e GI = {br(g1["GI_jusante"])} na saída (lado noroeste), i ≈ {br(g1["i_pct"], 1)} %.',
            '• Textos da prancha: "DIÂMETRO DA TUBULAÇÃO Ø 1200 mm" nas duas pontas e "REDE FUTURA SE NECESSÁRIO – NÃO EDIFICAR NESSA FAIXA".',
            f'• Coordenadas (UTM SIRGAS 2000 / 24S): entrada E {br(g1["E_ini"])} / N {br(g1["N_ini"])}; saída E {br(g1["E_fim"])} / N {br(g1["N_fim"])}.',
            '',
            'Perguntas',
            '1. A galeria será executada nesta obra, ou a faixa fica só reservada para uma rede futura?',
            '2. Se for executada: confirmar o traçado, a quantidade de linhas (2 × Ø1200), o material e a classe dos tubos, as GI de entrada e',
            '   saída, as alas/cabeceiras e o dissipador na saída.',
            '3. Pela topografia e pela terraplanagem, a saída (GI 228,80) fica de 0,14 m a 0,46 m acima do terreno natural e o recobrimento',
            '   varia muito ao longo do corpo (há trechos sem recobrimento junto às pontas). Qual é a cota de saída e para onde vai a água?',
            f'4. As demais redes cruzam a faixa da galeria em {len(cz)} pontos (ver página 2): ' + ', '.join(f'{k} {v}' for k, v in por.items()) + '.',
            '   Se a galeria for executada, as redes passam por cima dela? Há folga mínima a respeitar?',
            '',
            'Observação: as coordenadas e cotas acima saem dos DWG do projeto referenciados em UTM. O terreno usado para o recobrimento é',
            'provisório (platôs da terraplanagem + topografia), até a conferência com o modelo as built da implantação.',
        ]
        y = 0.86
        for linha in corpo:
            peso = 'bold' if linha in ('O que o projeto de drenagem mostra', 'Perguntas') else 'normal'
            fig.text(0.05, y, linha, fontsize=10.5, weight=peso); y -= 0.038
        fig.text(0.05, 0.03, 'Arquivos: 24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02 (dwg/pdf) — referenciamento em CAD_GEORREFERENCIADO\\REGISTRO_GEORREFERENCIAMENTO.md', fontsize=8, color='0.4')
        pdf.savefig(fig); plt.close(fig)
        # ---------------- página 2: planta
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.add_collection(LineCollection(arq_sit(), colors='0.82', linewidths=0.3))
        cores = {'Água fria / reúso': '#1f77b4', 'Pluvial (ESG-001)': '#17becf', 'Esgoto': '#8c564b', 'Elétrica': '#d62728', 'Hidrantes': '#e377c2', 'SDAI': '#bcbd22'}
        for nome, arq, sel in (('Água fria / reúso', 'af_rede.json', None), ('Pluvial (ESG-001)', 'ap_rede.json', 'ap'), ('Esgoto', 'esg_rede.json', None)):
            J = ld(arq)
            for t in J['trechos']:
                if sel == 'ap' and t['classe'].startswith('calha'): continue
                p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color=cores[nome], lw=0.9)
        ele = ld('ele_rede.json')
        for k in ('EL1', 'EL2', 'CPS_EL1'):
            for t in ele[k]['trechos']: p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '--', color=cores['Elétrica'], lw=0.8)
        pci = ld('pci_rede.json')
        for t in pci['HID']['trechos']: p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '-', color=cores['Hidrantes'], lw=1.2)
        for t in pci['SDAI']['trechos']: p = np.array(t['pts']); ax.plot(p[:, 0], p[:, 1], '--', color=cores['SDAI'], lw=0.8)
        for g in dre:
            p = np.array(g['pts']); ax.plot(p[:, 0], p[:, 1], '-', color='#9467bd', lw=4, alpha=0.8)
        ax.annotate(f'entrada GI {g1["GI_montante"]:.2f}', xy=g1['pts'][0], xytext=(g1['pts'][0][0] + 8, g1['pts'][0][1] - 8), arrowprops=dict(arrowstyle='->'), fontsize=9)
        ax.annotate(f'saída GI {g1["GI_jusante"]:.2f}', xy=g1['pts'][1], xytext=(g1['pts'][1][0] - 30, g1['pts'][1][1] + 8), arrowprops=dict(arrowstyle='->'), fontsize=9)
        for i, c in enumerate(cz):
            ax.plot(*c['p'], 'o', ms=6, mfc='none', mec='k'); ax.text(c['p'][0] + 0.8, c['p'][1] + 0.4, str(i + 1), fontsize=7)
        for nome, cor in cores.items(): ax.plot([], [], '-', color=cor, label=nome)
        ax.plot([], [], '-', color='#9467bd', lw=4, label='galeria 2 × Ø1200 (rede futura)')
        ax.legend(loc='upper right', fontsize=8)
        ax.set_xlim(545880, 546000); ax.set_ylim(8716105, 8716240); ax.set_aspect('equal'); ax.ticklabel_format(useOffset=False, style='plain'); ax.grid(alpha=0.2)
        ax.set_title('Planta (UTM): galeria dupla Ø1200 e as redes que cruzam a faixa (○ = cruzamento numerado)', fontsize=11)
        pdf.savefig(fig); plt.close(fig)
        # ---------------- página 2b: lista dos cruzamentos
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.text(0.05, 0.94, 'Cruzamentos com a faixa da galeria (cotas no terreno provisório)', fontsize=13, weight='bold')
        y = 0.89
        fig.text(0.05, y, f'{"nº":>3}  {"rede":<20} {"trecho":<10} {"descrição":<28} {"E":>11} {"N":>12} {"terreno":>8} {"topo galeria":>12}', fontsize=8.5, family='monospace'); y -= 0.028
        for i, c in enumerate(cz):
            fig.text(0.05, y, f'{i + 1:>3}  {c["rede"]:<20} {c["trecho"]:<10} {str(c["desc"])[:28]:<28} {c["p"][0]:>11.2f} {c["p"][1]:>12.2f} {c["terreno"]:>8.2f} {c["topo_gal"]:>12.2f}',
                     fontsize=8.5, family='monospace'); y -= 0.024
            if y < 0.05: break
        pdf.savefig(fig); plt.close(fig)
        # ---------------- página 3: recorte da prancha original
        d = fitz.open(PDF_DRE); pg = d[0]
        clip = fitz.Rect(330, 380, 870, 935)
        pix = pg.get_pixmap(dpi=220, clip=clip)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.imshow(img[:, :, :3]); ax.axis('off')
        ax.set_title('Recorte da prancha 24-049-STK-XXX-ETIB-IMP-PE-DRE-001-DRG-R02 (como enviada)', fontsize=11)
        pdf.savefig(fig); plt.close(fig)
    print('ok', SAIDA, '| cruzamentos', len(cz), dict(por))


if __name__ == '__main__':
    main()
