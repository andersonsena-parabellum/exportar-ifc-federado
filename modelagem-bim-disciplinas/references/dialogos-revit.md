# Diálogos e suplementos do Revit (destravar sem o usuário)

Ferramenta: `scripts/revit_dialog.ps1` (cópia de `FERRAMENTAS\revit_dialog.ps1` do ETIB). Lê o texto de qualquer diálogo do Revit (UIAutomation) e, com `-Click "texto"`, aperta o botão. `-WaitSec N` espera até N s pelo diálogo.

```powershell
powershell -ExecutionPolicy Bypass -File revit_dialog.ps1               # só lê
powershell -ExecutionPolicy Bypass -File revit_dialog.ps1 -Click "OK"   # lê e clica
```

O filtro de janela principal do script ignora títulos com `MODELAGEM`, `Monitor` ou `- [`. Se o RVT do projeto tiver outro nome e a janela principal aparecer como diálogo, ajuste a regex.

## Regras

- **Sempre leia antes de clicar.**
  - **Aviso** (marca duplicada, hachura) → OK.
  - **Erro não ignorável** → em geral **Cancelar**, que desfaz só o comando do MCP. "Desconectar" resolve conexões ruins sem perder o lote.
- **TaskDialog do Revit:** os botões aparecem como `Pane`, sem InvokePattern; o script clica pela posição (`SetCursorPos` + `mouse_event`).
- **Diálogo Win32 clássico** (`#32770`, ex.: "Referências não solucionadas"): os botões têm hwnd próprio e `PostMessage(BM_CLICK)` funciona mesmo com o Revit em segundo plano.
- **O Windows bloqueia `SetForegroundWindow`** para processos em segundo plano: o clique por posição pode cair em outra janela. Prefira BM_CLICK ou peça o clique ao usuário.
- **Revit ocupado:** até a UIAutomation dá timeout. Espere `Process.Responding` e tente de novo.
- **Não deixe watcher de diálogos rodando em segundo plano:** consome memória e foi morto no ETIB. Só reinicie se o usuário pedir.

## Suplemento com MessageBox em loop

Ex.: DarivaBIM sem login ("Nenhum token fornecido"; achado procurando o texto nas DLLs em `C:\ProgramData\Autodesk\Revit\Addins\2025`).
- A caixa não aceita PostMessage, só clique real, e reabre na hora.
- **Para salvar o trabalho:** deixe um comando do MCP na fila (`PostCommand(Save)`), clique OK uma vez; o Revit salva antes de a caixa voltar.
- **Para resolver:** com autorização do usuário, feche o Revit, renomeie o `.addin` para `.addin.off` e reabra. Registre no `licoes-modelagem.md` como reativar.

## Reabrir o Revit por script

- `Start-Process "C:\Program Files\Autodesk\Revit 2025\Revit.exe" '"arquivo.rvt"'`.
- Espere o título da janela conter o nome do arquivo (~3,5 min com 18 vínculos).
- "Referências não solucionadas" (vínculos aninhados ausentes) → "Ignorar e continuar" (aceita BM_CLICK pelo hwnd).
- **O serviço do MCP não liga sozinho:** Complementos › "Revit MCP Switch". Peça ao usuário, porque o Windows bloqueia trazer o Revit para a frente.
