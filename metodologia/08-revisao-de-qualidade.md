# 08. Revisão de qualidade

Nenhuma entrega sai sem o veredito **APROVADO** do [checklist](referencias/CHECKLIST.md). A skill [`revisao-qualidade-etib`](../revisao-qualidade-etib/SKILL.md) executa a revisão.

## Papel

- O analista de qualidade **não faz o projeto**: abre o que a entrega tem (IFC, PDF, DWG, pasta de envio), confere e devolve pendências objetivas. Quem corrige é quem é dono da entrega.
- Só lê. O que a revisão grava fica em `FERRAMENTAS/revisao/relatorios/<ESCOLA>/`.
- Exceção a uma regra (ex.: profundidade além do máximo) só vale com aprovação escrita do dono, registrada em `entregas.py` com a fonte.
- Esforço de raciocínio alto (xhigh) na revisão.

## Como rodar

1. Atualizar a entrada da escola em `FERRAMENTAS/revisao/entregas.py`: pastas do IFC, PDF, DWG, envio e CDE; onde estão as revisões de origem; exceções aprovadas; pendências declaradas.
2. Rodar (2 a 4 min):
   ```
   cd FERRAMENTAS/revisao
   bash ../_nuvem/etib-python revisar.py <escola> --recortes
   ```
   Opções: `--sem-envio`, `--sem-ifc`, `--sem-pdf`, `--ifc/--pdf/--dwg/--envio PASTA`, `--classes-suspensas`.
3. Olhar os recortes (origem à esquerda, revisada à direita) para os itens visuais.
4. Conferir à mão cada grupo de pendência: o script aponta, o analista confirma.
5. Devolver o veredito e a lista (prancha ou arquivo, local, regra). A entrega corrige em lote e pede nova rodada até zerar.

## Módulos

| Arquivo | Itens | O que confere |
|---|---|---|
| `envio_conf.py` | A | conteúdo, revisão única, hash envio = conferido = CDE, PDF + DWG + logos, nomes, LEIA-ME |
| `ifc_conf.py` | B, C, D | lê os IFC como o cliente recebe: classes, material, diâmetro, sistema, processo interno, continuidade, profundidade, degrau, elétrica × água, caixas, clash pela malha real |
| `pdf_conf.py` | E | texto vetorial do PDF, carimbo, quadro de revisões, notas de profundidade, sobreposição por caractere, etiquetas e cotas × origem, tipo de linha, padrão gráfico |
| `pendencias/pagina.py` | F | página de pendências abre no celular, dois blocos, conteúdo das fichas |

## Seções do checklist

| Seção | Assunto |
|---|---|
| 0 | Entrada da escola |
| A | Entregável e pasta de envio |
| B | IFC: informação (classes, PredefinedType, material, diâmetro, sistema, código, processo interno, caixas ocas) |
| C | IFC: continuidade e conexões |
| D | IFC: regras de compatibilização (profundidade, Z, elétrica acima da água, caixas no terreno, clash, gravidade com cota do projeto, escopo, rede acima do piso fora da estrutura) |
| E | Pranchas (A0, carimbo, revisão coerente, uma nota por trecho, legibilidade, nada de processo, tipo de linha, padrão gráfico) |
| F | Página de pendências |

## Veredito

- **APROVADO**, **APROVADO COM ITEM SUSPENSO** (combinado antes) ou **REPROVADO**.
- Pendência bloqueia; observação não bloqueia, mas volta para a entrega; suspenso é item combinado para depois.
- Relatório `REVISAO_<SIGLA>_<data>.md` + `_achados.csv` (uma linha por achado, com coordenada).

## Armadilhas já calibradas

- PV redondo lido como quadrado acusa colisão falsa nos cantos.
- Caixa de texto girado no PDF é a caixa envolvente (enorme): sobreposição só pela caixa de cada caractere.
- Nota que já vinha do projetista não é nota de processo: só conta texto novo em relação à origem.
- Federado com marcadores de "atenção" ou Pset com nome de pessoa é processo interno indo ao cliente.
- Ponta de rede sem nada no modelo pode ser entrada de edificação: observação, não pendência.
