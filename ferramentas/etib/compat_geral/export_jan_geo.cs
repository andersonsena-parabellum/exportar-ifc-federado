// Parte 2 de 2: com o modelo já aberto pela parte 1, grava <DISC>_segs.tsv (tubos/eletrodutos) e <DISC>_mesh.tsv (sólidos) em coord. internas (m) e fecha sem salvar.
string ARQ = @"@@ARQ@@"; string DISC = "@@DISC@@"; string OUT = @"@@OUT@@"; int MODO = @@MODO@@; bool FECHAR = @@FECHAR@@;
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
var app = document.Application; Document e = null;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("modelo nao aberto: " + ARQ);
var t0 = System.DateTime.Now; var opt = new Options(); opt.DetailLevel = ViewDetailLevel.Fine;
System.Func<double, string> S = v => (v * F).ToString("0.####", ci);
System.Func<Element, BuiltInParameter, string> BP = (el, b) => { var p = el.get_Parameter(b); return p == null ? "" : (p.AsString() ?? p.AsValueString() ?? "").Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' '); };
System.Action<GeometryElement, System.Text.StringBuilder, int[]> W = null;
System.Action<XYZ, System.Text.StringBuilder> A = (q, sb) => sb.Append(S(q.X)).Append(',').Append(S(q.Y)).Append(',').Append(S(q.Z)).Append(',');
W = (ge, sb, n) => {
  foreach (GeometryObject go in ge) {
    if (go is Solid) { var so = (Solid)go; if (so.Volume <= 1e-9) continue;
      foreach (Face f in so.Faces) { var mm = f.Triangulate(0.3); for (int i = 0; i < mm.NumTriangles; i++) { var t = mm.get_Triangle(i); for (int k = 0; k < 3; k++) A(t.get_Vertex(k), sb); n[0]++; } } }
    else if (go is Mesh && MODO == 2) { var mm = (Mesh)go; for (int i = 0; i < mm.NumTriangles; i++) { var t = mm.get_Triangle(i); for (int k = 0; k < 3; k++) A(t.get_Vertex(k), sb); n[0]++; } }
    else if (go is GeometryInstance) W(((GeometryInstance)go).GetInstanceGeometry(), sb, n);
  }
};
int ns = 0, nm = 0, nt = 0;
if (MODO == 0) {
  var segs = new System.Text.StringBuilder();
  foreach (var bic in new[] { BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_Conduit, BuiltInCategory.OST_FlexPipeCurves }) {
    foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
      var lc = el.Location as LocationCurve; if (lc == null) continue;
      var a = lc.Curve.GetEndPoint(0); var b = lc.Curve.GetEndPoint(1);
      double de = 0; var pd = el.get_Parameter(BuiltInParameter.RBS_PIPE_OUTER_DIAMETER); if (pd == null || pd.AsDouble() <= 0) pd = el.get_Parameter(BuiltInParameter.RBS_CONDUIT_OUTER_DIAM_PARAM); if (pd != null) de = pd.AsDouble();
      string dn = BP(el, BuiltInParameter.RBS_PIPE_DIAMETER_PARAM); if (dn == "") dn = BP(el, BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM);
      segs.AppendLine(string.Join("\t", new[] { DISC, el.Id.ToString(), el.Category.Name, (e.GetElement(el.GetTypeId())?.Name ?? ""), BP(el, BuiltInParameter.RBS_SYSTEM_NAME_PARAM), BP(el, BuiltInParameter.RBS_SYSTEM_CLASSIFICATION_PARAM),
        S(de), S(a.X), S(a.Y), S(a.Z), S(b.X), S(b.Y), S(b.Z), dn, BP(el, BuiltInParameter.ALL_MODEL_MARK), BP(el, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS), BP(el, BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM) }));
      ns++;
    }
  }
  System.IO.File.WriteAllText(OUT + DISC + "_segs.tsv", segs.ToString(), new System.Text.UTF8Encoding(false));
}
var L = new System.Collections.Generic.List<BuiltInCategory> { BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory, BuiltInCategory.OST_ConduitFitting, BuiltInCategory.OST_GenericModel,
  BuiltInCategory.OST_PlumbingFixtures, BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_ElectricalEquipment,
  BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_FireAlarmDevices, BuiltInCategory.OST_PlumbingEquipment, BuiltInCategory.OST_FireProtection, BuiltInCategory.OST_Sprinklers,
  BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_CableTray, BuiltInCategory.OST_LightingFixtures };
if (MODO == 1) L = new System.Collections.Generic.List<BuiltInCategory> { BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Walls };
if (MODO == 2) L = new System.Collections.Generic.List<BuiltInCategory> { BuiltInCategory.OST_Toposolid, BuiltInCategory.OST_Topography, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Walls, BuiltInCategory.OST_Stairs, BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Site };
var mesh = new System.Text.StringBuilder();
foreach (var bic in L) {
  foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
    var ge = el.get_Geometry(opt); if (ge == null) continue;
    var sb = new System.Text.StringBuilder(); var n = new int[1]; W(ge, sb, n); if (n[0] == 0) continue;
    string nome = el.Name; if (el is FamilyInstance) nome = ((FamilyInstance)el).Symbol.FamilyName + " : " + el.Name;
    mesh.AppendLine(string.Join("\t", new[] { DISC, el.Id.ToString(), el.Category.Name, nome.Replace('\t', ' '), BP(el, BuiltInParameter.ALL_MODEL_MARK), BP(el, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS),
      BP(el, BuiltInParameter.RBS_SYSTEM_NAME_PARAM), n[0].ToString(), sb.ToString().TrimEnd(',') }));
    nm++; nt += n[0];
  }
}
System.IO.File.WriteAllText(OUT + DISC + "_mesh.tsv", mesh.ToString(), new System.Text.UTF8Encoding(false));
if (FECHAR) e.Close(false);
return "GEO " + DISC + " ok: segs " + ns + " | solidos " + nm + " (" + nt + " tri) | " + (System.DateTime.Now - t0).TotalSeconds.ToString("0", ci) + " s";
