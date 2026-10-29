# Exportar os RVT da construtora em IFC (Revit, na máquina com Revit)

Os RVT ficam no Drive da construtora (pasta "QG as built" > escola), **somente leitura**: copie para a sua máquina antes de abrir.
Confira o código da escola no nome do arquivo (na pasta da Jandaíra havia IFC soltos da Pojuca).

## Implantação (IMP)
1. Abrir o RVT da implantação. Deixar a topografia visível na vista 3D exportada (o p0 compara o terreno dele com o as built).
2. Exportar IFC: versão **IFC4**, coordenadas **compartilhadas** (o arquivo sai em UTM absoluto), sem exportar vínculos.
3. Anotar os vínculos (Gerenciar vínculos): o que estiver descarregado ou ausente (ETE, outros IFC) não entra e vai em `leia_me.nao_entra`.
4. Rodar `p0_cota_rvt.py` para achar o `dz` (o RVT pode estar na cota de projeto, não na do as built).

## Módulos (BP4, GUA...)
Dois caminhos; use o que der menos trabalho e confira com o p6 (arquitetura × estrutura) e as prévias:
- **A. Exportar o módulo sozinho** (coordenadas próprias do RVT do módulo) e posicionar com `posicao: {giro_graus, e, n, dz}`: no RVT da implantação, o vínculo do módulo diz onde ele fica. `e`/`n` = posição em UTM da origem interna do módulo; `giro_graus` = rotação do vínculo; `dz` = cota absoluta do zero do módulo (piso as built − cota do piso no RVT). Na Jandaíra: BP4 giro −58,9075°, E 631529,527, N 8721120,793, dz 147,465 (térreo +0,10 no piso as built 147,565).
- **B. Exportar pela implantação com os vínculos carregados**, opção de exportar vínculos como IFC separados, coordenadas compartilhadas: cada módulo já sai em UTM; use `posicao: {"dz": ...}` (só o ajuste de cota, se houver).

Exportar em IFC4. Não precisa limpar nada no Revit: o p1 tira tubulação, portas de conexão, fundação e os grupos de modelo; louças, metais e mobiliário ficam (são da arquitetura).

## Sem RVT
Use o IFC padrão ETIB do módulo (biblioteca de padrões) e ache giro e translação encaixando as paredes do padrão nas linhas da planta de implantação, ou centrando nos pilares as built (`posicao: {giro_graus, x, y, dz}` em coordenadas do projeto). Citar a orientação adotada no LEIA-ME.
