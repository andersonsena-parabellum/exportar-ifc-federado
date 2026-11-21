# 04. Modelagem IFC

## O motor: `preclash`

`FERRAMENTAS/preclash` monta as redes em 3D já georreferenciadas (UTM SIRGAS 2000, cota absoluta, diâmetro externo real), roda o clash entre disciplinas, testa soluções e exporta IFC4 e um visualizador 3D em HTML. Uma escola = um **adaptador** (`preclash/escolas/<escola>.py`) que diz onde estão os dados e quais regras valem.

```
bash _nuvem/etib-python rodar.py <escola>        (na nuvem)
..\.venv\Scripts\python.exe -X utf8 rodar.py <escola>   (no notebook)
```

| Etapa | Módulo | O que faz |
|---|---|---|
| Leitura | `leitura.py`, `leitura_ifc.py` | CSV das fases 2 e 3, ou IFC do Revit/da própria ferramenta |
| Terreno | `terreno.py` | TIN e ajuste às cotas da base |
| Estudo de cota | `estudo.py` | cota de cada rede pressurizada com menos colisões (capítulo 05) |
| Clash | `clash.py` | tubo = cápsula (eixo + raio externo), caixa = prisma ou malha real |
| Soluções | `solver.py`, `desvio.py` | mergulho local, depois desvio em planta e caixa deslocada |
| Conexões | `conexoes.py`, `costura.py` | peças comerciais e continuidade |
| Verificação | `verificar.py` | ponta solta, degrau, pedaço curto, rede fora do lugar |
| Exportação | `export_ifc.py` | IFC por disciplina, federado, visualizador |

Saída por rodada: LEIA-ME, visualizador HTML, IFC de projeto e de solução por cenário, CSV de conflitos antes e depois, soluções, pendentes e verificação. Cenários servem para dúvida em aberto que muda o clash (ex.: galeria "rede futura" com e sem).

Para uma escola nova: gravar o terreno `.npz`, copiar um adaptador pronto (ex.: `satiro.py`) trocando sigla, origem, EPSG, retângulo da obra e CSV, rodar e conferir no HTML.

## Georreferência

Todo IFC tem `IfcMapConversion` + `IfcProjectedCRS` (EPSG:31984), com a origem da escola (capítulo 01). Unidades SI e ângulo em radiano.

## Classes IFC: perfil "revit"

Decisão de 20/10/2026 ("um dos princípios do BIM é a informação"): o Revit 2025 escolhe a categoria **só pela classe IFC** (PredefinedType e tipo não mudam nada). Num teste com 40 classes, o eletroduto pela norma (`IfcCableCarrierSegment`) virava "Bandeja de cabos" e as caixas (`IfcDistributionChamberElement`) "Modelo genérico". Por isso o padrão é o perfil `'revit'`, e a classe da norma vai num Pset (`classe_ifc_norma`).

| Elemento | Classe | Categoria no Revit |
|---|---|---|
| Tubo AF, ESG, DRE, hidrante | `IfcPipeSegment` | Tubulação |
| Conexão de tubo | `IfcPipeFitting` | Conexões de tubo |
| Eletroduto (ELE, SDAI) e suas curvas | `IfcCableSegment` USERDEFINED "ELETRODUTO" / "CURVA DE ELETRODUTO" | Conduítes |
| Caixa de passagem elétrica | `IfcJunctionBox` | Dispositivos elétricos |
| PV, CI de esgoto e drenagem | `IfcWasteTerminal` USERDEFINED "POÇO DE VISITA" / "CAIXA DE INSPEÇÃO" | Equipamento hidráulico |
| Caixa de areia, boca de lobo, ralo | `IfcWasteTerminal` GULLYSUMP | Equipamento hidráulico |
| Caixa de gordura | `IfcInterceptor` | Equipamento hidráulico |
| Caixa de registro AF/hidrante, válvulas | `IfcValve` | Acessórios do tubo |
| Hidrômetro | `IfcFlowMeter` | |
| Reservatório | `IfcTank` | |
| Bomba | `IfcPump` | |
| Quadro | `IfcElectricDistributionBoard` | |
| Poste, luminária | `IfcLightFixture` | |
| Abrigo de hidrante | `IfcFireSuppressionTerminal` | Sprinklers (PCI) |
| Estrutura | `IfcColumn`, `IfcBeam`, `IfcFooting` | |

Proibidas no perfil: `IfcCableCarrierSegment/Fitting`, `IfcDistributionChamberElement`, `IfcCableFitting` e `IfcBuildingElementProxy` (fora os marcadores de pendência do federado).

## Informação de cada peça

