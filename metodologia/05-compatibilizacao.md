# 05. Compatibilização

## Princípios

1. **Mexer o mínimo; preferir mudar só a profundidade.** Mudar traçado em planta obriga novo as built.
2. **NUNCA mover vértice em planta para encaixar ângulo comercial.**
3. **Divergência projeto × as built: vale o as built** (decisão de 23/10/2026), que é sempre mais recente. A rede executada entra no modelo e a prancha é redesenhada por ela em revisão nova, sem perguntar; o que o projeto tinha e não foi executado sai da folha. A mudança vai como ficha "Aplicado (pode reverter)".
4. **Terreno: vale a base** (CT das caixas, implantação, TOP, TER), capítulo 03.
5. Quem se move primeiro: ELE e PCI, depois AF. ESG, pluvial e drenagem são fixas (só a caixa anda, dentro dos limites).

## Parâmetros

| Parâmetro | Valor |
|---|---|
| Profundidade máxima, do terreno ao topo do tubo, todas as disciplinas | **2,00 m** (outro valor só se combinado com o dono para a escola, em `PROF_MAX_ESCOLA`) — `preclash/parametros.py` |
| Recobrimento mínimo de referência | 0,30 m; 0,60 m na elétrica e sob área de veículos (vale a nota do projeto) |
| Colisão crítica | interferência física (< −2 mm) |
| Atenção | folga abaixo de 0,20 m |
| Elétrica × água | elétrica **sempre acima** da água, em todo cruzamento |
| Mudança de cota de pressurizada | só dentro das caixas; nada de degrau em "Z" nem mergulho pontual |
| Água fria e hidrante | uma cota por rede |
| Elétrica, SDAI | uma cota por trecho entre caixas |

## Estudo de cota das pressurizadas

Antes do clash de soluções, cada rede pressurizada ganha a cota de implantação com menos colisões (`preclash/estudo.py`, `REGRAS['estudo']`). O perfil segue o terreno, com o topo até a profundidade máxima. Lições da escola A (133 → 23 colisões):

- água rasa impede a elétrica por cima: com a elétrica a 0,60 m, a água precisa de topo a pelo menos 0,90 m (0,60 + diâmetro + 0,20 de folga); dar mínimo por rede;
- o fundo da caixa de passagem desce até o eletroduto mais fundo que chega nela, e o custo do estudo conta o que essa caixa passa a pegar;
- elétrica numa rede só (BT, iluminação e campo dividem caixas), com caixa e poste na rede dos trechos que chegam nela;
- recobrimento único por rede gera cruzamentos na mesma cota entre redes da mesma disciplina: prever regra de cruzamento (o menor passa por baixo, com folga).

Barrilete e casa de bombas ficam fora do estudo, na cota do modelo.

## Clash

- Rede × rede, rede × caixa, caixa × caixa (de disciplinas diferentes) e rede × estrutura.
- **Contra a estrutura pela forma real** (decisão de 20/10/2026): a caixa envolvente de uma sapata cônica acusa colisão que não existe (na escola A R03, 3 de 6 críticos passavam livres). A malha real da estrutura as built entra no clash (corte em 5 alturas da seção do tubo, a cada 2 cm do eixo) e vai para o IFC como `IfcTriangulatedFaceSet`.
- Duas redes por gravidade que se encontram na ponta de um trecho são ligação, não conflito, só entre a mesma disciplina ou grupos combinados (ex.: pluvial e drenagem; condensado no pluvial).
- Reservatório inferior sempre modelado.

## Ordem das soluções

1. **Profundidade:** a rede móvel faz um mergulho local na janela do conflito, com conexões verticais nas pontas; a planta não muda. Repete clash → solução até não sobrar nada resolvível.
2. **Caixa deslocada:** gravidade × gravidade e choque com a estrutura deslocam um pouco a caixa de uma das redes, mantendo a CF; os tubos acompanham.
3. **Desvio em planta:** só para o que a profundidade não resolve (pressurizada atravessando PV/CI/CA), com transições a 45° e cota refeita pelo recobrimento.
4. **Pendente:** o que passa dos limites vai para decisão.

## Aplicar e avisar

Decisão de 22/10/2026. Dentro destes limites a solução é **aplicada sem perguntar** e a ficha mostra "aplicado, pode reverter":

| Situação | Limite |
|---|---|
| Caixa de gravidade deslocada | até 0,60 m em planta |
| Geratriz de chegada ajustada | até 0,20 m, mantendo a declividade mínima |
| Pressurizada sem cota livre | desvio lateral até 2,00 m, curvas de 45° |
| CT/CF incoerente com a profundidade | corrigida na prancha, com nova revisão |
| Poste, torneira, caixa de passagem | deslocados até 1,50 m junto com o ramal |

Gravidade × gravidade dentro desses limites é resolvido pela equipe, sem ir ao projetista.

**Continua pergunta:** estrutura executada, falta de projeto, mudança de escopo e tudo o que passar desses limites.

## Página de pendências

Colisões que dependem de decisão vão numa página (gerador único `FERRAMENTAS/pendencias/pagina.py`), com dois blocos:

- **Precisa de decisão:** o que passa dos limites ou depende de alguém. Botões: aceito a proposta / levar ao projetista / aceitar como está / outra solução.
- **Aplicado (pode reverter):** o que entrou pelo aplicar e avisar, com o "como reverter". Botões: manter / reverter / outra solução.

Cada ficha tem:
- recorte da prancha do projetista centrado no ponto, com círculo, e os **códigos citados escritos** ao lado dos elementos (a prancha original não traz DRN-164, CX03…);
- vistas 3D e em planta do IFC de entrega;
- o que é, o que já foi testado, a proposta;
- campo de decisão, de texto e de imagem (print da solução sugerida).

Imagens embutidas em base64, senão não abrem no celular. A página só é publicada com a conferência `CONFERENCIA_F.md` aprovada (seção F do checklist). As respostas ficam no banco da página (coleção `decisoes`, um documento por ficha) e voltam para o adaptador da escola.

## O que nunca vai em documento entregue

- Desvios de conexão fora de 45°/90° (só registro interno).
- Cota da água fria como item de relatório (é premissa).
- Disciplina fora do escopo.
- Nome de ferramenta, pessoa ou processo interno.
