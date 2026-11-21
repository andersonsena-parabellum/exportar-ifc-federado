# Georreferenciamento de CAD e vínculos

## Sumário
1. Diagnóstico do DWG
2. CAD local → UTM (ICP)
3. DWG de disciplina em outro sistema local
4. Georreferenciar dentro do Revit (quando o AutoCAD falha)
5. Vínculos RVT com coordenadas próprias
6. Copiar vínculos de um RVT para outro (receita JSON)
7. Navisworks
8. accoreconsole (scripts .scr)

---

## 1. Diagnóstico do DWG

Rode o `accoreconsole` numa **cópia** e leia: `INSUNITS`, `EXTMIN`/`EXTMAX`, a lista de layers e os blocos.
- Extensão na casa de 500 000 / 8 600 000 (SIRGAS UTM) → já está em UTM.
- Extensão perto de 0 → coordenadas **locais** (comum em QiBuilder).
- Extensão absurda → há lixo longe da obra; limpe antes.

## 2. CAD local → UTM (ICP)

- A transformação é **rígida**: rotação + translação, sem escala.
- **Não confie em "ponte" por PDF ou em coordenadas impressas:** no ETIB isso errou ~2,3 m.
- O que funciona: **ICP** (casamento de pontos) entre um **bloco de arquitetura embutido** no projeto da disciplina (ex.: `ARQ_BASE_...`) e a mesma arquitetura na planta de implantação georreferenciada. Resíduo esperado: poucos mm.
- **Ordem:** primeiro rotacionar em torno de (0,0), depois transladar. Grave os valores com todas as casas decimais num JSON (`transformacao_<DISC>_local_para_UTM.json`).
- Aplique na cópia (`_GEO.dwg`) e nunca no original.
- **Blocos com transformações enormes** são deslocados pelo Revit ao vincular: explodir antes, na cópia `_REF`.

## 3. DWG de disciplina em outro sistema local

Não presuma que todos os DWGs usam o mesmo sistema local. No ETIB, o incêndio (mesmo escritório da AF e do ESG) estava deslocado ~70 m.

Diagnóstico rápido:
1. Vincule o DWG de origem a origem.
2. Leia a posição e a rotação dos blocos de arquitetura embutidos pela geometria (ver `revit-mcp-api.md`, "CAD importado").
3. Se a **rotação for igual** à da disciplina de referência e o deslocamento for o **mesmo em todos os blocos** (diferença < 1 µm), é só uma translação até o sistema da referência; depois vale a transformação dela.
4. Se a rotação diferir, faça um ICP próprio.

## 4. Georreferenciar dentro do Revit (quando o AutoCAD falha)

1. Vincule com `ImportPlacement.Origin` e `Unit = Meter`.
2. `ElementTransformUtils.RotateElement` em torno da origem interna, pelo ângulo da transformação.
3. `ElementTransformUtils.MoveElement` por `R·d + t − origem do projeto` (d = translação local entre sistemas, se houver; t = translação para UTM).
4. Prove: vincule o CAD base UTM com `ImportPlacement.Shared` e compare um bloco comum (Δ deve ser ≈ 0 mm).

## 5. Vínculos RVT com coordenadas próprias

- `ProjectLocation.GetTotalTransform()` mapeia compartilhado → interno.
- Matriz do vínculo: **`M = T_host × T_link⁻¹`**.
- No ETIB, a primeira tentativa saiu invertida: **valide sempre** sobrepondo a planta.
- "Adquirir coordenadas"/vínculo por coordenadas compartilhadas pode ser recusado ou abrir diálogo pela API. A saída é posicionar por transformação calculada.
- Se o modelo base tem um "SIT movido" levemente deslocado do SIT original, meça o deslocamento e inclua na transformação (ETIB: −0,150 ; +0,165 m).
- Vínculos aninhados: posição real = `T_base × T_aninhado`.
- **Se o usuário diz que "não está alinhado", pare.** Pergunte qual arquivo está na posição certa e alinhe o outro a ele.

## 6. Copiar vínculos de um RVT para outro (receita JSON)

No RVT de origem, para cada `RevitLinkInstance` e `ImportInstance` relevante, grave:
- caminho do arquivo, nome do tipo;
- origem da transformação total e ângulo de `BasisX` (para CAD: use `GeometryInstance.Transform`, não `GetTotalTransform`);
- pinned, tipo de anexação (Sobreposição/Anexo);
- pontos de base e de levantamento, níveis, filtros e modelos de vista.

No RVT novo: `RevitLinkType.Create(doc, ModelPathUtils.ConvertUserVisiblePathToModelPath(caminho), new RevitLinkOptions(true))` (caminho relativo) → `RevitLinkInstance.Create(doc, typeId, ImportPlacement.Origin)` → rotação + movimento → `Pinned = true`. Desvio medido no ETIB: 0,000 mm.

**Lotes de ~6 vínculos por chamada:** 10 RVTs numa chamada deram timeout (105 s), com a resposta chegando atrasada na chamada seguinte.

Um modelo aberto na sessão **não pode ser vinculado**: feche o RVT anterior depois de exportar a receita.

## 7. Navisworks

- Coordenadas iguais em todas as disciplinas = federação direta (NWC com "Coordenadas compartilhadas").
- RVTs de referência posicionados por transformação (sem compartilhar coordenadas) devem sair **pelo NWC do hospedeiro**, com "Converter arquivos vinculados".
- Publicar coordenadas em arquivos de terceiros altera esses arquivos: só com autorização.

## 8. accoreconsole (scripts .scr)

- Executar via PowerShell: `Start-Process accoreconsole.exe -ArgumentList '/i "copia.dwg" /s "script.scr"'`, sempre com timeout (`WaitForExit(ms)` + `Kill`), porque o console trava em silêncio.
- Scripts com quebra de linha **CRLF**. Comece com `SECURELOAD 0` para carregar LISP.
- **Sem `vla-*`** (ActiveX não existe no console): use `entget`/`entmod`/`ssget`.
- Para apagar entidades em layer travado, destrave o layer antes do `ERASE`.
- Não gere scripts com heredoc sem aspas no bash: ele altera as barras invertidas dos caminhos. Use o Write ou heredoc com aspas simples.
- Trabalhe em **cópia** e salve com sufixo (`_GEO`, `_REF`).
- **Alguns DWGs não abrem** (QiBuilder com objetos personalizados: `ErrorStatus=53` com `/readonly`; sem `/readonly` espera para sempre; `RECOVER` passa mas `SAVEAS` derruba). Não insista: georreferencie no Revit (seção 4) e use os textos do PDF (`pdf-como-fonte.md`).
