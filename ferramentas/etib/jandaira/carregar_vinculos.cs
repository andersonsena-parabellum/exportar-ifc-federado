// Recarrega, no modelo aberto em segundo plano, os vínculos RVT a partir da pasta da escola (LoadFrom), só os do filtro.
string ARQ = @"@@ARQ@@"; string FILTRO = "@@FILTRO@@"; string B = @"D:\Projeto Modelagem\ETIB-JANDAIRA\";
Document e = null; foreach (Document d in document.Application.Documents) if (!d.IsLinked && d.PathName == ARQ) e = d;
if (e == null) throw new Exception("nao aberto: " + ARQ);
var sb = new System.Text.StringBuilder(); var t0 = System.DateTime.Now;
foreach (RevitLinkType lt in new FilteredElementCollector(e).OfClass(typeof(RevitLinkType))) {
  string n = lt.Name; if (!n.Contains(FILTRO)) continue;
  if (lt.GetLinkedFileStatus() == LinkedFileStatus.Loaded) { sb.AppendLine("ja: " + n); continue; }
  string up = n.ToUpperInvariant(); string alvo = null;
  if (up.StartsWith("JAN-")) alvo = B + n;
  else if (up.Contains("-IMP-R00")) alvo = B + @"REFERENCIAS_RVT\IMP\" + n;
  else if (up.Contains("-PE-FUN-")) { foreach (var bl in new[] { "BP4", "GUA", "SB3", "VST", "QDC" }) if (up.Contains("-" + bl + "-")) alvo = B + @"REFERENCIAS_RVT\" + bl + @"\" + n;
    if (up.Contains("-CDG-") || up.Contains("-CDR-")) alvo = B + @"REFERENCIAS_RVT\CDG_CDR\" + n; }
  if (alvo == null || !System.IO.File.Exists(alvo)) { sb.AppendLine("sem arquivo: " + n); continue; }
  try { var r = lt.LoadFrom(ModelPathUtils.ConvertUserVisiblePathToModelPath(alvo), null); sb.AppendLine(r.LoadResult + ": " + n); }
  catch (Exception x) { sb.AppendLine("ERRO " + n + ": " + x.Message); }
}
sb.AppendLine((System.DateTime.Now - t0).TotalSeconds.ToString("0") + " s");
return sb.ToString();
