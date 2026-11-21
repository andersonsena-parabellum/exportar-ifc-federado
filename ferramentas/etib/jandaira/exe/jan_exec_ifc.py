# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — as 8 pranchas no padrão de executivo final a partir do modelo IFC compatibilizado:
1) FERRAMENTAS/jandaira/ifc/jan_mudancas_ifc.py junta as mudanças (estudo de cota, contornos, caixas deslocadas) em UTM;
2) preclash/executivo/rever.py (PRECLASH_UTM=1) planeja e aplica cada prancha no accoreconsole -> EXECUTIVO_R02_IFC/*_REVISADO.dwg;
3) jan_carimbo.py (JAN_EXEC_OUT) põe a linha no quadro de revisões, troca o código e plota o PDF A0.
Uso: python -X utf8 jan_exec_ifc.py [--so-comandos] [--sem-carimbo]"""
import os, sys, subprocess
OUT = os.environ.get('JAN_EXEC_OUT') or r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R02_IFC'
os.environ.update(PRECLASH_UTM='1', PRECLASH_MUDANCAS=os.path.join(OUT, 'JAN_mudancas_UTM.json'), PRECLASH_EXEC_SAIDA=OUT, JAN_EXEC_OUT=OUT)
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.stdout.reconfigure(encoding='utf-8')
PY = r'D:\Projeto Modelagem\FERRAMENTAS\.venv\Scripts\python.exe'
if __name__ == '__main__':
    subprocess.run([PY, '-X', 'utf8', '-W', 'ignore', r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\ifc\jan_mudancas_ifc.py'], check=True)
    import rever
    os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
    rever.main('jandaira', so_comandos='--so-comandos' in sys.argv)
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        subprocess.run([PY, '-X', 'utf8', '-W', 'ignore', r'D:\Projeto Modelagem\FERRAMENTAS\jandaira\exe\jan_carimbo.py'], check=True)
