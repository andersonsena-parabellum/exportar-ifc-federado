// ETIB Catu — lê fundação e estrutura as built (FUN/ECC dos blocos em REFERENCIAS_RVT) SEM salvar: elementos estruturais
// (fundações, pilares, vigas, paredes estruturais) com caixa envolvente em coordenadas INTERNAS do próprio modelo (m).
// A posição em UTM vem depois, pela transformação do vínculo no IMP (work/CATU/imp/imp_vinculos.csv), em Python.
// Abre cada RVT em segundo plano e fecha sem salvar (só os que este script abriu).
string B = @"D:\Projeto Modelagem\ETIB-CATU\REFERENCIAS_RVT\";
string OUT = @"D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp\fun_@@NOME@@.csv";
string[] ARQS = { @"@@ARQ@@" };
var app = document.Application; var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
var cats = new System.Collections.Generic.HashSet<long> { (long)BuiltInCategory.OST_StructuralFoundation, (long)BuiltInCategory.OST_StructuralColumns,
  (long)BuiltInCategory.OST_StructuralFraming, (long)BuiltInCategory.OST_Walls, (long)BuiltInCategory.OST_Floors };
var sb = new System.Text.StringBuilder("arquivo;id;categoria;familia;tipo;x;y;z;bbminx;bbminy;bbminz;bbmaxx;bbmaxy;bbmaxz;rot\n");
var log = new System.Text.StringBuilder("CATU-FUN-LER\n");
System.Func<double, string> M = v => (v * F).ToString("0.0000", ci);
foreach (var rel in ARQS) {
  string arq = B + rel; if (!System.IO.File.Exists(arq)) { log.AppendLine("sem arquivo: " + rel); continue; }
  Document e = null; bool abri = false;
  foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == arq) e = d;
  try {
    if (e == null) { e = app.OpenDocumentFile(arq); abri = true; }
    int n = 0; string nome = System.IO.Path.GetFileName(arq);
    foreach (Element el in new FilteredElementCollector(e).WhereElementIsNotElementType()) {
      if (el.Category == null || !cats.Contains(el.Category.Id.Value)) continue;
      var bb = el.get_BoundingBox(null); if (bb == null) continue;
      double x = (bb.Min.X + bb.Max.X) / 2, y = (bb.Min.Y + bb.Max.Y) / 2, z = (bb.Min.Z + bb.Max.Z) / 2, rot = 0; string fam = "", tipo = el.Name;
      var fi = el as FamilyInstance;
      if (fi != null) { fam = fi.Symbol != null ? fi.Symbol.FamilyName : ""; var lp = fi.Location as LocationPoint; if (lp != null) { x = lp.Point.X; y = lp.Point.Y; z = lp.Point.Z; try { rot = lp.Rotation * 180 / System.Math.PI; } catch { } } }
      sb.Append(nome + ";" + el.Id.Value + ";" + el.Category.Name + ";" + fam + ";" + tipo + ";" + M(x) + ";" + M(y) + ";" + M(z) + ";" + M(bb.Min.X) + ";" + M(bb.Min.Y) + ";" + M(bb.Min.Z) + ";"
        + M(bb.Max.X) + ";" + M(bb.Max.Y) + ";" + M(bb.Max.Z) + ";" + rot.ToString("0.000", ci) + "\n"); n++;
    }
    var pbp = BasePoint.GetProjectBasePoint(e); var sp = BasePoint.GetSurveyPoint(e);
    log.AppendLine(nome + ": " + n + " elementos | PBP " + pbp.Position + " / " + pbp.SharedPosition + " | SP " + sp.SharedPosition);
  } catch (Exception x) { log.AppendLine("ERRO " + rel + ": " + x.Message); }
  finally { if (abri && e != null) { e.Close(false); log.AppendLine("  fechado sem salvar"); } }
}
System.IO.File.WriteAllText(OUT, sb.ToString());
System.IO.File.WriteAllText(OUT.Replace(".csv", "_log.txt"), log.ToString());
return log.ToString();
