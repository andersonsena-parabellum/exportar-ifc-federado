# Roda o accoreconsole num DWG (SEMPRE uma cópia) com um script .scr, com timeout.
# Uso: run_acc.ps1 -Dwg "copia.dwg" -Scr "script.scr" -Log "saida.txt" [-TimeoutSec 600] [-EnvVars @{DUMP_TSV='D:/x.tsv'}]
param(
  [Parameter(Mandatory)] [string]$Dwg,
  [Parameter(Mandatory)] [string]$Scr,
  [Parameter(Mandatory)] [string]$Log,
  [int]$TimeoutSec = 600,
  [hashtable]$EnvVars = @{}
)
$acc = "C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe"
if ($Dwg -like "*PROJETO_ORIGINAL*") { throw "Recusado: nao rodar o console em PROJETO_ORIGINAL (use uma copia)" }
foreach ($k in $EnvVars.Keys) { [Environment]::SetEnvironmentVariable($k, $EnvVars[$k], "Process") }
$t0 = Get-Date
$p = Start-Process -FilePath $acc -ArgumentList "/i `"$Dwg`" /s `"$Scr`"" -PassThru -NoNewWindow `
      -RedirectStandardOutput $Log -RedirectStandardError "$Log.err"
if (-not $p.WaitForExit($TimeoutSec * 1000)) {
  $p.Kill()
  "TIMEOUT apos $TimeoutSec s: $Dwg"
} else {
  "OK ($([int]((Get-Date) - $t0).TotalSeconds) s, exit $($p.ExitCode)): $Dwg"
}
