# Regras de modelagem por disciplina

Disciplinas marcadas **[validado]** foram modeladas de ponta a ponta no ETIB Alagoinhas. As marcadas **[a validar]** seguem as mesmas regras gerais por analogia: apresente as premissas ao usuário antes de modelar e registre o que der certo ou errado no `licoes-modelagem.md`.

## Sumário
1. Regras comuns a todas
2. Água fria [validado]
3. Esgoto sanitário [validado]
4. Incêndio / hidrantes [validado]
5. SDAI e eletrodutos enterrados [validado]
6. Drenagem pluvial [a validar]
7. GLP [a validar]
8. Elétrica / dados / telecom enterrados [a validar]
9. Estrutura / fundações [a validar]
10. Parâmetros COMP_*

---

## 1. Regras comuns a todas

| Tema | Regra |
|---|---|
| Níveis | Cota absoluta, com elevação base no Ponto de Levantamento e cota interna = absoluta. Um nível por platô (`PLATÔ +135,50`). |
| Arquivos | Um RVT por disciplina ou par afim (AF + ESG juntos). Todos com a mesma origem e as mesmas coordenadas compartilhadas. |
| Vínculos | Base (terreno, implantação, blocos) sempre como vínculo. Disciplinas anteriores como **Sobreposição**, de origem a origem, fixadas. |
| Recobrimento | A nota do projeto manda. Na falta: 0,30 m (passeio/grama) e 0,60 m (veículos), registrado como premissa. Topo do tubo = superfície − recobrimento; eixo = topo − DE/2. |
| Área de veículos | Polígono desenhado uma vez e reaproveitado entre disciplinas. |
| Nomenclatura | A do projeto: trechos `AF-07.3`, `ESG-36`; caixas `CI-xx`, `CG-xx`, `PVE-xx`. Gravar em `COMP_Trecho` e/ou Marca. |
| Nomes de vista | Prefixo da disciplina (`AF -`, `ESG -`, `DRN -`, `INC -`, `COMPAT -`). `:` é proibido. |
| Equipamentos sem família | DirectShape tirado do **contorno do próprio CAD** (layer da parede, da caixa), com `COMP_*` e `COMP_Observação = "esquemático"`. |
| Saídas "segue para instalações internas" | Tampão (`PlumbingUtils.PlaceCapOnOpenEnds`) + `COMP_Observação`. No fim, só sobram pontas abertas onde há equipamento. |
| Divergência projeto × obra | Modelar conforme o projeto e reportar. Nunca ajustar em silêncio. |
| Tipo de tubo novo | Criar segmento com os DE reais (`Autodesk.Revit.DB.Plumbing.PipeSegment.Create`, namespace qualificado) e testar as conexões antes de modelar. Se uma redução não existir no template, ligação direta e registrar. |

## 2. Água fria [validado]

- Rede pressurizada: **segue o terreno** com recobrimento constante. Transições entre platôs viram trechos verticais ou inclinados.
- **Algoritmo de cotas** (`scripts/cotas_pressurizada.py`):
  1. amostrar a superfície a cada 0,5 m ao longo da rede (`ReferenceIntersector` no Toposolid do vínculo, ver `revit-mcp-api.md`);
  2. quebrar o trecho onde o terreno desvia mais de **0,20 m** da reta, com trecho mínimo de **2 m** (Douglas-Peucker);
  3. iterar abaixando nós até nenhum ponto ficar com recobrimento menor que o mínimo;
  4. gravar o recobrimento real mínimo em `COMP_Recobrimento Mín` e o exigido em `COMP_Recobrimento Exigido`.
- Material típico: PVC soldável marrom (DE 25 a 75). Hidrômetro → bombas/reservatório → blocos.
- Se houver terreno de projeto **e** terreno "as built", pergunte ao usuário qual vale para a AF; no ETIB isso ficou pendente.

## 3. Esgoto sanitário [validado]

