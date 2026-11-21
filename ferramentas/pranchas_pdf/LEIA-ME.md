# PDF de prancha na nuvem (ezdxf), versão de 26/10 (Olindina + Sátiro); adotado nas entregas em 26/10, conferindo a 1ª escola lado a lado com o AutoCAD

Rodar de dentro desta pasta (o script procura `fontes/` e `prancha/logos/` a partir dela):

    bash ../ambiente/preparar_nuvem.sh      # venv com as versões fixas, ODA, LibreOffice e fontes
    apt-get install -y ./ODAFileConverter_QT6_lnxX64_11dll.deb libopengl0 libegl1 xvfb   # se precisar ler DWG
    xvfb-run -a ODAFileConverter <pasta_dwg> <pasta_dxf> ACAD2018 DXF 0 1 "*.DWG"
    CTB=prancha/acad.ctb LAY=<layout> python -I render_pdf_nuvem.py <prancha.dxf> <saida.pdf>

LAY é o nome da folha (padrão "01"); se não existir, usa a única folha do arquivo (ex.: "Layout1" das elétricas). São cerca de 50 s por prancha A0.
O CTB do projetista ("FAC - HID.ctb", "FAC - ELE 03_.ctb") não existe nem no notebook; os dois lados plotam com as cores do objeto.

O que o script corrige em relação ao ezdxf puro (tudo medido contra o PDF do AutoCAD):
- fonte Arial real; logos do carimbo QG; imagem sem moldura;
- entrelinha `\pxsm`; recuo, tabulação e justificado das listas mantidos;
- marcador de lista da fonte Symbol vira •; `%%216` e ∅ viram Ø;
- quebra de linha do MTEXT com a folga do AutoCAD (8 %, só em rótulo curto de até 30 caracteres; nota longa fica sem folga);
- fontes reais do AutoCAD/Windows em `fontes/`: Arial, Swiss 721 (swiss*.ttf), romans/simplex/isocp IV25 (copiadas do notebook em 26/10);
- ponto (_DotSmall) na ponta do MLEADER com o tamanho que o AutoCAD plota (cerca de metade do ezdxf);
- tabela do Excel colada como OLE (OLE2FRAME): a imagem guardada no OLE é convertida pelo LibreOffice e colada no quadro, opaca;
- máscara (WIPEOUT) no fundo do bloco e com borda quando WIPEOUTFRAME = 1;
- camada "não plotar" (Defpoints) e bloco inserido nela somem;
- tracejado na viewport conforme o PSLTSCALE da folha;
- cinza 252 = #989898;
- gravação do PDF em lotes (de 5 min para cerca de 35 s).

Diferença que sobra: a posição em que o tracejado começa (fase) e a espessura de algumas linhas.
