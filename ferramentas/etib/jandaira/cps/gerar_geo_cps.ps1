# Gera as cópias _GEO (UTM) das pranchas do campo society da Jandaíra em CAD_GEORREFERENCIADO\, a partir de CÓPIAS dos DWGs
# (nunca de PROJETO_ORIGINAL). Parâmetros de transf_cps.py (JSON ao lado). Uso: gerar_geo_cps.ps1 <pasta_com_as_copias_dwg>
param([Parameter(Mandatory)][string]$Copias)
$lsp = "D:/Projeto Modelagem/FERRAMENTAS/georef_dxf/georef_geo.lsp"
$CAD = "D:\Projeto Modelagem\ETIB-JANDAIRA\CAD_GEORREFERENCIADO"
foreach ($k in @("DRE-001-DRG-R01", "EL-001-ELG-R01", "IN-001-ING-R01")) {
  $n = "24-049-JDI-CTO-ETIB-CPS-PE-$k"
  $j = Get-Content "$CAD\transformacao_CPS_${k}_local_para_UTM.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $geo = "$CAD\${n}_GEO.dwg"
  if (Test-Path $geo) { "ja existe: $geo"; continue }
  $out = $geo.Replace('\', '/')
  $par = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0} {1} {2} {3}", $j.rot_utm_graus, $j.t_utm[0], $j.t_utm[1], $out)   # cultura pt-BR poria vírgula e o atof do LISP cortaria a fração
  & "D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\run_one.ps1" -Dwg "$Copias\$n.dwg" -ScrLines @("SECURELOAD 0", "FILEDIA 0", "AUPREC 8", "LUPREC 8", "_.AUDIT _Y", "(load `"$lsp`")", "GEOREFGEO", "_.QUIT", "_Y") -Log "$Copias\$n.geo.log" -TimeoutSec 600 -EnvVars @{GEO_PARAMS = $par}
  if (-not (Test-Path $geo)) { "FALHOU: $n" }
}
