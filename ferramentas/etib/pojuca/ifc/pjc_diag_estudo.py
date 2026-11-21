# -*- coding: utf-8 -*-
"""Pojuca — diagnóstico do estudo de cota de uma rede (AF ou HID): custo, colisões e folgas curtas por recobrimento, contra a gravidade,
as caixas e a estrutura (a elétrica ainda não estudada entra como 'futuros', que precisam passar por cima).
Uso: python pjc_diag_estudo.py HID|AF"""
import sys, os
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
from escolas import pojuca as S
from preclash import estudo as etd, parametros, clash as cl


def main():
    disc = sys.argv[1] if len(sys.argv) > 1 else 'HID'
    D = S.carregar(); R = parametros.aplicar(S); cfg = dict(etd.PADRAO, **R['estudo'])
    E, C, ter = D['elementos'], D['caixas'], D['terreno']
    for e in E: e.setdefault('pts_sol', e['pts'].copy())
    G = [g for g in etd.grupos(E, C, cfg) if g['disc'] == disc]
    ter2 = etd.TerrenoPreenchido(ter, S.CAIXA_OBRA, 1)
    for g in G:
        ids = {e['id'] for e in g['els']}
        fixos = [e for e in E if e['id'] not in ids and e['disc'] not in ('AF', 'HID', 'ELE', 'SDAI')]
        outros = etd._segs(fixos, 'pts_sol')
        futuros = etd._segs([e for e in E if e['disc'] in ('ELE', 'SDAI') and e['tipo'] == 'pressao'], 'pts')
        print(g['nome'], len(g['els']), 'trechos')
        for cob in np.arange(cfg['cob_min'][disc], cfg['prof_max'] + 1e-6, 0.05):
            cand = [(e, etd._perfil(e, float(cob), ter2)) for e in g['els']]
            c, nc, nk = etd.custo(cand, outros, C, R, cfg, disc, futuros, ter2)
            # quem colide (sem os futuros)
            cs = []
            for e, P in cand:
                e2 = dict(e, pts=P, pts_sol=P)
                for x in cl.detectar([e2] + fixos, C, R, campo='pts_sol'):
                    if x['gravidade'] == 'CRÍTICA' and e['id'] in (x['a'], x['b']) and not x['ligacao']:
                        o = x['b'] if x['a'] == e['id'] else x['a']
                        cs.append(f"{e['trecho']}×{o.split(':', 1)[-1]}")
            print(f'  cob {cob:.2f}: custo {c:.0f} colisões {nc} curtas {nk} | {", ".join(sorted(set(cs)))}')


if __name__ == '__main__':
    main()
