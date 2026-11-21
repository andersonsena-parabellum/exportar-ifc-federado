// Cria o MODELAGEM-FEDERADO.rvt: abre a cópia da base limpa (IMP + estruturas já vinculados), vincula HS/DRN/INC/ELE por origem (Sobreposição),
// cria a vista 3D "FEDERADO - 3D - TODAS AS DISCIPLINAS" com filtros de cor por disciplina e salva.
string P = @"D:\Projeto Modelagem\ETIB-ALAGOINHAS\";
var app = document.Application;
var log = new System.Text.StringBuilder();
Document fd = null; foreach (Document d in app.Documents) if (!d.IsLinked && d.Title.StartsWith("MODELAGEM-FEDERADO")) fd = d;
if (fd == null) { fd = app.OpenDocumentFile(P + "MODELAGEM-FEDERADO.rvt"); log.AppendLine("aberto " + fd.Title); } else log.AppendLine("já aberto " + fd.Title);
string[] files = { "Modelagem - HidroSanitário.rvt", "MODELAGEM-DRENAGEM.rvt", "MODELAGEM-INCENDIO.rvt", "MODELAGEM-ELETRICA.rvt" };
var existentes = new System.Collections.Generic.HashSet<string>();
foreach (RevitLinkType lt in new FilteredElementCollector(fd).OfClass(typeof(RevitLinkType))) existentes.Add(lt.Name);
using (var t = new Transaction(fd, "Federar disciplinas")) {
  t.Start();
  foreach (var f in files) {
    if (existentes.Contains(f)) { log.AppendLine("já vinculado " + f); continue; }
    try {
      var mp = ModelPathUtils.ConvertUserVisiblePathToModelPath(P + f);
      var res = RevitLinkType.Create(fd, mp, new RevitLinkOptions(false));
      var inst = RevitLinkInstance.Create(fd, res.ElementId, ImportPlacement.Origin);
      log.AppendLine("link " + f + " -> " + res.LoadResult + " tipo " + res.ElementId + " inst " + inst.Id);
    } catch (System.Exception ex) { log.AppendLine("link " + f + " ERRO " + ex.Message); }
  }
  // vista 3D
  View3D v3 = null; foreach (View3D v in new FilteredElementCollector(fd).OfClass(typeof(View3D))) if (!v.IsTemplate && v.Name == "FEDERADO - 3D - TODAS AS DISCIPLINAS") v3 = v;
  if (v3 == null) {
    ViewFamilyType vft = null; foreach (ViewFamilyType x in new FilteredElementCollector(fd).OfClass(typeof(ViewFamilyType))) if (x.ViewFamily == ViewFamily.ThreeDimensional) { vft = x; break; }
    v3 = View3D.CreateIsometric(fd, vft.Id); v3.Name = "FEDERADO - 3D - TODAS AS DISCIPLINAS";
  }
  v3.ViewTemplateId = ElementId.InvalidElementId; v3.DetailLevel = ViewDetailLevel.Fine;
  try { v3.get_Parameter(BuiltInParameter.MODEL_GRAPHICS_STYLE).Set(3); } catch { }
  // filtros de cor (aplicam-se aos vínculos "Por vista do hospedeiro")
  ElementId solid = ElementId.InvalidElementId;
  foreach (FillPatternElement fp in new FilteredElementCollector(fd).OfClass(typeof(FillPatternElement))) { var pat = fp.GetFillPattern(); if (pat.IsSolidFill && pat.Target == FillPatternTarget.Drafting) { solid = fp.Id; break; } }
  System.Func<string, Color, OverrideGraphicSettings> OGS = (n, c) => { var o = new OverrideGraphicSettings(); o.SetProjectionLineColor(c); o.SetCutLineColor(c); if (solid != ElementId.InvalidElementId) { o.SetSurfaceForegroundPatternId(solid); o.SetSurfaceForegroundPatternColor(c); o.SetCutForegroundPatternId(solid); o.SetCutForegroundPatternColor(c); } return o; };
  var pipes = new System.Collections.Generic.List<ElementId> { new ElementId(BuiltInCategory.OST_PipeCurves), new ElementId(BuiltInCategory.OST_PipeFitting), new ElementId(BuiltInCategory.OST_PipeAccessory) };
  var cond = new System.Collections.Generic.List<ElementId> { new ElementId(BuiltInCategory.OST_Conduit), new ElementId(BuiltInCategory.OST_ConduitFitting) };
  var sysp = new ElementId(BuiltInParameter.RBS_SYSTEM_NAME_PARAM);
  var typp = new ElementId(BuiltInParameter.ELEM_TYPE_PARAM);
  var defs = new object[][] {
    new object[]{ "FED - INC (hidrantes)", pipes, ParameterFilterRuleFactory.CreateContainsRule(sysp, "INC"), new Color(229,57,53) },
    new object[]{ "FED - ESG", pipes, ParameterFilterRuleFactory.CreateContainsRule(sysp, "Esgoto"), new Color(181,101,29) },
    new object[]{ "FED - AF", pipes, ParameterFilterRuleFactory.CreateContainsRule(sysp, "fria"), new Color(47,140,255) },
    new object[]{ "FED - DRN (demais tubos)", pipes, null, new Color(46,158,91) },
    new object[]{ "FED - SDAI", cond, ParameterFilterRuleFactory.CreateContainsRule(new ElementId(BuiltInParameter.ALL_MODEL_TYPE_NAME), "SDAI"), new Color(255,143,0) },
    new object[]{ "FED - TEL (dados/CFTV)", cond, ParameterFilterRuleFactory.CreateContainsRule(new ElementId(BuiltInParameter.ALL_MODEL_TYPE_NAME), "TEL"), new Color(156,91,214) },
    new object[]{ "FED - ELE (demais eletrodutos)", cond, null, new Color(242,208,42) },
  };
  var nomes = new System.Collections.Generic.Dictionary<string, ParameterFilterElement>();
  foreach (ParameterFilterElement pf in new FilteredElementCollector(fd).OfClass(typeof(ParameterFilterElement))) nomes[pf.Name] = pf;
  foreach (var df in defs) {
    string n = (string)df[0]; var cats = (System.Collections.Generic.List<ElementId>)df[1]; var rule = df[2] as FilterRule; var col = (Color)df[3];
    try {
      ParameterFilterElement pf;
      if (nomes.ContainsKey(n)) pf = nomes[n];
      else if (rule != null) pf = ParameterFilterElement.Create(fd, n, cats, new ElementParameterFilter(rule));
      else pf = ParameterFilterElement.Create(fd, n, cats);
      if (!v3.IsFilterApplied(pf.Id)) v3.AddFilter(pf.Id);
      v3.SetFilterOverrides(pf.Id, OGS(n, col));
      log.AppendLine("filtro " + n + " ok");
    } catch (System.Exception ex) { log.AppendLine("filtro " + n + " ERRO " + ex.Message); }
  }
  // esconder categorias de anotação que poluem
  foreach (var bic in new BuiltInCategory[]{ BuiltInCategory.OST_Levels, BuiltInCategory.OST_Grids, BuiltInCategory.OST_SectionBox, BuiltInCategory.OST_ReferencePoints, BuiltInCategory.OST_VolumeOfInterest })
    try { var c = Category.GetCategory(fd, bic); if (c != null && v3.CanCategoryBeHidden(c.Id)) v3.SetCategoryHidden(c.Id, true); } catch { }
  t.Commit();
  log.AppendLine("vista " + v3.Name + " id " + v3.Id);
}
try { fd.Save(); log.AppendLine("SALVO " + fd.PathName); } catch (System.Exception ex) { log.AppendLine("save ERRO " + ex.Message); }
return log.ToString();
