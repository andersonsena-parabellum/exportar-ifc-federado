# 01. Contexto e escopo

## Contrato

- Contrato 24-049 da Construtora QG, com aprovação da CONDER. A equipe faz a modelagem BIM e a compatibilização das redes externas da implantação de escolas de tempo integral (ETIB) já construídas ou em obra.
- Papéis: **dono do projeto** (decide escopo, aprova exceções e o padrão das entregas), **sócio de modelagem** (modelos no Revit e aprovação do federado), **projetistas** de cada disciplina (decidem o que passa dos limites da equipe) e **construtora** (fornece projeto, as built e RVT; recebe a entrega).
- Idioma de tudo: português do Brasil.

## Escolas e ordem de entrega

Oito escolas, uma depois da outra, nesta ordem (salvo pedido direto do dono na escola):

| Ordem | Escola | Sigla | Origem dos modelos (E / N / cota, EPSG:31984) |
|---|---|---|---|
| 1 | Jandaíra | JAN | 631578,10 / 8721003,57 / 0 |
| 2 | Alagoinhas (implantação + bloco BA2) | ALI / ALH | 561500 / 8658000 / 0 |
| 3 | Sátiro Dias | SAT | 546000 / 8716200 / 0 |
| 4 | Olindina | ONN | 573950 / 8743250 / 0 |
| 5 | Aporá Itamira | ITA | 584400 / 8704300 / 0 |
| 6 | Aporá Prof. Áurea | AUR | 600000 / 8711300 / 0 |
| 7 | Catu | CAT | 567700 / 8634650 / 0 |
| 8 | Pojuca | PJC | 572450 / 8626500 / 0 |

A origem é um ponto UTM redondo perto da obra, sem rotação e com cota 0: assim a cota interna é igual à absoluta. Todos os IFC de uma escola usam a mesma origem.

## Escopo

- **Só redes externas**, da face da parede dos prédios para fora (decisão de 21/10/2026, todas as escolas). O que fica dentro dos prédios não é modelado e não conta como conflito: descidas internas, ramais sob o prédio, redes × fundação interna. As redes são cortadas na face e a estrutura dos prédios vai só como referência.
- Exceção: o IFC das instalações internas do bloco BA2 de Alagoinhas vai no pacote só como modelagem, sem compatibilização.
- **Disciplinas:** hidráulica (água fria AF/AGF, esgoto ESG, drenagem DRE), elétrica (ELE) e incêndio (PCI: hidrante e SDAI), mais o campo society quando houver.
- **Fora do escopo:** ETE, GLP, CFTV/dados, solar, contenção e paisagismo. Disciplina fora do escopo não é citada em nenhum documento entregue.

## Entregável por escola

- IFC por disciplina, compatibilizado.
- Federado: hoje o **federado único** da escola inteira (capítulo 06).
- Pranchas modificadas em PDF e DWG, no padrão as built (capítulo 07).
- Sem RVT: a CONDER e a construtora aceitam IFC.

## Fontes de dados de uma escola

| Fonte | Para quê | Regra |
|---|---|---|
| DWG e PDF do projetista (por disciplina) | traçado, diâmetros, cotas (CT, CF, CE, CS), legendas, memorial | cópia fiel em `PROJETO_ORIGINAL`, nunca editada |
| As built da construtora | rede executada | vale sobre o projeto (capítulo 05) |
| RVT da implantação (IMP) | terreno e posição dos módulos | convertido em IFC no notebook |
| RVT de estrutura e arquitetura | clash com a forma real e federado | convertido em IFC no notebook |
| Planta de situação (SIT), topografia (TOP, TER), pavimentação (PAV) | terreno, divisa, platôs, pisos | cópia em DXF |

As pastas da construtora no Drive são **somente leitura**: nunca mover, apagar, renomear ou editar.
