// Parte 0: abre o modelo em segundo plano (se ainda não estiver aberto) e devolve o erro real, se houver.
string ARQ = @"@@ARQ@@"; var app = document.Application;
foreach (Document d in app.Documents) if (!d.IsLinked && d.PathName == ARQ) return "ABRIR ja aberto: " + d.Title;
var t0 = System.DateTime.Now;
bool AUD = @@AUDIT@@;
try { Document e; if (AUD) { var oo = new OpenOptions(); oo.Audit = true; e = app.OpenDocumentFile(ModelPathUtils.ConvertUserVisiblePathToModelPath(ARQ), oo); } else e = app.OpenDocumentFile(ARQ); return "ABRIR ok: " + e.Title + " em " + (System.DateTime.Now - t0).TotalSeconds.ToString("0") + " s"; }
catch (Exception ex) { return "ABRIR ERRO " + ex.GetType().Name + ": " + ex.Message + (ex.InnerException != null ? " | " + ex.InnerException.Message : ""); }
