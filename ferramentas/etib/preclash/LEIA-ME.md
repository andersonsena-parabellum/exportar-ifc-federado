# preclash — pré-compatibilização 3D sem Revit

Monta as redes externas em 3D já georreferenciadas (UTM SIRGAS 2000, cota absoluta, diâmetro externo real), roda o clash entre disciplinas, testa soluções **só de profundidade** e exporta IFC + visualizador 3D em HTML. Serve para decidir a compatibilização **antes** de modelar no Revit; os RVTs por disciplina e o federado vêm depois que as soluções forem aprovadas.

## Rodar

```
cd "D:\Projeto Modelagem\FERRAMENTAS\preclash"
..\.venv\Scripts\python.exe -X utf8 rodar.py satiro
```

Saída em `ETIB-<ESCOLA>\RELATORIOS\PRECLASH_<data>\` (pasta definida no adaptador): `<SIGLA>_preclash_LEIA-ME.md` (resumo), `_visualizador.html`, `_projeto.ifc`, `_solucao_<cenário>.ifc`, e por cenário `_conflitos_antes.csv`, `_conflitos_depois.csv`, `_solucoes.csv` (com a nota para a planta) e `_pendentes.csv`.

O HTML abre direto no navegador (o three.js vem de unpkg.com, precisa de internet). Para servir local: configuração `preclash-visualizador` em `.claude\launch.json` (porta 8765, raiz `D:\Projeto Modelagem`).

## Como funciona

| Etapa | Arquivo | O que faz |
|---|---|---|
| Leitura | `preclash/leitura.py` | Lê os CSVs padrão das fases 2/3 (trechos, caixas, galeria, nós). Gravidade: GI pela CF do projeto; sem CF, declividade do rótulo; sem nada, propaga pelo nó; sem nada mesmo, terreno − 0,60 m (marcado "cota estimada"). Pressurizadas: eixo da fase 3 ou `perfil_por_recobrimento()` (algoritmo da skill). |
| Terreno | `preclash/terreno.py` | TIN (`.npz` com `pts`, opcional `tri`, platôs e linhas da SIT). Sem `tri`, faz Delaunay dos pontos. |
| Clash | `preclash/clash.py` | Tubo = cápsula (eixo + raio externo), caixa = prisma. CRÍTICA < −2 mm; ATENÇÃO < folga (0,20 m). Mesma rede não se testa. Duas redes por gravidade que se encontram na ponta de um trecho = ligação, não conflito. |
| Soluções | `preclash/solver.py` | Para cada conflito, a rede móvel (ordem `REGRAS['ordem_mover']`) faz um mergulho local: janela = trecho em planta perto do obstáculo + 0,15 m, cota que dá a folga, conexões verticais nas pontas. Planta não muda. Repete clash → solução até não sobrar nada resolvível. O que não cabe nos limites vai para pendentes, separado por categoria. |
| Desvios em planta | `preclash/desvio.py` | Passo 2, só para o que a profundidade não resolve: **contorno** (desloca o trecho que atravessa PV/CI/CA de ±0,4 a ±3,0 m, transições a 45°, pontas do trecho fixas, cota refeita pelo recobrimento; penaliza cruzar linhas da SIT) e **caixa deslocada** (caixa de ELE/SDAI anda perpendicular ao tubo; os eletrodutos que chegam nela acompanham). Depois refaz a profundidade. Liga-se com `DESVIOS = ['A']` no adaptador; vira o cenário `AD`. |
| Exportação | `preclash/export_ifc.py`, `preclash/visualizador.html`, `rodar.py` | IFC4 com `IfcMapConversion` + `IfcProjectedCRS` (EPSG), um `IfcSystem` por disciplina, Pset `PRECLASH`; HTML com situações (projeto × solução por cenário), lista de conflitos/soluções/pendentes, clique para ver os dados. |

Categorias de pendentes (o que precisa de decisão humana):
- **exige desvio em planta (atravessa PV/CI/CA)**: rede pressurizada passa por dentro de PV/CI/CA (na Sátiro, corredor de 2 a 3 m entre as edificações e a BA-233 dividido por todas as redes); desvio em planta (executivo novo) ou mergulho fundo.
- **caixa de ELE/PCI no caminho**: caixa de passagem encosta em outra rede; deslocar a caixa alguns centímetros (ajuste pequeno da ELE/SDAI).
- **gravidade × gravidade**: esgoto, pluvial e drenagem entre si; só se resolve no projeto hidrossanitário.
- **Δz acima do limite**: daria para resolver com profundidade, mas passando do `dz_max` ou da profundidade máxima; aceitar ou desviar.

## Replicar para outra escola

1. **Terreno** → `escolas/dados/<escola>_terreno.npz`. Copiar `escolas/satiro_terreno.py`, que só importa a classe de terreno que a thread da escola já usou na fase 3 e grava `pts`, `tri`, platôs e as linhas da SIT. Se a escola só tiver pontos (TOP, curvas), basta gravar `pts` (n×3). Quando vier o terreno do IMP as built, regravar o `.npz` e rodar de novo.
2. **Adaptador** → `escolas/<escola>.py`, copiando `escolas/satiro.py`: trocar `BASE`, `SIGLA`, `ORIGEM` e `EPSG` (as do `AGENTS.md`), `CAIXA_OBRA` (retângulo UTM da obra) e, em `carregar()`, os nomes dos CSVs. Quando as colunas forem diferentes do padrão, ler o CSV no próprio adaptador e criar os elementos com `modelo.elemento(...)` / `leitura.elemento_3d(...)`. Rede pressurizada sem cota: `leitura.perfil_por_recobrimento(pontos_2D, DE, recobrimento, terreno)`.
3. **Cenários** podem trazer `elementos`, `caixas` e `terreno` próprios no dict do cenário (ex.: hipótese de CT diferente); `CENARIO_PROJETO` escolhe o cenário do IFC de projeto (padrão: o primeiro). O visualizador ainda desenha as caixas com a cota do cenário-base. **Regras** (`REGRAS` no adaptador): folga, ordem de quem se move, `dz_max`, profundidade máxima. **Cenários**: um por dúvida em aberto que muda o clash (ex.: galeria "rede futura" com e sem).
4. Rodar `rodar.py <escola>` e conferir no HTML.

Situação das escolas em 18/10/2026 (o que cada adaptador vai ler):

| Escola | Gravidade com cota | Pressurizadas com cota | Terreno | Trabalho do adaptador |
|---|---|---|---|---|
| Sátiro Dias | ESG, pluvial, CPS-DRE, galeria (fase 2) | AF, HID, SDAI, ELE (fase 3) | provisório da fase 3 (`satiro_terreno.npz`) | **pronto** (`escolas/satiro.py`) |
| Aporá Prof. Áurea | `RELATORIOS\GEORREF_E_REDES_2026-10-18\revit\dre_tubos.csv` + `dre_caixas.csv` (eixo 3D) | `revit\ele_eletrodutos.csv`, `pci_tubos.csv` (eixo 3D: `x0_utm;y0_utm;z0_eixo;…`) | `FERRAMENTAS\georef\work\APORA\rede\terreno_pts.npz` | o mais simples: CSVs já em 3D, só mapear colunas |
| Aporá Itamira | `APR-ITA_fase3_cotas_DRE_trechos.csv` (`ci_montante`) + coordenadas da fase 2 | `APR-ITA_fase3_cotas_ELE.csv` (eixo por trecho) | IFC as built (já lido pela thread) | juntar fase 2 (planta) com fase 3 (cota) pelo nome do trecho |
| Pojuca | `PJC_fase3_DRE/CPS_DRE/ESG_trechos.csv` (GI) | não calculadas: ELE (`vertices_UTM`), PCI e AF só 2D | provisório dos platôs (+60/+61/+61,90) a gravar | `perfil_por_recobrimento` para ELE/PCI/AF; esperar as decisões do campo e da PI000 |
| Catu | `DRE/ESG_fase2_trechos` (mesmo formato da Sátiro) | não calculadas: ELE (`EL1/EL2_eletrodutos`), INC hidrantes/SDAI, AF só 2D | a montar (TOP/TER) | `perfil_por_recobrimento` para as pressurizadas |
| Alagoinhas BA2 | só planta (fase 2) | só planta | — | esperar a decisão do pluvial e as premissas de cota |

Regras do projeto que a ferramenta segue: planta não muda (traçado novo = executivo novo); mexer primeiro em ELE e PCI, depois AF; ESG, pluvial e drenagem fixas; conexões verticais sempre modeladas; cota da AF é premissa (não vira item de relatório). Arquivos das threads das escolas e `PROJETO_ORIGINAL` só são lidos.

## Visualizador de IFC (That Open Engine)

`thatopen\` gera um visualizador que lê os IFC por disciplina (não os dados do preclash): `node converter.mjs <pasta_IFC_POR_DISCIPLINA> frags` converte IFC → `.frag` (web-ifc, só aqui no computador) e `node montar.mjs frags <saida.html> [--artifact]` monta um HTML único (script empacotado + worker em blob + modelos em base64), que roda no claude.ai e no tablet sem WebAssembly. Serve para abrir o federado de entrega; para decidir a compatibilização, o visualizador do preclash (conflitos, soluções, desvios) continua sendo o principal.

## Visualizador único (todas as escolas)

Artifact **Pré-compatibilização ETIB**: <link privado da página>. A página não tem dados embutidos; cada escola é um arquivo `dados/<SIGLA>.json` publicado junto, e o seletor no topo troca a escola (`#SIGLA` no link abre direto).

