# Metodologia ETIB: modelagem e compatibilização em IFC

Método de trabalho da equipe para modelar, compatibilizar e entregar em IFC as redes externas das escolas ETIB (contrato 24-049), com o código e as skills que executam cada etapa.

- **Agente:** comece pelo [`AGENTS.md`](AGENTS.md).
- **Pessoa:** comece pela [metodologia](metodologia/README.md).
- **Executar uma escola:** [roteiro passo a passo](metodologia/13-execucao-passo-a-passo.md).
- **Ferramentas:** [`ferramentas/`](ferramentas/) (Python 3.11, versões fixas em `ferramentas/ambiente/requirements.txt`).

## Skills do Claude Code

| Skill | Para quê |
|---|---|
| [`federado-unico-etib`](federado-unico-etib/SKILL.md) | IFC federado único da escola (detalhes abaixo) |
| [`revisao-qualidade-etib`](revisao-qualidade-etib/SKILL.md) | revisão de qualidade antes de todo envio |
| [`modelagem-bim-disciplinas`](modelagem-bim-disciplinas/SKILL.md) | método antigo, no Revit via MCP |

Para instalar uma skill, copie a pasta dela para `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).

---

## Federado único

Este é o método do **IFC federado único** das escolas ETIB , empacotado como skill do Claude Code. É o padrão aprovado na Jandaíra R04 em 29/10/2026.

O resultado é um só IFC4 da escola com:
- o terreno recortado no lote;
- as redes externas compatibilizadas;
- a estrutura as built;
- a arquitetura completa dos módulos, vinda do RVT da construtora ou do padrão ETIB;
- a divisa, os reservatórios e a urbanização (platôs, pisos externos e piso tátil).

Ele passa por conferência automática e sai com prévias e o pacote de envio.


## Instalar (uma vez)

1. Copie a pasta `federado-unico-etib/` para a pasta de skills do Claude Code:
   - Windows: `%USERPROFILE%\.claude\skills\federado-unico-etib\`
   - Linux/Mac: `~/.claude/skills/federado-unico-etib/`
2. Crie o ambiente Python 3.11 com as versões fixas:
   ```
   python -m venv .venv-federado
   .venv-federado\Scripts\activate        (Linux/Mac: source .venv-federado/bin/activate)
   pip install -r federado-unico-etib/requirements.txt
   ```
3. Para ler DWG, salve como DXF no AutoCAD ou use o ODA File Converter.

## Usar

No Claude Code, aberto na pasta do projeto, peça por exemplo "monte o federado único da escola Alagoinhas". A skill guia o passo a passo:
- o JSON da escola;
- a cota do RVT;
- os módulos, a divisa, a urbanização e o terreno;
- a montagem, a conferência, as prévias e o pacote.

Os detalhes estão em:
- `federado-unico-etib/SKILL.md`: o método e as armadilhas;
- `federado-unico-etib/referencia/CONFIG.md`: cada campo do JSON;
- `federado-unico-etib/referencia/EXPORTAR_RVT.md`: como exportar os RVT da construtora;
- `federado-unico-etib/escolas/JDI.json`: o exemplo real da Jandaíra.

## Atualizar

Puxe o repositório (`git pull`) e copie a pasta de novo. As correções de método entram aqui, com uma linha no histórico explicando o que mudou.