- Gravidade: **usa as cotas do projeto**, não o terreno.
  - CT = tampa; CF = fundo; CE/CS = cota de entrada e de saída do tubo nas caixas.
  - A declividade sai das cotas.
  - Se o tubo chega acima do fundo da caixa de jusante além do normal, aplicar **tubo de queda** e marcar `queda` em `COMP_Observação`.
  - Trecho sem cota: preencher com a declividade mínima do projeto (ou da norma) e registrar a premissa.
- **Caixas:** famílias MEP reais quando houver (ex.: UnMEP CI 60×60, Caixa de Gordura). Na falta, DirectShape com `COMP_*`. Tampa = CT; fundo = CF; profundidade = CT − CF.
  - Famílias de terceiros podem ter a tampa fora do ponto de inserção (UnMEP: ~6 cm acima). Ajustar a elevação e a profundidade juntas e conferir pelo bounding box.
  - Algumas famílias têm profundidade mínima (CG): registrar a exceção.
- **Extração do DWG QiBuilder** (o que funcionou no `esg_build.py`):
  1. linhas duplas dos layers de conduto (`TQ-Condutos`, `TQ-Condutos Gordura`) → eixo;
  2. snap das pontas nos nós;
  3. tipo da caixa pela etiqueta do layer de símbolos (CE/CI/CES/CG);
  4. atribuição gulosa de CT/CF/CE/CS pelos textos próximos, com validação (CF < CT, declividade > 0 no sentido do fluxo);
  5. regra do tubo de queda;
  6. preenchimento da declividade nos trechos sem cota.
- Checagem de CT × terreno executado: caixa acima do terreno = exposta; muito abaixo = soterrada. Vira incompatibilidade, não ajuste.

## 4. Incêndio / hidrantes [validado]

