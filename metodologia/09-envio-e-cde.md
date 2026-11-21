# 09. Envio e CDE

Decisão de 22/10/2026: **envio e CDE no mesmo passo**. Com o checklist APROVADO, quem é dono da entrega sobe a pasta de envio e publica no CDE, no índice e na aba Pranchas do visualizador na mesma hora, sem pedir ok. O envio à construtora é o dono do projeto compartilhar o link. A escola só conta como entregue com o CDE atualizado (item A3 do checklist).

## Pasta de envio

```
ETIB-<ESCOLA>_<data>[_R<nn>]/
├── 01_PRANCHAS_PDF/     um PDF A0 por folha alterada
├── 02_PRANCHAS_DWG/     DWG de mesmo nome + os 3 logos do carimbo
├── 03_IFC/              IFC por disciplina + terreno + estrutura de referência + federado
├── 04_PREVIA/           imagens (federado único)
└── LEIA-ME.txt
```

- Só a revisão vigente de cada folha: nada de `_REVISADO`, `.bak`, `.dxf`, `.log`, cópia.
- Os arquivos do envio são os mesmos que foram revisados (hash igual).
- O LEIA-ME não fala de processo interno (ferramenta, script, nuvem, nomes de pessoas da equipe) nem de disciplina fora do escopo, e o que afirma bate com as pranchas.
- Entrega só de modelagem com rede acima do piso: lista de passagens em viga (`<SIGLA>_passagens_em_viga.csv`).

## Limpeza do IFC

Depois do APROVADO, na pasta de envio:

```
bash _nuvem/etib-python revisao/limpar_entrega.py <envio>/03_IFC <csv interno>
```

Tira `fora_do_comercial`, `angulo_real` e `deflexao_junta_graus` e grava o registro interno na pasta `revisao/` da escola. O `envio_conf.py` reprova envio com essas propriedades e aceita o IFC que só difere do conferido por elas.

## Onde sobe

| Destino | O quê | Quem faz |
|---|---|---|
| Pasta de envios do Drive do dono (privada) | a pasta de envio inteira | notebook (cópia para o Drive) |
| Pasta do CDE das pranchas no Drive | PDF de cada folha nova; a anterior vai para `_SUPERADAS` | notebook |
| `PRANCHAS/<ESCOLA>/` + `PRANCHAS_INDICE.md` | mesma coisa, cópia local e na biblioteca do projeto | nuvem |
| Visualizador (aba Pranchas) | `pranchas.json` | nuvem |

Arquivo grande para o Drive: partes de 24 MB, juntadas no notebook. Só a revisão vigente de cada entrega fica na pasta de envios; as superadas são apagadas a pedido do dono.

## CDE passo a passo

Seguir `FERRAMENTAS/pranchas_cde/LEIA-ME.md`; um trabalho por vez no CDE.

1. PDF novo em `PRANCHAS/<ESCOLA>/` e na pasta do CDE no Drive; a original vai para `_SUPERADAS/` nas duas.
2. Pegar o ID do PDF novo no Drive e pôr em `MODIFICADAS` no `pranchas_json.py`.
3. Rodar `pranchas_json.py` e publicar **só** o `pranchas.json` no visualizador (sem mexer no `index.html` nem em `dados/`).
4. Atualizar a linha no `PRANCHAS_INDICE.md` e subir PDF + índice para a biblioteca, mantendo um índice só.

Não mexer à mão no `pranchas.json` ao republicar.

## Depois da entrega

- Comentário na issue da escola no Linear e estado em Done (capítulo 10).
- Linha da escola atualizada na tabela de escolas do `AGENTS.md` (onde olhar o envio e o LEIA-ME).
- Thread da escola fechada.
