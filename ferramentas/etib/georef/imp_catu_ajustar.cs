// ETIB Catu — renivela uma CÓPIA do IMP as built na cota dos projetos de base (pedido do Anderson, 19/10/2026).
// Original intocado: REFERENCIAS_RVT\IMP\24-049-CAU-RNV-ETIB-IMP.rvt -> cópia ..._COTA-PROJETO.rvt (sobrescreve a cópia anterior, se houver).
// Toposolids: cada vértice vai para a superfície-alvo (alvo_raster.txt, cota absoluta: CT das caixas + SIT + TER + TOP); fora da área
//   do alvo o vértice anda o mesmo Δz da borda (alvo_dz_fora.txt), sem degrau. Subdivisões acompanham o hospedeiro.
// Pisos e muros: andam em bloco o Δz de ajuste_pisos.txt (mediana alvo − IMP sob cada um). Salva a cópia e fecha.
string B = @"D:\Projeto Modelagem\ETIB-CATU\REFERENCIAS_RVT\IMP\";
string ARQ0 = B + "24-049-CAU-RNV-ETIB-IMP.rvt", ARQ = B + "24-049-CAU-RNV-ETIB-IMP_COTA-PROJETO.rvt";
string W = @"D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\imp\";
var ci = System.Globalization.CultureInfo.InvariantCulture; const double F = 0.3048;
var log = new System.Text.StringBuilder("CATU-IMP-AJUSTE\n");
System.Func<string, double[]> Cab = fn => { var c = System.IO.File.ReadAllLines(fn)[0].Split(' '); return new[] { double.Parse(c[0], ci), double.Parse(c[1], ci), double.Parse(c[2], ci), double.Parse(c[3], ci), double.Parse(c[4], ci) }; };
System.Func<string, double[,]> Grade = fn => { var L = System.IO.File.ReadAllLines(fn); var h = Cab(fn); int nx = (int)h[3], ny = (int)h[4]; var M = new double[ny, nx];
  for (int j = 0; j < ny; j++) { var v = L[j + 1].Split(' '); for (int i = 0; i < nx; i++) M[j, i] = v[i] == "nan" ? double.NaN : double.Parse(v[i], ci); } return M; };
var hA = Cab(W + "alvo_raster.txt"); var GA = Grade(W + "alvo_raster.txt"); var GD = Grade(W + "alvo_dz_fora.txt");
System.Func<double[,], double, double, double> Amostra = (M, x, y) => {
  double fx = (x - hA[0]) / hA[2], fy = (y - hA[1]) / hA[2]; int i = (int)System.Math.Floor(fx), j = (int)System.Math.Floor(fy);
  if (i < 0 || j < 0 || i >= (int)hA[3] - 1 || j >= (int)hA[4] - 1) return double.NaN;
  double tx = fx - i, ty = fy - j;
  return M[j, i] * (1 - tx) * (1 - ty) + M[j, i + 1] * tx * (1 - ty) + M[j + 1, i] * (1 - tx) * ty + M[j + 1, i + 1] * tx * ty; };
