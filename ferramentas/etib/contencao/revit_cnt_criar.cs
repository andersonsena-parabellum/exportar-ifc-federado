// Cria a contenção (DirectShape) no MODELAGEM-CONTENCAO.rvt, aberto em segundo plano. Entrada: work/cnt_pecas.tsv (cnt_geometria.py)
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
string P = @"D:\Projeto Modelagem\"; string W = P + @"FERRAMENTAS\contencao\work\";
var app = document.Application;
Document e = null; foreach (Document d in app.Documents) if (!d.IsLinked && d.Title == "MODELAGEM-CONTENCAO") e = d;
if (e == null) e = app.OpenDocumentFile(P + @"ETIB-ALAGOINHAS\MODELAGEM-CONTENCAO.rvt");
var log = new System.Text.StringBuilder(); var ids = new System.Text.StringBuilder();
System.Func<string, double> D = s => double.Parse(s, ci);
System.Action<Element, string, string> SS = (el, n, v) => { var p = el.LookupParameter(n); if (p != null && !p.IsReadOnly) p.Set(v); };
System.Action<Element, string, double> SL = (el, n, v) => { var p = el.LookupParameter(n); if (p != null && !p.IsReadOnly) p.Set(v / F); };
string ORIGEM = "24-049-ALH-SLJ-ETIB-IMP-PE-CNT-001-DGE-R00 + CONTENÇÃO_MEMÓRIA-R0";
using (var t = new Transaction(e, "CNT - contenção (DirectShape)")) {
  t.Start();
  // 1) COMP_* também em Paredes, Fundação estrutural e Modelos genéricos
  var cats = new BuiltInCategory[] { BuiltInCategory.OST_Walls, BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_GenericModel };
  var it = e.ParameterBindings.ForwardIterator(); var defs = new System.Collections.Generic.List<Definition>(); var bds = new System.Collections.Generic.List<ElementBinding>();
  while (it.MoveNext()) { if (it.Key.Name.StartsWith("COMP_")) { defs.Add(it.Key); bds.Add((ElementBinding)it.Current); } }
  int nb = 0;
  for (int i = 0; i < defs.Count; i++) { bool ch = false; foreach (var bc in cats) { var c = Category.GetCategory(e, bc); if (!bds[i].Categories.Contains(c)) { bds[i].Categories.Insert(c); ch = true; } } if (ch) { e.ParameterBindings.ReInsert(defs[i], bds[i]); nb++; } }
  log.AppendLine("COMP_* encontrados " + defs.Count + " | bindings ampliados " + nb);
  // 2) limpa reexecução
  var old = new System.Collections.Generic.List<ElementId>();
  foreach (DirectShape ds0 in new FilteredElementCollector(e).OfClass(typeof(DirectShape))) { var p = ds0.LookupParameter("COMP_Disciplina"); if (p != null && p.AsString() == "CNT") old.Add(ds0.Id); }
  if (old.Count > 0) e.Delete(old); log.AppendLine("apagados (reexecução): " + old.Count);
  var catWall = new ElementId(BuiltInCategory.OST_Walls); if (!DirectShape.IsValidCategoryId(catWall, e)) { catWall = new ElementId(BuiltInCategory.OST_GenericModel); log.AppendLine("Paredes não aceita DirectShape -> Modelos genéricos"); }
  var catSap = new ElementId(BuiltInCategory.OST_StructuralFoundation); if (!DirectShape.IsValidCategoryId(catSap, e)) { catSap = new ElementId(BuiltInCategory.OST_GenericModel); log.AppendLine("Fundação não aceita DirectShape -> Modelos genéricos"); }
  var barb = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<GeometryObject>>();
  var barbN = new System.Collections.Generic.Dictionary<string, int>();
  int nm = 0, ns = 0, nerr = 0;
  foreach (var line in System.IO.File.ReadAllLines(W + "cnt_pecas.tsv", System.Text.Encoding.UTF8)) {
    var c = line.Split('\t'); if (c.Length < 9) continue;
    try {
      var g = c[8].Split(';');
      var p0 = new XYZ(D(g[0]) / F, D(g[1]) / F, 0); var u = new XYZ(D(g[2]), D(g[3]), 0).Normalize(); var n = new XYZ(D(g[4]), D(g[5]), 0).Normalize();
      double d0 = D(c[3]) / F, d1 = D(c[4]) / F, z0 = D(c[5]) / F;
      if (c[0] == "BARB") {
        var s = c[7].Split(','); double s0 = D(s[0]) / F, s1 = D(s[1]) / F, r = D(c[6]) / 2 / F;
        var C0 = p0 + u * d0 + n * s0 + XYZ.BasisZ * z0;
        var lp = new CurveLoop();
        lp.Append(Arc.Create(C0, r, 0, Math.PI, u, XYZ.BasisZ)); lp.Append(Arc.Create(C0, r, Math.PI, 2 * Math.PI, u, XYZ.BasisZ));
        var sol = GeometryCreationUtilities.CreateExtrusionGeometry(new System.Collections.Generic.List<CurveLoop> { lp }, n, s1 - s0);
        if (!barb.ContainsKey(c[1])) { barb[c[1]] = new System.Collections.Generic.List<GeometryObject>(); barbN[c[1]] = 0; }
        barb[c[1]].Add(sol); barbN[c[1]]++;
        continue;
      }
      var O = p0 + u * d0;
      var pts = new System.Collections.Generic.List<XYZ>();
      foreach (var q in c[7].Split(';')) { var a = q.Split(','); pts.Add(O + n * (D(a[0]) / F) + XYZ.BasisZ * (z0 + D(a[1]) / F)); }
      var loop = new CurveLoop(); for (int i = 0; i < pts.Count; i++) loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % pts.Count]));
      var solid = GeometryCreationUtilities.CreateExtrusionGeometry(new System.Collections.Generic.List<CurveLoop> { loop }, u, d1 - d0);
      bool muro = c[0] == "MURO";
      var ds = DirectShape.CreateElement(e, muro ? catWall : catSap);
      ds.SetShape(new System.Collections.Generic.List<GeometryObject> { solid });
      try { ds.SetName(c[2]); } catch { }
      double H = D(c[6]), zb = D(c[5]);
      SS(ds, "COMP_Disciplina", "CNT"); SS(ds, "COMP_Trecho", c[2]); SS(ds, "COMP_Origem", ORIGEM);
      if (muro) {
        SS(ds, "COMP_Descrição", "Muro de gravidade em alvenaria de pedra argamassada (traço 1:3) - seção " + c[1] + " H=" + H.ToString("0.00", ci) + " m - face frontal no lote, aterro ao sul");
        SL(ds, "COMP_Cota Topo Início", zb + H); SL(ds, "COMP_Cota Fundo (CF)", zb);
      } else {
        SS(ds, "COMP_Descrição", "Sapata do muro de gravidade (alvenaria de pedra) - seção " + c[1] + " - " + (D(c[7].Split(';')[1].Split(',')[0]) - D(c[7].Split(';')[0].Split(',')[0])).ToString("0.00", ci) + " x 0,50 m");
        SL(ds, "COMP_Cota Topo Início", zb); SL(ds, "COMP_Cota Fundo (CF)", zb - H);
      }
      SL(ds, "COMP_Terreno Início", D(c[9])); SL(ds, "COMP_Terreno Fim", D(c[10]));
      SS(ds, "COMP_Observação", "PREMISSA (aprovada 16/10/2026): projeto sem cotas; topo da sapata (A-C) / base do fuste (D) = menor terreno do IMP as built 0,5 m à frente da face no trecho; topo = base + H. O IMP não representa o desnível do muro.");
      ids.AppendLine(c[0] + "\t" + c[2] + "\t" + ds.Id.Value);
      if (muro) nm++; else ns++;
    } catch (System.Exception ex) { nerr++; if (nerr < 6) log.AppendLine("ERRO " + c[2] + ": " + ex.Message); }
  }
  foreach (var kv in barb) {
    var ds = DirectShape.CreateElement(e, new ElementId(BuiltInCategory.OST_GenericModel));
    ds.SetShape(kv.Value);
    try { ds.SetName("CNT-BARBACÃS seção " + kv.Key); } catch { }
    SS(ds, "COMP_Disciplina", "CNT"); SS(ds, "COMP_Trecho", "CNT-BARB-" + kv.Key); SS(ds, "COMP_Origem", ORIGEM);
    SS(ds, "COMP_Descrição", "Barbacãs Ø100 (PVC ranhurado ou PEAD perfurado) da seção " + kv.Key + " - " + barbN[kv.Key] + " unidades");
    SS(ds, "COMP_Observação", "fileiras a 0,55/1,05/1,55/2,05 m acima da base do fuste, espaçamento do projeto, fileiras alternadas defasadas de meio espaçamento (inferido da elevação)");
    ids.AppendLine("BARB\tCNT-BARB-" + kv.Key + "\t" + ds.Id.Value);
  }
  log.AppendLine("muros " + nm + " | sapatas " + ns + " | barbacãs " + string.Join(", ", System.Linq.Enumerable.Select(barbN, kv => kv.Key + "=" + kv.Value)) + " | erros " + nerr);
  t.Commit();
}
System.IO.File.WriteAllText(W + "revit_ids_cnt.tsv", ids.ToString());
e.Save();
log.AppendLine("SALVO " + e.PathName);
return log.ToString();
