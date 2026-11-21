# -*- coding: utf-8 -*-
"""Entrada da escola, item 3 (CHECKLIST 03): numa sessão só do Revit, lê os RVT que a escola precisa e grava a malha em UTM/coords
internas para o preclash (equivale à conversão em IFC; o IFC de entrega do terreno e da estrutura sai do preclash):
  - IMP as built: terreno, pisos, paredes, vínculos dos blocos e famílias com ponto (entrada/revit/imp_ler.cs com os caminhos da escola);
  - estrutura as built (FUN/ECC/EMT de REFERENCIAS_RVT): triângulos de cada peça pela forma real (entrada/revit/estrutura_tri.cs).
Um RVT por chamada (revit_rpc, porta 8080); cada arquivo é aberto desanexado e fechado SEM salvar. Pula o que já tem saída.
Uso: .venv/Scripts/python.exe -X utf8 entrada/revit_conv.py EXEMPLO [OUTRA ...]"""
import os, sys, glob, time
sys.stdout.reconfigure(encoding='utf-8')
F = r'D:\Projeto Modelagem\FERRAMENTAS'
sys.path.insert(0, F)
import revit_rpc

ESC = {  # chave: (pasta da escola, pasta de trabalho em georef/work, ler o IMP?, ler a estrutura?) — MODELO
    'EXEMPLO': ('ETIB-<ESCOLA>', 'EXEMPLO', True, True),
}


def rodar(code, rotulo):
    t0 = time.time()
    try: r = revit_rpc.send(code, timeout=1800)
    except Exception as ex: r = f'FALHOU: {ex}'
    print(f'[{time.time() - t0:.0f} s] {rotulo}: {str(r).strip()[:400]}', flush=True)
    return r


def main(nomes):
    est = open(os.path.join(F, 'entrada', 'revit', 'estrutura_tri.cs'), encoding='utf-8').read()
    imp = open(os.path.join(F, 'entrada', 'revit', 'imp_ler.cs'), encoding='utf-8').read()
    for n in nomes:
        pasta, work, ler_imp, ler_est = ESC[n]
        base = os.path.join(r'D:\Projeto Modelagem', pasta)
        out = os.path.join(F, 'georef', 'work', work, 'imp')
        if ler_imp:
            rvt = glob.glob(os.path.join(base, 'REFERENCIAS_RVT', 'IMP', '*.rvt'))[0]
            if os.path.exists(os.path.join(out, 'imp_topo.csv')): print(n, 'IMP já lido')
            else:
                os.makedirs(out, exist_ok=True)
                c = imp.splitlines()
                c = [f'string ARQ = @"{rvt}";' if x.startswith('string ARQ =') else f'string OUT = @"{out}\\";' if x.startswith('string OUT =') else x for x in c]
                rodar('\n'.join(c), f'{n} IMP')
        if ler_est:
            for rvt in sorted(glob.glob(os.path.join(base, 'REFERENCIAS_RVT', '*', '*.rvt'))):
                b = os.path.basename(rvt)
                if '-IMP' in b: continue
                bloco = os.path.basename(os.path.dirname(rvt))
                tag = next((t for t in ('FUN', 'ECC', 'EMT') if f'-{t}-' in b), 'EST')
                blk = next((x for x in b.split('-ETIB-')[1].split('-')[:1]), bloco) if '-ETIB-' in b else bloco
                dst = os.path.join(out, f'est_{blk}-{tag}_tri.csv')
                if os.path.exists(dst): print(n, b, 'já lido'); continue
                rodar(est.replace('__ARQ__', rvt).replace('__OUT__', dst), f'{n} {b}')


if __name__ == '__main__':
    main(sys.argv[1:])
