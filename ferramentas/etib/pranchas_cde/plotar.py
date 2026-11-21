# -*- coding: utf-8 -*-
"""Plota em PDF A0 as originais que só existem em DWG (cópia em work\, nunca o arquivo do Drive). Um accoreconsole por vez.
Uso: python -X utf8 plotar.py [parte do nome ...]"""
import os, sys, shutil, subprocess, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from originais import L
H = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(H, 'work'); os.makedirs(W, exist_ok=True)
RUN = r'D:\Projeto Modelagem\FERRAMENTAS\georef\run_acc.ps1'
LSP = os.path.join(H, 'plot_todos.lsp').replace('\\', '/')


def outros_consoles():
    r = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-Process accoreconsole -ErrorAction SilentlyContinue).Count"], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


so = sys.argv[1:]
for e, s, f, rev, x, m in L:
    if not isinstance(x, tuple): continue
    src = x[1]; nome = os.path.splitext(os.path.basename(src))[0]
    if so and not any(t in nome for t in so): continue
    dwg = os.path.join(W, nome + '.dwg'); shutil.copy2(src, dwg)
    for p in glob.glob(os.path.join(W, nome + '__*.pdf')): os.remove(p)
    scr = os.path.join(W, nome + '.scr'); log = os.path.join(W, nome + '_log.txt')
    open(scr, 'w', encoding='utf-8', newline='\r\n').write('\n'.join(['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', f'(load "{LSP}")', 'PLOTTODOS', '_.QUIT', '_Y']) + '\n')
    while outros_consoles(): print('  aguardando outro accoreconsole terminar...'); time.sleep(20)
    base = os.path.join(W, nome).replace('\\', '/')
    cmd = f"& '{RUN}' -Dwg '{dwg}' -Scr '{scr}' -Log '{log}' -TimeoutSec 600 -EnvVars @{{ PLOT_BASE = '{base}' }}"
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', cmd], capture_output=True, text=True)
    pdfs = sorted(glob.glob(os.path.join(W, nome + '__*.pdf')))
    print(nome, '|', r.stdout.strip(), '|', ', '.join(f'{os.path.basename(p)[len(nome)+2:]} {os.path.getsize(p)/1e6:.1f} MB' for p in pdfs) or 'SEM PDF')
