# -*- coding: utf-8 -*-
"""Agrupa os pontos de clash em ITENS do relatório R02 (regras por par, tipo de elemento e área) e conta
hoje × com a solução (pontos_clash_sol2.csv = profundidades recomendadas + desvios testados).
Saída: RELATORIOS/compat_R02/itens_pontos.csv (ponto -> item) e itens_resumo.csv."""
import sys, csv, re, json, collections
sys.stdout.reconfigure(encoding='utf-8')
R = r"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02" + "\\"
HOJE = list(csv.DictReader(open(R + 'pontos_prof_elem.csv', encoding='utf-8-sig'), delimiter=';'))
SOL = list(csv.DictReader(open(R + 'pontos_clash_sol2.csv', encoding='utf-8-sig'), delimiter=';'))

# itens: código, gravidade-título, título, quem resolve
ITENS = [
    ('CP-01', 'Rede de hidrantes na mesma faixa de profundidade das outras redes', 'Incêndio'),
    ('CP-02', 'Eletroduto do alarme (SDAI) cruzando outras redes e caixas', 'Incêndio'),
    ('CP-03', 'Rede de hidrantes atravessando fundações (BA2 e TRT)', 'Incêndio'),
    ('CP-04', 'Água fria atravessando caixas e poços de outras redes', 'Água fria'),
    ('CP-05', 'Água fria cruzando tubos e eletrodutos com pouca folga', 'Água fria'),
    ('CP-06', 'Água fria × fundações e vigas baldrame (BA2, SB5, TRT)', 'Água fria e estrutura'),
    ('CP-07', 'Caixas e eletrodutos da elétrica e da CFTV/dados no mesmo lugar', 'Elétrica e dados/CFTV'),
    ('CP-08', 'Elétrica e dados atravessando caixas e poços da drenagem e do esgoto', 'Elétrica e dados/CFTV'),
    ('CP-09', 'Eletrodutos cruzando coletores de drenagem e esgoto', 'Elétrica e dados/CFTV'),
    ('CP-10', 'Eletrodutos × fundações (RST, SB5, BA2, TRT, GUA)', 'Elétrica e estrutura'),
    ('CP-11', 'Descidas pluviais nos pilares do BA2: saída atravessa pilar e sapata', 'Drenagem e estrutura'),
    ('CP-12', 'Drenagem × fundações e pilares dos demais blocos (RST, TRT, GUA, CDR, SB5)', 'Drenagem e estrutura'),
    ('CP-13', 'Travessias de vigas baldrame (RST, SB5, TRT)', 'Estrutura e redes'),
    ('CP-14', 'Drenagem × esgoto: coletores e caixas que se cruzam', 'Drenagem e esgoto'),
    ('CP-15', 'Drenagem: cotas de projeto acima do terreno executado', 'Drenagem'),
    ('CP-16', 'Esgoto × fundações (RST, CDR, BA2)', 'Esgoto e estrutura'),
    ('CP-17', 'Esgoto: tampas fora do terreno executado e trechos rasos', 'Esgoto'),
    ('CP-18', 'Muro de divisa existente dentro do muro de contenção novo', 'Contenção e arquitetura'),
    ('CP-19', 'Ponta da sapata do muro sobre redes e caixas junto ao RST', 'Contenção'),
    ('CP-20', 'Sapata do muro × fundações do RST', 'Contenção e estrutura'),
    ('CP-21', 'Contenção sem cotas no projeto e terreno as built sem o desnível', 'Contenção'),
    ('CP-22', 'Passagens por lajes, paredes estruturais e muros existentes', 'Arquitetura e estrutura'),
    ('CP-23', 'Caminhos do SIT R04 ausentes no IMP as built', 'Arquitetura/urbanismo'),
    ('CP-24', 'Dados de referência: IMP deslocado do SIT e caixas de esgoto sem cota', 'Arquitetura e esgoto'),
]
TIT = {c: t for c, t, q in ITENS}; QUEM = {c: q for c, t, q in ITENS}
BA2 = (32.0, 7.0, 89.0, 42.5)
def em(r, bb): x, y = float(r['x']), float(r['y']); return bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]


