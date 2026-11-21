// Parte 1 de 2 (o plugin só aceita pedidos de ~8 KB): abre o modelo em segundo plano (fica aberto para a parte 2) e grava <DISC>_meta.json.
string ARQ = @"@@ARQ@@"; string DISC = "@@DISC@@"; string OUT = @"@@OUT@@";
const double F = 0.3048; var ci = System.Globalization.CultureInfo.InvariantCulture;
System.IO.Directory.CreateDirectory(OUT);
var app = document.Application; Document e = null;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
var t0 = System.DateTime.Now;
if (e == null) e = app.OpenDocumentFile(ARQ);
double tOpen = (System.DateTime.Now - t0).TotalSeconds;
System.Func<double, string> S = v => (v * F).ToString("0.####", ci);
System.Func<XYZ, string> J3 = p => "[" + S(p.X) + "," + S(p.Y) + "," + S(p.Z) + "]";
System.Func<XYZ, string> J3u = p => "[" + p.X.ToString("0.##########", ci) + "," + p.Y.ToString("0.##########", ci) + "," + p.Z.ToString("0.##########", ci) + "]";
System.Func<string, string> Q = s => "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "'").Replace("\t", " ").Replace("\r", " ").Replace("\n", " ") + "\"";
var m = new System.Text.StringBuilder(); m.Append("{");
m.Append("\"disc\":" + Q(DISC) + ",\"titulo\":" + Q(e.Title) + ",\"arquivo\":" + Q(ARQ) + ",\"t_abrir_s\":" + tOpen.ToString("0.0", ci) + ",");
var pp = e.ActiveProjectLocation.GetProjectPosition(XYZ.Zero);
m.Append("\"local\":" + Q(e.ActiveProjectLocation.Name) + ",\"pos\":{\"ew\":" + S(pp.EastWest) + ",\"ns\":" + S(pp.NorthSouth) + ",\"elev\":" + S(pp.Elevation) + ",\"ang\":" + pp.Angle.ToString("0.############", ci) + "},");
var tt = e.ActiveProjectLocation.GetTotalTransform();
m.Append("\"tot\":{\"o\":" + J3(tt.Origin) + ",\"bx\":" + J3u(tt.BasisX) + ",\"by\":" + J3u(tt.BasisY) + "},");
var pbp = BasePoint.GetProjectBasePoint(e); var svp = BasePoint.GetSurveyPoint(e);
m.Append("\"pbp\":{\"pos\":" + J3(pbp.Position) + ",\"shared\":" + J3(pbp.SharedPosition) + "},\"svp\":{\"pos\":" + J3(svp.Position) + ",\"shared\":" + J3(svp.SharedPosition) + "},");
m.Append("\"niveis\":["); bool first = true;
foreach (Level lv in new FilteredElementCollector(e).OfClass(typeof(Level))) { m.Append((first ? "" : ",") + "[" + Q(lv.Name) + "," + S(lv.Elevation) + "]"); first = false; }
m.Append("],\"links\":["); first = true;
foreach (RevitLinkInstance li in new FilteredElementCollector(e).OfClass(typeof(RevitLinkInstance))) {
  var tf = li.GetTotalTransform(); var lt = e.GetElement(li.GetTypeId()) as RevitLinkType; string st = "";
  try { st = lt.GetLinkedFileStatus().ToString(); } catch { }
  m.Append((first ? "" : ",") + "{\"nome\":" + Q(li.Name) + ",\"status\":" + Q(st) + ",\"o\":" + J3(tf.Origin) + ",\"bx\":" + J3u(tf.BasisX) + "}"); first = false;
}
m.Append("],\"cads\":["); first = true;
foreach (ImportInstance ii in new FilteredElementCollector(e).OfClass(typeof(ImportInstance))) {
  var tf = ii.GetTotalTransform(); string nome = ""; try { nome = ii.Category != null ? ii.Category.Name : ""; } catch { }
  Transform gt = null; var ge = ii.get_Geometry(new Options());
  if (ge != null) foreach (GeometryObject go in ge) if (go is GeometryInstance) { gt = ((GeometryInstance)go).Transform; break; }
  if (gt == null) gt = tf;
  m.Append((first ? "" : ",") + "{\"nome\":" + Q(nome) + ",\"linked\":" + (ii.IsLinked ? "true" : "false") + ",\"vista\":" + (ii.ViewSpecific ? "true" : "false") + ",\"o\":" + J3(gt.Origin) + ",\"bx\":" + J3u(gt.BasisX) + "}"); first = false;
}
var cont = new System.Collections.Generic.Dictionary<string, int>();
foreach (Element el in new FilteredElementCollector(e).WhereElementIsNotElementType()) { if (el.Category == null) continue; var k = el.Category.Name; cont[k] = cont.ContainsKey(k) ? cont[k] + 1 : 1; }
m.Append("],\"contagem\":{"); first = true;
foreach (var kv in cont) { m.Append((first ? "" : ",") + Q(kv.Key) + ":" + kv.Value); first = false; }
m.Append("}}");
System.IO.File.WriteAllText(OUT + DISC + "_meta.json", m.ToString(), new System.Text.UTF8Encoding(false));
return "META " + DISC + " ok: abrir " + tOpen.ToString("0", ci) + " s";
