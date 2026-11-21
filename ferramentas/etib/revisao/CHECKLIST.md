# Checklist de revisão de qualidade — redes externas das escolas (contrato 24-049)

Usado pelo analista de qualidade **depois** que a thread da escola diz que a entrega está pronta e **antes** de qualquer envio. A pasta de envio só é liberada com veredito APROVADO (ou com item suspenso combinado com o coordenador).

- Ferramenta: `FERRAMENTAS\revisao\revisar.py <escola>` (lê; não edita nada da escola). Saída em `FERRAMENTAS\revisao\relatorios\<ESCOLA>\`.
- Coluna **Como**: AUTO = o script confere; VISUAL = olhar os recortes origem | revisada (`--recortes`); MANUAL = conferir à mão.
- Nível: **pendência** bloqueia o envio; **observação** não bloqueia, mas vai para a thread; **suspenso** = item combinado para depois.
- Fontes das regras: `licoes-modelagem.md` A2 e A2.1, `FERRAMENTAS\preclash\LEIA-ME.md` (parâmetros de compatibilização, padrão das pranchas, profundidade máxima), memórias `preclash-pre-compatibilizacao`, `carimbo-qg-asbuilt`, `feedback-preferir-profundidade`, `feedback-formato-relatorio-compat`.

## 0. Entrada da escola (antes de modelar; conferido pela thread dona, registrado no INVENTARIO.md)

| Item | Regra | Como |
|---|---|---|
| 01 | Todos os DWG da escola abrem no accoreconsole com AUDIT; os que não abrem estão listados para o Anderson salvar no AutoCAD com janela. | AUTO |
| 02 | CTB e fontes pedidos pelas pranchas listados; sem CTB do projetista, plota com o padrão e a conferência olha só a geometria. | AUTO |
| 03 | RVT necessários (terreno do IMP, estrutura) já convertidos em IFC, numa sessão só do Revit. | MANUAL |
| 04 | O que falta da construtora está num pedido único, e as decisões antigas da escola estão na página de entrada. | MANUAL |

## A. Entregável e pasta de envio

| Item | Regra | Como |
|---|---|---|
| A1 | Entrega = IFC por disciplina (HIDRO, ELE, PCIP) + TERRENO + estrutura de referência + FEDERADO, pranchas PDF A0 + DWG das folhas modificadas, LEIA-ME e imagens das pendências. | AUTO |
| A2 | Só a revisão vigente de cada folha; nada de `_REVISADO`, `_carimbo-antigo`, `.bak`, `.dxf`, `.log`, cópias. | AUTO |
| A3 | Os arquivos do envio são os mesmos que foram revisados (hash igual; IFC renomeados casam pelo hash) e o CDE (`PRANCHAS\<ESCOLA>` e `ETIB_PRANCHAS_CDE` no Drive) tem os mesmos PDFs. Envio e CDE sobem no mesmo passo, logo após o APROVADO; a escola só conta como entregue com este item conferido depois da subida. | AUTO |
| A4 | Todo PDF tem o DWG de mesmo nome e vice-versa; os 3 `CARIMBO_QG_logo_*.png` ficam ao lado dos DWG. | AUTO |
| A5 | Nome no padrão da lista mestra `24-049-<MUN>-CTO-ETIB-<SETOR>-PE-<DIS>-<NNN>-<CONT>-R<NN>`. | AUTO |
| A6 | LEIA-ME sem processo interno (preclash, pré-compatibilização, thread, script, nuvem, visualizador, nomes de pessoas da equipe) e sem disciplina fora do escopo (ETE, GLP, CFTV, solar); o que ele afirma bate com as pranchas (ex.: "cotas das caixas seguem o projeto"). | AUTO + MANUAL |
| A7 | As pendências declaradas batem com o clash da revisão (nenhuma colisão crítica fora da lista). | AUTO (D6) |
| A8 | Drive da construtora intocado; o envio fica só em `G:\Meu Drive\ETIB_ENVIOS\`. | MANUAL |
| A9 | Índice (`PRANCHAS_INDICE.md`) e aba Pranchas do visualizador com as folhas novas da escola. | MANUAL |

## B. IFC: informação (o "I" do BIM)

Perfil de classes **'revit'** (aprovado pelo Anderson em 20/10/2026, 19h28). O Revit 2025 escolhe a categoria só pela classe (PredefinedType e tipo não mudam nada): `IfcCableCarrierSegment` vira bandeja de cabos, `IfcCableCarrierFitting` vira conexão de bandeja, `IfcDistributionChamberElement`, `IfcCableFitting` e `IfcBuildingElementProxy` viram modelo genérico. A classe da norma IFC4 fica gravada no Pset (`classe_ifc_norma`): **não reprovar por usar a classe do perfil em vez da classe da norma**. Mapa completo do teste no Revit: docstring de `FERRAMENTAS\preclash\preclash\export_ifc.py`.

| Item | Regra | Como |
|---|---|---|
| B1 | Georreferenciado: `IfcMapConversion` + `IfcProjectedCRS` (EPSG:31984), origem = a registrada no `AGENTS.md` da escola. | AUTO |
| B2 | Classes do perfil 'revit': tubo `IfcPipeSegment` + `IfcPipeFitting` (Tubulação, Conexões de tubo); **eletroduto `IfcCableSegment`** (Conduítes), curva/derivação de eletroduto também `IfcCableSegment` com ObjectType; **caixa elétrica `IfcJunctionBox`** (Dispositivos elétricos); **caixa hidráulica (ESG/DRE) `IfcWasteTerminal` ou `IfcInterceptor`** (Equipamento hidráulico); caixa de registro de AF/hidrante `IfcValve`; **válvulas `IfcValve`**; hidrômetro `IfcFlowMeter`; **tanque/reservatório `IfcTank`**; quadro `IfcElectricDistributionBoard`; poste `IfcLightFixture`; abrigo `IfcFireSuppressionTerminal`; bomba `IfcPump`. Proibido no perfil: `IfcCableCarrierSegment/Fitting`, `IfcDistributionChamberElement`, `IfcCableFitting`, `IfcBuildingElementProxy` (fora os marcadores de pendência do federado). `IfcAlarm` vira modelo genérico: observação. Classe da norma no Pset `classe_ifc_norma`: observação se faltar. | AUTO |
| B3 | `PredefinedType` preenchido; `USERDEFINED` vale com `ObjectType` (ex.: ELETRODUTO, CAIXA DE INSPEÇÃO). NOTDEFINED = observação. | AUTO |
| B4 | Material preenchido em todo tubo/eletroduto (Pset `material` ou `IfcRelAssociatesMaterial`); conexão/caixa sem material = observação. **O material vem da legenda da planta e do memorial descritivo, não do tipo de família do Revit** (Anderson, 21/10/2026): eletroduto enterrado de elétrica e alarme é **flexível** (PVC corrugado/PEAD), então "rígido" ou "conduíte" genérico = pendência; nome com cara de tipo do Revit ("paramétrico", "padrão", "DN") = observação. O relatório lista os materiais por disciplina para o analista bater com a legenda. | AUTO + MANUAL |
| B5 | Diâmetro preenchido em todo tubo, eletroduto e conexão (`DN_mm`/`DE_mm` no Pset ou NominalDiameter). | AUTO |
| B6 | Cada elemento num `IfcDistributionSystem` com o tipo da disciplina (DOMESTICCOLDWATER, SEWAGE, STORMWATER, FIREPROTECTION, ELECTRICAL…); `IfcSystem` genérico = pendência. | AUTO |
| B7 | Cada peça com o código do projeto (trecho `AF-07.3`, caixa `CX-I12`, circuito na elétrica). | AUTO |
| B8 | Federado = soma das disciplinas + terreno + estrutura; só os marcadores das pendências declaradas (**nenhum de "atenção"**); **sem o Pset "PRECLASH"** e **sem nome de pessoa** (ex.: "modelo do Daniel"). | AUTO |
| B9 | IFC por disciplina sem processo interno: nome de ferramenta ou pessoa = pendência; jargão de trabalho ("estudo", "ajuste", "obstáculo", "premissa") = observação. A propriedade `recobrimento_estudo` é pedida (B10) e não conta. **IFC da pasta de envio sem as propriedades de trabalho `fora_do_comercial`, `angulo_real` e `deflexao_junta_graus`** (27/10/2026: tinham saído nos IFC do BP4 e do BA2): depois do APROVADO, rodar `revisao/limpar_entrega.py <03_IFC do envio> <csv interno>`, que grava o registro interno na pasta `revisao` da escola; o `envio_conf.py` reprova o envio com essas propriedades e aceita no A3 o IFC que só difere do conferido por elas. | AUTO |
| B10 | `recobrimento_estudo` preenchido em todo trecho pressurizado (AF, HID, ELE, SDAI). | AUTO |
| B11 | Caixas ocas (as de 0,30 m ou mais de altura e de lado): fundo 0,10 m, parede 0,10 m (retangular; menor nas caixas pequenas) ou anel 0,08 m (circular), tampa 0,05 m; tampa em **grelha de FoFo** nas caixas de areia (CA) e bocas de lobo (BL); Pset com `dimensao_interna` e `profundidade_util`. | AUTO |
| B12 | Furo de passagem dos tubos nas caixas: a ferramenta ainda não faz, então fica como **observação**, sem reprovar. | AUTO (aviso) |
| B13 | Abrir o federado no **Revit 2025** (Abrir IFC; vista 3D na Fase 3) e conferir as categorias (Tubulação, Conduítes, Dispositivos elétricos, Equipamento hidráulico, Acessórios do tubo) e as propriedades; abrir também num **visualizador neutro** (ex.: o That Open de `FERRAMENTAS\preclash\thatopen\`, BIMcollab Zoom) e conferir classes, Psets e sistemas. | MANUAL |

## C. IFC: continuidade e conexões (item de 20/10/2026, rede "picotada" no incêndio)

| Item | Regra | Como |
|---|---|---|
| C1 | Rede contínua de caixa a caixa: toda ponta termina em outro tubo, conexão, caixa/equipamento ou na edificação (sobe para o predial). Ponta sem destino no modelo = observação para conferir na prancha. | AUTO |
| C2 | Peças encostadas: pontas a mais de 2 cm uma da outra = folga; tubo que chega no meio de outro sem junção = erro. | AUTO |
| C3 | Nenhum pedaço de tubo menor que a conexão (comprimento < 3 × DE ou < 10 cm), salvo entre duas caixas. | AUTO |
| C4 | Sem peças sobrepostas: tubos colineares sobrepostos, conexões duplicadas no mesmo ponto. | AUTO |
| C5 | Conexão no vértice dos tubos (≤ 1 cm) e com as pernas alinhadas aos tubos (≤ 3°); nenhuma conexão solta. | AUTO |
| C6 | Conexão comercial em toda mudança de direção fora de caixa, horizontal ou vertical, inclusive DRE/ESG. **Peças comerciais: 45° e 90°, e 135° = 90° + 45°** (Anderson, 21/10/2026; 11,25° e 22,5° não contam); **tês e junções são comerciais** e não entram na conta do ângulo. O ângulo real da rede é o da peça (± 3°, a tolerância do preclash). Tubo rígido: deflexão de até 5° fica na junta. **Material flexível (eletroduto de elétrica e alarme enterrados, hidrante em PEAD): curva de até 30° no próprio tubo, sem peça**; peça marcada `curvatura_no_tubo` completa no tubo a diferença de até 30°. Peça em tubo rígido marcada `fora_do_comercial = sim` fica como observação enquanto a decisão do Anderson estiver pendente. Nó com 3+ tubos fora de caixa = junção (tê). Niple do barrilete (acima do piso, entre válvulas) não conta no C3. | AUTO |

## D. IFC: regras de compatibilização

| Item | Regra | Como |
|---|---|---|
| D1 | Profundidade máxima, do terreno ao topo do tubo, todas as disciplinas: a da escola em `preclash\parametros.py` (Jandaíra 1,50 m; demais 2,00 m desde 20/10/2026). Passar só com aprovação escrita do Anderson registrada em `entregas.py`; gravidade acima do máximo pela cota do projeto vira observação. | AUTO |
| D2 | Rede enterrada: topo abaixo do terreno do IFC (acima = pendência); recobrimento mínimo de referência 0,30 m (vale a nota de cada projeto; elétrica e área de veículos 0,60 m). | AUTO + MANUAL |
| D3 | Sem degrau em "Z" nas pressurizadas: subida/descida > 45° só dentro de caixa ou acompanhando o terreno; a cota da elétrica muda só na caixa (recobrimento variando > 0,25 m num trecho = conferir). | AUTO |
| D4 | Elétrica (ELE/SDAI) sempre acima da água (AF/HID) em todo cruzamento. | AUTO |
| D5 | Caixas nem enterradas nem sobrando: tampa no terreno (± 5 cm); caixa sem tubo = observação; fundo da caixa abaixo do tubo mais fundo que chega nela. | AUTO |
| D6 | Clash independente da ferramenta: rede × rede, rede × caixa e rede × estrutura **pela malha real** da estrutura as built (não a caixa envolvente); toda colisão crítica que sobra está declarada. | AUTO |
| D7 | Gravidade (ESG, pluvial, DRE) com as cotas do projeto: CT/CF/CS/CE das caixas não mudam (só deslocamento em planta até 0,60 m); mudança de cota de caixa = pendência, salvo aprovação declarada no envio. Exceções do "aplicar e avisar" (Anderson, 22/10), declaradas em `entregas.py`: geratriz de chegada ajustada até 0,20 m mantendo a declividade mínima, e CT/CF incoerente com a profundidade corrigida na prancha. | AUTO (E7) + MANUAL |
| D8 | Reservatório inferior modelado (`IfcTank`). | AUTO |
| D9 | Nada fora do escopo do contrato (ETE, GLP, CFTV/dados, solar, contenção). | AUTO |
| D10 | **Rede acima do piso fora da estrutura, inclusive em entrega só de modelagem** (Anderson, 27/10/2026, BP4 da Jandaíra: tubo atravessando pilar e viga e elétrica ora acima ora abaixo da laje). Nunca dentro de pilar: coluna/descida encosta na face (folga 2 cm) e trecho horizontal desvia de lado o mínimo, com a fileira reta. Rede de teto não corta viga: elétrica e SDAI ficam sob a viga mais baixa; o que ainda passar por viga (água, esgoto, frigorígena, hidrante) vai numa lista de passagens no envio. Pluvial de cobertura sobre a laje em todo o percurso (geratriz ≥ 0,05 m acima do ponto mais alto da laje embaixo, inclusive na emenda de blocos). Passagem vertical pela laje é normal. **Não se dispensa como "compatibilização fora do escopo"**: só rede enterrada × baldrame/sapata segue a regra de compatibilização (D6). Conferir pelo clash da malha real (D6 rede × estrutura com z acima do piso). | AUTO (D6) + VISUAL |

## E. Pranchas (PDF e DWG)

| Item | Regra | Como |
|---|---|---|
| E1 | Folha A0 (1189 × 841 mm), um PDF por folha. | AUTO |
| E2 | Carimbo QG as built no PDF (campos CONTRATADA/CONTRATANTE/DISCIPL_SETOR-FOLHA_REV/RESP. PROJETO/… e os 3 logos) e no DWG (DWG de mesmo nome, gravado antes do PDF, logos ao lado). | AUTO |
| E3 | Revisão coerente: nome do arquivo = código no carimbo = código curto = campo ARQUIVO = linha mais nova do quadro de revisões; escala igual à da origem. Numeração repetida/pulada que já vinha do original = observação. | AUTO |
| E4 | Uma nota "PROF. x,xx m" por trecho: 3 ou mais notas iguais a menos de 15 m (na escala da folha) = pendência; 2 = observação. | AUTO |
| E5 | Valor das notas ≤ profundidade máxima da escola (ou exceção aprovada). | AUTO |
| E6 | Nota legível: não escrita por cima de outro texto (caixa de cada caractere) = pendência; vale para a folha inteira, inclusive textos do projetista que se sobrepõem: sobreposição que não estava na revisão de origem (mesmo par de textos ou mesmo lugar, 5 mm) = pendência; a que já vinha do projetista = observação, uma linha por folha. Só encostar na ponta de um texto miúdo da base (letra com até metade do tamanho da nota e até 25% das letras cobertas) = observação. | AUTO + VISUAL |
| E7 | Etiquetas de material/diâmetro/trecho/circuito e cotas do projeto preservadas em relação à revisão de origem; cota de caixa alterada = pendência (ver D7). | AUTO + VISUAL |
| E8 | Nada de nuvem, traçado "substituído", rascunho ou nota de processo (pré-compatibilização, preclash, conflito, mergulho, ficha CP-xx, revisão interna) — nem em layer do PDF. Só texto novo (que não existia na origem) conta. | AUTO + VISUAL |
| E9 | Traçado redesenhado na mesma layer, cor e **tipo de linha** da rede (tracejado continua tracejado); caixa deslocada com símbolo e texto juntos; tags acompanham o trecho. | AUTO (tipo de linha) + VISUAL |
| E10 | Prancha × modelo: deslocamentos e notas da prancha batem com o IFC entregue (amostra nos recortes). | VISUAL |
| E11 | Padrão gráfico: rede existente ou de cadastro numa cor bem visível (nada de cinza, preto ou cor clara: Anderson, 22/10) que não repita a de outro item da legenda, ByLayer, e presente na legenda; toda cor ou elemento novo nosso na folha tem item na legenda; texto na altura padrão da folha; anotação nossa nunca maior que o texto do projetista. O `pdf_conf.py` (`conferir_grafico`) acha o layer de cadastro (EXISTENTE/CADASTRO) e confere: cor visível, diferente da rede nova e sem repetir item da legenda (`legenda()`: amostra de linha + texto na coluna da direita); item de rede existente na legenda com a mesma cor; cor nova em relação à origem sem item na legenda; altura mais comum dos textos do cadastro e dos textos novos ≤ etiquetas de rede do projetista + 15 %. Miniaturas antes e depois de cada folha alterada (`preclash\executivo\rever.py --miniaturas`) vão ao Anderson junto com o "pronto". | AUTO + VISUAL |

## F. Página de pendências

| Item | Regra | Como |
|---|---|---|
| F1 | Abre no celular: todas as imagens embutidas na página (base64), nenhum link externo de imagem. | AUTO (`FERRAMENTAS\pendencias\pagina.py` grava `CONFERENCIA_F.md`) |
| F2 | Dois blocos: "Aplicado (pode reverter)" com o que entrou pelo aplicar e avisar, e "Precisa de decisão" com o resto; ficha aplicada diz como reverter. | AUTO (`CONFERENCIA_F.md`) |
| F3 | Cada ficha: recorte da prancha do projetista centrado e marcado, com os códigos citados escritos (ex.: tubo DRN-164, caixa CX03); vistas 3D e em planta; campo de decisão, de texto e de imagem. | AUTO (`CONFERENCIA_F.md`) + VISUAL |

## Formato do relatório de revisão

`REVISAO_<SIGLA>_<data>.md` + `_achados.csv` (uma linha por achado, com E/N):
1. Cabeçalho: entrega revisada, profundidade máxima, exceções aprovadas, pendências declaradas, itens suspensos.
2. **Veredito**: APROVADO / APROVADO COM ITEM SUSPENSO / REPROVADO.
3. Pendências agrupadas: item, arquivo/prancha, quantidade, problema, até 4 locais (trecho + caixa mais próxima + coordenada, ou posição na folha em mm), regra.
4. Observações e itens suspensos.
5. Resultado por item, com a evidência (contagens) de cada um.

Ao coordenador vai só o veredito e a lista objetiva (prancha, local, regra); a thread da escola corrige e pede nova revisão.
