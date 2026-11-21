# Lições da modelagem: redes externas no Revit via MCP

> Modelagem de compatibilização das instalações externas (implantação), feita em out/2026 no projeto ETIB Alagoinhas-BA.
> Revit 2025.2 + MCP `mcp-server-for-revit` (ferramenta `send_code_to_revit`), AutoCAD 2023 (`accoreconsole`), Python (numpy, PyMuPDF).
>
> - **Parte A:** regras gerais, para reaproveitar em qualquer projeto.
> - **Parte B:** o que é específico do ETIB Alagoinhas.

---

# PARTE A: REGRAS GERAIS

## A1. Passo a passo que funcionou

1. **Diagnóstico dos DWGs antes de vincular.** Rodar o `accoreconsole` em cópia, sem abrir o AutoCAD, e ler:
   - INSUNITS, EXTMIN/EXTMAX e a lista de layers;
   - se o DWG está em UTM ou em coordenadas locais.

   Projetos feitos em QiBuilder costumam vir em coordenadas locais.
2. **Georreferenciar os CADs em cópias** numa pasta `CAD_GEORREFERENCIADO\`, sem mexer nos originais:
   - descobrir a transformação local → UTM (ver A4);
   - aplicar a transformação na cópia;
   - salvar a transformação em JSON para reuso.
3. **Limpar a planta base (SIT) numa cópia `_REF`:**
   - apagar entidades perdidas longe da obra;
   - remover blocos duplicados ou pesados (curvas de nível em bloco);
   - explodir blocos que tenham transformações enormes.
4. **Definir as coordenadas do RVT.** Origem interna = um ponto UTM redondo perto da obra, sem rotação e com cota 0. Assim, a cota interna é igual à cota absoluta.
5. **Vincular os CADs** (Link, nunca Import) em meio-tom, posicionados pela origem.
6. **Terreno:** usar o terreno real do modelo base ("as built"/IMP) como vínculo, quando existir. Caso contrário, criar um Toposolid a partir do topográfico.
7. **Configurar o MEP:**
   - tipos de tubo, segmentos (DE reais), sistemas com cor e abreviação;
   - filtros por disciplina;
   - parâmetros compartilhados COMP_*.
8. **Extrair a rede do CAD por script, não "na mão":**
   - ler as linhas e os textos (Ø, CT, CF, i%) dos layers da rede;
   - montar o grafo da rede (nós = caixas/conexões, arestas = trechos);
   - gerar um CSV de trechos e outro de nós para conferência.
9. **Calcular as cotas** (ver A2) e validar o CSV antes de criar qualquer elemento no Revit.
10. **Criar no Revit por API, em lotes:** tubos, conexões, caixas e preenchimento dos parâmetros COMP_*.
11. **Montar as vistas de validação** (ver A6). É etapa obrigatória, não um extra.
12. **Checagens automáticas por API:**
    - tubo × terreno (recobrimento) e caixa × terreno;
    - AF × ESG (colisão e folga mínima);
    - tubo × estrutura (sapatas, baldrames, pilares dos vínculos).
13. **Montar o relatório de incompatibilidades**, com uma ficha por problema (vistas 3D com foco, planta de localização e ação sugerida).

**Para a 2ª disciplina em diante (novo RVT), o roteiro que funcionou no Incêndio:**
1. Com o RVT anterior aberto, **exportar para JSON a "receita" dele**: a transformação total de cada vínculo, os pontos de base e de levantamento, os níveis, os filtros e os modelos de vista. Depois fechar esse RVT, porque **um modelo aberto na sessão não pode ser vinculado**.
2. No novo RVT:
   - definir a posição do projeto direto por `SetProjectPosition`, com a mesma origem;
   - substituir os níveis do template pelos platôs;
   - apagar o lixo do template (CADs importados, níveis de andar).
3. Recriar os vínculos com a **mesma transformação lida no JSON**: `RevitLinkType.Create` + `RevitLinkInstance.Create(Origin)` + rotação/movimento. O RVT da disciplina anterior entra como **Sobreposição**, de origem a origem.
4. Provar as coordenadas com dois testes:
   - o CAD UTM (SIT_REF), vinculado com `ImportPlacement.Shared`, tem de cair na mesma posição do RVT anterior;
   - um elemento do vínculo anterior tem de ter a mesma coordenada compartilhada nos dois arquivos.
5. Conferir **cada DWG de disciplina individualmente**: cada projetista pode ter usado um sistema local diferente (ver A4).
6. Só então seguir os passos 7 a 13 acima.

## A2. Regras de modelagem

| Tema | Regra |
|---|---|
| Níveis | Sempre em **cotas absolutas**, com a elevação base no Ponto de Levantamento e a cota interna igual à absoluta. Um nível por platô (ex.: `PLATÔ +135,50`). |
| Recobrimento | Vale o que a **nota de cada projeto** manda. Padrão: **0,30 m** sob passeio e grama; **0,60 m** sob área de veículos. Cota do topo do tubo = superfície − recobrimento. O eixo fica DE/2 abaixo. Área de veículos = polígono desenhado uma vez e reaproveitado entre disciplinas. |
| Água fria (pressão) | Segue o terreno, com recobrimento constante. As transições entre platôs viram trechos verticais ou inclinados. |
| Redes pressurizadas e eletrodutos enterrados (incêndio, SDAI) | Mesmo critério da AF: amostrar a superfície a cada 0,5 m ao longo da rede, por `ReferenceIntersector` no Toposolid do vínculo. Quebrar o trecho onde o terreno desvia mais de **0,20 m** da reta, com trecho mínimo de **2 m** (Douglas-Peucker). Iterar até nenhum ponto ficar com recobrimento menor que o mínimo. Gravar o recobrimento real mínimo em `COMP_Recobrimento Mín`. |
| Equipamentos sem família adequada | Casa de bombas, caixas de passagem e caixas de recalque viram **DirectShape tirado do contorno do próprio CAD** (ex.: layer da parede TRRF), com COMP_* e a observação "esquemático". Bombas e registros podem usar as famílias do template, conferindo a cota depois (ver A3). |
| Saídas "segue para instalações internas" | Tampão (`PlumbingUtils.PlaceCapOnOpenEnds`) e COMP_Observação explicando. No fim, só podem sobrar pontas abertas onde há equipamento (reservatório, registro). |
| Atributos de laço/circuito (SDAI, elétrica) | Gravar em `Comentários` e em `COMP_Descrição`, para aparecer na tabela. Se o projeto indica o laço por número circulado + legenda, casar os números do PDF com os blocos do DWG (ver A9). |
| Esgoto (gravidade) | **Usa as cotas do projeto**: CT (tampa), CF (fundo), CE/CS (entrada e saída nas caixas). A declividade sai das cotas. Se o tubo chega acima do fundo da caixa de jusante, aplicar **tubo de queda** (marcar `queda`). Trechos sem cota são preenchidos com a declividade mínima e a premissa é registrada. |
| Caixas | Usar famílias MEP reais quando houver (ex.: UnMEP CI 60×60, Caixa de Gordura). Na falta delas, usar DirectShape com parâmetros COMP_*. Tampa = CT do projeto; fundo = CF. A profundidade é CT − CF. |
| Disciplinas e arquivos | **Um RVT por disciplina** ou par afim (AF + ESG juntos). Todos usam a mesma origem e as mesmas coordenadas compartilhadas. |
| Vínculos | **Preferir sempre vínculo:** um arquivo base padrão (terreno, implantação, blocos) e as instalações em outro arquivo. Não copiar geometria da base para dentro das instalações. |
| Nomes de vistas | Prefixo da disciplina (`AF -`, `ESG -`, `COMPAT -`). O caractere `:` é proibido em nomes de vista. |
| Trechos | Usar a nomenclatura do projeto: `AF-07.3`, `ESG-36`, caixas `CI-xx`, `CG-xx`, `PVE-xx`. Gravar em `COMP_Trecho`. |
| Parâmetros COMP_* | COMP_Disciplina, Trecho, Descrição, Recobrimento Mín/Exigido, Cota Topo Início/Fim, Terreno Início/Fim, Origem; GI Montante/Jusante, Declividade, CT, CF, Profundidade, Observação. Ficam num arquivo TXT de parâmetros compartilhados próprio de compatibilização. |
| Critérios de clash | Colisão física = **CRÍTICA**. Folga AF × ESG abaixo de 0,20 m = **ATENÇÃO**. Dado faltante ou premissa = **INFORMAÇÃO**. |

## A3. Limitações e pegadinhas do MCP do Revit (`send_code_to_revit`)

- **O código já roda dentro de uma transação do add-in.**
  - Não abrir `new Transaction`, porque dá erro de transação aninhada.
  - Para isolar um trecho, usar `SubTransaction`.
  - Para desfazer tudo, **lançar uma exceção**.
- **Diálogos modais travam o MCP.** Os avisos de hachura ao vincular DWG e as janelas do add-in causam timeout.
  - Muitas vezes o comando termina mesmo assim: conferir o resultado antes de repetir.
  - Para destravar, o usuário fecha a janela, ou um PowerShell com user32 (EnumWindows + BM_CLICK no botão) fecha por você.
  - Não deixar watcher de diálogos rodando em segundo plano, porque consome memória e o processo foi morto.
- **Revit 2025:** usar `new ElementId(long)`, não `int`.
- **Apagar elementos enquanto se itera** um FilteredElementCollector causa erro de "Iterator": chamar `.ToElements()` antes.
- **Retorno grande** estoura a resposta: devolver resumos ou CSV curto e gravar o resto em arquivo.
- **Lotes:** criar dezenas de tubos por chamada, não centenas. Se um lote falhar, ele é desfeito inteiro.
- **"Adquirir coordenadas"/vínculo por coordenadas compartilhadas** pode ser recusado ou abrir diálogo via API. A saída que funcionou foi posicionar o vínculo por **transformação calculada** (ver A4).
- **Conexões MEP:**
  - a família de joelho falha com deflexão menor que ~15° ou maior que 90°: usar ligação direta (`ConnectTo`);
  - o tê exige principal reto e ramal a 90°: usar tocos curtos (~0,35 m) para "endireitar" a geometria.
- **`ViewSection.CreateSection`:** o Revit inverte o Z local e o plano de corte fica em −Min.Z. Usar Min.Z = 0 e posicionar o corte um pouco à frente do objeto (ex.: 0,6 m).
- **Exportar imagem de vista 3D:** sem a caixa de recorte (crop box) ativa e ajustada à projeção da caixa de corte, a imagem pega a extensão do modelo todo e o objeto sai minúsculo.
- **Altura de famílias de terceiros:** a tampa da família UnMEP ficava ~6 cm acima do ponto de inserção. Ajustar a elevação e a profundidade juntas. Algumas famílias têm **profundidade mínima** (ex.: CG), registrar a exceção.
- **Ao final de cada etapa, salvar.** `doc.Save()` não funciona dentro da transação, mas dá para **agendar o comando Salvar**, que roda logo após o código:
  `new UIApplication(doc.Application).PostCommand(RevitCommandId.LookupPostableCommandId(PostableCommand.Save))`.
  Conferir pela data do arquivo. Antes de operações arriscadas, copiar o RVT para `_BACKUP_data_hora.rvt`.
- **Confirmar o documento antes de editar.** `document` é o documento **ativo**, que muda quando o usuário troca de janela. Todo código que edita começa com `if (doc.Title != "...") throw`.
- **Depois de um timeout**, a resposta seguinte pode ser o resultado **atrasado** do comando anterior. Rodar uma consulta de conferência com um marcador ("CHECKn") antes de repetir qualquer coisa.
- **Mensagens de erro "Exception has been thrown by the target of an invocation"** escondem a causa. Envolver cada passo em `try/catch` dentro de `SubTransaction` e devolver `ex.Message` passo a passo.
- **Redirecionar um tubo já conectado** (ex.: para encaixar o toco do tê): preservar o sentido da curva, `atStart ? Line(S,F) : Line(F,S)`. Se inverter, aparece o erro que não pode ser ignorado: "o duto/tubo foi modificado para a direção oposta".
- **Toco do tê em tubo curto:** usar `min(0,35 m; comprimento/3)`.
- **Famílias baseadas em plano de trabalho** (bomba, registro de recalque) criadas com `NewFamilyInstance(ponto, símbolo, nível)` ficam em z ≈ 0. Mover em Z depois e conferir pelo bounding box.
- **Tipo de corte com modelo de vista** trava o nível de detalhe ("Detail Level cannot be modified"): zerar `ViewTemplateId` logo após `CreateSection`.
- **Eletroduto enterrado:** curvas tipo "condulete 90°" não aceitam dobras suaves e geram o erro "não é possível manter a conectividade". Deixar os eletrodutos ponta a ponta, sem conexão.
- **Padrão de eletroduto:**
  - `ConduitSizeSettings` é instância: `css.CreateConduitStandardTypeFromExisingStandardType(...)` e `css.AddSize(...)`;
  - o parâmetro `CONDUIT_STANDARD_TYPE_PARAM` do tipo é um **ElementId** de um ElementType com o nome do padrão.
- **Segmento de tubo novo:** `Autodesk.Revit.DB.Plumbing.PipeSegment.Create(doc, material, PipeScheduleType, List<MEPSize>)`. Qualificar o namespace, porque o nome curto dá "inacessível".
- **Testar as conexões do tipo de tubo antes de modelar**: criar curvas (90°, 45°, 22,5°) e um tê dentro de `SubTransaction` e desfazer com `RollBack()`.
- **CAD importado (ImportInstance):**
  - depois de mover ou rotacionar, `GetTotalTransform()` continua devolvendo identidade. A posição real está em `GeometryInstance.Transform` da geometria;
  - o nome de um bloco aninhado vem de `doc.GetElement(gi.GetSymbolGeometryId().SymbolId).Name` (`GeometryInstance.Symbol` não existe);
  - as hachuras chegam como **faces de um único Solid**, e o layer de cada uma está em `face.GraphicsStyleId`. `Face.IsInside` não é confiável nelas: exportar os laços (`EdgeLoops`) e fazer ponto-no-polígono em Python;
  - no Revit, clicar numa linha ou hachura seleciona o **CAD inteiro**. Para identificar o que o usuário está vendo, ler o zoom da vista (`UIView.GetZoomCorners()`) e varrer a geometria ou fazer `ReferenceIntersector` naquela área.
- **Amostrar o terreno de um vínculo:** `ReferenceIntersector(filtro Toposolid, Element, vista3D)` com `FindReferencesInRevitLinks = true`, raio vertical de cima para baixo. A vista 3D precisa existir, e a caixa de corte pode recortar: desligar e religar.
- **Diálogos do Revit (ver A10).**

## A4. Georreferenciamento e vínculos

- **CAD local → UTM:** a transformação é rígida (rotação + translação, sem escala).
  - Não confiar em "ponte" por PDF ou leitura de coordenadas impressas: errou cerca de 2,3 m.
  - O que funcionou foi um **ICP** (casamento de pontos) entre um bloco de arquitetura embutido no projeto da disciplina e a mesma arquitetura na planta de implantação georreferenciada. O resíduo ficou em 2 mm.
- **Ordem da transformação:** primeiro rotacionar em torno de (0,0), depois transladar. Gravar os valores com todas as casas decimais.
- **Blocos com transformações enormes:** o Revit desloca esses blocos ao vincular, por isso explodir antes.
- **Vínculo RVT com coordenadas próprias diferentes:**
  - `ProjectLocation.GetTotalTransform()` mapeia compartilhado → interno;
  - a matriz do vínculo é `M = T_host × T_link⁻¹`;
  - na primeira tentativa a transformação saiu invertida: **validar sempre** sobrepondo a planta.
- **Vínculos aninhados** (blocos dentro do modelo base): para checar clash, a posição real é `T_base × T_aninhado`.
- **Se o usuário diz que "não está alinhado", parar e corrigir antes de seguir.** Perguntar qual arquivo está na posição certa e alinhar o outro a ele.
- **Não presumir que todos os DWGs de disciplina usam o mesmo sistema local.**
  - O incêndio, do mesmo escritório da AF e do ESG, estava deslocado ~70 m.
  - Diagnóstico rápido: vincular o DWG de origem a origem e ler a posição e a rotação dos blocos de arquitetura embutidos (`ARQ_BASE...`) pela geometria. Se a **rotação for igual** à da AF e o deslocamento for o **mesmo nos três blocos** (abaixo de 1 µm), é só uma translação até o sistema da AF, e depois vale a transformação da AF.
- **Georreferenciar dentro do Revit**, quando o AutoCAD não processa o DWG:
  - vincular com `ImportPlacement.Origin` e `Unit = Meter`;
  - `RotateElement` em torno da origem interna;
  - `MoveElement` por `R·d + t − origem do projeto`.
- **Vínculos RVT copiados de outro RVT:** ler `GetTotalTransform()` de cada instância (origem + ângulo de BasisX) e reaplicar com rotação + movimento. O desvio medido foi de 0,000 mm. Gravar como `RevitLinkOptions(true)` (caminho relativo), Sobreposição e fixado.
- **Coordenadas iguais em todas as disciplinas = federação direta no Navisworks** (NWC com "Coordenadas compartilhadas").
  - Os RVTs de referência (IMP, estruturas) foram posicionados sem compartilhar coordenadas, então devem sair **pelo NWC do hospedeiro** com "Converter arquivos vinculados".
  - Publicar coordenadas neles altera arquivos de terceiros: só com autorização.

## A5. AutoCAD `accoreconsole` (scripts .scr)

- Executar via PowerShell `Start-Process`, com `/i arquivo.dwg /s script.scr`.
- Scripts com quebra de linha **CRLF**. Começar com `SECURELOAD 0` para carregar LISP.
- **Sem `vla-*`** (ActiveX não existe no console): usar `entget`/`entmod`/`ssget`.
- Para apagar entidades em layer travado, **destravar o layer antes do ERASE**.
- Não usar heredoc sem aspas no bash para gerar scripts: ele altera as barras invertidas dos caminhos. Escrever com aspas simples ou pelo Write.
- Trabalhar sempre em **cópia** e salvar com sufixo (`_GEO`, `_REF`).
- **Alguns DWGs não abrem no console:**
  - o `IN-001` (QiBuilder, com objetos personalizados) deu `ErrorStatus=53` com `/readonly`;
  - sem `/readonly`, ficou esperando sem fim;
  - o `RECOVER` passou, mas o `SAVEAS` derrubou o console.

  Não insistir: usar a geometria do vínculo no Revit (A4) e os textos do PDF (A9).
- Rodar sempre com timeout (`WaitForExit(ms)` e `Kill`), porque o console trava em silêncio.

## A6. Como montar as vistas de validação

Objetivo: o usuário abre o arquivo e valida sem configurar nada.

**Modelos de vista** (aplicados e bloqueados):

| Modelo | Configuração |
|---|---|
| `<DISC> - PLANTA` | Escala do PDF do projeto (1:200 ou 1:300) e detalhe **Alto**, para o tubo aparecer com o Ø real. Faixa de vista cobrindo todos os platôs (corte acima do platô mais alto, profundidade abaixo da rede mais funda). Toposolid oculto. CAD em meio-tom. Filtro de cor por disciplina, com linha grossa. Níveis e eixos ocultos. |
| `<DISC> - 3D` | Toposolid com transparência (60–85%), CAD oculto e caixa de corte no lote. |
| `<DISC> - CORTE` | Toposolid visível em corte e níveis com cotas absolutas. |
| `COMPAT - 3D` | Fundo neutro; elementos em conflito em vermelho via sobreposição por elemento; o resto em meio-tom ou transparente. |

**Vistas entregues por disciplina:**
- planta de validação com o CAD da disciplina sobreposto;
- a mesma planta sem CAD;
- 3D com caixa de corte;
- cortes longitudinais nos trechos principais e nas transições de platô;
- tabela de tubulação (trecho, Ø, comprimento, cota de topo, terreno, recobrimento);
- tabela de caixas (CT, CF, profundidade);
- folhas `<DISC>-VAL-01/02/03` juntando planta, 3D e tabela.

**Outras configurações:**
- Região de recorte ajustada à área da obra, com o recorte de anotação ligado.
- Etiquetas de Ø e cota de topo nos tubos, para comparar direto com os textos do CAD.
- Para compatibilização: uma vista 3D `COMPAT - INC-xx` por incompatibilidade, com caixa de corte justa no ponto e crop box ativo, mais uma planta geral `COMPAT - PLANTA GERAL` com a base vinculada.
- Agrupar no navegador pelos parâmetros de organização do template (Disciplina/Subdisciplina).
- **Folhas:**
  - **Tamanho:** A1 (841×594) comporta a implantação inteira em **1:300**, recortada na rede com 10 m de folga; em 1:200 não cabe. Os 3D vão em **1:1000**, lado a lado, e os cortes em 1:200.
  - **Conferência do layout:** depois de posicionar, ler `Viewport.GetBoxOutline()` e o bounding box das tabelas na folha para achar sobreposições. Atenção à **tabela de revisão do carimbo** no canto direito.
  - **Tabelas:** colocar com `ScheduleSheetInstance.Create` pelo canto superior esquerdo.
- **Etiquetas:** 1 por trecho (o maior segmento do trecho, sem os tocos), com a família "Identificador do tamanho ... : Diâmetro" do template.
- **Filtros de cor por regra de sistema/marca** (`RBS_PIPING_SYSTEM_TYPE_PARAM` igual ao sistema; `ALL_MODEL_MARK` começa com "SDAI"), aplicados em todas as vistas novas, cortes inclusive.
- **Layers do CAD base que confundem** (ex.: `ARQ_DEMOLIÇÃO`, edificações existentes a demolir) devem ser **ocultados em todas as vistas** pela subcategoria do CAD (`CADLinkType.Category.SubCategories`). Deixar "cinza tracejado" ainda incomoda o usuário. Antes de ocultar, avisar do que se trata.

## A7. Relatório de incompatibilidades (formato que funcionou)

- **Estrutura do PDF A4 paisagem:**
  1. Capa.
  2. Projeto e metodologia (objeto, documentos, passos, legenda de severidade).
  3. Resumo: mapa geral com marcadores numerados por cor de severidade, mais a tabela.
  4. Uma página por ficha.
- **Cada ficha tem:**
  - selo de severidade;
  - 3D exportado do Revit com **círculo tracejado vermelho "FOCO"**;
  - recorte de localização em planta;
  - "O que foi encontrado", "Elementos/Local" (com coordenadas) e "Ação sugerida".
- **Ferramentas:** PyMuPDF com fontes Segoe UI. As cores e o logo seguem o padrão da empresa (Populus: dourado `#D8A800` e azul-marinho `#0B0B26`, com logo branco sobre o fundo azul).
- **Pegadinhas do script:**
  - `insert_textbox` devolve o espaço que sobrou: o espaço usado é `altura − sobra`;
  - quando o texto não cabe, reduzir a fonte em degraus;
  - listas longas vão abaixo da imagem, em duas colunas.
