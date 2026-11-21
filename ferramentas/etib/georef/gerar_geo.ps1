# Gera os DWGs georreferenciados de uma escola, um console por vez, a partir dos JSON de transformação.
#   _GEO: cópia movida para UTM (geo.lsp), nada apagado.        _REF: base limpa para vincular no Revit (ref.lsp).
# Uso: gerar_geo.ps1 [-Escola ETIB-CATU] [-W pasta_de_trabalho] [-So @("AF","SIT_REF")]
param(
  [string]$Escola = "ETIB-CATU",
  [string]$W = "D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU",
  [string[]]$So = @()
)
$G = "D:\Projeto Modelagem\FERRAMENTAS\georef"
$OUT = "D:\Projeto Modelagem\$Escola\CAD_GEORREFERENCIADO"
$P = "24-049-CAU-RNV-ETIB-"
function F([double]$v) { $v.ToString("0.00000000", [Globalization.CultureInfo]::InvariantCulture) }
function Scr([string]$nome, [string[]]$lsps, [string[]]$cmds, [string]$saida, [bool]$wblock = $false) {
  $l = @("SECURELOAD 0", "FILEDIA 0", "CMDDIA 0")
  foreach ($x in $lsps) { $l += "(load `"$($G.Replace('\','/'))/$x`")" }
  $l += $cmds
  # WBLOCK "*" quando o SAVEAS falha por reator salvo no desenho (TER: "_cvo-proxy.axvlo-dump")
  if ($wblock) { $l += "(command `"_.-WBLOCK`" `"$($saida.Replace('\','/'))`" `"*`")" } else { $l += "_.SAVEAS 2018 `"$($saida.Replace('\','/'))`"" }
  $l += "_.QUIT"; $l += "_Y"
  $f = "$W\scr_$nome.scr"
  [IO.File]::WriteAllText($f, ($l -join "`r`n") + "`r`n", (New-Object Text.UTF8Encoding $false))
  $f
}
$base = Get-Content "$OUT\transformacao_SIT_para_UTM.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$tarefas = @()
foreach ($tag in @("AF","ESG","DRE","INC","EL1","EL2")) {
  $j = Get-Content "$OUT\transformacao_${tag}_local_para_UTM.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $rf = if (Test-Path "$W\ref_$tag.txt") { "$W\ref_$tag.txt" } else { $null }   # lixo a milhares de km (ex.: hachuras do EL)
  $tarefas += @{ nome = $tag; src = $j.fonte; saida = $j.saida; dx = $j.rigid.t[0]; dy = $j.rigid.t[1]; ref = $rf }
}
$tarefas += @{ nome = "SIT_GEO"; src = "${P}IMP-PE-URB-001-SIT-R02.dwg"; saida = "${P}IMP-PE-URB-001-SIT-R02_GEO.dwg"; dx = $base.SIT_R02_para_UTM.t[0]; dy = $base.SIT_R02_para_UTM.t[1]; ref = $null }
$tarefas += @{ nome = "SIT_REF"; src = "${P}IMP-PE-URB-001-SIT-R02.dwg"; saida = "${P}IMP-PE-URB-001-SIT-R02_REF.dwg"; dx = $base.SIT_R02_para_UTM.t[0]; dy = $base.SIT_R02_para_UTM.t[1]; ref = "$W\ref_SIT.txt" }
$tarefas += @{ nome = "TOP_REF"; src = "${P}IMP-PE-TOP-001-PLT-R00.dwg"; saida = "${P}IMP-PE-TOP-001-PLT-R00_REF.dwg"; dx = $null; dy = $null; ref = "$W\ref_TOP.txt" }
$tarefas += @{ nome = "TER-IMP_REF"; src = "${P}TER-IMP-001-R00.dwg"; saida = "${P}TER-IMP-001-R00_REF.dwg"; dx = $null; dy = $null; ref = "$W\ref_TER-IMP.txt"; wblock = $true }

foreach ($t in $tarefas) {
  if ($So.Count -gt 0 -and -not ($So -contains $t.nome)) { continue }
  $saida = "$OUT\$($t.saida)"
  if (Test-Path $saida) { "JA EXISTE (nao sobrescrevo): $saida"; continue }
  $lsps = @(); $cmds = @(); $ev = @{}
  if ($null -ne $t.dx) { $lsps += "geo.lsp"; $cmds += "GEO"; $ev["GEO_DX"] = (F $t.dx); $ev["GEO_DY"] = (F $t.dy); $ev["GEO_ROT"] = "0" }
  if ($t.ref) { $lsps += "ref.lsp"; $cmds += "REFLIMPA"; $ev["REF_TXT"] = $t.ref.Replace('\','/') }
  $scr = Scr $t.nome $lsps $cmds $saida ([bool]$t.wblock)
  & "$G\run_acc.ps1" -Dwg "$W\src\$($t.src)" -Scr $scr -Log "$W\log\geo_$($t.nome).txt" -TimeoutSec 900 -EnvVars $ev
  $txt = (Get-Content "$W\log\geo_$($t.nome).txt" -Encoding Unicode -ErrorAction SilentlyContinue) -join " "
  $m = [regex]::Matches($txt, "(GEO_ENTIDADES=\d+|GEO_OK[^C]*|REF_OK[^C]*|REF_NAO_EXPLODIU \S+ \S+|REF_SEM_HANDLE \S+)")
  "   " + (($m | ForEach-Object { $_.Value.Trim() }) -join " | ")
  if (Test-Path $saida) { "   gravado: $([math]::Round((Get-Item $saida).Length/1MB,1)) MB" } else { "   FALHOU: $saida nao foi gravado" }
}
"FIM"
