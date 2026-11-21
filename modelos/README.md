# Modelos para uma escola nova

| Arquivo | Para quê | Onde vai |
|---|---|---|
| `ETIB-ESCOLA/INVENTARIO.md` | quadro de entrada e fontes da escola | `ETIB-<ESCOLA>/INVENTARIO.md` |
| `ETIB-ESCOLA/LEIA-ME_envio.txt` | LEIA-ME da pasta de envio | raiz da pasta de envio |
| `../ferramentas/etib/preclash/escolas/exemplo.py` | adaptador da escola para o motor | `preclash/escolas/<escola>.py` |
| `../ferramentas/etib/preclash/escolas/exemplo_terreno.py` | terreno da escola | `preclash/escolas/<escola>_terreno.py` |
| `../ferramentas/etib/revisao/entregas.py` (bloco `exemplo`) | o que a revisão confere | nova entrada em `ESCOLAS` |
| `../ferramentas/etib/entrada/revit_conv.py` (`ESC`) | RVT que a escola precisa ler | nova linha em `ESC` |
| `../ferramentas/etib/pranchas_cde/originais.py`, `drive_ids.py`, `pranchas_json.py`, `cde.py` | folhas da escola no CDE | novas linhas |
| `../federado-unico-etib/escolas/EXEMPLO.json` | configuração do federado único | pasta FEDERADO_UNICO da escola |

Todos os valores dos modelos são fictícios.
