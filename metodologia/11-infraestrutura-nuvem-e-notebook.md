# 11. Infraestrutura: nuvem e notebook

## Nuvem primeiro

Decisão de 26/10/2026: todo o trabalho de escola nova roda na nuvem, sem esperar o notebook: entrada, leitura e gravação de DWG, compatibilização, IFC, visualizador, revisão das pranchas, carimbo, PDF, revisão de qualidade, página de pendências e CDE.

| Etapa | Onde | Por quê |
|---|---|---|
| Ler e gravar DWG | nuvem (ODA File Converter + ezdxf) | |
| Modelagem, clash, IFC, federado | nuvem (Python) | |
| Revisão do desenho, carimbo, PDF | nuvem | |
| Revisão de qualidade, página de pendências | nuvem | |
| **Ler RVT (terreno, estrutura, arquitetura)** | **máquina Windows com Revit + add-in revit-mcp** | o Revit só roda no Windows com licença |
| **DWG que não abre no ODA** | **AutoCAD com janela** | objetos personalizados (QiBuilder) |
| **Cópia para o Google Drive** | **notebook** (pasta sincronizada) | o conector não grava arquivo grande |

## Ambiente da nuvem

```
bash ferramentas/ambiente/preparar_nuvem.sh       # 1x por sessão, < 1 min
export ETIB_RAIZ=$HOME/etib-raiz                   # árvore igual à da pasta do projeto no notebook
cd $ETIB_RAIZ/FERRAMENTAS/revisao && bash $ETIB_RAIZ/FERRAMENTAS/_nuvem/etib-python revisar.py <escola>
```

- Python 3.11 com **versões fixas** (`ferramentas/ambiente/requirements.txt`): ifcopenshell 0.9.0.post1, ifcclash 0.9.0, numpy 2.4.6, shapely 2.2.0, pymupdf 1.28.2, matplotlib 3.11.2, pillow 13.0.0, ezdxf 1.4.5, olefile 0.47. ifcopenshell muda a API entre versões: não subir sem testar.
- ODA File Converter (baixar no site da Open Design Alliance; roda com `xvfb-run`) e LibreOffice (tabelas OLE do Excel nas pranchas).
- Os scripts **não foram reescritos** para a nuvem: `_nuvem/etib-python` carrega um `sitecustomize.py` que traduz na hora `D:\Projeto Modelagem\...` → `$ETIB_RAIZ/...` e `G:\Meu Drive\...` → `$ETIB_G/...`, troca barra invertida e acha nome com maiúscula diferente como no Windows.
- Passos que chamam accoreconsole, Revit, PowerShell ou tasklist não rodam na nuvem.
- Os dados da escola chegam na nuvem copiados do notebook (mesma árvore). Atenção: copiar a pasta de trabalho da escola inteira; alguns scripts regeneram arquivos e ignoram em silêncio os que faltam.

## Notebook

- Pasta do projeto no Windows, com a mesma árvore (capítulo 02) e um `.venv` com as mesmas versões.
- Acessado pelo agente por Remote Control (sessão do Claude Code no próprio notebook) ou por acesso a pasta.
- **Um accoreconsole por vez**; encerrar só os PIDs próprios. Rodar sempre com timeout, porque o console trava em silêncio.
- **Revit: um trabalho por vez; nunca fechar modelo sem salvar.**
- As pastas da construtora no Drive são somente leitura.

## Etapa do Revit: duas formas

Tudo o que lê RVT precisa de uma máquina Windows com o **Revit 2025 aberto e licenciado** e com o add-in **revit-mcp** (o servidor MCP do Revit) instalado. Não há como rodar o Revit na nuvem. O add-in recebe código C# (o comando `send_code_to_revit`) na porta 8080 e o executa dentro do Revit. As duas formas abaixo usam o mesmo add-in; muda só quem manda o comando.

Requisitos comuns: Revit aberto, **algum documento aberto** e o botão **"Revit MCP Switch"** ligado em Complementos (volta desligado quando o Revit reinicia; esperar a porta 8080 responder).

### Forma atual: scripts no notebook pelo Remote Control

O agente abre uma sessão do Claude Code no notebook (Remote Control) e roda os scripts, que falam com o add-in pela porta 8080 por meio do `FERRAMENTAS/revit_rpc.py` (cliente direto, sem depender do servidor MCP conectar):

