# -*- coding: utf-8 -*-
"""Jandaíra (19/10/2026 noite) — terceira passada para os contornos que nem a tolerância de 0,30 m achou (o eletroduto da prancha
fica até ~1 m do modelo): acha a linha da prancha mais parecida com o trecho do modelo (até 1,2 m), alinha o contorno do modelo
nela pela translação mediana e troca só o pedaço do contorno (pontas da prancha mantidas), copiando layer/tipo/cor da linha (PLC).
Uso: python -X utf8 jan_contornos3.py"""
import os, sys, json, math, shutil
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC'
M = json.load(open(os.path.join(OUT, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
# contornos que o rever.py não achou na prancha (registro da 1ª passada) e o estado de partida (a 1ª passada guardada em _copias)
_INV = {os.path.splitext(os.path.basename(v))[0]: k for k, v in S._DWG.items()}
FALTAM = {}
for r in json.load(open(os.path.join(OUT, 'JAN_executivo_AD.json'), encoding='utf-8')):
    base_ = os.path.splitext(os.path.basename(r['dwg']))[0]
    tr = [l.split(':')[0].strip() for l in r['registro'] if 'não achado' in l and 'traçado' in l]
    if tr and base_ in _INV and _INV[base_] not in ('DRE-001', 'ESG-001', 'CPS-DRE-001'): FALTAM[_INV[base_]] = tr   # gravidade: jan_grav_exec.py
ORIGEM = {k: '_REVISADO_p1.dwg' for k in FALTAM}
for k in FALTAM:
    b_ = os.path.splitext(os.path.basename(S._DWG[k]))[0]; p1 = os.path.join(OUT, '_copias', b_ + '_REVISADO_p1.dwg')
    if not os.path.exists(p1): shutil.copy2(os.path.join(OUT, b_ + '_REVISADO.dwg'), p1)
print('contornos a refazer:', FALTAM)


def amostra(P, passo=0.25):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / passo))); out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def proj(P, q):
    """ponto mais próximo de q na polilinha P: (dist, ponto, abscissa)."""
    best = (9e9, None, 0.0); s = 0.0
    for a, b in zip(P[:-1], P[1:]):
        d = b - a; L = np.hypot(*d)
        u = 0.0 if L < 1e-9 else float(np.clip(np.dot(q - a, d) / L ** 2, 0, 1)); c = a + d * u; dist = np.hypot(*(q - c))
        if dist < best[0]: best = (dist, c, s + u * L)
        s += L
    return best


for folha, trechos in FALTAM.items():
    dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
    rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda P: np.array([R.T @ (np.asarray(p[:2], float) - np.array(t)) for p in P])
    rev = os.path.join(OUT, base + '_REVISADO.dwg'); src = os.path.join(OUT, '_copias', base + ORIGEM[folha]); dxf = src[:-4] + '.dxf'
    if not os.path.exists(dxf) or os.path.getmtime(dxf) < os.path.getmtime(src):
        rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                      src + '.dxf.log', {'DXF_OUT': dxf.replace(chr(92), '/')})
    E = ab.entidades(dxf); L = [e for e in E if 'pts' in e and len(e['pts']) >= 2 and not e.get('fechada') and e['typ'] in ('LINE', 'LWPOLYLINE')]
    cmds, log, atual = [], [], {}          # atual: polilinha já emendada por handle (dois contornos na mesma linha da prancha)
    for m in M:
        if m['folha'] != folha or m['tipo'] != 'contorno' or m['trecho'] not in trechos: continue
        A = loc(m['antigo']); N = loc(m['novo']); As = amostra(A)
        lo, hi = As.min(0) - 1.5, As.max(0) + 1.5
        best = None
        for e in L:
            if not (np.all(e['pts'].max(0) >= lo) and np.all(e['pts'].min(0) <= hi)): continue
            sc = float(np.percentile([proj(e['pts'], q)[0] for q in As[::4]], 70))
            if best is None or sc < best[0]: best = (sc, e)
        if best is None or best[0] > 1.2: log.append(f"{m['trecho']}: linha da prancha não achada"); continue
        sc, e = best; P = np.asarray(atual.get(e['h'], e['pts']), float)
        tr = np.median(np.array([proj(P, q)[1] - q for q in As[::2]]), 0); Nd = N + tr
        ix = [k for k in range(1, len(Nd) - 1) if proj(A + tr, Nd[k])[0] > 0.05]
        if not ix: log.append(f"{m['trecho']}: contorno sem vértice fora da linha"); continue
        # entrada e saída projetadas na linha da prancha + os cantos do contorno (alinhados pela translação)
        fora = [proj(P, Nd[ix[0] - 1])[1]] + list(Nd[ix[0]:ix[-1] + 1]) + [proj(P, Nd[ix[-1] + 1])[1]]
        s0 = proj(P, fora[0])[2]; s1 = proj(P, fora[-1])[2]
        if s0 > s1: fora = fora[::-1]; s0, s1 = s1, s0
        S_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
        novo = [p for p, s in zip(P, S_) if s < s0 - 0.01] + fora + [p for p, s in zip(P, S_) if s > s1 + 0.01]
        atual[e['h']] = np.array(novo, float)
        log.append(f"{m['trecho']}: contorno sobre a linha {e['h']} da prancha (a {sc:.2f} m do modelo), {len(ix)} canto(s)")
    for h, P in atual.items():
        cmds += ['PLC\t%s\t0\t' % h + '\t'.join(f'{p[0]:.4f}\t{p[1]:.4f}' for p in P), 'DEL\t%s' % h]
    print(folha); [print('   ', x) for x in log]
    if not cmds: continue
    dels = [l for l in cmds if l.startswith('DEL')]; resto = [l for l in cmds if not l.startswith('DEL')]
    cmd = os.path.join(OUT, f'_cmd_{base}_p3.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(resto + dels) + '\n')
    if os.path.exists(rev): os.remove(rev)
    out = rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', '(load "%s")' % rever.LSP, 'REVR01', '_.QUIT', '_Y'], src + '.p3.log',
                        {'REV_CMD': cmd, 'REV_OUT': rev.replace(chr(92), '/')})
    print('   ->', 'OK' if os.path.exists(rev) else 'FALHOU', out[-120:])
    if not os.path.exists(rev): shutil.copy2(src, rev)
