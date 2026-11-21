string ARQ = @"D:\Projeto Modelagem\ETIB-JANDAIRA\JAN-PCIrvt.rvt"; Document e = null;
foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
var sb = new System.Text.StringBuilder(); var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
System.Func<XYZ, string> P = p => "(" + (p.X * F).ToString("0.000", ci) + ";" + (p.Y * F).ToString("0.000", ci) + ";" + (p.Z * F).ToString("0.000", ci) + ")";
foreach (var id in new long[] { 4423534, 4423535, 4423536, 4423537, 4423538 }) {
  var el = e.GetElement(new ElementId(id)) as FamilyInstance; var bb = el.get_BoundingBox(null);
  sb.AppendLine(id + " " + el.LookupParameter("Marca")?.AsString() + " bb " + P(bb.Min) + " " + P(bb.Max) + " loc " + P(((LocationPoint)el.Location).Point) + " host=" + (el.Host != null) + " lvl=" + e.GetElement(el.LevelId)?.Name);
  foreach (Parameter p in el.Parameters) if (p.StorageType == StorageType.Double && !p.IsReadOnly) sb.AppendLine("   inst " + p.Definition.Name + "=" + p.AsValueString());
  foreach (Parameter p in el.Symbol.Parameters) if (p.StorageType == StorageType.Double) sb.AppendLine("   tipo " + p.Definition.Name + "=" + p.AsValueString());
  if (id != 4423534) { sb.Length = sb.Length; }
}
var pipe = e.GetElement(new ElementId(4422699L)) as Autodesk.Revit.DB.Plumbing.Pipe; var pt = pipe.PipeType;
var rpm = pt.RoutingPreferenceManager; sb.AppendLine("tipo tubo " + pt.Name + " elbows=" + rpm.GetNumberOfRules(RoutingPreferenceRuleGroupType.Elbows));
for (int i = 0; i < rpm.GetNumberOfRules(RoutingPreferenceRuleGroupType.Elbows); i++) { var r = rpm.GetRule(RoutingPreferenceRuleGroupType.Elbows, i); sb.AppendLine("   elbow " + e.GetElement(r.MEPPartId)?.Name); }
sb.AppendLine("nivel tubo " + e.GetElement(pipe.ReferenceLevel.Id).Name + " sistema " + pipe.MEPSystem?.Name + " systype " + pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsValueString());
foreach (var id in new long[] { 4422717, 4422724 }) { var f = e.GetElement(new ElementId(id)) as FamilyInstance; sb.AppendLine(id + " " + f.Symbol.FamilyName + " : " + f.Name); }
return sb.ToString();
