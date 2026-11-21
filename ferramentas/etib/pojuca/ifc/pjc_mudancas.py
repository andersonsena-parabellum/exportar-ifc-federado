# -*- coding: utf-8 -*-
"""Pojuca — lista única de mudanças para as pranchas, em UTM (preclash/executivo/rever.py), como na Catu (catu/ifc/cat_mudancas.py):
  - do preclash (PJC_preclash_AD_mudancas.json): profundidade de cada trecho pelo estudo de cota (nota "PROF. x,xx m") e caixas
    deslocadas pela ferramenta;
  - do adaptador e dos ajustes (pjc_ajustes.py): contornos de PV/peça da estrutura e caixas de passagem deslocadas.
Cada mudança ganha 'folha' (AF-001, ESG-001, DRE-001, EL-001, EL-002, IC-001, CPS-DRE-001, CPS-EL-001). Grava <SAIDA>/PJC_mudancas_UTM.json."""
import os, sys, json, collections, math
import numpy as np
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import escolas.pojuca as S

PRE = S.SAIDA
EXE = os.path.join(S.REL, 'EXECUTIVO_2026-10-26')
br = lambda v: ('%.2f' % v).replace('.', ',')
_ENT = {}


# entidade(), mesma_entidade() e ajustar_ao_desenho(): cópia de catu/ifc/cat_mudancas.py (25/10/2026)
def entidade(r):
    """handle da linha da prancha que contém o traçado original do trecho (pela cópia DXF da folha em EXECUTIVO_.../_copias)."""
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
    import asbuilt as ab
    dwg = S.executivo_dwg(dict(r, folha=S.folha(r)))
    if not dwg: return None
    dxf = os.path.join(EXE, '_copias', os.path.basename(dwg)[:-4] + '.dxf')
    if not os.path.exists(dxf): return None
    if dxf not in _ENT:
        rot, t = S.TRANSF_DWG[dwg]
        _ENT[dxf] = ([e for e in ab.entidades(dxf) if e['typ'] in ('LINE', 'LWPOLYLINE')], math.radians(rot), np.array(t))
    E, a, t = _ENT[dxf]
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    A = (R.T @ (np.array(r['antigo'])[:, :2] - t).T).T
    melhor = None
    for e in E:
        P = np.asarray(e['pts'], float)[:, :2]

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
    """os dois trechos estão na mesma linha da prancha e o traçado antigo dos dois juntos cabe nela (senão não junta)."""
    ha, hb = entidade(a), entidade(b)
    if ha is None or ha != hb: return False
    return entidade(dict(a, antigo=a['antigo'] + b['antigo'][1:])) == ha


