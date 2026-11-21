# -*- coding: utf-8 -*-
"""Parâmetros do projeto (contrato 24-049), valem para todas as escolas salvo o que o adaptador fixar.
Profundidade máxima das redes, do terreno ao topo do tubo, todas as disciplinas:
  - 19/10/2026 (Anderson): "até 1,5 m" -> Jandaíra entregue assim e fica com 1,50;
  - 20/10/2026 (Anderson): "para os outros projetos vamos aumentar a profundidade para até 2 m" -> 2,00 nas demais.
rodar.py põe esse valor em REGRAS['prof_max_geral'] (teto dos mergulhos, solver.py) e em REGRAS['estudo']['prof_max']
(estudo de cota) quando o adaptador não define; o 'prof_max_topo' de cada disciplina no adaptador continua valendo abaixo do teto."""

PROF_MAX_PADRAO = 2.00
PROF_MAX_ESCOLA = {'JAN': 1.50}


def prof_max(sigla):
    return PROF_MAX_ESCOLA.get(sigla, PROF_MAX_PADRAO)


def aplicar(S):
    """completa S.REGRAS com os parâmetros do projeto (sem sobrescrever o que o adaptador já fixou)."""
    R = dict(S.REGRAS); pm = prof_max(S.SIGLA)
    R.setdefault('prof_max_geral', pm)
    if R.get('estudo') is not None:
        R['estudo'] = dict(R['estudo']); R['estudo'].setdefault('prof_max', pm)
    S.REGRAS = R
    return R
