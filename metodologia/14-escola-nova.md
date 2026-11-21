# 14. Começar uma escola nova

O que um agente faz para replicar o método numa escola (ou obra) que ainda não passou por ele. O roteiro com comandos está no [capítulo 13](13-execucao-passo-a-passo.md); aqui fica a ordem e o que é preciso combinar antes.

## O que pedir antes de começar

| O quê | De quem |
|---|---|
| Pasta da construtora com projeto (DWG e PDF de cada disciplina), as built, memoriais e RVT | construtora |
| Escopo: disciplinas, setores (implantação, blocos, campo) e o que fica fora | dono do projeto |
| Ordem de entrega e prazo | dono do projeto |
| Nome completo da escola e endereço (título do carimbo) | construtora / dono |
| Logos do carimbo do cliente e tabela de nomenclatura do órgão aprovador | construtora |
| Profundidade máxima, se diferente de 2,00 m | dono do projeto |
| Acesso a uma máquina com Revit (para ler os RVT) e à pasta de envio | dono do projeto |

## Ordem

1. **Registrar a escola.** Escolher a sigla (3 letras) e a origem (ponto UTM redondo perto da obra, cota 0). Pôr na tabela de escolas do `AGENTS.md` da pasta do projeto.
2. **Pasta da escola.** Copiar a estrutura do capítulo 02 e o modelo `modelos/ETIB-ESCOLA/INVENTARIO.md`. `PROJETO_ORIGINAL` = cópia fiel do que veio da construtora.
3. **Entrada** (capítulo 02). Fechar o quadro antes de modelar.
4. **Georreferenciar e extrair** (capítulo 03). Uma transformação por DWG; CSV das fases 2 e 3.
5. **Terreno** (`exemplo_terreno.py` → `<escola>_terreno.py`) e **adaptador** (`exemplo.py` → `<escola>.py`).
6. **Modelar e compatibilizar** (capítulos 04 e 05): `rodar.py <escola>` até 0 colisão crítica fora das pendências; aplicar e avisar dentro dos limites.
7. **Página de pendências** (capítulo 05), se houver decisão; voltar ao passo 6 com as respostas.
8. **Pranchas** (capítulo 07) com o carimbo AS BUILT.
9. **Revisão de qualidade** (capítulo 08): entrada nova em `entregas.py`; repetir até APROVADO.
10. **Envio e CDE** (capítulo 09), com o LEIA-ME do modelo `modelos/ETIB-ESCOLA/LEIA-ME_envio.txt`.
11. **Federado único** (capítulo 06), com `federado-unico-etib/escolas/EXEMPLO.json` como ponto de partida.
12. **Registrar lições.** Erro novo vira linha no capítulo 12 e, se mudar regra, a regra muda no capítulo dela.

## Adaptar a outro contrato

O método não depende do contrato. Ao usar em outro:

- trocar a nomenclatura das folhas (capítulo 07) pela do órgão aprovador do novo contrato e o carimbo pelo do cliente;
- revisar o escopo e as disciplinas (capítulo 01) e a profundidade máxima (`preclash/preclash/parametros.py`);
- conferir o EPSG da zona UTM da obra;
- manter as regras de compatibilização, de IFC e de revisão, que são do método e não do contrato.
