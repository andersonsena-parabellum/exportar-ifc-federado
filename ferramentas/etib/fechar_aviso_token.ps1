param([int]$Minutos = 10, [string]$Texto = "Nenhum token fornecido")
# Fecha (com OK) apenas as caixas de mensagem do Revit que contenham $Texto.
# Usado para o aviso em loop do suplemento DarivaBIM quando está sem login.
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class TokBox {
  public delegate bool EP(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EP f, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EP f, IntPtr l);
  [DllImport("user32.dll")] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public static int Close(uint pid, string txt) {
    int n = 0;
    EnumWindows((h, l) => {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p != pid || !IsWindowVisible(h)) return true;
      var cls = new StringBuilder(64); GetClassName(h, cls, 64);
      if (cls.ToString() != "#32770") return true;
      bool hit = false;
      EnumChildWindows(h, (c, l2) => { var s = new StringBuilder(512); GetWindowText(c, s, 512); if (s.ToString().Contains(txt)) hit = true; return true; }, IntPtr.Zero);
      if (hit) { PostMessage(h, 0x0111, (IntPtr)1, IntPtr.Zero); n++; }   // WM_COMMAND IDOK
      return true;
    }, IntPtr.Zero);
    return n;
  }
}
"@
$fim = (Get-Date).AddMinutes($Minutos); $total = 0
while ((Get-Date) -lt $fim) {
  $pr = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $pr) { break }
  $total += [TokBox]::Close([uint32]$pr.Id, $Texto)
  Start-Sleep -Milliseconds 400
}
"Avisos fechados: $total"
