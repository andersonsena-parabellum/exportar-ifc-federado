# Página de pendências — gerador único

Página que vai ao dono do projeto (e ao sócio de modelagem) com as colisões e decisões de uma escola, no padrão das páginas de escola B e escola C.
Regra em `AGENTS.md` > Forma de trabalho; conferência na seção F do `FERRAMENTAS\revisao\CHECKLIST.md`.

```
..\.venv\Scripts\python.exe -X utf8 pagina.py <config.json> [--sem-recortes] [--sem-vistas]
```

Grava em `saida`: `index.html` (a página, com todas as imagens embutidas em base64), `img\` (as mesmas imagens em tamanho cheio, para
conferir) e `CONFERENCIA_F.md` (F1 abre no celular, F2 dois blocos, F3 conteúdo de cada ficha). Só publicar com a conferência
**APROVADA**. Modelos de `config.json` e `fichas.json` abaixo (valores fictícios).

## O que a página tem

- Dois blocos: **Precisa de decisão** (o que passa dos limites do "aplicar e avisar" ou depende de alguém) e **Aplicado (pode reverter)**.
- Em cada ficha: recorte da prancha do projetista de cada folha citada, centrado no ponto (círculo vermelho) e com os **códigos citados
  escritos em azul** ao lado dos elementos (a prancha original não traz DRN-164, CX03…); vistas **3D** e **em planta** do IFC de entrega;
  textos; encaminhamento (botões), texto livre e **imagem anexada** (print em planta da solução sugerida).
- Decisão: "Aceito a proposta / Levar ao projetista / Aceitar como está / Outra solução". Aplicado: "Manter / Reverter / Outra solução".

## Publicar e ler as respostas

- Publicar o `index.html` com o Artifact e `capabilities: {db: {}, user: {}, assets: {}}`. Republicar a mesma escola no mesmo link.
- As respostas ficam na coleção `decisoes`, um documento por ficha (`d01`, `d02`… = número da ficha):
  `decisao`, `nota`, `imagem` (id do asset; a imagem abre em `/_blob/<id>`), `em`, `por`. Ler com `ArtifactData` (`list` da coleção).
- Só quem edita o artifact anexa imagem (capability `assets`); quem só vê lê as decisões sem anotar.

## config.json

Caminhos relativos valem a partir da pasta do config.

```json
{
 "escola": "ETIB escola E", "sigla": "EXE", "data": "23/10/2026",
 "fichas": "fichas.json",
 "saida": "D:\\Projeto Modelagem\\ETIB-<ESCOLA>\\RELATORIOS\\PENDENCIAS_2026-10-23",
 "ifc": "D:\\Projeto Modelagem\\ETIB-<ESCOLA>\\RELATORIOS\\ENTREGA_IFC\\*.ifc",
 "terreno": "D:\\Projeto Modelagem\\FERRAMENTAS\\preclash\\escolas\\dados\\exemplo_terreno.npz",
 "transf_json": "D:\\Projeto Modelagem\\ETIB-<ESCOLA>\\CAD_GEORREFERENCIADO\\transformacoes_local_para_UTM.json",
 "folhas": {
   "EL-001": {"dxf": "...\\_copias\\<folha>.dxf", "pdf": "...\\PDF\\<folha>-R01.pdf", "chave": "PROJETO_ORIGINAL/.../<folha>.dwg"},
   "DRE-001": {"dxf": "...\\<folha>_GEO.dxf", "pdf": "...\\PRANCHAS\\...\\<folha>.pdf", "chave": null}
 }
}
```

- `folhas`: o DXF da folha (a cópia que o `rever.py` grava em `_copias\`, ou o `_GEO.dxf`), o PDF que o projetista vai ver (a revisão
  nova, se a folha foi revisada) e a `chave` da transformação no JSON do georreferenciamento (`null` = DXF já em UTM). DXF → PDF é
  calibrado por textos iguais e únicos nos dois (o log mostra os pares usados e o resíduo; resíduo acima de ~3 pt = conferir).
- Opcionais: `titulo`, `h1`, `subtitulo`, `selo` (lista de linhas do carimbo da página).
- `ifc`: glob dos IFC de entrega por disciplina (o federado é ignorado). Sem `ifc` não há vistas do modelo nem posição dos códigos.

## fichas.json

```json
[{"n": 1, "bloco": "decisao", "quem": "projetista de drenagem",
  "titulo": "DRN-164 encosta na sapata S12 do BP4",
  "o": "o que é", "t": "o que já foi feito ou testado", "p": "proposta",
  "E": 500412.3, "N": 8700321.8, "z": 182.4, "raio": 10, "raio3d": 4.5,
  "folhas": ["DRE-001"], "codigos": ["DRN-164", "CX03", {"codigo": "S12", "E": 500413.0, "N": 8700322.5}]},
 {"n": 2, "bloco": "aplicado",
  "titulo": "CX-07 deslocada 0,45 m", "o": "o que era", "t": "o que foi aplicado", "reverter": "como voltar atrás",
  "E": 500420.0, "N": 8700300.0, "folhas": ["EL-001"], "codigos": ["CX-07", "ELE-06"]}]
```

- `bloco`: `decisao` ou `aplicado` (o formato antigo, `grupo` D/G e `a`/`b`, também é aceito).
- `codigos`: nomes dos elementos como estão no IFC (trecho, caixa); a posição usada é o ponto do elemento mais perto do ponto da ficha.
  Elemento que não está no modelo (estrutura, galeria fora do escopo) vai com `{"codigo", "E", "N"}`; código não achado é pendência F3.
- `raio`: metade da altura da planta e, acima de 12 m, o recorte da prancha cresce junto; `raio3d`: meia largura da vista 3D; `z`: cota do ponto.
- Ficha aplicada precisa de `reverter` (ou `p`), senão é pendência F2.

## Peças

- `recortes.py`: calibração DXF → PDF e recorte com o círculo e os códigos (generalizado de `exemplo\pendencias\sat_recortes.py`).
- `vistas.py`: planta e 3D do IFC de entrega (generalizado de `exemplo\pendencias\sat_vistas.py`; lê pelo `revisao\ifc_conf.py`).
- `modelo.html`: a página (dados e imagens entram no lugar de `__DADOS__` e `__IMAGENS__`).
