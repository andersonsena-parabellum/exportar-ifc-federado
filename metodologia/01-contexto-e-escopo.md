# 01. Contexto e escopo

## Para que serve

O método atende contratos de **modelagem BIM e compatibilização das redes externas da implantação** de escolas (ou de qualquer conjunto de edificações num lote) já construídas ou em obra, com entrega em IFC e pranchas as built para aprovação de um órgão público. Foi construído e validado em outubro de 2026, em oito escolas de tempo integral (ETIB) na Bahia, com aprovação da CONDER.

- Papéis: **dono do projeto** (decide escopo, aprova exceções e o padrão das entregas), **sócio de modelagem** (modelos no Revit e aprovação do federado), **projetistas** de cada disciplina (decidem o que passa dos limites da equipe), **construtora** (fornece projeto, as built e RVT; recebe a entrega) e **órgão aprovador** (define a nomenclatura e aprova).
- Idioma de tudo: português do Brasil.

## Escolas e ordem de entrega

- **Uma escola depois da outra**, numa ordem combinada com o dono no início do contrato (salvo pedido direto dele numa escola).
- Cada escola tem uma **sigla** de 3 letras e uma **origem** própria: um ponto UTM redondo perto da obra, sem rotação e com cota 0, para que a cota interna seja igual à absoluta. Todos os IFC de uma escola usam a mesma origem. Sigla e origem ficam na tabela de escolas do `AGENTS.md` da pasta do projeto e no adaptador da escola.
- Sistema de coordenadas: UTM SIRGAS 2000 na zona da obra (na Bahia, EPSG:31984, zona 24S).

## Escopo

- **Só redes externas**, da face da parede dos prédios para fora (decisão de 21/10/2026, todas as escolas). O que fica dentro dos prédios não é modelado e não conta como conflito: descidas internas, ramais sob o prédio, redes × fundação interna. As redes são cortadas na face e a estrutura dos prédios vai só como referência.
- Exceção combinada caso a caso: instalações internas de um bloco podem ir no pacote só como modelagem, sem compatibilização (seguindo a regra de rede acima do piso fora da estrutura, capítulo 04).
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
