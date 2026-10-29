---
name: federado-unico-etib
description: Monta o IFC federado único de uma escola ETIB (contrato QG 24-049 / CONDER): terreno recortado no lote, redes externas, estrutura as built, arquitetura completa dos módulos, divisa, reservatórios e urbanização, num só IFC4 conferido. Use quando pedirem "federado único", "modelo federado da escola" ou refazer o federado de uma escola no padrão da Jandaíra R04.
---

# Federado único ETIB

Padrão aprovado pelo Daniel em 29/10/2026 no piloto da Jandaíra (R04). O resultado é **um só arquivo IFC4** da escola inteira, com esta estrutura:

```
IfcProject "ETIB <escola> — modelo federado único"
└─ IfcSite "ETIB <escola>"   terreno: "Terreno — lote" (verde) e "Terreno — entorno" (transparente)
   ├─ IfcBuilding "Implantação — redes externas"   redes compatibilizadas, agrupadas por sistema
   ├─ IfcBuilding "<MÓD> — <nome>"                 um por módulo: estrutura as built + arquitetura completa
   └─ IfcBuilding "URB — Urbanização"              divisa, reservatórios, platôs, pisos externos, piso tátil
```

Cada elemento leva o pset `Dados_ETIB` (disciplina, sistema, modulo, origem). Instalações internas dos módulos não entram.

## Antes de começar: o que pedir e juntar

Monte a pasta da escola (a "raiz") assim. Os nomes são livres, porque a configuração aponta cada arquivo:

| O quê | De onde | Para quê |
|---|---|---|
| IFC das redes externas compatibilizadas (por disciplina) | entrega da escola | Implantação |
| IFC do terreno as built (o mesmo das redes) | entrega da escola | terreno e cota do pé do muro |
| IFC da estrutura as built dos módulos | entrega da escola / modelo do módulo | estrutura |
| RVT de arquitetura de cada módulo e o RVT da implantação | Drive da construtora, pasta "QG as built" (**somente leitura**) | arquitetura e urbanização |
| IFC padrão ETIB do módulo sem RVT | biblioteca de padrões | arquitetura de reserva |
| DWG da situação (SIT) e da pavimentação (PAV) em DXF | pranchas da escola | divisa, reservatórios, lote, gramado e pisos |

Exportar os RVT em IFC está em `referencia/EXPORTAR_RVT.md`. A configuração da escola está em `referencia/CONFIG.md`, e o exemplo real é `escolas/JDI.json`.

## Passo a passo

Ambiente: Python 3.11 com `pip install -r requirements.txt`. As versões são fixas: ifcopenshell 0.9 muda a API, então não suba a versão sem testar. Todos os comandos recebem o JSON da escola.

1. **Configuração.** Copie `escolas/JDI.json` para a raiz da escola e ajuste: sigla, georreferência (a MESMA origem dos IFC já entregues da escola), redes, estrutura, módulos e posições, divisa e terreno. Veja `referencia/CONFIG.md` para achar cada valor.
2. **Cota do RVT da implantação.** Rode `python scripts/p0_cota_rvt.py escola.json <IMP_RVT.ifc>`. Se a diferença for constante, use o dz sugerido em `urbanizacao_rvt.posicao`. Na Jandaíra o RVT estava 0,565 m abaixo do as built.
3. **Módulos.** Rode `python scripts/p1_modulos.py escola.json`, ou passe só alguns módulos no fim. Confira na saída a unidade de cada módulo e os ângulos convertidos.
4. **Divisa e reservatórios.** Rode `python scripts/p2_divisa.py escola.json`.
5. **Urbanização do RVT.** Rode `python scripts/p3_urbanizacao.py escola.json`. Confira na saída quanto saiu de divisa, quanto ficou fora do lote e os platôs recortados.
6. **Terreno e pisos.** Rode `python scripts/p4_terreno.py escola.json`.
7. **Montagem.** Rode `FED_CACHE=<arquivo_temp>.ifc python scripts/p5_montar.py escola.json R00`. A junção leva de 5 a 50 minutos. Com o cache, a próxima rodada pula a junção. **Apague o cache quando qualquer fonte mudar.**
8. **Conferência.** Rode `python scripts/p6_conferir.py escola.json saida/<SIGLA>_FEDERADO-UNICO_R00.ifc`. O resultado precisa ser **APROVADO**, e os itens "fora do razoável" se olham um a um.
9. **Prévias.** Rode `python scripts/p7_previas.py escola.json saida/<...>.ifc previas`. **Olhe as imagens**: módulo no lugar, nada fora do lote, piso duplo, terreno cobrindo prédio.
10. **Pacote.** Rode `python scripts/p8_pacote.py escola.json R00 previas`. Ele gera `envio/ETIB-<ESCOLA>-FEDERADO-UNICO_<data>_R00` com 03_IFC, 04_PREVIA, LEIA-ME e o .zip.
11. **Revit.** Abra no Revit antes de mandar: Fase 3 na vista 3D; VV → Local → desmarcar pontos de levantamento e base; ZF; estilo Sombreado.

