// Pegadas em planta dos elementos estruturais dos vínculos (FUN/ECC/EMT) -> work/estrut_pegadas.csv
// Linha: bloco;arquivo;categoria;id;zmin;zmax;x,y x,y ... (m, coordenadas internas do MODELAGEM-ELETRICA = UTM - (561500, 8658000))
Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.Title == "MODELAGEM-ELETRICA") e = d;
if (e == null) e = document.Application.OpenDocumentFile(@"D:\Projeto Modelagem\ETIB-ALAGOINHAS\MODELAGEM-ELETRICA.rvt");
var opt = new Options(); opt.DetailLevel = ViewDetailLevel.Coarse;
var cats = new BuiltInCategory[] { BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors };
var sw = new System.IO.StreamWriter(@"D:\Projeto Modelagem\FERRAMENTAS\eletrica\work\estrut_pegadas.csv", false, new System.Text.UTF8Encoding(false));
var log = new System.Text.StringBuilder(); var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
foreach (RevitLinkInstance li in new FilteredElementCollector(e).OfClass(typeof(RevitLinkInstance))) {
  var ld = li.GetLinkDocument(); if (ld == null) continue;
  string nm = ld.Title; if (!(nm.Contains("-FUN-") || nm.Contains("-ECC-") || nm.Contains("-EMT-"))) continue;
  string bloco = nm.Split('-')[5];
  var T = li.GetTotalTransform(); int k = 0;
  foreach (var bic in cats) {
    foreach (Element el in new FilteredElementCollector(ld).OfCategory(bic).WhereElementIsNotElementType()) {
      var ge = el.get_Geometry(opt); if (ge == null) continue;
      var set = new System.Collections.Generic.HashSet<string>(); double z0 = 1e9, z1 = -1e9;
      var stack = new System.Collections.Generic.List<GeometryObject>(); foreach (var g in ge) stack.Add(g);
      while (stack.Count > 0) {
        var g = stack[stack.Count - 1]; stack.RemoveAt(stack.Count - 1);
        var s = g as Solid;
        if (s != null && s.Volume > 1e-9) {
          foreach (Edge ed in s.Edges) foreach (XYZ p0 in ed.Tessellate()) {
            var p = T.OfPoint(p0); z0 = System.Math.Min(z0, p.Z); z1 = System.Math.Max(z1, p.Z);
            set.Add((p.X * F).ToString("0.000", ci) + "," + (p.Y * F).ToString("0.000", ci));
          }
          continue;
        }
        var gi = g as GeometryInstance; if (gi != null) foreach (var g2 in gi.GetInstanceGeometry()) stack.Add(g2);
      }
      if (set.Count == 0) continue;
      sw.WriteLine(bloco + ";" + nm + ";" + bic.ToString() + ";" + el.Id.Value + ";" + (z0 * F).ToString("0.000", ci) + ";" + (z1 * F).ToString("0.000", ci) + ";" + string.Join(" ", set));
      k++;
    }
  }
  log.AppendLine(nm + ": " + k);
}
sw.Close();
return log.ToString();
