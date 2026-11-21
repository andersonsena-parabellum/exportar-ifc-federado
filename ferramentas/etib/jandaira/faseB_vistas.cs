// Vistas de validação da Fase B no JAN-ELE (segundo plano): planta, 3 cortes e 3D; eletrodutos e caixas em laranja; vínculos em meio-tom na planta.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var log = new System.Text.StringBuilder();
System.Func<double, double, double, XYZ> P = (x, y, z) => new XYZ(x / F, y / F, z / F);
ViewFamilyType vPl = null, vSe = null, v3 = null;
foreach (ViewFamilyType t in new FilteredElementCollector(e).OfClass(typeof(ViewFamilyType))) {
  if (t.ViewFamily == ViewFamily.FloorPlan && vPl == null) vPl = t; if (t.ViewFamily == ViewFamily.Section && vSe == null) vSe = t; if (t.ViewFamily == ViewFamily.ThreeDimensional && v3 == null) v3 = t; }
Level niv = null; foreach (Level l in new FilteredElementCollector(e).OfClass(typeof(Level))) if (l.Name.StartsWith("ELE - NIVEL 0,00")) niv = l;
var vermelho = new OverrideGraphicSettings().SetProjectionLineColor(new Color(235, 120, 0)).SetProjectionLineWeight(7).SetCutLineColor(new Color(235, 120, 0)).SetCutLineWeight(7);
var roxo = new OverrideGraphicSettings().SetProjectionLineColor(new Color(130, 0, 170)).SetProjectionLineWeight(7).SetCutLineColor(new Color(130, 0, 170)).SetCutLineWeight(7);
var pci = new System.Collections.Generic.List<ElementId>(); var sdai = new System.Collections.Generic.List<ElementId>();
foreach (var bic in new[] { BuiltInCategory.OST_Conduit, BuiltInCategory.OST_ElectricalEquipment }) foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) pci.Add(el.Id);
System.Action<View, bool> Config = (v, meio) => {
  v.ViewTemplateId = ElementId.InvalidElementId; v.DetailLevel = ViewDetailLevel.Fine;
  foreach (var bic in new[] { BuiltInCategory.OST_Toposolid, BuiltInCategory.OST_Topography, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Levels }) {
    var c = Category.GetCategory(e, bic); if (c != null && v.CanCategoryBeHidden(c.Id)) v.SetCategoryHidden(c.Id, bic != BuiltInCategory.OST_Levels || v is ViewPlan || v is View3D); }
  if (meio) v.SetCategoryOverrides(new ElementId(BuiltInCategory.OST_RvtLinks), new OverrideGraphicSettings().SetHalftone(true));
  foreach (var id in pci) v.SetElementOverrides(id, vermelho); foreach (var id in sdai) v.SetElementOverrides(id, roxo); };
var criadas = new System.Collections.Generic.List<View>();
using (var t = new Transaction(e, "R01 Fase B - vistas de validacao")) {
  t.Start();
  var pl = ViewPlan.Create(e, vPl.Id, niv.Id); pl.Name = "ELE - R01 - FASE B - PLANTA DE VALIDACAO"; pl.Scale = 400;
  var vr = pl.GetViewRange(); vr.SetOffset(PlanViewPlane.TopClipPlane, 3 / F); vr.SetOffset(PlanViewPlane.CutPlane, 1.5 / F);
  vr.SetOffset(PlanViewPlane.BottomClipPlane, -3 / F); vr.SetOffset(PlanViewPlane.ViewDepthPlane, -3 / F); pl.SetViewRange(vr);
  pl.CropBoxActive = true; var cb = pl.CropBox; cb.Min = new XYZ(-5 / F, -12 / F, cb.Min.Z); cb.Max = new XYZ(142 / F, 145 / F, cb.Max.Z); pl.CropBox = cb; pl.CropBoxVisible = false;
  Config(pl, true); criadas.Add(pl);
  // cortes: (nome, ponto inicial, ponto final, lado de quem olha)
  var cortes = new[] { new { n = "ELE - R01 - FASE B - CORTE 1 - ESPINHA (ELE-I-28/29, DESVIO NA CX-SDAI-03)", a = P(66.2, 27, 0), b = P(66.2, 74, 0), lado = 1.0 },
                       new { n = "ELE - R01 - FASE B - CORTE 2 - ELE-I-31 (DESVIO NO PVE-10)", a = P(66.4, 76.0, 0), b = P(60.8, 95.6, 0), lado = 1.0 },
                       new { n = "ELE - R01 - FASE B - CORTE 3 - GUARITA (ELE-I-01, DESVIO NA SUBIDA DO HIDRANTE)", a = P(44.4, 1.5, 0), b = P(45.5, 8.0, 0), lado = 1.0 } };
  foreach (var c in cortes) {
    var dir = (c.b - c.a).Normalize(); var bz = new XYZ(dir.Y, -dir.X, 0) * c.lado; var bx = XYZ.BasisZ.CrossProduct(bz).Normalize();
    var tr = Transform.Identity; tr.Origin = (c.a + c.b) / 2 - bz * (2.6 / F); tr.BasisX = bx; tr.BasisY = XYZ.BasisZ; tr.BasisZ = bx.CrossProduct(XYZ.BasisZ);
    var box = new BoundingBoxXYZ(); box.Transform = tr; double L = c.a.DistanceTo(c.b) / 2;
    box.Min = new XYZ(-L, -2.5 / F, 0); box.Max = new XYZ(L, 1.5 / F, 5.2 / F);
    var s = ViewSection.CreateSection(e, vSe.Id, box); s.Name = c.n; s.Scale = 100; Config(s, false); criadas.Add(s);
  }
  var v = View3D.CreateIsometric(e, v3.Id); v.Name = "ELE - R01 - FASE B - 3D"; v.IsSectionBoxActive = true;
  var sbox = new BoundingBoxXYZ(); sbox.Min = P(-5, -12, -2.0); sbox.Max = P(142, 145, 1.5); v.SetSectionBox(sbox); Config(v, false); criadas.Add(v);
  t.Commit();
}
var ids = new System.Collections.Generic.List<ElementId>(); foreach (var v in criadas) { ids.Add(v.Id); log.AppendLine(v.Id + " | " + v.Name + (v is ViewSection ? " | direita=" + ((ViewSection)v).RightDirection.ToString() : "")); }
var opt = new ImageExportOptions { ExportRange = ExportRange.SetOfViews, FilePath = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\JAN_R01_faseB", ZoomType = ZoomFitType.FitToPage,
  PixelSize = 2400, ImageResolution = ImageResolution.DPI_150, HLRandWFViewsFileType = ImageFileType.PNG, ShadowViewsFileType = ImageFileType.PNG };
opt.SetViewsAndSheets(ids);
try { e.ExportImage(opt); log.AppendLine("imagens exportadas"); } catch (Exception x) { log.AppendLine("ExportImage: " + x.Message); }
e.Save();
return log.ToString();