var dzEl = new System.Collections.Generic.Dictionary<long, double>();
foreach (var l in System.IO.File.ReadAllLines(W + "ajuste_pisos.txt")) { var c = l.Split(' '); if (c.Length == 3) dzEl[long.Parse(c[1])] = double.Parse(c[2], ci); }
System.IO.File.Copy(ARQ0, ARQ, true);
var app = document.Application;
Document e = app.OpenDocumentFile(ARQ);
try {
  Transform T = e.ActiveProjectLocation.GetTotalTransform(); Transform S = T.Inverse; Transform Si = T;   // S: interno -> compartilhado (conferido no imp_catu_ler.cs)
  int nts = 0, nv = 0, nvf = 0, npi = 0, npa = 0;
  using (var t = new Transaction(e, "Cota dos projetos de base")) {
    t.Start();
    foreach (Toposolid ts in new FilteredElementCollector(e).OfClass(typeof(Toposolid))) {
      try { if (ts.HostTopoId != ElementId.InvalidElementId) { log.AppendLine("subdivisao " + ts.Id.Value + " acompanha o hospedeiro"); continue; } } catch { }
      var ed = ts.GetSlabShapeEditor(); if (ed == null) { log.AppendLine("sem editor " + ts.Id.Value); continue; }
      if (!ed.IsEnabled) ed.Enable();
      var orig = new System.Collections.Generic.List<XYZ>(); foreach (SlabShapeVertex v in ed.SlabShapeVertices) orig.Add(v.Position);
      if (orig.Count == 0) { log.AppendLine("sem vertices " + ts.Id.Value); continue; }
      // referência do deslocamento: um vértice com deslocamento 0
      SlabShapeVertex v0 = null; foreach (SlabShapeVertex v in ed.SlabShapeVertices) { v0 = v; break; }
      XYZ p0 = v0.Position; ed.ModifySubElement(v0, 0.0); e.Regenerate();
      double zRef = double.NaN;
      foreach (SlabShapeVertex v in ed.SlabShapeVertices) if (System.Math.Abs(v.Position.X - p0.X) < 1e-4 && System.Math.Abs(v.Position.Y - p0.Y) < 1e-4) zRef = v.Position.Z;
      if (double.IsNaN(zRef)) { log.AppendLine("sem referencia " + ts.Id.Value); continue; }
      var alvo = new System.Collections.Generic.List<double>();
      foreach (var p in orig) {
        var w = S.OfPoint(p); double x = w.X * F, y = w.Y * F, z = w.Z * F;
        double za = Amostra(GA, x, y); if (double.IsNaN(za)) { double d = Amostra(GD, x, y); za = double.IsNaN(d) ? z : z + d; nvf++; }
        alvo.Add(Si.OfPoint(new XYZ(w.X, w.Y, za / F)).Z);
      }
      int k = 0;
      foreach (SlabShapeVertex v in ed.SlabShapeVertices) {
        var p = v.Position; int best = -1; double bd = 1e9;
        for (int q = 0; q < orig.Count; q++) { double dd = System.Math.Abs(orig[q].X - p.X) + System.Math.Abs(orig[q].Y - p.Y); if (dd < bd) { bd = dd; best = q; } if (dd < 1e-6) break; }
        if (best >= 0) { ed.ModifySubElement(v, alvo[best] - zRef); k++; }
      }
      nts++; nv += k; log.AppendLine("toposolid " + ts.Id.Value + " " + ts.Name + ": " + k + " vertices");
    }
    foreach (Floor fl in new FilteredElementCollector(e).OfClass(typeof(Floor))) {
      double dz; if (!dzEl.TryGetValue(fl.Id.Value, out dz)) continue;
      var pr = fl.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM); if (pr == null || pr.IsReadOnly) { log.AppendLine("piso sem offset " + fl.Id.Value); continue; }
      pr.Set(pr.AsDouble() + dz / F); npi++; log.AppendLine("piso " + fl.Id.Value + " dz " + dz.ToString("0.00", ci));
    }
    foreach (Wall wa in new FilteredElementCollector(e).OfClass(typeof(Wall))) {
      double dz; if (!dzEl.TryGetValue(wa.Id.Value, out dz)) continue;
      var pb = wa.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET); if (pb == null || pb.IsReadOnly) continue;
      pb.Set(pb.AsDouble() + dz / F);
      var ht = wa.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE); var pt = wa.get_Parameter(BuiltInParameter.WALL_TOP_OFFSET);
      if (ht != null && ht.AsElementId() != ElementId.InvalidElementId && pt != null && !pt.IsReadOnly) pt.Set(pt.AsDouble() + dz / F);
      npa++;
    }
    var fo = t.GetFailureHandlingOptions(); fo.SetClearAfterRollback(true); t.SetFailureHandlingOptions(fo);
    t.Commit();
  }
  log.AppendLine("toposolids " + nts + " | vertices " + nv + " (fora do alvo " + nvf + ") | pisos " + npi + " | muros " + npa);
  e.Save(); log.AppendLine("salvo " + ARQ);
} catch (Exception x) { log.AppendLine("ERRO " + x.GetType().Name + ": " + x.Message); }
finally { e.Close(false); log.AppendLine("fechado"); }
System.IO.File.WriteAllText(W + "ajuste_log.txt", log.ToString());
return log.ToString();