- **Siglas fixas** (o `SIGLA` do adaptador tem que ser uma destas): `SAT` Sátiro Dias, `CAT` Catu, `PJC` Pojuca, `ITA` Aporá Itamira, `AUR` Aporá Prof. Áurea, `JAN` Jandaíra, `ALH` Alagoinhas (BA2).
- `rodar.py` grava `<SIGLA>.json` na pasta de saída da escola, ao lado do HTML local. **Quem publica no artifact é a thread "Pré-compatibilização sem Revit"**: as threads das escolas avisam o coordenador com o caminho do `.json` e não publicam nem editam a ferramenta.
- Para publicar: `PRECLASH_ARTEFATO=<pasta>` gera `preclash_portal.html` (a página); publicar essa página no link acima com `files={"dados/<SIGLA>.json": ...}` (os outros arquivos ficam).
- Mudou só a interface: `reempacotar.py <HTML local> <pasta>` remonta o HTML local e a página única sem rodar o clash.

## Caixas retangulares giradas e estrutura (19/10/2026)

- `modelo.caixa_retangular(id, disc, rede, E, N, lx, ly, rot, zb, zt, **info)`: prisma lx × ly (m, com parede) girado `rot` (rad, anti-horário a partir do E) — pilar 30×70, quadro, evaporadora/condensadora, abrigo, reservatório. Entra no clash, nas soluções, nos desvios, no IFC (perfil retangular girado) e no visualizador. Equivale a `caixa(..., forma='r', mx=lx/2, my=ly/2, rot=...)`.
- Estrutura como obstáculo: disciplina `EST` (ou outra listada em `REGRAS['estrutura']`) ou elemento com `tipo='estrutura'`. Conflito com ela vira o pendente **"estrutura (pilar, viga, fundação)"**, com a sugestão de passagem/furo pelo projetista estrutural ou desvio da rede.
- Para a estrutura e os equipamentos aparecerem no IFC de entrega, incluir a disciplina deles em `DISCIPLINAS_ENTREGA` (ex.: `'EST': ('EST',)`), ou deixar só no federado.

