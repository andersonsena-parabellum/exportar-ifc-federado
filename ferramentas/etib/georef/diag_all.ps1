# DiagnÃ³stico de todos os DWGs da pasta de trabalho (cÃ³pias), um por vez.
param([string]$W = "D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU", [int]$TimeoutSec = 600)
$G = "D:\Projeto Modelagem\FERRAMENTAS\georef"
Get-ChildItem "$W\src\*.dwg" | Sort-Object Length | ForEach-Object {
  $n = $_.BaseName
  if (Test-Path "$W\diag\$n.txt") { if ((Get-Content "$W\diag\$n.txt" | Select-String '^LAYOUT').Count -gt 0) { "JA FEITO: $n"; return } }
  & "$G\run_acc.ps1" -Dwg $_.FullName -Scr "$G\diag.scr" -Log "$W\log\diag_$n.txt" -TimeoutSec $TimeoutSec -EnvVars @{DIAG_TXT = "$($W.Replace('\','/'))/diag/$n.txt"}
}
"FIM"

