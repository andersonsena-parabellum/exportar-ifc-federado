# -*- coding: utf-8 -*-
"""Exporta um modelo da Jandaíra pelo plugin do Revit (porta 8080), em duas chamadas (o plugin recusa pedidos acima de ~8 KB):
export_jan_abrir.cs (abre em segundo plano, até 3 tentativas), export_jan_meta.cs (meta) e export_jan_geo.cs (geometria + fecha sem salvar).
Uso: python exportar_jan.py <DISC> <arquivo.rvt> [modo: 0=disciplina 1=estrutura 2=terreno/IMP] [timeout_s]"""
import sys, os, json, time
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS")
import revit_rpc
sys.stdout.reconfigure(encoding='utf-8')
OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01\geo" + "\\"
AQUI = os.path.dirname(os.path.abspath(__file__))


def carregar(nome, **kw):
    c = open(os.path.join(AQUI, nome), encoding='utf-8').read()
    for k, v in kw.items(): c = c.replace('@@%s@@' % k, v)
    c = '\n'.join(l.strip() for l in c.splitlines() if l.strip() and not l.strip().startswith('//'))
    n = len(json.dumps({'jsonrpc': '2.0', 'method': 'send_code_to_revit', 'params': {'code': c, 'parameters': []}, 'id': '1'}))
    if n > 8000: raise SystemExit('%s: pedido com %d bytes (> 8000)' % (nome, n))
    return c


def rodar(code, tmo):
    r = revit_rpc.send(code, tmo)
    res = r.get('result') if isinstance(r, dict) else r
    try: res = json.loads(res)
    except Exception: pass
    if isinstance(r, dict) and not r.get('success', True): raise SystemExit('ERRO: ' + str(r.get('errorMessage')))
    return res


def exportar(disc, arq, modo='0', tmo=1800, audit=False):
    arq = os.path.normpath(arq); t0 = time.time()
    for tent in range(3):
        r = rodar(carregar('export_jan_abrir.cs', ARQ=arq, AUDIT='true' if (audit or tent > 0) else 'false'), tmo); print(disc, r, f'[{time.time()-t0:.0f}s]', flush=True)
        if 'ERRO' not in str(r): break
        time.sleep(10)
    else:
        print(disc, 'nao abriu', flush=True); return False
    print(disc, rodar(carregar('export_jan_meta.cs', ARQ=arq, DISC=disc, OUT=OUT), tmo), f'[{time.time()-t0:.0f}s]', flush=True)
    print(disc, rodar(carregar('export_jan_geo.cs', ARQ=arq, DISC=disc, OUT=OUT, MODO=str(modo), FECHAR='true'), tmo), f'[{time.time()-t0:.0f}s]', flush=True)
    return True


if __name__ == '__main__':
    # sem argumentos: lote padrão da Jandaíra (modelos que faltam, IMP e estruturas copiadas para nomes únicos)
    if len(sys.argv) > 2:
        exportar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '0', float(sys.argv[4]) if len(sys.argv) > 4 else 1800)
    else:
        J = r"D:\Projeto Modelagem\ETIB-JANDAIRA" + "\\"
        lote = [(d, J + f, '0') for d, f in (('ESG', 'JAN-ESG.rvt'), ('DRE', 'JAN-DRE.rvt'), ('PCI', 'JAN-PCIrvt.rvt'))]
        lote.append(('IMP', os.path.join(J, 'REFERENCIAS_RVT', 'IMP', '24-049-JDI-CTO-ETIB-IMP-R00.rvt'), '2'))
        EST = os.environ.get('JAN_EST_DIR')
        if EST:
            for f in sorted(os.listdir(EST)):
                if f.endswith('.rvt'):
                    tag = 'EST_' + f.split('-ETIB-')[1].split('-PE-')[0] + '_' + f.split('-PE-')[1][:7].replace('-', '')
                    lote.append((tag, os.path.join(EST, f), '1'))
        pular = set(sys.argv[1].split(',')) if len(sys.argv) == 2 else set()
        for d, f, m in lote:
            if d in pular or os.path.exists(OUT + d + '_mesh.tsv'): print(d, 'ja exportado', flush=True); continue
            try: exportar(d, f, m, 2300)
            except SystemExit as ex: print(d, 'ERRO', ex, flush=True)
            except Exception as ex: print(d, 'ERRO', type(ex).__name__, ex, flush=True)
