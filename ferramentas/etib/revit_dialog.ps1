param([string]$Click = "", [int]$WaitSec = 0)
# Lê diálogos abertos do Revit (título "Autodesk Revit 2025", sem ser a janela principal)
# e, se -Click for informado, pressiona o botão com esse texto.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$deadline = (Get-Date).AddSeconds($WaitSec)
do {
  $pr = Get-Process Revit -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $pr) { "Revit não está aberto"; exit }
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $pr.Id)
  $wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
  $dlgs = @()
  foreach ($w in $wins) {
    $n = $w.Current.Name
    if ($n -notmatch 'MODELAGEM|Monitor|- \[') { $dlgs += $w }
    # diálogos modais também podem ser filhos da janela principal
    $kids = $w.FindAll([System.Windows.Automation.TreeScope]::Children, (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Window)))
    foreach ($k in $kids) { $dlgs += $k }
  }
  if ($dlgs.Count -gt 0) { break }
  if ($WaitSec -gt 0) { Start-Sleep -Milliseconds 500 }
} while ((Get-Date) -lt $deadline)
if ($dlgs.Count -eq 0) { "Nenhum diálogo aberto no Revit"; exit }
foreach ($d in $dlgs) {
  "=== DIÁLOGO: " + $d.Current.Name
  $all = $d.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $buttons = @()
  foreach ($e in $all) {
    $t = $e.Current.ControlType.ProgrammaticName
    $nm = $e.Current.Name
    $val = ""
    try { $vp = $e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern); $val = $vp.Current.Value } catch {}
    if ($t -eq "ControlType.Button") { $buttons += $e }
    elseif (($nm -and $nm.Trim()) -or ($val -and $val.Trim())) { "  [" + $t.Replace("ControlType.","") + "] " + $nm + $(if ($val) { " | " + $val } else { "" }) }
  }
  "  Botões: " + (($buttons | ForEach-Object { $_.Current.Name }) -join " | ")
  if ($Click) {
    $b = $buttons | Where-Object { $_.Current.Name -eq $Click } | Select-Object -First 1
    if (-not $b) { $b = $all | Where-Object { $_.Current.Name -eq $Click } | Select-Object -First 1 }
    if ($b) {
      $done = $false
      try { $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); $done = $true } catch {}
      if (-not $done) {
        # clique pela posição na tela (os botões dos diálogos de erro do Revit não expõem InvokePattern)
        Add-Type -Namespace U -Name M -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y); [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,int e); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);' -ErrorAction SilentlyContinue
        $r = $b.Current.BoundingRectangle
        [U.M]::SetForegroundWindow([IntPtr]$d.Current.NativeWindowHandle) | Out-Null
        Start-Sleep -Milliseconds 200
        [U.M]::SetCursorPos([int]($r.X + $r.Width/2), [int]($r.Y + $r.Height/2)) | Out-Null
        [U.M]::mouse_event(2,0,0,0,0); [U.M]::mouse_event(4,0,0,0,0)
      }
      "  >> Clicado: " + $Click
    }
    else { "  >> Botão '" + $Click + "' não encontrado" }
  }
}
