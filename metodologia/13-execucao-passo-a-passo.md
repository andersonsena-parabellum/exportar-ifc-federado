# 13. Execução passo a passo (para um agente)

Roteiro executável de uma escola nova, do zero à entrega. Cada passo diz **onde roda**, o **comando**, o que **conferir** e o **critério para seguir**. Marcadores:

- ☁️ roda na nuvem (Linux, Python do ambiente fixo);
- 💻 **precisa do notebook** (Windows com Revit, AutoCAD ou a pasta sincronizada do Drive);
- 🙋 **precisa do dono** (decisão ou ação que só ele faz).

Os exemplos usam `<escola>` = nome do adaptador (ex.: `catu`) e `<SIGLA>` = sigla da escola (ex.: `CAT`). Para cada passo há um script pronto de uma escola já entregue: copiar e trocar o que é da escola é o caminho mais rápido.

## 0. Preparar o ambiente ☁️

```
git clone <este repositório> ~/metodologia-etib
bash ~/metodologia-etib/ferramentas/ambiente/preparar_nuvem.sh
export ETIB_RAIZ=$HOME/etib-raiz ETIB_G=$HOME/etib-raiz/_G
mkdir -p $ETIB_RAIZ && ln -sfn ~/metodologia-etib/ferramentas/etib $ETIB_RAIZ/FERRAMENTAS
alias etib='bash $ETIB_RAIZ/FERRAMENTAS/_nuvem/etib-python'
```

- Antes: colocar o instalador `.deb` do ODA File Converter em `ferramentas/` e as fontes das pranchas (Arial, Swiss 721, romans, simplex, isocp) em `ferramentas/pranchas_pdf/fontes/`. Os dois têm licença e não vão no repositório.
- Conferir: o script imprime as versões de ifcopenshell, ezdxf e numpy e o caminho do ODA.
- Dados da escola: copiar do notebook a pasta `ETIB-<ESCOLA>` inteira para `$ETIB_RAIZ/ETIB-<ESCOLA>` (mesma árvore).

## 1. Entrada da escola (capítulo 02)

| Passo | Onde | Comando / ação | Conferir |
|---|---|---|---|
| 1.1 Pasta da escola | ☁️ | copiar `_MODELO-ESCOLA` para `ETIB-<ESCOLA>`; `PROJETO_ORIGINAL` = cópia fiel do Drive da construtora | nada editado em `PROJETO_ORIGINAL` |
| 1.2 DWG abrem? | ☁️ | `xvfb-run -a ODAFileConverter <pasta_dwg> <pasta_dxf> ACAD2018 DXF 0 1 "*.DWG"` (ou 💻 `etib entrada/entrada.py ETIB-<ESCOLA>` no notebook, com AUDIT) | lista dos que não abrem |
| 1.3 DWG que não abre | 🙋💻 | o dono salva de uma vez no AutoCAD com janela | todos abrem |
| 1.4 CTB e fontes | ☁️ | sair da lista do 1.2 | lista no INVENTARIO |
| 1.5 RVT | 💻 | `entrada/revit_conv.py <ESCOLA>` (capítulo 11) | malhas do IMP e da estrutura gravadas |
| 1.6 Pedido único | 🙋 | o que falta da construtora, numa mensagem | registrado no INVENTARIO |
| 1.7 Decisões antigas | 🙋 | página de entrada respondida | respostas no INVENTARIO |

**Seguir quando:** quadro "Entrada" do `INVENTARIO.md` fechado ou com o que falta registrado no pedido.

## 2. Georreferenciamento e extração (capítulo 03) ☁️

| Passo | Comando / ação | Conferir |
|---|---|---|
| 2.1 Diagnóstico | ler INSUNITS, EXTMIN/EXTMAX e layers de cada DXF (ezdxf) | UTM ou local |
| 2.2 Transformação | ICP dos blocos de arquitetura contra a implantação; libs em `georef_dxf/` (ex.: `georef_dxf/satiro/`) | resíduo de milímetros; JSON gravado em `CAD_GEORREFERENCIADO/` |
| 2.3 Extração em planta | script da escola lendo layers e textos, montando o grafo (ex.: `georef_dxf/satiro/`, `catu/`, `georef/rede_lib.py`) | CSV de trechos, caixas e nós; códigos do projeto em cada peça |
| 2.4 Terreno | `preclash/escolas/<escola>_terreno.py` (copiar `catu_terreno.py`) | `.npz` gravado; ajuste às cotas da base com relatório antes/depois |

**Seguir quando:** sobreposição da rede extraída com o PDF conferida em imagem, sem deslocamento.

## 3. Modelagem e compatibilização (capítulos 04 e 05) ☁️

```
cd $ETIB_RAIZ/FERRAMENTAS/preclash
cp escolas/catu.py escolas/<escola>.py      # trocar BASE, SIGLA, ORIGEM, EPSG, CAIXA_OBRA, CSV, REGRAS
etib rodar.py <escola>
```