## Caixa × caixa e ligações (19/10/2026)

- O clash testa também **caixa × caixa** de disciplinas diferentes (caixa de passagem, poste ou equipamento em cima de PV/CA, sapata etc.). Caixa móvel (ELE/SDAI) vira o pendente "caixa de ELE/PCI no caminho" e os desvios tentam deslocá-la; com estrutura, vira "estrutura"; entre fixas, "gravidade × gravidade".
- **Ligação** (trecho por gravidade que termina numa caixa de outra rede) agora só vale entre a mesma disciplina ou entre grupos de `REGRAS['ligacao_entre']` (padrão `[{'AP', 'DRE'}]`). Ex.: dreno de condensado da climatização no pluvial → `'ligacao_entre': [{'AP', 'DRE'}, {'AP', 'CLI'}]`. Trecho de esgoto/pluvial terminando em poste ou caixa de ELE deixa de ser "ligação" e vira conflito.

## Classe IFC das peças (19/10/2026)

`export_ifc.classe_caixa`: caixa com `info['classe_ifc']` (ex.: `IfcElectricDistributionBoard`, `IfcUnitaryEquipment`, `IfcLightFixture`, `IfcTank`, `IfcFireSuppressionTerminal`; `info['pred']` opcional) sai nessa classe; disciplina `EST` sai como `IfcColumn` (tipo com "pilar"), `IfcBeam` ("viga"/"quadro") ou `IfcFooting`; o resto, `IfcDistributionChamberElement`. Formas especiais de equipamento (poste com braço, reservatório taça) continuam no adaptador da escola (ex.: `georef_dxf\satiro\entrega_sat.py`).

## Passo 7 — revisão dos DWG (`executivo\rever.py`)

