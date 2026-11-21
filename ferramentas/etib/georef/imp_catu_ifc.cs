// ETIB Catu — exporta a cópia renivelada do IMP (…_COTA-PROJETO.rvt) em IFC4, nas coordenadas compartilhadas (UTM), e fecha sem salvar.
string B = @"D:\Projeto Modelagem\ETIB-CATU\REFERENCIAS_RVT\IMP\";
string ARQ = B + "24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.rvt";
string DIR = B + @"IFC\"; string NOME = "24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.ifc";
System.IO.Directory.CreateDirectory(DIR);
var log = new System.Text.StringBuilder("CATU-IMP-IFC\n");
Document e = document.Application.OpenDocumentFile(ARQ);
try {
  var o = new IFCExportOptions();
  o.FileVersion = IFCVersion.IFC4;
  o.ExportBaseQuantities = false;
  o.WallAndColumnSplitting = false;
  o.AddOption("SitePlacement", "0");          // coordenadas compartilhadas
  o.AddOption("ExportLinkedFiles", "false");
  o.AddOption("IncludeSiteElevation", "true");
  bool ok;
  using (var t = new Transaction(e, "IFC")) { t.Start(); ok = e.Export(DIR, NOME, o); t.RollBack(); }
  log.AppendLine("export " + ok + " -> " + DIR + NOME + " (" + (System.IO.File.Exists(DIR + NOME) ? new System.IO.FileInfo(DIR + NOME).Length.ToString() : "nao gerado") + " bytes)");
} catch (Exception x) { log.AppendLine("ERRO " + x.GetType().Name + ": " + x.Message); }
finally { e.Close(false); log.AppendLine("fechado sem salvar"); }
System.IO.File.WriteAllText(@"D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp\ifc_log.txt", log.ToString());
return log.ToString();
