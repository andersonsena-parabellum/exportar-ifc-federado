// Lista a ligação da rede de incêndio do JAN-PCI (tubos AH/AF e eletrodutos EL, conexões e o que está ligado a cada conector).
string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; var app = document.Application; Document e = null;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) return "PCI nao aberto";
var sb = new System.Text.StringBuilder(); var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
System.Func<XYZ, string> P = p => "(" + (p.X * F).ToString("0.000", ci) + ";" + (p.Y * F).ToString("0.000", ci) + ";" + (p.Z * F).ToString("0.000", ci) + ")";
foreach (var bic in new[] { BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory, BuiltInCategory.OST_Conduit, BuiltInCategory.OST_ConduitFitting }) {
  foreach (Element el in new FilteredElementCollector(e).OfCategory(bic).WhereElementIsNotElementType()) {
    ConnectorManager cm = null;
    if (el is MEPCurve) cm = ((MEPCurve)el).ConnectorManager; else if (el is FamilyInstance && ((FamilyInstance)el).MEPModel != null) cm = ((FamilyInstance)el).MEPModel.ConnectorManager;
    var mk = el.get_Parameter(BuiltInParameter.ALL_MODEL_MARK); string m = mk == null ? "" : (mk.AsString() ?? "");
    sb.Append(el.Id + "\t" + el.Category.Name + "\t" + m + "\t" + el.Name);
    if (cm != null) foreach (Connector c in cm.Connectors) {
      if (c.ConnectorType != ConnectorType.End) continue;
      string liga = ""; foreach (Connector o in c.AllRefs) if (o.Owner.Id != el.Id && o.ConnectorType == ConnectorType.End) liga += o.Owner.Id + ",";
      sb.Append("\t" + P(c.Origin) + "->" + liga);
    }
    sb.AppendLine();
  }
}
System.IO.File.WriteAllText(@"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\pci_topologia.tsv", sb.ToString(), new System.Text.UTF8Encoding(false));
return "TOPO ok " + sb.Length;