def ajustar_ao_desenho(mud, tol=0.60, log=print):
    """na prancha (como na Catu) um eletroduto/tubo é muitas vezes uma LINE só que passa por várias caixas (o EL2-024 e o EL2-025 são a mesma
    linha 3C783 da EL-002), e o banco de eletrodutos é desenhado com uma linha por eletroduto, 0,2 a 0,5 m uma da outra (no modelo os
    eletrodutos do banco têm o mesmo eixo): o rever.py só acha a entidade quando o traçado antigo é a entidade inteira. Aqui cada
    contorno pega a entidade da prancha que contém o traçado antigo (até 'tol', uma entidade por mudança: no banco, cada eletroduto
    fica com uma linha), e a mudança vira a entidade inteira: o pedaço antes, o traçado novo deslocado do mesmo afastamento da linha
    do banco e o pedaço depois."""
    sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo')
    import asbuilt as ab
    from shapely.geometry import LineString, Point
    usadas = set(); atual = {}; n_ok = 0
    for m in mud:
        if m['tipo'] != 'contorno': continue
        dwg = S.executivo_dwg(dict(m, folha=S.folha(m)))
        dxf = os.path.join(EXE, '_copias', os.path.basename(dwg)[:-4] + '.dxf') if dwg else None
        if not dxf or not os.path.exists(dxf): continue
        if dxf not in _ENT:
            rot, t = S.TRANSF_DWG[dwg]
            _ENT[dxf] = ([e for e in ab.entidades(dxf) if e['typ'] in ('LINE', 'LWPOLYLINE')], math.radians(rot), np.array(t))
        E, a, t = _ENT[dxf]
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        loc = lambda P: (R.T @ (np.asarray(P, float)[:, :2] - t).T).T
        utm = lambda P: (R @ np.asarray(P, float).T).T + t
        A = loc(m['antigo']); Nv = loc(m['novo'])
        cand = []
        for e in E:
            P = np.asarray(e['pts'], float)[:, :2]
            if len(P) < 2: continue
            Ls = LineString(P); d = [Ls.distance(Point(q)) for q in A]
            if max(d) <= tol: cand.append(((dxf, e['h']) in usadas, float(np.mean(d)), e, Ls))
        if not cand: log(f"  {m['trecho']}: nenhuma entidade da prancha contém o traçado antigo"); continue
        usada, _, e, Ls = min(cand, key=lambda x: (x[0], x[1]))       # linha livre primeiro (banco: uma por eletroduto)
        P = np.asarray(e['pts'], float)[:, :2]
        proj = [np.array(Ls.interpolate(Ls.project(Point(q))).coords[0]) for q in A]
        sh = np.mean([p - q for p, q in zip(proj, A)], axis=0)               # afastamento da linha do banco
        base = loc(atual[(dxf, e['h'])]['novo']) if usada else P              # a mesma linha mudada por outro trecho antes
        Lb = LineString(base)
        s0, s1 = Lb.project(Point(A[0] + sh)), Lb.project(Point(A[-1] + sh))
        if s0 > s1: s0, s1 = s1, s0; Nv = Nv[::-1]
        S_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(base, axis=0).T))])
        antes = [p for p, s_ in zip(base, S_) if s_ < s0 - 0.05]; depois = [p for p, s_ in zip(base, S_) if s_ > s1 + 0.05]
        Q = np.array(antes + [q + sh for q in Nv] + depois)
        if usada:
            m0 = atual[(dxf, e['h'])]; m0['novo'] = utm(Q).tolist(); m0['trecho'] += ', ' + m['trecho']; m['_absorvida'] = True
        else:
            usadas.add((dxf, e['h'])); m['antigo'] = utm(P).tolist(); m['novo'] = utm(Q).tolist(); m['handle'] = e['h']; atual[(dxf, e['h'])] = m
        n_ok += 1
    mud[:] = [m for m in mud if not m.get('_absorvida')]
    log(f'  {n_ok} contornos casados com a entidade inteira da prancha')





def _ler(nome):
    fn = os.path.join(PRE, nome)
    return json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else []


