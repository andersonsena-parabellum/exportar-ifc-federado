# Checagem de interferências e relatório de incompatibilidades

## Checagens automáticas (por API)

- **Tubo × terreno:** recobrimento real ao longo do tubo (amostrar a cada 0,5 m) × exigido.
- **Caixa × terreno:** CT acima do terreno (exposta) ou muito abaixo (soterrada).
- **Disciplina × disciplina:** colisão física (sólidos que se cruzam) e folga mínima entre geratrizes.
- **Rede × estrutura:** sapatas, blocos, baldrames e pilares dos vínculos, com a transformação total (inclusive aninhados `T_base × T_aninhado`).
- **Rede × referências:** área de demolição, caminhos/pavimentos divergentes entre plantas. Quantifique (m², metros de rede) e mapeie antes de decidir com o usuário.

## Severidade

| Severidade | Critério |
|---|---|
| **CRÍTICA** | Colisão física |
| **ATENÇÃO** | Folga entre redes < 0,20 m; elemento estrutural muito próximo; caixa exposta/soterrada; profundidade mínima de família |
| **INFORMAÇÃO** | Dado faltante no projeto, premissa adotada, deslocamento entre referências |

Divergência projeto × obra (ex.: CT de projeto × terreno executado) entra como incompatibilidade. **Não ajuste o modelo**; o usuário decide.

## Estrutura do PDF (A4 paisagem)

1. Capa.
2. Projeto e metodologia: objeto, documentos usados, passos, legenda de severidade.
3. Resumo: mapa geral com marcadores numerados na cor da severidade + tabela.
4. Uma página por ficha:
   - selo de severidade;
   - 3D exportado do Revit com **círculo tracejado vermelho "FOCO"**;
   - recorte de localização em planta;
   - "O que foi encontrado", "Elementos/Local" (com coordenadas) e "Ação sugerida".

Saídas: o PDF + uma pasta `PRINTS_Rxx\` com as imagens marcadas. Revisões R00, R01... acumulam as disciplinas novas.

## Ferramentas e identidade visual

- PyMuPDF com fontes Segoe UI.
- Cores e logo da empresa do usuário. Padrão usado (Populus): dourado `#D8A800`, azul-marinho `#0B0B26`, logo branco sobre o fundo azul. Confirme com o usuário se o relatório é para outra empresa.

## Pegadinhas do script

- `page.insert_textbox` devolve o espaço que **sobrou**: o usado é `altura − sobra`. Se negativo, o texto não coube.
- Texto que não cabe: reduza a fonte em degraus.
- Listas longas vão abaixo da imagem, em duas colunas.
- Campos com `" | "` dentro do texto quebram o split: use `join(p[6:])` ou outro separador.
- Gerando o script por heredoc, `\n` pode quebrar: use `chr(10)` ou escreva o arquivo pelo Write.
- Prints 3D minúsculos: crop box desligado (ver `revit-mcp-api.md`).
