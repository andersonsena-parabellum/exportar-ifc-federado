# -*- coding: utf-8 -*-
"""Pojuca — fichas da página de pendências (gerador único FERRAMENTAS/pendencias/pagina.py) a partir das soluções do adaptador
(escolas/pojuca.py) e da rodada de 26/10 (PRECLASH_2026-10-25). Dois blocos:
  - Precisa de decisão: as caixas de iluminação do corredor norte do bloco pedagógico (EL2-CX06 a CX09), que não têm lugar livre dentro
    do limite do "aplicar e avisar" (1,50 m) nem a 4 m;
  - Aplicado (pode reverter): o que entrou pelo "aplicar e avisar" (Anderson, 22/10): CT pelo terreno executado, profundidades do estudo
    de cota, contornos de PV e de fundação, caixas de passagem e postes até 1,50 m, caixas de esgoto até 0,60 m, geratriz de chegada.
Grava fichas.json, config.json e transf.json ao lado.
Uso: .venv/Scripts/python.exe -X utf8 pojuca/pendencias/pjc_fichas.py"""
import os, sys, json
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno

AQUI = os.path.dirname(os.path.abspath(__file__))
B = r'D:/Projeto Modelagem/ETIB-POJUCA/RELATORIOS'
EXE = B + '/EXECUTIVO_2026-10-26'
T = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\pojuca_terreno.npz')
CT = json.load(open(os.path.join(EXE, 'PJC_ct_corrigidas.json'), encoding='utf-8'))
ct_txt = ', '.join(f"{c['caixa']} {c['ct_nova']:.2f}".replace('.', ',') for c in sorted(CT, key=lambda c: c['caixa']))

