# Estudo de caso: ETIB Alagoinhas-BA (out/2026)

Referência de ordem de grandeza e de erros reais. Os dados vivos do projeto (caminhos, IDs, pendências) ficam em `D:\Projeto Modelagem\licoes-modelagem.md`, Parte B: leia lá, não aqui, quando trabalhar nesse projeto.

## Configuração

- Revit 2025.2; templates DARIVABIM (HS) e G.Alves V.15 (INC). Federação no Navisworks 2024.
- Origem interna = UTM SIRGAS 2000 24S E 561500 / N 8658000 / cota 0, sem rotação.
- Platôs +135,50 / +136,10 / +137,40 / +138,50.
- Arquivos: `Modelagem - HidroSanitário.rvt` (AF + ESG) e `MODELAGEM-INCENDIO.rvt` (hidrantes + SDAI), base "as built" IMP + 16 RVTs de blocos (fundações) como vínculos.
- CADs QiBuilder em coordenadas locais: AF/ESG num sistema; incêndio em outro, deslocado (65,31 ; 27,43) m.

## Resultado (ordem de grandeza)

| Disciplina | Quantidades |
|---|---|
| AF | 60 tubos, ~475 m, PVC DE 25–75 |
| ESG | 63 tubos, ~534 m, 42 caixas/PVs |
| Hidrantes | PEAD SDR11 DE75 298,9 m + DE85 8,0 m; 19 trechos, 7 tês, 9 tampões; casa de bombas esquemática |
| SDAI | eletroduto PEAD Ø2" 271,9 m em 29 trechos, 15 caixas |
| Relatório R00 (AF×ESG×EST) | 16 fichas: 8 críticas, 6 de atenção, 2 de informação |
| Verificação INC | 14 colisões com AF/ESG, 7 com estruturas |

Conclusão-chave do R00: a CT das caixas era a do projetista (cota de platô), mas o terreno executado diferia. A divergência virou incompatibilidade (projeto × obra), sem ajuste no modelo.

## Erros que aconteceram e como se resolveram

| Erro | Causa | Solução |
|---|---|---|
| MCP travado/timeout | Janela modal no Revit | Ler e fechar o diálogo por script (`revit_dialog.ps1`) |
| "Transação aninhada" | `new Transaction` no MCP | `SubTransaction` |
| SIT com lixo | Entidades distantes, bloco duplicado em layer travado, blocos deslocados | Limpeza em cópia: destravar, apagar, explodir |
| AF desalinhada ~2,3 m | Transformação pela "ponte" do PDF | ICP no bloco de arquitetura (2 mm) |
| Toposolid 135,5 m acima | Criado no nível da vista | Mover −135,5 m; criar com nível de cota 0 |
| Joelho/tê não conectavam | Limites da família | `ConnectTo` direto e tocos de 0,35 m |
| Corte vazio/deslocado | Z invertido no `CreateSection` | Min.Z = 0, corte 0,6 m à frente |
| Vínculo IMP recusado por coordenadas compartilhadas | API/diálogo | Transformação calculada `M = Th × Tl⁻¹` (1ª tentativa saiu invertida) |
| Erro de "Iterator" ao apagar | Coleção alterada na iteração | `.ToElements()` antes |
| Tampa da família 6 cm acima da CT | Ponto de inserção da família | Ajustar elevação e profundidade juntas |
| Prints 3D minúsculos | Crop box desligado | Ativar e ajustar à caixa de corte |
| MCP editou o arquivo errado | Usuário trocou a janela ativa | Conferir `document.Title` |
| Vínculo de 10 RVTs deu timeout | Lote grande | Lotes de ~6 |
| accoreconsole travado / ErrorStatus 53 | Objetos QiBuilder | Georreferenciar no Revit + textos do PDF |
| Movimento do CAD "não aplicado" | `GetTotalTransform` de ImportInstance | Ler `GeometryInstance.Transform` |
| Laço de comprimento zero na topologia | Elo de 0,37 m colapsado pelo snap de 0,6 m | Tirar do snap e recriar o elo como trecho |
| Trecho de 3" não detectado | Snap moveu a ponta de divisão | Imprimir os vértices reais e usar o vértice certo |
| Erro "direção oposta" nos tês | Tubo redirecionado com sentido invertido | Preservar o sentido da curva |
| Bombas e registro em z ≈ 0 | Família baseada em plano de trabalho | Mover em Z |
| Erro de conectividade no eletroduto | Condulete 90° em dobra suave | Desconectar e apagar as curvas órfãs |
| 3D grande demais na folha | Escala 1:600 | 1:1000 e conferir os contornos |
| Revit travado por "Nenhum token fornecido" | Suplemento sem login | Salvar via PostCommand; desativar o `.addin` com autorização |
| "Banheiro no meio do passeio" | Layer `ARQ_DEMOLIÇÃO` do SIT | Identificar o layer, avisar e ocultar nas vistas |
| "Outro caminho" cinza | Hachura do SIT sem correspondente no as built | Quantificar (454 m²) e decidir com o usuário |