- **Saídas:** o PDF mais uma pasta `PRINTS_Rxx\` com as imagens marcadas.

## A8. Comportamento e comunicação

- Responder sempre em **português**.
- Validar cada disciplina sobre o CAD (checkpoint com o usuário) antes de seguir para a próxima.
- Quando houver divergência entre projeto e realidade (ex.: CT de projeto × terreno "as built"), **não "corrigir" o modelo em silêncio**. Modelar conforme o projeto e reportar como incompatibilidade, decidindo com o usuário se é erro do projetista ou da obra.
- Sempre informar os IDs e os nomes das vistas criadas e lembrar de salvar.
- **Quando o usuário aponta algo estranho num print** ("banheiro no meio do passeio", "outro caminho"), descobrir de **qual arquivo e de qual layer** aquilo vem antes de opinar (zoom da vista → geometria/raycast) e responder com o dado.
  - Se for divergência entre duas referências (ex.: caminhos do SIT R04 × passeios do IMP as-built), **quantificar e mapear** (m² e imagem) e perguntar como tratar: virar item do relatório ou ocultar.
  - Não "consertar" a referência.
- **Retomar o projeto** ("onde paramos"):
  1. ler a memória e o plano;
  2. listar os arquivos por data;
  3. ler o fim das transcrições anteriores;
  4. **consultar o Revit pelo MCP** (o que está aberto, os vínculos, os níveis, as contagens).

  O usuário pode ter avançado sozinho: neste projeto, o RVT de incêndio já tinha sido criado por ele.
- **Pedir só o que depende do usuário** (um clique que o Windows bloqueia, uma decisão de projeto) e fazer o resto: fechar e reabrir o Revit, desativar um suplemento com autorização, salvar.

## A9. Usar o PDF do projeto como fonte de dados

O Revit não importa textos de DWG, e o `accoreconsole` pode falhar. O PDF vetorial (PyMuPDF) tem todos os textos com posição.

- **Textos com posição:** `page.get_text('dict')` (spans com bbox, tamanho e cor). Filtrar por cor e tamanho, por exemplo os números de laço em vermelho com 7,9 pt; as cotas do QiBuilder são cinza e menores.
- **Tabelas e legendas** (quadro de bitolas, legenda de laços): `page.get_text('words')` agrupando por linha (y/6) dentro da caixa do título da tabela.
- **Transformação PDF → modelo:** basta uma similaridade com **2 âncoras** que se reconheçam nos dois. Usamos o centro do símbolo do hidrante de recalque e o centro da casa de bombas, achados em ampliações do PDF a 200 dpi (`get_pixmap(clip=...)`).
  - **Conferir pela escala:** 1:200 dá **0,0706 m/pt**; o obtido foi 0,07046.
  - Depois, casar cada texto com o bloco do DWG mais próximo. Os 20 números casaram com 20 blocos `NUM`, todos a menos de 0,45 m.
  - Os quadradinhos das caixas não serviram de âncora: só 6 das 15 eram retângulos no PDF.
- **Número com linha de chamada:** atribuir **cada número ao trecho mais próximo dele**, não cada trecho ao número mais próximo, porque os números ficam a ~2 m da linha e dá empate. Conflitos se resolvem pela lógica: ramal curto de um bloco = laço único; tronco = vários laços.
- **Diâmetro e material:** contar os rótulos (`PEAD 2.1/2"` 16×, `3"` 1× perto do reservatório) e cruzar com o **quadro de equivalência de bitolas** (2½" = PEAD DE 75; 3" = DE 85).
- **Ampliar regiões do PDF** para entender o projeto (casa de bombas, recalque) antes de modelar equipamentos.

## A10. Diálogos e suplementos do Revit (destravar sem o usuário)

Ferramenta: `D:\Projeto Modelagem\FERRAMENTAS\revit_dialog.ps1`. Ela lê o texto de qualquer diálogo do Revit (UIAutomation) e, com `-Click "texto"`, aperta o botão.

- **Sempre ler antes de clicar.**
  - **Aviso** (ex.: marca duplicada, hachura) → OK.
  - **Erro que não pode ser ignorado** → em geral **Cancelar**, que desfaz só o comando do MCP. "Desconectar" resolve conexões ruins sem perder o lote.
- **TaskDialog do Revit:** os botões aparecem como `Pane`, sem InvokePattern, então a ferramenta clica pela posição (`SetCursorPos` + `mouse_event`).
- **Diálogo Win32 clássico** (`#32770`, ex.: "Referências não solucionadas"): os botões e "command links" têm hwnd próprio, e **`PostMessage(BM_CLICK)` no hwnd do botão funciona** mesmo com o Revit em segundo plano.
- **O Windows bloqueia `SetForegroundWindow`** para processos em segundo plano. O clique por posição pode cair em outra janela que esteja por cima. Preferir BM_CLICK ou pedir o clique ao usuário (ex.: "Revit MCP Switch").
- **Com o Revit ocupado**, até a UIAutomation dá timeout ("Tempo limite da operação"). Esperar `Process.Responding` e tentar de novo.
- **Suplemento com MessageBox em loop** (ex.: DarivaBIM sem login: "Nenhum token fornecido", achado procurando o texto dentro das DLLs em `ProgramData\Autodesk\Revit\Addins\2025`):
  - a caixa não aceita PostMessage, só clique real, e reabre na hora;
  - **para salvar o trabalho:** deixar um comando do MCP na fila (`PostCommand(Save)`), clicar OK uma vez e o Revit salva antes de a caixa voltar;
  - **para resolver:** fechar o Revit, renomear o `.addin` para `.addin.off` (com autorização) e reabrir.
