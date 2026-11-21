// ETIB Olindina — estrutura as built do BA5 (fundação FUN e estrutura ECC de REFERENCIAS_RVT\BA5): triângulos de cada peça
// (fundação, viga/baldrame, pilar, laje/piso), em coordenadas INTERNAS do RVT e em metros, mais a transformação interno -> compartilhado
// do próprio arquivo. A posição na implantação sai do vínculo do BA5 no IMP (onn_estrutura.py). Cada arquivo é aberto desanexado,
// lido e fechado SEM salvar. Saída: FERRAMENTAS\georef\work\OLINDINA\imp\ba5_<FUN|ECC>_tri.csv + ba5_estrutura_log.txt
string OUT = @"D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\imp\";
string DIR = @"D:\Projeto Modelagem\ETIB-OLINDINA\REFERENCIAS_RVT\BA5\";
var arqs = new string[] { "25-XXX-XXX-XXX-ETIB-BA5-PE-FUN-001-MOD-R00.rvt", "25-XXX-XXX-XXX-ETIB-BA5-PE-ECC-001-MOD-R00.rvt" };
var app = document.Application; var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
var cats = new System.Collections.Generic.Dictionary<BuiltInCategory, string> {
  { BuiltInCategory.OST_StructuralFoundation, "fundacao" }, { BuiltInCategory.OST_StructuralFraming, "viga" },
  { BuiltInCategory.OST_StructuralColumns, "pilar" }, { BuiltInCategory.OST_Floors, "laje/piso" } };
var log = new System.Text.StringBuilder("ONN-BA5-EST\n");
foreach (var nome in arqs) {
  string arq = DIR + nome; Document d = null; bool abri = false;
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
    log.AppendLine(nome + " | interno->compartilhado: origem " + (S.Origin.X * F).ToString("0.0000", ci) + "," + (S.Origin.Y * F).ToString("0.0000", ci) + "," + (S.Origin.Z * F).ToString("0.0000", ci)
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
    string tag = nome.Contains("-FUN-") ? "FUN" : "ECC";
    System.IO.File.WriteAllText(OUT + "ba5_" + tag + "_tri.csv", sb.ToString());
    var partes = new System.Collections.Generic.List<string>(); foreach (var k in cnt.Keys) partes.Add(k + " " + cnt[k]);
    log.AppendLine("  peças: " + string.Join(", ", partes));
    var niv2 = new System.Text.StringBuilder();
    foreach (Level lv in new FilteredElementCollector(d).OfClass(typeof(Level))) niv2.Append(lv.Name + "=" + (lv.Elevation * F).ToString("0.000", ci) + " ");
    log.AppendLine("  níveis: " + niv2.ToString());
  } catch (System.Exception ex) { log.AppendLine("  ERRO " + nome + ": " + ex.Message); }
  finally { if (abri && d != null) { try { d.Close(false); log.AppendLine("  fechado sem salvar"); } catch { } } }
}
System.IO.File.WriteAllText(OUT + "ba5_estrutura_log.txt", log.ToString());
return log.ToString();
