---
name: modelagem-bim-disciplinas
description: 'Modelagem BIM de disciplinas de infraestrutura e instalações (água fria, esgoto, drenagem pluvial, incêndio/hidrantes, SDAI, GLP, elétrica/dados enterrados, estrutura/fundações) no Revit via MCP (send_code_to_revit), a partir de DWG/PDF de projeto, para compatibilização. Cobre georreferenciar CADs locais (QiBuilder) em UTM, criar o RVT da disciplina com coordenadas compartilhadas e vínculos, extrair a rede do CAD por script, calcular cotas (recobrimento, declividade, tubo de queda), criar tubos/caixas/conexões por API, montar vistas e folhas de validação, checar interferências e gerar relatório de incompatibilidades. Use SEMPRE que o usuário pedir para modelar, continuar, retomar ou validar uma rede ou disciplina no Revit, vincular/georreferenciar DWG, configurar vistas de validação, compatibilizar disciplinas ou montar relatório de clash, mesmo que não diga "BIM" nem "skill" (ex.: "vamos fazer a drenagem agora", "modela o esgoto do DWG", "onde paramos no incêndio?", "o tubo não bate com o CAD").'
---

# Modelagem BIM de disciplinas no Revit (via MCP)

Esta skill reúne o método que funcionou na modelagem das redes externas da ETIB escola B-BA (AF, ESG, incêndio e SDAI, out/2026). O objetivo de cada disciplina é um modelo **fiel ao projeto**, nas coordenadas reais, pronto para o usuário validar sobre o CAD e para a compatibilização com as outras disciplinas no Navisworks.

