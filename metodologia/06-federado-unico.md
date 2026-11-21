# 06. Federado único

Padrão aprovado em 29/10/2026 no piloto da escola A (R04) e aplicado depois a todas as escolas. O método completo, com scripts, está na skill [`federado-unico-etib`](../federado-unico-etib/SKILL.md) deste repositório; aqui fica o resumo e as regras.

## O que é

Um só arquivo IFC4 da escola inteira, montado na nuvem:

```
IfcProject "ETIB <escola> — modelo federado único"
└─ IfcSite "ETIB <escola>"          terreno: lote (verde opaco) e entorno (transparente)
   ├─ IfcBuilding "Implantação — redes externas"   redes compatibilizadas, por sistema
   ├─ IfcBuilding "<MÓD> — <nome>"                 um por módulo: estrutura as built + arquitetura completa
   └─ IfcBuilding "URB — Urbanização"              divisa, reservatórios, platôs, pisos externos, piso tátil
```

Cada elemento leva `Dados_ETIB` (disciplina, sistema, módulo, origem). Instalações internas dos módulos não entram.

## Fontes

- Redes externas compatibilizadas e terreno as built: a entrega da escola.
- Estrutura as built dos módulos.
- Arquitetura **completa** de cada módulo (paredes, portas, janelas, pisos, forros, cobertura, louças, mobiliário), de preferência do RVT de arquitetura da construtora exportado em IFC4 no Revit do notebook; sem RVT, o modelo padrão ETIB posicionado na implantação.
- Urbanização: RVT da implantação + planta de situação e de pavimentação (DXF).

## Ajustes que sempre se conferem

- Cota do RVT da implantação contra o terreno as built (na escola A estava 0,565 m abaixo): `p0_cota_rvt.py`.
- Posição em planta do Revit contra as redes já entregues (na escola B, 22 cm): tudo segue o sistema das redes.
- Módulo do RVT na posição do vínculo dentro da implantação; cada RVT de módulo exportado sozinho na origem interna e posicionado na nuvem pela linha do próprio arquivo (arquitetura e estrutura podem ter origens diferentes).
- Tirar dos platôs a projeção dos pisos dos módulos (senão piso duplo); tirar muro e gradil do RVT que repetem a divisa, o que estiver fora do lote e o terreno do RVT.
- Vínculo ausente (ex.: ETE) não entra e é citado no LEIA-ME.

## Passos (skill)

`p0` cota do RVT → `p1` módulos → `p2` divisa → `p3` urbanização → `p4` terreno recortado no lote → `p5` montagem → `p6` conferência → `p7` prévias → `p8` pacote. Cerca de 1h30 na nuvem.

## Antes de entregar

- Validação IFC4 = 0 erro; nenhum elemento sem edificação ou sem geometria; GUID repetido = 0; sem propriedade de trabalho; unidades SI e ângulo em radiano em todo arquivo-fonte; caixa envolvente por módulo e cotas coerentes.
- Prévias 3D (geral e de perto) e planta.
- Pacote `envio/ETIB-<ESCOLA>-FEDERADO-UNICO_<data>_R<nn>/` com `03_IFC`, `04_PREVIA`, `LEIA-ME` e `.zip`. Arquivo grande vai ao Drive em partes.
