// Fase E (R01) — drenagem do campo 50x30 (CPS DRE-001 R01) no JAN-DRE aberto em segundo plano, a partir de compat_R01\cps_dre_instrucoes.tsv
// (gerado por FERRAMENTAS\jandaira\cps\dre_cps_plano.py):
//   DEL <id> <marca>                       -> apaga o tubo da espinha de peixe do campo 45x25
//   MOD <id> <marca> ax ay az bx by bz     -> redesenha o tubo (solta as ligações das pontas antes)
//   NEW <PVCR150|PVCDR100> <marca> a.. b.. -> tubo novo (tipos, sistema e nível do Daniel)
//   CX  CX-43 <fundo interno>              -> aprofunda a caixa (Profundidade da caixa)
//   CAN <marca> cx cy ux uy                -> canaleta 54 x 0,50 x 0,30 (DirectShape de Modelo genérico)
// Uma transação por linha (um erro não desfaz as outras); Save no fim; log em cps_dre_instrucoes_log.txt.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-DRE.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\cps_dre_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("DRE nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
System.Func<string, double> N = v => double.Parse(v, ci) / F;
var sis = new ElementId(3528241L); var niv = new ElementId(7627049L);
var tipos = new System.Collections.Generic.Dictionary<string, ElementId> { { "PVCR150", new ElementId(7345496L) }, { "PVCDR100", new ElementId(7329989L) } };
var diam = new System.Collections.Generic.Dictionary<string, double> { { "PVCR150", 150 }, { "PVCDR100", 100 } };
var mat = new System.Collections.Generic.Dictionary<string, string> { { "PVCR150", "PVCR DN150" }, { "PVCDR100", "PVC-DR DN100" } };
string NOTA = "R01 18/10: campo society 50x30 (CPS)";
string OBS = "PREMISSAS (R01 18/10): tracado do CPS DRE-001 R01 (campo 50x30); espinha descarrega a oeste na CX-43 (o CPS manda a leste, onde nao ha rede); 1 %; ponta alta dos drenos com eixo 0,25 m abaixo do campo.";
System.Action<Element, string, string> Dados = (el, mk, desc) => {
  el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(mk);
  el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(desc + " | " + NOTA);
  foreach (var kv in new[] { new[] { "COMP_Origem", "DWG CPS-PE-DRE-001-R01" }, new[] { "COMP_Trecho", mk }, new[] { "COMP_Descrição", desc }, new[] { "COMP_Disciplina", "DRENAGEM" }, new[] { "COMP_Observação", OBS } }) {
    var p = el.LookupParameter(kv[0]); if (p != null && !p.IsReadOnly && p.StorageType == StorageType.String) p.Set(kv[1]); }
};
System.Action<MEPCurve> Soltar = (c) => {
  foreach (Connector k in c.ConnectorManager.Connectors) { var outros = new System.Collections.Generic.List<Connector>(); foreach (Connector o in k.AllRefs) if (o.Owner.Id != c.Id && o.ConnectorType == ConnectorType.End) outros.Add(o); foreach (var o in outros) k.DisconnectFrom(o); }
};
var log = new System.Text.StringBuilder(); int nd = 0, nm = 0, nn = 0, nc = 0;
foreach (var l in System.IO.File.ReadAllLines(INS)) {
  var r = l.Split('\t'); if (r.Length < 3) continue;
  using (var t = new Transaction(e, "R01 Fase E - " + r[0] + " " + r[1] + " " + r[2])) {
    t.Start();
    try {
      if (r[0] == "DEL") { var el = e.GetElement(new ElementId(long.Parse(r[1]))); if (el != null) { Soltar((MEPCurve)el); e.Delete(el.Id); nd++; } else log.AppendLine("DEL nao achou " + r[1]); }
      else if (r[0] == "MOD") {
        var p = (Autodesk.Revit.DB.Plumbing.Pipe)e.GetElement(new ElementId(long.Parse(r[1]))); Soltar(p);
        ((LocationCurve)p.Location).Curve = Line.CreateBound(new XYZ(N(r[3]), N(r[4]), N(r[5])), new XYZ(N(r[6]), N(r[7]), N(r[8])));
        var c = p.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); c.Set(((c.AsString() ?? "") + " | " + NOTA + ": cotas/ponta refeitas").Trim(' ', '|')); nm++;
      }
      else if (r[0] == "NEW") {
        var p = Autodesk.Revit.DB.Plumbing.Pipe.Create(e, sis, tipos[r[1]], niv, new XYZ(N(r[3]), N(r[4]), N(r[5])), new XYZ(N(r[6]), N(r[7]), N(r[8])));
        p.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(diam[r[1]] / 304.8);
        Dados(p, r[2], mat[r[1]] + " | i rótulo 1.00% | i modelo 1.00%"); nn++;
      }
      else if (r[0] == "CX") {
        Element cx = null; foreach (Element el in new FilteredElementCollector(e).WhereElementIsNotElementType().OfClass(typeof(FamilyInstance))) if ((el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.AsString() ?? "") == r[1]) cx = el;
        var pp = cx.LookupParameter("Profundidade da caixa"); double antes = pp.AsDouble() * F;
        var bb = cx.get_BoundingBox(null); double fundoAtual = bb.Min.Z * F + 0.06;   // base de 6 cm sob o fundo interno
        double nova = antes + (fundoAtual - double.Parse(r[2], ci)); pp.Set(nova / F);
        var c = cx.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); c.Set(((c.AsString() ?? "") + " | " + NOTA + ": profundidade " + nova.ToString("0.00", ci)).Trim(' ', '|'));
        log.AppendLine("CX-43 profundidade " + antes.ToString("0.000", ci) + " -> " + nova.ToString("0.000", ci) + " (fundo " + fundoAtual.ToString("0.000", ci) + " -> " + r[2] + ")"); nc++;
      }
      else if (r[0] == "CAN") {
        double cx = double.Parse(r[2], ci), cy = double.Parse(r[3], ci), ux = double.Parse(r[4], ci), uy = double.Parse(r[5], ci);
        var u = new XYZ(ux, uy, 0); var v = new XYZ(-uy, ux, 0); var c0 = new XYZ(cx / F, cy / F, -0.30 / F);
        var P = new[] { c0 + (-u * 27 - v * 0.25) / F, c0 + (u * 27 - v * 0.25) / F, c0 + (u * 27 + v * 0.25) / F, c0 + (-u * 27 + v * 0.25) / F };
        var loop = new CurveLoop(); for (int k = 0; k < 4; k++) loop.Append(Line.CreateBound(P[k], P[(k + 1) % 4]));
        var sol = GeometryCreationUtilities.CreateExtrusionGeometry(new[] { loop }, XYZ.BasisZ, 0.30 / F);
        var ds = DirectShape.CreateElement(e, new ElementId(BuiltInCategory.OST_GenericModel)); ds.SetShape(new GeometryObject[] { sol }); ds.Name = "Canaleta semicircular de concreto com grelha (CPS)";
        Dados(ds, r[1], "Canaleta semicircular de concreto com grelha metálica, 54 m (volume 0,50 x 0,30)"); nc++;
      }
      t.Commit();
    } catch (Exception x) { t.RollBack(); var ie = x; while (ie.InnerException != null) ie = ie.InnerException; log.AppendLine("ERRO " + l.Substring(0, System.Math.Min(40, l.Length)) + ": " + ie.Message); }
  }
}
System.IO.File.WriteAllText(INS.Replace(".tsv", "_log.txt"), "apagados " + nd + " | alterados " + nm + " | novos " + nn + " | caixa/canaletas " + nc + "\r\n" + log.ToString());
e.Save();
return "FASE E CPS: apagados " + nd + " | alterados " + nm + " | novos " + nn + " | caixa/canaletas " + nc + "\n" + log.ToString();
