# Organização dos arquivos da construtora (Drive → pastas das escolas)

Feito em 18/10/2026. Serve para refazer quando a construtora publicar revisões novas.

## Fontes (SOMENTE LEITURA — não mover, apagar, renomear nem editar nada lá)
- `CT 049-2024` — <link privado da pasta no Drive>
  Uma pasta por escola (`ALAGOINHAS`, `APORÁ - PROF. ÁUREA`, `APORÁ ITAMIRA`, `CATU`, `JANDAÍRA`, `POJUCA`, `SÁTIRO DIAS`; `OLINDINA` fora da proposta).
  Dentro: `4 - IMPLANTAÇÃO\<n> - <disciplina>\`, `AVCB\02. MEMORIAL(IS)\` (memoriais de incêndio da implantação), `1 - LISTA MESTRA\`, blocos.
  `2 - AS BUILT CT 049.24\` = IFCs (não baixados).
- `CT049_2024` — <link privado da pasta no Drive>
  Pastas `004-25-…-QG as built <escola>\<bloco>\{Arquitetura,Estrutura,Fundação,Metálica}\` com os RVTs as built e o IMP.

## Regra de seleção (sel.py)
Implantação: `00_BASE` (pastas IMPLANTAÇÃO/SIT, TOPOGRÁFICO, TERRAPLANAGEM, PAVIMENTAÇÃO), `01_AF`, `02_ESG`, `03_DRE`, `04_ELE`, `05_PCI`
(+ `06_CLI` no BA2). Só a última revisão de cada documento (DWG e PDF separados); fora OBSOLETO(S), ETE, imagens/ctb.
RVTs: IMP + FUN/ECC de cada bloco (+ EMT do QDC); sem arquitetura, sem IFC, sem metálica grande (TRT 348 MB).

## Passo a passo
1. **Listar o Drive** (Chrome/Edge do usuário, aba do drive.google.com, `javascript_tool`): `crawler.js` busca cada pasta
   por `fetch('/drive/folders/<id>')`, lê `_DRIVE_ivd` (índices: 0 id, 2 nome, 3 mime, 10 data ms, 13 bytes) e salva
   `drive_listing_<ESCOLA>.json` em ~/Downloads (download de blob, sem diálogo). Pastas vazias dão `noivd`.
   A saída do `javascript_tool` corta em ~1000 caracteres: por isso o JSON vai para arquivo.
2. `python -I sel.py <listagem> "<ESCOLA>/4 - IMPLANTAÇÃO/" IMP sel/<ESCOLA>_IMP.json` → `python -I manifest.py`.
3. **Baixar**:
   - DWG/RVT/XLSX/DOCX: link direto `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t&authuser=0`
     por âncora `target=_blank` num laço síncrono (sem `setTimeout`: o Edge congela abas em segundo plano).
     Arquivo > 100 MB abre a página "aviso de verificação de vírus": clicar "Fazer o download mesmo assim".
   - **PDF NÃO por link direto**: o Edge do usuário abre cada PDF baixado no Acrobat (e o arquivo fica preso).
     PDFs vêm em zip: selecionar a pasta/arquivos no Drive (clique na linha, Ctrl+A) e o ícone de download da barra
     (~x=537,y=123 na tela de 1568 px). Esperar "Preparando o download" sumir antes de navegar. Fazer na aba ATIVA.
4. `python -I mover.py <ESCOLA> 300 [--direto|--naopdf]` (move de ~/Downloads conferindo bytes) e
   `python -I unzip_sel.py <ESCOLA> <zips>` (extrai só o que está no manifesto, por nome+tamanho).
5. `python -I gen_inv.py <ESCOLA>` → `<escola>\INVENTARIO.md` (observações manuais em `notas.json`).

## Achados
- Os RVTs de bloco padrão (GUA, CDG, CDR, VST…) são idênticos entre escolas (mesmo hash): quem posiciona é o vínculo no IMP.
- Lista mestra (aba IMP) só registra o SIT; não serve para saber quais complementares existem.
- O Drive para desktop (G:) não mostra essas pastas (não há atalho em "Meu Drive"); o conector do Drive só devolve 1 item por pasta.

## Acréscimo 18/10/2026 — fora da "4 - IMPLANTAÇÃO"
`extras_sel.py` acrescenta ao `manifest.json` (lote `extras-2026-10-18`) o campo society (DRE/ELE/PCI) de Pojuca, Sátiro Dias
e Jandaíra e a pasta `10 - QUADRA (30X18)/6 - IMPLANTAÇÃO` de Pojuca. Projetos de edificação ficam de fora (critério no topo
do script). `inv_extras.py <ESCOLA>` acrescenta a seção no fim do `INVENTARIO.md` sem regenerar o resto (as threads das
escolas também editam esse arquivo). Download: zip da pasta pelo Drive, na aba ativa, com o Edge visível (janela coberta
por outro programa congela a página: screenshot e cliques dão timeout).