- **Reabrir o Revit por script:** `Start-Process Revit.exe "arquivo.rvt"`.
  - Esperar o título da janela conter o nome do arquivo (~3,5 min com 18 vínculos).
  - Tratar o diálogo de "Referências não solucionadas" (vínculos aninhados ausentes) com "Ignorar e continuar".
  - O **serviço do MCP não liga sozinho**: Complementos › "Revit MCP Switch".
- **Filtro de avisos via `FailuresProcessing`** instalado pelo código do MCP **não** evitou o aviso de hachura ao vincular DWG. Não contar com ele.

---

# PARTE B: ESPECÍFICO DO ETIB ALAGOINHAS-BA

## B1. Arquivos

| Item | Caminho |
|---|---|
| Modelo AF + ESG | `D:\Projeto Modelagem\Modelagem - HidroSanitário.rvt` (template DARIVABIM) |
| CADs georreferenciados | `D:\Projeto Modelagem\CAD_GEORREFERENCIADO\` (`...AGF-001-R06_GEO.dwg`, `...ESG-001-HIG-R06_GEO.dwg`, `...URB-001-SIT-R04_REF.dwg`, `transformacao_AF_local_para_UTM.json`) |
| Parâmetros compartilhados | `D:\Projeto Modelagem\BIM - Parametros Compartilhados - Compatibilizacao.txt` |
| Base "as built" (IMP) | `D:\Projeto Modelagem\REFERENCIAS_RVT\IMP\24-049-ALH-SLJ-ETIB-IMP_R00.rvt` |
| Blocos (FUN/ECC/EMT) | `D:\Projeto Modelagem\REFERENCIAS_RVT\` (TRT, GUA, SB5, BA2, RST, CDG_CDG), 16 RVTs |
| Relatório R00 | `D:\Projeto Modelagem\RELATORIOS\ETIB-ALH_Relatorio_Compatibilizacao_AF-ESG-EST_R00.pdf` + `PRINTS_R00\` |
| Origem dos dados | Drive CT049_2024 → "004-...QG as built Alagoinhas" (zip em `D:\Projeto Modelagem`; uma 2ª parte, possivelmente com RF2, ainda não foi processada) |
| Modelo Incêndio (hidrantes + SDAI) | `D:\Projeto Modelagem\MODELAGEM-INCENDIO.rvt` (template G.Alves V.15, já carregado no arquivo pelo usuário) + backup `MODELAGEM-INCENDIO_BACKUP_2026-10-09_1440.rvt` |
| Projeto de incêndio | `4 - IMPLANTAÇÃO...\14 - COMBATE A INCÊNDIO\24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05.dwg/.pdf` + memoriais em `DOCUMENTOS\` |
| Receita de vínculos do HS | `REFERENCIAS_RVT\posicao_vinculos_HS.json` (transformação de cada vínculo, CADs, pontos e níveis), para reaproveitar nas próximas disciplinas |
| Verificação do INC | `RELATORIOS\INC_Verificacao_Interferencias_R00.txt` e `RELATORIOS\INC_caminhos_SIT_x_IMP.png` |
| Ferramentas | `FERRAMENTAS\revit_dialog.ps1` (diálogos), `FERRAMENTAS\fechar_aviso_token.ps1` (tentativa para o DarivaBIM, que não funcionou), `FERRAMENTAS\incendio_scripts\` (topologia, cotas, SDAI e casamento PDF×DWG) |

## B2. Coordenadas

- **Origem interna do RVT:** UTM SIRGAS 2000 24S **E 561500 / N 8658000 / cota 0**, sem rotação; o norte do projeto é o norte da quadrícula.
- **AGF e ESG (QiBuilder, locais) → UTM:** rotacionar **+0,04622757474485582°** em torno de (0,0) e depois mover **+(561398.39297302 ; 8657855.98329653)**.
  - Obtida por ICP do bloco `ARQ_BASE_09-02-26`, embutido na AF, sobre a arquitetura da SIT, com resíduo de 2 mm.
  - O ESG tem o mesmo bloco na mesma posição e usa a mesma transformação.
- **IMP "as built":** tem coordenadas próprias (PBP E 561605,72 / N 8657885,97 / cota 138,12, rotação 8,06°).
  - O "SIT_MOVIDO" dele está deslocado **(−0,150 ; +0,165) m** em relação ao SIT R04 original.
  - O vínculo foi posicionado por transformação + esse ajuste, sem adquirir coordenadas.
- **Planta de implantação:** o bloco "curvas alaoinhas" foi removido da SIT_REF e os blocos foram explodidos.
- **Incêndio (`IN-001-ING-R05`, QiBuilder):** está em **outro sistema local**.
  - IN local **+ (65,3108830209 ; 27,4284168787)** = AF local, com a mesma rotação (conferido nos blocos ARQ_BASE_09-02-26, _TXT e _TXT2); depois vale a transformação da AF.
  - Georreferenciado dentro do Revit, sem `_GEO.dwg`, porque o accoreconsole falha nesse arquivo. O ARQ_BASE caiu sobre o da AF com 0,000 mm de desvio.
- **No INC, o SIT_REF vinculado por coordenadas compartilhadas** caiu na mesma posição do HS, com 0,001 mm de desvio. Um tubo do HS tem a mesma coordenada compartilhada nos dois arquivos, com Δ 0,000 mm.

## B3. Níveis e terreno

- **Platôs:** +135,50 / +136,10 / +137,40 / +138,50.
- O Toposolid feito a partir do topográfico foi **substituído pelo terreno do IMP** (vínculo), conforme a preferência por vínculos. O TOP chegou a ficar 135,5 m acima por ter sido colocado no nível da vista; foi corrigido.

## B4. O que foi modelado

- **AF:** 60 tubos, ~475 m, PVC soldável marrom (DE 25 a 75), do hidrômetro → bombas/RES → blocos (24 Salas Ø60, ADM/Auditório/Refeitório Ø50, Guarita e torneiras Ø25). A AF segue o terreno existente, e o renivelamento sobre o terreno "as built" segue **pendente**.
- **ESG:** 63 tubos, ~534 m, 42 caixas/PVs.
  - Caixas CI e CG com famílias UnMEP (`%APPDATA%\Autodesk\Revit\Addins\2023\UnMEP\Element\Familias\Caixas e Ralos`); os PVs como DirectShape.
  - Cotas conforme o projeto (CT = platôs).
- **Script do ESG** (`esg_build.py`):
  1. linhas duplas dos layers `TQ-Condutos` / `TQ-Condutos Gordura` → eixo;
  2. snap nos nós;
  3. tipo da caixa pela etiqueta do layer `Simbolos` (CE/CI/CES/CG);
  4. atribuição gulosa de CT/CF/CE/CS com validação;
  5. regra do tubo de queda;
  6. preenchimento da declividade.
- **Incêndio (INC):**
  - **Rede de hidrantes:** PEAD SDR 11, **DE 75 (2½") com 298,9 m** e **DE 85 (3") com 8,0 m**. O 3" é só o trecho reservatório → casa de bombas.
    - Tipo "INC - PEAD": segmento novo "PEAD - SDR 11" + conexões Tigrefire do template, testadas em DE 75/85.
    - Sistemas "INC - Hidrante" e "INC - Recalque".
    - **Recobrimento 0,50 m** (nota 5 do projeto). A rede toda fica fora da área de veículos, que é o polígono V1 da AF.
  - **Topologia:** 19 trechos e 7 tês, com um elo de 0,78 m no cruzamento junto ao CDG (no DWG, um elo de 0,37 m + arcos).
    - Os arcos de 0,35 m em pares no layer `HI-Condutos` são **símbolos de ponta** (tampão/"segue"), não tês.
    - O bloco `zw$4B94` é o detalhe da casa de bombas fora de posição (x ≈ 256): ignorar.
  - **Conexões:** 9 tês com tocos, 9 curvas (inclusive de 5,9° e 8,3°) e 3 ligações diretas (deflexão de 0,5°, curva de 3,5° e a redução 85×75, que não existe no template). Tampão nas 9 saídas "segue para instalações internas" (os hidrantes ficam dentro dos blocos).
  - **Casa de bombas:** DirectShape a partir do layer `0. F_PCI - Parede TRRF` (2,4 × 3,0 m, piso +136,00), com 2 bombas elétricas 5 cv + jockey (famílias do template; não são o modelo do projeto).
  - **Hidrante de recalque:** subida + registro com retenção (topo +138,83) + caixa 40×40 (DirectShape).
  - **SDAI:** eletroduto "SDAI - PEAD enterrado" Ø2" (padrão "SDAI PEAD" criado) com 271,9 m em 29 trechos e 15 caixas CX (DirectShape 0,68 m, profundidade 0,66–0,82 m).
    - Laços pela legenda do PDF (11 combinações de L01–L06 + 24Vcc).
    - S01/S02 (casa de bombas) = L06 e S15 (sai da central no CDR) = L01–L06, ambos **inferidos**.
  - **O IMP tem o reservatório só como massa** ("RESERVATORIOS"); não tem bombas nem recalque.

## B5. Erros que aconteceram e como resolvemos

| Erro | Causa | Solução |
|---|---|---|
| MCP travado/timeout | Janela modal no Revit | O usuário fechou a janela; depois, o fechamento passou a ser feito por PowerShell (user32) |
| "Transação aninhada" | `new Transaction` dentro do MCP | Usar a transação do add-in ou `SubTransaction` |
| SIT com lixo | Entidades distantes, bloco de curvas duplicado (layer travado), blocos deslocados | Limpeza em cópia: destravar o layer, apagar e explodir |
| AF desalinhada ~2,3 m | Transformação feita pela "ponte" do PDF | ICP no bloco ARQ_BASE (2 mm) |
| Toposolid 135,5 m acima | Criado no nível da vista | Mover −135,5 m |
| Joelho e tê não conectavam | Limitações da família (< 15°, ramal fora de 90°) | `ConnectTo` direto e tocos de 0,35 m |
| Corte vazio ou deslocado | Z invertido no CreateSection | Min.Z = 0 e corte 0,6 m à frente; Toposolid 85% transparente no modelo de corte |
| Vínculo IMP recusado por coordenadas compartilhadas | API/diálogo | Transformação calculada. A 1ª tentativa saiu invertida e foi refeita com `M = Th × Tl⁻¹` |
| Erro de "Iterator" ao apagar | Coleção alterada durante a iteração | `.ToElements()` antes |
| Tampa UnMEP 6 cm acima da CT | Origem da família | Baixar a elevação e a profundidade juntas. A CG-02 ficou na profundidade mínima da família |
| Prints 3D minúsculos | Crop box desligado | Ativar o crop box e ajustar à caixa de corte |
| Bugs no script do relatório | O campo info continha " \| "; heredoc quebrou `\n`; overflow de texto; `fit` devolvia o valor errado | `join(p[6:])`, `chr(10)`, redução de fonte em degraus, `r.height − rc` |
| Watcher de diálogos morto | Pouca memória | Não reiniciar sem o usuário pedir |
| MCP lendo o HS em vez do INC | O usuário trocou a janela ativa | Conferir `doc.Title` em todo código que edita |
| Vínculo de 10 RVTs deu timeout | Lote grande (105 s) | Lotes de ~6. A resposta veio atrasada na chamada seguinte |
| accoreconsole travado/ErrorStatus 53 no IN-001 | Objetos QiBuilder | Georreferenciar no Revit + textos do PDF |
| Movimento do CAD "não aplicado" | `GetTotalTransform` de ImportInstance não muda | Ler `GeometryInstance.Transform` |
| Topologia com laço de comprimento zero | Elo de 0,37 m colapsado pelo snap de 0,6 m | Tirar o elo do snap e recriá-lo como trecho explícito |
| Trecho de 3" não detectado | Vértice de divisão errado (o snap moveu a ponta) | Imprimir os vértices do trecho e usar o vértice real |
| Erro "direção oposta" nos tês | Tubo redirecionado com o sentido invertido | Preservar o sentido (A3) |
| "Marca duplicada" (aviso) | Dois tocos no mesmo tubo | OK no aviso e renumerar as marcas |
| Bombas e registro em z ≈ 0 | Família baseada em plano de trabalho | `MoveElement` em Z |
| Erro de conectividade no eletroduto | Condulete 90° em dobra suave | "Desconectar" e apagar as curvas órfãs |
| Corte sem nível de detalhe | Modelo de vista do tipo de corte | `ViewTemplateId = Invalid` |
| 3D grande demais na folha | Escala 1:600 | 1:1000 e conferir os contornos |
| Revit travado por "Nenhum token fornecido" | DarivaBIM sem login | Salvar via PostCommand, fechar e desativar o suplemento |
| "Banheiro no meio do passeio" | Layer `ARQ_DEMOLIÇÃO` do SIT (existente a demolir) | Ocultar o layer em todas as vistas INC |
| "Outro caminho" cinza | Hachura `#ARQ_CAMINHOS` do SIT R04 sem correspondente no IMP | Mapear a divergência (454 m² viram grama no IMP) e decidir com o usuário |

