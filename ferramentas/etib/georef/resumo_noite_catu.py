# -*- coding: utf-8 -*-
"""Resumo da compatibilização da Catu (noite 18→19/10/2026) a partir das saídas do preclash e dos executivos revisados.
Grava ETIB-CATU/RELATORIOS/CAT_compatibilizacao_2026-10-19.md (o que ficou pronto + o que trava)."""
import os, csv, json, re, collections
PRE = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\PRECLASH_2026-10-18'
EXE = r'D:\Projeto Modelagem\ETIB-CATU\EXECUTIVO_REVISADO'
OUT = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS\CAT_compatibilizacao_2026-10-19.md'
CEN = 'BD'


def ler(fn):
    fn = os.path.join(PRE, fn)
    return list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter=';')) if os.path.exists(fn) else []


def conta(fn):
    R = ler(fn); c = collections.Counter(r['gravidade'] for r in R); return c.get('CRÍTICA', 0), c.get('ATENÇÃO', 0)


EQUIP = ('abrigo', 'poste', 'casa de bombas', 'registro', 'hidrante', 'recalque', 'QD', 'QGBT', 'central')


def conta_grupos(fn):
    R = ler(fn); g = collections.defaultdict(lambda: [0, 0])
    for r in R:
        k = 'estrutura' if 'EST' in (r['disc_A'], r['disc_B']) else 'equipamento' if any(x in r['descricao'] for x in EQUIP) else 'redes'
        g[k][0 if r['gravidade'] == 'CRÍTICA' else 1] += 1
    return g


