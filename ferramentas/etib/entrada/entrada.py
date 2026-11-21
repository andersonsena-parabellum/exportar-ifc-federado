# -*- coding: utf-8 -*-
"""Entrada da escola (regra do projeto, 22/10/2026; CHECKLIST.md itens 01 e 02), antes de modelar:
  - abre CADA DWG de PROJETO_ORIGINAL (numa cópia, fora da pasta da escola) no accoreconsole com AUDIT e lista os que não abrem,
    para o dono do projeto salvar de uma vez no AutoCAD com janela;
  - lista o CTB de cada folha e as fontes (SHX/TTF) e xrefs que o DWG pede, e diz o que falta na máquina.
Um accoreconsole por vez (espera os das outras threads; mata só o próprio PID no timeout, run_one.ps1).
Saída: ETIB-<ESCOLA>/RELATORIOS/ENTRADA_<data>/<SIGLA>_entrada_dwg.json e .md (o quadro vai para o INVENTARIO.md à mão).
Uso: .venv/Scripts/python.exe -X utf8 entrada/entrada.py ETIB-<ESCOLA> [ETIB-<ESCOLA> ...]"""
import os, sys, json, glob, shutil, datetime, importlib.util, collections
sys.stdout.reconfigure(encoding='utf-8')
RAIZ = r'D:\Projeto Modelagem'
AQUI = os.path.dirname(os.path.abspath(__file__))
LSP = os.path.join(AQUI, 'entrada.lsp').replace('\\', '/')
TMP = os.path.join(os.environ.get('TEMP', r'C:\Temp'), 'etib_entrada')
_sp = importlib.util.spec_from_file_location('rever', os.path.join(RAIZ, 'FERRAMENTAS', 'preclash', 'executivo', 'rever.py'))
rever = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(rever)