## B6. Resultado da compatibilização (R00)

**16 fichas:** 8 críticas, 6 de atenção, 2 de informação.

**Críticas:**

| Ficha | Problema |
|---|---|
| INC-01 | AF-11.1 × ESG-36 |
| INC-02 | AF-07.5 × ESG-58 |
| INC-03 | AF-07.3 atravessa o PVE-07 |
| INC-05 | Guarita AL-01.1 × sapata |
| INC-06 | RST ESG-29 × sapata |
| INC-07 | CDR ESG-23 × pilar/sapata corrida |
| INC-08 | BA2 AF-12.1 e ESG-41 × sapatas |
| INC-10 | 11 caixas com CT acima do terreno final |

**Atenção:**
- 4 folgas AF × ESG abaixo de 0,20 m;
- baldrames × ESG-27/28/61 (RST) e AF-07.6 (SB5);
- caixas expostas ou soterradas: 26 acima e 12 abaixo do terreno "as built";
- CG-02 rasa.

**Informação:** caixas sem cota no projeto e o deslocamento de ~22 cm do "as built".

**Conclusão-chave:** a CT das caixas é a do projetista (cota de platô), mas o terreno executado difere. Por isso a divergência foi tratada como incompatibilidade (projeto × obra), sem ajuste no modelo.

