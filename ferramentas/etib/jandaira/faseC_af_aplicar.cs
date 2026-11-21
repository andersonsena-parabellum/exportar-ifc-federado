// Fase C (R01) — aplica no JAN-AGF (aberto em segundo plano) o plano da água fria lido de af_instrucoes.tsv:
//   MOVE <id> <dx> <dy> <nota>              -> desloca o tubo em planta (as conexões das pontas acompanham)
//   POLY <id> <nota> x1 y1 z1 x2 y2 z2 ...   -> redesenha o tubo como polilinha (mergulho): 1º trecho no próprio tubo, demais tubos novos ligados por curvas
// Coordenadas internas em metros. Transação própria por instrução (um erro não desfaz as outras). Save no fim; log em af_instrucoes_log.txt.
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-AGF.rvt"; string INS = @"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\af_instrucoes.tsv";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("AGF nao aberto");
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture; var log = new System.Text.StringBuilder();
System.Func<string, double> N = v => double.Parse(v, ci) / F;
System.Action<Element, string> Nota = (el, t) => { var p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS); if (p == null || p.IsReadOnly || t == "") return; p.Set(((p.AsString() ?? "") + " | " + t).Trim(' ', '|')); };
System.Func<Element, System.Collections.Generic.List<Connector>> Cs = el => { var r = new System.Collections.Generic.List<Connector>(); foreach (Connector c in ((MEPCurve)el).ConnectorManager.Connectors) if (c.ConnectorType == ConnectorType.End) r.Add(c); return r; };
System.Func<Element, XYZ, Connector> Em = (el, pt) => { Connector b = null; foreach (var c in Cs(el)) if (b == null || c.Origin.DistanceTo(pt) < b.Origin.DistanceTo(pt)) b = c; return b; };
int nmov = 0, npol = 0, nnovos = 0;
foreach (var l in System.IO.File.ReadAllLines(INS)) {
  var r = l.Split('\t'); if (r.Length < 3) continue;
  using (var t = new Transaction(e, "R01 Fase C - " + r[0] + " " + r[1])) {
    t.Start();
    try {
      var tubo = (Autodesk.Revit.DB.Plumbing.Pipe)e.GetElement(new ElementId(long.Parse(r[1])));
      if (r[0] == "MOVE") { ElementTransformUtils.MoveElement(e, tubo.Id, new XYZ(N(r[2]), N(r[3]), 0)); Nota(tubo, r[4]); nmov++; }
      else if (r[0] == "POLY") {
        var V = new System.Collections.Generic.List<XYZ>(); for (int k = 3; k + 2 < r.Length; k += 3) V.Add(new XYZ(N(r[k]), N(r[k + 1]), N(r[k + 2])));
        var c = ((LocationCurve)tubo.Location).Curve; var p0 = c.GetEndPoint(0); var p1 = c.GetEndPoint(1);
        bool dir = p0.DistanceTo(V[0]) <= p1.DistanceTo(V[0]);          // V começa na ponta 0 do tubo?
        var fim = dir ? p1 : p0; Connector cfim = Em(tubo, fim); Connector outro = null;
        foreach (Connector o in cfim.AllRefs) if (o.Owner.Id != tubo.Id && o.ConnectorType == ConnectorType.End) outro = o;
        if (outro != null) cfim.DisconnectFrom(outro);
        ((LocationCurve)tubo.Location).Curve = dir ? Line.CreateBound(V[0], V[1]) : Line.CreateBound(V[1], V[0]);
        Nota(tubo, r[2]); Element ant = tubo; var mk = tubo.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString() ?? "";
        for (int k = 1; k + 1 < V.Count; k++) {
          var np = Autodesk.Revit.DB.Plumbing.Pipe.Create(e, tubo.MEPSystem.GetTypeId(), tubo.GetTypeId(), tubo.ReferenceLevel.Id, V[k], V[k + 1]);
          np.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(tubo.Diameter); np.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(mk + ".g" + k); Nota(np, r[2]);
          e.Regenerate();
          try { e.Create.NewElbowFitting(Em(ant, V[k]), Em(np, V[k])); } catch { Em(ant, V[k]).ConnectTo(Em(np, V[k])); }
          ant = np; nnovos++;
        }
        e.Regenerate();
        if (outro != null) { try { Em(ant, V[V.Count - 1]).ConnectTo(outro); } catch (Exception x) { log.AppendLine("ponta final " + r[1] + ": " + x.Message); } }
        npol++;
      }
      t.Commit();
    } catch (Exception x) { t.RollBack(); log.AppendLine("ERRO " + r[0] + " " + r[1] + ": " + x.Message); }
  }
}
System.IO.File.WriteAllText(INS.Replace(".tsv", "_log.txt"), "deslocados " + nmov + " | mergulhos " + npol + " | tubos novos " + nnovos + "\r\n" + log.ToString());
e.Save();
return "FASE C: deslocados " + nmov + " | mergulhos " + npol + " | tubos novos " + nnovos;