DEC = [
 dict(quem='projetista de elétrica', titulo='Caixa EL2-CX09 da iluminação sobre a caixa de areia CA-12',
      o='No corredor entre a face norte do bloco pedagógico e o coletor pluvial, a EL2-CX09 (iluminação, EL-002) está desenhada em cima da '
        'caixa de areia CA-12 e dos ramais pluviais DRE-004, DRE-032 e DRE-052 que chegam nela.',
      t='Procuramos lugar livre para a caixa (com os eletrodutos acompanhando) até 1,50 m, o limite do "aplicar e avisar", e depois até 4 m: '
        'o corredor está ocupado pelo esgoto, pela drenagem e pela base do poste IE-09 (que já andou 0,90 m). Mudar só a profundidade não '
        'resolve: os ramais pluviais passam a 0,75 m do terreno.',
      p='Levar ao projetista de elétrica: tirar a caixa do corredor (mudar o ponto de passagem no EL-002, por exemplo para o outro lado do '
        'coletor) ou dispensar a caixa nesse ponto, com o eletroduto PEAD flexível passando direto até a próxima.',
      E=572458.10, N=8626542.80, raio=6, raio3d=3, folhas=['EL-002', 'DRE-001'],
      codigos=['EL2-CX09', 'CA-12', 'DRE-004', 'DRE-032', 'DRE-052', 'POSTE-IE-09']),
 dict(quem='projetista de elétrica', titulo='Caixa EL2-CX08 da iluminação sobre os ramais DRE-045 e DRE-100',
      o='A EL2-CX08 está desenhada em cima dos ramais pluviais DRE-045 e DRE-100, junto do poste IE-11.',
      t='Sem lugar livre até 1,50 m nem até 4 m (corredor norte do bloco pedagógico). O poste IE-11 já andou 0,80 m.',
      p='Levar ao projetista de elétrica: mudar o ponto da caixa no EL-002 para fora do corredor ou dispensar a caixa nesse ponto.',
      E=572476.30, N=8626552.40, raio=6, raio3d=3, folhas=['EL-002', 'DRE-001'], codigos=['EL2-CX08', 'DRE-045', 'DRE-100', 'POSTE-IE-11']),
 dict(quem='projetista de elétrica', titulo='Caixa EL2-CX07 e poste IE-13 sobre o PVE-01 e o coletor DRE-183',
      o='A EL2-CX07 está desenhada em cima do PVE-01 (esgoto) e do ESG-33; a base do poste IE-13 fica sobre o coletor pluvial DRE-183. No '
        'mesmo nó, o ESG-40 passa encostado na PVP-01 (3 cm) e o eletroduto EL1-054 cruza o hidrante HI-05 a 1 cm.',
      t='A base do poste IE-13 já andou 0,90 m (dentro do limite) e ainda encosta no DRE-183. Sobra lugar livre para a EL2-CX07 a 1,80 m e '
        'para o poste a 1,20 m, os dois para o lado do bloco pedagógico: passa do limite de 1,50 m da caixa.',
      p='Deslocar a EL2-CX07 1,80 m e o poste IE-13 1,20 m (com os eletrodutos), e afastar a PVP-01 0,10 m do ESG-40. Precisa do sim por passar '
        'do limite.',
      E=572491.50, N=8626561.20, raio=7, raio3d=3.5, folhas=['EL-002', 'ESG-001', 'DRE-001'],
      codigos=['EL2-CX07', 'POSTE-IE-13', 'PVE-01', 'ESG-33', 'DRE-183', 'PVP-01', 'ESG-40', 'HI-05', 'EL1-054.1']),
 dict(quem='projetista de elétrica', titulo='Caixa EL2-CX06 da iluminação sobre o esgoto ESG-35',
      o='A EL2-CX06 está desenhada em cima do ESG-35, na ponta leste do corredor norte do bloco pedagógico, junto da subestação.',
      t='Sem lugar livre até 1,50 m nem até 4 m; a base do poste IE-16 já andou 0,20 m.',
      p='Levar ao projetista de elétrica: mudar o ponto da caixa no EL-002 ou dispensar a caixa nesse ponto.',
      E=572506.70, N=8626569.70, raio=6, raio3d=3, folhas=['EL-002', 'ESG-001'], codigos=['EL2-CX06', 'ESG-35', 'POSTE-IE-16']),
 dict(quem='projetista de drenagem e construtora', titulo='Ramais pluviais na saída dos prédios encostando nas fundações executadas',
      o='Os ramais das descidas pluviais saem da face do bloco pedagógico, da quadra coberta e da guarita junto dos pilares e, no primeiro '
        'metro, encostam nos blocos e pedestais das fundações executadas (as built): de 1 a 23 cm em cerca de 20 ramais (DRE-025, DRE-031, '
        'DRE-097, DRE-114, DRE-148, DRE-174, DRE-189, DRE-198 e outros), além do ramal de esgoto ESG-14 e do hidrante HI-01 junto da guarita.',
      t='As cotas dos ramais são as das pranchas (GI na saída) e a estrutura é a do RVT as built pela forma real. A fundação é estrutura '
        'executada: pela regra, não mexemos sem perguntar. Dentro do prédio nada é modelado; o conflito está na passagem pela face.',
      p='Confirmar com a construtora como os ramais foram (ou serão) executados na saída das descidas: passando por cima do bloco, ao lado do '
        'pedestal ou com a descida deslocada. Se a saída for por cima do bloco, subimos a GI de saída dos ramais (até 0,20 m) e corrigimos a DRE-001.',
      E=572456.6, N=8626507.4, raio=10, raio3d=4, folhas=['DRE-001'],
      codigos=['DRE-025', 'DRE-077', 'DRE-029', {'codigo': 'fundação 2143648', 'E': 572456.6, 'N': 8626507.4}]),
]