ACAD = r'C:\Program Files\Autodesk\AutoCAD 2023'
APPD = os.path.join(os.environ['APPDATA'], 'Autodesk', 'AutoCAD 2023', 'R24.2', 'enu')
PASTAS_FONTE = [os.path.join(ACAD, 'Fonts'), r'C:\Windows\Fonts', os.path.join(APPD, 'Support'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts')]
PASTA_CTB = os.path.join(APPD, 'Plotters', 'Plot Styles')
VERSAO = {'AC1015': '2000', 'AC1018': '2004', 'AC1021': '2007', 'AC1024': '2010', 'AC1027': '2013', 'AC1032': '2018'}


def tem(nome, pastas):
    if not nome: return True
    n = os.path.basename(nome).lower()
    if '.' not in n: n += '.shx'
    return any(os.path.exists(os.path.join(p, n)) for p in pastas if p)


def ler_log(fn):
    if not os.path.exists(fn): return ''
    b = open(fn, 'rb').read()
    t = b.decode('utf-16-le', 'replace') if b[1:2] == b'\x00' else b.decode('mbcs', 'replace')
    return t.replace('\x00', '')


def um_dwg(esc, dwg, pasta_tmp):
    copia = os.path.join(pasta_tmp, os.path.basename(dwg))
    shutil.copy2(dwg, copia)
    out = copia[:-4] + '.ent.txt'; log = copia + '.ent.log'
    for f in (out, log):
        if os.path.exists(f): os.remove(f)
    r = rever.console(copia, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '_.AUDIT', '_Y', f'(load "{LSP}")', 'ENTDUMP', '_.QUIT', '_Y'],
                      log, {'ENT_OUT': out.replace('\\', '/')})
    cab = open(dwg, 'rb').read(6).decode('ascii', 'replace')
    d = dict(dwg=os.path.relpath(dwg, os.path.join(RAIZ, esc)), mb=round(os.path.getsize(dwg) / 2**20, 1),
             versao=VERSAO.get(cab, cab), abriu=os.path.exists(out), console=r.splitlines()[-1] if r else '',
             folhas=[], ctb=[], estilos=[], fontes_faltando=[], xrefs=[], audit='')
    L = ler_log(log)
    d['audit'] = ' | '.join(sorted({x.strip() for x in L.splitlines() if 'erro' in x.lower() and ('total' in x.lower() or 'corrig' in x.lower())}))[:300]
    if 'TIMEOUT' in r: d['falha'] = 'timeout'
    elif not d['abriu']:
        fim = [x.strip() for x in L.splitlines() if x.strip()][-4:]
        d['falha'] = ' / '.join(fim)[:300] or 'não abriu (log vazio)'
    if d['abriu']:
        for ln in open(out, encoding='mbcs', errors='replace').read().splitlines():
            c = ln.split('\t')
            if c[0] == 'LAYOUT' and c[1] != 'Model':
                d['folhas'].append(c[1]); d['ctb'].append(c[2] if len(c) > 2 else '')
            elif c[0] == 'LAYOUT' and len(c) > 2 and c[2]:
                d['ctb'].append(c[2])
            elif c[0] == 'STYLE':
                f1, f2 = (c[2] if len(c) > 2 else ''), (c[3] if len(c) > 3 else '')
                d['estilos'].append(c[1])
                for f in (f1, f2):
                    if f and not tem(f, PASTAS_FONTE + [os.path.dirname(dwg)]): d['fontes_faltando'].append(f)
            elif c[0] == 'XREF':
                d['xrefs'].append(c[1] + (' (' + os.path.basename(c[2]) + ')' if len(c) > 2 and c[2] else ''))
            elif c[0] == 'PSTYLEMODE':
                d['pstylemode'] = c[1]
        d['ctb'] = sorted({x for x in d['ctb'] if x})
        d['fontes_faltando'] = sorted(set(d['fontes_faltando']), key=str.lower)
    for f in (copia, out, log, copia[:-4] + '.ent.log.scr', log[:-4] + '.scr'):
        if os.path.exists(f):
            try: os.remove(f)
            except OSError: pass
    return d


def escola(esc):
    base = os.path.join(RAIZ, esc)
    dwgs = sorted(glob.glob(os.path.join(base, 'PROJETO_ORIGINAL', '**', '*.dwg'), recursive=True))
    pasta_tmp = os.path.join(TMP, esc); os.makedirs(pasta_tmp, exist_ok=True)
    R = []
    for i, f in enumerate(dwgs, 1):
        d = um_dwg(esc, f, pasta_tmp); R.append(d)
        print(f'[{esc} {i}/{len(dwgs)}] {"ok " if d["abriu"] else "NÃO ABRE"} {os.path.basename(f)}  ctb={d["ctb"]} fontes_faltando={d["fontes_faltando"]}', flush=True)
    ctb = collections.Counter(c for d in R for c in d['ctb'])
    ctb_falta = sorted(c for c in ctb if not os.path.exists(os.path.join(PASTA_CTB, c)) and not any(
        os.path.exists(os.path.join(os.path.dirname(os.path.join(base, d['dwg'])), c)) for d in R))
    fontes = collections.Counter(f for d in R for f in d['fontes_faltando'])
    hoje = datetime.date.today().isoformat()
    sai = os.path.join(base, 'RELATORIOS', f'ENTRADA_{hoje}'); os.makedirs(sai, exist_ok=True)
    sig = esc.replace('ETIB-', '')
    res = dict(escola=esc, data=hoje, dwg=R, nao_abrem=[d['dwg'] for d in R if not d['abriu']], ctb=dict(ctb), ctb_falta=ctb_falta,
               fontes_faltando=dict(fontes), xrefs=sorted({x for d in R for x in d['xrefs']}))
    json.dump(res, open(os.path.join(sai, f'{sig}_entrada_dwg.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = [f'# Entrada — {esc}: DWG, CTB e fontes ({hoje})', '',
          f'{len(R)} DWG de `PROJETO_ORIGINAL\\` abertos no accoreconsole com AUDIT (numa cópia; a pasta original não foi tocada).', '',
          f'- **Não abrem:** {len(res["nao_abrem"])}' + (''.join(f'\n  - `{x}`' for x in res['nao_abrem']) if res['nao_abrem'] else ' (nenhum)'),
          f'- **CTB pedidos:** ' + (', '.join(f'{k} ({v})' for k, v in sorted(ctb.items())) or 'nenhum'),
          f'- **CTB que não estão na máquina:** ' + (', '.join(ctb_falta) or 'nenhum') + ' (sem o CTB do projetista, plota com o padrão e a conferência olha só a geometria)',
          f'- **Fontes que não estão na máquina:** ' + (', '.join(f'{k} ({v})' for k, v in sorted(fontes.items(), key=lambda x: x[0].lower())) or 'nenhuma'),
          f'- **Xrefs:** ' + (', '.join(res['xrefs']) or 'nenhum'), '',
          '| DWG | MB | Formato | Abre | AUDIT | Folhas | CTB | Fontes faltando |', '|---|---|---|---|---|---|---|---|']
    for d in R:
        md.append(f"| {os.path.basename(d['dwg'])} | {d['mb']} | {d['versao']} | {'sim' if d['abriu'] else 'NÃO: ' + d.get('falha', '')} | {d['audit'] or '—'} | "
                  f"{len(d['folhas'])} | {', '.join(d['ctb']) or '—'} | {', '.join(d['fontes_faltando']) or '—'} |")
    open(os.path.join(sai, f'{sig}_entrada_dwg.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print(f'{esc}: {len(R)} DWG, não abrem {len(res["nao_abrem"])}, CTB faltando {ctb_falta}, fontes faltando {dict(fontes)} -> {sai}', flush=True)
    return res


if __name__ == '__main__':
    for e in sys.argv[1:]:
        escola(e)
