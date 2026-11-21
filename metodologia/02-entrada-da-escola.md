# 02. Entrada da escola

Decisão de 22/10/2026 (PDCA do fluxo): 70 a 87 % do prazo das primeiras escolas foi espera (DWG que não abria, clique no Revit, decisões antigas sem resposta). Por isso toda escola passa por uma **entrada** antes de modelar, para que nada dependa do notebook ou de uma resposta no meio da modelagem.

## Os cinco passos

1. **DWG.** Abrir todos os DWG da escola na nuvem (ODA File Converter, com AUDIT) e listar os que não abrem. O dono salva de uma vez no AutoCAD com janela os que falharam.
2. **CTB e fontes.** Listar os estilos de plotagem (CTB) e as fontes que as pranchas pedem. Sem o CTB do projetista, plota-se com o padrão e a conferência olha só a geometria.
3. **RVT numa sessão só.** Ler no Revit do notebook, de uma vez, todos os RVT necessários (terreno da implantação, estrutura e, para o federado, a arquitetura exportada em IFC4). Assim nenhuma escola espera clique no notebook depois. Script: `FERRAMENTAS/entrada/revit_conv.py` (capítulo 11, etapa do Revit).
4. **Pedido único à construtora.** Tudo o que falta (memorial, as built, cotas executadas, pavimentação, levantamento) vai num pedido só.
5. **Página de entrada.** As decisões antigas da escola (de rodadas anteriores, de outras escolas que se aplicam) numa página respondida antes de modelar.

## Onde registrar

- Quadro "Entrada" no `INVENTARIO.md` da escola: o que veio do Drive, o que abre, o que falta, o que foi pedido e quando.
- Seção 0 do [checklist](referencias/CHECKLIST.md) (itens 01 a 04).
- **A modelagem só começa com a entrada fechada** ou com o que falta registrado no pedido.

## Pasta da escola

Toda escola nova copia o modelo `_MODELO-ESCOLA` e ganha sigla e origem na tabela de escolas:

```
ETIB-<ESCOLA>/
├── INVENTARIO.md          o que veio do Drive e o que falta (quadro "Entrada")
├── PROJETO_ORIGINAL/      cópia fiel do Drive, NÃO editar
├── REFERENCIAS_RVT/       IMP e estrutura as built (e os IFC convertidos)
├── CAD_GEORREFERENCIADO/  *_GEO.dwg + JSON da transformação + LEIA-ME
├── RELATORIOS/            rodadas, IFC, pranchas, LEIA-ME de entrega, envio
└── _BACKUPS/
```

O adaptador da escola (`FERRAMENTAS/preclash/escolas/<escola>.py`) é criado nesta hora: sigla, origem, EPSG, retângulo da obra e onde estão os dados.