Se um passo muda, refaça dele em diante. Para módulos, rode p1, depois p3 (o recorte dos platôs usa os pisos dos módulos), depois p4 e p5.

## Armadilhas já pegas (não repetir)

- **Unidade.** Todo IFC criado com ifcopenshell.api precisa de `unit.add_si_unit` explícito. Sem argumento ele cria MILÍMETRO, e a junção reescala tudo por 1/1000, então as paredes "somem". O `etib_fed.novo_ifc` já faz isso.
- **Ângulo em grau.** Os IFC padrão e os do Revit vêm em GRAU, e o MergeProjects só converte comprimento: arcos e giros deformam. `graus_para_rad` em todo arquivo-fonte (os passos 1 e 3 já chamam).
- **Georreferência.** Todo arquivo precisa da mesma IfcMapConversion. Arquivo diferente ou sem ela leva SetFalseOrigin na junção e fica deslocado.
- **Piso duplo.** No RVT da implantação os módulos são vínculos e os platôs passam por baixo deles. O passo 3 tira dos platôs a projeção dos pisos dos módulos.
- **Casas vizinhas.** O RVT da implantação pode ter paredes genéricas fora do lote. O passo 3 tira o que está fora do contorno da divisa.
- **Muro repetido.** Muro e gradil do RVT ficam a até 1 m da situação. Vale a situação (passo 2), e o do RVT perto da divisa sai.
- **Cota do RVT.** Na Jandaíra o RVT estava na cota de projeto e o as built 0,565 m acima. Sempre rode o p0.
- **Arquivo grande (200 MB).** Use `spatial.assign_container` e `remove_deep2` só em arquivo pequeno. No federado eles levam horas, e o p5 já cria as relações direto. Rode os passos longos em segundo plano. Na nuvem o contêiner é reciclado quando a sessão parece parada.
- **IFC soltos na pasta da construtora.** Confira o código da escola no nome do arquivo e as coordenadas: na pasta da Jandaíra havia IFC da Pojuca.
- **Propriedades de trabalho.** `fora_do_comercial`, `angulo_real` e `deflexao_junta_graus` nunca vão no entregue. O p5 tira e o p6 confere.
- **Drive da construtora.** É somente leitura: baixe, nunca grave lá.
- **Vínculo que não existe** (ex.: ETE descarregada no RVT): não entra e é citado em `leia_me.nao_entra`.
- **Memória.** As prévias usam cerca de 7 GB num federado de 200 MB. Não rode p6 e p7 ao mesmo tempo numa máquina de 16 GB. O p7 cria o cache da geometria e se reinicia sozinho antes de desenhar: com o IFC aberto no mesmo processo, a vista 3D estoura a memória.

## Entrega

Mande o .zip e o LEIA-ME e diga, em poucas linhas, o que entrou, o que foi adotado e o que não entra. O LEIA-ME sai da configuração (`leia_me`): escreva ali o que mudou, os valores adotados (alturas não cotadas, dz do RVT, posições adotadas) e o que ficou de fora.
