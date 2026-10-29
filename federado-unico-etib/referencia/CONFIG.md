# Configuração da escola (escola.json)

Um JSON por escola, na pasta FEDERADO_UNICO dela. Caminhos relativos à `raiz`. Exemplo completo: `escolas/JDI.json` (Jandaíra R04).

## Geral
| chave | o que é | como achar |
|---|---|---|
| `escola`, `sigla`, `pasta_envio` | nome, sigla de 3 letras (JDI, ALH...), nome da pasta de envio sem acento (JANDAIRA) | lista mestra |
| `nome_completo`, `contrato` | nome oficial do colégio e contrato, vão no IfcSite e no projeto | carimbo das pranchas |
| `raiz`, `pasta_saidas` | pasta base dos caminhos; onde gravar trabalho/, saida/, envio/ | — |
| `georref` | EPSG, zona, `e0`/`n0` = origem do arquivo | **a mesma dos IFC já entregues** da escola (IfcMapConversion deles) |
| `cota.min`/`max` | faixa razoável de cota (conferência) | terreno ± 10 m |
| `cota.piso_max` | lajes com topo abaixo disto são "piso de módulo" (recorte dos platôs) e o que está acima é cobertura na prévia | piso dos módulos + ~1,5 m |
| `cota.pegada_acima_de` | o que está acima disto conta como construído (sai dos pisos externos) | terreno − ~1 m |

## Redes, terreno e estrutura
- `terreno_asbuilt`: IFC do terreno as built (IfcGeographicElement) — o mesmo das redes.
- `redes`: IFC das redes externas compatibilizadas (vão todas para "Implantação").
- `estrutura`: lista de arquivos. Arquivo com vários módulos: `"modulo": "EST"`, `modulo_por_sistema` (sistema do Dados_ETIB → módulo), `modulo_outros`, `excluir_sistemas` (o que vem de outro arquivo). Arquivo de um módulo só: `"modulo": "BP4"`. `prefixo` vai no nome dos grupos.

- `estrutura_rvt`: estrutura exportada dos RVT da construtora (ECC, FUN, EMT), um item por arquivo: `{"arquivo", "modulo", "posicao", "origem"}`. O p1 posiciona cada um pela linha do PRÓPRIO arquivo (ARQ e estrutura do mesmo módulo podem ter origens diferentes) e grava Dados_ETIB (EST, EST-<MÓD>). Exemplo: Alagoinhas.

## Módulos (`modulos`)
Um por módulo; a chave é a sigla (BP4, GUA, SB3, VST, QDC, CDG, CDR, CPS...) e precisa bater com a do `modulo_por_sistema`.
- `nome`: nome da IfcBuilding ("GUA — Guarita").
- `arquivo`: IFC exportado do RVT da construtora (preferido) ou IFC padrão ETIB.
- `posicao`: `{"giro_graus", "e", "n", "dz"}` quando o arquivo está nas coordenadas próprias do módulo e se conhece a origem dele em UTM (vínculo dentro do RVT da implantação, ver EXPORTAR_RVT.md); `{"giro_graus", "x", "y", "dz"}` quando a translação já está em coordenadas do projeto (padrão encaixado na implantação); `{"dz": ...}` com e = n = 0 quando o arquivo já está em UTM absoluto. `dz` = cota absoluta do zero do arquivo (ex.: piso as built − cota do piso no RVT).
- `manter_estrutura` (padrão true): false tira pilares e vigas do padrão quando a estrutura as built vem de outro arquivo.
- `manter_nomes_com`: exceções da limpeza de instalações (ex.: `["CALHA"]` mantém as calhas da cobertura).
- `excluir_classes_extra`: classes a mais para tirar (ex.: `["IfcFlowTerminal"]` nas calhas do campo, que valem as canaletas da drenagem).
- `origem`: texto que vai no Dados_ETIB e no LEIA-ME.

Conferir a posição: no p6 a distância "arquitetura × estrutura" de cada módulo deve ficar abaixo de ~1,5 m, e nas prévias o módulo cai sobre os pilares.

## Divisa (`divisa`, DXF da situação em UTM)
- `muros` / `gradis`: lista de pares `{"a": handle, "b": handle}` = as duas faces do muro (polilinhas). Face partida em duas polilinhas no DXF: `"a": ["B177", "1068C"]` emenda na ordem (Alagoinhas). `a_max_pontos` corta a polilinha quando ela continua além do muro. Achar os handles: abrir o DXF no AutoCAD (LIST na polilinha) ou com ezdxf (`for e in msp.query('LWPOLYLINE'): print(e.dxf.handle, e.dxf.layer, len(e))`).
- `alturas`: muro, gradil, mureta, reservatório, base (adotadas quando a situação não cota: citar no LEIA-ME).
- `reservatorios`: prefixo do nome do bloco do tanque, raio mínimo do círculo, volume e descrição.

## Urbanização do RVT (`urbanizacao_rvt`)
- `arquivo`, `posicao` (normalmente só `dz`, do p0_cota_rvt.py), `distancia_divisa` (1,5 m), `excluir_areas` (polígonos em coordenadas do projeto onde a situação as built manda, ex.: reservatório de projeto que mudou), `origem`.

## Terreno e pisos (`terreno`, DXF da pavimentação em UTM)
- `lote.camada`: camada da hachura cujo maior contorno é o lote. Sem hachura do lote: `{"dxf": <situação>, "polilinha": handle}` (ex.: PERIMETRO da situação; fecha sozinha).
- `gramado.camada` / `padrao`: hachura da área gramada (maior), fica sem piso. Gramado em várias hachuras: `"todas": true` junta todas da camada/padrão.
- `excluir`: `{"circulo": [x, y, r]}`, `{"poligono": [...]}` ou `{"hachura_maior": camada, "folga": m}` (ex.: pista do campo, ETE).
- `janela_local`: [xmin, ymin, xmax, ymax] em coordenadas do projeto, para ignorar cópias da planta deslocadas no mesmo DXF.
- `piso_topo` (0,03) e `piso_espessura` (0,10).

## LEIA-ME (`leia_me`)
`substitui`, `mudou` (lista), `adotados` (lista), `nao_entra` (lista). O resto (edificações, contagens, coordenadas, conferência) o p8 escreve sozinho.