APL = [
 dict(titulo='CT das caixas de esgoto e drenagem pelo terreno executado',
      o='Na ESG-001 e na DRE-001 todas as caixas têm CT 61,00; o terreno executado (IMP as built) vai de 59,8 a 62,8 m.',
      t=f'A tampa de cada caixa vai para o terreno executado e a CT da prancha foi corrigida onde a diferença passa de 0,10 m ({len(CT)} caixas); '
        f'o fundo (CF) e as declividades não mudam. CT novas: {ct_txt}.',
      reverter='Voltar as CT para 61,00 (as caixas ficam com a tampa fora do terreno executado: enterradas no pátio e acima do terreno ao norte).',
      E=572470.0, N=8626530.0, raio=40, raio3d=20, folhas=['ESG-001', 'DRE-001'], codigos=['PVE-10', 'CA-25', 'CA-20', 'PVE-01']),
 dict(titulo='Profundidade das redes de pressão (estudo de cota)',
      o='Água, hidrante, elétrica e alarme não têm profundidade no projeto.',
      t='Uma cota por rede na água e no hidrante: hidrante a 0,85 m (por cima dos coletores PVC-V de 250 e 300 mm), água potável a 1,00 m e '
        'alimentação dos reservatórios a 1,12 m (por baixo do hidrante e por cima dos coletores) e reúso a 1,85 m. Elétrica e alarme por '
        'trecho entre caixas, sempre por cima da água (0,70 a 1,45 m). Nenhuma rede passa de 1,90 m. Uma nota "PROF." por trecho nas folhas.',
      reverter='Outra cota para uma rede (as colisões com os coletores e entre a água e o hidrante voltam).',
      E=572500.0, N=8626535.0, raio=12, raio3d=6, folhas=['AF-001', 'IC-001'], codigos=['HI-09', 'AF-04', 'AL-03', 'DRE-192', 'DRE-182']),
 dict(titulo='Eletrodutos em volta de caixas de areia e PV',
      o='O EL1-008, EL1-023, EL1-027, EL1-038 e EL1-048 atravessavam as caixas CA-05, CA-07, CA-09 e CA-11; o EL1-009 e o EL1-024 a PVP-03; o '
        'EL2-001 a CA-06 e a PVP-01; o EL2-011 o PVE-16.',
      t='Os eletrodutos contornam as caixas a 0,30 m da parede, no próprio eletroduto flexível; as caixas não mudam.',
      reverter='Voltar os eletrodutos ao traçado do EL-001 e do EL-002 (passando pelas caixas).',
      E=572513.0, N=8626547.0, raio=10, raio3d=5, folhas=['EL-001', 'EL-002'],
      codigos=['EL1-027', 'EL1-009', 'CA-11', 'CA-09', 'PVP-03', 'EL2-001']),
 dict(titulo='Hidrante HI-09 e alarme SD-13 em volta da PVP-06',
      o='O HI-09 e o SD-13 atravessavam a PVP-06.',
      t='Os dois contornam o PV a 0,30 m da parede (curvas de 45° no PEAD do hidrante; no próprio eletroduto do alarme).',
      reverter='Voltar ao traçado do IC-001 (passando pelo PV).',
      E=572498.3, N=8626527.4, raio=6, raio3d=3, folhas=['IC-001'], codigos=['PVP-06', 'HI-09', 'SD-13']),
 dict(titulo='Elétrica do campo society em volta das caixas de drenagem',
      o='No campo, os eletrodutos CPS-EL-01 a CPS-EL-04 passavam pelas caixas de interligação da drenagem CA-30, CA-34, CA-37 e CA-41.',
      t='Contornam as caixas a 0,30 m da parede. A CPS EL-001 não desenha os eletrodutos (só caixas e postes), então o contorno está só no IFC.',
      reverter='Voltar ao traçado reto caixa a caixa.',
      E=572430.0, N=8626475.0, raio=20, raio3d=10, folhas=['CPS-EL-001'], codigos=['CPS-EL-01', 'CPS-EL-02', 'CA-34', 'CA-30']),
 dict(titulo='Água, reúso e elétrica em volta de fundações do bloco pedagógico',
      o='O AL-03 (alimentação), o RU-06 (reúso) e o banco EL1-039/EL1-049 passavam por pedestais de fundação do bloco pedagógico fora da face '
        'do prédio (passarela para o teatro e lado sul).',
      t='Contornam a peça pela lateral mais curta, a 0,30 m, em curvas de 90° (água) e no próprio eletroduto (elétrica).',
      reverter='Voltar ao traçado do AF-001 e do EL-001 (passando pelas fundações).',
      E=572500.5, N=8626548.0, raio=8, raio3d=4, folhas=['AF-001', 'EL-001'],
      codigos=['AL-03', 'RU-06', 'EL1-039', {'codigo': 'fundação 2148756', 'E': 572501.03, 'N': 8626538.36}]),
 dict(titulo='Caixas de passagem e postes deslocados (até 1,50 m)',
      o='Caixas de passagem e bases de poste da iluminação e do alarme caíam sobre tubos e caixas de esgoto e drenagem.',
      t='Deslocadas com os eletrodutos que chegam nelas: EL1-CX06 1,30 m; EL2-CX03 0,20 m; EL2-CX12 0,31 m; alarme CX03 1,31 m e CX04 1,40 m; '
        'bases e postes IE-04 0,30 m, IE-07 0,90 m, IE-09 0,90 m, IE-11 0,80 m, IE-13 0,90 m, IE-15 0,50 m, IE-16 0,20 m e o poste 3 do campo 0,30 m.',
      reverter='Voltar cada caixa e poste ao desenho (volta o conflito com o esgoto e a drenagem).',
      E=572503.0, N=8626544.5, raio=10, raio3d=5, folhas=['EL-001', 'EL-002', 'IC-001'],
      codigos=['EL1-CX06', 'EL2-CX03', 'POSTE-IE-15', 'CX03', 'CX04']),
 dict(titulo='Poços de visita do esgoto PVE-05, PVE-06 e PVE-07 deslocados',
      o='Os três PV do esgoto a oeste do bloco pedagógico encostavam nas caixas e nos tubos da drenagem.',
      t='PVE-05 0,23 m, PVE-06 0,21 m e PVE-07 0,28 m, com o fundo (CF) mantido e os tubos acompanhando.',
      reverter='Voltar os PV ao desenho da ESG-001.',
      E=572438.0, N=8626533.1, raio=6, raio3d=3, folhas=['ESG-001'], codigos=['PVE-05', 'PVE-06', 'PVE-07']),
 dict(titulo='Ramal de esgoto ESG-12 chega 0,15 m acima do fundo da CES-07',
      o='O ESG-12 (ramal do bloco pedagógico) cruzava o coletor pluvial DRE-212 7 cm abaixo do topo dele.',
      t='O ramal sobe inteiro 0,15 m (declividade mantida) e chega na CES-07 0,15 m acima do fundo: passa por cima do DRE-212. Nota de chegada na ESG-001.',
      reverter='Voltar a geratriz do ESG-12 (volta a colisão com o DRE-212).',
      E=572469.0, N=8626512.2, raio=5, raio3d=2.5, folhas=['ESG-001'], codigos=['ESG-12', 'CES-07', 'DRE-212']),
]


