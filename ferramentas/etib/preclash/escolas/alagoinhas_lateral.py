# -*- coding: utf-8 -*-
"""TESTE (21/10/2026, pergunta do Anderson): Alagoinhas com o deslocamento lateral do trecho ligado (preclash/desvio.py:
contornos, ±0,4 a ±3,0 m com transições a 45°), em pasta separada — a entrega continua sendo a de escolas/alagoinhas.py."""
import os, shutil, copy
from escolas import alagoinhas as _A
from escolas.alagoinhas import *          # noqa
SAIDA = os.path.join(os.path.dirname(_A.SAIDA), 'PRECLASH_IMP_R03_TESTE_LATERAL')
os.makedirs(SAIDA, exist_ok=True)
shutil.copy2(os.path.join(_A.SAIDA, 'ALI_ajustes_pares.json'), SAIDA)
REGRAS = copy.deepcopy(_A.REGRAS); REGRAS['contornos'] = True
_A.SAIDA = SAIDA                           # carregar() do adaptador grava os ajustes aqui, não na rodada de entrega


def carregar():
    return _A.carregar()


# o contorno da ferramenta só olha pressurizada × caixa de gravidade; aqui todo crítico de um trecho pressurizado móvel entra,
# e o cruzamento com tubo de gravidade conta inteiro (sem mergulho depois: 'mergulho_local' é False em Alagoinhas)
import collections as _col
import numpy as _np
from preclash import desvio as _dv, clash as _cl
from preclash.modelo import comprimento_planta as _cp
from preclash.leitura import perfil_por_recobrimento as _perfil
RELATORIO = []


def _crit(e, E, C, regras):
    ev, cv = _dv._vizinhos(e, E, C)
    return [c for c in _cl.detectar([e] + ev, cv, regras, campo='pts') if not c['ligacao'] and e['id'] in (c['a'], c['b']) and c['gravidade'] == 'CRÍTICA']


def _contornos(E, C, pend, regras, ter, log=print):
    ids = {e['id']: e for e in E}
    alvo = set()
    for p in pend:
        for k in ('a', 'b'):
            x = ids.get(p.get(k))
            if x is not None and x['tipo'] == 'pressao' and x['movel'] and x.get('estudo'): alvo.add(x['id'])
    feitos = []
    for eid in sorted(alvo):
        e = ids[eid]; P2 = e['pts'][:, :2]; S = _cp(e['pts']); conf0 = _crit(e, E, C, regras)
        if not conf0: continue
        cob = e['estudo']['cob']
        ss = sorted(_dv._proj_s(P2, S, _np.array([c['E'], c['N']])) for c in conf0)
        melhor = None
        for s0, s1 in {(max(_dv.PONTA, ss[0] - 1.2), min(S[-1] - _dv.PONTA, ss[-1] + 1.2))} | {(max(_dv.PONTA, s - 1.2), min(S[-1] - _dv.PONTA, s + 1.2)) for s in ss}:
            if s1 <= s0: continue
            for o in _dv.OFFSETS:
                for sg in (1, -1):
                    Q = _dv._deslocar(P2, s0, s1, sg * o)
                    try: P3 = _perfil(Q, e['de'], cob, ter)
                    except ValueError: continue
                    n = len(_crit(dict(e, pts=P3), E, C, regras))
                    chave = (n, o)
                    if melhor is None or chave < melhor[0]: melhor = (chave, sg * o, P3, s0, s1)
        outros = sorted({(c['b'] if c['a'] == eid else c['a']) for c in conf0})
        nomes = [next((x['trecho'] for x in E if x['id'] == o), None) or next((cx['info'].get('nome', cx['id']) for cx in C if cx['id'] == o), o) for o in outros]
        r = dict(trecho=e['trecho'], disc=e['disc'], antes=len(conf0), depois=melhor[0][0] if melhor else len(conf0),
                 desloc=melhor[1] if melhor else None, com=nomes, s0=melhor[3] if melhor else None, s1=melhor[4] if melhor else None)
        RELATORIO.append(r); log(f"  lateral {e['trecho']} ({e['disc']}) × {', '.join(nomes)}: {r['antes']} -> {r['depois']} críticos com {r['desloc']} m")
        if melhor and melhor[0][0] < len(conf0):
            e['pts'] = melhor[2]; e['pts_sol'] = melhor[2].copy(); e.pop('S', None)
            feitos.append({'tipo': 'contorno', 'elemento': eid, 'disc': e['disc'], 'trecho': e['trecho'], 'status': 'aplicado',
                           'E': float(conf0[0]['E']), 'N': float(conf0[0]['N']), 's0': melhor[3], 's1': melhor[4], 'desloc': melhor[1],
                           'acrescimo': float(_cp(melhor[2])[-1] - S[-1]), 'linhas_sit': 0, 'evitados': nomes, 'fixos_antes': len(conf0), 'fixos_depois': melhor[0][0]})
    import json
    json.dump(RELATORIO, open(os.path.join(SAIDA, 'ALI_teste_lateral.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return feitos


_dv.contornos = _contornos