- **Sistema:** cada elemento num `IfcDistributionSystem` com o tipo da disciplina (DOMESTICCOLDWATER, SEWAGE, STORMWATER, FIREPROTECTION, ELECTRICAL, SECURITY). `IfcSystem` genérico não serve.
- **PredefinedType** sempre preenchido; USERDEFINED com `ObjectType`.
- **Código do projeto** em cada peça (trecho `AF-07.3`, caixa `CX-I12`, circuito).
- **Diâmetro** em `Pset_PipeSegmentTypeCommon` / `Pset_CableCarrierSegmentTypeConduitSegment` e no Pset próprio.
- **Material** por `IfcRelAssociatesMaterial` e no Pset.
- **Pset `Dados_ETIB`:** material, diâmetro, sistema, `recobrimento_estudo` (obrigatório em toda pressurizada), `curvatura_no_tubo`, classe da norma, e nas caixas `dimensao_interna` e `profundidade_util`.
- **Nada de processo interno no IFC entregue:** sem Pset "PRECLASH", sem nome de pessoa ou ferramenta, sem jargão ("estudo", "ajuste", "obstáculo", "premissa") e sem as propriedades de trabalho `fora_do_comercial`, `angulo_real` e `deflexao_junta_graus`. Elas existem durante o trabalho e saem com `revisao/limpar_entrega.py` depois do APROVADO (capítulo 09).

## Material: da legenda, não da família

Decisão de 21/10/2026: o material vem da **legenda da planta e do memorial descritivo**, nunca do tipo padrão da família do Revit (na Jandaíra o modelo dizia "Eletroduto Rígido PVC Roscável" e a prancha pedia PVC corrugado flexível).

- Eletroduto enterrado de elétrica e de alarme = **flexível** (PEAD corrugado). Hidrante em PEAD.
- Material flexível curva até ~30° no próprio tubo, sem peça.

## Conexões

- **Peça comercial em toda mudança de direção** fora de caixa, horizontal ou vertical, inclusive DRE e ESG.
- **Só 45° e 90°** (decisão de 21/10/2026); 135° = 90° + 45°. Tês e junções são comerciais e não entram na conta do ângulo. Nó com 3 ou mais tubos fora de caixa = junção.
- Tubo rígido aceita até 5° de deflexão na junta.
- **NUNCA mover vértice em planta para encaixar ângulo comercial.** Ângulo do traçado fora do comercial é geometria do projeto: a peça sai com o ângulo comercial mais próximo e o desvio fica só em registro interno, nunca em LEIA-ME, pendência, prancha ou Pset entregue.
- A perna da conexão não passa de 45 % do tubo vizinho.

## Caixas ocas

PV, CI, CA e caixa de passagem (a partir de 0,30 m de altura e de lado) saem por extrusão com fundo de 0,10 m, parede de 0,10 m (retangular) ou anel de 0,08 m (PV circular) e tampa de 0,05 m; tampa em grelha de ferro fundido nas caixas de areia e bocas de lobo. Tampa = CT do projeto; fundo = CF, e desce até abaixo do tubo mais fundo que chega na caixa. Caixa redonda é cilindro (quadrado acusa colisão falsa nos cantos). Furo de passagem dos tubos ainda não é feito.

## Continuidade da rede

Regra de 20/10/2026, depois que o incêndio da Jandaíra saiu "picotado":

- Rede contínua de caixa a caixa: toda ponta termina em tubo, conexão, caixa, equipamento ou na edificação.
- Pontas da mesma rede a até 15 cm (planta) e 5 cm (cota), fora de caixa, viram um nó (`costura.py`). Tubo que chega no meio de outro ganha junção. Uma peça por ponto.
- Nada de pedaço menor que a conexão (< 3 × DE ou < 10 cm), salvo entre caixas. Nada de tubos colineares sobrepostos.
- **Barrilete e casa de bombas ficam na cota do modelo**, fora do estudo de cota (raio fixo de 3 m em torno de bomba e tanque); válvulas, tês e reduções do barrilete entram como peças.
- `verificar.py` roda em toda rodada; item explicado (fim de rede no quadro, niple entre válvulas, saída de prédio) vai em `VERIFICACAO_ESPERADA` no adaptador. A lista é conferida no 3D antes de entregar.

## Rede acima do piso (entregas só de modelagem)

Decisão de 27/10/2026 (bloco BP4 da Jandaíra): mesmo quando a entrega é só modelagem, a rede acima do piso fica **fora da estrutura**:

- nunca dentro de pilar: a coluna encosta na face (folga 2 cm) e o trecho horizontal desvia de lado o mínimo, com a fileira reta;
- elétrica e SDAI de teto sob a viga mais baixa;
- o que ainda passar por viga (água, esgoto, hidrante) vai numa lista de passagens no envio;
- pluvial de cobertura sobre a laje em todo o percurso (geratriz ≥ 0,05 m acima do ponto mais alto da laje embaixo).

Não se dispensa como "compatibilização fora do escopo". Item D10 do checklist.

## Abrir no Revit

"Abrir IFC" no Revit 2025 cria um projeto que vincula o `.ifc.RVT` e põe tudo na Fase 3, enquanto a vista 3D mostra a Fase 1. Para ver: Fase 3 na vista 3D; VV → Local → desmarcar pontos de levantamento e base; depois ZF.

## Visualizadores

- Visualizador do preclash (HTML com three.js): situação projeto × solução, conflitos, soluções, pendentes. Botão de validação: 1º toque esconde terreno e arquitetura (colisões e conexões), 2º volta o terreno sólido (tampas das caixas), 3º volta ao normal.
- Visualizador único de todas as escolas: a página não tem dados embutidos; cada escola é um `dados/<SIGLA>.json` publicado junto, e tem a aba Pranchas do CDE.
- Visualizador neutro de IFC (That Open Engine, `preclash/thatopen/`) para abrir o federado como o cliente recebe.
