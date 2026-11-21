// Vistas de validação da Fase A no JAN-PCI (aberto em segundo plano): planta, 3 cortes e 3D, com terreno e pisos ocultos,
// hidrantes em vermelho e alarme em roxo (sobreposição por elemento), vínculos em meio-tom na planta. Exporta PNG para RELATORIOS.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("PCI nao aberto");
const double F = 0.3048; var log = new System.Text.StringBuilder();
System.Func<double, double, double, XYZ> P = (x, y, z) => new XYZ(x / F, y / F, z / F);
ViewFamilyType vPl = null, vSe = null, v3 = null;
foreach (ViewFamilyType t in new FilteredElementCollector(e).OfClass(typeof(ViewFamilyType))) {
  if (t.ViewFamily == ViewFamily.FloorPlan && vPl == null) vPl = t; if (t.ViewFamily == ViewFamily.Section && vSe == null) vSe = t; if (t.ViewFamily == ViewFamily.ThreeDimensional && v3 == null) v3 = t; }
Level niv = null; foreach (Level l in new FilteredElementCollector(e).OfClass(typeof(Level))) if (l.Name == "PCI - NIVEL 0,00") niv = l;
var vermelho = new OverrideGraphicSettings().SetProjectionLineColor(new Color(220, 0, 0)).SetProjectionLineWeight(8).SetCutLineColor(new Color(220, 0, 0)).SetCutLineWeight(8);
var roxo = new OverrideGraphicSettings().SetProjectionLineColor(new Color(130, 0, 170)).SetProjectionLineWeight(7).SetCutLineColor(new Color(130, 0, 170)).SetCutLineWeight(7);
var pci = new System.Collections.Generic.List<ElementId>(); var sdai = new System.Collections.Generic.List<ElementId>();
foreach (var bic in new[] { BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_PipeFitting }) foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) pci.Add(el.Id);
foreach (var bic in new[] { BuiltInCategory.OST_Conduit }) foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) sdai.Add(el.Id);
foreach (var id in new long[] { 4423534, 4423535, 4423536, 4423537, 4423538 }) sdai.Add(new ElementId(id));
System.Action<View, bool> Config = (v, meio) => {
  v.ViewTemplateId = ElementId.InvalidElementId; v.DetailLevel = ViewDetailLevel.Fine;
  foreach (var bic in new[] { BuiltInCategory.OST_Toposolid, BuiltInCategory.OST_Topography, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Levels }) {
    var c = Category.GetCategory(e, bic); if (c != null && v.CanCategoryBeHidden(c.Id)) v.SetCategoryHidden(c.Id, bic != BuiltInCategory.OST_Levels || v is ViewPlan || v is View3D); }
  if (meio) v.SetCategoryOverrides(new ElementId(BuiltInCategory.OST_RvtLinks), new OverrideGraphicSettings().SetHalftone(true));
  foreach (var id in pci) v.SetElementOverrides(id, vermelho); foreach (var id in sdai) v.SetElementOverrides(id, roxo); };
var criadas = new System.Collections.Generic.List<View>();
using (var t = new Transaction(e, "R01 Fase A - vistas de validacao")) {
  t.Start();
  var pl = ViewPlan.Create(e, vPl.Id, niv.Id); pl.Name = "PCI - R01 - FASE A - PLANTA DE VALIDACAO"; pl.Scale = 250;
  var vr = pl.GetViewRange(); vr.SetOffset(PlanViewPlane.TopClipPlane, 3 / F); vr.SetOffset(PlanViewPlane.CutPlane, 1.5 / F);
  vr.SetOffset(PlanViewPlane.BottomClipPlane, -3 / F); vr.SetOffset(PlanViewPlane.ViewDepthPlane, -3 / F); pl.SetViewRange(vr);
  pl.CropBoxActive = true; var cb = pl.CropBox; cb.Min = new XYZ(36 / F, -9 / F, cb.Min.Z); cb.Max = new XYZ(86 / F, 76 / F, cb.Max.Z); pl.CropBox = cb; pl.CropBoxVisible = false;
  Config(pl, true); criadas.Add(pl);
  // cortes: (nome, ponto inicial, ponto final, lado de quem olha)
  var cortes = new[] { new { n = "PCI - R01 - FASE A - CORTE 1 - ESPINHA (AH-02/04, ALARME A LESTE)", a = P(65.6, 4, 0), b = P(65.6, 74, 0), lado = 1.0 },
                       new { n = "PCI - R01 - FASE A - CORTE 2 - TRECHO SUL (AH-05/06, EL-03)", a = P(42, 7.6, 0), b = P(68.5, 7.6, 0), lado = -1.0 },
                       new { n = "PCI - R01 - FASE A - CORTE 3 - GUARITA (AH-08, EL-01)", a = P(44.4, 0.5, 0), b = P(44.4, 10, 0), lado = 1.0 } };
  foreach (var c in cortes) {
    var dir = (c.b - c.a).Normalize(); var bz = new XYZ(dir.Y, -dir.X, 0) * c.lado; var bx = XYZ.BasisZ.CrossProduct(bz).Normalize();
    var tr = Transform.Identity; tr.Origin = (c.a + c.b) / 2 + bz * (2.6 / F); tr.BasisX = bx; tr.BasisY = XYZ.BasisZ; tr.BasisZ = bx.CrossProduct(XYZ.BasisZ);
    var box = new BoundingBoxXYZ(); box.Transform = tr; double L = c.a.DistanceTo(c.b) / 2;
    box.Min = new XYZ(-L, -2.5 / F, 0); box.Max = new XYZ(L, 1.5 / F, 5.2 / F);
    var s = ViewSection.CreateSection(e, vSe.Id, box); s.Name = c.n; s.Scale = 100; Config(s, false); criadas.Add(s);
  }
  var v = View3D.CreateIsometric(e, v3.Id); v.Name = "PCI - R01 - FASE A - 3D"; v.IsSectionBoxActive = true;
  var sbox = new BoundingBoxXYZ(); sbox.Min = P(36, -9, -2.6); sbox.Max = P(86, 76, 1.5); v.SetSectionBox(sbox); Config(v, false); criadas.Add(v);
  t.Commit();
}
var ids = new System.Collections.Generic.List<ElementId>(); foreach (var v in criadas) { ids.Add(v.Id); log.AppendLine(v.Id + " | " + v.Name + (v is ViewSection ? " | direita=" + ((ViewSection)v).RightDirection.ToString() : "")); }
var opt = new ImageExportOptions { ExportRange = ExportRange.SetOfViews, FilePath = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\JAN_R01_faseA", ZoomType = ZoomFitType.FitToPage,
  PixelSize = 2400, ImageResolution = ImageResolution.DPI_150, HLRandWFViewsFileType = ImageFileType.PNG, ShadowViewsFileType = ImageFileType.PNG };
opt.SetViewsAndSheets(ids);
try { e.ExportImage(opt); log.AppendLine("imagens exportadas"); } catch (Exception x) { log.AppendLine("ExportImage: " + x.Message); }
e.Save();
return log.ToString();
