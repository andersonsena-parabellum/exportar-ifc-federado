# -*- coding: utf-8 -*-
"""Passo 7 do preclash: as pranchas executivas no padrão de EXECUTIVO FINAL (as built), numa cópia do DWG de projeto.
Padrão (19/10/2026, pedido do dono do projeto): a prancha vai para o campo, então
  - mudança de traçado: o trecho antigo sai e o novo entra na MESMA entidade/layer/tipo de linha/cor; as tags de diâmetro
    e de fluxo junto do trecho acompanham (nada de nuvem, rascunho ou traçado "substituído");
  - caixa deslocada: o bloco/contorno e o texto dela andam; as pontas das linhas que chegam nela acompanham;
  - mergulho (só profundidade): nota curta no estilo do texto mais próximo da prancha ("ELETRODUTO A 1,40 m DE PROFUNDIDADE");
  - nenhuma menção a revisão interna, pré-compatibilização ou ao processo.
Fluxo por DWG: cópia -> DXF da cópia (handles) -> asbuilt.py planeja -> revisao.lsp aplica no accoreconsole (um por vez,
esperando os das outras threads) -> <nome>_REVISADO.dwg. O modo antigo (layers <REV>-NOVO/SUBSTITUIDO/NUVEM/NOTA) fica em --rascunho.

O adaptador da escola define:
  EXECUTIVO = {'ELE': 'PROJETO_ORIGINAL/.../EL-001.dwg', ...}           disciplina -> DWG (caminho relativo a BASE), ou
  def executivo_dwg(m): return 'PROJETO_ORIGINAL/...dwg' | None          para escolher pelo trecho/folha (m = mudança)
  TRANSF_JSON (opcional; padrão BASE/CAD_GEORREFERENCIADO/transformacoes_local_para_UTM.json, lista 'arquivos' com
  arquivo_original, rot_deg, t) ou TRANSF_DWG = {'caminho.dwg': (rot_deg, (tx, ty))}
  EXECUTIVO_TOL (tolerância para achar o traçado original na prancha, m, padrão 0,06).
  EXECUTIVO_EXT (opcional, m): prolonga as pontas do traçado do modelo ao procurar a linha na prancha (caixa do modelo fora do vértice da prancha).
  EXECUTIVO_CAIXA_SEM_SIMBOLO (opcional): a prancha marca a caixa só com texto no vértice; caixa deslocada move o vértice e o texto.
  EXECUTIVO_NOTA_ALT (opcional, (min, max) m): altura dos textos que servem de molde para a nota de profundidade.
  EXECUTIVO_FAMILIA (opcional): função elemento -> chave; mergulhos da mesma família a menos de 4 m viram uma nota só.
  EXECUTIVO_NOTA_RAIO (opcional, m, padrão 15): no mesmo grupo de profundidade, outra nota só a mais disso da anterior.
  Notas de profundidade (20/10/2026): uma por trecho — ver asbuilt.agrupar_notas; ao lado da etiqueta do trecho quando houver.
Uso: ..\\..\\.venv\\Scripts\\python.exe -X utf8 rever.py <escola> [cenário] [--so-comandos] [--rascunho]
Prévia (PDCA A3, 22/10/2026): depois de plotar os PDF com o carimbo da construtora,
     rever.py --miniaturas <pasta dos PDF revisados> --origem <_SUPERADAS do CDE> [<PROJETO_ORIGINAL>] [--saida PASTA]
grava uma imagem ANTES | DEPOIS por folha (miniaturas.py), que vai ao dono do projeto junto com o "pronto para envio"."""
import os, sys, json, math, shutil, subprocess, importlib, collections
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.stdout.reconfigure(encoding='utf-8')
RUN = r'D:\Projeto Modelagem\FERRAMENTAS\georef_dxf\run_one.ps1'
LSP = os.path.join(AQUI, 'revisao.lsp').replace('\\', '/')


def esperar_console(max_min=30):
    """RAM limitada: um accoreconsole por vez na máquina — espera os das outras threads terminarem."""
    import time
    for _ in range(max_min * 6):
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq accoreconsole.exe', '/NH'], capture_output=True, text=True, encoding='mbcs', errors='replace')
        if 'accoreconsole.exe' not in r.stdout.lower(): return
        time.sleep(10)
    raise RuntimeError('outro accoreconsole ocupado há muito tempo')


