# -*- coding: utf-8 -*-
"""Sátiro Dias — lista única de mudanças para as pranchas, em UTM (preclash/executivo/rever.py), como em Alagoinhas (alh_mudancas.py):
  - do preclash (SAT_preclash_AD_mudancas.json): profundidade de cada trecho pelo estudo de cota (nota "PROF. x,xx m") e caixas
    deslocadas pela ferramenta;
  - do adaptador (escolas/satiro.py): contornos curtos, derivações levadas para dentro da caixa, nós tirados de dentro de caixa
    de esgoto/pluvial, a TJ-02 que recua pelo AF-16 e caixas deslocadas/afastadas.
Cada mudança ganha 'folha' (AF-001, ESG-001, EL-001, EL-002, IN-001, CPS-DRE-001, CPS-ELE-001). Grava <SAIDA>/SAT_mudancas_UTM.json."""
import os, sys, json, collections
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import escolas.satiro as S

PRE = S.SAIDA
# último trecho (montante, jusante) em planta dos tubos de pluvial que chegam acima do fundo (S.CHEGADA)
CHEGADA_XY = {'AP-199': [(545977.258, 8716244.439), (545983.114, 8716236.994)]}
# etiquetas trocadas na ESG-001 (o sat_exec.py troca o texto; (E, N) UTM do texto): fundo da PVE-06 5 cm mais baixo e o ESG-014
# saindo dela (S.SAIDA_ABAIXO), Anderson, 22/10/2026
_T = (545929.370875, 8716089.409625)      # translação local -> UTM da ESG-001
TEXTOS = [dict(caixa='PVE-06', E=_T[0] + 98.417, N=_T[1] + 95.961, de='CF.: 234.30', para='CF.: 234.25'),
          dict(caixa='PVE-06', E=_T[0] + 101.817, N=_T[1] + 96.371, de='(01.70)', para='(01.75)'),
          dict(caixa='ESG-014', E=_T[0] + 95.747, N=_T[1] + 93.501, de='i=1%', para='i=0.67%')]
br = lambda v: ('%.2f' % v).replace('.', ',')


_ENT = {}


def entidade(r):
    """handle da linha da prancha que contém o traçado original do trecho (pela cópia DXF da folha em EXECUTIVO_.../_copias),
    ou None se a cópia ainda não existe."""
    import math
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
    import asbuilt as ab
    dwg = S.executivo_dwg(dict(r, folha=S.folha(r)))
    if not dwg: return None
    dxf = os.path.join(S.REL, 'EXECUTIVO_2026-10-21', '_copias', os.path.basename(dwg)[:-4] + '.dxf')
    if not os.path.exists(dxf): return None
    if dxf not in _ENT:
        T = json.load(open(os.path.join(S.BASE, 'CAD_GEORREFERENCIADO', 'transformacoes_local_para_UTM.json'), encoding='utf-8'))['arquivos'][dwg]
        _ENT[dxf] = ([e for e in ab.entidades(dxf) if e['typ'] in ('LINE', 'LWPOLYLINE')], math.radians(T['rot_deg']), np.array(T['t']))
    E, a, t = _ENT[dxf]
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    A = (R.T @ (np.array(r['antigo'])[:, :2] - t).T).T
    melhor = None
    for e in E:
        P = np.asarray(e['pts'], float)[:, :2]
        d = max(min(np.min(np.hypot(*(P - q).T)), 99) for q in A[1:-1]) if len(A) > 2 else None
        # distância de cada ponto do traçado ao segmento mais próximo da entidade
        def dseg(q):
            m = 99
            for u, v in zip(P[:-1], P[1:]):
                w = v - u; L2 = float(w @ w)
                if L2 < 1e-12: continue
                tt = float(np.clip((q - u) @ w / L2, 0, 1)); m = min(m, float(np.hypot(*(u + w * tt - q))))
            return m
        dd = max(dseg(q) for q in A)
        if dd < 0.30 and (melhor is None or dd < melhor[0]): melhor = (dd, e['h'])
    return melhor[1] if melhor else None


def mesma_entidade(a, b):
    ha, hb = entidade(a), entidade(b)
    return ha is not None and ha == hb


