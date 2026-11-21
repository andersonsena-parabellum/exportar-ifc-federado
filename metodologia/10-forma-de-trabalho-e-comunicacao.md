# 10. Forma de trabalho e comunicação

## Quem faz o quê

- **Uma thread (ou agente) dona de cada entregável, de ponta a ponta.** Ela modela, compatibiliza, revisa as pranchas, roda ela mesma os scripts de revisão, corrige em lote e repete até zerar. Só fala com a coordenação quando está limpo ou com as decisões do dono agrupadas numa pergunta.
- **Coordenação:** abre uma thread por entregável, repassa só entregas e decisões (nada no meio do trabalho), mantém o painel e fecha cada thread assim que o trabalho dela termina.
- **Revisão de qualidade:** conferência final independente (capítulo 08).
- **Uma escola por vez**, na ordem de entrega.

## Como decidir

- **Decisão que permite seguir:** aplicar a opção recomendada, registrar e continuar. Não parar o processo.
- **Aplicar e avisar** dentro dos limites do capítulo 05.
- **Pergunta ao dono** só para o que passa dos limites, estrutura executada, falta de projeto e mudança de escopo, agrupada numa vez só, com recomendação.
- Divergência entre referências (ex.: caminhos da situação × passeios do as built): quantificar e mapear (m² e imagem) antes de perguntar. Não "consertar" a referência.
- Quando alguém aponta algo estranho num print, descobrir de qual arquivo e layer aquilo vem antes de opinar.

## Esforço de raciocínio

| Trabalho | Nível |
|---|---|
| CAD, pranchas, organização, compatibilização | alto |
| Revisão de qualidade | muito alto (xhigh) |
| Coordenação | médio |

## Linear

Decisão de 28-29/10/2026:

- Um projeto no Linear com uma issue por escola, na ordem de entrega.
- **O Linear está sempre atualizado:** a thread dona comenta na issue da escola a cada etapa relevante (início, pedido ao notebook ou a terceiro, bloqueio, conferência, entrega) e mantém o estado em dia (In Progress enquanto houver trabalho, inclusive quando uma escola entregue volta a ter serviço; Done só quando não sobra nada).
- **Quando precisa do dono:** sub-issue atribuída a ele, etiqueta "Precisa do dono do projeto" (ou "Esperando terceiro" / "Esperando sócio de modelagem"), texto curto e bem explicado, imagem anexada com destaque desenhado no ponto (círculo ou seta). Fecha quando ele responde.
- Uma tarefa agendada lê as respostas no Linear de hora em hora (7h às 22h) e repassa à thread dona.
- O conector escreve como o dono: todo comentário de agente termina com "_— Claude_".
- O painel do contrato e as páginas de pendências continuam: linkar na issue, não substituir.

## Painel do gerente

Cada escola mostra se está trabalhando, esperando o dono, esperando terceiro ou esperando o notebook.

## Mensagens

- Menos mensagens: posts curtos, só na entrega ou na decisão.
- Junto com o "pronto para envio": miniaturas antes e depois de cada folha alterada.
- Decisões para o dono e o sócio de modelagem vão no canal do Slack do contrato só quando o dono pedir.

## Regra nova

Quando o dono decide algo que muda uma regra, quem recebeu a decisão atualiza **na mesma hora**: as instruções do projeto, `GERAL/INSTRUCOES_PROJETO.md`, o `AGENTS.md` do notebook e esta metodologia, **apagando a regra antiga** (sem cópia de backup; o histórico fica no git).

## Organização

- Arquivos em pastas por escola e por tipo. Nomes novos sem acento e sem espaço.
- Antes de apagar ou sobrescrever, olhar o alvo. Backups do Revit da escola só se apagam ao fechá-la, com o sim do dono.
- Retomar uma escola: ler o LEIA-ME indicado na tabela de escolas e o `INVENTARIO.md`; listar arquivos por data; conferir o estado real (ex.: o que está aberto no Revit) antes de seguir.
