# Lista diálogos Win32 clássicos (#32770) do Revit, com texto e botões, e opcionalmente clica um botão (BM_CLICK).
# Útil quando o revit_dialog.ps1 (UIAutomation) não enxerga o diálogo (ex.: aviso de hachura ao vincular DWG
# num documento aberto em segundo plano). Uso: .\revit_win32_dialog.ps1 [-Click "OK"] [-WaitSec 0]
param([string]$Click = "", [int]$WaitSec = 0)
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class RW32 {
  public delegate bool EP(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EP f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EP f, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int SendMessage(IntPtr h, int m, int w, StringBuilder l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public static List<IntPtr> Dialogs(uint pid) { var r = new List<IntPtr>(); EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); var c = new StringBuilder(64); GetClassName(h, c, 64); if (p == pid && IsWindowVisible(h) && c.ToString() == "#32770") r.Add(h); return true; }, IntPtr.Zero); return r; }
  public static List<string[]> Children(IntPtr par) { var r = new List<string[]>(); EnumChildWindows(par, (h, l) => { var t = new StringBuilder(4096); SendMessage(h, 0x000D, 4096, t); var c = new StringBuilder(64); GetClassName(h, c, 64); r.Add(new[] { h.ToString(), c.ToString(), t.ToString().Replace("\r", " ").Replace("\n", " ") }); return true; }, IntPtr.Zero); return r; }
}
'@
$deadline = (Get-Date).AddSeconds($WaitSec)
do {
  $p = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $p) { "Revit não está aberto"; exit }
  $ds = [RW32]::Dialogs([uint32]$p.Id)
  if ($ds.Count -gt 0) { break }
  if ((Get-Date) -lt $deadline) { Start-Sleep 2 }
} while ((Get-Date) -lt $deadline)
if ($ds.Count -eq 0) { "Nenhum diálogo Win32 (#32770) aberto no Revit"; exit }
foreach ($d in $ds) {
  $t = New-Object System.Text.StringBuilder 512; [void][RW32]::GetWindowText($d, $t, 512)
  "=== DIÁLOGO Win32 $d : $t"
  $kids = [RW32]::Children($d)
  foreach ($k in $kids) { if ($k[2]) { "  [$($k[1])] $($k[2])" } }
  if ($Click) {
    $b = $kids | Where-Object { $_[1] -eq "Button" -and ($_[2] -replace '&', '') -eq $Click } | Select-Object -First 1
    if ($b) { [void][RW32]::PostMessage([IntPtr][long]$b[0], 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero); "  >> Clicado: $Click" } else { "  (botão '$Click' não encontrado)" }
  }
}
