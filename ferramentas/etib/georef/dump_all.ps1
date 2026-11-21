# Dump (accoreconsole) de várias cópias de DWG. Modo: INS (dump_deep só inserções/textos/círculos), DEEP (dump_deep completo) ou FLAT (dump_dwg, só nível superior).
param([string]$W = "D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU", [string]$Mode = "INS", [string[]]$Filtro = @("*"), [int]$TimeoutSec = 900, [string]$Excl = "")
$G = "D:\Projeto Modelagem\FERRAMENTAS\georef"
$scr = if ($Mode -eq "FLAT") { "$G\dump.scr" } else { "$G\dump_deep.scr" }
$pref = $Mode.ToLower()
Get-ChildItem "$W\src\*.dwg" | Where-Object { $n = $_.Name; ($Filtro | Where-Object { $n -like $_ }).Count -gt 0 } | Sort-Object Length | ForEach-Object {
  $n = $_.BaseName
  $out = "$($W.Replace('\','/'))/dump/$($pref)_$n.tsv"
  $ev = @{ DUMP_TSV = $out; DUMP_MODE = $(if ($Mode -eq "INS") { "INS" } else { "ALL" }) }
  if ($Excl) { $ev["DUMP_EXCL"] = $Excl } else { [Environment]::SetEnvironmentVariable("DUMP_EXCL", $null, "Process") }
  & "$G\run_acc.ps1" -Dwg $_.FullName -Scr $scr -Log "$W\log\$($pref)_$n.txt" -TimeoutSec $TimeoutSec -EnvVars $ev
}
"FIM"