- Pressurizada: mesmo algoritmo da AF. Recobrimento da nota do projeto (no ETIB: **0,50 m**, e 0,60 m em área de veículos).
- Tipo próprio (ex.: "INC - PEAD": segmento PEAD SDR 11 + conexões do template testadas nos DE usados). Sistemas separados para hidrante e recalque.
- **Topologia:** confira no DWG o que é símbolo e o que é rede. No ETIB, arcos de 0,35 m em pares no layer da rede eram **símbolos de ponta** ("segue"), não tês. Blocos de detalhe fora de posição (ampliações) devem ser ignorados.
- Elos muito curtos no DWG (0,37 m) somem com o snap de 0,6 m: tire-os do snap e recrie como trecho explícito.
- **Conexões:** tês com tocos; curvas inclusive de poucos graus (5,9°, 8,3°); ligação direta para deflexão < ~1° e para reduções que não existem no template.
- Casa de bombas: DirectShape do contorno da parede no CAD; bombas e registros com famílias do template, mas **move em Z depois** (famílias baseadas em plano de trabalho caem em z ≈ 0).
- Hidrante de recalque: subida + registro + caixa (DirectShape).
- Se o diâmetro maior aparece só num trecho (ex.: 3" reservatório → bombas), confirme o vértice de troca imprimindo os vértices reais do trecho; o snap pode ter movido a ponta.

## 5. SDAI e eletrodutos enterrados [validado]

- Cotas pelo mesmo algoritmo da AF.
- **Eletroduto enterrado fica ponta a ponta, sem conexões:** curvas tipo "condulete 90°" não aceitam dobras suaves e geram "não é possível manter a conectividade". Se acontecer: "Desconectar" e apagar as curvas órfãs.
- Padrão de eletroduto novo: `ConduitSizeSettings` é instância → `css.CreateConduitStandardTypeFromExisingStandardType(...)` e `css.AddSize(...)`. O parâmetro `CONDUIT_STANDARD_TYPE_PARAM` do tipo é um **ElementId** de um ElementType com o nome do padrão.
- **Laços/circuitos:** gravar em `Comentários` e `COMP_Descrição`, para aparecer na tabela. Se o projeto indica o laço por número circulado + legenda, casar os números do PDF com os blocos do DWG (ver `pdf-como-fonte.md`). Laços sem indicação explícita: inferir pela lógica (ramal curto de um bloco = laço único; tronco = vários) e marcar como **inferido**.
- Caixas de passagem: DirectShape com profundidade = topo do terreno − fundo.
- Filtro por regra `ALL_MODEL_MARK` começa com "SDAI" (ou pelo tipo de eletroduto).

## 6. Drenagem pluvial [a validar]

Por analogia com o esgoto (gravidade):
- **Cotas do projeto:** CT/CF de PVs, caixas de passagem, bocas de lobo e caixas ralo; CE/CS quando houver. Declividade a partir das cotas; trecho sem cota com a declividade mínima do projeto, registrada como premissa.
- **Diâmetro:** projetos de drenagem costumam indicar o **DN interno** (concreto, PEAD corrugado). Crie o segmento com o DI e o DE corretos do fabricante; o recobrimento é medido no topo externo.
- Elementos de superfície (canaletas, sarjetas, grelhas, valas): perguntar ao usuário se entram no modelo. Se entrarem, DirectShape a partir do contorno do CAD ou família de vala; marcar como esquemático.
- Lançamentos (saída para a rua, dissipador, poço de infiltração): modelar até o ponto de lançamento e tamponar/registrar.
- Checagem extra: interferência drenagem × esgoto nos cruzamentos (redes por gravidade não têm folga para desviar; o conflito é sempre crítico ou de atenção).

## 7. GLP [a validar]

- Pressurizada enterrada: algoritmo da AF.
- Recobrimento, envelopamento/proteção mecânica e afastamentos mínimos de outras redes: **seguir a nota do projeto**. Se a nota não trouxer, pergunte ao usuário antes de adotar valor.
- Abrigo de cilindros/central: DirectShape do contorno do CAD.
- Afastamento GLP × elétrica é critério de compatibilização próprio: inclua na checagem de folga, com o valor que o usuário definir.

## 8. Elétrica / dados / telecom enterrados [a validar]

- Mesmo tratamento do SDAI: eletroduto ponta a ponta, cotas pelo terreno, caixas de passagem em DirectShape.
- Circuitos/bancos de dutos: atributo em `Comentários` + `COMP_Descrição`. Bancos com vários eletrodutos lado a lado: modelar cada eletroduto (ou um DirectShape do envelope, se o usuário preferir) e confirmar a configuração do banco no corte típico do projeto.
- Média tensão × baixa tensão × dados: sistemas/filtros separados.

## 9. Estrutura / fundações [a validar]

- No fluxo validado, a estrutura **chega como vínculo de terceiros** (blocos FUN/ECC/EMT em RVTs separados) e serve de referência para o clash: sapatas, blocos, baldrames e pilares.
  - Vínculos aninhados (blocos dentro do modelo base): a posição real é `T_base × T_aninhado`.
  - Para checar clash, leia a geometria do vínculo com a transformação total e compare em coordenadas do hospedeiro.
- Se for preciso **modelar** fundações a partir do CAD (planta de locação/formas):
  - famílias de Fundação Estrutural (sapata, bloco, estaca) e Estrutura (viga baldrame), com dimensões e cota de fundo/topo do projeto;
  - níveis absolutos; o topo da sapata/bloco vem do corte ou da tabela do projeto, nunca do terreno;
  - pilares até o nível de arranque, só o necessário para a compatibilização.
  - Apresente ao usuário as premissas de cota antes de modelar.
- Não publique coordenadas nem altere arquivos de terceiros sem autorização.

## 10. Parâmetros COMP_*

Ficam num TXT de parâmetros compartilhados próprio de compatibilização (no ETIB: `BIM - Parametros Compartilhados - Compatibilizacao.txt`).

- Gerais: `COMP_Disciplina`, `COMP_Trecho`, `COMP_Descrição`, `COMP_Origem`, `COMP_Observação`.
- Pressurizadas: `COMP_Recobrimento Mín`, `COMP_Recobrimento Exigido`, `COMP_Cota Topo Início/Fim`, `COMP_Terreno Início/Fim`.
- Gravidade: `COMP_GI Montante/Jusante`, `COMP_Declividade`, `COMP_CT`, `COMP_CF`, `COMP_Profundidade`.

Preencha os `COMP_*` na mesma chamada que cria o elemento: é o que alimenta as tabelas de validação e o relatório.
