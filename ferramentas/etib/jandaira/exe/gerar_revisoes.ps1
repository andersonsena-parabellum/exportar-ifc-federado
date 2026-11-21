# Gera as cópias revisadas (R01) dos DWGs de projeto da Jandaíra em RELATORIOS\EXECUTIVO_R01\, a partir de CÓPIAS dos DWGs
# (nunca de PROJETO_ORIGINAL) e dos arquivos de comandos de exe_revisoes.py. Uso: gerar_revisoes.ps1 <pasta_com_as_copias_dwg>
param([Parameter(Mandatory)][string]$Copias)
$lsp = "D:/Projeto Modelagem/FERRAMENTAS/jandaira/exe/revisao_r01.lsp"
$OUT = "D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R01"
$J = Get-Content "$OUT\revisoes_R01.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $J.PSObject.Properties) {
  $arq = $p.Value.arquivo; $cmd = $p.Value.cmd
  $dst = "$OUT\${arq}_REV-R01.dwg"
  if (Test-Path $dst) { "ja existe: $dst"; continue }
  & "D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\run_one.ps1" -Dwg "$Copias\$arq.dwg" -ScrLines @("SECURELOAD 0", "FILEDIA 0", "(load `"$lsp`")", "REVR01", "_.QUIT", "_Y") -Log "$Copias\$arq.rev.log" -TimeoutSec 900 -EnvVars @{REV_CMD = $cmd; REV_OUT = $dst.Replace('\', '/')}
  if (-not (Test-Path $dst)) { "FALHOU: $arq" }
}
