# Revit API pelo MCP (`send_code_to_revit`): limitações e receitas

## Sumário
1. Transação, erros e retorno
2. Sessão: documento ativo, timeouts, salvar
3. Tubos e conexões MEP
4. Eletrodutos
5. Famílias e DirectShape
6. Cortes e vistas 3D
7. CAD importado (ImportInstance)
8. Amostrar o terreno de um vínculo
9. Ler o que o usuário está vendo

---

## 1. Transação, erros e retorno

- O código **já roda dentro de uma transação do add-in**. `new Transaction` dá erro de transação aninhada.
- Isole passos com `SubTransaction`. Para desfazer tudo, **lance uma exceção**.
- "Exception has been thrown by the target of an invocation" esconde a causa: envolva cada passo em `try/catch` dentro de `SubTransaction` e devolva `ex.Message` (e `ex.InnerException?.Message`) passo a passo.
- Retorno grande estoura a resposta: devolva resumo ou CSV curto e grave o resto em arquivo (`File.WriteAllText`).
- Revit 2025: `new ElementId(long)`, não `int`.
- Apagar elementos enquanto itera um `FilteredElementCollector` dá erro de "Iterator": chame `.ToElements()` (ou `.ToElementIds().ToList()`) antes.
- Lotes de **dezenas** de elementos por chamada, não centenas. Um lote que falha é desfeito inteiro.

## 2. Sessão: documento ativo, timeouts, salvar

- `document` é o documento **ativo**, que muda quando o usuário troca de janela. Todo código que edita começa com `if (document.Title != "...") throw ...`.
- **Diálogo modal = timeout.** Avisos de hachura ao vincular DWG e janelas de add-in travam o MCP. Muitas vezes o comando terminou: confira antes de repetir. Ver `dialogos-revit.md`.
- **Depois de um timeout,** a resposta seguinte pode ser o resultado atrasado do comando anterior. Rode uma consulta com marcador (`return "CHECK4 " + ...`) antes de repetir.
- **Salvar:** `doc.Save()` não funciona dentro da transação. Agende o comando, que roda logo após o código:
  `new UIApplication(document.Application).PostCommand(RevitCommandId.LookupPostableCommandId(PostableCommand.Save));`
  Confira pela data de modificação do arquivo.
- Antes de operação arriscada: copie o RVT para `<nome>_BACKUP_aaaa-mm-dd_hhmm.rvt`.
- Filtro de avisos via `FailuresProcessing` instalado pelo código **não** evitou o aviso de hachura ao vincular DWG. Não conte com ele.

## 3. Tubos e conexões MEP

- **Teste as conexões do tipo antes de modelar:** crie curvas (90°, 45°, 22,5°) e um tê dentro de `SubTransaction` e desfaça com `RollBack()`.
- Segmento novo: `Autodesk.Revit.DB.Plumbing.PipeSegment.Create(doc, materialId, scheduleTypeId, List<MEPSize>)`. Qualifique o namespace: o nome curto dá "inacessível".
- **Joelho:** a família falha com deflexão < ~15° (algumas aceitam 5–8°) ou > 90°. Use ligação direta (`connA.ConnectTo(connB)`).
- **Tê:** exige principal reto e ramal a 90°. Use **tocos** curtos para "endireitar": `min(0,35 m; comprimento/3)`.
- **Redirecionar um tubo já conectado** (ex.: encaixar o toco do tê): preserve o sentido da curva, `atStart ? Line.CreateBound(S,F) : Line.CreateBound(F,S)`. Se inverter, aparece o erro não ignorável "o duto/tubo foi modificado para a direção oposta".
- Dois tocos no mesmo tubo geram aviso de "marca duplicada": OK no aviso e renumere as marcas.
- Pontas abertas que não chegam a equipamento: `PlumbingUtils.PlaceCapOnOpenEnds(doc, pipeId, typeId)`.

## 4. Eletrodutos

