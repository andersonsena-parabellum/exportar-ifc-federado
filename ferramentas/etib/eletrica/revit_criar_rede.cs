// Cria eletrodutos (Conduite sem conexões, Tabela RNC 40) e caixas (DirectShape) de UMA rede no MODELAGEM-ELETRICA (aberto em segundo plano).
// Entrada: work/revit_conduits.tsv e work/revit_caixas.tsv (ele_export_revit.py). Saída: work/revit_ids_<TAG>.tsv
string TAG = "EL1";
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
string W = @"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.Title == "MODELAGEM-ELETRICA") e = d;
if (e == null) return "MODELAGEM-ELETRICA não está aberto";
var log = new System.Text.StringBuilder(); var ids = new System.Text.StringBuilder();
Level lv = null; foreach (Level l in new FilteredElementCollector(e).OfClass(typeof(Level))) if (l.Name == "PLATÔ +135,50") lv = l;
System.Func<string, double> D = s => double.Parse(s, ci);
System.Action<Element, string, string> SS = (el, n, v) => { var p = el.LookupParameter(n); if (p != null && !p.IsReadOnly) p.Set(v); };
System.Action<Element, string, double> SL = (el, n, v) => { var p = el.LookupParameter(n); if (p != null && !p.IsReadOnly) p.Set(v / F); };
using (var t = new Transaction(e, "ELE fase 4 - " + TAG)) {
  t.Start();
  // 1) COMP_* também em Conduítes
  var conCat = Category.GetCategory(e, BuiltInCategory.OST_Conduit); int nb = 0;
  var it = e.ParameterBindings.ForwardIterator(); var defs = new System.Collections.Generic.List<Definition>(); var bds = new System.Collections.Generic.List<ElementBinding>();
  while (it.MoveNext()) { if (it.Key.Name.StartsWith("COMP_")) { defs.Add(it.Key); bds.Add((ElementBinding)it.Current); } }
  for (int i = 0; i < defs.Count; i++) if (!bds[i].Categories.Contains(conCat)) { bds[i].Categories.Insert(conCat); e.ParameterBindings.ReInsert(defs[i], bds[i]); nb++; }
  log.AppendLine("bindings COMP_ + Conduítes: " + nb);
  // 2) limpa o que já foi criado desta rede (reexecução)
  var old = new System.Collections.Generic.List<ElementId>();
  foreach (Element el in new FilteredElementCollector(e).WhereElementIsNotElementType()) {
    if (!(el is Autodesk.Revit.DB.Electrical.Conduit) && !(el is DirectShape)) continue;
    var p = el.LookupParameter("COMP_Trecho"); if (p != null && p.HasValue && (p.AsString() ?? "").StartsWith(TAG + "-")) old.Add(el.Id);
  }
  if (old.Count > 0) e.Delete(old); log.AppendLine("apagados (reexecução): " + old.Count);
  // 3) eletrodutos
  int nc = 0, ne = 0;
  foreach (var line in System.IO.File.ReadAllLines(W + "revit_conduits.tsv", System.Text.Encoding.UTF8)) {
    var c = line.Split('\t'); if (c[0] != TAG) continue;
    try {
      var a = new XYZ(D(c[5]) / F, D(c[6]) / F, D(c[7]) / F); var b = new XYZ(D(c[8]) / F, D(c[9]) / F, D(c[10]) / F);
      var cd = Autodesk.Revit.DB.Electrical.Conduit.Create(e, new ElementId(long.Parse(c[3])), a, b, lv.Id);
      cd.get_Parameter(BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM).Set(D(c[4]));
      SS(cd, "COMP_Disciplina", c[11]); SS(cd, "COMP_Trecho", c[1] + "." + c[2]); SS(cd, "COMP_Descrição", c[12]);
      cd.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(c[13]);
      SL(cd, "COMP_Recobrimento Mín", D(c[14])); SL(cd, "COMP_Recobrimento Exigido", D(c[15]));
      SL(cd, "COMP_Cota Topo Início", D(c[16])); SL(cd, "COMP_Cota Topo Fim", D(c[17]));
      SL(cd, "COMP_Terreno Início", D(c[18])); SL(cd, "COMP_Terreno Fim", D(c[19]));
      SS(cd, "COMP_Origem", c[20]); SS(cd, "COMP_Observação", (c[21] == "-" ? "" : c[21] + "; ") + "de: " + c[22] + " | até: " + c[23] + "; cota = premissa NBR 5410 sobre o terreno as built (IMP)");
      ids.AppendLine(TAG + "\tconduite\t" + c[1] + "." + c[2] + "\t" + cd.Id.Value); nc++;
    } catch (System.Exception ex) { ne++; if (ne < 6) log.AppendLine("ERRO " + c[1] + "." + c[2] + ": " + ex.Message); }
  }
  log.AppendLine("eletrodutos criados: " + nc + " | erros: " + ne);
  // 4) caixas (DirectShape, Modelos genéricos)
  int nx = 0, nxe = 0;
  foreach (var line in System.IO.File.ReadAllLines(W + "revit_caixas.tsv", System.Text.Encoding.UTF8)) {
    var c = line.Split('\t'); if (c[0] != TAG) continue;
    try {
      double cx = D(c[2]), cy = D(c[3]), hx = D(c[4]) / 200.0, hy = D(c[5]) / 200.0, ang = D(c[6]), ct = D(c[7]), cf = D(c[8]);
      var pts = new System.Collections.Generic.List<XYZ>();
      double[] us = { -1, 1, 1, -1 }, vs = { -1, -1, 1, 1 };
      for (int i = 0; i < 4; i++) { double u = us[i] * hx, v = vs[i] * hy; pts.Add(new XYZ((cx + u * System.Math.Cos(ang) - v * System.Math.Sin(ang)) / F, (cy + u * System.Math.Sin(ang) + v * System.Math.Cos(ang)) / F, cf / F)); }
      var loop = new CurveLoop(); for (int i = 0; i < 4; i++) loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]));
      var sol = GeometryCreationUtilities.CreateExtrusionGeometry(new System.Collections.Generic.List<CurveLoop> { loop }, XYZ.BasisZ, (ct - cf) / F);
      var ds = DirectShape.CreateElement(e, new ElementId(BuiltInCategory.OST_GenericModel));
      ds.SetShape(new System.Collections.Generic.List<GeometryObject> { sol });
      try { ds.SetName("ELE-CX " + c[1] + " " + c[4] + "x" + c[5]); } catch { }
      SS(ds, "COMP_Disciplina", TAG.StartsWith("EL") ? "ELE" : "TEL"); SS(ds, "COMP_Trecho", c[1]);
      SS(ds, "COMP_Descrição", "Caixa de passagem " + c[4] + "x" + c[5] + " cm - " + c[13]);
      SL(ds, "COMP_Cota Tampa (CT)", ct); SL(ds, "COMP_Cota Fundo (CF)", cf); SL(ds, "COMP_Profundidade", D(c[9]));
      SS(ds, "COMP_Origem", c[14]);
      SS(ds, "COMP_Observação", "esquemático (DirectShape, dimensões externas = nominais do projeto); CT = terreno as built; CF = eletroduto mais fundo - DE/2 - 0,10; posição: " + c[10] + "; eletrodutos: " + c[11] + (c[12] == "-" ? "" : "; " + c[12]));
      ids.AppendLine(TAG + "\tcaixa\t" + c[1] + "\t" + ds.Id.Value); nx++;
    } catch (System.Exception ex) { nxe++; if (nxe < 6) log.AppendLine("ERRO caixa " + c[1] + ": " + ex.Message); }
  }
  log.AppendLine("caixas criadas: " + nx + " | erros: " + nxe);
  if (ne + nxe > 0) { t.RollBack(); log.AppendLine("ROLLBACK (houve erro)"); return log.ToString(); }
  t.Commit();
}
System.IO.File.WriteAllText(W + "revit_ids_" + TAG + ".tsv", ids.ToString());
return log.ToString();
