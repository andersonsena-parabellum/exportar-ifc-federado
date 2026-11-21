# Metodologia ETIB: modelagem e compatibilização em IFC

Este é o método de trabalho da equipe para modelar, compatibilizar e entregar em IFC as redes externas das escolas ETIB (com aprovação da CONDER). Ele junta num só lugar o que antes estava espalhado entre as instruções do projeto, o `AGENTS.md` do notebook, as lições de modelagem, as skills locais, o checklist de qualidade e os LEIA-ME das ferramentas.

O método foi construído em outubro de 2026, em oito escolas, e cada regra tem a data em que foi decidida. Quando uma regra muda, este texto muda junto e a regra antiga é apagada (o histórico fica no git).

## Ideia central

1. **Tudo em IFC, sem Revit no meio.** As redes são montadas em Python a partir dos DWG e PDF do projetista e do as built, já georreferenciadas em UTM (SIRGAS 2000), com cota absoluta e diâmetro externo real. O Revit entra só para ler os RVT da construtora (terreno da implantação, estrutura, arquitetura).
2. **Compatibilizar antes de entregar, mexendo o mínimo.** Primeiro profundidade; planta só quando não há outro jeito. Dentro de limites combinados a solução é aplicada e avisada; fora deles, vira decisão.
3. **Informação é parte do BIM.** Cada peça sai com classe IFC que o Revit lê certo, sistema, material da legenda, diâmetro, código do projeto e Pset próprio, sem nenhum dado de processo interno.
4. **A prancha vai para o campo.** As folhas são as built, lidas pelo mestre de obras: sem nuvem, sem nota de processo, no padrão gráfico do projetista.
5. **Nada sai sem revisão.** Um checklist automático (com conferência visual) dá APROVADO ou REPROVADO; só o APROVADO sobe para o envio e o CDE.
6. **Nuvem primeiro.** Todo o processamento roda na nuvem; o notebook fica só com o Revit e a cópia para o Drive.

## Fluxo de uma escola

```
Entrada  ->  Georreferenciamento e extração  ->  Modelagem IFC  ->  Compatibilização
   |                                                                     |
   v                                                                     v
INVENTARIO.md                                  Página de pendências (aplicado / precisa de decisão)
                                                                         |
Pranchas as built (DWG + PDF)  <-  decisões  <---------------------------+
   |
   v
Revisão de qualidade (CHECKLIST)  ->  APROVADO  ->  Envio + CDE no mesmo passo  ->  Federado único
```

## Capítulos

| # | Capítulo | O que tem |
|---|---|---|
| 01 | [Contexto e escopo](01-contexto-e-escopo.md) | contrato, escolas, disciplinas, o que entra e o que fica fora, entregável |
| 02 | [Entrada da escola](02-entrada-da-escola.md) | os 5 passos antes de modelar e o INVENTARIO.md |
| 03 | [Georreferenciamento e extração da rede](03-georreferenciamento-e-extracao.md) | CAD local para UTM, leitura do DWG e do PDF, grafo da rede, terreno |
| 04 | [Modelagem IFC](04-modelagem-ifc.md) | motor sem Revit, cotas, classes, Psets, caixas, conexões, material, continuidade |
| 05 | [Compatibilização](05-compatibilizacao.md) | regras, estudo de cota, clash pela forma real, aplicar e avisar, pendências |
| 06 | [Federado único](06-federado-unico.md) | um IFC4 da escola inteira (skill `federado-unico-etib`) |
| 07 | [Pranchas e carimbo AS BUILT](07-pranchas-e-carimbo-asbuilt.md) | revisão do DWG, padrão gráfico, carimbo, PDF |
| 08 | [Revisão de qualidade](08-revisao-de-qualidade.md) | papel do analista, como rodar, veredito ([checklist completo](referencias/CHECKLIST.md)) |
| 09 | [Envio e CDE](09-envio-e-cde.md) | pasta de envio, limpeza do IFC, CDE, índice, visualizador |
| 10 | [Forma de trabalho e comunicação](10-forma-de-trabalho-e-comunicacao.md) | threads, decisões, Linear, página de pendências, regras novas |
| 11 | [Infraestrutura: nuvem e notebook](11-infraestrutura-nuvem-e-notebook.md) | o que roda onde, versões fixas, pastas, armadilhas do AutoCAD e do Revit |
| 12 | [Lições aprendidas](12-licoes-aprendidas.md) | erros que já aconteceram e como não repetir |
| 14 | [Começar uma escola nova](14-escola-nova.md) | o que pedir, a ordem e como adaptar a outro contrato |
| — | [Glossário](glossario.md) | siglas e termos |

## Skills deste repositório

As skills do Claude Code que executam o método ficam na raiz do repositório:

| Skill | Pasta | Quando usar |
|---|---|---|
| `federado-unico-etib` | [`../federado-unico-etib/`](../federado-unico-etib/SKILL.md) | montar o IFC federado único da escola |
| `revisao-qualidade-etib` | [`../revisao-qualidade-etib/`](../revisao-qualidade-etib/SKILL.md) | revisar uma entrega antes do envio |
| `modelagem-bim-disciplinas` | [`../modelagem-bim-disciplinas/`](../modelagem-bim-disciplinas/SKILL.md) | método antigo, no Revit via MCP (usado no piloto) |
| `modelagem-ifc-sem-revit` | ainda não copiada | método atual de modelagem; ver capítulos 03 a 05 |

O código das ferramentas (motor `preclash`, revisão, pranchas, CDE, página de pendências) fica na pasta `FERRAMENTAS` do projeto e na cópia da nuvem; os capítulos dizem qual script faz cada etapa.

## Manutenção

- Este repositório é a fonte do método. As regras do dia a dia continuam também nas instruções do projeto, no `GERAL/INSTRUCOES_PROJETO.md` e no `AGENTS.md` do notebook; quando uma regra muda lá, muda aqui no mesmo dia.
- Sem dados pessoais, senhas, links privados do Drive ou de páginas internas. Pessoas aparecem pelo papel (dono do projeto, sócio de modelagem, projetista, construtora).
