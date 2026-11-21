// Vistas de validação da contenção no MODELAGEM-CONTENCAO.rvt (segundo plano): planta 1:200, 3D, 4 cortes A–D, folha CNT-VAL-01.
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.Title == "MODELAGEM-CONTENCAO") e = d;
if (e == null) return "CNT não aberto";
var log = new System.Text.StringBuilder();
System.Func<double, double> M = v => v / F;
var segs = new string[][] {   // seção, p0x, p0y, ux, uy, nx, ny, L (de work/cnt_face.json)
  new []{"A","-21.6307","-100.3650","0.99474","-0.102428","-0.102428","-0.99474","53.33"},
  new []{"B","31.4188","-105.8275","0.99474","-0.102428","-0.102428","-0.99474","39.50"},
  new []{"C","70.7110","-109.8734","0.99474","-0.102429","-0.102429","-0.99474","19.80"},
  new []{"D","90.4069","-111.9014","0.99474","-0.102428","-0.102428","-0.99474","5.111"} };
System.Func<string, View> FindV = n => { foreach (View v in new FilteredElementCollector(e).OfClass(typeof(View))) if (!v.IsTemplate && v.Name == n) return v; return null; };
var topo = Category.GetCategory(e, BuiltInCategory.OST_Toposolid);
using (var t = new Transaction(e, "CNT - vistas de validação")) {
  t.Start();
  // planta
  ViewPlan vp = FindV("CNT - IMPLANTAÇÃO - VALIDAÇÃO CAD") as ViewPlan;
  if (vp == null) { vp = ViewPlan.Create(e, new ElementId(49552L), new ElementId(438217L)); vp.Name = "CNT - IMPLANTAÇÃO - VALIDAÇÃO CAD"; }
  vp.ViewTemplateId = ElementId.InvalidElementId; vp.Scale = 200; vp.DetailLevel = ViewDetailLevel.Fine;
  var vr = vp.GetViewRange();
  vr.SetOffset(PlanViewPlane.CutPlane, M(1.2)); vr.SetOffset(PlanViewPlane.TopClipPlane, M(6));
  vr.SetOffset(PlanViewPlane.BottomClipPlane, M(-5)); vr.SetOffset(PlanViewPlane.ViewDepthPlane, M(-5));
  vp.SetViewRange(vr);
  vp.CropBoxActive = true; vp.CropBoxVisible = true;
  var bb = new BoundingBoxXYZ(); bb.Min = new XYZ(M(-30), M(-122), M(-50)); bb.Max = new XYZ(M(102), M(-84), M(50)); vp.CropBox = bb;
  if (vp.CanCategoryBeHidden(topo.Id)) vp.SetCategoryHidden(topo.Id, true);
  var tops = new System.Collections.Generic.List<ElementId>(); foreach (ImportInstance ii in new FilteredElementCollector(e).OfClass(typeof(ImportInstance))) if (ii.Category != null && ii.Category.Name.Contains("TOP-001")) tops.Add(ii.Id);
  if (tops.Count > 0) try { vp.HideElements(tops); } catch { }
  log.AppendLine("planta " + vp.Id);
  // 3D
  View3D v3 = FindV("CNT - 3D") as View3D;
  if (v3 == null) { v3 = View3D.CreateIsometric(e, new ElementId(49559L)); v3.Name = "CNT - 3D"; }
  v3.ViewTemplateId = ElementId.InvalidElementId; v3.DetailLevel = ViewDetailLevel.Fine;
  var sb3 = new BoundingBoxXYZ(); sb3.Min = new XYZ(M(-30), M(-120), M(133)); sb3.Max = new XYZ(M(102), M(-88), M(145)); v3.SetSectionBox(sb3); v3.IsSectionBoxActive = true;
  try { v3.get_Parameter(BuiltInParameter.MODEL_GRAPHICS_STYLE).Set(3); } catch { }
  log.AppendLine("3D " + v3.Id);
  // cortes no meio de cada seção (olhando ao longo do muro; sul à direita)
  var cortes = new System.Collections.Generic.List<ViewSection>();
  foreach (var s in segs) {
    string nome = "CNT - CORTE " + s[0] + "-" + s[0];
    var vs = FindV(nome) as ViewSection;
    double L = double.Parse(s[7], ci);
    var u = new XYZ(double.Parse(s[3], ci), double.Parse(s[4], ci), 0).Normalize(); var n = new XYZ(double.Parse(s[5], ci), double.Parse(s[6], ci), 0).Normalize();
    var p = new XYZ(M(double.Parse(s[1], ci)), M(double.Parse(s[2], ci)), 0) + u * M(L / 2);
    var tr = Transform.Identity; tr.Origin = p; tr.BasisX = n; tr.BasisY = XYZ.BasisZ; tr.BasisZ = n.CrossProduct(XYZ.BasisZ);
    var box = new BoundingBoxXYZ(); box.Transform = tr; box.Min = new XYZ(M(-5), M(135.5), 0); box.Max = new XYZ(M(5), M(143.5), M(1.0));
    if (vs != null) e.Delete(vs.Id);
    vs = ViewSection.CreateSection(e, new ElementId(49554L), box); vs.Name = nome;
    vs.ViewTemplateId = ElementId.InvalidElementId; vs.Scale = 50; vs.DetailLevel = ViewDetailLevel.Fine;
    cortes.Add(vs); log.AppendLine("corte " + s[0] + " " + vs.Id);
  }
  // folha
  ViewSheet sh = null; foreach (ViewSheet x in new FilteredElementCollector(e).OfClass(typeof(ViewSheet))) if (x.SheetNumber == "CNT-VAL-01") sh = x;
  if (sh != null) e.Delete(sh.Id);
  sh = ViewSheet.Create(e, new ElementId(4428L)); sh.SheetNumber = "CNT-VAL-01"; sh.Name = "CONTENÇÃO - VALIDAÇÃO - PLANTA, CORTES E 3D";
  // A1: 841 x 594 mm (área útil aproximada)
  System.Func<double, double> MM = v => v / 304.8;
  try { Viewport.Create(e, sh.Id, vp.Id, new XYZ(MM(360), MM(450), 0)); } catch (System.Exception ex) { log.AppendLine("vp planta: " + ex.Message); }
  for (int i = 0; i < cortes.Count; i++) { try { Viewport.Create(e, sh.Id, cortes[i].Id, new XYZ(MM(110 + i * 175), MM(250), 0)); } catch (System.Exception ex) { log.AppendLine("vp corte: " + ex.Message); } }
  try { Viewport.Create(e, sh.Id, v3.Id, new XYZ(MM(380), MM(100), 0)); } catch (System.Exception ex) { log.AppendLine("vp 3D: " + ex.Message); }
  log.AppendLine("folha " + sh.Id);
  t.Commit();
}
e.Save(); log.AppendLine("SALVO");
return log.ToString();
