# Exporta para DXF (accoreconsole, um por vez) os DWGs de uma pasta. Padrão: as cópias de trabalho em <W>\src -> <W>\dxf.
param([string]$W = "D:\Projeto Modelagem\FERRAMENTAS\georef\work\<ESCOLA>", [string]$Src = "", [string]$Dst = "", [string[]]$Filtro = @("*"), [int]$TimeoutSec = 600)
$G = "D:\Projeto Modelagem\FERRAMENTAS\georef"
if (-not $Src) { $Src = "$W\src" }
if (-not $Dst) { $Dst = "$W\dxf" }
New-Item -ItemType Directory -Force $Dst | Out-Null
Get-ChildItem "$Src\*.dwg" | Where-Object { $n = $_.Name; ($Filtro | Where-Object { $n -like $_ }).Count -gt 0 } | Sort-Object Length | ForEach-Object {
  $n = $_.BaseName
  if (Test-Path "$Dst\$n.dxf") { "JA FEITO: $n"; return }
  & "$G\run_acc.ps1" -Dwg $_.FullName -Scr "$G\dxfout.scr" -Log "$W\log\dxf_$n.txt" -TimeoutSec $TimeoutSec -EnvVars @{DXF_OUT = "$($Dst.Replace('\','/'))/$n.dxf"}
}
"FIM"
