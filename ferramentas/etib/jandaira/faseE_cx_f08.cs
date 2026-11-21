// Correção (19/10): CX-F08 e CX-I01 da guarita ficaram sobrepostas na fase B. Move a CX-F08 (id 5247215) e as pontas dos eletrodutos
// que chegam nela pelo deslocamento de compat_R01\cx_f08_corrige.json (m, interno); JAN-ELE aberto em segundo plano; Save no fim.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var v = new XYZ(0.1464 / F, -0.6464 / F, 0);
var pontas = new[] { new[] { "5247289", "b" }, new[] { "5247291", "a" }, new[] { "5247457", "b" }, new[] { "5248089", "a" }, new[] { "5248089", "b" }, new[] { "5248092", "a" } };
var log = new System.Text.StringBuilder();
using (var t = new Transaction(e, "R01 - CX-F08 fora da CX-I01")) {
  t.Start();
  var cx = e.GetElement(new ElementId(5247215L));
  ElementTransformUtils.MoveElement(e, cx.Id, v);
  var p = cx.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); p.Set(((p.AsString() ?? "") + " | R01 19/10: posicao corrigida (fora da CX-I01)").Trim(' ', '|'));
  var porId = new System.Collections.Generic.Dictionary<long, System.Collections.Generic.List<string>>();
  foreach (var q in pontas) { long id = long.Parse(q[0]); if (!porId.ContainsKey(id)) porId[id] = new System.Collections.Generic.List<string>(); porId[id].Add(q[1]); }
  foreach (var kv in porId) {
    var c = (MEPCurve)e.GetElement(new ElementId(kv.Key));
    foreach (Connector k in c.ConnectorManager.Connectors) { var outros = new System.Collections.Generic.List<Connector>(); foreach (Connector o in k.AllRefs) if (o.Owner.Id != c.Id && o.ConnectorType == ConnectorType.End) outros.Add(o); foreach (var o in outros) k.DisconnectFrom(o); }
    var cv = ((LocationCurve)c.Location).Curve; var a = cv.GetEndPoint(0); var b = cv.GetEndPoint(1);
    if (kv.Value.Contains("a")) a = a + v; if (kv.Value.Contains("b")) b = b + v;
    ((LocationCurve)c.Location).Curve = Line.CreateBound(a, b); log.AppendLine(kv.Key + " pontas " + string.Join(",", kv.Value));
  }
  t.Commit();
}
e.Save();
return "CXF08 corrigida\n" + log.ToString();
