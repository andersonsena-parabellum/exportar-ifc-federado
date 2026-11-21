// Regrava os vínculos dos 5 modelos JAN (fechados) para a estrutura da pasta da escola, sem abrir os modelos (TransmissionData).
// RVT de IMP/FUN -> REFERENCIAS_RVT\<bloco>\ ; modelos JAN entre si -> mesma pasta ; DWG SIT/AF/ESG -> CAD_GEORREFERENCIADO\ ; DWGs da OneDrive do Daniel -> não carregar.
// ARQ (não baixados), DWG copia de DRE e _GEO de ELE ficam como estão (pendentes). SIMULAR=true só lista.
bool SIMULAR = @@SIMULAR@@; string B = @"D:\Projeto Modelagem\ETIB-JANDAIRA\";
var sb = new System.Text.StringBuilder(); sb.AppendLine("RELINK " + (SIMULAR ? "simulação" : "gravando"));
System.Func<string, string> Alvo = nome => {
  string n = nome.ToUpperInvariant();
  if (n.StartsWith("JAN-") && n.EndsWith(".RVT")) return B + nome;
  if (n.Contains("-IMP-R00.RVT")) return B + @"REFERENCIAS_RVT\IMP\" + nome;
  if (n.Contains("-PE-FUN-")) { foreach (var bl in new[] { "BP4", "GUA", "SB3", "VST", "QDC" }) if (n.Contains("-" + bl + "-")) return B + @"REFERENCIAS_RVT\" + bl + @"\" + nome;
    if (n.Contains("-CDG-") || n.Contains("-CDR-")) return B + @"REFERENCIAS_RVT\CDG_CDR\" + nome; }
  if (n.Contains("-SIT-R03.DWG") || n.Contains("-AF-001-HIG-R01.DWG") || n.Contains("-ESG-001-HIG-R01.DWG")) return B + @"CAD_GEORREFERENCIADO\" + nome;
  return null; };
foreach (var a in new[] { "JAN-AGF.rvt", "JAN-DRE.rvt", "JAN-ELE.rvt", "JAN-ESG.rvt", "JAN-PCIrvt.rvt" }) {
  var mp = ModelPathUtils.ConvertUserVisiblePathToModelPath(B + a); var td = TransmissionData.ReadTransmissionData(mp);
  sb.AppendLine("== " + a); int mud = 0;
  foreach (var id in td.GetAllExternalFileReferenceIds()) {
    var r = td.GetLastSavedReferenceData(id); var tipo = r.ExternalFileReferenceType;
    if (tipo != ExternalFileReferenceType.RevitLink && tipo != ExternalFileReferenceType.CADLink) continue;
    string p = ModelPathUtils.ConvertModelPathToUserVisiblePath(r.GetPath()); string nome = System.IO.Path.GetFileName(p);
    if (tipo == ExternalFileReferenceType.CADLink && (nome == "idrometro.dwg" || nome == "CAIXA ESOTO.dwg")) {
      if (!SIMULAR) td.SetDesiredReferenceData(id, r.GetPath(), r.PathType, false);
      sb.AppendLine("  nao carregar: " + nome); mud++; continue; }
    string alvo = Alvo(nome);
    if (alvo == null) { sb.AppendLine("  mantido: " + p); continue; }
    if (!System.IO.File.Exists(alvo)) { sb.AppendLine("  SEM ARQUIVO: " + alvo); continue; }
    bool carregar = !alvo.Contains(@"\VST\");   // VST corrompido no download: aponta, mas não carrega até baixar de novo
    if (!SIMULAR) td.SetDesiredReferenceData(id, ModelPathUtils.ConvertUserVisiblePathToModelPath(alvo), PathType.Relative, carregar);
    sb.AppendLine("  " + nome + " -> " + alvo.Substring(B.Length) + (carregar ? "" : " (não carregar)")); mud++;
  }
  if (!SIMULAR && mud > 0) { td.IsTransmitted = false; TransmissionData.WriteTransmissionData(mp, td); }
  if (!SIMULAR) { var td2 = TransmissionData.ReadTransmissionData(mp); int ok = 0;
    foreach (var id in td2.GetAllExternalFileReferenceIds()) { var d = td2.GetDesiredReferenceData(id); var pp = ModelPathUtils.ConvertModelPathToUserVisiblePath(d.GetPath()); if (pp.Contains("REFERENCIAS_RVT") || pp.Contains("CAD_GEORREF") || pp.StartsWith("JAN-")) ok++; }
    sb.AppendLine("  conferido (desejado aponta para a pasta da escola): " + ok); }
}
return sb.ToString();
