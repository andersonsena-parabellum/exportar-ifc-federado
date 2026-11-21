param([Parameter(Mandatory)][string]$Dwg, [Parameter(Mandatory)][string[]]$ScrLines, [Parameter(Mandatory)][string]$Log, [int]$TimeoutSec = 900, [hashtable]$EnvVars = @{})
# Roda UM accoreconsole (num DWG de cópia) com as linhas de script dadas; mata só o próprio PID no timeout.
if ($Dwg -like "*PROJETO_ORIGINAL*") { throw "Recusado: nao rodar o console em PROJETO_ORIGINAL (use uma copia)" }
$acc = "C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe"
$scr = [IO.Path]::ChangeExtension($Log, ".scr")
[IO.File]::WriteAllText($scr, (($ScrLines + @("")) -join "`r`n"))
foreach ($k in $EnvVars.Keys) { [Environment]::SetEnvironmentVariable($k, $EnvVars[$k], "Process") }
$t0 = Get-Date
$p = Start-Process $acc -ArgumentList "/i `"$Dwg`" /s `"$scr`" /l pt-BR" -PassThru -WindowStyle Hidden -RedirectStandardOutput $Log
if (-not $p.WaitForExit($TimeoutSec * 1000)) { Stop-Process -Id $p.Id -Force; "TIMEOUT ($TimeoutSec s): $Dwg" }
else { "OK ({0:N0} s): {1}" -f ((Get-Date) - $t0).TotalSeconds, $Dwg }