def main():
    mud = []
    for m in json.load(open(os.path.join(PRE, 'PJC_preclash_AD_mudancas.json'), encoding='utf-8'))['mudancas']:
        if m['tipo'] == 'mergulho': m['nota'] = 'PROF. %s m' % br(m['prof_topo'])
        mud.append(m)
    ult = {}
    for r in _ler('PJC_contornos.json'):
        if r.get('status') != 'contorno em planta': continue
        k = r['elemento']
        if k in ult: r = dict(r, caixa=', '.join(x for x in (ult[k]['caixa'], r['caixa']) if x), antigo=ult[k]['antigo'])
        ult[k] = r
    rs = list(ult.values()); feito = True
    while feito:
        feito = False
        for a in rs:
            b = next((b for b in rs if b is not a and b['disc'] == a['disc'] and np.hypot(*(np.array(a['antigo'][-1]) - np.array(b['antigo'][0]))) < 0.05
                      and np.hypot(*(np.array(a['pontos'][-1]) - np.array(b['pontos'][0]))) < 0.05 and mesma_entidade(a, b)), None)
            if b is None: continue
            a.update(trecho=a['trecho'] + ', ' + b['trecho'], caixa=', '.join(x for x in (a['caixa'], b['caixa']) if x),
                     antigo=a['antigo'] + b['antigo'][1:], pontos=a['pontos'] + b['pontos'][1:])
            rs.remove(b); feito = True; break
    for r in rs:
        nov = np.array(r['pontos'])
        mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, antigo=r['antigo'], novo=r['pontos'],
                        E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()), nota=f"contorno de {r['caixa']}" if r['caixa'] else 'traçado novo'))
    for r in _ler('PJC_caixas_movidas.json') + _ler('PJC_caixas_movidas_manual.json'):
        if r.get('status') != 'caixa deslocada': continue
        mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                        lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r.get('forma', 'r'), nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
    # geratriz de chegada ajustada (aplicar e avisar): nota com a GI nova na chegada, no último trecho do tubo; trecho sem cota no
    # projeto (CPS-DRE-021, DRE-204) fica só no modelo
    import csv
    tr = {r['trecho']: r for fn in ('PJC_fase2_DRE_trechos.csv', 'PJC_fase2_ESG_trechos.csv')
          for r in csv.DictReader(open(os.path.join(S.REL, fn), encoding='utf-8-sig'), delimiter=';')}
    g3 = {r['trecho']: r for fn in ('PJC_fase3_DRE_trechos.csv', 'PJC_fase3_ESG_trechos.csv')
          for r in csv.DictReader(open(os.path.join(S.REL, fn), encoding='utf-8-sig'), delimiter=';')}
    for a in _ler('PJC_aplicado_carregamento.json'):
        if a.get('tipo') != 'geratriz ajustada': continue
        r, f = tr.get(a['trecho']), g3.get(a['trecho'])
        if r is None or f is None or not f.get('GI_jusante'): continue
        pa = np.array([float(r['E_ini']), float(r['N_ini'])]); pb = np.array([float(r['E_fim']), float(r['N_fim'])])
        mud.append(dict(tipo='mergulho', origem='aplicar e avisar', disc=a['disc'], elemento=f"{a['disc']}:{a['trecho']}", trecho=a['trecho'], info={},
                        E=float(pb[0]), N=float(pb[1]), planta=[list(pa + (pb - pa) * s) for s in (0.6, 0.8, 1.0)], prof_topo=None,
                        nota_fixa=('CHEGADA NA %s: GI %.2f' % (r['para'], float(f['GI_jusante']) + a['dz_jusante'])).replace('.', ',')))
    # CT das caixas pelo terreno executado (pojuca/exe/pjc_exec.py troca os textos): uma marca por folha para o rever.py abrir a folha
    mud.append(dict(tipo='ct', disc='ESG', trecho='CT das caixas', elemento='ESG:CT', info={}, E=572470.0, N=8626530.0))
    mud.append(dict(tipo='ct', disc='DRE', trecho='CT das caixas', elemento='DRE:CT', info={}, E=572470.0, N=8626530.0))
    ajustar_ao_desenho(mud)
    vistas = {}
    for m in mud:
        if m['tipo'] != 'caixa deslocada': continue
        k = m['trecho']
        if k in vistas: vistas[k]['E'], vistas[k]['N'] = m['E'], m['N']; m['_dup'] = True
        else: vistas[k] = m
    mud = [m for m in mud if not m.get('_dup')]
    saida = []
    for m in mud:
        f = S.folha(m)
        if f: saida.append(dict(m, folha=f))
    fn = os.path.join(PRE, 'PJC_mudancas_UTM.json')
    json.dump({'mudancas': saida, 'coordenadas': 'UTM SIRGAS 2000 24S (m)'}, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    c = collections.Counter((m['folha'], m['tipo']) for m in saida)
    for k in sorted(c): print(k, c[k])
    pr = [m['prof_topo'] for m in saida if m['tipo'] == 'mergulho' and m.get('prof_topo') is not None]
    if pr: print('maior PROF. nas notas: %s m' % br(max(pr)))
    return fn


if __name__ == '__main__':
    main()
