# -*- coding: utf-8 -*-
"""Jandaíra — quadro "hoje × com a solução" por par de disciplinas (1 caixa = 1 elemento; peças da mesma caixa agrupadas).
Gravidade (formato R02): colisão física = CRÍTICA; folga < 20 cm = ATENÇÃO; estrutura: fundação/pilar = CRÍTICA, viga baldrame = ATENÇÃO (travessia),
laje/parede = INFORMAÇÃO (passagem). Pares só entre redes fixas (DRE, ESG, estrutura) = "a definir pelo projetista".
Uso: jan_resumo.py [solucao.json] -> RELATORIOS/compat_R01/resumo_R01.json, pontos_R01_hoje.csv, pontos_R01_solucao.csv"""
import sys, os, json, csv, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan_dados as JD, jan_clash as JC, motor
sys.stdout.reconfigure(encoding='utf-8')
FIXO = {'DRE', 'ESG', 'EST'}
SAIDA = os.path.dirname(JD.G)


def gravidade(A, B, g):
    if 'EST' in (A['disc'], B['disc']):
        E = A if A['disc'] == 'EST' else B
        if E['cat'] in ('Pisos', 'Paredes'): return 'INFORMACAO' if g < motor.TOL else None
        if E['cat'] == 'Quadro estrutural': return 'ATENCAO' if g < 0.10 else None
        return 'CRITICA' if g < motor.TOL else ('ATENCAO' if g < 0.10 else None)
    return 'CRITICA' if g < motor.TOL else 'ATENCAO'


def agrupar(P):
    G = {}
    for A, B, g, pt in P:
        if (A['disc'], A['grupo']) > (B['disc'], B['grupo']): A, B = B, A
        k = (A['disc'], A['grupo'], B['disc'], B['grupo'])
        if k not in G or g < G[k][0]: G[k] = (g, pt, A, B)
    out = []
    for (da, ga, db, gb), (g, pt, A, B) in G.items():
        sev = gravidade(A, B, g)
        if sev: out.append(dict(da=da, ga=ga, db=db, gb=gb, g=g, pt=pt, sev=sev, A=A, B=B, par='×'.join(sorted((da, db))),
                                fixo=(da in FIXO and db in FIXO)))
    return out


def rodar(mods=None):
    S, M, P = JC.rodar('daniel', mods)
    JD.agrupar_caixas(S, M)
    return agrupar(P)


def gravar(L, nome):
    with open(os.path.join(SAIDA, nome), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['par', 'gravidade', 'disc_a', 'elem_a', 'disc_b', 'elem_b', 'folga_cm', 'x', 'y', 'cota', 'E', 'N', 'a_definir'])
        for r in sorted(L, key=lambda r: (r['par'], r['sev'], r['g'])):
            e = JD.para_compart(np.array([r['pt']]))[0]
            w.writerow([r['par'], r['sev'], r['da'], r['ga'], r['db'], r['gb'], '%.1f' % (r['g'] * 100), '%.2f' % r['pt'][0], '%.2f' % r['pt'][1],
                        '%.2f' % e[2], '%.2f' % e[0], '%.2f' % e[1], 'sim' if r['fixo'] else ''])


if __name__ == '__main__':
    sol = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SAIDA, 'solucao_R01.json')
    H = rodar(); S = rodar(json.load(open(sol, encoding='utf-8')))
    gravar(H, 'pontos_R01_hoje.csv'); gravar(S, 'pontos_R01_solucao.csv')
    tab = collections.defaultdict(lambda: collections.Counter())
    for nome, L in (('hoje', H), ('sol', S)):
        for r in L: tab[r['par']][(nome, r['sev'])] += 1
    res = {}
    print(f"{'par':12s} | hoje: col  aten info | solução: col  aten info")
    for par in sorted(tab):
        c = tab[par]; res[par] = {k[0] + '_' + k[1]: v for k, v in c.items()}
        print(f"{par:12s} |      {c[('hoje','CRITICA')]:4d} {c[('hoje','ATENCAO')]:4d} {c[('hoje','INFORMACAO')]:4d} |          {c[('sol','CRITICA')]:4d} {c[('sol','ATENCAO')]:4d} {c[('sol','INFORMACAO')]:4d}")
    tot = lambda L, s: sum(1 for r in L if r['sev'] == s)
    print('TOTAL hoje', tot(H, 'CRITICA'), tot(H, 'ATENCAO'), tot(H, 'INFORMACAO'), '| solução', tot(S, 'CRITICA'), tot(S, 'ATENCAO'), tot(S, 'INFORMACAO'))
    print('colisões que sobram com a solução:')
    for r in sorted(S, key=lambda r: (r['fixo'], r['par'], r['g'])):
        if r['sev'] == 'CRITICA': print(f"  {'[a definir] ' if r['fixo'] else ''}{r['da']} {r['ga'][:26]} × {r['db']} {r['gb'][:30]} {r['g']*100:.1f} cm ({r['pt'][0]:.1f};{r['pt'][1]:.1f})")
    json.dump(res, open(os.path.join(SAIDA, 'resumo_R01.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
