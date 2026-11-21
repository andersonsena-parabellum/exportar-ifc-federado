---
name: revisao-qualidade-etib
description: 'Revisão de qualidade (analista de qualidade) das entregas das escolas ETIB do contrato: confere IFC por disciplina e federado, pranchas PDF/DWG e a pasta de envio contra o checklist do projeto (classes e informação BIM, continuidade da rede e conexões, profundidade máxima, degrau em Z, elétrica acima da água, caixas no terreno, clash com a estrutura pela forma real, carimbo da construtora as built, uma nota de profundidade por trecho, nada de nuvem ou nota de processo) e devolve o relatório aprovado/pendências por escola. Use SEMPRE que pedirem para revisar, auditar, conferir ou liberar a entrega de uma escola antes do envio, rodar o checklist de qualidade, ou "passar pelo analista de qualidade", mesmo sem dizer "skill" (ex.: "revisa a escola H antes de mandar", "confere a pasta de envio da escola A", "a escola G pode ir?"). Não faz o projeto: para modelar ou corrigir use modelagem-ifc-sem-revit.'
---

# Revisão de qualidade das entregas (ETIB, contrato)

O analista de qualidade **não faz o projeto**: abre o que a thread da escola entregou (IFC, PDF, DWG, pasta de envio), confere contra o checklist e devolve uma lista objetiva de pendências. A pasta de envio só é liberada com o veredito APROVADO. Responda em **português**, curto.

- Checklist (fonte única dos itens): `D:\Projeto Modelagem\FERRAMENTAS\revisao\CHECKLIST.md`.
- Parâmetros de compatibilização, padrão das pranchas e profundidade máxima: **não repetir aqui**; vêm da skill `modelagem-ifc-sem-revit`, do `FERRAMENTAS\preclash\LEIA-ME.md`, de `preclash\parametros.py` e do `licoes-modelagem.md` (A2, A2.1). Se uma regra mudar lá, o checklist acompanha.

## Regras do papel

- **Só ler** os arquivos das escolas, o CDE e o Drive. Nada de editar, mover ou "consertar" o entregável; quem corrige é a thread da escola. Tudo o que a revisão grava fica em `FERRAMENTAS\revisao\relatorios\<ESCOLA>\`.
- Drive da construtora é somente leitura; a pasta de envio (`G:\Meu Drive\ETIB_ENVIOS\…`) também não se mexe: a revisão só diz se pode ou não ir.
- `accoreconsole` e Revit só com a vez dada pelo coordenador (a revisão normal não precisa: o PDF é plotado do DWG e o script confere a coerência dos dois).
- Exceção às regras (ex.: profundidade além do máximo) só vale com aprovação escrita do dono do projeto, registrada em `entregas.py` com a fonte.

## Como rodar

1. Atualizar a entrada da escola em `FERRAMENTAS\revisao\entregas.py`: pastas do IFC, PDF, DWG, envio e CDE; `origem_pdf` (onde estão as revisões de origem: `PRANCHAS\<ESCOLA>\_SUPERADAS` e `PROJETO_ORIGINAL`); exceções aprovadas; pendências declaradas pela entrega (trechos).
2. Rodar (2 a 4 min):
   ```
   cd "D:\Projeto Modelagem\FERRAMENTAS\revisao"
   ..\.venv\Scripts\python.exe -X utf8 revisar.py <escola> --recortes [--classes-suspensas]
   ```
   `--classes-suspensas` deixa B2–B6 como "suspenso" enquanto a correção das classes IFC estiver em andamento; `--sem-envio/--sem-ifc/--sem-pdf` e `--ifc/--pdf/--dwg/--envio PASTA` para rodar parte ou outra pasta.
3. **Olhar os recortes** (`relatorios\<ESCOLA>\recortes\`, origem à esquerda e revisada à direita) para os itens visuais (E6, E8, E9, E10): tipo de linha, caixa e texto juntos, nota sobre linha, traçado novo coerente com o IFC.
4. Conferir à mão cada grupo de pendência antes de mandar (abrir o recorte ou o ponto no IFC): o script aponta, o analista confirma.
5. Devolver ao coordenador: veredito + tabela de pendências (prancha/arquivo, local, regra) e o caminho do `REVISAO_<SIGLA>_<data>.md`. A thread da escola corrige e pede nova rodada.

## Módulos (`FERRAMENTAS\revisao\`)

| Arquivo | Itens | O que faz |
|---|---|---|
| `envio_conf.py` | A | conteúdo, revisão única, hash envio = conferido = CDE, PDF+DWG+logos, nomes, LEIA-ME |
| `ifc_conf.py` | B, C, D | lê os IFC como o cliente recebe (eixo do IfcSweptDiskSolid, pernas das conexões, prisma/cilindro das caixas, malha real da estrutura, terreno do IfcGeographicElement); classes/material/diâmetro/sistema/processo interno; continuidade; profundidade, degrau, elétrica × água, caixas, clash |
| `pdf_conf.py` | E | texto vetorial do PDF (girado), carimbo da construtora, quadro de revisões, notas PROF., sobreposição por caractere, etiquetas e cotas × revisão de origem, layers, tipo de linha (tracejado perdido), recortes |
| `revisar.py`, `rev_comum.py`, `entregas.py` | — | orquestra, agrupa achados e grava o relatório + CSV |

## Armadilhas já vistas (calibração na escola A R03, 20/10/2026)

- PV redondo lido como quadrado acusa colisão falsa nos cantos: as caixas de planta redonda viram cilindro.
- Conexão em uma polilinha só ([ponta, vértice, ponta]): o centro é o vértice do meio, não o primeiro ponto.
- Caixa de texto girado no PDF é a caixa envolvente (enorme): sobreposição só pela caixa de cada caractere.
- Nota da legenda que já vinha do projetista (ex.: "verificar possíveis interferências") não é nota de processo: só texto novo em relação à origem conta.
- Etiqueta que sumiu pode ter saído junto com o trecho removido (campo da escola A mudou a descarga): é observação, conferir no recorte; cota de caixa que mudou de valor é pendência.
- Eletroduto que segue o "rebaixo preenchido só para o perfil" fica acima do terreno real do IFC: conferir sempre contra o terreno entregue.
- Federado com marcadores de "atenção" (folga curta) e Pset `PRECLASH` com nome de pessoa é processo interno indo para o cliente.
- Ponta de rede sem nada no modelo pode ser entrada de edificação sem estrutura baixada: é observação, não pendência.
- Patches de código com regex por heredoc no Git Bash comem barras invertidas; editar com Edit/Write.