def console_nuvem(dwg, linhas, log, env):
    """o mesmo trabalho do accoreconsole, na nuvem (Linux): ODA File Converter + ezdxf, e o PDF pelo render_pdf_nuvem.py.
    Entende os roteiros usados aqui e no carimbo_qg.py: DXFX (DXF da cópia), REVR01 (revisao.lsp), CARQGAPL (aplicar.lsp) e o
    -PLOT do carqg_pdf_*.lsp."""
    import re, tempfile
    N = getattr(sys.modules.get('sitecustomize'), 'N', lambda x: x)
    E = {k: N(v) for k, v in env.items()}; dwg = N(dwg); feito = []
    import revisao_ezdxf as rz
    if 'DXFX' in linhas:
        rz.oda(dwg, E['DXF_OUT']); feito.append('DXFX')
    if 'REVR01' in linhas:
        src = dwg if os.path.exists(dwg) or not os.path.exists(dwg[:-4] + '.dxf') else dwg[:-4] + '.dxf'   # o DXF da cópia tem os mesmos handles
        rz.revisar(src, E['REV_CMD'], E['REV_OUT']); feito.append('REVR01')
    if 'CARQGAPL' in linhas:
        import carimbo_ezdxf as cz
        doc = rz.ler(dwg); n, faltou = cz.aplicar(doc, E['CARQG_CMD'])
        dxf = os.path.join(tempfile.mkdtemp(), os.path.basename(dwg)[:-4] + '.dxf'); doc.saveas(dxf); rz.oda(dxf, dwg)
        feito.append(f'CARQG_OK apagados={n}' + (f' faltou={faltou}' if faltou else ''))
        pdf_nuvem = os.environ.get('ETIB_PDF_NUVEM') or next((x for x in (os.path.normpath(os.path.join(AQUI, '..', '..', '..', 'pranchas_pdf')),
                                                                          '/mnt/project-files/ferramentas_nuvem/pranchas_pdf') if os.path.isdir(x)), None)
        for l in linhas:
            m = re.match(r'\(load "(.+carqg_pdf_.+\.lsp)"\)', l)
            if not m: continue
            lsp = open(N(m.group(1)), encoding='ascii').read()
            for lay, pdf in re.findall(r'"_\.-PLOT" "_Y" "([^"]+)" .*?"([^"]+\.pdf)"', lsp):
                r = subprocess.run([sys.executable, '-I', 'render_pdf_nuvem.py', dxf, N(pdf)], cwd=pdf_nuvem, capture_output=True, text=True,
                                   env=dict(os.environ, LAY=lay, CTB='prancha/acad.ctb'))
                feito.append(f'PDF {os.path.basename(N(pdf))}: ' + ('OK' if r.returncode == 0 else 'FALHOU ' + r.stderr[-300:]))
    if not feito: raise RuntimeError('roteiro do accoreconsole sem equivalente na nuvem: ' + ' | '.join(linhas))
    open(N(log), 'w', encoding='utf-16-le').write('\n'.join(feito) + '\n')
    return '\n'.join(feito)


def console(dwg, linhas, log, env):
    """roda UM accoreconsole na cópia, esperando os das outras threads (na nuvem: console_nuvem)."""
    if os.name != 'nt': return console_nuvem(dwg, linhas, log, env)
    esperar_console()
    q = lambda s: "'" + s.replace("'", "''") + "'"
    ps = ('& ' + q(RUN) + ' -Dwg ' + q(dwg) + ' -ScrLines @(' + ','.join(q(x) for x in linhas) + ') -Log ' + q(log) + ' -TimeoutSec 900 -EnvVars @{'
          + ';'.join(f'{k}={q(v)}' for k, v in env.items()) + '}')
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], capture_output=True, text=True, encoding='mbcs', errors='replace')
    return ((r.stdout or '') + (r.stderr or '')).strip()


def transformacoes(S):
    if getattr(S, 'TRANSF_DWG', None):
        return {os.path.normcase(os.path.normpath(k)): (float(v[0]), np.array(v[1], float)) for k, v in S.TRANSF_DWG.items()}
    fn = getattr(S, 'TRANSF_JSON', os.path.join(S.BASE, 'CAD_GEORREFERENCIADO', 'transformacoes_local_para_UTM.json'))
    J = json.load(open(fn, encoding='utf-8'))
    arqs = J['arquivos'].values() if isinstance(J['arquivos'], dict) else J['arquivos']
    return {os.path.normcase(os.path.normpath(a['arquivo_original'])): (float(a['rot_deg']), np.array(a['t'], float)) for a in arqs}