```
cd "D:\Projeto Modelagem\FERRAMENTAS"
.venv\Scripts\python.exe -X utf8 entrada\revit_conv.py <ESCOLA> <ESCOLA> <ESCOLA>
```

- `entrada/revit_conv.py`: numa sessão só do Revit, abre cada RVT da escola desanexado, lê o terreno e os pisos do IMP e a estrutura pela forma real (`entrada/revit/estrutura_tri.cs`) em coordenada UTM, grava para o preclash e fecha **sem salvar**. O IFC de entrega do terreno e da estrutura sai depois do preclash, na nuvem.
- Federado único: a implantação é exportada em IFC4 nas coordenadas compartilhadas, com a lista dos vínculos e a transformação de cada um, e cada RVT de módulo sozinho na origem interna (modelo de script `FERRAMENTAS/exemplo/revit/alh_asbuilt_ifc.py`, no notebook; passo a passo em `federado-unico-etib/referencia/EXPORTAR_RVT.md`).
- Os IFC e malhas vão para `G:\Meu Drive\ETIB_ENVIOS\_TROCA_NUVEM\` e de lá para a nuvem.

### Opção: o agente chama o MCP do Revit direto

Um agente rodando na própria máquina do Revit, com o servidor MCP do Revit configurado no Claude Code, chama a ferramenta `send_code_to_revit` sem script intermediário. Foi o método da escola A e de escola B (modelagem inteira no Revit); a skill [`modelagem-bim-disciplinas`](../modelagem-bim-disciplinas/SKILL.md) documenta o uso completo. Serve para conversões pontuais, para conferir o que está aberto e para destravar o Revit. Não tira a dependência da máquina: o MCP só existe onde o Revit está aberto.

### Armadilhas do add-in (valem nas duas formas)

- O código já roda numa transação: não abrir `Transaction` (usar `SubTransaction`); para desfazer, lançar exceção.
- Um comando por vez. Depois de um timeout, a resposta seguinte pode ser a do comando anterior: conferir com um marcador ("CHECKn") antes de repetir.
- **Diálogo modal = timeout.** Ler e clicar com `FERRAMENTAS/revit_dialog.ps1 -Click "OK"` (UIAutomation) ou `revit_win32_dialog.ps1` (diálogo Win32 clássico, BM_CLICK). Sempre ler antes de clicar.
- Conferir `doc.Title` antes de editar (o documento ativo muda quando o usuário troca de janela).
- Salvar: `PostCommand(PostableCommand.Save)` no documento ativo; `doc.Save()` fora de transação no documento em segundo plano. Conferir pela data do arquivo. **Nunca fechar modelo sem salvar** quando houve edição.
- Retorno grande estoura a resposta: gravar em arquivo e devolver resumo. Lotes de dezenas de elementos, não centenas.
- Revit 2025: `new ElementId(long)`.
- Suplemento com caixa de mensagem em loop (ex.: sem login) trava tudo: com autorização, renomear o `.addin` para `.addin.off`.

## AutoCAD `accoreconsole` (só no notebook)

- `Start-Process` com `/i arquivo.dwg /s script.scr`, scripts em CRLF começando com `SECURELOAD 0`.
- Sem `vla-*` (não há ActiveX no console): `entget`, `entmod`, `ssget`.
- Destravar o layer antes de apagar; trabalhar sempre em cópia.
- O dump por LISP não traz chamadas nem MULTILEADER: ler pelo PDF.
- Situação completa estoura 5 min: filtrar layers no `ssget`.
- Na nuvem o equivalente é ODA → DXF → ezdxf, já conferido igual ao AutoCAD.

## Estrutura de pastas do projeto

```
<pasta do projeto>/
├── ETIB-<ESCOLA>/            uma por escola (capítulo 02)
├── FERRAMENTAS/              motor preclash, revisão, pranchas_cde, pendências, entrada, scripts por escola
├── PRANCHAS/                 CDE das pranchas vigentes + PRANCHAS_INDICE.md
├── TEMPLATES/, _MODELO-ESCOLA/
├── VISUALIZADOR_CONFLITOS/
├── AGENTS.md                 regras vigentes (para qualquer agente)
└── licoes-modelagem.md       histórico de lições
```

Vínculos do Revit são relativos à pasta da escola: mover a pasta inteira é seguro; mover arquivo solto quebra vínculo.
