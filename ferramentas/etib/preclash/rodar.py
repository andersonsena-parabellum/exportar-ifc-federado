# -*- coding: utf-8 -*-
"""Pré-compatibilização sem Revit: redes 3D georreferenciadas -> clash -> soluções só de profundidade -> IFC + visualizador.
Uso:  ..\\.venv\\Scripts\\python.exe -X utf8 rodar.py exemplo
A escola é um módulo em escolas/<nome>.py com carregar() e as constantes (ver escolas/exemplo.py e LEIA-ME.md)."""
import os, sys, re, csv, json, copy, importlib, time, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from preclash import clash as cl, solver as sv, desvio as dsv, estudo as etd, conexoes as cnx, parametros, verificar as vrf, costura as cst
from preclash.export_ifc import Ifc, COR

AQUI = os.path.dirname(os.path.abspath(__file__))
f2 = lambda v: '' if v is None else f'{v:.2f}'.replace('.', ',')
f3 = lambda v: '' if v is None else f'{v:.3f}'.replace('.', ',')


def gravar_csv(fn, linhas, cols):
    with open(fn, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(cols)
        for l in linhas: w.writerow([l.get(c, '') for c in cols])


def nome_b(c, ids, cx):
    if c['b'] in ids: return ids[c['b']]
    return cx[c['b']]


def _rot(i, ids, cx):
    if i in ids: return f"{ids[i]['trecho']} ({ids[i]['disc']})"
    C = cx[i]; return f"caixa {C['info'].get('nome', C['id'])} ({C['disc']} {C['info'].get('tipo')})"


def desc_conf(c, ids, cx):
    est = [i for i in (c['a'], c['b']) if i in ids and 'estimada' in ids[i]['info'].get('cota', '')]
    return f"{_rot(c['a'], ids, cx)} × {_rot(c['b'], ids, cx)} — folga {f2(c['folga'])} m" + (' · cota estimada' if est else ''), bool(est)


def linhas_conf(conf, ids, cx, ter):
    out = []
    for n, c in enumerate([c for c in conf if not c['ligacao']], 1):
        A = ids.get(c['a']) or cx[c['a']]; B = ids.get(c['b']) or cx[c['b']]
        nm = lambda x: x['trecho'] if 'trecho' in x else x['info'].get('nome', x['id'])
        txt, est = desc_conf(c, ids, cx)
        zt = float(ter.z([[c['E'], c['N']]])[0])
        out.append({'n': n, 'gravidade': c['gravidade'], 'tipo': c['tipo'], 'disc_A': A['disc'], 'trecho_A': nm(A), 'rede_A': A['rede'],
                    'disc_B': B['disc'], 'trecho_B': nm(B), 'rede_B': B['rede'],
                    'folga_m': f3(c['folga']), 'E': f3(c['E']), 'N': f3(c['N']), 'z': f3(c['z']), 'terreno': f3(zt),
                    'eixo_A': f3(c['zA']), 'eixo_B': f3(c['zB']), 'cota_estimada': 'sim' if est else '', 'descricao': txt})
    return out


def main(nome):
    t0 = time.time()
    S = importlib.import_module(f'escolas.{nome}')
    os.makedirs(S.SAIDA, exist_ok=True)
    D = S.carregar(); ter = D['terreno']; sig = S.SIGLA
    R = parametros.aplicar(S)          # parâmetros do projeto (profundidade máxima por escola) onde o adaptador não fixou
    for chave in ('elementos', 'caixas'):     # id repetido no adaptador = peça desenhada duas vezes no IFC (Revisão: PCI-AH-05/08)
        vistos, uni = set(), []
        for x in D[chave]:
            if x['id'] in vistos: continue
            vistos.add(x['id']); uni.append(x)
        if len(uni) < len(D[chave]): print(f"  aviso: {len(D[chave]) - len(uni)} {chave} com id repetido no adaptador (ficou um de cada)")
        D[chave] = uni
    todos = D['elementos']; cx = {c['id']: c for c in D['caixas']}
    print(f"{S.ESCOLA}: {len(todos)} trechos, {len(cx)} caixas")
    res = {}
    br = lambda s: re.sub('([0-9])[.]([0-9])', lambda m: m.group(1) + ',' + m.group(2), s)
    for k, cen in D['cenarios'].items():
        # o cenário pode trazer elementos e caixas próprios (ex.: hipótese de CT diferente); senão usa os da escola
        C0 = cen.get('caixas', D['caixas']); terk = cen.get('terreno', ter)   # terreno próprio do cenário (opcional)
        E = [copy.deepcopy(e) for e in cen.get('elementos', todos) if not cen['excluir'](e)]
        ids = {e['id']: e for e in E}
        antes = cl.detectar(E, C0, R, campo='pts')
        print(f"cenário {k} ({cen['nome']}): antes {cl.resumo(antes)}")
        est = etd.estudar(E, C0, R, terk) if R.get('estudo') else []      # estudo de cota das pressurizadas (sem mergulho pontual)
        if est: print(f"  depois do estudo de cota: {cl.resumo(cl.detectar(E, C0, R))}")
        final, pend, alertas = sv.resolver(E, C0, R, terk)
        final = cl.refinar_forma(final, E, C0, R); vivos = {(c['a'], c['b']) for c in final}   # forma real das peças com malha
        pend = [p_ for p_ in pend if (p_['a'], p_['b']) in vivos]
        for p in pend: p['motivo'] = br(p['motivo']); p['necessario'] = br(p['necessario'])
        sol = sv.solucoes(E, terk)
        cst.costurar(E, C0)   # pontas da mesma rede com folga viram um nó
        cst.costurar_colinear(E, C0); (cnx.ajustar_vertices(E, C0, R) if R.get('ajustar_vertices') else 0)   # vão colinear (peça que faltou) e vértice no ângulo comercial
        print(f"  depois {cl.resumo(final)} | {len(sol)} mergulhos em {len({s['elemento'] for s in sol})} trechos | {len(pend)} pendentes")
        res[k] = dict(nome=cen['nome'], E=E, ids=ids, antes=antes, final=final, pend=pend, sol=sol, alertas=alertas, caixas=C0, desvios=[], estudo=est,
                      conexoes=cnx.gerar(E, C0, R) if R.get('conexoes', True) is not False else [])
        res[k]['verificacao'] = vrf.marcar(vrf.verificar(res[k]['E'], res[k]['caixas'], terk, R), getattr(S, 'VERIFICACAO_ESPERADA', {}))   # continuidade (ponta solta, degrau, pedaço curto)
        if res[k]['verificacao']: print(f"  verificação: {vrf.resumo(res[k]['verificacao'])}")
        tabelas(S, k, res[k], terk)
    # desvios em planta (passo 2): sobre o cenário escolhido, recomeça do projeto com os traçados novos e refaz a profundidade
    for k in getattr(S, 'DESVIOS', []):
        cen = D['cenarios'][k]
        E = [copy.deepcopy(e) for e in cen.get('elementos', todos) if not cen['excluir'](e)]; C = copy.deepcopy(cen.get('caixas', D['caixas']))
        print(f"cenário {k}D: desvios em planta sobre os pendentes de {k}")
        terk = cen.get('terreno', ter)
        est = etd.estudar(E, C, R, terk, log=lambda *a: None) if R.get('estudo') else []
        dv = dsv.aplicar(E, C, res[k]['pend'], R, terk)
        final, pend, alertas = sv.resolver(E, C, R, terk)
        final = cl.refinar_forma(final, E, C, R); vivos = {(c['a'], c['b']) for c in final}
        pend = [p_ for p_ in pend if (p_['a'], p_['b']) in vivos]
        for p in pend: p['motivo'] = br(p['motivo']); p['necessario'] = br(p['necessario'])
        sol = sv.solucoes(E, terk)
        cst.costurar(E, C)   # pontas da mesma rede com folga viram um nó
        cst.costurar_colinear(E, C); (cnx.ajustar_vertices(E, C, R) if R.get('ajustar_vertices') else 0)   # vão colinear (peça que faltou) e vértice no ângulo comercial
        print(f"  depois {cl.resumo(final)} | {sum(d['status'] == 'aplicado' for d in dv)} desvios + {len(sol)} mergulhos | {len(pend)} pendentes")
        res[k + 'D'] = dict(nome=cen['nome'] + ' + desvios em planta', E=E, ids={e['id']: e for e in E}, antes=res[k]['antes'], final=final, pend=pend,
                            sol=sol, alertas=alertas, caixas=C, desvios=dv, estudo=est,
                            conexoes=cnx.gerar(E, C, R) if R.get('conexoes', True) is not False else [])
        res[k + 'D']['verificacao'] = vrf.marcar(vrf.verificar(res[k + 'D']['E'], res[k + 'D']['caixas'], terk, R), getattr(S, 'VERIFICACAO_ESPERADA', {}))   # continuidade (ponta solta, degrau, pedaço curto)
        if res[k + 'D']['verificacao']: print(f"  verificação: {vrf.resumo(res[k + 'D']['verificacao'])}")
        tabelas(S, k + 'D', res[k + 'D'], terk)
    exportar_ifc(S, D, res)
    exportar_html(S, D, res)
    resumo_md(S, D, res)
    print(f'pronto em {time.time() - t0:.0f} s -> {S.SAIDA}')


def tabelas(S, k, r, ter):
    sig = S.SIGLA; ids = r['ids']; cx = {c['id']: c for c in r['caixas']}
    from preclash import mudancas as mud           # lista das mudanças para o passo 7 (executivo/rever.py)
    mud.gravar(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_mudancas.json'), S, k, r, ter)
    cols_c = ['n', 'gravidade', 'tipo', 'disc_A', 'trecho_A', 'rede_A', 'disc_B', 'trecho_B', 'rede_B', 'folga_m', 'E', 'N', 'z', 'terreno', 'eixo_A', 'eixo_B', 'cota_estimada', 'descricao']
    if not k.endswith('D'):
        gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_conflitos_antes.csv'), linhas_conf(r['antes'], ids, cx, ter), cols_c)
    gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_conflitos_depois.csv'), linhas_conf(r['final'], ids, cx, ter), cols_c)
    ls = []
    for n, s in enumerate(sorted(r['sol'], key=lambda s: (s['disc'], s['trecho'], s['s0'])), 1):
        mot = ', '.join((ids[m]['trecho'] + f" ({ids[m]['disc']})") if m in ids else ('caixa ' + cx[m]['info'].get('nome', m)) for m in s['motivos'])
        s['txt'] = (f"{s['trecho']} ({s['disc']}): {s['modo']} de {mot}; eixo {f2(s['eixo_antes'])} → {f2(s['eixo_depois'])} (Δz {f2(s['dz'])} m) "
                    f"em {f2(s['extensao'])} m; topo a {f2(s['prof_topo_depois'])} m do terreno")
        ls.append({'n': n, 'disciplina': s['disc'], 'trecho': s['trecho'], 'solucao': s['modo'], 'obstaculos': mot, 'E': f3(s['E']), 'N': f3(s['N']),
                   'dist_inicio_trecho_m': f2(s['s0']), 'dist_fim_trecho_m': f2(s['s1']), 'extensao_m': f2(s['extensao']),
                   'eixo_antes': f3(s['eixo_antes']), 'eixo_depois': f3(s['eixo_depois']), 'dz_m': f3(s['dz']), 'terreno': f3(s['terreno']),
                   'prof_topo_antes': f2(s['prof_topo_antes']), 'prof_topo_depois': f2(s['prof_topo_depois']),
                   'nota_para_planta': (f"{'Rebaixar' if s['dz'] < 0 else 'Elevar'} {s['trecho']} {f2(abs(s['dz']))} m entre {f2(s['s0'])} e {f2(s['s1'])} m do início do trecho "
                                        f"(eixo {f2(s['eixo_depois'])}), com conexões verticais nas pontas, para {'passar sob' if s['dz'] < 0 else 'passar sobre'} {mot}.")})
    gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_solucoes.csv'), ls, list(ls[0].keys()) if ls else ['n'])
    vv = [dict(v, E=f3(v['E']), N=f3(v['N']), z=f3(v['z']), valor=f3(v['valor'])) for v in r.get('verificacao', [])]
    gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_verificacao.csv'), vv, ['tipo', 'disc', 'rede', 'trecho', 'outro', 'E', 'N', 'z', 'valor', 'o_que_fazer', 'esperado'])
    lp = []
    for n, p in enumerate(sorted(r['pend'], key=lambda p: (p.get('categoria', ''), p['folga'])), 1):
        txt, est = desc_conf(p, ids, cx)
        p['txt'] = txt + ' — ' + p['necessario']
        lp.append({'n': n, 'categoria': p.get('categoria', ''), 'gravidade': p['gravidade'], 'conflito': txt, 'motivo': p['motivo'], 'o_que_seria_preciso': p['necessario'],
                   'E': f3(p['E']), 'N': f3(p['N']), 'z': f3(p['z']), 'cota_estimada': 'sim' if est else ''})
    gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_pendentes.csv'), lp, list(lp[0].keys()) if lp else ['n'])
    if r['desvios']:
        ld = []
        for n, d in enumerate(sorted(r['desvios'], key=lambda d: (d['disc'], d['tipo'], str(d['trecho']))), 1):
            evit = ', '.join((ids[m]['trecho'] if m in ids else cx[m]['info'].get('nome', m) if m in cx else m) for m in d['evitados'])
            if d['tipo'] == 'contorno' and d['status'] == 'aplicado':
                lado = 'à esquerda' if d['desloc'] > 0 else 'à direita'
                nota = (f"Deslocar {d['trecho']} {f2(abs(d['desloc']))} m {lado} (no sentido do traçado) entre {f2(d['s0'])} e {f2(d['s1'])} m do início, "
                        f"com transições a 45°, para não atravessar {evit}.")
            elif d['tipo'] == 'caixa deslocada' and d['status'] == 'aplicado':
                nota = f"Deslocar a caixa {d['trecho']} {f2(d['desloc'])} m em planta (afastando de {evit}); eletrodutos que chegam nela acompanham."
            else:
                nota = ''
            d['txt'] = f"{d['trecho']} ({d['disc']}): {d['tipo']} — {d['status']}" + (f"; {nota}" if nota else '')
            ld.append({'n': n, 'disciplina': d['disc'], 'tipo': d['tipo'], 'trecho_ou_caixa': d['trecho'], 'status': d['status'],
                       'deslocamento_m': f2(d['desloc']) if d['desloc'] is not None else '', 'acrescimo_comprimento_m': f2(d.get('acrescimo')) if d.get('acrescimo') is not None else '',
                       'linhas_SIT_cruzadas_a_mais': d.get('linhas_sit', '') if d.get('linhas_sit') is not None else '', 'evita': evit,
                       'colisoes_com_caixas_antes': d['fixos_antes'], 'colisoes_com_caixas_depois': d['fixos_depois'],
                       'E': f3(d['E']), 'N': f3(d['N']), 'nota_para_planta': nota})
        gravar_csv(os.path.join(S.SAIDA, f'{sig}_preclash_{k}_desvios.csv'), ld, list(ld[0].keys()))


def pset_el(e, k=None, s=None):
    d = {'disciplina': e['disc'], 'rede': e['rede'], 'trecho': e['trecho'], 'tipo_rede': e['tipo'], 'DE_mm': e['de'] * 1000,
         'origem_cota': e['info'].get('cota'), 'pendente': 'sim' if e.get('pendente') else None,
         'eixo_min_projeto': float(e['pts'][:, 2].min()), 'eixo_max_projeto': float(e['pts'][:, 2].max())}
    for kk in ('DN_mm', 'material', 'GI_mont', 'GI_jus', 'classe', 'sub'):
        if e['info'].get(kk) not in (None, ''): d[kk] = e['info'][kk]
    if s:
        d['mergulhos'] = len(s); d['dz_min'] = float(min(x['dz'] for x in s)); d['eixo_min_solucao'] = float(e['pts_sol'][:, 2].min())
    return d


def exportar_ifc(S, D, res):
    # peça de linha (conexão, válvula, sensor) vinda como 'caixa' sem diâmetro: o do tubo da mesma rede mais perto (Revisão de qualidade)
    for r in res.values():
        for c in r['caixas']:
            if c['info'].get('classe_ifc') not in ('IfcPipeFitting', 'IfcValve', 'IfcSensor', 'IfcFlowInstrument', 'IfcCableCarrierFitting') or c['info'].get('DN_mm'): continue
            viz = [(float(np.min(np.hypot(e['pts_sol'][:, 0] - c['E'], e['pts_sol'][:, 1] - c['N']))), e) for e in r['E'] if e['rede'] == c['rede']]
            viz = [v for v in viz if v[0] < 0.5]
            if viz:
                e = min(viz, key=lambda v: v[0])[1]
                c['info']['DE_mm'] = round(e['de'] * 1000, 1); c['info']['DN_mm'] = e['info'].get('DN_mm')
    ter = D['terreno']
    V, F = ter.grade(S.CAIXA_OBRA, 2.0)
    kp = getattr(S, 'CENARIO_PROJETO', None) or next(iter(D['cenarios']))     # cenário do IFC "projeto" (antes das soluções)
    casos = [('projeto', 'Projeto (antes das soluções)', kp, 'pts')] + [(f'solucao_{k}', f"Solução {k} — {r['nome']}", k, 'pts_sol') for k, r in res.items()]
    for nomearq, titulo, k, campo in casos:
        r = res[k]; cx = r['caixas']
        f = Ifc(f'{S.ESCOLA} — pré-compatibilização — {titulo}', S.ORIGEM, S.EPSG, perfil=S.REGRAS.get('perfil_ifc'))
        f.terreno(V, F)
        porel = collections.defaultdict(list)
        for s in r['sol']: porel[s['elemento']].append(s)
        for e in r['E']:
            s = porel.get(e['id']) if campo == 'pts_sol' else None
            ps = pset_el(e, k, s)
            if campo == 'pts_sol' and e.get('desvio'): ps['desvio_em_planta'] = 'sim'
            if campo == 'pts_sol' and e.get('estudo'): ps['recobrimento_estudo'] = e['estudo']['cob']; ps['grupo_estudo'] = e['estudo']['grupo']
            if campo == 'pts' and 'pts_projeto' in e: ps['eixo_min_projeto'] = float(e['pts_projeto'][:, 2].min())
            f.tubo(e, e[campo], ps, S.NOMES_DISC.get(e['disc'], e['disc']))
        for c in cx: f.caixa(c, S.NOMES_DISC.get(c['disc'], c['disc']) + ' — caixas')
        pecas = r.get('conexoes', []) if campo == 'pts_sol' else (cnx.gerar(r['E'], cx, S.REGRAS, campo='pts') if S.REGRAS.get('conexoes', True) is not False else [])
        for pc in pecas: f.conexao(pc, S.NOMES_DISC.get(pc['disc'], pc['disc']) + ' — conexões')
        conf = r['antes'] if campo == 'pts' else r['final']
        for n, c in enumerate([c for c in conf if not c['ligacao']], 1):
            txt, est = desc_conf(c, r['ids'], {q['id']: q for q in cx})
            f.conflito(c, f'C{n:03d}', {'gravidade': c['gravidade'], 'descricao': txt, 'folga_m': c['folga'], 'A': c['a'], 'B': c['b'], 'cota_estimada': 'sim' if est else None})
        fn = os.path.join(S.SAIDA, f'{S.SIGLA}_preclash_{nomearq}.ifc'); f.salvar(fn)
        print('  IFC', os.path.basename(fn), f'{os.path.getsize(fn) / 1e6:.1f} MB')
    # um IFC por disciplina do contrato (o federado é o solucao_<cenário>.ifc), do cenário de entrega
    k = getattr(S, 'CENARIO_ENTREGA', None)
    if k in res:
        r = res[k]; pasta = os.path.join(S.SAIDA, f'IFC_POR_DISCIPLINA_{k}'); os.makedirs(pasta, exist_ok=True)
        porel = collections.defaultdict(list)
        for s in r['sol']: porel[s['elemento']].append(s)
        for grupo, discs in S.DISCIPLINAS_ENTREGA.items():
            f = Ifc(f'{S.ESCOLA} — {grupo} — compatibilizado (cenário {k})', S.ORIGEM, S.EPSG, perfil=S.REGRAS.get('perfil_ifc'))
            for e in r['E']:
                if e['disc'] not in discs: continue
                ps = pset_el(e, k, porel.get(e['id']))
                if e.get('desvio'): ps['desvio_em_planta'] = 'sim'
                if e.get('estudo'): ps['recobrimento_estudo'] = e['estudo']['cob']; ps['grupo_estudo'] = e['estudo']['grupo']
                f.tubo(e, e['pts_sol'], ps, S.NOMES_DISC.get(e['disc'], e['disc']))
            for c in r['caixas']:
                if c['disc'] in discs: f.caixa(c, S.NOMES_DISC.get(c['disc'], c['disc']) + ' — caixas')
            for pc in r.get('conexoes', []):
                if pc['disc'] in discs: f.conexao(pc, S.NOMES_DISC.get(pc['disc'], pc['disc']) + ' — conexões')
            fn = os.path.join(pasta, f'{S.SIGLA}_{grupo}_compatibilizado.ifc'); f.salvar(fn)
            print('  IFC', os.path.relpath(fn, S.SAIDA), f'{os.path.getsize(fn) / 1e6:.2f} MB')
        f = Ifc(f'{S.ESCOLA} — terreno provisório', S.ORIGEM, S.EPSG, perfil=S.REGRAS.get('perfil_ifc')); f.terreno(V, F)
        f.salvar(os.path.join(pasta, f'{S.SIGLA}_TERRENO.ifc'))


def exportar_html(S, D, res):
    o = np.array(S.ORIGEM, float); ter = D['terreno']
    V, F = ter.grade(S.CAIXA_OBRA, 2.0)
    zref = float(np.floor(np.nanmin(V[:, 2])))
    loc = lambda P: [[round(float(p[0] - o[0]), 3), round(float(p[1] - o[1]), 3), round(float(p[2] - zref), 3)] for p in P]
    ks = list(res.keys())
    els = []
    for e in D['elementos']:
        cen = [k for k in ks if e['id'] in res[k]['ids']]
        solp = {}
        for k in cen:
            ek = res[k]['ids'][e['id']]
            if ek.get('janelas') or ek.get('desvio') or ek.get('estudo'): solp[k] = loc(ek['pts_sol'])
        info = {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in e['info'].items() if v not in (None, '') and kk not in ('de_no', 'para_no')}
        dv = [k for k in cen if res[k]['ids'][e['id']].get('desvio')]
        if any(res[k]['ids'][e['id']].get('estudo') for k in cen):
            ee = next(res[k]['ids'][e['id']] for k in cen if res[k]['ids'][e['id']].get('estudo'))
            info['recobrimento do estudo'] = f2(ee['estudo']['cob']) + ' m'; info['grupo do estudo'] = ee['estudo']['grupo']
        els.append({'id': e['id'], 'disc': e['disc'], 'rede': e['rede'], 'trecho': e['trecho'], 'de': e['de'], 'p': loc(e['pts']), 'sol': solp or None,
                    'cen': cen, 'pend': bool(e.get('pendente')), 'info': info, 'dv': dv or None})
    caixas = [{'id': c['id'], 'disc': c['disc'], 'f': c['forma'], 'x': round(c['E'] - o[0], 3), 'y': round(c['N'] - o[1], 3), 'm': c['meia'],
               'zb': round(c['zb'] - zref, 3), 'zt': round(c['zt'] - zref, 3), 'tipo': c['info'].get('tipo'), 'cota': c['info'].get('cota'),
               **({'mx': c['mx'], 'my': c['my'], 'rot': round(c['rot'], 5)} if c['forma'] == 'r' else {})} for c in D['caixas']]
    for q in caixas:                                  # caixas deslocadas nos cenários de desvio
        for k in ks:
            c2 = next((c for c in res[k]['caixas'] if c['id'] == q['id'] and 'E0' in c), None)
            if c2: q.setdefault('mv', {})[k] = [round(c2['E'] - o[0], 3), round(c2['N'] - o[1], 3)]
    # arquitetura da SIT no nível do terreno, só dentro da obra
    b = S.CAIXA_OBRA; A = ter.arq
    m = (A[:, :, 0].min(1) > b[0]) & (A[:, :, 0].max(1) < b[2]) & (A[:, :, 1].min(1) > b[1]) & (A[:, :, 1].max(1) < b[3])
    A = A[m]; zA = ter.z(A.reshape(-1, 2)).reshape(-1, 2) + 0.03
    sit = []
    for (p, q), (za, zb) in zip(A, zA):
        if np.isnan(za) or np.isnan(zb): continue
        sit += [round(p[0] - o[0], 2), round(p[1] - o[1], 2), round(za - zref, 2), round(q[0] - o[0], 2), round(q[1] - o[1], 2), round(zb - zref, 2)]
    cxd = {c['id']: c for k in ks for c in res[k]['caixas']}

    def cf(L, ids):
        out = []
        for c in L:
            if c['ligacao']: continue
            txt, est = desc_conf(c, ids, cxd)
            out.append({'g': c['gravidade'], 'x': round(c['E'] - o[0], 3), 'y': round(c['N'] - o[1], 3), 'z': round(c['z'] - zref, 3), 'a': c['a'], 'b': c['b'], 'txt': txt,
                        'det': {'folga': f2(c['folga']) + ' m', 'E': f3(c['E']), 'N': f3(c['N']), 'cota do ponto': f3(c['z']),
                                'eixo A': f3(c['zA']), 'eixo B': f3(c['zB']) if c['zB'] is not None else 'caixa', 'cota estimada': 'sim' if est else 'não'}})
        return out
    estados, conf, sols, pend, desv, pec = [], {}, {}, {}, {}, {}
    for k in ks:
        r = res[k]
        if not k.endswith('D'): estados.append({'k': 'antes_' + k, 'cen': k, 'fase': 'antes', 'nome': f'Projeto — {r["nome"]}'})
        estados.append({'k': k, 'cen': k, 'fase': 'sol', 'nome': f'Solução — {r["nome"]}'})
        conf['antes_' + k] = cf(r['antes'], r['ids']); conf[k] = cf(r['final'], r['ids'])
        pec[k] = [[round(pc['E'] - o[0], 3), round(pc['N'] - o[1], 3), round(pc['z'] - zref, 3), pc['disc'], round(pc['de'], 3),
                   ('J' if pc['tipo'] == 'junção' else f"{pc['comercial']:g}"), 1 if pc['fora'] else 0, pc['plano'][0]] for pc in r.get('conexoes', [])]
        sols[k] = [{'modo': s['modo'], 'txt': s['txt'], 'el': s['elemento'], 'x': round(s['E'] - o[0], 3), 'y': round(s['N'] - o[1], 3), 'z': round(s['eixo_depois'] - zref, 3),
                    'det': {'Δz': f2(s['dz']) + ' m', 'extensão': f2(s['extensao']) + ' m', 'eixo antes': f3(s['eixo_antes']), 'eixo depois': f3(s['eixo_depois']),
                            'topo antes (prof.)': f2(s['prof_topo_antes']) + ' m', 'topo depois (prof.)': f2(s['prof_topo_depois']) + ' m'}} for s in r['sol']]
        desv[k] = [{'modo': d['tipo'], 'txt': d['txt'], 'el': d['elemento'], 'x': round(d['E'] - o[0], 3), 'y': round(d['N'] - o[1], 3),
                    'z': round(float(ter.z([[d['E'], d['N']]])[0]) - zref, 3), 'ok': d['status'] == 'aplicado',
                    'det': {'situação': d['status'], 'deslocamento': (f2(d['desloc']) + ' m') if d['desloc'] is not None else '',
                            'linhas da SIT cruzadas a mais': d.get('linhas_sit')}} for d in r['desvios']]
        pend[k] = [{'cat': p.get('categoria', ''), 'txt': p['txt'], 'a': p['a'], 'b': p['b'], 'x': round(p['E'] - o[0], 3), 'y': round(p['N'] - o[1], 3), 'z': round(p['z'] - zref, 3),
                    'det': {'motivo': p['motivo'], 'o que seria preciso': p['necessario']}} for p in r['pend']]
    vv = [[round(float(v[0] - o[0]), 2), round(float(v[1] - o[1]), 2), round(float(v[2] - zref), 2)] for v in V]
    # curvas de nível do terreno (0,50 m; mestras a cada 2,50 m), um pouco acima da superfície
    import matplotlib.pyplot as plt
    xs = np.arange(b[0], b[2] + 1, 1.0); ys = np.arange(b[1], b[3] + 1, 1.0); X, Y = np.meshgrid(xs, ys)
    Z = np.ma.masked_invalid(ter.z(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape))
    niveis = np.arange(np.floor(Z.min()), np.ceil(Z.max()) + 0.5, 0.5)
    fig = plt.figure(); cs = plt.contour(X, Y, Z, levels=niveis); plt.close(fig)
    curv, mest = [], []
    for nv, segs in zip(cs.levels, cs.allsegs):
        alvo = mest if abs(nv / 2.5 - round(nv / 2.5)) < 1e-6 else curv
        for sg in segs:
            for p, q in zip(sg[:-1], sg[1:]):
                alvo += [round(p[0] - o[0], 2), round(p[1] - o[1], 2), round(nv - zref + 0.02, 2), round(q[0] - o[0], 2), round(q[1] - o[1], 2), round(nv - zref + 0.02, 2)]
    ctr = [(b[0] + b[2]) / 2 - o[0], (b[1] + b[3]) / 2 - o[1], float(np.nanmean(V[:, 2])) - zref, max(b[2] - b[0], b[3] - b[1])]
    hexc = lambda c: '#%02x%02x%02x' % tuple(int(255 * x) for x in c)
    dados = {'escola': S.ESCOLA.replace('ETIB ', ''), 'sigla': S.SIGLA, 'sub': f"UTM SIRGAS 2000/24S · origem E {S.ORIGEM[0]:.0f} N {S.ORIGEM[1]:.0f} · cotas absolutas (−{zref:.0f} no 3D) · terreno: {ter.fonte}",
             'zref': zref, 'centro': ctr, 'disc': {k: {'nome': v, 'cor': hexc(COR.get(k, (.6, .6, .6)))} for k, v in S.NOMES_DISC.items()},
             'elementos': els, 'caixas': caixas, 'terreno': {'v': [x for v in vv for x in v], 'f': [int(i) for t in F for i in t]}, 'sit': sit,
             'estados': estados, 'conflitos': conf, 'solucoes': sols, 'pendentes': pend, 'desvios': desv, 'curvas': {'v': curv, 'm': mest}, 'conexoes': pec}
    tpl = open(os.path.join(AQUI, 'preclash', 'visualizador.html'), encoding='utf-8').read()
    js = json.dumps(dados, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = tpl.replace('__TITULO__', f'Pré-compatibilização {S.ESCOLA}').replace('__DADOS__', js)
    fn = os.path.join(S.SAIDA, f'{S.SIGLA}_preclash_visualizador.html')
    open(fn, 'w', encoding='utf-8').write(html)
    print('  HTML', os.path.basename(fn), f'{os.path.getsize(fn) / 1e6:.1f} MB')
    # dados da escola para o visualizador único (artifact "Pré-compatibilização ETIB": dados/<SIGLA>.json)
    fj = os.path.join(S.SAIDA, f'{S.SIGLA}.json')
    open(fj, 'w', encoding='utf-8').write(json.dumps(dados, ensure_ascii=False, separators=(',', ':')))
    print('  dados p/ o visualizador único', os.path.basename(fj), f'{os.path.getsize(fj) / 1e6:.1f} MB')
    pa = os.environ.get('PRECLASH_ARTEFATO')          # pasta para a página do visualizador único (claude.ai), opcional
    if pa:
        os.makedirs(pa, exist_ok=True)
        fa = os.path.join(pa, 'preclash_portal.html')
        open(fa, 'w', encoding='utf-8').write(pagina_portal())
        print('  página do visualizador único', fa)


def pagina_portal():
    """página do artifact único: o mesmo template, sem dados embutidos (cada escola vem de dados/<SIGLA>.json)."""
    tpl = open(os.path.join(AQUI, 'preclash', 'visualizador.html'), encoding='utf-8').read()
    return versao_artefato(tpl.replace('__TITULO__', 'Pré-compatibilização ETIB').replace('__DADOS__', 'null'))


def versao_artefato(html):
    """a página de Artifact recebe o esqueleto (doctype/head/body) na publicação: tira os do arquivo local."""
    for tag in ('<!doctype html>', '<html lang="pt-BR">', '<head>', '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">', '</head>', '<body>', '</body>', '</html>'):
        html = html.replace(tag, '', 1)
    i = html.index('</title>') + len('</title>')
    return html[:i] + '<meta name="claude:viewport-fit-sides" content="cover">' + html[i:].lstrip()


def resumo_md(S, D, res):
    L = [f'# {S.ESCOLA} — pré-compatibilização 3D sem Revit', '',
         f'Gerado por `FERRAMENTAS\\preclash\\rodar.py {S.__name__.split(".")[-1]}` em {time.strftime("%d/%m/%Y %H:%M")}. '
         'Redes da fase 2/3 da escola em 3D (diâmetro real), clash físico e por folga, e soluções testadas só de profundidade.', '',
         '## Critérios', '',
         f"- Colisão (CRÍTICA): folga < −2 mm. Folga curta (ATENÇÃO): < {f2(S.REGRAS['folga'])} m entre redes diferentes.",
         f"- Quem muda de cota, nessa ordem: {', '.join(S.REGRAS['ordem_mover'])}. ESG, pluvial e drenagem ficam fixas (cotas do projeto).",
         '- Solução = mergulho local com conexões verticais nas pontas; o traçado em planta não muda.',
         '- Limites de Δz por cruzamento: ' + ', '.join(f'{k} {f2(v)} m' for k, v in S.REGRAS['dz_max'].items()) + '; profundidade máxima do topo: ' +
         ', '.join(f'{k} {f2(v)} m' for k, v in S.REGRAS['prof_max_topo'].items()) + '.',
         '- Encontro de duas redes por gravidade na ponta de um trecho = ligação provável, não conflito.', '']
    for k, r in res.items():
        a = cl.resumo(r['antes']); d = cl.resumo(r['final'])
        L += [f'## Cenário {k}: {r["nome"]}', '',
              '| | Críticos | Atenção |', '|---|---|---|', f"| Projeto | {a['CRÍTICA']} | {a['ATENÇÃO']} |", f"| Depois das soluções | {d['CRÍTICA']} | {d['ATENÇÃO']} |", '',
              f"**{len(r['sol'])} mergulhos** em {len({s['elemento'] for s in r['sol']})} trechos:"]
        if r.get('estudo'):
            L[-1:-1] = [f"**Estudo de cota** (sem mergulho pontual): {len(r['estudo'])} grupos. " + '; '.join(
                f"{g['grupo']}: topo a {f2(g['cob'])} m" for g in r['estudo'] if g['disc'] in ('AF', 'HID')) + '.', '']
        if r.get('conexoes'):
            cc = collections.Counter(p['disc'] for p in r['conexoes'])
            L[-1:-1] = [f"**{len(r['conexoes'])} conexões** (curvas e junções): " + ', '.join(f'{d} {n}' for d, n in cc.most_common()) +
                        f"; {sum(p['fora'] for p in r['conexoes'])} com ângulo fora do comercial (conferir).", '']
        pd = collections.defaultdict(list)
        for s in r['sol']: pd[s['disc']].append(s)
        for disc, ss in pd.items():
            L.append(f"- {S.NOMES_DISC.get(disc, disc)}: {len(ss)} mergulhos em {len({s['elemento'] for s in ss})} trechos, Δz de {f2(min(s['dz'] for s in ss))} a {f2(max(s['dz'] for s in ss))} m.")
        if r['desvios']:
            ok = [d for d in r['desvios'] if d['status'] == 'aplicado']
            L += ['', f"**{len(ok)} desvios em planta testados** (mudam o traçado: executivo novo da disciplina):"]
            pdv = collections.defaultdict(list)
            for d in ok: pdv[d['disc']].append(d)
            for disc, ds in pdv.items():
                L.append(f"- {S.NOMES_DISC.get(disc, disc)}: " + '; '.join(
                    (f"{d['trecho']} {f2(abs(d['desloc']))} m para o lado" + (f" (cruza {d['linhas_sit']} linha(s) da SIT a mais: conferir)" if d.get('linhas_sit') else ''))
                    if d['tipo'] == 'contorno' else f"caixa {d['trecho']} anda {f2(d['desloc'])} m" for d in ds) + '.')
            nao = [d for d in r['desvios'] if d['status'] != 'aplicado']
            if nao: L.append('- Sem desvio que resolva: ' + ', '.join(f"{d['trecho']} ({d['disc']})" for d in nao) + '.')
        if r.get('verificacao'):
            L += ['', '**Verificação de continuidade** (conferir no 3D antes de entregar, `_verificacao.csv`): ' + ', '.join(f'{k_} {n_}' for k_, n_ in vrf.resumo(r['verificacao']).items()) + '.']
        pc = collections.Counter(p.get('categoria', '') for p in r['pend'])
        L += ['', f"**{len(r['pend'])} pendentes** (não se resolvem só com profundidade dentro dos limites):"]
        for cat, n in pc.most_common():
            L.append(f'- {cat}: {n}')
        if r['alertas']: L += ['', 'Alertas:'] + [f'- {x}' for x in r['alertas']]
        L.append('')
    L += ['## Arquivos', '',
          f'- `{S.SIGLA}_preclash_visualizador.html`: 3D no navegador (precisa de internet para o three.js). Escolha a situação, ligue/desligue disciplinas, clique nos itens.',
          f'- `{S.SIGLA}_preclash_projeto.ifc` e `{S.SIGLA}_preclash_solucao_<cenário>.ifc`: IFC4 georreferenciado (EPSG:{S.EPSG}, origem E {S.ORIGEM[0]:.0f} N {S.ORIGEM[1]:.0f}), um sistema por disciplina, conflitos como esferas.',
          f'- `{S.SIGLA}_preclash_<cenário>_conflitos_antes.csv` / `_depois.csv`, `_solucoes.csv` (com a nota para a planta) e `_pendentes.csv`.',
          f'- Cenário com "D" (ex.: `AD`): o mesmo cenário com os desvios em planta testados; `_desvios.csv` traz a nota para a planta de cada desvio.', '',
          '## Limites desta pré-compatibilização', '',
          '- Terreno provisório (platôs da terraplanagem + existente): o recobrimento real muda com o terreno do IMP as built.',
          '- Trechos por gravidade sem CF no projeto estão com cota estimada (marcados "cota estimada" nas tabelas).',
          '- Sem fundações e edificações (não baixadas); caixas das redes pressurizadas com dimensão de premissa.', '']
    open(os.path.join(S.SAIDA, f'{S.SIGLA}_preclash_LEIA-ME.md'), 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'exemplo')