def main():
    mud = []
    for m in json.load(open(os.path.join(PRE, 'SAT_preclash_AD_mudancas.json'), encoding='utf-8'))['mudancas']:
        if m['tipo'] == 'mergulho': m['nota'] = 'PROF. %s m' % br(m['prof_topo'])
        mud.append(m)
    ult = {}
    fc = os.path.join(PRE, 'SAT_contornos.json')
    for r in (json.load(open(fc, encoding='utf-8')) if os.path.exists(fc) else []):
        if r.get('status') != 'contorno em planta': continue
        k = r['elemento']
        if k in ult: r = dict(r, caixa=ult[k]['caixa'] + ', ' + r['caixa'], antigo=ult[k]['antigo'])
        ult[k] = r
        if r.get('torneira'):            # a torneira (símbolo e texto) anda até a ponta nova do ramal
            mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento='AF:' + r['caixa'], info={}, E=r['pontos'][-1][0],
                            N=r['pontos'][-1][1], de=r['antigo'][-1], lado=0.30, lado_y=0.30, rot=0.0, forma='q', nota=f"torneira {r['caixa']} recuada"))
    # contornos de trechos seguidos da mesma rede (SDAI-01, 02 e 03 contornando os PV do esgoto) viram uma mudança só: na prancha os
    # três são uma polilinha única, e o rever.py só altera uma entidade uma vez (SDAI-02/03 ficavam "traçado original não achado")
    rs = list(ult.values()); feito = True
    while feito:
        feito = False
        for a in rs:
            b = next((b for b in rs if b is not a and b['disc'] == a['disc'] and np.hypot(*(np.array(a['antigo'][-1]) - np.array(b['antigo'][0]))) < 0.05
                      and np.hypot(*(np.array(a['pontos'][-1]) - np.array(b['pontos'][0]))) < 0.05 and mesma_entidade(a, b)), None)
            if b is None: continue
            a.update(trecho=a['trecho'] + ', ' + b['trecho'], caixa=a['caixa'] + ', ' + b['caixa'], antigo=a['antigo'] + b['antigo'][1:],
                     pontos=a['pontos'] + b['pontos'][1:])
            rs.remove(b); feito = True; break
    for r in rs:
        nov = np.array(r['pontos'])
        mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, antigo=r['antigo'], novo=r['pontos'],
                        E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()), nota=f"contorno de {r['caixa']}"))
    fm = os.path.join(PRE, 'SAT_caixas_movidas.json')
    for r in (json.load(open(fm, encoding='utf-8')) if os.path.exists(fm) else []):
        if r['status'] != 'caixa deslocada': continue
        mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                        lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r.get('forma', 'r'), nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
    # pluvial que chega acima do fundo da caixa de jusante (d08 da página; AP-108 × ESG-014): nota na ESG-001 com a GI da chegada
    for tr, (cx, dz, gi0) in S.CHEGADA.items():
        a, b = CHEGADA_XY[tr]
        mud.append(dict(tipo='mergulho', origem='decisao', disc='AP', elemento='AP:' + tr, trecho=tr, info={}, E=b[0], N=b[1],
                        planta=[[a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t] for t in (0.6, 0.8, 1.0)],
                        prof_topo=None, nota_fixa=('CHEGADA NA %s: GI %.2f' % (cx, gi0 + dz)).replace('.', ',')))
    for t in TEXTOS:
        mud.append(dict(tipo='texto', disc='ESG', trecho=t['caixa'], elemento='ESG:' + t['caixa'], info={}, **t))
    vistas = {}
    for m in mud:                       # a mesma caixa deslocada duas vezes: de = a primeira origem, para = a última posição
        if m['tipo'] != 'caixa deslocada': continue
        k = m['trecho']
        if k in vistas: vistas[k]['E'], vistas[k]['N'] = m['E'], m['N']; m['_dup'] = True
        else: vistas[k] = m
    mud = [m for m in mud if not m.get('_dup')]
    saida = []
    for m in mud:
        f = S.folha(m)
        if f: saida.append(dict(m, folha=f))
    fn = os.path.join(PRE, 'SAT_mudancas_UTM.json')
    json.dump({'mudancas': saida, 'coordenadas': 'UTM SIRGAS 2000 24S (m)'}, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    c = collections.Counter((m['folha'], m['tipo']) for m in saida)
    for k in sorted(c): print(k, c[k])
    pr = [m['prof_topo'] for m in saida if m['tipo'] == 'mergulho' and m.get('prof_topo') is not None]
    if pr: print('maior PROF. nas notas: %s m' % br(max(pr)))
    return fn


if __name__ == '__main__':
    main()
