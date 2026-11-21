# Vistas de validação

Objetivo: o usuário abre o arquivo e valida **sem configurar nada**. É etapa obrigatória de toda entrega de modelagem.

## Modelos de vista (aplicados e bloqueados)

| Modelo | Configuração |
|---|---|
| `<DISC> - PLANTA` | Escala do PDF do projeto (1:200 ou 1:300) e detalhe **Alto** (tubo com o Ø real). Faixa de vista cobrindo todos os platôs: corte acima do platô mais alto, profundidade abaixo da rede mais funda. Toposolid oculto. CAD em meio-tom. Filtro de cor da disciplina com linha grossa. Níveis e eixos ocultos. |
| `<DISC> - 3D` | Toposolid com transparência 60–85%, CAD oculto, caixa de corte no lote. |
| `<DISC> - CORTE` | Toposolid visível em corte (85% transparente ajuda), níveis com cotas absolutas. |
| `COMPAT - 3D` | Fundo neutro; elementos em conflito em vermelho por sobreposição por elemento; o resto em meio-tom ou transparente. |

## Vistas entregues por disciplina

- Planta de validação com o CAD da disciplina sobreposto (`<DISC> - IMPLANTAÇÃO - VALIDAÇÃO CAD`).
- A mesma planta sem CAD (`<DISC> - MODELO`).
- 3D com caixa de corte.
- Cortes longitudinais nos trechos principais e nas transições de platô.
- Tabela de tubulação: trecho, Ø, comprimento, cota de topo, terreno, recobrimento.
- Tabela de caixas: CT, CF, profundidade.
- Folhas `<DISC>-VAL-01/02/03` juntando planta, 3D e tabelas.

## Configurações

- Região de recorte ajustada à área da obra, recorte de anotação ligado.
- **Etiquetas:** 1 por trecho (o maior segmento, sem os tocos), com a família de identificador de tamanho/diâmetro do template, e cota de topo quando útil. Servem para comparar direto com os textos do CAD.
- **Filtros de cor** por regra (`RBS_PIPING_SYSTEM_TYPE_PARAM` = sistema; `ALL_MODEL_MARK` começa com o prefixo), aplicados em **todas** as vistas novas, cortes inclusive.
- Agrupar no navegador pelos parâmetros de organização do template (Disciplina/Subdisciplina).
- **Layers do CAD base que confundem** (ex.: `ARQ_DEMOLIÇÃO`): oculte em todas as vistas pela subcategoria do CAD. Deixar "cinza tracejado" ainda incomoda. **Avise o usuário do que se trata antes de ocultar.**
- Compatibilização: uma vista 3D `COMPAT - INC-xx` por incompatibilidade, com caixa de corte justa no ponto e crop box ativo, mais `COMPAT - PLANTA GERAL` com a base vinculada.

## Folhas

- **A1 (841×594)** comporta uma implantação de porte médio em **1:300**, recortada na rede com 10 m de folga (em 1:200 não coube no ETIB). 3D em **1:1000**, lado a lado; cortes em 1:200.
- Conferência do layout: depois de posicionar, leia `Viewport.GetBoxOutline()` e o bounding box das tabelas na folha para achar sobreposições. Atenção à tabela de revisão do carimbo no canto direito.
- Tabelas: `ScheduleSheetInstance.Create`, posicionando pelo canto superior esquerdo.

## Ao entregar

Informe o nome e o ID de cada vista, modelo, filtro, tabela e folha criados, e lembre que o arquivo foi (ou precisa ser) salvo.
