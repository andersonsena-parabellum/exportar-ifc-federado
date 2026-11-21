# Fecha, por até 8 min, os diálogos previsíveis da abertura/vínculo (referências não solucionadas, avisos de hachura)
$deadline = (Get-Date).AddMinutes(8)
while ((Get-Date) -lt $deadline) {
  foreach ($b in @("Ignorar e continuar","OK","Fechar","Não")) {
    $r = & "D:\Projeto Modelagem\FERRAMENTAS\revit_dialog.ps1" -Click $b 2>$null
    if ($r -and ($r -join "`n") -match "DIÁLOGO") { Write-Output ((Get-Date).ToString("HH:mm:ss") + " " + (($r -join " | ").Substring(0,[Math]::Min(300,($r -join " | ").Length)))) }
  }
  Start-Sleep -Seconds 3
}
