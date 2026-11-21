# -*- coding: utf-8 -*-
"""Passa a prancha com carimbo QG as built (bloco CARIMBO_QG_ASBUILT, do carimbo_qg.py) para a etapa AS BUILT
(pedido do Anderson, 27/10/2026, piloto na Jandaíra):
  - código e arquivo: etapa PE -> AB, revisão R00 e disciplina pelo código CONDER (tabela 9.1 de nomenclatura; Anderson,
    28/10: AF -> AGF, EL -> ELE, IN/INC -> PCI): 24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03 -> ...-IMP-AB-AGF-001-HIG-R00;
  - DISCIPL_SETOR-FOLHA_REV com a mesma disciplina e R00 (AF_IMP-001_R03 -> AGF_IMP-001_R00);
  - assunto: "PROJETO EXECUTIVO" -> "PROJETO DE AS BUILT DE <disciplina por extenso>" (disciplina = DISCIPLINA do carimbo
    sem o setor, com INST. por extenso);
  - título como no modelo do Anderson (24-049-JDI-CTO-ETIB-GUA-AB-ARQ-001-PLB-R00): nome da escola (--escola), na linha de
    baixo só o setor (IMPLANTAÇÃO) e o endereço completo (--endereco);
  - quadro de revisões: é outra etapa, então as linhas do executivo saem e fica só a R00 (data cheia, EMISSÃO INICIAL,
    responsável vazio: Anderson, 28/10);
  - data da emissão.
O resto da folha não muda. Roda só com ezdxf + ODA (nuvem).

Uso: python carimbo_asbuilt.py <prancha.dwg|dxf> <pasta_saida> [--data dd/mm/aaaa] [--resp NOME]
                                 [--escola "NOME DA ESCOLA" ("|" quebra a linha)] [--endereco "RUA ..., MUNICÍPIO - BA"]
     grava <pasta_saida>/<código novo>.dwg (e .dxf ao lado, para o PDF)."""
import os, re, sys, datetime
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from revisao_ezdxf import ler, oda
from ezdxf.enums import TextEntityAlignment

NOME = 'CARIMBO_QG_ASBUILT'
LARG, CAB, LIN = 175.0, 117.60, 3.83                  # mesmos números do carimbo_qg.py
COLS = (0.0, 17.0, 44.0, 149.55, 174.95)
H2, Y2, DY_SETOR = 3.2, (75.6, 70.6), -1.5   # nome da escola em duas linhas: altura, topo de cada linha acima da base e
                                             # quanto a linha do setor desce (topo 66,46 -> 64,96) para caber
AJUSTE = dict(PROJETO=(3.5, 1, 168), DISCIPLINA=(3.5, 1, 168), ENDERECO=(2.5, 1, 168), ETAPA=(4.0, 1, 118),
              CODIGO=(4.0, 1, 168), ARQUIVO=(1.5, 1, 80), FOLHA=(4.5, 0.7, 48))


# disciplina: nossos códigos (e os dos projetistas) -> código CONDER da tabela 9.1 (AGF, ESG, DRE, PCI, ELE, PDA, CTV, AAC ...)
DISC_CONDER = {'AF': 'AGF', 'EL': 'ELE', 'IN': 'PCI', 'INC': 'PCI'}
CONDER = {'URB', 'ARQ', 'TER', 'SND', 'TOP', 'PAV', 'CMV', 'AMB', 'GEO', 'ECC', 'EMT', 'EMD', 'CNT', 'FND', 'AGG', 'AGF', 'AGQ',
          'AAC', 'DRE', 'ACU', 'GLP', 'ESG', 'GAM', 'PDA', 'PCI', 'ELE', 'PSG', 'CTV', 'CLI', 'SCA', 'ACE', 'SOM', 'COM'}


def disc_conder(d):
    d = DISC_CONDER.get(d.upper(), d.upper())
    if d not in CONDER: raise ValueError(f'disciplina {d} fora da tabela CONDER: acrescente em DISC_CONDER')
    return d


