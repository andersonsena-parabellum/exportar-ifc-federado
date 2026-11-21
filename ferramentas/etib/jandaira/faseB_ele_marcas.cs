// Fase B (R01) — corrige a marca dos pedaços novos de eletroduto do JAN-ELE (aberto em segundo plano).
// O CopyElement do faseB_ele_aplicar.cs deixou a cópia sem a marca do original (ficou só ".m1", ".d1"...).
// Para cada eletroduto com marca começando em ".", acha a linha de ele_instrucoes.tsv com as mesmas pontas (tolerância 5 mm)
// e grava marca do original + sufixo. Transação própria e Save no fim.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\ele_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
var L = new System.Collections.Generic.List<string[]>();
foreach (var l in System.IO.File.ReadAllLines(INS)) { var r = l.Split('\t'); if (r.Length > 8 && r[0] == "SEG" && r[8] != "") L.Add(r); }
System.Func<XYZ, string[], int, bool> Igual = (p, r, k) => System.Math.Abs(p.X * F - double.Parse(r[k], ci)) < 0.005 && System.Math.Abs(p.Y * F - double.Parse(r[k + 1], ci)) < 0.005 && System.Math.Abs(p.Z * F - double.Parse(r[k + 2], ci)) < 0.005;
int ok = 0, sem = 0; var log = new System.Text.StringBuilder();
using (var t = new Transaction(e, "R01 Fase B - marcas dos pedacos novos")) {
  t.Start();
  foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsNotElementType()) {
    var pm = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK); var m = pm.AsString() ?? "";
    if (!m.StartsWith(".")) continue;
    var c = ((LocationCurve)el.Location).Curve; var a = c.GetEndPoint(0); var b = c.GetEndPoint(1); string[] achou = null;
    foreach (var r in L) if (r[8] == m && ((Igual(a, r, 2) && Igual(b, r, 5)) || (Igual(b, r, 2) && Igual(a, r, 5)))) { achou = r; break; }
    if (achou == null) { sem++; log.AppendLine("sem par: " + el.Id + " " + m); continue; }
    var o = e.GetElement(new ElementId(long.Parse(achou[1]))); var mo = o == null ? "" : (o.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? "");
    if (mo == "") { sem++; log.AppendLine("original sem marca: " + el.Id + " <- " + achou[1]); continue; }
    pm.Set(mo + m); ok++;
  }
  t.Commit();
}
System.IO.File.WriteAllText(INS.Replace(".tsv", "_marcas_log.txt"), "marcas corrigidas " + ok + " | sem par " + sem + "\r\n" + log.ToString());
e.Save();
return "MARCAS: corrigidas " + ok + " | sem par " + sem;
