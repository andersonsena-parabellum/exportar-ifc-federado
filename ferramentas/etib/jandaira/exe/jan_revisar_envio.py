# -*- coding: utf-8 -*-
"""Checklist da Revisão de qualidade na pasta de envio da Jandaíra (R03 final, 21/10/2026), sem mexer na ferramenta da Revisão.
A cópia de entrega do IFC não leva a marcação das 20 conexões em PVC rígido fora de 45°/90° (Anderson, 21/10: "fica só entre a
gente"); a lista delas fica no registro interno (EXECUTIVO_R03_IFC\\conferencia\\JAN_R03_conexoes_fora_45-90_INTERNO.csv).
Este script lê essa lista e passa a C6 dessas 20 peças a observação (opção b), como a ferramenta faz quando a marcação está no IFC.
Uso:  ..\\..\\.venv\\Scripts\\python.exe -X utf8 jan_revisar_envio.py [pasta_envio]"""
import os, sys, re, csv, math
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
import revisar

STG = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\_revisao_qualidade'
INTERNO = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R03_IFC\conferencia\JAN_R03_conexoes_fora_45-90_INTERNO.csv'
ENVIO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(STG, '_ENVIO_2026-10-21')
MOTIVO = 'conexão em PVC rígido fora de 45°/90° aceita como observação interna (Anderson, 21/10/2026, opção b; fora dos documentos de entrega)'

PTS = [(float(r['E']), float(r['N'])) for r in csv.DictReader(open(INTERNO, encoding='utf-8-sig'), delimiter=';')]
RX = re.compile(r'E (\d+(?:\.\d+)?) / N (\d+(?:\.\d+)?)')
_aceitos = revisar.aceitos


def aceitos(rv, lista):
    _aceitos(rv, lista)
    n = 0
    for x in rv.achados:
        if x.item != 'C6' or x.nivel != 'PENDENCIA': continue
        m = RX.search(x.local or '')
        if not m: continue
        e, nn = float(m.group(1)), float(m.group(2))
        if min(math.hypot(e - a, nn - b) for a, b in PTS) <= 0.5:
            x.nivel = 'OBSERVACAO'; x.problema += f' — {MOTIVO}'; n += 1
    rv.ev('C6', f'{n} achados nas {len(PTS)} conexões da lista interna (opção b) passados a observação')


revisar.aceitos = aceitos
sys.argv = ['revisar.py', 'jandaira', '--rodada', 'ENVIO_2026-10-21',
            '--entrega', 'R03 final, pasta de envio de 21/10/2026 (IFC de entrega sem a marcação interna; pranchas e LEIA-ME de _revisao_qualidade)',
            '--ifc', os.path.join(STG, '03_IFC'), '--pdf', os.path.join(STG, 'PDF'), '--dwg', STG, '--envio', ENVIO]
revisar.main()
