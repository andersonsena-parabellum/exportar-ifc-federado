# -*- coding: utf-8 -*-
"""Jandaíra (20/10/2026) — caixas de passagem deslocadas que o rever.py não achou na prancha ("nada a mover"/"NÃO achada"): na
prancha a caixa é o vértice onde os eletrodutos se encontram (com o texto "Cx. 80x80 cm" ao lado), até ~1,5 m da posição do modelo.
Acha o vértice comum a 2 ou mais linhas mais perto da posição antiga do modelo (até 1,5 m), move esse vértice nas linhas que chegam
nele e o texto "Cx" mais próximo (até 2 m), sobre a *_REVISADO.dwg (depois do rever.py e dos contornos).
Uso: python -X utf8 jan_caixas_exec.py   (JAN_EXEC_OUT = pasta da revisão)"""
import os, sys, json, math, shutil, re
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC'
M = json.load(open(os.path.join(OUT, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
_INV = {os.path.splitext(os.path.basename(v))[0]: k for k, v in S._DWG.items()}
falta = {}
for r in json.load(open(os.path.join(OUT, 'JAN_executivo_AD.json'), encoding='utf-8')):
    b = os.path.splitext(os.path.basename(r['dwg']))[0]
    nomes = [l.split(':')[0].strip() for l in r['registro'] if 'nada a mover' in l or 'NÃO achada' in l]
    if nomes and b in _INV: falta[_INV[b]] = nomes
print('caixas a mover à mão:', falta)
for folha, nomes in falta.items():
    dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
    rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda p: R.T @ (np.asarray(p[:2], float) - np.array(t))
    rev = os.path.join(OUT, base + '_REVISADO.dwg'); src = os.path.join(OUT, '_copias', base + '_REVISADO_antes_caixas.dwg')
    shutil.copy2(rev, src)
    rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                  src + '.dxf.log', {'DXF_OUT': src[:-4].replace(chr(92), '/') + '.dxf'})
    E = ab.entidades(src[:-4] + '.dxf')
    linhas = [e for e in E if e['typ'] in ('LINE', 'LWPOLYLINE') and not e.get('fechada')]
    textos = [e for e in E if e['typ'] in ('TEXT', 'MTEXT')]
    L, log, usados = [], [], set()
    for m in M:
        if m['folha'] != folha or m['tipo'] != 'caixa deslocada' or m['trecho'] not in nomes: continue
        de = loc(m['de']); v = loc((m['E'], m['N'])) - de
        # vértices de linha perto da posição antiga, agrupados (5 cm): o nó com mais linhas e mais perto
        V = [(e, k, p) for e in linhas for k, p in enumerate(e['pts']) if np.hypot(*(p - de)) < 1.5]
        grupos = []
        for e, k, p in V:
            g = next((g for g in grupos if np.hypot(*(g['p'] - p)) < 0.05), None)
            if g: g['v'].append((e, k))
            else: grupos.append({'p': p, 'v': [(e, k)]})
        grupos = [g for g in grupos if len({id(e) for e, _ in g['v']}) >= 2]
        if not grupos: log.append(f"{m['trecho']}: nenhum vértice de eletroduto até 1,5 m (fica só no modelo)"); continue
        g = min(grupos, key=lambda g: np.hypot(*(g['p'] - de)) - 0.2 * len(g['v']))
        for e, k in g['v']:
            if (e['h'], k) in usados: continue
            usados.add((e['h'], k)); kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1); q = e['pts'][k] + v
            L.append(f"VTX\t{e['h']}\t{kk}\t{q[0]:.4f}\t{q[1]:.4f}")
        tx = [x for x in textos if re.match(r'\s*\\?[{]?\s*CX', str(x.get('txt', '')), re.I) and np.hypot(*(x['p'] - g['p'])) < 2.0]
        if tx:
            x = min(tx, key=lambda x: np.hypot(*(x['p'] - g['p']))); L.append(f"MV\t{x['h']}\t{v[0]:.4f}\t{v[1]:.4f}")
        log.append(f"{m['trecho']}: vértice a {np.hypot(*(g['p'] - de)):.2f} m do modelo, {len(g['v'])} ponta(s) movida(s) {np.hypot(*v):.2f} m" + (', texto junto' if tx else ''))
    print(folha); [print('   ', x) for x in log]
    if not L: continue
    cmd = os.path.join(OUT, f'_cmd_{base}_caixas.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    os.remove(rev)
    out = rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', '(load "%s")' % rever.LSP, 'REVR01', '_.QUIT', '_Y'], src + '.caixas.log',
                        {'REV_CMD': cmd, 'REV_OUT': rev.replace(chr(92), '/')})
    print('   ->', 'OK' if os.path.exists(rev) else 'FALHOU', out[-120:])
    if not os.path.exists(rev): shutil.copy2(src, rev)
