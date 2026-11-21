# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — DRE-001 e ESG-001: caixas e junções deslocadas (jan_ajustes.ajustar) desenhadas como
um ESTICAR do AutoCAD em volta de cada nó: a prancha desenha o tubo em linha dupla com as conexões em bloco, então o contorno da
ferramenta (uma linha só) deixava uma das paredes para trás. Em volta do nó antigo (raio 0,45 m na junção; meio lado + 0,25 m na caixa):
  - bloco (conexão, caixa), polilinha fechada e hachura com o centro dentro: andam;
  - vértice de linha/polilinha dentro: anda (as duas paredes do tubo esticam juntas);
  - na caixa, os textos dela (CT/CF/CS/CE e o nome) andam junto.
Aplica no accoreconsole sobre a cópia original -> <prancha>_REVISADO.dwg (substitui a do rever.py para essas duas folhas).
Uso: python -X utf8 jan_grav_exec.py"""
import os, sys, json, math, shutil
import numpy as np
os.environ['PRECLASH_UTM'] = '1'
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
import asbuilt as ab, rever
from escolas import jandaira as S
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC'
F = json.load(open(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02\JAN_ajustes_gravidade_final.json', encoding='utf-8'))
TXT_CAIXA = ('CX', 'PV', 'CI', 'CE', 'CG', 'CT', 'CF', 'CS', 'PI', 'CES', 'TQ')


def nos(disc):
    """(de, para, raio, nome, é_caixa) em UTM; caixas primeiro, junções que não coincidem com caixa depois."""
    out = []
    for c in F['caixas']:
        if c['disc'] == disc: out.append((np.array(c['de'][:2]), np.array([c['E'], c['N']]), max(c['lado'], c['lado_y']) / 2 + 0.25, c['caixa'], True))
    for t in F['tubos']:
        if t['disc'] != disc: continue
        for k in (0, -1):
            a, b = np.array(t['antigo'][k]), np.array(t['novo'][k])
            if np.hypot(*(b - a)) < 0.005 or any(np.hypot(*(a - o[0])) < 0.5 for o in out): continue
            out.append((a, b, 0.45, f'junção de {t["trecho"]}', False))
    return out


def plano(folha, disc):
    dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
    rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda p: R.T @ (np.asarray(p, float) - np.array(t))
    E = ab.entidades(os.path.join(OUT, '_copias', base + '.dxf'))
    L, log, feitos, vtx = [], [], set(), set()
    for de_u, para_u, r, nome, cx in nos(disc):
        de = loc(de_u); v = loc(para_u) - de; n_b = n_v = n_t = 0
        for e in E:
            if e['h'] in feitos: continue
            if e['typ'] in ('INSERT', 'HATCH') or (e['typ'] == 'LWPOLYLINE' and e.get('fechada')):
                c = e['pts'].mean(0) if 'pts' in e and e['typ'] == 'LWPOLYLINE' else e['p']
                if np.hypot(*(c - de)) < r and (e['typ'] != 'LWPOLYLINE' or np.ptp(e['pts'], axis=0).max() < 2 * r + 0.3):
                    L.append(f"MV\t{e['h']}\t{v[0]:.4f}\t{v[1]:.4f}"); feitos.add(e['h']); n_b += 1
            elif e['typ'] in ('TEXT', 'MTEXT'):
                if cx and np.hypot(*(e['p'] - de)) < r + 1.0 and str(e.get('txt', '')).strip().upper().lstrip('\\{').startswith(TXT_CAIXA):
                    L.append(f"MV\t{e['h']}\t{v[0]:.4f}\t{v[1]:.4f}"); feitos.add(e['h']); n_t += 1
            elif 'pts' in e:
                for k, p in enumerate(e['pts']):
                    if np.hypot(*(p - de)) < r and (e['h'], k) not in vtx:
                        kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1); q = p + v
                        L.append(f"VTX\t{e['h']}\t{kk}\t{q[0]:.4f}\t{q[1]:.4f}"); vtx.add((e['h'], k)); n_v += 1
        log.append(f'{nome}: {np.hypot(*v):.2f} m; {n_b} bloco(s)/hachura(s), {n_v} vértice(s) de linha' + (f', {n_t} texto(s)' if cx else ''))
    # notas "PROF. x,xx m" das junções que mudaram de cota (jan_mudancas_ifc.py), no estilo das notas da prancha
    Mj = [m for m in json.load(open(os.path.join(OUT, 'JAN_mudancas_UTM.json'), encoding='utf-8'))['mudancas'] if m['folha'] == folha and m['tipo'] == 'mergulho']
    if Mj:
        Pl = ab.Plano(E, tol=getattr(S, 'EXECUTIVO_TOL', 0.06)); Pl.alt_nota = getattr(S, 'EXECUTIVO_NOTA_ALT', None)
        for m in Mj:
            Pl.nota(np.array([loc(p) for p in m['planta']]), ab.texto_profundidade(m), m['trecho'])
        L += Pl.L; log += Pl.log
    # caixas com cota nova (jan_ajustes2.cota_grav): CF, CS e CE sobem/descem dz e a profundidade (P) muda ao contrário
    import re
    dzs = json.load(open(os.path.join(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02', 'JAN_cota_grav_caixas.json'), encoding='utf-8'))         if os.path.exists(os.path.join(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02', 'JAN_cota_grav_caixas.json')) else {}
    ROT = json.load(open(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02\rotulos_gravidade.json', encoding='utf-8')).get(disc, {})
    porh = {e['h']: e for e in E if e['typ'] in ('TEXT', 'MTEXT')}
    for nome, dz in dzs.items():
        for chave, lst in ROT.get(nome, {}).items():
            if chave == 'CT': continue
            for val, _, h in lst:
                e = porh.get(h)
                if not e: continue
                novo_v = val - dz if chave == 'P' else val + dz
                fmt = ('%05.2f' % novo_v) if chave == 'P' else ('%.2f' % novo_v)
                txt = re.sub(r'\d+[.,]\d+', fmt, str(e['txt']), count=1)
                L.append(f"ST	{h}	{txt}"); log.append(f'{nome}: {chave} {val:.2f} -> {novo_v:.2f}')
    return base, L, log


def postes(folha='EL-002'):
    """postes deslocados (jan_ajustes2.mover_postes): o bloco do poste e as pontas dos eletrodutos num raio de 0,5 m andam, sobre a
    *_REVISADO.dwg da prancha (depois do rever.py e dos contornos)."""
    reg = json.load(open(r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\IFC_R02\JAN_postes_registro.json', encoding='utf-8'))
    if not reg: return
    dwg = S._DWG[folha]; base = os.path.splitext(os.path.basename(dwg))[0]
    rot, t = S.TRANSF_DWG[dwg]; a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = lambda p: R.T @ (np.asarray(p, float) - np.array(t))
    rev = os.path.join(OUT, base + '_REVISADO.dwg'); src = os.path.join(OUT, '_copias', base + '_REVISADO_antes_postes.dwg')
    shutil.copy2(rev, src)
    rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp")', 'DXFX', '_.QUIT', '_Y'],
                  src + '.dxf.log', {'DXF_OUT': src[:-4].replace(chr(92), '/') + '.dxf'})
    E = ab.entidades(src[:-4] + '.dxf'); L, log, vtx = [], [], set()
    for r in reg:
        de = loc(r['de']); v = loc((r['E'], r['N'])) - de; nb = nv = 0
        for e in E:
            if e['typ'] == 'INSERT' and np.hypot(*(e['p'] - de)) < 0.5:
                L.append(f"MV	{e['h']}	{v[0]:.4f}	{v[1]:.4f}"); nb += 1
            elif 'pts' in e and e['typ'] in ('LINE', 'LWPOLYLINE') and not e.get('fechada'):
                for k, p in enumerate(e['pts']):
                    if np.hypot(*(p - de)) < 0.5 and (e['h'], k) not in vtx:
                        kk = k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1); q = p + v
                        L.append(f"VTX	{e['h']}	{kk}	{q[0]:.4f}	{q[1]:.4f}"); vtx.add((e['h'], k)); nv += 1
        log.append(f"poste {r['poste']}: {np.hypot(*v):.2f} m; {nb} bloco(s), {nv} ponta(s) de eletroduto")
    cmd = os.path.join(OUT, f'_cmd_{base}_postes.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(base, len(L), 'comandos'); [print('   ', x) for x in log]
    os.remove(rev)
    out = rever.console(src, ['SECURELOAD 0', 'FILEDIA 0', '(load "%s")' % rever.LSP, 'REVR01', '_.QUIT', '_Y'], src + '.postes.log',
                        {'REV_CMD': cmd, 'REV_OUT': rev.replace(chr(92), '/')})
    print('   ->', 'OK' if os.path.exists(rev) else 'FALHOU', out[-150:])
    if not os.path.exists(rev): shutil.copy2(src, rev)


if __name__ == '__main__':
    if '--postes' in sys.argv: postes(); sys.exit()
    for folha, disc in (('DRE-001', 'DRE'), ('ESG-001', 'ESG')):
        base, L, log = plano(folha, disc)
        cmd = os.path.join(OUT, f'_cmd_{base}_grav.txt'); open(cmd, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
        print(base, len(L), 'comandos'); [print('   ', x) for x in log]
        # notas de profundidade não se aplicam (gravidade): a revisada sai só com o esticar
        copia = os.path.join(OUT, '_copias', base + '.dwg'); dst = os.path.join(OUT, base + '_REVISADO.dwg')
        if os.path.exists(dst): os.replace(dst, os.path.join(OUT, '_copias', base + '_REVISADO_rever.dwg'))
        out = rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', '_.AUDIT', '_Y', '(load "%s")' % rever.LSP, 'REVR01', '_.AUDIT', '_Y', '_.QUIT', '_Y'],
                            copia + '.grav.log', {'REV_CMD': cmd, 'REV_OUT': dst.replace('\\', '/')})
        print('   ->', 'OK' if os.path.exists(dst) else 'FALHOU', out[-150:])
