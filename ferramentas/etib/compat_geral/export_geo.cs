// Exporta a geometria de UMA disciplina para o clash geral (R02). Troque ALVO/DISC/ARQ a cada execução.
// Saída: RELATORIOS\compat_R02\geo\<DISC>_segs.tsv (tubos/eletrodutos) e <DISC>_mesh.tsv (demais sólidos, triangulados), em metros (coord. internas).
// Com ESTRUT=true exporta também os vínculos de estrutura/IMP do documento (transformação total) para EST_mesh.tsv.
string ALVO = "MODELAGEM-ELETRICA"; string DISC = "ELE"; string ARQ = @"D:\Projeto Modelagem\ETIB-ALAGOINHAS\MODELAGEM-ELETRICA.rvt"; bool ESTRUT = true;
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
string OUT = @"D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS\compat_R02\geo\"; System.IO.Directory.CreateDirectory(OUT);
var app = document.Application; Document e = null; bool abriu = false;
foreach (Document d in app.Documents) if (!d.IsLinked && d.Title == ALVO) e = d;
if (e == null) { e = app.OpenDocumentFile(ARQ); abriu = true; }
var log = new System.Text.StringBuilder(); var opt = new Options(); opt.DetailLevel = ViewDetailLevel.Fine; opt.ComputeReferences = false;
System.Func<double, string> S = v => (v * F).ToString("0.###", ci);
System.Func<Element, string, string> P = (el, n) => { var p = el.LookupParameter(n); return p == null ? "" : (p.AsString() ?? p.AsValueString() ?? ""); };
// triangula um elemento (com transformação opcional); devolve "x,y,z,x,y,z,..." de todos os triângulos
System.Func<Element, Transform, System.Text.StringBuilder, int> Tri = null;
System.Action<GeometryElement, Transform, System.Text.StringBuilder, int[]> Walk = null;
Walk = (ge, tf, sb, cnt) => {
  foreach (GeometryObject go in ge) {
    if (go is Solid) { var so = (Solid)go; if (so.Volume <= 1e-9) continue;
      foreach (Face f in so.Faces) { var m = f.Triangulate(0.3); for (int i = 0; i < m.NumTriangles; i++) { var t = m.get_Triangle(i);
        for (int k = 0; k < 3; k++) { var q = t.get_Vertex(k); if (tf != null) q = tf.OfPoint(q); sb.Append(S(q.X)).Append(',').Append(S(q.Y)).Append(',').Append(S(q.Z)).Append(','); } cnt[0]++; } } }
    else if (go is GeometryInstance) { var gi = (GeometryInstance)go; Walk(gi.GetInstanceGeometry(), tf, sb, cnt); }
  }
};
Tri = (el, tf, sb) => { var ge = el.get_Geometry(opt); if (ge == null) return 0; var cnt = new int[1]; Walk(ge, tf, sb, cnt); return cnt[0]; };
// 1) segmentos
var segs = new System.Text.StringBuilder(); int nseg = 0;
foreach (var bic in new[] { BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_Conduit, BuiltInCategory.OST_FlexPipeCurves }) {
  foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
    var lc = el.Location as LocationCurve; if (lc == null) continue;
    var a = lc.Curve.GetEndPoint(0); var b = lc.Curve.GetEndPoint(1);
    double de = 0; var pd = el.get_Parameter(BuiltInParameter.RBS_PIPE_OUTER_DIAMETER); if (pd == null || pd.AsDouble() <= 0) pd = el.get_Parameter(BuiltInParameter.RBS_CONDUIT_OUTER_DIAM_PARAM); if (pd != null) de = pd.AsDouble();
    string sis = ""; var ps = el.get_Parameter(BuiltInParameter.RBS_SYSTEM_NAME_PARAM); if (ps != null) sis = ps.AsString() ?? "";
    string tipo = e.GetElement(el.GetTypeId())?.Name ?? "";
    segs.AppendLine(string.Join("\t", new[] { DISC, el.Id.ToString(), el.Category.Name, tipo, sis, P(el, "COMP_Trecho"), S(de), S(a.X), S(a.Y), S(a.Z), S(b.X), S(b.Y), S(b.Z), P(el, "COMP_Descrição").Replace('\t', ' ') }));
    nseg++;
  }
}
System.IO.File.WriteAllText(OUT + DISC + "_segs.tsv", segs.ToString(), new System.Text.UTF8Encoding(false));
// 2) malhas (sólidos que não são tubo/eletroduto)
var cats = new[] { BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory, BuiltInCategory.OST_ConduitFitting, BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_PlumbingFixtures,
  BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_Walls, BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_ElectricalEquipment,
  BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_FireAlarmDevices, BuiltInCategory.OST_PlumbingEquipment };