`rodar.py` grava `<SIGLA>_preclash_<cen>_mudancas.json` (mergulhos, contornos, caixas deslocadas, em UTM). `..\.venv\Scripts\python.exe -X utf8 executivo
ever.py <escola> [cen] [--so-comandos]` desenha numa **cópia** de cada DWG de projeto os layers `<REV>-NOVO`, `-SUBSTITUIDO` (tracejado), `-NUVEM` e `-NOTA` (quadro da revisão), com `executivo
evisao.lsp` (do método da Jandaíra) no accoreconsole, um por vez. Saída: `RELATORIOS\EXECUTIVO_<REV>_<SIGLA>_<cen>\`. No adaptador: `EXECUTIVO = {disc: 'PROJETO_ORIGINAL/...dwg'}` ou `executivo_dwg(m)`; `TRANSF_DWG = {dwg: (rot_deg, (tx, ty))}` se a transformação não estiver em `CAD_GEORREFERENCIADO	ransformacoes_local_para_UTM.json`; `REVISAO` (padrão R01) e `EXECUTIVO_TEXTO` (altura, padrão 0,30).

### Armadilhas do passo 7 (Pojuca, 19/10/2026)

- DWG que não reabre depois de gravado (ErrorStatus 53, ex.: IC-001): o `rever.py` roda `AUDIT` antes e depois da revisão.
- MTEXT: sem fundo (grupos 90/63/45) e com no máximo 250 caracteres no grupo 1; o resto vai em blocos de 250 no grupo 3 (`revisao.lsp` já faz). Senão o `entmake` falha sem avisar.
- PDF: as folhas vêm com "DWG to PDF.pc5" em ANSI A; o `-PLOT` padrão sai em Carta. Usar o `-PLOT` detalhado com "ISO full bleed A0 (841.00 x 1189.00 MM)", Extents e Fit.

## Pranchas no padrão de executivo final / as built (19/10/2026, pedido do Anderson)

As pranchas vão para o campo (construtor, mestre de obras): **nada de nuvem, rascunho, traçado "substituído" ou menção a revisão interna e pré-compatibilização**. O `executivo\rever.py` (padrão) faz, numa cópia de cada DWG:
- **mudança de traçado:** o trecho antigo sai e o novo entra **na mesma entidade** (polilinha: troca dos vértices; linha: redesenhada com layer, tipo e escala de linha, cor e espessura dela); as tags de diâmetro e de fluxo junto do trecho acompanham o deslocamento;
- **caixa deslocada:** o bloco (ou contorno) e o texto da caixa andam; as pontas das linhas que chegam nela acompanham;
- **só profundidade (mergulho):** nota curta no estilo (layer, fonte, altura, cor) do texto mais próximo da prancha: "ELETRODUTO A 1,40 m DE PROFUNDIDADE" / "TUBULAÇÃO A …";
- saída `RELATORIOS\EXECUTIVO_<SIGLA>_<cen>\<nome>_REVISADO.dwg` + `_cmd_<nome>.txt` + registro (`<SIGLA>_executivo_<cen>.json`, com o que não foi achado na prancha para conferir à mão).
Como funciona: cópia → DXF da cópia (handles) → `executivo\asbuilt.py` acha a entidade de cada trecho (vértices a até `EXECUTIVO_TOL` = 0,06 m do traçado antigo) e planeja → `revisao.lsp` (DEL, PLC, REPL, MV, VTX, TXC, e RT/CPR/ST: girar, copiar+girar e trocar o texto de uma entidade) aplica. Carimbo/quadro de revisões e código da folha continuam com a escola. O modo antigo (layers R01-NOVO/SUBSTITUIDO/NUVEM/NOTA) só com `--rascunho`.
- **Uma nota de profundidade por trecho** (Jandaíra, 20/10/2026). O Anderson reclamou de "PROF. 0,90 m" repetido umas 20 vezes num eletroduto: o modelo quebra curvas em pedaços de 1,4 m (ELE-F-23.1 … .19) e cada eletroduto do banco é um elemento.
  - `asbuilt.agrupar_notas` (usado pelo `rever.py`; o `agrupar_mergulhos` antigo fica para quem já chamava) junta as mudanças de profundidade da mesma disciplina e com o mesmo texto quando:
    - se tocam;
    - correm a menos de 1 m;
    - têm o mesmo nome de trecho sem o sufixo `.N`;
    - ou são da mesma `EXECUTIVO_FAMILIA`.
  - Os pedaços viram uma polilinha com a nota no meio. Outra nota no mesmo grupo só sai a mais de `EXECUTIVO_NOTA_RAIO` (15 m) e em trecho de pelo menos 3 m.
  - `Plano.nota` põe a nota logo abaixo ou acima da etiqueta de diâmetro/material do próprio trecho, no estilo dela, quando a etiqueta está mais perto dessa linha do que de qualquer outra.
  - `entidades(dxf, arcos=True)` lê ARC só para a folga da nota e para achar a etiqueta (o `Plano.linhas` continua sem arco). A folga da tinta é 0,5 h, o primeiro afastamento 0,8 h, e a rotação de TEXT é sempre lida em graus.
  - Resultado na Jandaíra: AF-001 foi de 57 para 20 notas, EL-001 de 56 para 18, EL-002 de 76 para 25, IN-001 de 31 para 8. Na cópia da Pojuca (estudo de cota), 161 mudanças viraram 87 notas.
  - Cuidado: o `executivo_campo_pojuca.py` tem o seu próprio `nota()` e não passa por aqui. Contar as notas no PDF antes de entregar.
- **Nota de elétrica e alarme** (Jandaíra, 20/10/2026): o `agrupar_notas` leva a 'disc', e o `Plano.nota` não usa etiqueta de tubo de água (PVC, PEAD, mm, 2.1/2") para posicionar nota de ELE/SDAI/CFTV. Texto de bloco tem caixa conservadora (bloco espelhado inverte o ponto de inserção; altura até 2× o grupo 40), e o lugar livre é procurado num anel de até 4 m.
- **Tipo de linha e textos de bloco** (Jandaíra, 20/10/2026, itens da Revisão de qualidade):
  - Rede tracejada saía contínua: o `entmake` sem o grupo 6 pegava o CELTYPE do desenho. O `revisao.lsp` agora grava ByLayer, cor 256 e espessura −1 quando a entidade original não declara (`r01:props_bl`), e ganhou o comando `LT h tipo`.
  - `asbuilt.entidades(..., blocos=True)` vê os textos dentro de blocos (arquitetura), e o MTEXT de várias linhas conta a altura inteira: a nota não cai mais por cima de "Banco H=0.50m".
  - `georef_dxf\dxfgeo.py` passa o ponto de inserção (anexo) dos textos de bloco.
- Ajustes da Jandaíra (19/10/2026): caixa deslocada não mexe em poste, luminária nem quadro, e o texto só anda se o símbolo for achado; ponta de linha que só estica/encurta é movida (antes ia para "não achado"). O TXC só copia o grupo 41 (fator de largura) quando o molde é TEXT: com molde MTEXT o 41 é a largura da caixa e esticava a nota. Opções do adaptador, desligadas por padrão: `EXECUTIVO_EXT` (m, prolonga as pontas do traçado do modelo ao procurar a linha, quando a caixa do modelo fica fora do vértice da prancha) e `EXECUTIVO_CAIXA_SEM_SIMBOLO = True` (prancha que marca a caixa só com texto no vértice: move o vértice e o texto).

## Profundidade máxima (parâmetro do projeto)

Do terreno ao topo do tubo/eletroduto, todas as disciplinas. O valor fica em `preclash/parametros.py`:
- 19/10/2026: "até 1,5 m". A **Jandaíra** foi entregue assim e continua com **1,50 m**.
- 20/10/2026 (Anderson): "para os outros projetos vamos aumentar a profundidade para até 2 m". Pojuca, Catu, Sátiro, Prof. Áurea, Itamira e Alagoinhas ficam com **2,00 m**.

O `rodar.py` grava esse valor em `REGRAS['prof_max_geral']` (teto dos mergulhos) e em `REGRAS['estudo']['prof_max']` (estudo de cota) quando o adaptador não fixa outro. O `prof_max_topo` de cada disciplina no adaptador continua valendo abaixo do teto, e vale o menor dos dois. Ao rodar de novo uma escola cujo adaptador ainda tenha 1,50 (Pojuca), suba para 2,00. Antes de mudar traçado em planta, o solver tenta um mergulho com Δz maior que o `dz_max` (até `REGRAS['dz_max_profundo']`, padrão igual ao teto); `REGRAS['profundo'] = False` desliga essa tentativa.

## Abrir o IFC no Revit
IFC aberto no Revit 2025 com a vista 3D vazia (Catu, 19/10/2026): o "Abrir IFC" cria um projeto novo que **vincula** o `<arquivo>.ifc.RVT` gerado ao lado; com o template brasileiro (fases Existente/Demonstração/Fase 1/2/3) o importador põe todos os elementos na **última fase (Fase 3)** e a vista {3D} do projeto novo mostra a **Fase 1**, então nada aparece, nem com ZF. Não é coordenada (a geometria fica certa, perto da origem) nem tipo de elemento. Solução: na vista 3D, Propriedades → Fase = **Fase 3** (a última). Depois, VV → Local: desligar "Ponto de levantamento topográfico" (e o ponto base) e dar ZF; o IFC é georreferenciado, então o ponto de levantamento fica na origem UTM, a ~8.600 km, e o ZF encolhe a escola a um ponto sob o ⊗. O IFC não controla isso. O importador do Revit também não lê `IfcSphere` ("Unhandled subtype of IfcCsgSelect"): as esferas de conflito agora saem em malha (IfcTriangulatedFaceSet).

## Parâmetros de compatibilização (19/10/2026, Anderson e Daniel)
Valem para as entregas a partir da Jandaíra (piloto) e da Pojuca. Tudo liga por `REGRAS` no adaptador; sem as chaves, a escola roda como antes.
- **Terreno pelas cotas de base:** se o terreno do modelo (IMP/IFC) diverge das cotas de base (CT das caixas de DRE/ESG das pranchas, implantação, TOP, TER), vale a base. `preclash/terreno.py: ajustar(npz_entrada, pontos_base (n,3), npz_saida, modo='local'|'constante', raio=12)` corrige o terreno pelos resíduos (núcleo gaussiano que some longe dos pontos; os pontos entram no TIN; platôs andam pela mediana) e devolve o relatório antes/depois.
- **Estudo de cota das pressurizadas** (`preclash/estudo.py`, `REGRAS['estudo']`): antes do clash de soluções, cada rede ganha uma cota de implantação, a de menos colisões. AF e HID têm um recobrimento por rede (`'por_rede'`). ELE, SDAI e CFTV têm um por trecho entre caixas (`'por_trecho'`): a troca de cota fica dentro da caixa. O perfil segue o terreno, com o topo até `'prof_max'` (parâmetro do projeto: JAN 1,50 m, demais 2,00 m). A elétrica passa sempre **por cima** da água (`'acima'`): a água, estudada primeiro, já deixa o lugar da elétrica no recobrimento mínimo dela. Com `REGRAS['mergulho_local'] = False` não há mergulho pontual (o degrau em "Z" serve para instalação predial, não para implantação); o que sobra vai para pendentes, na categoria "estudo de cota: sem cota livre". O passo 7 recebe a nota "PROF." por trecho (mudancas.json, origem 'estudo').
- **Gravidade × gravidade:** `REGRAS['caixas_moveis_grav'] = ['DRE', 'ESG']` e `'desloc_max_grav'` (0,60 m) deslocam a caixa de uma das redes no cenário de desvios (`DESVIOS`), mantendo a CF; os tubos acompanham. Com `REGRAS['contornos'] = False` o cenário de desvios só desloca caixas, sem contornar as pressurizadas em planta.
- **Conexões** (`preclash/conexoes.py`, ligado por padrão; `REGRAS['conexoes'] = False` desliga): peça comercial (11,25°, 22,5°, 45°, 90°) em toda mudança de direção acima de 5°, horizontal ou vertical, inclusive DRE/ESG. Nó com 3 ou mais trechos fora de caixa é junção. Dentro de caixa não há peça. No IFC saem como IfcPipeFitting / IfcCableCarrierFitting (BEND, JUNCTION/TEE); no visualizador, como esferas na cor da disciplina, rosa quando o ângulo real foge do comercial.
- **Reservatório inferior:** caixa com `info['classe_ifc'] = 'IfcTank'` no adaptador.
- **Ajustes vindos da Jandaíra (20/10/2026), já na ferramenta:**
  - `'desvio_perfil'` 0,05 m no perfil do estudo (padrão).
  - `'caixa_acompanha'` (padrão sim): o fundo da caixa de passagem/registro desce até 10 cm abaixo do tubo mais fundo, e o custo da elétrica conta o que essa caixa passa a pegar.
  - `'preencher_rebaixo'` (m, desligado por padrão; a Jandaíra usa 5): preenche rebaixo estreito de piso só para o perfil.
  - `mover_caixas` só para colisão de fato (`'mover_so_colisao'`), não mexe em equipamento (poste, quadro, abrigo) e põe a tampa da caixa de passagem que andou no terreno do lugar novo.
  - O adaptador antigo da Jandaíra (que fazia isso por conta própria, `estudo._jan`) continua dando o mesmo resultado.
  - Pojuca, só estudo: 104 → 110 críticos com esses padrões. A diferença é a caixa que desce e o perfil mais colado, ou seja, conflito real que antes não aparecia.
- **Validação** (botão no visualizador): o 1º toque esconde terreno e arquitetura (SIT, curvas, malhas ARQ) para conferir colisões e conexões; o 2º põe o terreno sólido de volta para conferir as tampas; o 3º volta ao que estava.
- **Leitor de IFC** (`preclash/leitura_ifc.py: ler(arquivos, ...)` e `terreno_npz(...)`): IFC do Revit ou da própria ferramenta → elementos e caixas. Tubos pelo IfcSweptDiskSolid, pela extrusão circular ou pela malha (PCA); caixas pelo menor retângulo da planta. A disciplina vem do Pset PRECLASH ou do nome do sistema (`DISC_PADRAO`). É para as próximas escolas; a Jandaíra lê os RVT extraídos (`compat_geral\jan_dados.py`).

## Classes do IFC e categorias do Revit (20/10/2026, Anderson: "um dos princípios do BIM é a informação")
O Revit 2025 escolhe a categoria só pela classe IFC; PredefinedType e tipo não contam. Testado com 40 classes em 20/10/2026: IfcCableCarrierSegment (eletroduto pela norma) virava "Bandeja de cabos", a conexão dele "Conexões da bandeja" e as caixas (IfcDistributionChamberElement) "Modelo genérico".
- `REGRAS['perfil_ifc']` é `'revit'` por padrão; `'norma'` mantém o IFC4 puro. No perfil `'revit'`:
  - tubos AF/ESG/DRE/HID: IfcPipeSegment (Tubulação);
  - conexões de tubo: IfcPipeFitting (Conexões de tubo);
  - eletrodutos ELE/SDAI/CFTV e as curvas deles: IfcCableSegment USERDEFINED "ELETRODUTO" / "CURVA DE ELETRODUTO" (Conduítes). Nenhuma classe vira "Conexões de conduíte";
  - caixa de passagem elétrica: IfcJunctionBox (Dispositivos elétricos);
  - PV/CI/CA de esgoto e drenagem: IfcWasteTerminal USERDEFINED "POÇO DE VISITA" / "CAIXA DE INSPEÇÃO", ou GULLYSUMP para caixa de areia/boca de lobo/ralo; caixa de gordura: IfcInterceptor (Equipamento hidráulico);
  - caixa de registro de AF/HID: IfcValve USERDEFINED "CAIXA DE REGISTRO" (Acessórios do tubo); hidrômetro: IfcFlowMeter;
  - abrigo de hidrante: IfcFireSuppressionTerminal (Sprinklers, a categoria de PCI do Revit);
  - reservatório: IfcTank; bomba: IfcPump; quadro: IfcElectricDistributionBoard; luminária: IfcLightFixture.
- A classe da norma vai sempre no Pset PRECLASH (`classe_ifc_norma`), com identificação, disciplina, rede, DE e material.
- Os sistemas saem como IfcDistributionSystem com PredefinedType: DOMESTICCOLDWATER, SEWAGE, STORMWATER, FIREPROTECTION, ELECTRICAL, SECURITY.
- Quem prefere a norma pura pode usar `'norma'` e ajustar a tabela de importação do Revit à mão (Abrir IFC > Opções > mapeamento de classes); pela API ela é só leitura.
- Tabela completa do teste no cabeçalho de `preclash/export_ifc.py`.
- **Decisão do Anderson (20/10/2026): fica o perfil `'revit'`** como padrão.
- **Caixas com geometria de caixa** (pedido dele no mesmo dia): PV, CI, CA e caixa de passagem saem por extrusão (leve) com:
  - fundo de 0,10 m;
  - paredes ocas: 0,10 m na retangular de alvenaria/concreto, anel de 0,08 m no PV circular;
  - tampa de 0,05 m (concreto; grelha de FoFo nas caixas de areia/boca de lobo).
  - O Pset leva a dimensão interna, a parede e a profundidade útil.
  - Equipamento, estrutura e caixa rasa (< 0,30 m) continuam como prisma.
  - Ainda sem furo de passagem dos tubos (o tubo entra pela parede).

## Verificação de continuidade (20/10/2026)
Correções da Revisão de qualidade da Jandaíra R03 (20/10/2026), todas na ferramenta e sem mudar cota de rede enterrada:
- `preclash/costura.py`: pontas da mesma rede a até 15 cm (planta) e 5 cm (cota), fora de caixa, viram um nó. Fecha as folgas de 2 a 14 cm e os tubos sobrepostos.
- `conexoes.py`:
  - ponta que chega no meio de outro tubo da rede ganha junção;
  - uma peça por ponto (sem conexões sobrepostas);
  - curva sem peça até 30° só para eletroduto FLEXÍVEL (material com PEAD/corrugado/flex: `materiais_flexiveis`). O eletroduto rígido (PVC roscável) leva curva a partir de 5° (correção da 2ª revisão, 20/10/2026).
  - A peça comercial aceita até 5° de deflexão na junta (`tol`, campo `deflexao`); acima disso ela é marcada "fora do comercial".
- `rodar.py` tira elemento ou caixa com id repetido no adaptador (a peça saía duas vezes no IFC: PCI-AH-05/08).
- `export_ifc.py`:
  - a perna da conexão não passa de 45% do tubo vizinho (sem "pedaço menor que a conexão");
  - federado só com os marcadores CRÍTICOS;
  - Pset neutro `Dados_ETIB`, sem campos nem texto de processo (sem "PRECLASH", nome de pessoa ou "estudo");
  - material por IfcRelAssociatesMaterial;
  - diâmetro em `Pset_PipeSegmentTypeCommon` / `Pset_CableCarrierSegmentTypeConduitSegment`;
  - PredefinedType sempre informado (USERDEFINED + ObjectType quando não há um padrão).
- Ângulo do traçado fora do comercial (AF 30,8°, DRE 15,7°/93,9°) é geometria do projeto: a peça sai com o ângulo comercial mais próximo e `angulo_real` no Pset. Mudar exigiria mexer em planta.

O incêndio da Jandaíra R03 saiu "picotado" na casa de bombas. Causas:
- o estudo de cota tratou o barrilete das bombas como rede enterrada e o levou a 1,10 m de recobrimento, 2 m abaixo das bombas;
- cada pedaço foi para a cota pelo próprio diâmetro, desalinhado;
- as válvulas e tês do barrilete não vieram no modelo, e ficaram vãos.

Correções:
- `estudo.py` não estuda pressurizada a menos de `'raio_fixo'` (3 m) de bomba ou tanque (`'fixar_perto_de'`), nem a marcada com `info['estudo'] = False`: ela fica na cota do modelo.
- O eixo do grupo segue o maior diâmetro, então a redução não vira degrau.
- `preclash/verificar.py` roda em todo cenário do `rodar.py` e grava `<SIGLA>_preclash_<cen>_verificacao.csv`, com o resumo no LEIA-ME da rodada. Ele aponta:
  - ponta solta: não encosta em outra ponta, caixa ou trecho da mesma rede;
  - degrau: mesmo ponto em planta, cotas diferentes e sem peça vertical;
  - pedaço curto: menos de 0,15 m que não é vertical;
  - rede fora do lugar: topo acima do terreno ou abaixo do teto + 0,30 m.
- Item já explicado (fim de rede no quadro, niple entre válvulas, saída de prédio): no adaptador, `VERIFICACAO_ESPERADA = {(tipo, trecho): motivo}` (trecho com `*` no começo vale para todos os `.N`). Sai como `esperado` no CSV e fora da contagem.
- Conferir a lista no 3D antes de entregar. Válvula, tê ou redução que falta precisa entrar no adaptador como caixa com `classe_ifc` (ex.: IfcValve).

## Clash pela forma real da estrutura (20/10/2026)
A caixa envolvente de uma sapata cônica acusa colisão que não existe. Na Jandaíra R03, 3 dos 6 críticos passavam livres na forma real.
- Caixa (estrutura ou equipamento) com `info['malha']`, triângulos (n,3,3) em UTM: o `rodar.py` recalcula os conflitos tubo × caixa dela por `clash.refinar_forma`.
- O cálculo corta a malha em 5 alturas da seção do tubo, a cada 2 cm do eixo, e mede a distância ao fecho convexo do corte. É o método do `folga_forma_real.py` da Jandaíra.
- O que fica livre sai dos conflitos, dos pendentes, do federado e do resumo. O que fica marca `forma_real=True`.
- A mesma malha vai para o IFC (IfcTriangulatedFaceSet): quem abre o federado vê a sapata como ela é, e não um prisma.
- Sem `malha`, vale a caixa envolvente, como antes.
- O adaptador põe a malha (o `jan_modelo.estrutura` já lê os triângulos do RVT as built).
