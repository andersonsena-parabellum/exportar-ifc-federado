// Vistas de validação da Fase E (drenagem do campo 50x30) no JAN-DRE (segundo plano): vincula o CPS EL _GEO (coordenadas compartilhadas),
// planta do campo, 2 cortes e 3D; peças do CPS em laranja, o resto em meio-tom. Exporta PNG em RELATORIOS\JAN_R01_faseD - *.png.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-DRE.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("DRE nao aberto");
string DWG = @"D:\Projeto Modelagem\ETIB-JANDAIRA\CAD_GEORREFERENCIADO\24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01_GEO.dwg";
const double F = 0.3048; var log = new System.Text.StringBuilder();
System.Func<double, double, double, XYZ> P = (x, y, z) => new XYZ(x / F, y / F, z / F);
ViewFamilyType vPl = null, vSe = null, v3 = null;
foreach (ViewFamilyType t in new FilteredElementCollector(e).OfClass(typeof(ViewFamilyType))) {
  if (t.ViewFamily == ViewFamily.FloorPlan && vPl == null) vPl = t; if (t.ViewFamily == ViewFamily.Section && vSe == null) vSe = t; if (t.ViewFamily == ViewFamily.ThreeDimensional && v3 == null) v3 = t; }
Level niv = null; foreach (Level l in new FilteredElementCollector(e).OfClass(typeof(Level))) if (l.Id.Value == 7627049) niv = l;
var laranja = new OverrideGraphicSettings().SetProjectionLineColor(new Color(235, 120, 0)).SetProjectionLineWeight(8).SetCutLineColor(new Color(235, 120, 0)).SetCutLineWeight(8);
var meio = new OverrideGraphicSettings().SetHalftone(true);
var cps = new System.Collections.Generic.List<ElementId>(); var outros = new System.Collections.Generic.List<ElementId>();
foreach (var bic in new[] { BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_PlumbingFixtures }) foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
  var c = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); var m = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
  bool eh = (c != null && (c.AsString() ?? "").Contains("campo society")) || (m != null && ((m.AsString() ?? "").StartsWith("DRE-CPS") || (m.AsString() ?? "") == "CX-43"));
  var fi = el as FamilyInstance; if (!eh && fi != null && fi.MEPModel != null && fi.MEPModel.ConnectorManager != null) { foreach (Connector k in fi.MEPModel.ConnectorManager.Connectors) foreach (Connector o in k.AllRefs) { if (o.Owner == null) continue; var mm = o.Owner.get_Parameter(BuiltInParameter.ALL_MODEL_MARK); if (mm != null && (mm.AsString() ?? "").StartsWith("DRE-CPS")) eh = true; } }
  (eh ? cps : outros).Add(el.Id); }
System.Action<View> Config = v => {
  v.ViewTemplateId = ElementId.InvalidElementId; v.DetailLevel = ViewDetailLevel.Fine;
  foreach (var bic in new[] { BuiltInCategory.OST_Toposolid, BuiltInCategory.OST_Topography, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Levels }) {
    var c = Category.GetCategory(e, bic); if (c != null && v.CanCategoryBeHidden(c.Id)) v.SetCategoryHidden(c.Id, bic != BuiltInCategory.OST_Levels || v is ViewPlan || v is View3D); }
  v.SetCategoryOverrides(new ElementId(BuiltInCategory.OST_RvtLinks), meio);
  foreach (var id in outros) v.SetElementOverrides(id, meio); foreach (var id in cps) v.SetElementOverrides(id, laranja); };
var criadas = new System.Collections.Generic.List<View>();
using (var t = new Transaction(e, "R01 Fase E - vistas de validacao da drenagem do campo")) {
  t.Start();
  var pl = ViewPlan.Create(e, vPl.Id, niv.Id); pl.Name = "DRE - R01 - FASE E - CAMPO - PLANTA DE VALIDACAO"; pl.Scale = 200;
  var vr = pl.GetViewRange(); vr.SetOffset(PlanViewPlane.TopClipPlane, 3 / F); vr.SetOffset(PlanViewPlane.CutPlane, 1.5 / F);
  vr.SetOffset(PlanViewPlane.BottomClipPlane, -3 / F); vr.SetOffset(PlanViewPlane.ViewDepthPlane, -3 / F); pl.SetViewRange(vr);
  pl.CropBoxActive = true; var cb = pl.CropBox; cb.Min = new XYZ(50 / F, 86 / F, cb.Min.Z); cb.Max = new XYZ(132 / F, 142 / F, cb.Max.Z); pl.CropBox = cb; pl.CropBoxVisible = false;
  var op = new DWGImportOptions { Placement = ImportPlacement.Shared, ThisViewOnly = false, Unit = ImportUnit.Meter, ColorMode = ImportColorMode.Preserved };
  ElementId lid; try { e.Link(DWG, op, pl, out lid); log.AppendLine("DWG vinculado " + lid); } catch (Exception x) { log.AppendLine("Link DWG: " + x.Message); }
  Config(pl); criadas.Add(pl);
  var cortes = new[] { new { n = "DRE - R01 - FASE E - CAMPO - CORTE 1 - ESPINHA (ATE A CX-43)", a = P(51.5, 118.1, 0), b = P(115.5, 111.8, 0) },
                       new { n = "DRE - R01 - FASE E - CAMPO - CORTE 2 - TRANSVERSAL (CX-16 / CX-41)", a = P(88.8, 90, 0), b = P(91.4, 138, 0) } };
  foreach (var c in cortes) {
    var dir = (c.b - c.a).Normalize(); var bz = new XYZ(dir.Y, -dir.X, 0); var bx = XYZ.BasisZ.CrossProduct(bz).Normalize();
    var tr = Transform.Identity; tr.Origin = (c.a + c.b) / 2 - bz * (2.6 / F); tr.BasisX = bx; tr.BasisY = XYZ.BasisZ; tr.BasisZ = bx.CrossProduct(XYZ.BasisZ);
    var box = new BoundingBoxXYZ(); box.Transform = tr; double L = c.a.DistanceTo(c.b) / 2;
    box.Min = new XYZ(-L, -2.5 / F, 0); box.Max = new XYZ(L, 1.5 / F, 5.2 / F);
    var s = ViewSection.CreateSection(e, vSe.Id, box); s.Name = c.n; s.Scale = 100; Config(s); criadas.Add(s);
  }
  var v = View3D.CreateIsometric(e, v3.Id); v.Name = "DRE - R01 - FASE E - CAMPO - 3D"; v.IsSectionBoxActive = true;
  var sbox = new BoundingBoxXYZ(); sbox.Min = P(50, 86, -2.0); sbox.Max = P(132, 142, 1.5); v.SetSectionBox(sbox); Config(v); criadas.Add(v);
  t.Commit();
}
var ids = new System.Collections.Generic.List<ElementId>(); foreach (var v in criadas) { ids.Add(v.Id); log.AppendLine(v.Id + " | " + v.Name); }
log.AppendLine("pecas do CPS realcadas: " + cps.Count);
var opt = new ImageExportOptions { ExportRange = ExportRange.SetOfViews, FilePath = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\JAN_R01_faseE", ZoomType = ZoomFitType.FitToPage,
  PixelSize = 2400, ImageResolution = ImageResolution.DPI_150, HLRandWFViewsFileType = ImageFileType.PNG, ShadowViewsFileType = ImageFileType.PNG };
opt.SetViewsAndSheets(ids);
try { e.ExportImage(opt); log.AppendLine("imagens exportadas"); } catch (Exception x) { log.AppendLine("ExportImage: " + x.Message); }
e.Save();
return log.ToString();
