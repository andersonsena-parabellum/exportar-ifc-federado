// Fase A (R01) — alarme (SDAI) do JAN-PCI: espinha 1,4 m a leste (+x), fora da faixa do ELE, na cota atual (eixo -0,68);
// trecho sul EL-03 a -1,30 (por baixo das caixas da drenagem e dos hidrantes); chegada à guarita a -0,95;
// CX-SDAI-02 sai de cima do coletor DRE-046 (1,0 m a noroeste) e CX-SDAI-02/04 ficam mais fundas. Eletrodutos ponta a ponta, sem conexão.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("PCI nao aberto");
const double F = 0.3048; var log = new System.Text.StringBuilder(); var ci = System.Globalization.CultureInfo.InvariantCulture;
System.Func<long, Element> G = id => e.GetElement(new ElementId(id));
System.Func<double, double, double, XYZ> P = (x, y, z) => new XYZ(x / F, y / F, z / F);
System.Action<Element, string> Nota = (el, t) => { var p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p != null && !p.IsReadOnly) p.Set(((p.AsString() ?? "") + " | " + t).Trim(' ', '|')); };
System.Action<long, XYZ, XYZ, string> Eletro = (id, a, b, t) => { var el = G(id); ((LocationCurve)el.Location).Curve = Line.CreateBound(a, b); Nota(el, "R01 18/10: " + t); };
double X = 67.5, zE = -0.68, zS = -1.30, zG = -0.95;           // espinha nova (x), cotas do eixo
using (var t = new Transaction(e, "R01 Fase A - alarme")) {
  t.Start();
  // caixas: espinha +1,4 m em x; CX-SDAI-02 1,0 m a noroeste; profundidades
  foreach (var id in new long[] { 4423534, 4423536, 4423537 }) ElementTransformUtils.MoveElement(e, new ElementId(id), new XYZ(1.4 / F, 0, 0));
  ElementTransformUtils.MoveElement(e, new ElementId(4423535L), new XYZ(-0.7071 / F, 0.7071 / F, 0));
  G(4423535).LookupParameter("Profundidade").Set(1.35 / F); G(4423537).LookupParameter("Profundidade").Set(1.40 / F);
  Nota(G(4423535), "R01 18/10: 1,0 m a noroeste (fora do DRE-046), prof. 1,35"); Nota(G(4423537), "R01 18/10: espinha 1,4 m a leste, prof. 1,40");
  Nota(G(4423534), "R01 18/10: espinha 1,4 m a leste"); Nota(G(4423536), "R01 18/10: espinha 1,4 m a leste");
  // espinha e ramais (cota atual)
  Eletro(4423549, P(X, 35.5, zE), P(X, 7.64, zE), "espinha 1,4 m a leste (fora da faixa do ELE)");
  Eletro(4423552, P(X, 36.3, zE), P(X, 71.31, zE), "espinha 1,4 m a leste (fora da faixa do ELE)");
  Eletro(4423555, P(82.3, 71.71, zE), P(X + 0.4, 71.71, zE), "ramal norte ate a nova espinha");
  Eletro(4423558, P(77.405, 35.9, zE), P(X + 0.4, 35.9, zE), "ramal da casa de bombas ate a nova espinha");
  // trecho sul mais fundo, da CX-SDAI-02 nova até a CX-SDAI-04 nova
  Eletro(4423546, P(44.47, 7.24, zS), P(X - 0.4, 7.24, zS), "trecho sul a 1,30 (sob caixas DRE e hidrantes)");
  // guarita: EL-01 (até a central) e EL-02 (entrada do BP4) a 0,95; subida EL-10 acompanha
  Eletro(4423540, P(44.07, 6.84, zG), P(44.07, 1.0, zG), "chegada a guarita a 0,95");
  Eletro(4423543, P(44.07, 8.9, zG), P(43.563, 8.347, zG), "liga a CX-SDAI-02 nova, a 0,95");
  Eletro(4423629, P(44.07, 1.0, 1.45), P(44.07, 1.0, zG), "subida ate a central (base a 0,95)");
  // pedaços novos ligando a CX-SDAI-02 nova
  var el1 = (Autodesk.Revit.DB.Electrical.Conduit)G(4423540); var tp = el1.GetTypeId(); var lv = el1.ReferenceLevel.Id; double dn = el1.Diameter;
  var n1 = Autodesk.Revit.DB.Electrical.Conduit.Create(e, tp, P(43.563, 7.547, zG), P(44.07, 6.84, zG), lv);
  var n2 = Autodesk.Revit.DB.Electrical.Conduit.Create(e, tp, P(43.763, 7.947, zS), P(44.47, 7.24, zS), lv);
  foreach (var n in new[] { n1, n2 }) { n.get_Parameter(BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM).Set(dn); }
  n1.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set("PCI-EL-01b"); n2.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set("PCI-EL-03a");
  Nota(n1, "SDAI - eletroduto PEAD 2\" (DE60) enterrado: CX-SDAI-02 (nova) -> EL-01 | R01 18/10");
  Nota(n2, "SDAI - eletroduto PEAD 2\" (DE60) enterrado: CX-SDAI-02 (nova) -> EL-03 a 1,30 | R01 18/10");
  t.Commit();
}
var sb = new System.Text.StringBuilder();
foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsNotElementType()) {
  var c = ((LocationCurve)el.Location).Curve; var a = c.GetEndPoint(0); var b = c.GetEndPoint(1);
  sb.AppendLine((el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? "") + " (" + (a.X * F).ToString("0.00", ci) + ";" + (a.Y * F).ToString("0.00", ci) + ";" + (a.Z * F).ToString("0.00", ci) + ") -> (" + (b.X * F).ToString("0.00", ci) + ";" + (b.Y * F).ToString("0.00", ci) + ";" + (b.Z * F).ToString("0.00", ci) + ") DE " + (((MEPCurve)el).get_Parameter(BuiltInParameter.RBS_CONDUIT_OUTER_DIAM_PARAM).AsDouble() * F * 1000).ToString("0", ci));
}
foreach (var id in new long[] { 4423534, 4423535, 4423536, 4423537, 4423538 }) { var bb = G(id).get_BoundingBox(null); sb.AppendLine(id + " bb x " + (bb.Min.X * F).ToString("0.00", ci) + "-" + (bb.Max.X * F).ToString("0.00", ci) + " y " + (bb.Min.Y * F).ToString("0.00", ci) + "-" + (bb.Max.Y * F).ToString("0.00", ci) + " z " + (bb.Min.Z * F).ToString("0.00", ci) + "/" + (bb.Max.Z * F).ToString("0.00", ci)); }
e.Save();
return sb.ToString();