- Eletroduto enterrado: **sem conexões**, ponta a ponta. Condulete 90° em dobra suave = "não é possível manter a conectividade".
- `ConduitSizeSettings.GetConduitSizeSettings(doc)` é instância: `css.CreateConduitStandardTypeFromExisingStandardType(...)` e `css.AddSize(...)`.
- `CONDUIT_STANDARD_TYPE_PARAM` do tipo é um **ElementId** de um ElementType com o nome do padrão.

## 5. Famílias e DirectShape

- Famílias baseadas em plano de trabalho (bomba, registro) criadas com `NewFamilyInstance(ponto, símbolo, nível)` ficam em z ≈ 0: mova em Z depois e confira pelo bounding box.
- Famílias de terceiros podem ter o ponto de inserção deslocado da tampa (UnMEP: ~6 cm). Confira pelo bounding box e ajuste.
- DirectShape a partir do contorno do CAD: extrusão (`GeometryCreationUtilities.CreateExtrusionGeometry`) do laço fechado, categoria adequada (Equipamento mecânico, Acessório de tubulação, Genérico), `ApplicationId`/`ApplicationDataId` preenchidos, e `COMP_*` com "esquemático".

## 6. Cortes e vistas 3D

- `ViewSection.CreateSection`: o Revit inverte o Z local e o plano de corte fica em −Min.Z. Use `Min.Z = 0` e posicione o corte um pouco à frente do objeto (ex.: 0,6 m).
- Logo após `CreateSection`, zere `ViewTemplateId = ElementId.InvalidElementId` se for mexer no nível de detalhe ("Detail Level cannot be modified").
- **Exportar imagem de 3D:** ative a crop box e ajuste-a à projeção da caixa de corte; senão a imagem pega o modelo todo e o objeto sai minúsculo.

## 7. CAD importado (ImportInstance)

- Depois de mover/rotacionar, `GetTotalTransform()` continua identidade. A posição real está em `GeometryInstance.Transform` da geometria.
- Nome de bloco aninhado: `doc.GetElement(gi.GetSymbolGeometryId().SymbolId).Name` (`GeometryInstance.Symbol` não existe).
- Hachuras chegam como **faces de um único Solid**; o layer de cada uma está em `face.GraphicsStyleId`. `Face.IsInside` não é confiável: exporte os `EdgeLoops` e faça ponto-no-polígono em Python.
- Layers: `CADLinkType.Category.SubCategories` (para ocultar/colorir por vista).
- O Revit **não** importa textos de DWG: use o PDF (`pdf-como-fonte.md`).

## 8. Amostrar o terreno de um vínculo

```csharp
var v3d = new FilteredElementCollector(document).OfClass(typeof(View3D)).Cast<View3D>()
    .First(v => !v.IsTemplate && v.Name == "AF - 3D");   // precisa existir
bool box = v3d.IsSectionBoxActive; v3d.IsSectionBoxActive = false;  // a caixa de corte recorta
var ri = new ReferenceIntersector(new ElementCategoryFilter(BuiltInCategory.OST_Toposolid),
                                  FindReferenceTarget.Element, v3d) { FindReferencesInRevitLinks = true };
// para cada ponto (x, y) em pés internos:
var hit = ri.FindNearest(new XYZ(x, y, 1000), XYZ.BasisZ.Negate());
double zTerreno = hit != null ? hit.GetReference().GlobalPoint.Z : double.NaN;
v3d.IsSectionBoxActive = box;
```

Grave os pontos em arquivo (`x;y;z` em metros) e passe para `scripts/cotas_pressurizada.py`.

## 9. Ler o que o usuário está vendo

Clicar numa linha/hachura do CAD seleciona o CAD inteiro. Para identificar o que o usuário aponta num print:
- leia o zoom da vista (`uidoc.GetOpenUIViews().First(u => u.ViewId == view.Id).GetZoomCorners()`);
- varra a geometria do CAD naquela área (layer de cada curva/face) ou faça `ReferenceIntersector` ali;
- responda com o arquivo e o layer de origem antes de opinar.
