# -*- coding: utf-8 -*-
"""Lista das mudanças de um cenário resolvido (mergulhos, contornos e caixas deslocadas), em UTM, para o passo 7
(revisão das pranchas executivas em DWG: executivo/rever.py). Grava <SIGLA>_preclash_<cenário>_mudancas.json."""
import json
import numpy as np
from . import solver as sv


def br(v, d=2):
    return f'{v:.{d}f}'.replace('.', ',')


def _trecho_planta(e, s0, s1, n=12):
    s = np.linspace(s0, s1, n)
    return [[round(float(x), 3), round(float(y), 3)] for x, y in sv._pos(e, s)]


def listar(r, ter):
    out = []
    ids = r['ids']; cx = {c['id']: c for c in r['caixas']}
    nome = lambda m: (ids[m]['trecho'] + f" ({ids[m]['disc']})") if m in ids else ('caixa ' + cx[m]['info'].get('nome', m) if m in cx else m)
    for s in r['sol']:
        e = ids[s['elemento']]
        mot = ', '.join(nome(m) for m in s['motivos'])
        out.append({'tipo': 'mergulho', 'disc': e['disc'], 'elemento': e['id'], 'trecho': e['trecho'], 'info': {k: v for k, v in e['info'].items() if isinstance(v, (str, int, float))},
                    'E': round(float(s['E']), 3), 'N': round(float(s['N']), 3), 'planta': _trecho_planta(e, s['s0'], s['s1']),
                    'dz': round(float(s['dz']), 3), 'eixo_depois': round(float(s['eixo_depois']), 3), 'extensao': round(float(s['extensao']), 2), 'prof_topo': round(float(s['prof_topo_depois']), 2),
                    'nota': f"{'Rebaixar' if s['dz'] < 0 else 'Elevar'} {e['trecho']} {br(abs(s['dz']))} m em {br(s['extensao'])} m (eixo {br(s['eixo_depois'])}), "
                            f"com conexões verticais, para {'passar sob' if s['dz'] < 0 else 'passar sobre'} {mot}."})
    # cota do estudo (estudo.py): a rede inteira/o trecho muda de profundidade -> nota de profundidade ao longo do trecho
    for e in r['E']:
        if not e.get('estudo') or 'pts_projeto' not in e: continue
        S = sv.comprimento_planta(e['pts']); z0 = np.interp(S, sv.comprimento_planta(e['pts_projeto']), e['pts_projeto'][:, 2])
        dz = float(np.mean(e['pts'][:, 2] - z0))
        if abs(dz) < 0.05: continue
        sm = S[-1] / 2; p = sv._pos(e, [sm])[0]
        out.append({'tipo': 'mergulho', 'origem': 'estudo', 'disc': e['disc'], 'elemento': e['id'], 'trecho': e['trecho'],
                    'info': {k: v for k, v in e['info'].items() if isinstance(v, (str, int, float))},
                    'E': round(float(p[0]), 3), 'N': round(float(p[1]), 3), 'planta': [[round(float(x), 3), round(float(y), 3)] for x, y in e['pts'][:, :2]],
                    'dz': round(dz, 3), 'eixo_depois': round(float(np.mean(e['pts'][:, 2])), 3), 'extensao': round(float(S[-1]), 2), 'prof_topo': round(float(e['estudo']['cob']), 2),
                    'nota': f"{e['trecho']}: implantar com o topo a {br(e['estudo']['cob'])} m do terreno (estudo de cota da rede)."})
    for d in r.get('desvios', []):
        if d['status'] != 'aplicado': continue
        if d['tipo'] == 'contorno':
            e = ids[d['elemento']]
            antigo = e.get('pts_original', e['pts'])[:, :2]; novo = e['pts'][:, :2]
            evit = ', '.join(nome(m) for m in d['evitados'])
            lado = 'à esquerda' if d['desloc'] > 0 else 'à direita'
            out.append({'tipo': 'contorno', 'disc': e['disc'], 'elemento': e['id'], 'trecho': e['trecho'], 'info': {k: v for k, v in e['info'].items() if isinstance(v, (str, int, float))},
                        'E': round(float(d['E']), 3), 'N': round(float(d['N']), 3),
                        'desloc': float(d['desloc']), 'antigo': [[round(float(x), 3), round(float(y), 3)] for x, y in antigo], 'novo': [[round(float(x), 3), round(float(y), 3)] for x, y in novo],
                        'nota': f"Deslocar {e['trecho']} {br(abs(d['desloc']))} m {lado} (sentido do traçado), transições a 45°, para não atravessar {evit}."})
        elif d['tipo'] == 'caixa deslocada':
            c = cx[d['elemento']]
            out.append({'tipo': 'caixa deslocada', 'disc': c['disc'], 'elemento': c['id'], 'trecho': c['info'].get('nome', c['id']), 'info': {},
                        'E': round(float(c['E']), 3), 'N': round(float(c['N']), 3), 'de': [round(float(c.get('E0', c['E'])), 3), round(float(c.get('N0', c['N'])), 3)],
                        'lado': round(2 * float(c.get('mx', c['meia'])), 3), 'lado_y': round(2 * float(c.get('my', c['meia'])), 3), 'rot': float(c.get('rot', 0.0)),
                        'forma': c['forma'], 'nota': f"Deslocar a caixa {c['info'].get('nome', c['id'])} {br(d['desloc'])} m; as redes que chegam nela acompanham."})
    return out


def gravar(fn, S, k, r, ter):
    dados = {'escola': S.ESCOLA, 'sigla': S.SIGLA, 'cenario': k, 'nome_cenario': r['nome'], 'mudancas': listar(r, ter)}
    open(fn, 'w', encoding='utf-8').write(json.dumps(dados, ensure_ascii=False, indent=1))
    return len(dados['mudancas'])