def codigo_ab(cod):
    """ANO-CTR-MUN-LOC-EMPR-SETOR-ETAPA-DIS-Nº-CONTEÚDO-REV: etapa -> AB, disciplina CONDER, rev -> R00."""
    p = cod.upper().split('-')
    if len(p) < 11 or not re.fullmatch(r'R\d\d', p[-1]): raise ValueError(f'código fora do padrão: {cod}')
    p[6], p[7], p[-1] = 'AB', disc_conder(p[7]), 'R00'
    return '-'.join(p)


def folha_ab(folha):
    """DISCIPL_SETOR-FOLHA_REV: AF_IMP-001_R03 -> AGF_IMP-001_R00."""
    m = re.fullmatch(r'([A-Z]+)_(.*)_R\d\d', folha.upper())
    return f'{disc_conder(m.group(1))}_{m.group(2)}_R00' if m else folha


FONTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'pranchas_pdf', 'fontes', 'arialbd.ttf')
_F = ImageFont.truetype(FONTE, 1000) if os.path.exists(FONTE) else None


def medida(v, h):
    """largura em mm do texto em Arial negrito (a altura do AutoCAD é a das maiúsculas: 0,716 do em)."""
    return _F.getlength(v) / 1000 * h / 0.716 if _F else len(v) * h * 0.95


def largura(tag, v, h=None):
    h0, wf, wmax = AJUSTE.get(tag, (0, 1, 0)); h = h or h0
    return min(1.0, wmax / (medida(v, h) * wf)) * wf if h and v else None


def duas_linhas(v, h, wmax):
    """quebra no espaço que deixa a 1ª linha mais longa que ainda cabe."""
    p = v.split(); k = len(p) - 1
    while k > 1 and medida(' '.join(p[:k]), h) > wmax: k -= 1
    return ' '.join(p[:k]), ' '.join(p[k:])


def linhas_quadro(lay, x0, y0):
    """linhas e textos das revisões empilhadas acima do cabeçalho do bloco (as que o carimbo_qg.py desenhou)."""
    def pts(e):
        t = e.dxftype()
        if t == 'LINE': return [e.dxf.start, e.dxf.end]
        if t in ('TEXT', 'MTEXT'): return [e.dxf.insert]
        return []
    revs = sorted({round((e.dxf.insert.y - y0 - CAB - LIN / 2) / LIN) for e in lay.query('TEXT MTEXT')
                   if abs(e.dxf.insert.x - x0 - 7.1) < 1.5 and 0 < e.dxf.insert.y - y0 - CAB < 30 * LIN})
    n = 0
    while n in revs: n += 1                          # só as linhas contíguas a partir do cabeçalho
    topo = y0 + CAB + n * LIN + 0.05
    sai = [e for e in lay.query('LINE TEXT MTEXT') if pts(e) and
           all(x0 - 0.5 <= p[0] <= x0 + LARG + 0.5 and y0 + CAB - 0.05 <= p[1] <= topo for p in pts(e))]
    return n, sai


