# -*- coding: utf-8 -*-
"""Checklist da Revisão de qualidade na pasta de envio de Catu (25/10/2026), no mesmo esquema da Sátiro
(satiro/exe/sat_revisar_envio.py) e da Jandaíra: a cópia de entrega do IFC não leva a marcação das conexões em tubo rígido fora de 45°/90°
(regra: só registro interno); a lista delas sai do IFC de trabalho (ENTREGA_IFC_2026-10-25) para
EXECUTIVO_2026-10-25/conferencia/CAT_conexoes_fora_45-90_INTERNO.csv, e a C6 dessas peças passa a observação, como a ferramenta
faz quando a marcação está no IFC.
Uso: python -X utf8 cat_revisar_envio.py"""
import os, sys, re, csv, math, glob
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
import revisar, ifc_conf

REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
TRAB = os.path.join(REL, 'ENTREGA_IFC_2026-10-25')
INTERNO = os.path.join(REL, 'EXECUTIVO_2026-10-25', 'conferencia', 'CAT_conexoes_fora_45-90_INTERNO.csv')
ENVIO = os.path.join(REL, 'ENVIO_2026-10-25')
MOTIVO = 'conexão em tubo rígido fora de 45°/90° aceita como observação interna (opção b do Anderson; fora dos documentos de entrega)'

R = ifc_conf.ler(sorted(glob.glob(os.path.join(TRAB, 'CAT_*.ifc'))), log=lambda *a: None)
PTS = []
for f in R['fit']:
    if str((f.get('ps') or {}).get('fora_do_comercial', '')).lower() == 'sim':
        c = f['c']; PTS.append((f['nome'], f['disc'], float(c[0]), float(c[1]), (f.get('ps') or {}).get('angulo_real')))
os.makedirs(os.path.dirname(INTERNO), exist_ok=True)
with open(INTERNO, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';'); w.writerow(['peca', 'disc', 'E', 'N', 'angulo_real'])
    for p in PTS: w.writerow(p)
print(len(PTS), 'conexões fora de 45°/90° no registro interno ->', INTERNO)
RX = re.compile(r'E (\d+(?:\.\d+)?) / N (\d+(?:\.\d+)?)')
_aceitos = revisar.aceitos


def aceitos(rv, lista):
    _aceitos(rv, lista)
    n = 0
    for x in rv.achados:
        if x.item != 'C6' or x.nivel != 'PENDENCIA': continue
        m = RX.search(x.local or '')
        if not m or not PTS: continue
        e, nn = float(m.group(1)), float(m.group(2))
        if min(math.hypot(e - p[2], nn - p[3]) for p in PTS) <= 0.5:
            x.nivel = 'OBSERVACAO'; x.problema += f' — {MOTIVO}'; n += 1
    rv.ev('C6', f'{n} achados nas {len(PTS)} conexões da lista interna (opção b) passados a observação')


revisar.aceitos = aceitos
sys.argv = ['revisar.py', 'catu', '--rodada', 'ENVIO_2026-10-25',
            '--entrega', 'pasta de envio local de 25/10/2026 (IFC de entrega sem a marcação interna; pranchas de EXECUTIVO_2026-10-25)',
            '--ifc', os.path.join(REL, 'ENVIO_2026-10-25', '03_IFC'), '--envio', ENVIO, '--recortes']
revisar.main()
