# 03. Georreferenciamento e extração da rede

O método atual monta as redes **sem Revit**, em três fases, a partir dos DWG e PDF do projetista. Cada fase grava arquivos que a seguinte lê, e tudo é refeito por script quando uma fonte muda.

| Fase | Entrada | Saída |
|---|---|---|
| 1. Referenciamento | DWG de cada disciplina em coordenada local | cópias `_GEO` em UTM + JSON da transformação |
| 2. Extração em planta | DWG georreferenciado (+ PDF para textos) | CSV de trechos, caixas e nós de cada rede |
| 3. Cotas | CSV da fase 2 + terreno | eixo 3D de cada trecho (gravidade pelas cotas do projeto, pressurizada pelo recobrimento) |

## Fase 1. CAD local para UTM

1. **Diagnóstico antes de qualquer coisa.** Ler de cada DWG, numa cópia: INSUNITS, EXTMIN/EXTMAX, lista de layers e se está em UTM ou em coordenada local. Projetos feitos em QiBuilder costumam vir em coordenada local.
2. **Transformação rígida** (rotação + translação, sem escala): primeiro rotacionar em torno de (0,0), depois transladar. Gravar os valores com todas as casas decimais em `CAD_GEORREFERENCIADO/transformacoes_local_para_UTM.json`.
3. **Como achar a transformação:** casamento de pontos (ICP) entre um bloco de arquitetura embutido no projeto da disciplina e a mesma arquitetura na planta de implantação georreferenciada. O resíduo esperado é de milímetros. Leitura de coordenada impressa ou "ponte" pelo PDF errou 2,3 m e não se usa.
4. **Cada DWG tem a sua transformação.** Não presumir que todas as disciplinas, nem todas as pranchas do mesmo escritório, usam o mesmo sistema local: um incêndio estava 70 m deslocado, e uma prancha elétrica 0,46 m. Vale a transformação calculada pelos blocos de arquitetura de cada DWG.
5. **Desempate entre hipóteses:** contar os pontos da rede a menos de 0,30 m de uma parede da planta de situação para cada hipótese, e repetir numa prancha de controle com deslocamento falso.
6. Trabalhar sempre em **cópia**, com sufixo (`_GEO`, `_REF`). Na planta de situação (`_REF`): apagar entidades perdidas longe da obra, tirar blocos pesados (curvas de nível em bloco) e explodir blocos com transformações enormes.
7. Se alguém diz que "não está alinhado", parar e corrigir antes de seguir: perguntar qual arquivo está certo e alinhar o outro a ele.

## Fase 2. Extração em planta

- **A rede sai do CAD por script, nunca "na mão":** ler linhas e textos (Ø, CT, CF, i %) dos layers da rede, montar o grafo (nós = caixas e conexões, arestas = trechos) e gravar CSV de trechos e de nós para conferência.
- **Nomes do projeto:** trecho `AF-07.3`, `ESG-36`, caixas `CI-xx`, `CG-xx`, `PVE-xx`, circuitos da elétrica. Esses códigos vão para o IFC e para a página de pendências.
- **Caixa desenhada como polilinha "aberta" com o último vértice igual ao primeiro** é tratada como fechada, senão o detector não a vê.
- **Eletrodutos em banco** (cada linha do DWG = um eletroduto): cortar cada eletroduto nas caixas e dar a cada pedaço o rótulo mais próximo; pedaço sem rótulo herda do vizinho, um para um, marcado "continuidade presumida". Não encadear o eletroduto inteiro através das caixas (já trocou diâmetros entre tubos vizinhos).
- **Eletroduto sem rótulo:** vale o Ø da nota geral do projeto ("eletrodutos não cotados serão de Ø3/4"") como premissa, não como erro.
- **Corte na face das edificações:** contorno do bloco pela estrutura (pilares + baldrames até 1,0 m acima do mais baixo, paredes e lajes de fundação, fecho com 1,0 m e buracos preenchidos); bloco de dois pavimentos com pátio usa o laço externo da laje do 1º pavimento; nunca a laje de cobertura (o beiral passa da face). Só corta o eletroduto que passa 0,50 m além da face ou termina dentro do bloco; caixa com o centro dentro do bloco é interna e não é modelada.
- **Eletroduto termina na face da caixa**, não no centro: ponta dentro da caixa é cortada na face; ponta antes da caixa e alinhada é prolongada; banco mais largo que a caixa converge no último metro; ponta solta a menos de 1 m de caixa da mesma rede é ligada a ela.

### O PDF como fonte

O PDF vetorial tem todos os textos com posição (PyMuPDF, `page.get_text('dict')`). Serve quando o DWG não abre ou quando o dado está numa chamada (MULTILEADER), que o dump do console não traz.

- Calibrar PDF para modelo por similaridade com duas âncoras reconhecíveis nos dois (centro de símbolos de equipamento), com o eixo y do PDF invertido antes do ajuste. Conferir pela escala (1:200 = 0,0706 m/pt).
- Número com linha de chamada: atribuir cada número ao trecho mais próximo dele (não o contrário).
- Diâmetro e material: contar os rótulos e cruzar com o quadro de equivalência de bitolas da folha.
- Âncoras que não servem: pontas de linha tracejada e caixas desenhadas ao lado do eletroduto.

## Fase 3. Cotas

- **Níveis e cotas sempre absolutos.** Um nível por platô.
- **Gravidade (ESG, pluvial, DRE): usa as cotas do projeto** (CT da tampa, CF do fundo, CE/CS de entrada e saída). A declividade sai das cotas. Tubo que chega acima do fundo da caixa de jusante leva tubo de queda. Sem cota: declividade do rótulo, depois propagação pelo nó, e por último terreno − 0,60 m, sempre marcado "cota estimada".
- **Pressurizadas (AF, hidrante, ELE, SDAI): seguem o terreno com recobrimento.** O topo fica a "superfície − recobrimento" e o eixo meio diâmetro abaixo. O perfil é amostrado ao longo da rede e simplificado (nó a cada 4 m, Douglas-Peucker de 5 cm); os trechos retos incluem os vértices da planta com z interpolado, senão cortam as curvas. A cota final de cada rede sai do estudo de cota (capítulo 05).
- **Recobrimento:** vale a nota de cada projeto. Referência: 0,30 m sob passeio e grama, 0,60 m sob área de veículos e na elétrica. Área de veículos = polígono desenhado uma vez e reaproveitado entre disciplinas.
- **Cota da água fria é premissa de modelagem**, nunca item de relatório.

## Terreno

- **Vale a base:** CT das caixas de DRE/ESG, implantação, TOP e TER. Usa-se o terreno do RVT da implantação convertido em IFC, ajustado às cotas da base quando diverge (`preclash/terreno.py: ajustar`, correção local pelos resíduos, platôs pela mediana).
- O terreno vira um TIN (`preclash/escolas/dados/<escola>_terreno.npz`: pontos, triângulos, platôs e linhas da situação). Sem triângulos, faz-se Delaunay dos pontos.
- Rebaixo estreito de piso (pátio rebaixado) pode ser preenchido só para o perfil das pressurizadas (`preencher_rebaixo`), senão a rede inteira desce. Conferir depois contra o terreno entregue: a rede não pode ficar acima do terreno real.