**Verificação do Incêndio (09/10/2026), a entrar no relatório R01:**
- **INC × AF/ESG: 14 colisões.**
  - INC-T01.2 atravessa o **PVE-08**;
  - a linha do recalque (T19) atravessa a **CI-21**;
  - cruzamentos na mesma profundidade com a AF de bombeamento junto ao reservatório (AF-02/03/05/11), com a AL-02.3 e com o ESG-11;
  - a caixa CX03 do SDAI é atravessada pela AF-11.1.
  - Folgas menores que 0,20 m em vários pontos.
- **INC × estruturas: 7 colisões**, todas em ramais que entram nos blocos: T07 × sapatas/pilares do BA2 e T09 × bloco de fundação do TTR.
- **Referências:** o tronco norte (T05/S04/S05) passa sobre a área da demolição (`ARQ_DEMOLIÇÃO`), e a demolição e a remoção das fundações antigas têm de vir antes. Caminhos do SIT R04 × IMP: 454 m² de caminho do SIT são grama no IMP e 53 m² são asfalto.

**Relatório R01 (13/10/2026):** `RELATORIOS\ETIB-ALH_Relatorio_Compatibilizacao_AF-ESG-EST_R01.pdf` (20 páginas, 17 fichas: 8 críticas, 7 atenção, 2 informação) + `PRINTS_R01\`.
- Nova ficha **INC-17 (ATENÇÃO): caminhos do SIT R04 (#ARQ_CAMINHOS) ausentes no IMP as built.**
  - De ≈867 m² de caminho, 454 m² são grama e 53 m² são asfalto no IMP.
  - Redes sob esses caminhos: AF 37,7 m, ESG 50,8 m, INC 17,1 m e SDAI 11,0 m. Vale conferir o recobrimento onde o caminho vira asfalto (ESG-15/43/11, AF-13.7).
  - Vista no INC: "COMPAT - INC-17 - CAMINHOS SIT x IMP".
- **Fontes do relatório agora ficam no projeto:** `RELATORIOS\fonte_relatorio\`, com `rel\dados.json` + imagens, `relatorio.py`, `prep_rel.py` (R00) e `build_R01.py`.
  - Para uma nova revisão: acrescentar a ficha em `dados.json` (por script), regenerar `mapa_geral.png` e rodar `python relatorio.py <pasta fonte> <pdf>`.
  - A planta base tem escala fixa de 30 px/m: `PX = (x+32)·30`, `PY = (52−y)·30`.
- **Pendente:** as colisões do Incêndio (verificação de 09/10) ainda **não** viraram fichas; o subtítulo do relatório continua "AF × ESG × Estrutura".

## B7. IDs úteis no RVT

| Item | ID |
|---|---|
| Modelo `COMPAT - 3D` | 455857 |
| Vistas `COMPAT - INC-01…14` | 455861 a 455982 (INC-08 em 08A/08B) |
| `COMPAT - PLANTA GERAL` | 455991 (vínculo SIT 456001) |
| Vínculo IMP | 455751 |
| Modelos ESG: planta / 1-300 / corte / 3D | 444356 / 444368 / 445186 / 445175 |
| Cortes ESG | 445178, 445189, 445198, 445207, 445216 |
| Tabela de tubulação ESG | 445224 |
| Folhas ESG-VAL | 445232 / 445238 / 445244 |
| Folhas AF-VAL | 444165 / 444171 / 444177 |
| Filtros | "COMP - Disciplina AF" / "COMP - Disciplina ESG" |

**MODELAGEM-INCENDIO.rvt:**

| Item | ID |
|---|---|
| Vínculo do DWG IN-001 (georreferenciado) | 8676304 |
| Plantas: VALIDAÇÃO CAD / MODELO / SDAI VALIDAÇÃO / COORDENAÇÃO | 8674988 / 8677140 / 8677152 / 8677164 |
| Folha 1:300: implantação / SDAI | 8677287 / 8677298 |
| 3D validação | 8676635 (+ "COMPAT - INC x AF x ESG - 3D") |
| Cortes 01–04 | 8677252 / 8677261 / 8677270 / 8677279 |
| Casa de bombas / bombas / registro de recalque / caixa do recalque | 8677034 / 8677035–37 / 8677046 / 8677047 |
| Folhas | INC-VAL-01, 02, 03 |
| Vista "COMPAT - INC-17 - CAMINHOS SIT x IMP" | 8677444 |
| Filtros | "INC - Hidrante", "INC - Recalque", "INC - SDAI", "INC - Equipamentos" |

## B8. Pendências

- Renivelar a AF sobre o terreno "as built" (definir com o usuário).
- Decidir se as tampas das caixas acompanham o terreno, mantendo o CF.
- Vincular a arquitetura dos blocos e processar a 2ª parte do zip (RF2).
- Próximas disciplinas em RVTs próprios (drenagem, GLP, elétrica/dados), com a mesma origem e com os vínculos copiados de `posicao_vinculos_HS.json`. A federação será no Navisworks 2024.
- **Incêndio:**
  - Checkpoint 2 (validação do traçado, dos diâmetros e dos laços pelo usuário);
  - confirmar as premissas: trecho de 3", casa de bombas esquemática, laços S01/S02/S15 e redução 85×75 direta;
  - colocar as fichas INC no relatório R01.
- **Divergência SIT R04 × IMP nos caminhos:** registrada como INC-17 no R01. Falta a resposta da arquitetura/urbanismo sobre qual implantação vale.
- **HS:** ocultar o layer `ARQ_DEMOLIÇÃO` nas vistas AF/ESG.
- **DarivaBIM está desativado** (`darivabim.addin.off`). Reativar renomeando de volta, depois de fazer login.
- **Arquitetura dos blocos:** é o aviso de 12 referências não solucionadas ao abrir (vínculos aninhados no IMP). Extrair do zip se for preciso.

---

# DRENAGEM (iniciada em 13/10/2026) — notas parciais

- **DWG DRE-001-DRG-R04 usa o mesmo sistema local da AF** (blocos ARQ_BASE coincidem a <1 mm; AF tem o bloco aninhado em `zw$C2DE`, inserido em (200.004;127.138)). Georreferenciado com a transformação da AF em `CAD_GEORREFERENCIADO\...DRE-001-DRG-R04_GEO.dwg` (JSON `transformacao_DRE_local_para_UTM.json`). O accoreconsole abre este DWG sem erro.
- **accoreconsole (A5):** para ROTATE/MOVE de todo o modelo, o script precisa de `(setvar "TILEMODE" 1)` + `(setvar "CTAB" "Model")`; sem isso aparece "were not in current space" e nada é movido. Descongelar/destravar layers antes (`-LAYER T * ON * U *`). Passar o ângulo como string (`"0.04622757474485582"`).
- **Texto e geometria saem do DWG por LISP** (`FERRAMENTAS\drenagem_scripts\dump.lsp` → TSV por entidade, 29 mil linhas em UTM). Não foi preciso PDF.
- **Condutos desenhados em escala**: duas paredes (LINE) em AP-Condutos com espaçamento = Ø real (0,04 m = 40 mm; 0,10–0,11 = PVCR 100; 0,14–0,15 = 150; 0,20/0,25/0,30/0,40 = PVC-V). Setas de sentido de fluxo em `AP-Sentido conduto` (LWPOLYLINE de 0,8 m no eixo do tubo, sentido primeiro→último vértice — a confirmar). MLINE em AP-Condutos = 12 trechos em linha única.
- Cotas: `TQ-Textos conduto` guarda CT./CF./(prof) e CE./CS. das caixas e PVs (77 triplas CT/CF); rótulos de tubo em `AP-Textos conduto` (3 MTEXT: material, "NNN mm", "i=N%", com rotação do tubo). `AP-Caixa de alvenaria` (56 CAs conectadas) + `TQ-Caixa de alvenaria` (~12 caixas); vários PVs de tronco não têm caixa desenhada (só o vazio na junção).
- Pares de paredes por script falham em feixes densos de drenos de condicionadores (paredes de tubos vizinhos pareiam errado); solução parcial: ancorar na seta (centro da seta = eixo; paredes simétricas) e completar com pares de Ø nominal sem seta.
- **MCP do Revit não conectou nesta sessão** (CONNECT_TIMEOUT na inicialização): ligar o "Revit MCP Switch" antes de abrir a sessão.
- Scripts: `FERRAMENTAS\drenagem_scripts\` (drn_geom, drn_runs, drn_labels, drn_net, drn_topo, drn_cotas, plotdrn/plotruns); resultados intermediários em `work\*.pkl`.

## Drenagem — progresso de 13/10/2026 (tarde, modo contínuo)

- **MCP voltou a conectar** (documento ativo = MODELAGEM-INCENDIO; nao editar nele). `MODELAGEM-DRENAGEM.rvt` foi criado como CÓPIA do HS (`Modelagem - HidroSanitário.rvt`, 13/10 09:47) e aberto em segundo plano por `app.OpenDocumentFile` (o aviso de hachura aparece: fechar com `revit_dialog.ps1 -Click OK`). Documento nao ativo recebe `new Transaction(dr, ...)` proprio (a transacao do MCP é do ativo).
- **PENDENTE (bloqueio): limpar AF/ESG da cópia.** O classificador de permissões do Claude Code negou a exclusão em massa (123 tubos, 47 conexões, 22 DirectShape, vistas/folhas `AF -`/`ESG -`/`COMPAT -`, DWG AGF/ESG). Precisa do OK explícito do usuário (ou outra via: projeto novo por template).
- **Rede extraída e resolvida offline** (`FERRAMENTAS\drenagem_scripts\`): `drn_topo.py` → `drn_cotas.py` → `drn_solve.py` → `work\network_drn.json` + `work\trechos_drn.csv`. 410 trechos / 1.905 m após limpar laços, trechos < 0,35 m e duplicatas sobrepostas (730 → 410). DN por espaçamento das paredes (rótulo corrige 16); materiais pela legenda do projeto (≤50 soldável / 75–150 reforçado / ≥200 Vinilfort).
- **Terreno:** o IMP "as built" está em média 0,45 m abaixo do CT de projeto. Amostrado via `ReferenceIntersector` no INC (`{3D}`) → `work\terreno_z.csv`. O terreno de projeto de cada nó = CT da caixa mais próxima corrigido pela diferença do IMP.
- **Erro de projeto (INFORMAÇÃO/ATENÇÃO):** nos PVs do tronco PVC-V 250 (x≈+38…+70 / y≈−35…−23) e em outros 16 pontos os rótulos CE/CS ficam ~2,7 m ACIMA do CT (ex.: CE 137,83 com CT 136,10 e CF 135,18; a sequência CE/CS acompanha a CF + 2,74 m). Foram descartados pelo script; vale a CF. Listados em `work\solve_report.txt`.
- **Offset de PDF → modelo** (conferência visual): `X_pdf = 11,3386·(E−561500)+824`, `Y_pdf = 880 − 11,3386·(N−8658000)` (pt; 1:250). Renderizar com PyMuPDF (`pymupdf`) para ver rótulos.
- Lições de extração: o mesmo DWG repete CE/CS em linhas diferentes; atribuir rótulo a NÓ (não a ponta de trecho) e validar contra CT. Hubs de grau 20–46 eram símbolos de CA/PV (arestas minúsculas): remover antes de resolver. `numpy.linalg.lstsq` com coeficientes em dicionário: cuidado com chaves repetidas (colapsam e zeram a variável).

## Drenagem — entrega do modo contínuo (13/10/2026, 11:50)

- **Arquivo:** `MODELAGEM-DRENAGEM.rvt` (+ `_BACKUP_2026-10-13_1150.rvt`). Cópia do HS com AF/ESG apagados (autorizado pelo usuário só na cópia). **Base reaproveitável para as próximas escolas:** `TEMPLATES\MODELO-BASE-ESCOLAS_limpo_2026-10-13.rvt` (HS sem AF/ESG, com tipos de tubo, filtros, parâmetros COMP_*; os vínculos/níveis/coordenadas são os da ETIB e precisam ser trocados em cada escola). Templates brutos no Drive: `DFE PROJETOS OFICIAL\TEMPLATE REVIT\TEMPLATE.BIM HIDRO 5.0 + UNMEP.rte` e `CLIENTES\template-hidro-anderson.rte` (Revit 2023: a atualização para 2025 leva vários minutos e trava o MCP).
- **Modelado:** 410 tubos (1.905 m), 56 caixas (CX) e 31 PVs como DirectShape (Modelos genéricos), 3 tipos `DRN_Tubo …` (segmentos com DE real), sistemas `DRN - Águas pluviais` / `DRN - Dreno de ar-condicionado`, filtros `DRN - …`, modelo de vista `DRN - PLANTA`, 4 folhas `DRN-VAL-01…04`, 5 cortes, 5 `COMPAT - DRN - …`, tabelas. Tubos **sem conexões** (esquemático, trecho a trecho).
- **Lições de API/MCP:**
  - documento NÃO ativo: `app.OpenDocumentFile` abre em 2º plano e dá para editar com `new Transaction(dr, …)` próprio e `dr.Save()` (a transação do MCP é do documento ativo). Funciona para vincular CAD (`dr.Link(path, DWGImportOptions{ThisViewOnly}, view, out id)`), criar vistas, folhas, tabelas e `ExportImage` de folhas.
  - `IndependentTag.Create` num documento com 17 vínculos leva ~35 min para 222 etiquetas e o MCP dá timeout (o comando continua rodando). Alterar escala de vista/folha com muitas etiquetas também demora. Esperar o Revit ficar ocioso medindo `Get-Process Revit` CPU (Δ < 0,8 s em 10 s) e conferir com consulta-marcador.
  - `MEPSize` está em `Autodesk.Revit.DB` (não em `.Plumbing`); `View.CreateViewTemplate()` não recebe nome (renomear depois); `using` em código do MCP vira "using statement": usar nomes qualificados.
  - Tabela longa em folha estoura: dividir por prefixo (CX-/PV-), esconder coluna de observação, `SetColumnWidth`, unidades em m com `FormatOptions(UnitTypeId.Meters)`.
  - Bloco de título "A1 métrico" do HS ocupa a faixa x > ~715 mm: manter vistas em x < 715.
  - Interferência sem Navisworks: distância segmento×segmento (3D) entre eixos menos raios para tubo×tubo; `ElementIntersectsSolidFilter` por tubo contra vínculos estruturais (63 interferências em ~12 min).
- **Achados de projeto (ver `RELATORIOS\DRN_Interferencias_R00.csv`):** rótulos CE/CS acima do CT em 16 pontos (descartados, vale CF); declividade padrão em 276 de 410 trechos (sem rótulo); terreno IMP "as built" 0,45 m abaixo do CT de projeto (103 tubos acima do terreno as built; 54 tampas > 0,30 m acima).
- **Pendente:** vincular o INC (arquivo aberto na sessão não pode ser vinculado; clash INC×DRN foi calculado direto pelo documento aberto: 3 colisões + 24 folgas < 0,20 m); validação do traçado pelo usuário; fichas DRN no relatório R02.

## Drenagem — ajustes pós-feedback (13/10/2026)

- **Lacunas:** vinham de (a) elos < 0,35 m removidos na limpeza e (b) pontas dos tubos fora do nó. `FERRAMENTAS\drenagem_scripts\drn_fix.py` une nós ligados por elos minúsculos, encosta as pontas no centro da caixa/no centróide do nó e classifica interno/externo (`work\revit_pipes_fix.csv`). Aplicado movendo `LocationCurve` dos 410 tubos (409 ok; DRN-378 colapsou a comprimento 0 e ficou como estava).
- **Conexões:** `NewElbowFitting`/`NewTeeFitting` geram o erro não ignorável "tubo modificado para direção oposta" e desfazem tudo; vale só `Connector.ConnectTo` entre ponta de jusante de um tubo e ponta de montante do outro (cauda→cabeça). 79 pares ligados (158 de 820 conectores); ficam sem ligar: 98 nós com > 2 pontas, 15 pares cabeça×cabeça, 8 com Δz > 2 cm. Pipes soltos nas caixas (DirectShape).
- **Interno × externo:** sistema `DRN - Interno (ramais de edificação)` (filtro com visibilidade desligada nas plantas, 3D e cortes). Critério: DN ≤ 50 ou (DN ≤ 100 e ponto médio dentro de laje do IMP/ECC): 149 tubos, 515 m. O IMP/ARQ aninhado não está extraído, então o contorno dos blocos é aproximado; conferir.
- **Etiquetas:** `IndependentTag.Create` fica ~100× mais rápido com `OST_RvtLinks` oculto e os CADs ocultos na vista durante a criação (0,5 s para 15 tags). Só trechos externos > 6 m (110 tags).
- **Poluição:** o CAD "TOP" (levantamento) trazia as cotas pontuais; oculto na vista com CAD, junto com 21 layers de texto/cotas do SIT.
- Quando o usuário troca de janela, o documento ativo do MCP vira o da drenagem: aí NÃO abrir `new Transaction` (só SubTransaction) e salvar com PostCommand(Save).

## Drenagem — erros achados pela validação do usuário (13/10/2026, noite) e auditoria

Erros meus (valem para qualquer disciplina extraída de DWG QiBuilder):
1. **Caixas duplicadas:** o DWG desenha cada caixa com 2 contornos (parede interna e externa) e o agrupamento por linhas virou 2 caixas no mesmo ponto (22 duplicadas). Regra: deduplicar caixas por centro (< 0,3 m).
2. **PV falso:** tripla CT/CF ligada a um nó de junção perto de uma caixa real criou PV fantasma (2). Regra: não criar PV a < 2 m de caixa existente.
3. **Caixas e PVs só onde havia tubo:** 18 CA e 12 PVP do projeto ficaram de fora porque eu só modelava caixa de nó da rede. Regra: as caixas vêm dos SÍMBOLOS do DWG (texto "CA" no layer Simbolos e bloco `zw$12D9` = PVP), com e sem tubo; depois conferir símbolo × modelo.
4. **Trechos perdidos:** 9 trechos (80 m), inclusive PVC-V 300 (20 m) e PVC-V 200 (18 m), sumiram na limpeza de duplicatas/feixes. Regra: no fim, cobertura parede-de-conduto × tubo modelado (`drn_audit.py`) e listar o que ficou > 1,5 m sem tubo.
5. **Declividade anômala:** 33 tubos com i < 0 ou > 3% (pontas encostadas em caixas de cota diferente/rotulo errado). Marcados em `COMP_Observação` "DECLIVIDADE ANÔMALA" para o relatório, sem correção silenciosa.
6. CSV com `;` dentro de texto: o `csv.writer` coloca aspas e o `Split(';')` do C# quebra o campo. Não usar `;` em observações ou ler com parser de CSV.

Correções aplicadas: −24 caixas (22 dup + 2 PV falsos), +28 caixas/PVs (17 CA 0,60 + 11 PVP Ø1,10; 8 CA sem tubulação no projeto com nota "RELATÓRIO: CA sem tubulação no projeto R04" nas plantas), +9 tubos `DRN-A01…A09`. Agora: 91 caixas/PVs, 419 tubos. PDF: `RELATORIOS\DRN_revisao_pos_validacao_tablet_2026-10-13.pdf`.
Para o relatório R02: 8 CA sem tubulação; rótulos CE/CS acima do CT (16); 33 declividades anômalas; terreno as built × projeto.

## Drenagem v2 — método "como o projetista" (13/10/2026, noite)

Diagnóstico da v1 (por que a drenagem deu tanto retrabalho e AF/ESG/INC não): rede por gravidade é uma ÁRVORE com centenas de ramais pequenos desenhados em parede dupla, feixes e pedaços de 3 m; eu extraí linhas e deduzi a rede, e só validei linha × tubo. Resultado: só 32% dos 2.070 m chegavam a um lançamento; 7 tubos vinham de um DETALHE (corte de prumadas) desenhado no espaço do modelo (x≈220 m).

Método v2 (`FERRAMENTAS\drenagem_scripts\drn_v2.py` → `drn_v2b.py` → `drn_v2c.py`, mapa `plotbacias.py`):
1. Recortar só a implantação (fora dela = detalhes/cortes do desenho).
2. Nós de projeto primeiro: lançamentos ("SEGUE PARA A REDE..."), PV (bloco `zw$12D9`), CA (texto "CA" em Simbolos), prumadas AP (ponta da chamada fora do balão; a linha interna do balão NÃO é chamada).
3. Eixos: setas + pares de parede + paredes sem par (= linha simples: drenos de 32 mm) + MLINE; unir colineares; cortar nas caixas e nos tês; pontas a < 1,2 m de caixa ou < 0,9 m de trecho são ligadas (o desenho não encosta).
4. Sentido: seta do projeto; sem seta, pela distância hidráulica ao lançamento; nó que recebe e não tem saída → inverter trecho sem seta (ou seta curta < 2,5 m de outro tubo).
5. Validação obrigatória: todo trecho escoa até um lançamento; toda prumada e toda caixa ligadas; listar o que não fecha como dúvida de projeto.
6. Cotas por mínimos quadrados com sentido fixo (CS na saída, CE na entrada, CF; CE/CS acima do CT descartados) e checagem de trecho subindo/raso.
Resultado v2: 511 trechos / 2.305 m, 100% chegam a um dos 3 lançamentos; 68/70 prumadas ligadas; 8 trechos "sobem" por cotas do projeto.

## Erro de sobreposição PDF × modelo (14/10/2026) — documentado a pedido do usuário

- Sintoma: no PDF "mapa v2 sobre a arquitetura", a rede aparecia ~2 m a leste (e ~0,2 m ao sul) da rede desenhada no PDF do projeto. O MODELO não estava deslocado (as coordenadas vêm do DWG georreferenciado, conferido no Revit contra o SIT com Δ ≈ 0); o erro era só na montagem da imagem.
- Causa: a transformação PDF → modelo foi calibrada casando TEXTOS de cota (votação em caixas de 4 pt). No PDF a posição de um texto é o centro da palavra; no DWG é o ponto de inserção do MTEXT (canto). Diferença ≈ meia palavra → ~2 m. Além disso assumi escala exata 1:250 (real: 11,317 pt/m, −0,19%) e sem rotação (real: −0,0462°, a mesma do georreferenciamento).
- Correção: calibrar com GEOMETRIA exata e repetida (142 círculos das chamadas de prumada: centro no DWG × centro do caminho no PDF), mínimos quadrados de similaridade (escala, rotação, translação) → resíduo 0,000 m. Transformação em `work\pdf_transform_geo.txt`.
- Regra: nunca calibrar sobreposição por textos; usar círculos/blocos/vértices; sempre reportar o resíduo e conferir 2–3 símbolos visualmente (PV sobre PV, caixa sobre caixa) antes de enviar.

## Substituição da rede de drenagem pela v2 no Revit (14/10/2026)
- **MCP do Revit sem conectar (CONNECT_TIMEOUT do npx)**: o plugin continua escutando em localhost:8080. Cliente direto: `FERRAMENTAS\revit_rpc.py arquivo.cs [timeout]` (JSON-RPC `send_code_to_revit`, mesmo contrato). O plugin tem timeout próprio (~1–2 min): "代码执行超时" = Revit ainda rodando; esperar CPU ociosa e conferir.
- **ConnectTo em emendas de mesmo DN** faz o Revit inserir luvas/uniões automaticamente (preferências de roteamento); as que ficam curtas geram um aviso modal por luva ("A linha é muito curta") que trava o plugin até alguém clicar OK. O clique por UIAutomation não funcionou nesse diálogo — pedir ao usuário. Próxima vez: conectar só depois de checar se o tipo de tubo tem união configurada, ou aceitar sem ConnectTo.
- **Rótulo CE/CS acima da tampa/terreno** (PV04: 137,76/137,83 com terreno 136,06) puxa o mínimo quadrados e cria trechos subindo; filtrar no solver (descartar + registrar), nunca usar.
- **Cortes longitudinais**: o terreno cortado (vínculo) esconde tudo que está atrás do plano, então o plano precisa passar exatamente pelo eixo do coletor (girar + mover o viewer pelo ajuste dos trechos; profundidade ~1,5 m). Deslocar "no escuro" não funciona. Coletor com quebras (oeste: 6–15°) → um corte por trecho reto.
- Rede v2 no modelo: 516 tubos (476 AP + 40 internos, 2.471,7 m), 82 caixas/PV (DirectShape `DRN-V2-<id>`), ids em `work\v2_pipes_ids.csv` / `v2_boxes_ids.csv`. Backup da rede antiga: `MODELAGEM-DRENAGEM_BACKUP_2026-10-14_rede-antiga.rvt`.

## Drenagem v2 R02 — feixes, mergulhos e pés de prumada (14/10/2026)
Pergunta do usuário que revelou o problema: "você verificou a inclinação da rede?". Eu só tinha olhado estatística (mediana), não trecho a trecho.
- **Erro 1 (extração): feixes de tubos paralelos.** Nas fachadas o projetista desenha um tubo POR PRUMADA, lado a lado a ~12 cm, até a caixa. O detector "parede + parceira mais próxima" casou paredes de tubos vizinhos (folgas 10–40 mm) → 113 tubos falsos (DN32/DN40) e os tubos reais fundidos no mesmo eixo (sobrepostos). **Regra:** par de paredes = mesma extensão (pontas iguais) + espaçamento de diâmetro de desenho (40, 75, 95–105, 145, 200, 250, 300, 400 mm); cada trecho de parede usado UMA vez (ranking guloso). Na topologia, nada de tê/fusão/ligação entre tubos PARALELOS afastados > 6 cm (são vizinhos de feixe), e ponta que já é cotovelo não vira tê no corpo de outro.
- **Erro 2 (cotas): forçar declividade para vencer desnível.** O projeto vence desnível com CONEXÕES VERTICAIS desenhadas como círculo duplo (camadas Simbolos + Simbolos_int, raio ∝ DN): **pé de prumada** (joelho no início do ramal, vertical enterrada até o terreno) e **mergulho** (antes da parede da caixa, desce até a CE). Modelar essas verticais; o tubo horizontal fica SEMPRE na declividade do rótulo (ou 1%). (Observação do usuário: "se não os tubos vão sair tortos".)
- **Erro 3 (cotas): CE/CS valem para o tubo do rótulo, não para todas as entradas/saídas** — cada rótulo vai para a caixa mais próxima e, dentro dela, para o tubo mais próximo do texto. Aplicar a CE única a todas as entradas criou o "trecho subindo" PV20→PV19.
- **Erro 4 (cotas): fundo de CA (caixa de areia) não é cota de tubo** — tem rebaixo; é limite inferior.
- **Solver:** mínimos quadrados com conjunto ativo de verdade (ativa a desigualdade violada E SOLTA a que puxa para o lado errado — sem soltar, "entrada ≥ saída" vira igualdade e gera 8–17%). Recobrimento mínimo como desigualdade só fora de caixa; se obrigar trecho a subir, libera e registra (terreno estimado × cota do projeto).
- **Validação obrigatória antes do Revit** (`drn_v2c2.py` + leitura de volta do Revit): 0 sobreposições, 0 trechos subindo, junções sem conexão com Δz ≤ 5 mm, declividade × rótulo trecho a trecho (204/210 iguais; 6 impostos pelas cotas das caixas → relatório).
- **ConnectTo** em emendas → Revit insere luvas e abre aviso modal por luva; nesta rodada NÃO conectei (continuidade geométrica).
- **14/10/2026 — drenagem R02 VALIDADA pelo usuário.** Fluxo que funcionou: extração v2 (lógica do projetista) → mapa sobre a arquitetura (calibrado por círculos) → validação visual → cotas com conexões verticais do desenho → checagem trecho a trecho (lida de volta do Revit) → substituição no Revit com backup.

## AF renivelada sobre o terreno as built (14/10/2026)
- **Decisão do usuário:** o projeto AF não tem cota de tubo → cota da AF é **premissa de modelagem** (recobrimento 0,30 m; 0,60 m em V1), **nunca item de relatório**. O recobrimento do ESG continua sendo item de relatório (vem das cotas do projeto).
- Auditoria AF/ESG (DWG × modelo): sem trecho perdido, duplicado, DN errado; ESG 9/9 PVs e 33/33 caixas. Scripts em `FERRAMENTAS\auditoria_afesg\` (audit_esg.py, audit_af.py).
- Renivelamento (`af_renivel.py` → `af_plano_revit.py`): mantém a planta, Douglas-Peucker 0,20 m / 2 m, nós da casa de bombas/reservatório (x 91,5–99,5 / y 2–14) FIXOS nas cotas atuais (alinhados às bombas). Grupos tê+tocos movidos inteiros em Z (não recriados); 31 tubos principais → 35 trechos; 9 cotovelos/bucha recriados; 2 dobras de 2,6° e 3,5° em ligação direta. Recobrimento conferido no modelo (1.037 pontos): 0,28–0,94 m, nenhum acima do terreno. Backup: `Modelagem - HidroSanitário_BACKUP_2026-10-14_pre-renivel-AF.rvt`.
- **Editar um RVT que está só VINCULADO** nos documentos abertos: descarregar o vínculo em todos (no documento não ativo, `RevitLinkType.Unload(null)` direto pelo MCP; no ATIVO dá "open transaction phase" → registrar um handler `UIApplication.Idling` que descarrega e se remove), depois `app.OpenDocumentFile` (aviso de hachura → `revit_dialog.ps1 -Click OK`). No fim: `Close(false)` e `Reload()`. O mesmo vínculo só recarrega em UM documento por sessão ("loaded into multiple documents") — o outro fica descarregado até reabrir.
- **NÃO usar `Application.FailuresProcessing` com `ProceedWithRollBack` no código do MCP:** o comando travou até o timeout sem aplicar nada. Funcionou: transação principal sem handler + cada cotovelo em transação própria com try/catch e fallback `ConnectTo`.
- `NewElbowFitting` recusa deflexão pequena ("angle too small" / "not close enough"): 2,6° e 3,5° → ligação direta.
- Etiquetas: ~33 por vista em ~2,7 min mesmo com vínculos e CAD ocultos (HS tem 17 vínculos). Rodar e acompanhar por log em arquivo.

# ELÉTRICA / DADOS / CFTV (iniciada em 15/10/2026, modo por fases)
- **Fase 1 (diagnóstico) feita.** 4 DWGs, todos em coordenadas LOCAIS (m) com os blocos ARQ_BASE_09-02-26 / _TXT / _TXT2: EL-001-ELG-R07 (alimentação BT, SUB/QGBT → quadros dos blocos, bancos de eletrodutos), EL-002-ELG-R05 (iluminação externa, circuitos IE-xx, postes), CF-001-ELG-R05 (CFTV, câmeras nos postes, FO/UTP), CF-002-ELG-R04 (dados/telefonia, entrada das concessionárias, caixa R-2).
- **Georreferência** por ajuste rígido nos 3 blocos ARQ_BASE (contra o ESG_GEO em UTM): rotação 0,04622337° (= AF), resíduo 0,000 m. EL-001 tem translação própria (561101,4113 ; 8657866,3342); EL-002/CF-001/CF-002 = (561101,3499 ; 8657866,7961). Arquivo: `FERRAMENTAS\eletrica\transformacao_ELE_local_para_UTM.json`.
- Rede enterrada = layer `02. F_ELETRODUTO PISO` (+ `02. F_ELETRODUTO`). `E-eletrodutopiso/teto`, `E-quadro` etc. são internos (sala de quadros). Rótulos do CF-001/CF-002 estão em MULTILEADER (o dump não lê o texto) → ler pelo PDF.
- Quantidades brutas (soma de linhas): EL-001 ~1.040 m (bancos), EL-002 ~870 m, CF-001 ~590 m, CF-002 ~440 m. Caixas por texto: EL-001 13×80×80 + 7×60×60; EL-002 26 "Cx 80x80" (o bloco se chama Cx60x60, 32 inserções); CF-001 23 "Cx 60x60" (25 blocos); CF-002 21×80×80 + 2×20×20 + 1×40×40.
- Memoriais (MD-PE-ELG-R01, MD-PE-CF-001) NÃO trazem profundidade de eletroduto enterrado → premissa a decidir com o usuário.
- accoreconsole no SIT_REF completo estoura 5 min: filtrar layers (excluir 09-PISO, ARQ_DEMOLI*, 0) → 2 min.
- **Decisões do usuário (15/10/2026):** profundidade pela NBR 5410 — elétrica (alimentação e iluminação) 0,70 m (1,00 m sob área de veículos V1); dados e CFTV 0,60 m; medida do terreno as built (IMP) ao TOPO do eletroduto. Bancos: cada eletroduto modelado separado, lado a lado, com o Ø do rótulo. Arquivo: `MODELAGEM-ELETRICA.rvt` copiado de `TEMPLATES\MODELO-BASE-ESCOLAS_limpo_2026-10-13.rvt`.
- **Georreferência do EL-001 (15/10):** os blocos ARQ do EL-001 estão 0,46 m deslocados em relação às outras 3 pranchas (o texto de carimbo "ALAGOINHAS" fica nas mesmas coordenadas locais em todas). Teste de proximidade a paredes do SIT (tubulações internas do EL-001 a < 0,30 m de parede: 88 pontos com a transformação pelos blocos ARQ do próprio EL-001 × 51 no sistema das outras pranchas; controle EL-002: 63 × 37) → **vale a transformação pelos blocos ARQ de cada DWG**. Não "uniformizar" pelo carimbo.
- **Ø dos eletrodutos (rótulos):** EL-001 = chamada no PDF (círculo sobre o eletroduto → linha → texto Ø), calibração PDF×modelo pelas caixas (13 pares, resíduo 0,000 m); CF-002 idem (22 caixas, 0,027 m); CF-001 = calibração do CF-002 + deslocamento de folha medido por textos de arquitetura (−2,9; −45,5 pt); EL-002 = textos Ø do próprio DWG (sem bancos). As linhas de chamada do DWG não saem no dump (LEADER/POLYLINE 2D). Propagação: no mesmo eletroduto e, através da caixa, pela ponta mais próxima (marcado "continuidade presumida"). Sem rótulo: Ø da nota do projeto (EL 3/4", CF 1").
- **Fase 2 + cotas (15/10):** 169 pedaços caixa a caixa (~2.940 m), 94 caixas. EL-001 68 pedaços/1.041 m/20 cx (Ø3/4"–6"); EL-002 42/866 m/26 cx (Ø3/4"–1.1/4"); CF-001 26/590 m/23 cx (Ø1.1/4"–1.1/2"); CF-002 33/444 m/25 cx (Ø1"–1.1/2"). Cotas: Douglas-Peucker 0,20/2 m sobre terreno IMP (6.297 amostras via ReferenceIntersector no DRN {3D} 438207 — 6.300 raios estouram o timeout do MCP mas terminam; esperar o arquivo). Caixa: topo = terreno; fundo = eletroduto mais fundo − DE/2 − 0,10. Scripts: `FERRAMENTAS\eletrica\` (ele_extract, pdf_calib, ele_labels, ele_rede, ele_cotas, plot_val). CSV: `RELATORIOS\ELE_fase2_trechos_2026-10-15.csv`; mapas `RELATORIOS\ELE_fase2_<TAG>_validacao_2026-10-15.png`.
- **Escopo (skill nova, 15/10):** só rede externa → cortar eletrodutos na face das edificações (pendente: confirmar com o usuário e definir o contorno dos blocos — o `floors.csv` do IMP inclui pisos externos, não serve).
- **Pendente fase 1 no Revit:** criar `MODELAGEM-ELETRICA.rvt` (cópia da base limpa), vincular os 4 DWG georreferenciados e provar coordenadas.
