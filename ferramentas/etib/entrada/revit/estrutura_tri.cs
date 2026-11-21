// Entrada da escola — estrutura as built pela FORMA REAL (mesmo método do olindina/revit/onn_ba5_estrutura.cs): triângulos de cada
// peça (fundação, viga/baldrame, pilar, laje/piso) em coordenadas INTERNAS do RVT e em metros + transformação interno -> compartilhado.
// A posição na implantação sai do vínculo do bloco no IMP (imp_vinculos.csv da escola). Abre desanexado, lê e fecha SEM salvar.
// Marcadores trocados pelo entrada/revit_conv.py: __ARQ__ (RVT) e __OUT__ (CSV de saída).
string arq = @"__ARQ__"; string outf = @"__OUT__";
var app = document.Application; var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
var cats = new System.Collections.Generic.Dictionary<BuiltInCategory, string> {
  { BuiltInCategory.OST_StructuralFoundation, "fundacao" }, { BuiltInCategory.OST_StructuralFraming, "viga" },
  { BuiltInCategory.OST_StructuralColumns, "pilar" }, { BuiltInCategory.OST_Floors, "laje/piso" } };
var log = new System.Text.StringBuilder("EST-TRI " + System.IO.Path.GetFileName(arq) + "\n");
Document d = null; bool abri = false;
try {
  foreach (Document x in app.Documents) if (!x.IsLinked && x.PathName == arq) d = x;
  if (d == null) {
    var mp = ModelPathUtils.ConvertUserVisiblePathToModelPath(arq); var oo = new OpenOptions();
    try { oo.DetachFromCentralOption = DetachFromCentralOption.DetachAndDiscardWorksets; } catch { }
    try { d = app.OpenDocumentFile(mp, oo); } catch { d = app.OpenDocumentFile(arq); }
    abri = true;
  }
  var pbp = BasePoint.GetProjectBasePoint(d);
  Transform T = d.ActiveProjectLocation.GetTotalTransform(); Transform Ti = T.Inverse;
  double d1 = Ti.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition), d2 = T.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition);
  Transform S = d1 <= d2 ? Ti : T;
  log.AppendLine("interno->compartilhado: origem " + (S.Origin.X * F).ToString("0.0000", ci) + "," + (S.Origin.Y * F).ToString("0.0000", ci) + "," + (S.Origin.Z * F).ToString("0.0000", ci)
    + " ang " + (System.Math.Atan2(S.BasisX.Y, S.BasisX.X) * 180 / System.Math.PI).ToString("0.000000", ci));
  var opt = app.Create.NewGeometryOptions(); opt.DetailLevel = ViewDetailLevel.Fine; opt.ComputeReferences = false;
  var sb = new System.Text.StringBuilder("id;categoria;tipo;nivel;ax;ay;az;bx;by;bz;cx;cy;cz\n");
  var cnt = new System.Collections.Generic.Dictionary<string, int>();
  foreach (var kv in cats) {
    foreach (Element el in new FilteredElementCollector(d).OfCategory(kv.Key).WhereElementIsNotElementType()) {
      var ge = el.get_Geometry(opt); if (ge == null) continue;
      string tipo = ""; var et = d.GetElement(el.GetTypeId()); if (et != null) tipo = et.Name.Replace(";", ",");
      string niv = ""; var lv = d.GetElement(el.LevelId) as Level; if (lv != null) niv = lv.Name.Replace(";", ",");
      int nt = 0;
      System.Action<GeometryElement, Transform> Geo = null;
      Geo = (g, tr) => {
        foreach (GeometryObject go in g) {
          if (go is GeometryInstance) { var gi = (GeometryInstance)go; Geo(gi.GetSymbolGeometry(), tr.Multiply(gi.Transform)); }
          else if (go is Solid && ((Solid)go).Volume > 1e-9) {
            foreach (Face f in ((Solid)go).Faces) { var m = f.Triangulate(); for (int k = 0; k < m.NumTriangles; k++) { var t3 = m.get_Triangle(k);
              sb.Append(el.Id.Value + ";" + kv.Value + ";" + tipo + ";" + niv);
              for (int v = 0; v < 3; v++) { var p = tr.OfPoint(t3.get_Vertex(v)); sb.Append(";" + (p.X * F).ToString("0.0000", ci) + ";" + (p.Y * F).ToString("0.0000", ci) + ";" + (p.Z * F).ToString("0.0000", ci)); }
              sb.Append("\n"); nt++; } } }
        } };
      Geo(ge, Transform.Identity);
      if (nt > 0) cnt[kv.Value] = (cnt.ContainsKey(kv.Value) ? cnt[kv.Value] : 0) + 1;
    }
  }
  System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(outf));
  System.IO.File.WriteAllText(outf, sb.ToString());
  var partes = new System.Collections.Generic.List<string>(); foreach (var k in cnt.Keys) partes.Add(k + " " + cnt[k]);
  log.AppendLine("peças: " + string.Join(", ", partes));
  var niv2 = new System.Text.StringBuilder();
  foreach (Level lv in new FilteredElementCollector(d).OfClass(typeof(Level))) niv2.Append(lv.Name + "=" + (lv.Elevation * F).ToString("0.000", ci) + " ");
  log.AppendLine("níveis: " + niv2.ToString());
} catch (System.Exception ex) { log.AppendLine("ERRO: " + ex.Message); }
finally { if (abri && d != null) { try { d.Close(false); log.AppendLine("fechado sem salvar"); } catch { } } }
System.IO.File.WriteAllText(outf + ".log.txt", log.ToString());
return log.ToString();
