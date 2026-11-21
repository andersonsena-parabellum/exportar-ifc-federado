# Usar o PDF do projeto como fonte de dados

O Revit não importa textos de DWG e o `accoreconsole` pode falhar. O PDF vetorial tem todos os textos com posição. Use PyMuPDF (`import fitz`).

## Textos com posição

```python
import fitz
page = fitz.open(pdf)[0]
for b in page.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            # s['text'], s['bbox'], s['size'], s['color'] (int RGB)
            ...
```

Filtre por cor e tamanho: no ETIB, os números de laço eram vermelhos com 7,9 pt; as cotas do QiBuilder eram cinza e menores.

## Tabelas e legendas

Quadro de bitolas, legenda de laços: `page.get_text('words')` dentro da caixa do título da tabela, agrupando por linha (`round(y/6)`).

## Transformação PDF → modelo

- Uma **similaridade com 2 âncoras** reconhecíveis nos dois (centro de um símbolo, centro de um equipamento) basta. Ache as âncoras em ampliações a 200 dpi: `page.get_pixmap(clip=fitz.Rect(...), dpi=200)`.
- **Confira pela escala:** em 1:200, 1 pt = 0,3528 mm × 200 = **0,0706 m/pt**. No ETIB, o obtido foi 0,07046.
- Depois, case cada texto com o elemento do DWG mais próximo (no ETIB: 20 números × 20 blocos `NUM`, todos a menos de 0,45 m).
- Símbolos pequenos nem sempre servem de âncora (só 6 de 15 caixas eram retângulos no PDF).

## Número com linha de chamada

Atribua **cada número ao trecho mais próximo dele**, não cada trecho ao número mais próximo: os números ficam a ~2 m da linha e dá empate. Conflitos se resolvem pela lógica da rede (ramal curto de um bloco = laço único; tronco = vários).

## Diâmetro e material

Conte os rótulos (ex.: `PEAD 2.1/2"` 16×, `3"` 1×) e cruze com o **quadro de equivalência de bitolas** do projeto (2½" = PEAD DE 75; 3" = DE 85). Não presuma a equivalência: ela muda com o material e o fabricante.

## Entender antes de modelar

Amplie regiões do PDF (casa de bombas, recalque, detalhes) para entender o projeto antes de modelar equipamentos.
