# 07. Pranchas e carimbo AS BUILT

As pranchas são **executivo final / as built, lidas no campo** pelo construtor e pelo mestre de obras (decisão de 19/10/2026). Nada de nuvem, rascunho, traçado "substituído" ou menção a revisão interna e pré-compatibilização.

## Regras do desenho

- Mudança de traçado no padrão da planta, mexendo o mínimo; o trecho antigo sai e o novo entra **na mesma entidade** (mesma layer, cor, tipo e escala de linha, espessura). Tracejado continua tracejado. ByLayer.
- Caixa deslocada: símbolo e texto andam juntos; as pontas das linhas que chegam nela acompanham; as tags de diâmetro e fluxo acompanham o trecho.
- Só profundidade: nota curta no estilo do texto mais próximo ("ELETRODUTO A 1,40 m DE PROFUNDIDADE").
- **No máximo UM rótulo de profundidade por trecho** (decisão de 20/10/2026: "PROF. 0,90 m" repetido 20 vezes num eletroduto). Os pedaços da mesma rede, mesmo texto e mesmo trecho se juntam; outra nota só a mais de 15 m.
- Nota nunca sobre tag ou texto da arquitetura; nada sobreposto na folha inteira.
- Etiquetas de material, diâmetro, trecho, circuito e cotas do projeto preservadas.

## Padrão gráfico

Decisão de 22/10/2026:

- Rede existente ou de cadastro numa **cor bem visível** que a legenda da folha não use (nada de cinza apagado, preto ou cor clara), com texto na altura padrão da folha.
- Anotação nossa nunca maior que o texto do projetista.
- Toda mudança de cor, tipo de linha ou elemento novo confere a legenda: a cor não repete a de outro item, e o que não estiver na legenda entra nela (ex.: linha "Rede existente").
- **Prévia:** junto com o "pronto para envio", miniaturas antes e depois de cada folha alterada vão ao dono (`rever.py --miniaturas`).

## Ferramentas

| Passo | Script | O que faz |
|---|---|---|
| Plano da revisão | `preclash/executivo/rever.py <escola> [cen]` | lê as mudanças da rodada (mergulhos, contornos, caixas deslocadas, em UTM), acha a entidade de cada trecho no DXF da cópia (tolerância 6 cm) e planeja os comandos |
| Aplicar (nuvem) | `revisao_ezdxf.py` | aplica o `_cmd` do `rever.py` com ezdxf |
| Aplicar (notebook) | `executivo/revisao.lsp` no accoreconsole | DEL, PLC, REPL, MV, VTX, TXC, RT, CPR, ST, LT |
| Carimbo QG | `carimbo_qg.py` / `carimbo_ezdxf.py` | carimbo da construtora com os 3 logos |
| Carimbo AS BUILT | `preclash/executivo/carimbo_asbuilt.py` | etapa AB, disciplina CONDER, R00, título |
| PDF | `pranchas_pdf/render_pdf_nuvem.py` | PDF A0 na nuvem |
| PDF híbrido | `pranchas_pdf/hibrido.py` | PDF do AutoCAD com só o carimbo novo encaixado |

Conferido na Sátiro: revisão e carimbo da nuvem idênticos aos do AutoCAD, entidade a entidade.

## Carimbo AS BUILT

Decisão de 27-28/10/2026, aprovada no piloto da Jandaíra e válida para todas as escolas. A prancha entregue é de **outra etapa** (As Built), então volta a R00.

- **Código pela nomenclatura CONDER** `AA-CTR-MUN-LOC-EMPR-PAE-EP-DIS-999-DES-R99`: etapa **AB** no lugar de PE; disciplina com o código CONDER da tabela 9.1: **AGF** água fria, **ESG** esgoto, **DRE** drenagem, **PCI** incêndio, **ELE** elétrica (também PDA SPDA, CTV CFTV, AAC águas pluviais). **Nunca AF, EL, IN.** Ex.: `24-049-JDI-CTO-ETIB-IMP-AB-AGF-001-HIG-R00`. O conteúdo (HIG, DRG, ELG, ING) fica como o do projetista.
- Mesma disciplina no código, no nome do arquivo e no campo da folha (`AGF_IMP-001_R00`).
- Assunto: "PROJETO DE AS BUILT DE <disciplina por extenso>".
- Título como no modelo da guarita: nome do colégio (em duas linhas se longo), setor (IMPLANTAÇÃO) e endereço completo.
- Quadro de revisões só com "R00 | data | EMISSÃO INICIAL", responsável **vazio**.

```
bash _nuvem/etib-python preclash/executivo/carimbo_asbuilt.py ... --escola "LINHA 1|LINHA 2" --endereco "RUA ..., CIDADE - BA"
```

## PDF

- Folha A0 (1189 × 841 mm, "ISO full bleed A0"), um PDF por folha, Extents e Fit. O DWG de mesmo nome é gravado antes do PDF, com os logos ao lado.
- Nuvem primeiro (decisão de 26/10/2026). O render da nuvem ainda perde tracejado grosso e negrito em algumas folhas: quando só o carimbo muda numa folha já plotada no AutoCAD, o PDF de entrega é o do AutoCAD com o carimbo novo encaixado (`pranchas_pdf/hibrido.py`).
- Fontes: o render usa as fontes reais das pranchas (Arial, Swiss 721, romans/simplex/isocp). Elas têm licença e não vão no repositório: copiar da pasta de fontes do Windows para `pranchas_pdf/fontes/`.

## Armadilhas

- DWG que não reabre depois de gravado (ErrorStatus 53): AUDIT antes e depois.
- MTEXT sem fundo e com no máximo 250 caracteres no grupo 1 (o resto em blocos de 250 no grupo 3), senão o `entmake` falha sem avisar.
- O DWG abre na folha: `(setvar "TILEMODE" 1)` antes de criar entidade, senão cai no espaço do papel.
- Estilo Standard das pranchas usa SHX sem acento: pôr `{\fArial|b0|i0|c0|p34;…}` no MTEXT.
- Texto novo copiando molde: o grupo 41 só se copia de molde TEXT (no MTEXT é a largura da caixa).
- Carimbo da QG: os atributos de revisão ficam fora do quadro; o código grande e o "ARQUIVO" são campos com o nome do arquivo, então salvar com o nome final e plotar de uma cópia com o mesmo nome.
