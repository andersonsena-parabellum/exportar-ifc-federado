# Ferramentas

Código genérico do método (o mesmo motor que roda no notebook e na nuvem), para que um agente execute o fluxo numa escola nova. Não há dados de nenhuma escola aqui: cada escola começa pelos modelos de `modelos/` e pelo guia `metodologia/14-escola-nova.md`.

| Pasta | O quê |
|---|---|
| `etib/preclash/` | motor de modelagem e pré-compatibilização sem Revit (`rodar.py`), adaptador de exemplo (`escolas/exemplo.py`, `exemplo_terreno.py`: copiar e preencher para cada escola nova), revisão das pranchas e carimbos (`executivo/`) |
| `etib/revisao/` | revisão de qualidade (`revisar.py`), `limpar_entrega.py`, `CHECKLIST.md` |
| `etib/pendencias/` | gerador da página de pendências |
| `etib/pranchas_cde/` | CDE das pranchas (IDs do Drive trocados por `<ID_DRIVE>`: preencher com os da sua pasta) |
| `etib/entrada/` | entrada da escola (DWG com AUDIT, leitura dos RVT pelo Revit) |
| `etib/georef/` | georreferenciamento e plotagem das redes sobre o DWG (`comum.py` lê os caminhos das variáveis `ETIB_DXF_GEO`, `ETIB_RELATORIOS`, `ETIB_WORK_REDE`, `ETIB_PREFIXO`) |
| `etib/_nuvem/` | `etib-python`: roda os scripts do Windows no Linux, traduzindo os caminhos |
| `etib/*.ps1`, `revit_rpc.py` | Revit e diálogos do Windows (só no notebook) |
| `ambiente/` | `requirements.txt` com versões fixas e `preparar_nuvem.sh` |
| `pranchas_pdf/` | render do PDF A0 na nuvem e PDF híbrido (carimbo novo sobre PDF do AutoCAD) |

Não estão no repositório (licença de terceiros): o instalador do ODA File Converter (`ferramentas/*.deb`) e as fontes das pranchas (`pranchas_pdf/fontes/`). Também ficaram de fora os logos do carimbo (colocar em `pranchas_pdf/prancha/logos/` com os nomes `CARIMBO_QG_logo_*.png`), as listagens do Drive e o `pranchas.json` com os links do CDE.

Variável `ETIB_NOMES_EQUIPE`: nomes da equipe separados por vírgula. A revisão (`revisar.py`, `ifc_conf.py`) e o `export_ifc.py` recusam qualquer entrega que contenha um desses nomes (o IFC e as pranchas saem sem nome de pessoa).

Como rodar: `metodologia/13-execucao-passo-a-passo.md`.
