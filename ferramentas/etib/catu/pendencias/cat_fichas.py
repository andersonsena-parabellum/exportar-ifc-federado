# -*- coding: utf-8 -*-
"""Catu — fichas da página de pendências (gerador único FERRAMENTAS/pendencias/pagina.py) a partir das soluções do adaptador
(escolas/catu.py) e da rodada de 25/10 (PRECLASH_2026-10-25). Todas entraram pelo "aplicar e avisar" (Anderson, 22/10): caixa de passagem
até 1,50 m, caixa de gravidade até 0,60 m, geratriz de chegada até 0,20 m, pressurizada com desvio lateral até 2,00 m, torneira/hidrante
recuado pelo ramal. Não sobrou colisão que precise de decisão. Grava fichas.json ao lado.
Uso: .venv/Scripts/python.exe -X utf8 catu/pendencias/cat_fichas.py"""
import os, sys, json
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from preclash.terreno import Terreno

AQUI = os.path.dirname(os.path.abspath(__file__))
T = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\catu_terreno_base.npz')
_U = np.array([0.7606, 0.6492]); _N = np.array([0.6492, -0.7606]); _CE04 = np.array([567699.2, 8634680.0])
P1 = _CE04 + _U * 5.0 + _N * 0.35

F = [
 dict(titulo='Iluminação EL2-025 ao lado do esgoto, entre a CE-04 e a CE-03',
      o='O EL2-025 (EL2-CX03 -> EL2-CX02) estava desenhado em cima do esgoto ESG-29/ESG-11 por 17 m, passando por dentro das caixas CES-01, '
        'CE-04 e CE-03, e a EL2-CX02 ficava sobre o ESG-01, na saída da CE-03.',
      t='O EL2-025 passa paralelo ao esgoto, 0,70 m a sudeste do eixo, fora das caixas e da caixa do registro RG-02. A EL2-CX02 foi 1,49 m '
        'para o mesmo lado da CE-03 e a EL2-CX03 andou 1,03 m (saiu de cima do ESG-05); os eletrodutos acompanham. A cota do esgoto não muda.',
      reverter='Voltar o EL2-025 ao traçado do EL-002 R02 e as caixas EL2-CX02 e EL2-CX03 ao lugar do projeto (volta a cruzar as três caixas de esgoto).',
      E=P1[0], N=P1[1], raio=12, raio3d=6, folhas=['EL-002'], codigos=['EL2-025', 'EL2-CX02', 'EL2-CX03', 'CE-03', 'CE-04', 'ESG-11']),
 dict(titulo='Caixas de iluminação e alarme fora da PVP-05',
      o='A EL2-CX04 (iluminação) e a CX-09 (alarme) estavam desenhadas encostadas e dentro da PVP-05; o EL2-013 e o EL2-014 saíam da EL2-CX04 '
        'atravessando o PV.',
      t='A EL2-CX04 foi 0,72 m para sudoeste e a CX-09 0,90 m para nordeste do coletor Ø280, com os eletrodutos acompanhando; o EL2-013 e o EL2-014 '
        'contornam a PVP-05 a 0,30 m da parede. Os ramais das descidas AP-17 e AP-18 (DRE-032, DRE-104 e DRE-212) chegam na PVP-05 0,10 m acima do '
        'fundo, para o AF-07 passar por baixo com folga.',
      reverter='Voltar as duas caixas e os eletrodutos ao desenho do EL-002 e do INC-001, e os ramais ao fundo da PVP-05 (volta o conflito com o PV e o AF-07).',
      E=567723.03, N=8634671.63, raio=7, raio3d=3.5, folhas=['EL-002', 'INC-001', 'DRE-001'],
      codigos=['PVP-05', 'EL2-CX04', 'CX-09', 'EL2-013', 'EL2-014', 'DRE-212', 'AF-07']),
 dict(titulo='Caixa CX-12 do alarme fora da PVP-07',
      o='A CX-12 do alarme estava desenhada dentro da PVP-07 (coletor Ø280).',
      t='A CX-12 foi 1,32 m para nordeste do coletor, com o SDAI-11 acompanhando.',
      reverter='Voltar a CX-12 ao desenho do INC-001 (dentro do PV).',
      E=567730.09, N=8634663.26, raio=6, raio3d=3, folhas=['INC-001'], codigos=['PVP-07', 'CX-12', 'SDAI-11']),
 dict(titulo='Água fria AF-06 e alarme SDAI-12 em volta da PVP-03',
      o='O AF-06 e o SDAI-12 estavam desenhados atravessando a PVP-03.',
      t='Os dois contornam o PV a 0,30 m da parede, em curvas de 90° (AF) e no próprio eletroduto (alarme).',
      reverter='Voltar ao traçado do AGF-001 e do INC-001 (passando pelo PV).',
      E=567717.99, N=8634677.57, raio=6, raio3d=3, folhas=['AGF-001', 'INC-001'], codigos=['PVP-03', 'AF-06', 'SDAI-12']),
 dict(titulo='Banco de eletrodutos da alimentação em volta da PVP-09',
      o='Os quatro eletrodutos do banco EL1-005, EL1-010, EL1-025 e EL1-038 estavam desenhados atravessando a PVP-09.',
      t='O banco contorna o PV a 0,30 m da parede, com os quatro eletrodutos lado a lado, a 1,10 m de profundidade.',
      reverter='Voltar o banco ao traçado do EL-001 R05.',
      E=567740.08, N=8634650.35, raio=6, raio3d=3, folhas=['EL-001'], codigos=['PVP-09', 'EL1-005', 'EL1-025', 'EL1-038']),
 dict(titulo='Iluminação, hidrante e alarme entre a PVP-13 e a casa de resíduos',
      o='O EL2-008 (iluminação), o HID-01 (hidrante) e o SDAI-38 (alarme) passavam pela PVP-13, pela PVE-07 e pelas sapatas da casa de resíduos; '
        'o SDAI-36 passava pela PVE-08, e a CX-20 do alarme encostava no SDAI-39.',
      t='O EL2-008 contorna o conjunto PV + sapata pelo leste; o HID-01 contorna a PVP-13; o SDAI-38 contorna a PVE-07 e a sapata; o SDAI-36 '
        'contorna a PVE-08 (todos a 0,30 m); o SDAI-38 chega na casa de resíduos fora da sapata; a CX-20 andou 0,20 m.',
      reverter='Voltar os quatro traçados ao EL-002 e ao INC-001 (voltam a passar pelos PV e pelas sapatas).',
      E=567775.0, N=8634628.5, raio=9, raio3d=4.5, folhas=['EL-002', 'INC-001'],
      codigos=['PVP-13', 'PVE-07', 'EL2-008', 'HID-01', 'SDAI-38', 'SDAI-36', {'codigo': 'sapata da casa de resíduos', 'E': 567774.2, 'N': 8634631.1}]),
 dict(titulo='Caixa EL1-CX12 fora da PVE-04 e chegada do ESG-04',
      o='A EL1-CX12 (alimentação) estava desenhada sobre a PVE-04 do esgoto; o banco EL1-R08 passava encostado no ESG-04.',
      t='A EL1-CX12 foi 0,98 m, com os 8 eletrodutos acompanhando. O ESG-04 (CE-06 -> PVE-04) chega na PVE-04 0,13 m acima do fundo '
        '(i de 1,65 % para 1,00 %, o mínimo), e passa por cima do banco com folga.',
      reverter='Voltar a EL1-CX12 ao desenho do EL-001 e o ESG-04 ao fundo da PVE-04.',
      E=567718.17, N=8634645.0, raio=7, raio3d=3.5, folhas=['EL-001', 'ESG-001'], codigos=['PVE-04', 'EL1-CX12', 'ESG-04', 'EL1-069']),
 dict(titulo='Caixa EL1-CX13 fora da CE-06',
      o='A EL1-CX13 (alimentação) estava desenhada sobre a CE-06 do esgoto.',
      t='A EL1-CX13 foi 0,82 m, com os 6 eletrodutos acompanhando.',
      reverter='Voltar a EL1-CX13 ao desenho do EL-001.',
      E=567702.96, N=8634632.07, raio=6, raio3d=3, folhas=['EL-001'], codigos=['CE-06', 'EL1-CX13']),
 dict(titulo='Chegada do ESG-15 na PVE-03',
      o='O ESG-15 (PVE-02 -> PVE-03, i 9,5 %) passava 2 cm dentro dos eletrodutos EL1-010 e EL1-025.',
      t='O ESG-15 chega na PVE-03 0,20 m acima do fundo (i de 9,5 % para 8,4 %); os eletrodutos passam por baixo com folga.',
      reverter='Voltar a chegada ao fundo da PVE-03.',
      E=567742.6, N=8634645.41, raio=6, raio3d=3, folhas=['ESG-001'], codigos=['PVE-03', 'ESG-15', 'EL1-010']),
 dict(titulo='Chegada do ramal DRE-125 na CA-13',
      o='O ramal da descida AP-7 (DRE-125) chegava no fundo da CA-13 na mesma cota do eletroduto EL2-021 da iluminação.',
      t='O DRE-125 chega na CA-13 0,20 m acima do fundo (a descida AP-7 sobe junto), e o EL2-021 fica a 0,95 m, passando por baixo dele e '
        'acima do hidrante HID-09.',
      reverter='Voltar a chegada ao fundo da CA-13 (volta o cruzamento com o EL2-021).',
      E=567666.46, N=8634632.61, raio=6, raio3d=3, folhas=['DRE-001', 'EL-002'], codigos=['CA-13', 'DRE-125', 'EL2-021']),
 dict(titulo='Chegada do ramal DRE-218 na PVP-02',
      o='O ramal da descida AP-6 (DRE-218) chegava no fundo da PVP-02 passando 7 cm dentro do AF-01.',
      t='O DRE-218 chega na PVP-02 0,20 m acima do fundo (a descida AP-6 sobe junto), por cima do AF-01.',
      reverter='Voltar a chegada ao fundo da PVP-02.',
      E=567700.04, N=8634683.97, raio=6, raio3d=3, folhas=['DRE-001'], codigos=['PVP-02', 'DRE-218', 'AF-01']),
 dict(titulo='Caixas do alarme CX-21 e CX-19 junto da CA-12',
      o='A CX-21 do alarme estava encostada na CA-12 da drenagem; a CX-19, no ramal do lado.',
      t='A CX-21 andou 0,42 m e a CX-19 0,20 m, com os eletrodutos.',
      reverter='Voltar as duas caixas ao desenho do INC-001.',
      E=567696.07, N=8634634.24, raio=5, raio3d=2.5, folhas=['INC-001'], codigos=['CA-12', 'CX-21', 'CX-19']),
 dict(titulo='Hidrante H-10 recuado pelo ramal',
      o='O H-10 estava desenhado em cima do tubo de drenagem DRE-205 (borda do campo).',
      t='O hidrante recua 0,35 m pelo próprio ramal HID-06, como se faz com a torneira de jardim; o abrigo não muda.',
      reverter='Voltar o H-10 ao desenho do INC-001 (em cima do DRE-205).',
      E=567712.67, N=8634595.35, raio=5, raio3d=2.5, folhas=['INC-001'], codigos=['H-10', 'HID-06', 'DRE-205']),
 dict(titulo='Caixa de areia CA-24 deslocada 0,34 m',
      o='A CA-24 da drenagem encostava no ESG-14.',
      t='A CA-24 andou 0,34 m em planta, com a CT e a CF do projeto; o tubo que chega nela acompanha.',
      reverter='Voltar a CA-24 ao desenho do DRE-001.',
      E=567764.32, N=8634595.10, raio=5, raio3d=2.5, folhas=['DRE-001'], codigos=['CA-24', 'ESG-14']),
 dict(titulo='Caixa do registro RG-03 deslocada 1,20 m',
      o='A caixa do registro RG-03 da água fria estava sobre o ramal de drenagem DRE-223.',
      t='A caixa andou 1,20 m pelo ramal AF-10, que acompanha.',
      reverter='Voltar a RG-03 ao desenho do AGF-001.',
      E=567747.34, N=8634631.58, raio=5, raio3d=2.5, folhas=['AGF-001'], codigos=['RG-03', 'AF-10', 'DRE-223']),
 dict(titulo='Caixa do registro RG-01 deslocada 0,15 m',
      o='A caixa do registro RG-01 da água fria encostava na CE-01 do esgoto.',
      t='A caixa andou 0,15 m pela linha do AF-02, que acompanha; as curvas continuam a 90°.',
      reverter='Voltar a RG-01 ao desenho do AGF-001.',
      E=567729.88, N=8634705.83, raio=5, raio3d=2.5, folhas=['AGF-001'], codigos=['RG-01', 'CE-01', 'AF-02']),
 dict(titulo='Caixa EL2-CX21 deslocada 0,42 m',
      o='A EL2-CX21 da iluminação encostava no DRE-229.',
      t='A caixa andou 0,42 m, com os eletrodutos.',
      reverter='Voltar a EL2-CX21 ao desenho do EL-002.',
      E=567771.52, N=8634613.24, raio=5, raio3d=2.5, folhas=['EL-002'], codigos=['EL2-CX21', 'DRE-229']),
 dict(titulo='Caixa EL2-CX08 deslocada 0,25 m',
      o='A EL2-CX08 da iluminação estava sobre o hidrante HID-08.',
      t='A caixa andou 0,25 m para o lado do eletroduto, que acompanha.',
      reverter='Voltar a EL2-CX08 ao desenho do EL-002.',
      E=567676.12, N=8634659.90, raio=5, raio3d=2.5, folhas=['EL-002'], codigos=['EL2-CX08', 'HID-08']),
 dict(titulo='Caixa CX-02 do alarme deslocada 0,40 m',
      o='A CX-02 do alarme encostava em outra rede no ramal SDAI-18.',
      t='A caixa andou 0,40 m, com o SDAI-18.',
      reverter='Voltar a CX-02 ao desenho do INC-001.',
      E=567737.06, N=8634689.96, raio=5, raio3d=2.5, folhas=['INC-001'], codigos=['CX-02', 'SDAI-18']),
]


def main():
    out = []
    for n, f in enumerate(F, 1):
        z = float(T.z([[f['E'], f['N']]])[0]) - 1.0
        out.append(dict(n=n, bloco='aplicado', E=round(float(f['E']), 3), N=round(float(f['N']), 3), z=round(z, 2), **{k: v for k, v in f.items() if k not in ('E', 'N')}))
    json.dump(out, open(os.path.join(AQUI, 'fichas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(out), 'fichas')


if __name__ == '__main__':
    main()
