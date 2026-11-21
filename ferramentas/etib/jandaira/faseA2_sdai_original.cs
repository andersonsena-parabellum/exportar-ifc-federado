// Fase A, revisão 2 (18/10, usuário: "só profundidade"): alarme volta ao traçado ORIGINAL e só desce.
// Espinha EL-04 a -1,18 e EL-05 a -1,13 (por baixo das caixas do ELE na cota da NBR); EL-03 a -1,28; chegada à guarita a -1,03; ramais EL-06/07 na cota original.
// Caixas CX-SDAI-01/03/04 voltam 1,4 m a oeste; profundidades = eletroduto mais fundo + 0,10. CX-SDAI-02 continua 1,0 m a noroeste (fora do DRE-046).
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("PCI nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
System.Func<long, Element> G = id => e.GetElement(new ElementId(id));
System.Func<double, double, double, XYZ> P = (x, y, z) => new XYZ(x / F, y / F, z / F);
System.Action<Element, string> Nota = (el, t) => { var p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p == null || p.IsReadOnly) return;
  var s = p.AsString() ?? ""; int k = s.IndexOf(" | R01 18/10"); if (k >= 0) s = s.Substring(0, k); p.Set((s + " | R01 18/10 (rev.2, só profundidade): " + t).Trim(' ', '|')); };
System.Action<long, XYZ, XYZ, string> Eletro = (id, a, b, t) => { var el = G(id); ((LocationCurve)el.Location).Curve = Line.CreateBound(a, b); Nota(el, t); };
System.Func<string, Element> PorMarca = m => { foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsNotElementType()) if ((el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? "") == m) return el; return null; };
double X = 66.1, zO = -0.68;
using (var t = new Transaction(e, "R01 Fase A rev.2 - alarme no tracado original")) {
  t.Start();
  foreach (var id in new long[] { 4423534, 4423536, 4423537 }) ElementTransformUtils.MoveElement(e, new ElementId(id), new XYZ(-1.4 / F, 0, 0));
  var prof = new System.Collections.Generic.Dictionary<long, double> { { 4423534, 1.15 }, { 4423536, 1.20 }, { 4423537, 1.40 }, { 4423535, 1.30 } };
  foreach (var kv in prof) { G(kv.Key).LookupParameter("Profundidade").Set(kv.Value / F); Nota(G(kv.Key), "posicao original, profundidade " + kv.Value.ToString("0.00", ci)); }
  Nota(G(4423535), "1,0 m a noroeste (sai de cima do DRE-046), profundidade 1,30");
  Eletro(4423549, P(X, 35.5, -1.18), P(X, 7.64, -1.18), "tracado original, eixo a -1,18 (sob as caixas do ELE)");
  Eletro(4423552, P(X, 36.3, -1.13), P(X, 71.31, -1.13), "tracado original, eixo a -1,13 (sob as caixas do ELE)");
  Eletro(4423555, P(82.3, 71.71, zO), P(66.5, 71.71, zO), "tracado e cota originais");
  Eletro(4423558, P(77.405, 35.9, zO), P(66.5, 35.9, zO), "tracado e cota originais");
  Eletro(4423546, P(44.47, 7.24, -1.28), P(65.7, 7.24, -1.28), "tracado original, eixo a -1,28 (sob as caixas da drenagem)");
  Eletro(4423540, P(44.07, 6.84, -1.03), P(44.07, 1.0, -1.03), "tracado original, eixo a -1,03");
  Eletro(4423629, P(44.07, 1.0, 1.45), P(44.07, 1.0, -1.03), "subida ate a central (base a -1,03)");
  var a = PorMarca("PCI-EL-01b"); ((LocationCurve)a.Location).Curve = Line.CreateBound(P(43.563, 7.547, -1.03), P(44.07, 6.84, -1.03));
  var b = PorMarca("PCI-EL-03a"); ((LocationCurve)b.Location).Curve = Line.CreateBound(P(43.763, 7.947, -1.28), P(44.47, 7.24, -1.28));
  t.Commit();
}
var sb = new System.Text.StringBuilder();
foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsNotElementType()) {
  var c = ((LocationCurve)el.Location).Curve; var p0 = c.GetEndPoint(0); var p1 = c.GetEndPoint(1);
  sb.AppendLine((el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? "") + " (" + (p0.X * F).ToString("0.00", ci) + ";" + (p0.Y * F).ToString("0.00", ci) + ";" + (p0.Z * F).ToString("0.00", ci) + ") -> (" + (p1.X * F).ToString("0.00", ci) + ";" + (p1.Y * F).ToString("0.00", ci) + ";" + (p1.Z * F).ToString("0.00", ci) + ")"); }
foreach (var id in new long[] { 4423534, 4423535, 4423536, 4423537, 4423538 }) { var bb = G(id).get_BoundingBox(null); sb.AppendLine(id + " x " + (bb.Min.X * F).ToString("0.00", ci) + "-" + (bb.Max.X * F).ToString("0.00", ci) + " y " + (bb.Min.Y * F).ToString("0.00", ci) + "-" + (bb.Max.Y * F).ToString("0.00", ci) + " z " + (bb.Min.Z * F).ToString("0.00", ci) + "/" + (bb.Max.Z * F).ToString("0.00", ci)); }
e.Save();
return sb.ToString();
