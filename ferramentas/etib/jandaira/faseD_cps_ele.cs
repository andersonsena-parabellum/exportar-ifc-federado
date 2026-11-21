// Fase D (R01) — iluminação do campo society (CPS EL-001 R01) no JAN-ELE aberto em segundo plano, a partir de compat_R01\cps_ele_instrucoes.tsv:
//   SEG <marca> ax ay az bx by bz   (m, interno)  -> eletroduto Ø1" (DN 32, mesmo tipo do Daniel), curva nas mudanças de direção
//   CX  <marca> cx cy ux uy                       -> caixa 30x30 (DirectShape de Equipamento elétrico: o modelo não tem família 30x30)
// Transação própria; Save no fim. Comentário "R01 18/10: campo society (CPS)" em tudo.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\cps_ele_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
System.Func<string, double> N = v => double.Parse(v, ci) / F;
var tipo = new ElementId(813753L); var nivel = new ElementId(5241991L);
string OBS = "PREMISSAS (R01 18/10): campo 50x30 do CPS centrado no piso do campo do IMP, no angulo da SIT (precisao ~1 m); eixo na cota 146,57 (mesma da eletrica do Daniel); caixa 30x30 interna, parede 10 cm, fundo 10 cm abaixo do eletroduto.";
System.Action<Element, string, string, string> Dados = (el, mk, desc, extra) => {
  el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(mk);
  el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(desc + " | Fonte: CPS EL-001 | R01 18/10: campo society (CPS)" + extra);
  foreach (var kv in new[] { new[] { "COMP_Origem", "DWG CPS-PE-EL-001-R01" }, new[] { "COMP_Trecho", mk }, new[] { "COMP_Descrição", desc }, new[] { "COMP_Disciplina", "ELÉTRICA" }, new[] { "COMP_Sistema CAD", "ILUMINAÇÃO EXTERNA" }, new[] { "COMP_Observação", OBS } }) {
    var p = el.LookupParameter(kv[0]); if (p != null && !p.IsReadOnly && p.StorageType == StorageType.String) p.Set(kv[1]); }
};
var log = new System.Text.StringBuilder(); int nseg = 0, ncx = 0, ncurva = 0;
var criados = new System.Collections.Generic.List<Autodesk.Revit.DB.Electrical.Conduit>();
using (var t = new Transaction(e, "R01 Fase D - iluminacao do campo (CPS)")) {
  t.Start();
  foreach (var l in System.IO.File.ReadAllLines(INS)) {
    var r = l.Split('\t'); if (r.Length < 6) continue;
    if (r[0] == "SEG") {
      var a = new XYZ(N(r[2]), N(r[3]), N(r[4])); var b = new XYZ(N(r[5]), N(r[6]), N(r[7]));
      var c = Autodesk.Revit.DB.Electrical.Conduit.Create(e, tipo, a, b, nivel);
      c.get_Parameter(BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM).Set(32.0 / 304.8);
      Dados(c, r[1], r[1] == "ELE-CPS-QDLT" ? "Subida do eletroduto Ø1\" ao QDLT-CAMPO" : "Eletroduto Ø1\" enterrado - iluminação do campo", "");
      criados.Add(c); nseg++;
    } else if (r[0] == "CX") {
      double cx = double.Parse(r[2], ci), cy = double.Parse(r[3], ci), ux = double.Parse(r[4], ci), uy = double.Parse(r[5], ci);
      double h = 0.25, z0 = -0.546 - 0.10, z1 = 0.0;   // externo 0,50 x 0,50; fundo externo 10 cm abaixo do fundo interno
      var u = new XYZ(ux, uy, 0); var v = new XYZ(-uy, ux, 0); var c0 = new XYZ(cx / F, cy / F, z0 / F);
      var P = new[] { c0 + (-u - v) * h / F, c0 + (u - v) * h / F, c0 + (u + v) * h / F, c0 + (-u + v) * h / F };
      var loop = new CurveLoop(); for (int k = 0; k < 4; k++) loop.Append(Line.CreateBound(P[k], P[(k + 1) % 4]));
      var sol = GeometryCreationUtilities.CreateExtrusionGeometry(new[] { loop }, XYZ.BasisZ, (z1 - z0) / F);
      var ds = DirectShape.CreateElement(e, new ElementId(BuiltInCategory.OST_ElectricalEquipment));
      ds.SetShape(new GeometryObject[] { sol }); ds.Name = "ELE_Caixa de Passagem 30x30 (CPS)";
      Dados(ds, r[1], "Caixa de passagem 30x30 cm (dimensão interna)", " | DirectShape: o modelo nao tem familia 30x30");
      ncx++;
    }
  }
  e.Regenerate();
  // curvas nas mudanças de direção (pontas coincidentes de eletrodutos não colineares)
  for (int i = 0; i < criados.Count; i++) for (int j = i + 1; j < criados.Count; j++) {
    foreach (Connector ca in criados[i].ConnectorManager.Connectors) foreach (Connector cb in criados[j].ConnectorManager.Connectors) {
      if (ca.IsConnected || cb.IsConnected || ca.Origin.DistanceTo(cb.Origin) > 0.01) continue;
      var da = ((Line)((LocationCurve)criados[i].Location).Curve).Direction; var db = ((Line)((LocationCurve)criados[j].Location).Curve).Direction;
      if (System.Math.Abs(da.DotProduct(db)) > 0.999) continue;
      try { e.Create.NewElbowFitting(ca, cb); ncurva++; } catch (Exception x) { log.AppendLine("curva " + criados[i].Id + "/" + criados[j].Id + ": " + x.Message); }
    }
  }
  t.Commit();
}
e.Save();
return "FASE D CPS: eletrodutos " + nseg + " | caixas " + ncx + " | curvas " + ncurva + "\n" + log.ToString();
