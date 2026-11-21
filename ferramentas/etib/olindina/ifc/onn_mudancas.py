# -*- coding: utf-8 -*-
"""Olindina — lista única de mudanças para as pranchas, em UTM (preclash/executivo/rever.py), como na Sátiro (sat_mudancas.py):
  - do preclash (ONN_preclash_AD_mudancas.json): profundidade de cada trecho pelo estudo de cota (nota "PROF. x,xx m");
  - do adaptador (escolas/olindina.py): caixas de passagem deslocadas (ONN_caixas_movidas.json);
  - etiquetas de cota corrigidas na prancha (TEXTOS; o onn_exec.py troca o texto).
A cota da água fria é premissa e não vira nota; trecho no recobrimento mínimo do projeto também não. Cada mudança ganha 'folha'. Grava <SAIDA>/ONN_mudancas_UTM.json."""
import os, sys, json, collections
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import escolas.olindina as S

PRE = S.SAIDA
br = lambda v: ('%.2f' % v).replace('.', ',')
# troca de texto nas pranchas: (E, N) UTM do texto, texto atual e novo
TEXTOS = [dict(caixa='CA-06', E=574033.1579 - 104.07, N=8743129.589 + 126.90, de='CT:166.91', para='CT:166.81')]


def main():
    mud = []
    for m in json.load(open(os.path.join(PRE, 'ONN_preclash_AD_mudancas.json'), encoding='utf-8'))['mudancas']:
        if m['disc'] == 'AF': continue
        # trecho que ficou no recobrimento mínimo do projeto (hidrante 0,50 m da nota 5 do IN-001; elétrica 0,70 m): a diferença é só
        # o terreno do IMP (poucos cm); não é mudança de projeto e não vira nota
        if m['tipo'] == 'mergulho' and m.get('origem') == 'estudo' and abs(m['prof_topo'] - S.REGRAS['estudo']['cob_min'].get(m['disc'], -1)) < 0.005:
            continue
        if m['tipo'] == 'mergulho': m['nota'] = 'PROF. %s m' % br(m['prof_topo'])
        mud.append(m)
    fm = os.path.join(PRE, 'ONN_caixas_movidas.json')
    for r in (json.load(open(fm, encoding='utf-8')) if os.path.exists(fm) else []):
        if r['status'] != 'caixa deslocada': continue
        mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                        lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r.get('forma', 'q'), nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
    # etiqueta de cota corrigida na própria prancha (Anderson, 22/10/2026: "podemos nós mesmos alterar isso e gerar revisão"):
    # CA-06 do pluvial do BA5, "CT:166.91" (segunda linha = fundo) com profundidade (01.19) -> 166,81 (fecha com i = 1 % da CA-05)
    for t in TEXTOS:
        mud.append(dict(tipo='texto', disc='AP', trecho=t['caixa'], elemento='AP:' + t['caixa'], info={}, **t))
    saida = []
    for m in mud:
        for f in S.folhas(m): saida.append(dict(m, folha=f))
    fn = os.path.join(PRE, 'ONN_mudancas_UTM.json')
    json.dump({'mudancas': saida, 'coordenadas': 'UTM SIRGAS 2000 24S (m)'}, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    c = collections.Counter((m['folha'], m['tipo']) for m in saida)
    for k in sorted(c): print(k, c[k])
    pr = [m['prof_topo'] for m in saida if m['tipo'] == 'mergulho']
    if pr: print('maior PROF. nas notas: %s m' % br(max(pr)))
    return fn


if __name__ == '__main__':
    main()