Ferramentas típicas:
- Revit 2025 + `mcp-server-for-revit` (ferramenta `send_code_to_revit`, C#);
- AutoCAD `accoreconsole` para tratar DWG sem abrir o AutoCAD;
- Python (numpy, PyMuPDF) para topologia, cotas e leitura de PDF.

Responda sempre em **português**.

## 0. Antes de mexer em qualquer coisa

1. **Leia o `licoes-modelagem.md` do projeto** (normalmente na raiz da pasta do projeto), além da memória e do plano, se existirem. A Parte B desse arquivo traz o que já foi decidido para o projeto (origem, transformações, níveis, recobrimentos, IDs). Essas decisões não se perguntam de novo.
2. **Consulte o Revit pelo MCP:** qual documento está ativo, os vínculos, os níveis e a contagem de elementos por categoria. O usuário pode ter avançado sozinho (no ETIB, ele já tinha criado o RVT de incêndio).
3. Se for uma **retomada** ("onde paramos?"), liste também os arquivos por data e leia o fim das transcrições anteriores antes de responder.

## 0.1 Perguntar o modo de trabalho (sempre, no início)

Antes de começar a modelar, pergunte ao usuário qual modo usar (use `AskUserQuestion`, com estas opções; recomende o **Por fases** se a disciplina for nova e o **Contínuo** se for parecida com uma já validada). Se ele já tiver dito o modo no pedido ("modo contínuo", "vá até o fim"), não pergunte de novo. Numa retomada, mantenha o modo da sessão anterior se ele estiver registrado no `licoes-modelagem.md` ou na memória, e só confirme em uma linha.

| Modo | Como se comporta |
|---|---|
| **Por fases** (padrão) | Para para conferência ao fim de cada fase (georreferência, rede extraída e CSV de cotas, modelagem, vistas, checagens) e espera o "ok" do usuário. |
| **Contínuo** | Executa tudo, do diagnóstico ao relatório final, sem pedir validação intermediária. O usuário confere no fim, pela lista de premissas e pelas vistas. |

**No modo contínuo, o Claude só para nestes casos** (o resto, decide, adota a premissa e registra):
1. **Prova de coordenadas reprovada.** Os dois testes do passo 4 da seção 3 (CAD UTM e elemento do vínculo anterior com Δ ≈ 0) são feitos sozinhos. Se passarem, segue; se falharem, para e corrige, porque uma base errada contamina todo o resto.
2. **Bloqueio que só o usuário resolve:** diálogo que o `revit_dialog.ps1` não consegue fechar, "Revit MCP Switch" desligado, falta de arquivo ou de dado que não existe no CAD/PDF.
3. **Ações que exigem autorização:** desativar suplemento, alterar ou publicar coordenadas em arquivo de terceiros, apagar o que o usuário criou.
4. **Decisão de projeto sem resposta nos documentos**, quando o palpite mudaria muito o modelo (ex.: qual terreno vale para a rede, Ø ou material ausente em trecho longo). Para dúvida pequena, adote a premissa.
5. **O mesmo erro duas vezes seguidas** sem causa clara: pare, descreva o que testou e peça orientação.

**Cuidados do modo contínuo** (o custo de um erro cedo é maior, porque ele se propaga):
- faça **backup do RVT** (`_BACKUP_data_hora.rvt`) antes de cada fase de criação em massa e salve ao fim de cada fase;
- rode as checagens automáticas (recobrimento, caixa × terreno, clash) e **não esconda resultado ruim**: ele vai para o relatório final;
- nunca "corrija" em silêncio uma divergência projeto × obra, nem no modo contínuo.

**Relatório final do modo contínuo** (a conferência do usuário; entregue neste formato):
1. **Resumo:** o que foi modelado, com quantidades (tubos, metros por Ø, caixas) e o arquivo/backup salvo.
2. **Premissas adotadas**, numeradas, cada uma com onde se aplica (trecho/caixa), o motivo e como reverter. Marque as **inferidas** (laços, cotas ausentes, famílias substitutas, elementos esquemáticos).
3. **Pontos de atenção em ordem de risco:** o que mais merece o olho dele primeiro.
4. **Interferências** por severidade (CRÍTICA / ATENÇÃO / INFORMAÇÃO).
5. **Vistas e folhas para validar**, com nome e ID, na ordem sugerida de conferência.
6. **Pendências e decisões** que dependem dele.

## 1. Princípios (e por quê)

- **Uma disciplina por vez.** No modo por fases, com checkpoint: o usuário valida cada rede visualmente sobre o CAD antes da próxima, porque um erro de georreferência ou de cota se propaga para todas as checagens de clash. No modo contínuo, o checkpoint vira o relatório final (seção 0.1).
- **Extrair a rede do CAD por script, nunca "na mão".** O script é reprodutível, gera CSV conferível e pode ser refeito quando o projeto mudar de revisão.
- **Modelar conforme o projeto, sem corrigi-lo em silêncio.** Se a CT da caixa não bate com o terreno executado, modele a CT do projeto e reporte como incompatibilidade. A decisão de quem errou (projetista ou obra) é do usuário.
- **Vínculos, não cópias.** Há um arquivo base (terreno, implantação, blocos) e as instalações ficam em outro RVT, ou em vários. Não copie geometria da base para dentro das instalações.
- **Vistas de validação fazem parte da entrega.** O usuário não quer configurar vista para conferir. Planta com CAD em meio-tom, 3D, cortes, tabelas e folhas saem junto com a modelagem.
- **Quando o usuário disser que algo "não está alinhado" ou "está estranho", pare.** Descubra de qual arquivo e de qual layer vem o elemento (zoom da vista → geometria/raycast) e responda com o dado antes de opinar ou corrigir.
- **Peça só o que depende do usuário:** decisão de projeto, um clique que o Windows bloqueia, autorização para mexer em arquivo de terceiros ou desativar suplemento. O resto, faça.

## 2. Fluxo da 1ª disciplina (RVT novo, sem disciplina anterior)

1. **Diagnosticar os DWGs** com `accoreconsole` em cópia: INSUNITS, EXTMIN/EXTMAX, layers, se está em UTM ou local. Projetos QiBuilder costumam vir em coordenadas **locais**. → `references/georreferenciamento-cad.md`
2. **Georreferenciar em cópias** (`CAD_GEORREFERENCIADO\`, sufixo `_GEO`): transformação rígida local → UTM por ICP em um bloco de arquitetura comum aos dois desenhos. Salve a transformação em JSON.
3. **Limpar a planta base** numa cópia `_REF`: entidades perdidas, blocos pesados ou duplicados, blocos com transformação enorme (explodir).
4. **Coordenadas do RVT:** origem interna = ponto UTM redondo perto da obra, sem rotação, cota 0. Assim, cota interna = cota absoluta.
5. **Vincular os CADs** (Link, nunca Import), em meio-tom.
6. **Terreno:** o do modelo base "as built" (vínculo), se existir. Senão, Toposolid do topográfico.
7. **Níveis** em cota absoluta, um por platô (`PLATÔ +135,50`).
8. **Configurar o MEP:** tipos de tubo e segmentos com DE reais, sistemas com cor e abreviação, filtros por disciplina, parâmetros compartilhados `COMP_*`. **Teste as conexões do tipo** (curvas de 90°/45°/22,5° e tê) em `SubTransaction` com `RollBack()` antes de modelar.
9. **Extrair a rede por script** → grafo (nós = caixas/conexões, arestas = trechos) → CSV de trechos e de nós. → `scripts/topologia_rede.py`
10. **Calcular as cotas** pela regra da disciplina (seção 4) e **validar o CSV** antes de criar qualquer coisa no Revit. → `scripts/cotas_pressurizada.py` para redes que seguem o terreno.
11. **Criar no Revit por API, em lotes de dezenas:** tubos, conexões, caixas, `COMP_*`. → `references/revit-mcp-api.md`
12. **Montar as vistas de validação e as folhas.** → `references/vistas-validacao.md`
13. **Checagens automáticas:** recobrimento (tubo × terreno), caixa × terreno, disciplina × disciplina (colisão e folga), tubo × estrutura dos vínculos.
14. **Checkpoint com o usuário** (no modo contínuo: relatório final da seção 0.1) e, depois, o relatório de incompatibilidades. → `references/relatorio-incompatibilidades.md`

## 3. Fluxo da 2ª disciplina em diante (novo RVT)

1. Com o RVT anterior aberto, **exporte a "receita" para JSON**: a transformação total de cada vínculo, os pontos de base e de levantamento, os níveis, os filtros e os modelos de vista. Depois **feche esse RVT**, porque um modelo aberto na sessão não pode ser vinculado.
2. No RVT novo:
   - aplique a posição do projeto com `SetProjectPosition`, com a mesma origem;
   - troque os níveis do template pelos platôs;
   - apague o lixo do template (CADs importados, níveis de andar).
3. **Recrie os vínculos com a transformação lida do JSON:** `RevitLinkType.Create` + `RevitLinkInstance.Create(Origin)` + rotação/movimento. O RVT da disciplina anterior entra como **Sobreposição**, de origem a origem, fixado.
4. **Prove as coordenadas com dois testes:**
   - o CAD UTM base vinculado com `ImportPlacement.Shared` cai na mesma posição do RVT anterior (Δ ≈ 0);
   - um elemento do vínculo anterior tem a mesma coordenada compartilhada nos dois arquivos.
5. **Confira o DWG da disciplina individualmente.** Cada projetista (e até o mesmo escritório) pode usar outro sistema local: no ETIB, o incêndio estava ~70 m deslocado da AF. → `references/georreferenciamento-cad.md`
6. Siga os passos 8 a 14 da seção 2.

Se o template da disciplina já estiver carregado no arquivo (o usuário pode ter criado o RVT), **não reinstale o template**.

## 4. Regras por disciplina (resumo)

O detalhe de cada uma, com tipos, parâmetros e pegadinhas, está em `references/regras-disciplinas.md`. Leia a seção da disciplina antes de começar.

| Disciplina | Como define as cotas | Status do método |
|---|---|---|
| Água fria (pressão) | Segue o terreno com recobrimento constante | Validado (ETIB) |
| Incêndio / hidrantes (pressão) | Igual à AF; recobrimento da nota do projeto | Validado (ETIB) |
| SDAI / eletrodutos enterrados | Igual à AF; eletroduto ponta a ponta, sem conexão | Validado (ETIB) |
| Esgoto (gravidade) | Cotas do projeto: CT, CF, CE/CS; tubo de queda | Validado (ETIB) |
| Drenagem pluvial (gravidade) | Igual ao esgoto (cotas do projeto) | A validar no 1º uso |
| GLP (pressão, enterrado) | Igual à AF; recobrimento da nota do projeto | A validar no 1º uso |
| Elétrica / dados enterrados | Igual ao SDAI; circuito em `Comentários`/`COMP_Descrição` | A validar no 1º uso |
| Estrutura / fundações | Em geral chega como vínculo de terceiros e serve de referência para clash | A validar no 1º uso |

**Recobrimento:** vale a nota de cada projeto. Na falta dela, use **0,30 m** sob passeio/grama e **0,60 m** sob área de veículos, e registre como premissa. O topo do tubo fica na superfície menos o recobrimento; o eixo fica DE/2 abaixo. Desenhe o polígono da área de veículos uma vez e reaproveite em todas as disciplinas.

Para disciplinas marcadas "a validar", apresente ao usuário as premissas adotadas antes de modelar, porque o método ainda não foi provado nelas.

## 5. Código no MCP: o mínimo de todo script

O código enviado por `send_code_to_revit` **já roda dentro de uma transação**. Os detalhes estão em `references/revit-mcp-api.md`; o essencial:

```csharp
// 1) confirme o documento: o ativo muda quando o usuário troca de janela
if (document.Title != "MODELAGEM-DRENAGEM") throw new Exception("Documento ativo: " + document.Title);
// 2) nada de new Transaction; isole passos com SubTransaction e devolva o erro de cada um
var log = new System.Text.StringBuilder();
using (var st = new SubTransaction(document)) {
    st.Start();
    try { /* ... passo ... */ st.Commit(); log.AppendLine("passo OK"); }
    catch (Exception ex) { st.RollBack(); log.AppendLine("passo ERRO: " + ex.Message); }
}
// 3) para desfazer tudo: throw. 4) devolva resumo curto; dados grandes vão para arquivo
return log.ToString();
```

- Revit 2025: `new ElementId(long)`.
- Lotes de dezenas de elementos por chamada; um lote que falha é desfeito inteiro.
- **Salvar ao fim de cada etapa:** `new UIApplication(document.Application).PostCommand(RevitCommandId.LookupPostableCommandId(PostableCommand.Save))` e confira pela data do arquivo. Antes de operação arriscada, copie o RVT para `_BACKUP_aaaa-mm-dd_hhmm.rvt`.
- **Depois de um timeout,** a próxima resposta pode ser a do comando anterior. Rode uma consulta com um marcador (`"CHECK3"`) antes de repetir qualquer coisa: muitas vezes o comando terminou.
- **Timeout quase sempre é um diálogo modal no Revit.** Leia o diálogo com `scripts/revit_dialog.ps1` e só então decida o botão. → `references/dialogos-revit.md`

## 6. Fontes de dados além do DWG

O Revit não importa textos de DWG, e o `accoreconsole` falha em alguns arquivos (objetos QiBuilder). O **PDF vetorial** do projeto tem todos os textos com posição: Ø, cotas, números de laço, quadros de bitolas e legendas. → `references/pdf-como-fonte.md`

## 7. Entrega de cada etapa

Ao terminar uma etapa, informe:
- o que foi criado (quantidades, comprimentos por Ø, número de caixas);
- os **nomes e IDs** das vistas, folhas, filtros e tabelas criados;
- as **premissas** adotadas (trechos sem cota, famílias substitutas, elementos esquemáticos, dados inferidos);
- as interferências encontradas, por severidade: colisão física = **CRÍTICA**; folga entre redes < 0,20 m = **ATENÇÃO**; dado faltante ou premissa = **INFORMAÇÃO**;
- se o arquivo foi salvo (e o backup, se houve).

No modo por fases, termine pedindo o checkpoint de validação ao usuário, com a lista do que ele deve conferir. No modo contínuo, esta lista é o relatório final da seção 0.1.

## 8. Fechar a etapa: registrar as lições

Ao fim de cada disciplina ou etapa relevante, **acrescente as lições novas ao `licoes-modelagem.md` do projeto**:
- regra que vale para qualquer projeto → Parte A;
- dado do projeto (caminhos, transformações, IDs, pendências) → Parte B.

Se a lição for geral e não estiver nesta skill, diga ao usuário que vale incorporá-la aqui também (em `references/`).

## Mapa das referências

| Arquivo | Quando ler |
|---|---|
| `references/regras-disciplinas.md` | Antes de começar qualquer disciplina |
| `references/georreferenciamento-cad.md` | Ao receber DWG novo, vincular CAD/RVT ou se algo "não alinha" |
| `references/revit-mcp-api.md` | Antes de escrever código para o MCP (conexões MEP, cortes, CAD, terreno) |
| `references/vistas-validacao.md` | Ao montar vistas, modelos de vista, folhas e etiquetas |
| `references/relatorio-incompatibilidades.md` | Ao checar clash e gerar o relatório PDF |
| `references/pdf-como-fonte.md` | Quando faltam textos/cotas do DWG ou o accoreconsole falha |
| `references/dialogos-revit.md` | Timeout, diálogo travando o MCP, suplemento em loop, reabrir o Revit |

Scripts:
- `scripts/topologia_rede.py`: polilinhas do CAD → grafo → trechos e nós (JSON + CSV);
- `scripts/cotas_pressurizada.py`: trechos + amostras de terreno → cotas com recobrimento mínimo (rede que segue o terreno);
- `scripts/revit_dialog.ps1`: lê e clica diálogos do Revit.
