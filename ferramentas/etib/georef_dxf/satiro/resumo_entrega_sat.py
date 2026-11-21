# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — resumo da entrega (IFC + pranchas) a partir das saídas do entrega_sat.py e do exec_rev_sat.py.
Grava RELATORIOS/SAT_ENTREGA_2026-10-19_LEIA-ME.md. Uso: .venv/Scripts/python.exe -X utf8 resumo_entrega_sat.py"""
import os, csv, glob, collections, time
BASE = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS'
REL = os.path.join(BASE, 'RELATORIOS')
PRE = os.path.join(REL, 'PRECLASH_2026-10-18')
EXE = os.path.join(REL, 'EXECUTIVOS_REVISADOS_2026-10-19')
OUT = os.path.join(REL, 'SAT_ENTREGA_2026-10-19_LEIA-ME.md')


def ler(fn):
    if not os.path.exists(fn): return []
    with open(fn, encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter=';'))


def conta(k, nome):
    return ler(os.path.join(PRE, f'SAT_preclash_{k}_{nome}.csv'))


def main():
    L = ['# ETIB Sátiro Dias — entrega da compatibilização (IFC + pranchas revisadas)', '',
         f'Gerado em {time.strftime("%d/%m/%Y %H:%M")} por `FERRAMENTAS\\georef_dxf\\satiro\\resumo_entrega_sat.py`. '
         'Método: pré-compatibilização 3D sem Revit (skill modelagem-ifc-sem-revit), terreno do IMP as built, equipamentos e fundações as built no clash.', '',
         '## O que foi entregue', '',
         '| Entregável | Arquivo |', '|---|---|',
         '| IFC por disciplina, cenário de entrega AD (sem a galeria Ø1200 + desvios em planta) | `RELATORIOS\\PRECLASH_2026-10-18\\IFC_POR_DISCIPLINA_AD\\SAT_HIDRO/ELE/PCIP_compatibilizado.ifc` + `SAT_TERRENO.ifc` |',
         '| IFC por disciplina, cenário BD (com a galeria Ø1200, se a construtora confirmar) | `...\\IFC_POR_DISCIPLINA_BD\\` |',
         '| Federado IFC (redes + caixas + equipamentos + fundações as built + terreno + conflitos que sobram) | `...\\SAT_preclash_solucao_AD.ifc` (e `_BD`, `_A`, `_B`, `_projeto`) |',
         '| Visualizador 3D local / dados do visualizador único | `...\\SAT_preclash_visualizador.html` / `...\\SAT.json` |',
         '| Pranchas executivas revisadas (DWG, cópia do original na revisão seguinte: AF, ESG e campo R01, EL-001/002 R02, IN-001 R04; linha nova no quadro de revisões do carimbo e código atualizado) | `RELATORIOS\\EXECUTIVOS_REVISADOS_2026-10-19\\*.dwg` |',
         '| As mesmas pranchas em PDF (uma por folha) | `...\\EXECUTIVOS_REVISADOS_2026-10-19\\PDF\\` |',
         '| Lista de itens de cada prancha | `...\\*_itens.csv` |', '',
         '## Números', '', '| Cenário | Críticos antes | Críticos depois | Atenção depois | Mergulhos | Desvios em planta | Pendentes |', '|---|---|---|---|---|---|---|']
    for k in ('A', 'B', 'AD', 'BD'):
        base = k[0]
        antes = conta(base, 'conflitos_antes'); dep = conta(k, 'conflitos_depois'); sol = conta(k, 'solucoes'); pen = conta(k, 'pendentes')
        dv = [d for d in conta(k, 'desvios') if d.get('status') == 'aplicado']
        L.append(f"| {k} | {sum(x['gravidade'] == 'CRÍTICA' for x in antes)} | {sum(x['gravidade'] == 'CRÍTICA' for x in dep)} | "
                 f"{sum(x['gravidade'] == 'ATENÇÃO' for x in dep)} | {len(sol)} | {len(dv) if k.endswith('D') else '—'} | {len(pen)} |")
    pen = conta('AD', 'pendentes')
    L += ['', '## Pendentes do cenário de entrega (AD), por categoria', '']
    for cat, n in collections.Counter(p['categoria'] for p in pen).most_common():
        L.append(f'- {cat}: {n}')
    L += ['', 'Lista completa: `SAT_preclash_AD_pendentes.csv` (com o que seria preciso para cada um).', '',
          '## Pranchas revisadas', '']
    for fn in sorted(glob.glob(os.path.join(EXE, '*_itens.csv'))):
        it = ler(fn); tipos = collections.Counter(i['descricao'].split(' —')[0] for i in it)
        L.append(f"- `{os.path.basename(fn).replace('_itens.csv', '.dwg')}`: {len(it)} itens ({', '.join(f'{n} {t.lower()}' for t, n in tipos.items())})")
    pdfs = sorted(glob.glob(os.path.join(EXE, 'PDF', '*.pdf')))
    L += ['', f'PDF gerados: {len(pdfs)}.', '']
    L += ['## Opções adotadas sem esperar decisão (noite de 18 para 19/10, a pedido do Anderson)', '',
          '- Cenário de entrega **AD** (sem a galeria Ø1200 + desvios em planta); o **BD** (com a galeria) está pronto em paralelo.',
          '- Recobrimentos: AF 0,30 m (premissa), hidrante/SDAI 0,50 m (nota 5 do PCI), elétrica 0,70 m (NBR 5410). O PAV R07 não tem estacionamento interno; o único acesso de veículos é o de serviço (não aplicado).',
          '- Campo: CPS ELE-001 (380/220 V); o ELE-002 é alternativa de tensão com o mesmo traçado.',
          '- Terreno: o do IMP as built (sólidos topográficos + pisos +233/+236), que bate com as CT das caixas do projeto (mediana 0,00 m).',
          '- Alinhamento do ELE/PCI pelas edificações: confirmado pelo IMP (edificações a 37,96°) e pelas fundações do BP4 (pilares a 0,10 m das paredes da base ELE/PCI; na SIT dão 0,54 m de mediana).',
          '- BP4: o vínculo dele no IMP está ~2,3 km fora da obra; as fundações foram posicionadas pelos pilares.',
          '- Equipamentos: postes da iluminação externa com 6 m (o desenho não dá a altura), do campo com 8 m (detalhe do CPS); quadros, abrigos, tanques e pilaretes com dimensões de catálogo; QDLT-CAMPO na posição do EL-002 (o CPS ELE-001 o põe 4,2 m ao lado).',
          '- Pranchas: mergulho só como nota e nuvem (a planta não muda); desvio com traçado novo em vermelho e o antigo marcado por cima com tracejado e X (o traçado original continua no desenho; apagá-lo é a limpeza final do projetista); caixa deslocada com a posição nova e a antiga cancelada. Deslocamentos menores que 10 cm não vão para a prancha.', '',
          '## O que de fato depende de alguém', '',
          '1. **Construtora: galeria 2 × Ø1200** ("rede futura se necessário"). Decide AD ou BD. No terreno do IMP ela ficaria até 1,17 m acima do chão no corpo e com a soleira 0,6–0,7 m acima na entrada: vale juntar à consulta já enviada.',
          '2. **Projetistas de esgoto/pluvial:** os pendentes "gravidade × gravidade" (só se resolvem no projeto hidrossanitário) e a **CA-01**: CT 236,00 no projeto, mas o IMP tem 235,15 ali; AP-011 e AP-158 ficariam ~0,3 m fora do chão.',
          '3. **Projetista estrutural / obra:** os pendentes "estrutura" (redes que cruzam sapatas, blocos e arranques de pilar as built): passagem prevista ou desvio local.',
          '4. **Ponto de atenção:** AF e esgoto foram desenhados sobre a base antiga (a da SIT), cujas edificações não coincidem com o as built; as saídas/entradas nas edificações podem estar deslocadas (até ~1 m nas pontas). Conferir na obra antes de executar.', '']
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('gravado', OUT)


if __name__ == '__main__':
    main()
