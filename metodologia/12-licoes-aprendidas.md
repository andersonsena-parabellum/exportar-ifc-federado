# 12. Lições aprendidas

Erros que já aconteceram e a regra que nasceu de cada um. A regra vigente está nos capítulos; aqui fica o porquê.

| Onde | O que aconteceu | Regra que ficou |
|---|---|---|
| Alagoinhas | Transformação por coordenada impressa errou 2,3 m | Georreferenciar por ICP dos blocos de arquitetura (cap. 03) |
| Alagoinhas | Incêndio do mesmo escritório 70 m deslocado; uma prancha elétrica 0,46 m | Cada DWG tem a sua transformação |
| Alagoinhas | Eletroduto encadeado através das caixas trocou diâmetros entre tubos vizinhos | Cortar nas caixas e rotular pedaço a pedaço |
| Alagoinhas | 49 pontas de eletroduto fora da face da caixa, vistas pelo usuário | Eletroduto termina na face, conferido no modelo |
| Alagoinhas | Terreno opaco escondeu 428 eletrodutos na vista | Vistas de validação com terreno oculto e pisos transparentes |
| Alagoinhas | Perfil 3D ligava as quebras em linha reta e cortava curvas (24,8 m) | Incluir os vértices da planta no perfil |
| Jandaíra | "PROF. 0,90 m" repetido 20 vezes num eletroduto | Uma nota de profundidade por trecho (cap. 07) |
| Jandaíra | Rede tracejada saiu contínua (entmake sem grupo 6) | Gravar ByLayer e tipo de linha explícitos |
| Jandaíra | Incêndio "picotado" na casa de bombas (barrilete foi para o estudo de cota) | Barrilete e casa de bombas na cota do modelo; verificar continuidade (cap. 04) |
| Jandaíra | 3 de 6 colisões críticas eram da caixa envolvente da sapata | Clash pela forma real da estrutura (cap. 05) |
| Jandaíra | Material "rígido" vindo do tipo da família do Revit | Material da legenda e do memorial |
| Jandaíra | Federado com marcadores de "atenção" e Pset com nome de pessoa | Nada de processo interno no IFC entregue |
| Jandaíra (BP4) | Tubo atravessando pilar e viga numa entrega só de modelagem | Rede acima do piso fora da estrutura (D10) |
| Revit 2025 | Eletroduto como IfcCableCarrierSegment virou "Bandeja de cabos" | Perfil de classes 'revit' (cap. 04) |
| Revit 2025 | IFC aberto com a vista 3D vazia | Fase 3 na vista 3D, ocultar pontos de base, ZF |
| Catu | IFC das BP4/BA2 com propriedades de trabalho | `limpar_entrega.py` depois do APROVADO |
| Pojuca | DWG que não reabria depois de gravado (ErrorStatus 53) | AUDIT antes e depois |
| Pojuca | PDF saiu em Carta | `-PLOT` detalhado em ISO full bleed A0 |
| Olindina | Rede existente rosa e textos de 0,40 m, retrabalho depois da entrega | Padrão gráfico e prévia antes/depois (cap. 07) |
| PDCA (22/10) | 70 a 87 % do prazo foi espera | Entrada da escola e aplicar e avisar (cap. 02 e 05) |
| Sátiro | Script regenerou arquivo e ignorou em silêncio os que faltavam | Copiar a pasta de trabalho inteira para a nuvem |
| Jandaíra (federado) | RVT da implantação 0,565 m abaixo do as built | Conferir a cota do RVT (`p0_cota_rvt.py`) |
| Alagoinhas (federado) | Revit da implantação 22 cm deslocado das redes | Tudo segue o sistema das redes |
| Nuvem | Render do PDF perdeu tracejado grosso e negrito | PDF híbrido quando só o carimbo muda |

O histórico completo, rodada a rodada, está no `licoes-modelagem.md` da pasta do projeto.
