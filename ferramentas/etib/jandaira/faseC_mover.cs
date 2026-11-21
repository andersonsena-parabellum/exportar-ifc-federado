// Fase C (R01): desloca em planta GRUPOS de tubos da água fria (uma linha inteira de uma vez, com MoveElements; os vizinhos ligados esticam).
// Linhas do arquivo af_mover.tsv: MOVESET <dx> <dy> <id1,id2,...> <nota>   (metros). Save no fim.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-AGF.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\af_mover.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("AGF nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture; var log = new System.Text.StringBuilder();
foreach (var l in System.IO.File.ReadAllLines(INS)) {
  var r = l.Split('\t'); if (r.Length < 4 || r[0] != "MOVESET") continue;
  using (var t = new Transaction(e, "R01 Fase C - deslocar linha")) { t.Start();
    var ids = new System.Collections.Generic.List<ElementId>(); foreach (var s in r[3].Split(',')) ids.Add(new ElementId(long.Parse(s)));
    ElementTransformUtils.MoveElements(e, ids, new XYZ(double.Parse(r[1], ci) / F, double.Parse(r[2], ci) / F, 0));
    foreach (var id in ids) { var p = e.GetElement(id).get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p != null && !p.IsReadOnly) p.Set(((p.AsString() ?? "") + " | " + r[4]).Trim(' ', '|')); }
    t.Commit(); log.AppendLine("ok " + r[1] + " " + r[2] + " (" + ids.Count + " tubos)"); }
}
e.Save();
return "MOVER: " + log.ToString();
