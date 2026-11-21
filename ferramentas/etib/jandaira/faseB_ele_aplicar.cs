// Fase B (R01) — aplica no JAN-ELE (aberto em segundo plano) o plano da elétrica lido de um arquivo de instruções (ele_instrucoes.tsv):
//   SEG <id> <x1> <y1> <z1> <x2> <y2> <z2> <sufixo> <nota>   -> 1ª linha do id: redesenha o eletroduto; demais: cópia (CopyElement) com marca + sufixo
//   CX  <marca> <dx> <dy> <prof> <nota>                       -> move a caixa e ajusta o parâmetro "Profundidade"
// Coordenadas internas em metros. Transação própria e Save no fim. Log em ele_instrucoes_log.txt.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-ELE.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\ele_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("ELE nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture; var log = new System.Text.StringBuilder();
System.Func<string, double> N = v => double.Parse(v, ci) / F;
System.Action<Element, string> Nota = (el, t) => { var p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p == null || p.IsReadOnly || t == "") return; p.Set(((p.AsString() ?? "") + " | " + t).Trim(' ', '|')); };
var caixas = new System.Collections.Generic.Dictionary<string, Element>();
foreach (Element el in new FilteredElementCollector(e).OfCategory(BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType()) { var m = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString(); if (m != null) caixas[m] = el; }
int nmod = 0, ncop = 0, ncx = 0; var feitos = new System.Collections.Generic.HashSet<string>();
using (var t = new Transaction(e, "R01 Fase B - eletrica (so profundidade)")) {
  t.Start();
  foreach (var l in System.IO.File.ReadAllLines(INS)) {
    var r = l.Split('\t'); if (r.Length < 2) continue;
    try {
      if (r[0] == "SEG") {
        var el = e.GetElement(new ElementId(long.Parse(r[1]))); var a = new XYZ(N(r[2]), N(r[3]), N(r[4])); var b = new XYZ(N(r[5]), N(r[6]), N(r[7]));
        if (!feitos.Contains(r[1])) { ((LocationCurve)el.Location).Curve = Line.CreateBound(a, b); Nota(el, r[9]); feitos.Add(r[1]); nmod++; }
        else { var ids = ElementTransformUtils.CopyElement(e, el.Id, XYZ.Zero); Element c = null; foreach (var cid in ids) { c = e.GetElement(cid); break; } ((LocationCurve)c.Location).Curve = Line.CreateBound(a, b);
          var mk = c.get_Parameter(BuiltInParameter.ALL_MODEL_MARK); mk.Set((mk.AsString() ?? "") + r[8]); ncop++; }
      } else if (r[0] == "CX") {
        if (!caixas.ContainsKey(r[1])) { log.AppendLine("caixa nao achada: " + r[1]); continue; }
        var cx = caixas[r[1]]; double dx = N(r[2]), dy = N(r[3]);
        if (System.Math.Abs(dx) + System.Math.Abs(dy) > 1e-6) ElementTransformUtils.MoveElement(e, cx.Id, new XYZ(dx, dy, 0));
        var pr = cx.LookupParameter("Profundidade"); if (pr != null && r[4] != "") pr.Set(N(r[4])); Nota(cx, r[5]); ncx++;
      }
    } catch (Exception x) { log.AppendLine("ERRO " + l.Substring(0, System.Math.Min(60, l.Length)) + ": " + x.Message); }
  }
  t.Commit();
}
System.IO.File.WriteAllText(INS.Replace(".tsv", "_log.txt"), "modificados " + nmod + " | copias " + ncop + " | caixas " + ncx + "\r\n" + log.ToString());
e.Save();
return "FASE B: modificados " + nmod + " | copias " + ncop + " | caixas " + ncx + " | erros " + (log.Length > 0 ? log.ToString().Split('\n').Length - 1 : 0);