class Folha:
    def __init__(self, dwg, rot_deg, t, h, rev):
        a = math.radians(rot_deg)
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        self.Ri, self.t, self.dwg, self.h, self.rev = R.T, t, dwg, h, rev
        self.L, self.notas, self.pts = [], [], []

    def P(self, p):
        q = self.Ri @ (np.asarray(p[:2], float) - self.t); self.pts.append(q); return q

    def pl(self, pts, lay, fechado=False):
        Q = [self.P(p) for p in pts]
        self.L.append(f"PL\t{self.rev}-{lay}\t{1 if fechado else 0}\t" + '\t'.join(f'{q[0]:.4f}\t{q[1]:.4f}' for q in Q))

    def caixa(self, c, lx, ly, rot, lay):
        u = np.array([math.cos(rot), math.sin(rot)]); v = np.array([-u[1], u[0]]); c = np.asarray(c, float)
        self.pl([c + su * u * lx / 2 + sv * v * ly / 2 for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))], lay, True)

    def nota(self, txt, p, r):
        n = len(self.notas) + 1; self.notas.append(txt); q = self.P(p)
        self.L.append(f"CLOUD\t{self.rev}-NUVEM\t{q[0]:.4f}\t{q[1]:.4f}\t{r:.4f}")
        self.L.append(f"TX\t{self.rev}-NOTA\t{q[0] + r * 0.75:.4f}\t{q[1] + r * 0.75:.4f}\t{self.h * 1.6:.4f}\t0\t{self.rev}-{n}")

    def comandos(self, escola, cenario):
        P = np.array(self.pts); x0, y1 = P[:, 0].min(), P[:, 1].max()
        texto = [f'REVISÃO {self.rev} — COMPATIBILIZAÇÃO ({escola}, cenário {cenario})',
                 f'Só profundidade: nota na planta. Traçado novo: layer {self.rev}-NOVO; traçado que sai: {self.rev}-SUBSTITUIDO (tracejado).'] + \
                [f'{self.rev}-{i + 1}  {t}' for i, t in enumerate(self.notas)]
        cab = [f'LAYER\t{self.rev}-NOVO\t1\tContinuous', f'LAYER\t{self.rev}-SUBSTITUIDO\t8\tDASHED',
               f'LAYER\t{self.rev}-NUVEM\t1\tContinuous', f'LAYER\t{self.rev}-NOTA\t1\tContinuous']
        larg = max(40 * self.h, (P[:, 0].max() - x0) * 0.35)
        cab.append(f"MT\t{self.rev}-NOTA\t{x0:.4f}\t{y1 + 3 * self.h * (len(texto) + 4):.4f}\t{self.h * 1.6:.4f}\t{larg:.4f}\t" + '\\P'.join(texto))
        return cab + self.L


