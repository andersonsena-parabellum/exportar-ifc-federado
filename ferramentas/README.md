# Ferramentas

Cópia do código da pasta `FERRAMENTAS` do projeto (o mesmo que roda no notebook e na nuvem), para que um agente execute o método. Os dados das escolas não estão aqui.

| Pasta | O quê |
|---|---|
| `etib/preclash/` | motor de modelagem e pré-compatibilização sem Revit (`rodar.py`), adaptadores das escolas (`escolas/`), revisão das pranchas e carimbos (`executivo/`) |
| `etib/revisao/` | revisão de qualidade (`revisar.py`), `limpar_entrega.py`, `CHECKLIST.md` |
| `etib/pendencias/` | gerador da página de pendências |
| `etib/pranchas_cde/` | CDE das pranchas (IDs do Drive trocados por `<ID_DRIVE>`: preencher com os da sua pasta) |
| `etib/entrada/` | entrada da escola (DWG com AUDIT, leitura dos RVT pelo Revit) |
| `etib/<escola>/` | scripts de cada escola entregue: exemplos prontos para copiar |
| `etib/_nuvem/` | `etib-python`: roda os scripts do Windows no Linux, traduzindo os caminhos |
| `etib/*.ps1`, `revit_rpc.py` | Revit e diálogos do Windows (só no notebook) |
| `ambiente/` | `requirements.txt` com versões fixas e `preparar_nuvem.sh` |
| `pranchas_pdf/` | render do PDF A0 na nuvem e PDF híbrido (carimbo novo sobre PDF do AutoCAD) |

Não estão no repositório (licença de terceiros): o instalador do ODA File Converter (`ferramentas/*.deb`) e as fontes das pranchas (`pranchas_pdf/fontes/`). Também ficaram de fora as listagens do Drive da construtora e o `pranchas.json` com os links do CDE.

Como rodar: `metodologia/13-execucao-passo-a-passo.md`.