def converter(prancha, pasta, data=None, resp='', desc='EMISSÃO INICIAL', escola=None, endereco=None):
    data = data or datetime.date.today().strftime('%d/%m/%Y')
    doc = ler(prancha)
    rel, novo = [], None
    for lay in doc.layouts:
        if lay.name == 'Model': continue
        for ins in [e for e in lay.query('INSERT') if e.dxf.name == NOME]:
            at = {a.dxf.tag: a for a in ins.attribs}
            antes = {k: a.dxf.text for k, a in at.items()}
            cod = codigo_ab(antes['CODIGO']); novo = novo or cod
            disc, _, setor = antes.get('DISCIPLINA', '').partition(' - ')
            disc = re.sub(r'^INST\.\s*', 'INSTALAÇÕES ', disc.strip()).replace('INSTALAÇÕES DE ', '')
            disc = {'ELÉTRICA': 'INSTALAÇÕES ELÉTRICAS'}.get(disc, disc)
            val = dict(CODIGO=cod, ARQUIVO=cod + '.DWG', DATA=data,
                       FOLHA=folha_ab(antes.get('FOLHA', '')),
                       ETAPA=f'PROJETO DE AS BUILT DE {disc}' if disc else 'PROJETO DE AS BUILT')
            if setor: val['DISCIPLINA'] = setor.strip()
            if escola: val['PROJETO'] = escola
            if endereco: val['ENDERECO'] = 'ENDEREÇO: ' + endereco
            x0, y0 = ins.dxf.insert.x - LARG, ins.dxf.insert.y
            l2 = None                                   # nome da escola longo: duas linhas, como no modelo da guarita
            if 'PROJETO' in val and 'PROJETO' in at and ('|' in val['PROJETO'] or largura('PROJETO', val['PROJETO']) < 0.85):
                val['PROJETO'], l2 = ([x.strip() for x in val['PROJETO'].split('|', 1)] if '|' in val['PROJETO']
                                      else duas_linhas(val['PROJETO'], H2, AJUSTE['PROJETO'][2]))
                a = at['PROJETO']; a.dxf.height = H2
                for c in ('insert', 'align_point'):              # alinhado pelo topo: o ponto que vale é o align_point
                    if a.dxf.hasattr(c): a.dxf.set(c, (a.dxf.get(c).x, y0 + Y2[0]))
                if 'DISCIPLINA' in at:
                    for c in ('insert', 'align_point'):
                        if at['DISCIPLINA'].dxf.hasattr(c): p = at['DISCIPLINA'].dxf.get(c); at['DISCIPLINA'].dxf.set(c, (p.x, p.y + DY_SETOR))
            for k, v in val.items():
                if k not in at: continue
                at[k].dxf.text = v
                f = largura(k, v, at[k].dxf.height)
                at[k].dxf.width = f if f and f < 0.999 else AJUSTE.get(k, (0, 1, 0))[1]
            if l2:
                a = at['PROJETO']; f = largura('PROJETO', l2, H2)
                t = lay.add_text(l2, height=H2, dxfattribs={'layer': ins.dxf.layer, 'style': a.dxf.style,
                                                            'width': f if f and f < 0.999 else 1.0})
                t.set_placement((a.dxf.insert.x, y0 + Y2[1]), align=TextEntityAlignment.TOP_LEFT)
            n, sai = linhas_quadro(lay, x0, y0)
            for e in sai: lay.delete_entity(e)
            ya, yb = y0 + CAB, y0 + CAB + LIN; ym = (ya + yb) / 2
            lay.add_line((x0 + COLS[0], yb), (x0 + COLS[-1], yb), dxfattribs={'layer': 'ARQ_TXT'})
            for xc in COLS: lay.add_line((x0 + xc, ya), (x0 + xc, yb), dxfattribs={'layer': 'ARQ_TXT'})
            st = 'Arial_1' if 'Arial_1' in doc.styles else 'Standard'
            for k, (txt, hj) in enumerate((('R00', 0), (data, 0), (desc, 0), (resp, 1))):
                if not txt: continue
                xa, xb = COLS[k], COLS[k + 1]
                t = lay.add_text(txt, height=1.8, dxfattribs={'layer': 'ARQ_TXT', 'style': st})
                t.set_placement((x0 + (xa + 1.0 if hj == 0 else (xa + xb) / 2), ym),
                                align=TextEntityAlignment.MIDDLE_LEFT if hj == 0 else TextEntityAlignment.MIDDLE_CENTER)
            rel.append(dict(layout=lay.name, linhas_saem=n, entidades_saem=len(sai),
                            antes={k: antes.get(k) for k in val}, depois=val))
    if not novo: raise RuntimeError(f'{prancha}: sem bloco {NOME}')
    os.makedirs(pasta, exist_ok=True)
    dxf = os.path.join(pasta, novo + '.dxf'); doc.saveas(dxf)
    dwg = oda(dxf, os.path.join(pasta, novo + '.dwg'))
    return dict(prancha=prancha, dwg=dwg, dxf=dxf, carimbos=rel)


if __name__ == '__main__':
    import json
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    print(json.dumps(converter(a[0], a[1], opt('--data'), opt('--resp') or '', escola=opt('--escola'), endereco=opt('--endereco')),
                     ensure_ascii=False, indent=1))
