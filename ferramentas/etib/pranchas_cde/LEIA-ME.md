# CDE das pranchas

Pranchas vigentes das 7 escolas: um PDF por folha do escopo, com a situação de cada uma (Original, Em revisão, Modificada).

Onde ficam:
- `D:\Projeto Modelagem\PRANCHAS\<ESCOLA>\` + `PRANCHAS_INDICE.md` (cópia local).
- Google Drive, pasta `ETIB_PRANCHAS_CDE` (conta <conta do Drive do escritório>; `G:\Meu Drive\ETIB_PRANCHAS_CDE` neste computador). É daqui que saem os links.
- Visualizador "Pré-compatibilização ETIB" (<link privado da página>): botão **Pranchas** na barra, que lê o `pranchas.json` publicado junto. O botão e o painel estão no template `FERRAMENTAS\preclash\preclash\visualizador.html` (trecho marcado "aba Pranchas (CDE)").
- Biblioteca do projeto: os mesmos PDFs, soltos, + `PRANCHAS_INDICE.md`.

Scripts:
- `originais.py`: lista das folhas (escola, grupo, folha, revisão original, fonte, revisão modificada).
- `plotar.py` + `plot_todos.lsp`: plota em A0 (cópia em `work\`) as folhas que só existem em DWG. Um accoreconsole por vez.
- `cde.py`: monta `PRANCHAS\<ESCOLA>\` e o índice.
- `drive_ids.py`: IDs do Drive de cada PDF (lidos com o conector do Google Drive).
- `pranchas_json.py`: gera o `pranchas.json` do visualizador.

Quando uma folha revisada ficar pronta:
1. PDF novo em `PRANCHAS\<ESCOLA>\` e em `G:\Meu Drive\ETIB_PRANCHAS_CDE\<ESCOLA>\`; a original vai para `_SUPERADAS\` nas duas.
2. Pegar o ID do PDF novo no Drive e pôr em `MODIFICADAS` no `pranchas_json.py` (escola, grupo, código da folha → rev, id, arquivo).
3. Rodar `pranchas_json.py` e publicar só o `pranchas.json` no artifact do visualizador (`files: {"pranchas.json": ...}`, sem mexer no index.html nem em `dados/`).
4. Atualizar a linha no `PRANCHAS_INDICE.md` e subir PDF + índice para a biblioteca.
   Do notebook (SendUserFile) o envio de um arquivo que já existe na biblioteca cai com sufixo de data (`PRANCHAS_INDICE-AAAAMMDDTHHMMSS-xxxx.md`): uma thread com acesso à pasta da biblioteca põe o conteúdo no `PRANCHAS_INDICE.md` e apaga as cópias com sufixo, para ficar um índice só.
