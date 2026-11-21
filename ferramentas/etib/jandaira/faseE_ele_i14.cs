// Fase E (R01) — refaz o mergulho do ELE-I-14 sob a CX-43 (mais funda com a drenagem do campo 50x30) no JAN-ELE aberto em segundo plano.
// Lê compat_R01\ele_i14_instrucoes.tsv: MODSEG <id> ax ay az bx by bz <nota> (m, interno). Solta as ligações, redesenha, anota; Save.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\ele_i14_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture; System.Func<string, double> N = v => double.Parse(v, ci) / F;
var log = new System.Text.StringBuilder(); int n = 0;
using (var t = new Transaction(e, "R01 Fase E - mergulho do ELE-I-14 sob a CX-43")) {
  t.Start();
  foreach (var l in System.IO.File.ReadAllLines(INS)) {
    var r = l.Split('\t'); if (r.Length < 9 || r[0] != "MODSEG") continue;
    var c = (MEPCurve)e.GetElement(new ElementId(long.Parse(r[1])));
    foreach (Connector k in c.ConnectorManager.Connectors) { var outros = new System.Collections.Generic.List<Connector>(); foreach (Connector o in k.AllRefs) if (o.Owner.Id != c.Id && o.ConnectorType == ConnectorType.End) outros.Add(o); foreach (var o in outros) { log.AppendLine(r[1] + " soltou de " + o.Owner.Category.Name + " " + o.Owner.Id); k.DisconnectFrom(o); } }
    ((LocationCurve)c.Location).Curve = Line.CreateBound(new XYZ(N(r[2]), N(r[3]), N(r[4])), new XYZ(N(r[5]), N(r[6]), N(r[7])));
    var p = c.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); p.Set(((p.AsString() ?? "") + " | " + r[8]).Trim(' ', '|')); n++;
  }
  t.Commit();
}
e.Save();
return "ELE-I-14: " + n + " pecas redesenhadas\n" + log.ToString();
