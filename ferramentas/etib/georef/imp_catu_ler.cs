// ETIB Catu — lê o IMP as built SEM salvar: terreno (Toposolid/Topografia), pisos, paredes, vínculos dos blocos e famílias com ponto,
// tudo em coordenadas COMPARTILHADAS (UTM do IMP) e metros. Saída em FERRAMENTAS\georef\work\CATU\imp\ (mesmo formato da Sátiro Dias).
// Abre o IMP em segundo plano se não estiver aberto e fecha sem salvar no fim (só o que este script abriu).
string ARQ = @"D:\Projeto Modelagem\ETIB-CATU\REFERENCIAS_RVT\IMP\24-049-CAU-RNV-ETIB-IMP.rvt";
string OUT = @"D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp\";
System.IO.Directory.CreateDirectory(OUT);
var app = document.Application; var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
Document e = null; bool abri = false;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) { e = app.OpenDocumentFile(ARQ); abri = true; }
var log = new System.Text.StringBuilder(); log.AppendLine("CATU-IMP-LER | " + e.Title + " | aberto agora: " + abri);
try {
  // ---- transformação interno -> compartilhado (testa os dois sentidos contra o ponto base do projeto)
  var pbp = BasePoint.GetProjectBasePoint(e); var sp = BasePoint.GetSurveyPoint(e);
  Transform T = e.ActiveProjectLocation.GetTotalTransform(); Transform Ti = T.Inverse;
  double d1 = Ti.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition), d2 = T.OfPoint(pbp.Position).DistanceTo(pbp.SharedPosition);
  Transform S = d1 <= d2 ? Ti : T;
  log.AppendLine("PBP interno " + pbp.Position + " compart. " + pbp.SharedPosition + " | SP compart. " + sp.SharedPosition + " | erro Ti " + d1.ToString("0.0000") + " T " + d2.ToString("0.0000"));
  var pp = e.ActiveProjectLocation.GetProjectPosition(XYZ.Zero);
  log.AppendLine("ProjectPosition(0): E/W " + (pp.EastWest * F).ToString("0.0000", ci) + " N/S " + (pp.NorthSouth * F).ToString("0.0000", ci) + " elev " + (pp.Elevation * F).ToString("0.0000", ci) + " ang " + (pp.Angle * 180 / System.Math.PI).ToString("0.000000", ci));
  System.Func<XYZ, string> P = q => { var w = S.OfPoint(q); return (w.X * F).ToString("0.0000", ci) + "," + (w.Y * F).ToString("0.0000", ci) + "," + (w.Z * F).ToString("0.0000", ci); };
  var opt = app.Create.NewGeometryOptions(); opt.DetailLevel = ViewDetailLevel.Fine; opt.ComputeReferences = false;
  // ---- triângulos
  var topo = new System.Text.StringBuilder("tag;id;a;b;c;nz\n"); var pisos = new System.Text.StringBuilder("tag;id;a;b;c;nz\n");
  int nt = 0, np = 0;
  System.Action<System.Text.StringBuilder, string, long, XYZ, XYZ, XYZ> Tri = (sb, tag, id, a, b, c) => {
    var n = (b - a).CrossProduct(c - a); double L = n.GetLength(); double nz = L > 1e-12 ? n.Z / L : 0;
    sb.Append(tag + ";" + id + ";" + P(a) + ";" + P(b) + ";" + P(c) + ";" + nz.ToString("0.000", ci) + "\n"); };
  System.Action<System.Text.StringBuilder, string, long, GeometryElement, Transform> Geo = null;
  Geo = (sb, tag, id, ge, tr) => {
    foreach (GeometryObject go in ge) {
      if (go is GeometryInstance) { var gi = (GeometryInstance)go; Geo(sb, tag, id, gi.GetSymbolGeometry(), tr.Multiply(gi.Transform)); }
      else if (go is Solid) { foreach (Face f in ((Solid)go).Faces) { var m = f.Triangulate(); for (int k = 0; k < m.NumTriangles; k++) { var t3 = m.get_Triangle(k);
            Tri(sb, tag, id, tr.OfPoint(t3.get_Vertex(0)), tr.OfPoint(t3.get_Vertex(1)), tr.OfPoint(t3.get_Vertex(2))); if (tag == "TOPO") nt++; else np++; } } }
      else if (go is Mesh) { var m = (Mesh)go; for (int k = 0; k < m.NumTriangles; k++) { var t3 = m.get_Triangle(k);
            Tri(sb, tag, id, tr.OfPoint(t3.get_Vertex(0)), tr.OfPoint(t3.get_Vertex(1)), tr.OfPoint(t3.get_Vertex(2))); if (tag == "TOPO") nt++; else np++; } }
    } };
  var resumo = new System.Collections.Generic.Dictionary<string, int>();
  foreach (Element el in new FilteredElementCollector(e).WhereElementIsNotElementType()) {
    if (el.Category == null) continue; var bic = (BuiltInCategory)el.Category.Id.Value;
    string tag = null;
    if (bic == BuiltInCategory.OST_Toposolid || bic == BuiltInCategory.OST_Topography) tag = "TOPO";
    else if (bic == BuiltInCategory.OST_Floors) tag = "PISO";
    if (tag == null) continue;
    var ge = el.get_Geometry(opt); if (ge == null) continue;
    Geo(tag == "TOPO" ? topo : pisos, tag, el.Id.Value, ge, Transform.Identity);
    string k2 = tag + " " + el.Id.Value + " " + el.Name; resumo[k2] = 1;
  }
  System.IO.File.WriteAllText(OUT + "imp_topo.csv", topo.ToString()); System.IO.File.WriteAllText(OUT + "imp_pisos.csv", pisos.ToString());
  log.AppendLine("triangulos TOPO " + nt + " | PISO " + np);
  foreach (var k in resumo.Keys) log.AppendLine("  " + k);
  // ---- paredes
  var par = new System.Text.StringBuilder("id;nome;p0;p1;zmin;zmax;espessura\n"); int nw = 0;
  foreach (Wall w in new FilteredElementCollector(e).OfClass(typeof(Wall))) {
    var lc = w.Location as LocationCurve; if (lc == null) continue; var bb = w.get_BoundingBox(null); if (bb == null) continue;
    par.Append(w.Id.Value + ";" + w.Name + ";" + P(lc.Curve.GetEndPoint(0)) + ";" + P(lc.Curve.GetEndPoint(1)) + ";" + (S.OfPoint(bb.Min).Z * F).ToString("0.000", ci) + ";" + (S.OfPoint(bb.Max).Z * F).ToString("0.000", ci) + ";" + (w.Width * F).ToString("0.000", ci) + "\n"); nw++; }
  System.IO.File.WriteAllText(OUT + "imp_paredes.csv", par.ToString());
  // ---- vínculos (blocos as built)
  var vin = new System.Text.StringBuilder("id;nome;tipo;origem;bx;ang_graus\n"); int nv = 0;
  foreach (RevitLinkInstance li in new FilteredElementCollector(e).OfClass(typeof(RevitLinkInstance))) {
    var tr = S.Multiply(li.GetTotalTransform()); var bx = tr.BasisX; var tipo = e.GetElement(li.GetTypeId());
    vin.Append(li.Id.Value + ";" + li.Name + ";" + (tipo != null ? tipo.Name : "") + ";" + (tr.Origin.X * F).ToString("0.0000", ci) + "," + (tr.Origin.Y * F).ToString("0.0000", ci) + "," + (tr.Origin.Z * F).ToString("0.0000", ci) + ";"
      + bx.X.ToString("0.000000000", ci) + "," + bx.Y.ToString("0.000000000", ci) + ";" + (System.Math.Atan2(bx.Y, bx.X) * 180 / System.Math.PI).ToString("0.000000", ci) + "\n"); nv++; }
  System.IO.File.WriteAllText(OUT + "imp_vinculos.csv", vin.ToString());
  // ---- famílias com ponto (postes, hidrantes, quadros, mobiliário etc.)
  var out2 = new System.Text.StringBuilder("id;categoria;nome;familia;ponto;rot_graus\n"); int no = 0;
  foreach (FamilyInstance fi in new FilteredElementCollector(e).OfClass(typeof(FamilyInstance))) {
    var lp = fi.Location as LocationPoint; if (lp == null) continue;
    double rot = 0; try { rot = lp.Rotation * 180 / System.Math.PI; } catch { }
    out2.Append(fi.Id.Value + ";" + (fi.Category != null ? fi.Category.Name : "") + ";" + fi.Name + ";" + (fi.Symbol != null ? fi.Symbol.FamilyName : "") + ";" + P(lp.Point) + ";" + rot.ToString("0.000", ci) + "\n"); no++; }
  System.IO.File.WriteAllText(OUT + "imp_outros.csv", out2.ToString());
  // ---- níveis
  var niv = new System.Text.StringBuilder("id;nome;elevacao_interna_m\n");
  foreach (Level lv in new FilteredElementCollector(e).OfClass(typeof(Level))) niv.Append(lv.Id.Value + ";" + lv.Name + ";" + (lv.Elevation * F).ToString("0.000", ci) + "\n");
  System.IO.File.WriteAllText(OUT + "imp_niveis.csv", niv.ToString());
  log.AppendLine("paredes " + nw + " | vinculos " + nv + " | familias com ponto " + no);
} finally {
  if (abri) { e.Close(false); log.AppendLine("IMP fechado sem salvar"); }
}
System.IO.File.WriteAllText(OUT + "imp_log.txt", log.ToString());
return log.ToString();