def main(nome, cen=None, so_comandos=False, rascunho=False):
    S = importlib.import_module(f'escolas.{nome}')
    cen = cen or getattr(S, 'CENARIO_ENTREGA', 'A')
    fn = os.environ.get('PRECLASH_MUDANCAS') or os.path.join(S.SAIDA, f'{S.SIGLA}_preclash_{cen}_mudancas.json')
    M = json.load(open(fn, encoding='utf-8'))['mudancas']
    T = transformacoes(S); h = getattr(S, 'EXECUTIVO_TEXTO', 0.30); rev = getattr(S, 'REVISAO', 'R01')
    escolher = getattr(S, 'executivo_dwg', None) or (lambda m: getattr(S, 'EXECUTIVO', {}).get(m['disc']))
    por_dwg, sem = collections.defaultdict(list), collections.Counter()
    for m in M:
        dwg = escolher(m)
        if not dwg: sem[m['disc']] += 1; continue
        k = os.path.normcase(os.path.normpath(dwg))
        if k not in T: sem[f"{m['disc']} (sem transformação para {dwg})"] += 1; continue
        por_dwg[k].append((dwg, m))
    if sem: print('mudanças sem DWG definido no adaptador:', dict(sem))
    pasta = os.environ.get('PRECLASH_EXEC_SAIDA') or os.path.join(S.BASE, 'RELATORIOS', f'EXECUTIVO_{S.SIGLA}_{cen}')
    os.makedirs(os.path.join(pasta, '_copias'), exist_ok=True)
    carregar = '(load ' + chr(34) + LSP + chr(34) + ')'
    resumo = []
    for k, lst in por_dwg.items():
        dwg = lst[0][0]; base = os.path.splitext(os.path.basename(dwg))[0]
        rot, tt = T[k]; F = Folha(dwg, rot, tt, h, rev)
        loc = lambda P: np.array([F.P(p) for p in P])
        cmd = os.path.join(pasta, f'_cmd_{base}.txt')
        copia = os.path.join(pasta, '_copias', base + '.dwg')
        dst = os.path.join(pasta, f'{base}_{"REV-" + rev if rascunho else "REVISADO"}.dwg')
        if rascunho:
            for _, m in lst:
                r = 6 * h
                if m['tipo'] == 'mergulho': F.pl(m['planta'], 'NOVO'); F.nota(m['nota'], (m['E'], m['N']), r)
                elif m['tipo'] == 'contorno': F.pl(m['antigo'], 'SUBSTITUIDO'); F.pl(m['novo'], 'NOVO'); F.nota(m['nota'], (m['E'], m['N']), r * 1.5)
                elif m['tipo'] == 'caixa deslocada':
                    F.caixa(m['de'], m['lado'], m['lado_y'], m['rot'], 'SUBSTITUIDO'); F.caixa((m['E'], m['N']), m['lado'], m['lado_y'], m['rot'], 'NOVO'); F.nota(m['nota'], (m['E'], m['N']), r)
            linhas, log = F.comandos(S.ESCOLA, cen), F.notas
        else:
            if so_comandos and not os.path.exists(copia[:-4] + '.dxf'): print(base, ': falta o DXF da cópia (rode sem --so-comandos)'); continue
            if not os.path.exists(copia[:-4] + '.dxf'):
                shutil.copy2(os.path.join(S.BASE, dwg), copia)          # o console só abre a CÓPIA
                console(copia, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '_.AUDIT', '_Y', '(load ' + chr(34) + 'D:/Projeto Modelagem/FERRAMENTAS/georef/dxfout.lsp' + chr(34) + ')',
                                'DXFX', '_.QUIT', '_Y'], copia + '.dxf.log', {'DXF_OUT': copia[:-4].replace(chr(92), '/') + '.dxf'})
            import asbuilt as ab
            Pl = ab.Plano(ab.entidades(copia[:-4] + '.dxf', arcos=True), tol=getattr(S, 'EXECUTIVO_TOL', 0.06), ext=getattr(S, 'EXECUTIVO_EXT', 0.0),
                          caixa_sem_simbolo=getattr(S, 'EXECUTIVO_CAIXA_SEM_SIMBOLO', False))
            Pl.alt_nota = getattr(S, 'EXECUTIVO_NOTA_ALT', None)
            for _, m in lst:
                if m['tipo'] == 'contorno': Pl.contorno(loc(m['antigo']), loc(m['novo']), m['trecho'])
            for _, m in lst:
                if m['tipo'] == 'caixa deslocada': Pl.caixa(F.P(m['de']), F.P((m['E'], m['N'])), max(m['lado'], m['lado_y']), m['trecho'])
            # uma nota por trecho (20/10/2026): pedaços da mesma curva, trechos encadeados e eletrodutos do mesmo banco com a mesma
            # profundidade dividem uma nota, posta ao lado da etiqueta de diâmetro/material do trecho quando ela existe
            for g in ab.agrupar_notas([m for _, m in lst if m['tipo'] == 'mergulho'], familia=getattr(S, 'EXECUTIVO_FAMILIA', None),
                                      raio=getattr(S, 'EXECUTIVO_NOTA_RAIO', 15.0)):
                Pl.nota(loc(g['P']), g['texto'], g['rotulo'], disc=g.get('disc'))
            linhas, log = Pl.L, Pl.log
        open(cmd, 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
        print(f'{base}: {len(lst)} mudanças, {len(linhas)} comandos')
        for x in log: print('   ', x)
        resumo.append({'dwg': dwg, 'saida': dst, 'registro': log, 'comandos': cmd})
        if so_comandos: continue
        if rascunho: shutil.copy2(os.path.join(S.BASE, dwg), copia)
        out = console(copia, ['SECURELOAD 0', 'FILEDIA 0', '_.AUDIT', '_Y', carregar, 'REVR01', '_.AUDIT', '_Y', '_.QUIT', '_Y'], copia + '.rev.log',
                      {'REV_CMD': cmd, 'REV_OUT': dst.replace(chr(92), '/')})
        print('  ', out[-200:], '->', 'OK' if os.path.exists(dst) else 'FALHOU')
    json.dump(resumo, open(os.path.join(pasta, f'{S.SIGLA}_executivo_{cen}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    if '--miniaturas' in sys.argv:          # prévia ANTES | DEPOIS das folhas já plotadas (vai ao dono do projeto junto com o "pronto")
        import argparse, miniaturas
        ap = argparse.ArgumentParser(); ap.add_argument('--miniaturas', required=True); ap.add_argument('--origem', nargs='+', required=True)
        ap.add_argument('--saida'); m = ap.parse_args()
        miniaturas.gerar(m.miniaturas, m.origem, m.saida); sys.exit()
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    main(a[0], a[1] if len(a) > 1 else None, '--so-comandos' in sys.argv, '--rascunho' in sys.argv)