def main():
    a0 = conta('CAT_preclash_A_conflitos_antes.csv'); a1 = conta('CAT_preclash_A_conflitos_depois.csv')
    b1 = conta(f'CAT_preclash_{CEN}_conflitos_depois.csv')
    g0, g1 = conta_grupos('CAT_preclash_A_conflitos_antes.csv'), conta_grupos(f'CAT_preclash_{CEN}_conflitos_depois.csv')
    sol = ler(f'CAT_preclash_{CEN}_solucoes.csv'); dv = [r for r in ler(f'CAT_preclash_{CEN}_desvios.csv') if r['status'] == 'aplicado']
    aj = [r for r in ler('CAT_preclash_B_ajustes_manuais.csv') if r['status'] == 'aplicado']
    pend = ler(f'CAT_preclash_{CEN}_pendentes.csv')
    pc = collections.Counter(r['categoria'] for r in pend)
    sd = collections.Counter(r['disciplina'] for r in sol)
    dd = collections.Counter(r['disciplina'] for r in dv) + collections.Counter(r['disciplina'] for r in aj)
    ex = json.load(open(r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\exec\exec_resumo_BD.json', encoding='utf-8')) if os.path.exists(r'D:\Projeto Modelagem\FERRAMENTAS\georef\work\CATU\exec\exec_resumo_BD.json') else []
    L = ['# ETIB Catu — compatibilização sem Revit (noite de 18 para 19/10/2026)', '',
         'Feito sem esperar decisão: em cada dúvida valeu a opção recomendada, registrada abaixo. Entrega = IFC por disciplina + federado IFC + executivos revisados (cópias dos DWG).', '',
         '## Resultado', '',
         '| | Críticos | Atenção |', '|---|---|---|',
         f'| Projeto (com equipamentos e fundações as built) | {a0[0]} | {a0[1]} |',
         f'| Só profundidade (cenário A) | {a1[0]} | {a1[1]} |',
         f'| Entrega (cenário {CEN}: caixas fora dos PV + desvios + profundidade) | {b1[0]} | {b1[1]} |', '',
         'Separado por tipo (críticos / atenção, projeto → entrega):', '',
         f"- Rede × rede: {g0['redes'][0]}/{g0['redes'][1]} → {g1['redes'][0]}/{g1['redes'][1]} (o que sobra é esgoto × drenagem, do projetista).",
         f"- Equipamento (hidrante, abrigo, poste, quadro, registro): {g0['equipamento'][0]}/{g0['equipamento'][1]} → {g1['equipamento'][0]}/{g1['equipamento'][1]}.",
         f"- Interface com fundação/estrutura as built: {g0['estrutura'][0]}/{g0['estrutura'][1]} → {g1['estrutura'][0]}/{g1['estrutura'][1]} "
         '(entradas de ramal, prumadas AP e caixas junto às sapatas/baldrames; a cota das fundações depende da decisão do terreno, ver abaixo).', '',
         f'- {len(sol)} mergulhos (só profundidade, nota na planta): ' + ', '.join(f'{k} {v}' for k, v in sd.most_common()) + '.',
         f'- {len(dv) + len(aj)} alterações em planta (executivo novo): ' + ', '.join(f'{k} {v}' for k, v in dd.most_common()) + '. ESG e drenagem não mudam.',
         f'- {len(pend)} pendentes: ' + '; '.join(f'{k} {v}' for k, v in pc.most_common()) + '.', '']
    L += ['## O que trava (decisão do Anderson ou de projetista)', '',
          '1. **Terreno:** o IMP as built (lido no Revit) bate em planta com a SIT, mas os platôs estão 1,6 a 5,1 m acima da SIT R02 e das CT do ESG/DRE '
          '(campo 83,35 × 78,25; restaurante 84,11 × 82,50; bloco principal 86,30 × 83,00/84,50). Mapa: `RELATORIOS\\CAT_IMP_terreno_x_SIT_x_CT.png`. '
          'Segui com o terreno do projeto (as redes por gravidade foram projetadas nele) e gravei o IMP à parte (`CAT_TERRENO_IMP_asbuilt.ifc`). '
          'Se o IMP for o executado, as CT do esgoto e da drenagem precisam ser refeitas pelo projetista e a compatibilização roda de novo.',
          '2. **Esgoto × drenagem (6):** só o projetista hidrossanitário resolve (as duas redes ficam fixas).',
          '3. **Interfaces com a fundação as built (111 pendentes):** ramais, prumadas AP e caixas junto às sapatas/baldrames do restaurante, subestação e guarita. '
          'São passagens a prever (luva/furo) ou caixa a afastar; a cota das fundações depende do item 1.', '',
          'Opções recomendadas que adotei sem esperar: as 17 da fase 2 (CF da drenagem = CT − profundidade nas 5 caixas, recobrimentos AF 0,30 / PCI 0,50 / '
          'ELE 0,70 m, drenos fora, Ø de premissa); Δz até 1,50 m e topo até 2,50 m antes de desviar (preferir profundidade); canaletas do campo esquemáticas; '
          'equipamentos com dimensão de premissa.', '']
    L += ['## Arquivos', '',
          f'- IFC por disciplina: `RELATORIOS\\PRECLASH_2026-10-18\\IFC_POR_DISCIPLINA_{CEN}\\` (CAT_HIDRO, CAT_ELE, CAT_PCIP + terreno do projeto e terreno do IMP as built).',
          f'- Federado: `RELATORIOS\\PRECLASH_2026-10-18\\CAT_preclash_solucao_{CEN}.ifc` (redes, equipamentos, fundações as built, terreno, conflitos).',
          '- 3D: `CAT_preclash_visualizador.html` e `CAT.json` (visualizador único).',
          '- Executivos na revisão seguinte, no padrão das outras escolas (linha nova no quadro de revisões do carimbo, código da folha, PDF A0 por folha): '
          '`ETIB-CATU\\EXECUTIVO_REVISADO\\` — AGF-001-R03, EL-001-ELG-R06, EL-002-ELG-R03, INC-001-ING-R04 (`.dwg` + `_itens.csv`); PDFs da folha e das notas em `PDF\\`; '
          'conferência em `conferencia\\`. Scripts: `FERRAMENTAS\\georef\\exec_catu.py` (desenho no modelo) e `exec_padrao_catu.py` (carimbo, código e PDF).']
    for r in ex:
        L.append(f"  - {r['nome']}: {r['trechos']} trechos refeitos, {r['caixas']} caixas deslocadas, {r['nuvens']} nuvens, {r['mergulhos']} mergulhos anotados ({r.get('marca', '')}).")
    L += ['', '## Pendentes por categoria', '']
    for cat, n in pc.most_common():
        L.append(f'### {cat} ({n})'); L.append('')
        for r in [r for r in pend if r['categoria'] == cat][:25]:
            L.append(f"- {r['gravidade']}: {r['conflito']} — {r['o_que_seria_preciso']}")
        if n > 25: L.append(f'- … mais {n - 25} (ver `CAT_preclash_{CEN}_pendentes.csv`).')
        L.append('')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
    print(OUT)


if __name__ == '__main__':
    main()