- Conferir no LEIA-ME da rodada: conflitos antes/depois, soluções, pendentes e o CSV de verificação (ponta solta, degrau, pedaço curto, rede fora do lugar).
- Conferir no visualizador HTML com o botão de validação (sem terreno: colisões e conexões; com terreno: tampas).
- Ligar `DESVIOS = ['A']` para o cenário de desvios (caixa deslocada, contorno) quando a profundidade não resolve.
- Aplicar e avisar dentro dos limites; o resto vira ficha de decisão.

**Seguir quando:** 0 colisão crítica fora das pendências declaradas e verificação sem item inesperado.

## 4. Página de pendências (capítulo 05) ☁️ 🙋

```
cd $ETIB_RAIZ/FERRAMENTAS/pendencias
etib pagina.py <config.json>       # modelo de config e fichas no LEIA-ME e em itamira/pendencias/, catu/pendencias/
```

- Conferir `CONFERENCIA_F.md` APROVADA antes de publicar.
- Publicar o `index.html` como página com banco de dados (respostas na coleção `decisoes`).
- Sub-issue no Linear atribuída ao dono, com imagem marcada.
- O dono responde; as decisões entram no adaptador e o passo 3 roda de novo.

## 5. IFC de entrega (capítulo 04) ☁️

- IFC por disciplina + terreno + estrutura + federado, perfil `'revit'`, Pset `Dados_ETIB`, georreferenciado. Exemplos: `catu/ifc/`, `itamira/ifc/ita_entrega.py`.
- Conferir rodando a revisão só do IFC: `cd ../revisao && etib revisar.py <escola> --sem-pdf --sem-envio`.

## 6. Pranchas (capítulo 07) ☁️

| Passo | Comando | Conferir |
|---|---|---|
| 6.1 Plano da revisão | `etib preclash/executivo/rever.py <escola> [cen]` | registro do que não foi achado na prancha (conferir à mão) |
| 6.2 Aplicar | `etib preclash/executivo/revisao_ezdxf.py ...` (ou 💻 `revisao.lsp` no accoreconsole) | entidade trocada na mesma layer, cor e tipo de linha |
| 6.3 Carimbo QG | `etib preclash/executivo/carimbo_ezdxf.py ...` | 3 logos ao lado do DWG |
| 6.4 Carimbo AS BUILT | `etib preclash/executivo/carimbo_asbuilt.py ... --escola "L1|L2" --endereco "..."` | AB, disciplina CONDER, R00, responsável vazio |
| 6.5 PDF | `cd ferramentas/pranchas_pdf && CTB=prancha/acad.ctb LAY=<folha> etib render_pdf_nuvem.py <prancha.dxf> <saida.pdf>` | A0, um PDF por folha |
| 6.6 Prévia | `etib preclash/executivo/rever.py --miniaturas <pasta> --origem <pdfs de origem>` | miniaturas antes e depois vão ao dono 🙋 |

Exemplos completos por escola: `catu/exe/cat_exec.py`, `satiro/exe/sat_exec.py`, `itamira/exe/`.

## 7. Revisão de qualidade (capítulo 08) ☁️

```
cd $ETIB_RAIZ/FERRAMENTAS/revisao
# atualizar a entrada da escola em entregas.py
etib revisar.py <escola> --recortes
```

- Olhar os recortes dos itens visuais; confirmar à mão cada grupo de pendência.
- Corrigir em lote e repetir até **APROVADO**. Exemplo: `catu/exe/cat_revisar_envio.py`.

## 8. Envio e CDE (capítulo 09)

| Passo | Onde | Comando | Conferir |
|---|---|---|---|
| 8.1 Montar a pasta de envio | ☁️ | ex.: `catu/exe/cat_envio.py` | conteúdo do item A |
| 8.2 Limpar o IFC | ☁️ | `etib revisao/limpar_entrega.py <envio>/03_IFC <csv interno>` | sem propriedades de trabalho |
| 8.3 Revisão do envio | ☁️ | `etib revisao/revisar.py <escola>` | APROVADO, hash igual |
| 8.4 Subir ao Drive | 💻 | `<script de envio> --drive` no notebook (cópia para a pasta de envios e do CDE) | arquivos no Drive |
| 8.5 CDE | ☁️ | `pranchas_cde/pranchas_json.py` + publicar só o `pranchas.json`; índice | item A3 conferido depois da subida |
| 8.6 Linear | ☁️ | comentário na issue da escola + Done | |

## 9. Federado único (capítulo 06) ☁️ 💻

Seguir a skill [`federado-unico-etib`](../federado-unico-etib/SKILL.md): exportar os RVT no notebook (💻), depois `p0` a `p8` na nuvem.

## O que o agente nunca faz sozinho

- Editar, mover ou apagar qualquer coisa nas pastas da construtora ou em `PROJETO_ORIGINAL`.
- Passar dos limites do aplicar e avisar sem decisão do dono.
- Fechar modelo do Revit sem salvar, ou rodar mais de um accoreconsole ou mais de um trabalho no Revit ao mesmo tempo.
- Compartilhar a pasta de envio com a construtora (é o dono que manda o link).
- Mexer à mão no `pranchas.json`.
