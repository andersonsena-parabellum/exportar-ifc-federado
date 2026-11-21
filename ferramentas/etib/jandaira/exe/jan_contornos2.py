# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — segunda passada nas pranchas de elétrica e incêndio para os contornos que o rever.py
não achou na prancha (o eletroduto do modelo fica 10 a 30 cm fora da linha da prancha): procura a linha com tolerância de 0,30 m
e pontas prolongadas 3 m, sobre a *_REVISADO.dwg da primeira passada.
ELE-I-13 (EL-002): a linha da prancha (C28BD) passa ~1 m ao lado do modelo; o contorno é redesenhado sobre ela: ponta da prancha,
vértices do contorno do modelo em volta da CX-10, chegada da prancha (como na R02 da tarde).
Uso: python -X utf8 jan_contornos2.py"""
import os, sys, json, math, shutil
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC'
M = json.load(open(os.path.join(OUT, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas']
FALTAM = {'EL-001': ['ELE-F-08'], 'EL-002': ['ELE-I-06', 'ELE-I-15', 'ELE-I-19'], 'IN-001': ['PCI-EL-03', 'PCI-EL-04']}
ESPECIAL = {'EL-002': ['ELE-I-13']}

for folha in ('EL-001', 'EL-002', 'IN-001'):
    dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
    rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda P: np.array([R.T @ (np.asarray(p[:2], float) - np.array(t)) for p in P])
    rev = os.path.join(OUT, base + '_REVISADO.dwg'); E = ab.entidades(rev[:-4] + '.dxf')
    Pl = ab.Plano(E, tol=0.30, ext=3.0)
    for m in M:
        if m['folha'] == folha and m['tipo'] == 'contorno' and m['trecho'] in FALTAM.get(folha, []):
            Pl.contorno(loc(m['antigo']), loc(m['novo']), m['trecho'])
    for m in M:
        if m['folha'] == folha and m['tipo'] == 'contorno' and m['trecho'] in ESPECIAL.get(folha, []):
            e = next((x for x in E if x['h'] == 'C28BD'), None)
            if e is None: Pl.log.append('ELE-I-13: linha C28BD não achada'); continue
            A, B = e['pts'][0], e['pts'][-1]; N = loc(m['novo'])
            # vértices do contorno do modelo (os que saem da reta do modelo), na ordem da linha da prancha
            O = loc(m['antigo']); d = O[-1] - O[0]; d = d / np.hypot(*d)
            fora = [p for p in N[1:-1] if abs(np.cross(d, p - O[0])) > 0.05]
            if np.hypot(*(fora[0] - A)) > np.hypot(*(fora[-1] - A)): fora = fora[::-1]
            pts = [A] + fora + [B]
            Pl.L += ['PLC\tC28BD\t0\t' + '\t'.join(f'{p[0]:.4f}\t{p[1]:.4f}' for p in pts), 'DEL\tC28BD']
            Pl.log.append(f'ELE-I-13: contorno da CX-10 redesenhado sobre a linha da prancha (C28BD), {len(fora)} vértice(s)')
    print(folha, len(Pl.L), 'comandos'); [print('   ', x) for x in Pl.log]
    if not Pl.L: continue
    dels = [l for l in Pl.L if l.startswith('DEL')]; resto = [l for l in Pl.L if not l.startswith('DEL')]
    cmd = os.path.join(OUT, f'_cmd_{base}_p2.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(resto + dels) + '\n')
    p1 = os.path.join(OUT, '_copias', base + '_REVISADO_p1.dwg'); shutil.move(rev, p1)
    out = rever.console(p1, ['SECURELOAD 0', 'FILEDIA 0', '(load "%s")' % rever.LSP, 'REVR01', '_.QUIT', '_Y'], p1 + '.p2.log',
                        {'REV_CMD': cmd, 'REV_OUT': rev.replace('\\', '/')})
    print('   ->', 'OK' if os.path.exists(rev) else 'FALHOU', out[-150:])
    if not os.path.exists(rev): shutil.copy2(p1, rev)
