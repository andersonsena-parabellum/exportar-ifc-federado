# -*- coding: utf-8 -*-
"""Jandaíra — EL-001, EL-002, AF-001 e IN-001 no padrão de executivo final:
1) preclash/executivo/rever.py (adaptador escolas/jandaira.py) planeja os comandos a partir de EXECUTIVO_R02/JAN_mudancas.json;
2) acrescenta o que é próprio da Jandaíra:
   ELE-I-13 (EL-002): na prancha o eletroduto sai da caixa ~1 m ao lado da caixa do modelo e passa 0,16 m da CX-10 da drenagem
   (fundo 144,99); o desvio do modelo é redesenhado sobre a linha da prancha (mesma ponta, vértice do desvio, mesma chegada);
3) aplica cada prancha no accoreconsole (cópia -> *_REVISADO.dwg).
Uso: python -X utf8 jan_exec.py [--so-comandos]"""
import os, sys, json, math, pickle
import numpy as np
os.environ['PRECLASH_MUDANCAS'] = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02\JAN_mudancas.json'
os.environ['PRECLASH_EXEC_SAIDA'] = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import rever, asbuilt as ab
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ['PRECLASH_EXEC_SAIDA']
TF = json.load(open(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R01\transformacoes_dwg_interno.json', encoding='utf-8'))


def D(folha, p):
    d = TF[folha]; a = math.radians(d['rot_inv_graus'])
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]) @ np.asarray(p[:2], float) + np.array(d['t_inv'])


def extra_el002(E):
    """ELE-I-13: linha C28BD da prancha -> ponta da prancha, vértice do desvio do modelo, chegada da prancha."""
    e = [x for x in E if x['h'] == 'C28BD'][0]; a, b = e['pts'][0], e['pts'][-1]; v = D('EL-002', (45.5, 96.6))
    return ['PLC\tC28BD\t0\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f' % (a[0], a[1], v[0], v[1], b[0], b[1]), 'DEL\tC28BD'], \
           ['ELE-I-13: desvio redesenhado sobre a linha da prancha (C28BD), vértice em %.2f, %.2f' % tuple(v)]


EXTRA = {'24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R01': extra_el002}

if __name__ == '__main__':
    so = '--so-comandos' in sys.argv
    rever.main('jandaira', so_comandos=True)
    R = json.load(open(os.path.join(OUT, 'JAN_executivo_R01.json'), encoding='utf-8'))
    for r in R:
        base = os.path.splitext(os.path.basename(r['dwg']))[0]; copia = os.path.join(OUT, '_copias', base + '.dwg')
        if base in EXTRA:
            linhas, log = EXTRA[base](ab.entidades(copia[:-4] + '.dxf'))
            atual = open(r['comandos'], encoding='utf-8').read().rstrip('\n').split('\n')
            dels = [l for l in atual if l.startswith('DEL')]; resto = [l for l in atual if not l.startswith('DEL')]
            novos_del = [l for l in linhas if l.startswith('DEL')]; novos = [l for l in linhas if not l.startswith('DEL')]
            open(r['comandos'], 'w', encoding='utf-8').write('\n'.join(resto + novos + dels + novos_del) + '\n')
            r['registro'] += log
            for x in log: print('   ', x)
        if so: continue
        out = rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', '_.AUDIT', '_Y', '(load "%s")' % rever.LSP, 'REVR01', '_.AUDIT', '_Y', '_.QUIT', '_Y'],
                            copia + '.rev.log', {'REV_CMD': r['comandos'], 'REV_OUT': r['saida'].replace('\\', '/')})
        print(base, '->', 'OK' if os.path.exists(r['saida']) else 'FALHOU', out[-120:])
    json.dump(R, open(os.path.join(OUT, 'JAN_executivo_R01.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
