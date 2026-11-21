# AGENTS.md — Metodologia ETIB (modelagem e compatibilização em IFC)

Ponto de entrada para qualquer agente (Claude Code, Codex etc.) que vá executar o método. Idioma de tudo: **português do Brasil**.

## O que é este repositório

O método completo da equipe para modelar, compatibilizar e entregar em IFC as redes externas das escolas ETIB (contrato da construtora, aprovação CONDER), com o código que executa cada etapa.

```
AGENTS.md                      este arquivo (leia primeiro)
metodologia/                   o método, capítulo por capítulo (comece pelo README)
  13-execucao-passo-a-passo.md roteiro executável de uma escola, com comandos e critérios
  14-escola-nova.md            como começar uma escola nova (ou outro contrato)
  referencias/CHECKLIST.md     checklist de qualidade (fonte única dos itens de revisão)
modelos/                       modelos fictícios: INVENTARIO, LEIA-ME de envio, onde ficam os modelos de configuração
ferramentas/
  etib/                        código das FERRAMENTAS (motor preclash, revisão, pranchas, CDE, pendências, entrada, scripts por escola)
  ambiente/                    requirements.txt (versões fixas) e preparar_nuvem.sh
  pranchas_pdf/                render do PDF das pranchas na nuvem
federado-unico-etib/           skill: IFC federado único da escola
revisao-qualidade-etib/        skill: revisão de qualidade antes do envio
modelagem-bim-disciplinas/     skill: método antigo, no Revit via MCP (usado no piloto)
```

## Antes de começar

1. Ler `metodologia/README.md` e o capítulo da etapa que vai fazer. As regras com data são decisões do dono do projeto: **não se perguntam de novo**.
2. Preparar o ambiente (`metodologia/13-execucao-passo-a-passo.md`, passo 0). Python 3.11 com as versões de `ferramentas/ambiente/requirements.txt`; não subir versão sem testar.
3. Saber onde estão os dados da escola. Eles **não** estão neste repositório: ficam na pasta do projeto (`ETIB-<ESCOLA>/`) e no Drive da construtora.

## Regras que não se quebram

- **Pastas da construtora e `PROJETO_ORIGINAL/`: somente leitura.** Nunca mover, apagar, renomear ou editar.
- **Só redes externas**, da face da parede para fora. Disciplinas: AF/AGF, ESG, DRE, ELE, PCI (hidrante e SDAI). Fora: ETE, GLP, CFTV/dados, solar, contenção, paisagismo (não citar em documento entregue).
- **Mexer o mínimo; preferir só profundidade. NUNCA mover vértice em planta para encaixar ângulo comercial.**
- Profundidade máxima do terreno ao topo do tubo: 2,00 m (outro valor só se combinado para a escola). Elétrica sempre acima da água. Cota de pressurizada só muda dentro de caixa.
- As built vale sobre o projeto. Terreno: vale a base.
- Aplicar e avisar só dentro dos limites do capítulo 05; o resto é decisão do dono.
- Nada de processo interno (ferramenta, pessoa, jargão, propriedades de trabalho) em IFC, prancha ou LEIA-ME entregue.
- Nada sai sem checklist **APROVADO**; envio e CDE no mesmo passo.
- Um accoreconsole por vez. Revit: um trabalho por vez; nunca fechar modelo sem salvar.
- Antes de apagar ou sobrescrever, olhar o alvo.

## O que roda onde

| Etapa | Onde |
|---|---|
| Tudo o que é Python (DWG via ODA + ezdxf, modelagem, clash, IFC, pranchas, PDF, revisão, página de pendências, CDE) | nuvem / qualquer Linux com o ambiente fixo |
| Ler RVT (terreno, estrutura, arquitetura) | **máquina Windows com Revit 2025 aberto + add-in revit-mcp** (capítulo 11) |
| DWG que não abre no ODA | **AutoCAD com janela**, pelo dono |
| Cópia para o Google Drive (envio e CDE) | **notebook** com a pasta do Drive sincronizada |

Os scripts foram escritos para o Windows (`D:\Projeto Modelagem\...`, `G:\Meu Drive\...`). No Linux, rode sempre com `ferramentas/etib/_nuvem/etib-python`, que traduz esses caminhos para `$ETIB_RAIZ` e `$ETIB_G`. Defina também `ETIB_NOMES_EQUIPE` (nomes da equipe, separados por vírgula) para que a revisão barre qualquer nome de pessoa na entrega.

## Quando parar e perguntar

- Colisão que passa dos limites do aplicar e avisar, estrutura executada, falta de projeto, mudança de escopo.
- Exceção a qualquer regra (ex.: profundidade acima do máximo): só com aprovação escrita do dono, registrada em `revisao/entregas.py`.
- Divergência entre referências: quantificar e mapear antes de perguntar; não "consertar" a referência.
- Agrupar as perguntas numa vez só, com a opção recomendada. Decisão que permite seguir: aplicar a recomendada, registrar e continuar.

## Manutenção

Regra nova do dono: atualizar no mesmo dia o capítulo da metodologia (e o checklist, se for item de revisão), apagando a regra antiga. Correção de código: editar em `ferramentas/` e no projeto, com commit explicando o que mudou.