def main():
    out = []
    for f in DEC: out.append(dict(bloco='decisao', **f))
    for f in APL: out.append(dict(bloco='aplicado', **f))
    for n, f in enumerate(out, 1):
        f['n'] = n; f['z'] = round(float(T.z([[f['E'], f['N']]])[0]) - 1.0, 2)
    json.dump(out, open(os.path.join(AQUI, 'fichas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    TR = {'AF-001': (0.0, [572432.856588, 8626427.301743]), 'ESG-001': (0.0, [572432.856588, 8626427.301743]),
          'DRE-001': (0.0, [572432.856588, 8626427.301743]), 'EL-001': (0.0, [-574.8428139999742, 2.2888219989836216]),
          'EL-002': (0.0, [-614.6108510000631, -1.8540980014950037]), 'IC-001': (0.0, [572024.0386, 8626407.4983])}
    import escolas.pojuca as S
    for k in ('CPS-EL-001', 'CPS-DRE-001'):
        r, t = S.TRANSF_DWG[S._DWG[k]]; TR[k] = (r, list(t))
    json.dump({'arquivos': [dict(arquivo_original=k, rot_deg=r, t=t) for k, (r, t) in TR.items()]},
              open(os.path.join(AQUI, 'transf.json'), 'w', encoding='utf-8'), indent=1)
    import exe_folhas
    cfg = dict(escola='ETIB Pojuca', sigla='PJC', data='26/10/2026', fichas='fichas.json', saida=B + '/PENDENCIAS_2026-10-26',
               ifc=B + '/ENTREGA_IFC_2026-10-26/PJC_IMP_*.ifc', terreno='D:/Projeto Modelagem/FERRAMENTAS/preclash/escolas/dados/pojuca_terreno.npz',
               transf_json='transf.json', folhas=exe_folhas.folhas(EXE))
    json.dump(cfg, open(os.path.join(AQUI, 'config.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(out), 'fichas:', sum(f['bloco'] == 'decisao' for f in out), 'decisão,', sum(f['bloco'] == 'aplicado' for f in out), 'aplicado')


if __name__ == '__main__':
    main()
