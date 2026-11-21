// ETIB Olindina — contorno dos prédios existentes do IMP as built (famílias de Massa: ESCOLA, REFEITORIO, ABRIGO RESIDUOS, CASA GÁS…):
// triângulos das faces de baixo de cada massa, em coordenadas COMPARTILHADAS (UTM) e metros, para a regra "só rede externa".
// Abre o IMP em segundo plano e fecha sem salvar. Saída: FERRAMENTAS\georef\work\OLINDINA\imp\imp_massas.csv
string ARQ = @"D:\Projeto Modelagem\ETIB-OLINDINA\REFERENCIAS_RVT\IMP\24-049-ONN-CTO-ETIB-IMP.rvt";
string OUT = @"D:\Projeto Modelagem\FERRAMENTAS\georef\work\OLINDINA\imp\";
var app = document.Application; var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
Document e = null; bool abri = false;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) { e = app.OpenDocumentFile(ARQ); abri = true; }
var log = new System.Text.StringBuilder("ONN-IMP-MASSAS | " + e.Title + "\n");
try {
  var pbp = BasePoint.GetProjectBasePoint(e);
  Transform T = e.ActiveProjectLocation.GetTotalTransform(); Transform Ti = T.Inverse;
  Transform S = Ti.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition) <= T.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition) ? Ti : T;
  System.Func<XYZ, string> P = q => { var w = S.OfPoint(q); return (w.X * F).ToString("0.0000", ci) + "," + (w.Y * F).ToString("0.0000", ci) + "," + (w.Z * F).ToString("0.0000", ci); };
  var opt = app.Create.NewGeometryOptions(); opt.DetailLevel = ViewDetailLevel.Fine;
  var sb = new System.Text.StringBuilder("id;nome;a;b;c\n"); int n = 0;
  foreach (FamilyInstance fi in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_Mass).WhereElementIsNotElementType()) {
    var ge = fi.get_Geometry(opt); if (ge == null) continue;
    System.Action<GeometryElement, Transform> Geo = null;
    Geo = (g, tr) => {
      foreach (GeometryObject go in g) {
        if (go is GeometryInstance) { var gi = (GeometryInstance)go; Geo(gi.GetSymbolGeometry(), tr.Multiply(gi.Transform)); }
        else if (go is Solid && ((Solid)go).Volume > 1e-9) {
          foreach (Face f in ((Solid)go).Faces) { var m = f.Triangulate(); for (int k = 0; k < m.NumTriangles; k++) { var t3 = m.get_Triangle(k);
            XYZ a = tr.OfPoint(t3.get_Vertex(0)), b = tr.OfPoint(t3.get_Vertex(1)), c = tr.OfPoint(t3.get_Vertex(2));
            var nn = (b - a).CrossProduct(c - a); if (nn.GetLength() < 1e-12 || nn.Z / nn.GetLength() > -0.5) continue;
            sb.Append(fi.Id.Value + ";" + fi.Name.Replace(";", ",") + ";" + P(a) + ";" + P(b) + ";" + P(c) + "\n"); n++; } } }
      } };
    Geo(ge, Transform.Identity);
  }
  System.IO.File.WriteAllText(OUT + "imp_massas.csv", sb.ToString());
  log.AppendLine("triângulos de base " + n);
} finally { if (abri) { e.Close(false); log.AppendLine("IMP fechado sem salvar"); } }
return log.ToString();
