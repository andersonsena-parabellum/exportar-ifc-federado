// Fase A (R01) — hidrantes do JAN-PCI nas profundidades do relatório PCI R00 (eixo a 1,30/1,20/1,10 m da cota 147,00), com degraus de 45° (AH-04/05 e AH-06/08).
// O JAN-PCI está aberto em segundo plano: transação própria e Save no fim. Sem LINQ (o plugin não importa System.Linq).
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("PCI nao aberto");
const double F = 0.3048; var log = new System.Text.StringBuilder(); var ci = System.Globalization.CultureInfo.InvariantCulture;
System.Func<long, Element> G = id => e.GetElement(new ElementId(id));
System.Func<long[], System.Collections.Generic.List<ElementId>> L = ids => { var r = new System.Collections.Generic.List<ElementId>(); foreach (var i in ids) r.Add(new ElementId(i)); return r; };
System.Func<Element, System.Collections.Generic.List<Connector>> Cs = el => { var r = new System.Collections.Generic.List<Connector>();
  var cm = el is MEPCurve ? ((MEPCurve)el).ConnectorManager : ((FamilyInstance)el).MEPModel.ConnectorManager;
  foreach (Connector c in cm.Connectors) if (c.ConnectorType == ConnectorType.End) r.Add(c); return r; };
System.Func<long, long, Connector> Soltar = (t, f) => { foreach (var ct in Cs(G(t))) foreach (Connector o in ct.AllRefs) if (o.Owner.Id.Value == f) { ct.DisconnectFrom(o); return o; } throw new Exception("sem ligacao " + t + "-" + f); };
System.Func<Element, XYZ, Connector> Em = (el, pt) => { Connector b = null; foreach (var c in Cs(el)) if (b == null || c.Origin.DistanceTo(pt) < b.Origin.DistanceTo(pt)) b = c; return b; };
System.Action<Element, string> Nota = (el, t) => { var p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p != null && !p.IsReadOnly) p.Set(((p.AsString() ?? "") + " | " + t).Trim(' ', '|')); };
var todos = new long[] { 4422687, 4422690, 4422693, 4422696, 4422699, 4422702, 4422705, 4422708, 4422711, 4422719, 4422722, 4422724, 4422714, 4422717, 4424057, 4423592, 4423616 };
var espinha = new long[] { 4422687, 4422690, 4422693, 4422696, 4422719, 4422714, 4424057, 4422717 };
using (var t = new Transaction(e, "R01 Fase A - hidrantes")) {
  t.Start();
  ElementTransformUtils.MoveElements(e, L(todos), new XYZ(0, 0, -0.35 / F));
  var e05 = Soltar(4422699, 4422717); var e08 = Soltar(4422708, 4422724);
  ElementTransformUtils.MoveElements(e, L(espinha), new XYZ(0, 0, -0.10 / F));
  ElementTransformUtils.MoveElement(e, new ElementId(4423592L), new XYZ(0, 0, 0.10 / F));
  e.Regenerate(); log.AppendLine("movidos: todos -0,35; espinha -0,10; cotovelo da guarita +0,10");
  System.Action<long, Connector, double, string> Degrau = (tid, ca, zq, nome) => {
    var tubo = (Autodesk.Revit.DB.Plumbing.Pipe)G(tid); var lc = (LocationCurve)tubo.Location; var c = lc.Curve;
    var p0 = c.GetEndPoint(0); var p1 = c.GetEndPoint(1); var A = ca.Origin;
    bool a0 = new XYZ(p0.X - A.X, p0.Y - A.Y, 0).GetLength() < new XYZ(p1.X - A.X, p1.Y - A.Y, 0).GetLength();
    var far = a0 ? p1 : p0; var u = new XYZ(far.X - A.X, far.Y - A.Y, 0).Normalize();
    var R = A + u * (0.30 / F); var Q = new XYZ(A.X, A.Y, zq / F) + u * (0.40 / F); var farN = new XYZ(far.X, far.Y, zq / F);
    lc.Curve = a0 ? Line.CreateBound(Q, farN) : Line.CreateBound(farN, Q);
    var s = tubo.MEPSystem.GetTypeId(); var lv = tubo.ReferenceLevel.Id;
    var t1 = Autodesk.Revit.DB.Plumbing.Pipe.Create(e, s, tubo.GetTypeId(), lv, A, R); var t2 = Autodesk.Revit.DB.Plumbing.Pipe.Create(e, s, tubo.GetTypeId(), lv, R, Q);
    t1.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(tubo.Diameter); t2.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(tubo.Diameter);
    t1.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(nome + ".d1"); t2.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(nome + ".d2");
    Nota(t1, "R01 18/10: degrau de 10 cm (curvas de 45 graus)"); Nota(t2, "R01 18/10: degrau de 10 cm (curvas de 45 graus)");
    e.Regenerate();
    Em(t1, A).ConnectTo(ca);
    try { e.Create.NewElbowFitting(Em(t1, R), Em(t2, R)); } catch (Exception x) { Em(t1, R).ConnectTo(Em(t2, R)); log.AppendLine("  " + nome + " curva 1 por ConnectTo: " + x.Message); }
    try { e.Create.NewElbowFitting(Em(t2, Q), Em(tubo, Q)); } catch (Exception x) { Em(t2, Q).ConnectTo(Em(tubo, Q)); log.AppendLine("  " + nome + " curva 2 por ConnectTo: " + x.Message); }
    log.AppendLine("degrau " + nome + ": z " + (A.Z * F).ToString("0.000", ci) + " -> " + zq.ToString("0.000", ci));
  };
  Degrau(4422699, e05, -1.20, "PCI-AH-05"); Degrau(4422708, e08, -1.10, "PCI-AH-08");
  var pr = new long[] { 4422687, 4422690, 4422693, 4422696, 4422699, 4422702, 4422705, 4422708, 4422711 }; var tx = new[] { "1,30", "1,30", "1,30", "1,30", "1,20", "1,20", "1,20", "1,10", "1,20" };
  for (int i = 0; i < pr.Length; i++) Nota(G(pr[i]), "R01 18/10: eixo a " + tx[i] + " m da cota 147,00 (relatorio PCI R00)");
  t.Commit();
}
var sb = new System.Text.StringBuilder();
foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_PipeCurves).WhereElementIsNotElementType()) {
  var mk = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? ""; if (!mk.StartsWith("PCI-AH") && !mk.StartsWith("PCI-AF-V01c")) continue;
  var c = ((LocationCurve)el.Location).Curve; int liv = 0; foreach (var x in Cs(el)) if (!x.IsConnected) liv++;
  sb.AppendLine(mk + " z " + (c.GetEndPoint(0).Z * F).ToString("0.000", ci) + " / " + (c.GetEndPoint(1).Z * F).ToString("0.000", ci) + " livres=" + liv);
}
e.Save();
return log.ToString() + sb.ToString();
