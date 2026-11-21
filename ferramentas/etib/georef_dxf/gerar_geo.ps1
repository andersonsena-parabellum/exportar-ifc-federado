# Gera as cópias _GEO (uma por vez) e o DXF de cada uma para conferência.
$S = "C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\b28e7087-be02-4c86-8417-721af249be58\scratchpad"
$lsp = ("$S\scripts\georef_geo.lsp") -replace '\\','/'
$P = "24-049-STK-XXX-ETIB-IMP-PE-"
# nome curto, rotação (graus, em torno de 0,0), tx, ty   (UTM SIRGAS 2000 / 24S)
$T = @(
  @("ESG-001-HIG-R00", "0", "545929.370875", "8716089.409625"),
  @("IN-001-ING-R03", "0.5674960469", "545931.222845", "8716090.163514"),
  @("EL-002-ELG-R01", "0.5674960469", "127352.385312", "60417.189666"),
  @("EL-001-ELG-R01", "38.2384588353", "5504381.199564", "1609035.590598"),
  @("URB-002-SIT-R06", "0", "-339.472979", "0"),
  @("URB-001-PAV-R07", "0", "0", "0"),
  @("TOP-001-PLT-R00", "0", "0", "0"),
  @("TER-001-SIT-R03", "0", "0", "0"),
  @("TER-001-PLT-R00", "0", "0", "0"),
  @("DRE-001-DRG-R02", "0", "0", "0"),
  @("DRE-002-DRG-R02", "0", "0", "0")
)
foreach ($t in $T) {
  $n = $P + $t[0]
  $geo = "$S\work\geo\${n}_GEO.dwg"
  if (Test-Path $geo) { "ja existe: $geo"; continue }
  $out = $geo -replace '\\','/'
  & "$S\scripts\run_one.ps1" -Dwg "$S\work\dwg\$n.dwg" -ScrLines @("SECURELOAD 0", "FILEDIA 0", "(load `"$lsp`")", "GEOREFGEO", "_.QUIT", "_Y") -Log "$S\work\out\$n.geo.log" -TimeoutSec 600 -EnvVars @{GEO_PARAMS = "$($t[1]) $($t[2]) $($t[3]) $out"}
  if (Test-Path $geo) {
    $dxf = ("$S\work\geo\${n}_GEO.dxf") -replace '\\','/'
    & "$S\scripts\run_one.ps1" -Dwg $geo -ScrLines @("FILEDIA 0", "_.DXFOUT `"$dxf`" 16", "_.QUIT", "_Y") -Log "$S\work\out\${n}_GEO.dxfout.log" -TimeoutSec 300
  } else { "FALHOU: $n" }
}