var mesh = new System.Text.StringBuilder(); int nmesh = 0, ntri = 0;
foreach (var bic in cats) {
  foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
    if (el is ElementType) continue;
    var sb = new System.Text.StringBuilder(); int nt = Tri(el, null, sb); if (nt == 0) continue;
    string nome = el.Name; if (el is FamilyInstance) nome = ((FamilyInstance)el).Symbol.FamilyName + " : " + el.Name;
    mesh.AppendLine(string.Join("\t", new[] { DISC, el.Id.ToString(), el.Category.Name, nome.Replace('\t', ' '), P(el, "COMP_Trecho"), P(el, "COMP_Descrição").Replace('\t', ' '), nt.ToString(), sb.ToString().TrimEnd(',') }));
    nmesh++; ntri += nt;
  }
}
System.IO.File.WriteAllText(OUT + DISC + "_mesh.tsv", mesh.ToString(), new System.Text.UTF8Encoding(false));
log.AppendLine(DISC + ": segmentos " + nseg + " | sólidos " + nmesh + " (" + ntri + " triângulos)");
// 3) estruturas e IMP pelos vínculos
if (ESTRUT) {
  var est = new System.Text.StringBuilder(); int ne = 0, nte = 0;
  var catsE = new[] { BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Walls };
  var catsI = new[] { BuiltInCategory.OST_Walls, BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_PlumbingFixtures };
  foreach (RevitLinkInstance li in new FilteredElementCollector(e).OfClass(typeof(RevitLinkInstance))) {
    var ld = li.GetLinkDocument(); if (ld == null) { log.AppendLine("vínculo não carregado: " + li.Name); continue; }
    var tf = li.GetTotalTransform(); bool imp = ld.Title.Contains("-IMP_");
    string bloco = imp ? "IMP" : ld.Title.Split('-').Length > 5 ? ld.Title.Split('-')[5] : ld.Title;
    foreach (var bic in imp ? catsI : catsE) {
      foreach (Element el in new FilteredElementCollector(ld).OfCategory(bic).WhereElementIsNotElementType()) {
        var bb = el.get_BoundingBox(null); if (bb == null) continue;
        var zmin = tf.OfPoint(bb.Min).Z * F; if (zmin > 140.5) continue;   // só o que está no terreno ou abaixo
        var sb = new System.Text.StringBuilder(); int nt = Tri(el, tf, sb); if (nt == 0) continue;
        string nome = el.Name; if (el is FamilyInstance) nome = ((FamilyInstance)el).Symbol.FamilyName + " : " + el.Name;
        est.AppendLine(string.Join("\t", new[] { "EST", bloco + ":" + el.Id.ToString(), el.Category.Name, nome.Replace('\t', ' '), ld.Title, "", nt.ToString(), sb.ToString().TrimEnd(',') }));
        ne++; nte += nt;
      }
    }
  }
  System.IO.File.WriteAllText(OUT + "EST_mesh.tsv", est.ToString(), new System.Text.UTF8Encoding(false));
  log.AppendLine("EST/IMP: sólidos " + ne + " (" + nte + " triângulos)");
}
if (abriu) e.Close(false);
return log.ToString();