def item(r):
    ds = {r['discA'], r['discB']}; cats = {r['catA'], r['catB']}
    other = lambda d: (r['discB'] if r['discA'] == d else r['discA'])
    catd = lambda d: (r['catA'] if r['discA'] == d else r['catB'])
    nomed = lambda d: (r['trechoB'] if r['discA'] != d else r['trechoA'])
    if 'IMP' in ds:
        return 'CP-18' if 'CNT' in ds else 'CP-22'
    if 'EST' in ds:
        ce = catd('EST')
        if ce in ('Pisos', 'Paredes'): return 'CP-22'
        o = other('EST')
        if o == 'CNT': return 'CP-20'
        if ce == 'Quadro estrutural': return 'CP-13'
        if o in ('INC', 'SDAI'): return 'CP-03'
        if o == 'AF': return 'CP-06'
        if o in ('ELE', 'TEL'): return 'CP-10'
        if o == 'ESG': return 'CP-16'
        if o == 'DRN': return 'CP-11' if r['trechoB'].startswith('BA2') or r['trechoA'].startswith('BA2') or em(r, BA2) else 'CP-12'
    if 'CNT' in ds: return 'CP-19'
    if 'INC' in ds: return 'CP-01'
    if 'SDAI' in ds: return 'CP-02'
    if 'AF' in ds:
        o = other('AF')
        return 'CP-04' if ('Modelos genéricos' in (catd(o),) or catd(o) == 'Acessórios do tubo' or catd('AF') == 'Modelos genéricos') else 'CP-05'
    if ds == {'ELE', 'TEL'}: return 'CP-07'
    if ds & {'ELE', 'TEL'} and ds & {'DRN', 'ESG'}:
        g = (ds & {'DRN', 'ESG'}).pop()
        return 'CP-08' if (catd(g) in ('Modelos genéricos', 'Acessórios do tubo') or catd((ds & {'ELE', 'TEL'}).pop()) == 'Modelos genéricos') else 'CP-09'
    if ds == {'DRN', 'ESG'}: return 'CP-14'
    return 'CP-99'


def chave(r): return (r['idA'], r['idB']) if r['idA'] < r['idB'] else (r['idB'], r['idA'])
sol_idx = {}
for r in SOL: sol_idx[chave(r)] = r
res = collections.defaultdict(lambda: dict(hc=0, ha=0, hi=0, sc=0, sa=0, si=0, pts=[]))
with open(R + 'itens_pontos.csv', 'w', encoding='utf-8-sig') as f:
    cols = list(HOJE[0].keys()) + ['item', 'gravidade_sol', 'folga_sol']
    f.write(';'.join(cols) + '\n')
    for r in HOJE:
        it = item(r); s = sol_idx.get(chave(r)); d = res[it]
        d['h' + {'CRÍTICA': 'c', 'ATENÇÃO': 'a', 'INFORMAÇÃO': 'i'}[r['gravidade']]] += 1
        if s: d['s' + {'CRÍTICA': 'c', 'ATENÇÃO': 'a', 'INFORMAÇÃO': 'i'}[s['gravidade']]] += 1
        d['pts'].append(r)
        f.write(';'.join([str(r[c]) for c in HOJE[0].keys()] + [it, s['gravidade'] if s else '', s['folga_m'] if s else '']) + '\n')
# pontos novos que só aparecem com a solução (efeito colateral)
novos = collections.Counter()
hk = {chave(r) for r in HOJE}
for r in SOL:
    if chave(r) not in hk: novos[(item(r), r['gravidade'])] += 1
with open(R + 'itens_resumo.csv', 'w', encoding='utf-8-sig') as f:
    f.write('item;título;quem resolve;hoje colisões;hoje folgas;hoje info;sol colisões;sol folgas;sol info;novos com a solução\n')
    for c, t, q in ITENS:
        d = res[c]; nv = sum(v for (i, g), v in novos.items() if i == c)
        d['sc'] += novos.get((c, 'CRÍTICA'), 0); d['sa'] += novos.get((c, 'ATENÇÃO'), 0); d['si'] += novos.get((c, 'INFORMAÇÃO'), 0)
        f.write(f"{c};{t};{q};{d['hc']};{d['ha']};{d['hi']};{d['sc']};{d['sa']};{d['si']};{nv}\n")
        print(f"{c} {t[:62]:62s} hoje {d['hc']:3d}c {d['ha']:3d}f {d['hi']:2d}i | sol {d['sc']:3d}c {d['sa']:3d}f {d['si']:2d}i | novos {nv}")
if 'CP-99' in res: print('SEM ITEM:', len(res['CP-99']['pts']), collections.Counter(r['par'] for r in res['CP-99']['pts']))
print('novos (todos):', dict(novos))
