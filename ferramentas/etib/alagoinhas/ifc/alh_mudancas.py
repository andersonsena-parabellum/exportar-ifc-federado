# -*- coding: utf-8 -*-
"""Alagoinhas (implantação) — lista única de mudanças para as pranchas, em UTM (preclash/executivo/rever.py):
  - do preclash (ALI_preclash_AD_mudancas.json): profundidade de cada trecho pelo estudo de cota (nota "PROF. x,xx m") e caixas
    deslocadas pela ferramenta (ELE/SDAI e, gravidade × gravidade, DRE/ESG até 0,60 m);
  - do adaptador (alh_ajustes.py): contornos curtos em volta de PV/peças da estrutura e caixas deslocadas.
Cada mudança ganha 'folha' (AGF-001, ESG-001, DRE-001, EL-001, EL-002, IN-001). Grava <SAIDA>/ALI_mudancas_UTM.json."""
import os, sys, json, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import escolas.alagoinhas as A

PRE = A.SAIDA
br = lambda v: ('%.2f' % v).replace('.', ',')


def main():
    mud = []
    for m in json.load(open(os.path.join(PRE, 'ALI_preclash_AD_mudancas.json'), encoding='utf-8'))['mudancas']:
        if m['tipo'] == 'mergulho' and not m.get('nota_fixa'): m['nota'] = 'PROF. %s m' % br(m['prof_topo'])
        mud.append(m)
    ult = {}
    fc = os.path.join(PRE, 'ALI_contornos.json')
    for r in (json.load(open(fc, encoding='utf-8')) if os.path.exists(fc) else []):
        k = r['elemento']
        if k in ult: r = dict(r, caixa=ult[k]['caixa'] + ', ' + r['caixa'], antigo=ult[k]['antigo'])
        ult[k] = r
    for r in ult.values():
        nov = np.array(r['pontos'])
        mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, antigo=r['antigo'], novo=r['pontos'],
                        E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()), nota=f"contorno de {r['caixa']}"))
    fm = os.path.join(PRE, 'ALI_caixas_movidas.json')
    for r in (json.load(open(fm, encoding='utf-8')) if os.path.exists(fm) else []):
        if r['status'] != 'caixa deslocada': continue
        mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                        lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r.get('forma', 'r'), nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
    # decisões das fichas da página de pendências (alh_decisoes.py): caixas movidas, desvios da gravidade e cotas da gravidade
    fd = os.path.join(PRE, 'ALI_decisoes.json')
    for r in (json.load(open(fd, encoding='utf-8')) if os.path.exists(fd) else []):
        if r['tipo'] == 'caixa deslocada':
            mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                            lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r.get('forma', 'r'), nota=f"caixa {r['trecho']} deslocada {br(r['desloc'])} m"))
        elif r['tipo'] == 'contorno':
            nov = np.array(r['novo'])
            mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, antigo=r['antigo'], novo=r['novo'],
                            E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()), nota=f"contorno de {r['caixa']}"))
        elif r['tipo'] == 'mergulho':
            mud.append(dict(r, info={}, nota=r['nota_fixa']))
    vistas = {}
    for m in mud:                       # a mesma caixa deslocada duas vezes: de = a primeira origem, para = a última posição
        if m['tipo'] != 'caixa deslocada': continue
        k = m['trecho']
        if k in vistas: vistas[k]['E'], vistas[k]['N'] = m['E'], m['N']; m['_dup'] = True
        else: vistas[k] = m
    mud = [m for m in mud if not m.get('_dup')]
    saida = []
    for m in mud:
        f = A.folha(m)
        if f: saida.append(dict(m, folha=f))
    fn = os.path.join(PRE, 'ALI_mudancas_UTM.json')
    json.dump({'mudancas': saida, 'coordenadas': 'UTM SIRGAS 2000 24S (m)'}, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    c = collections.Counter((m['folha'], m['tipo']) for m in saida)
    for k in sorted(c): print(k, c[k])
    pr = [m['prof_topo'] for m in saida if m['tipo'] == 'mergulho' and m.get('prof_topo') is not None]
    if pr: print('maior PROF. nas notas: %s m' % br(max(pr)))
    return fn


if __name__ == '__main__':
    main()
