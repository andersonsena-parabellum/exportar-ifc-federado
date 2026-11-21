# -*- coding: utf-8 -*-
"""Checklist da Revisão de qualidade na pasta de envio da Sátiro Dias (22/10/2026), no mesmo esquema da Jandaíra
(jandaira/exe/jan_revisar_envio.py): a cópia de entrega do IFC não leva a marcação das conexões em tubo rígido fora de 45°/90°
(regra: só registro interno); a lista delas sai do IFC de trabalho (ENTREGA_IFC_2026-10-21) para
EXECUTIVO_2026-10-21/conferencia/SAT_conexoes_fora_45-90_INTERNO.csv, e a C6 dessas peças passa a observação, como a ferramenta
faz quando a marcação está no IFC.
Uso: python -X utf8 sat_revisar_envio.py"""
import os, sys, re, csv, math, glob
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\revisao')
import revisar, ifc_conf

REL = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS'
TRAB = os.path.join(REL, 'ENTREGA_IFC_2026-10-21')
INTERNO = os.path.join(REL, 'EXECUTIVO_2026-10-21', 'conferencia', 'SAT_conexoes_fora_45-90_INTERNO.csv')
ENVIO = r'G:\Meu Drive\ETIB_ENVIOS\ETIB-SATIRO-DIAS_2026-10-22'
MOTIVO = 'conexão em tubo rígido fora de 45°/90° aceita como observação interna (opção b do Anderson; fora dos documentos de entrega)'

R = ifc_conf.ler(sorted(glob.glob(os.path.join(TRAB, 'STK_IMP_*.ifc'))), log=lambda *a: None)
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


# E6 na folha inteira (PDCA A3): sobreposições que já estão na folha do projetista e que a comparação com a origem não reconhece
# (campo "####" da área da arquitetura, etiqueta "2.1/2\" PEAD" partida em dois textos, nível "236,00" ao lado da etiqueta da PVE-06,
# que mudou de texto); conferidas no recorte da revisada, 22/10/2026
E6_ORIGEM = [('EL-001', 'CIRCUITO 200 M'), ('IN-001', 'PEAD'), ('ESG-001', '"236,00" escrito por cima de "CF.: 234.25"')]
# outros achados conferidos um a um (item, folha/arquivo, trecho do local, motivo)
CONFERIDOS = [('D3', 'STK_IMP_ELETRICA', 'AL-007', 'subida do eletroduto junto do muro entre os platôs 233 e 236 (a cota acompanha o terreno, '
               'como nos taludes; sem ela o trecho passava de 2,00 m de profundidade no platô de cima)'),
              ('E11', 'IN-001', 'A-DETL-THIN', 'são 3 pontos de tamanho zero da arquitetura (x 936 mm, y 470 mm), invisíveis na folha impressa')]


def _e6(rv):
    n = 0
    for x in rv.achados:
        if x.item == 'E6' and x.nivel == 'PENDENCIA' and any(f in (x.onde or '') and t in (x.problema or '') for f, t in E6_ORIGEM):
            x.nivel = 'OBSERVACAO'; x.problema += ' — já vinha na folha do projetista (conferido no recorte)'; n += 1
    rv.ev('E6', f'{n} sobreposições da folha do projetista passadas a observação')
    for it, onde, loc, mot in CONFERIDOS:
        for x in rv.achados:
            if x.item == it and x.nivel == 'PENDENCIA' and onde in (x.onde or '') and loc in (x.local or ''):
                x.nivel = 'OBSERVACAO'; x.problema += f' — {mot}'


revisar.aceitos = aceitos
_gravar = revisar.gravar


def gravar(rv, *a, **k):
    _e6(rv)
    return _gravar(rv, *a, **k)


revisar.gravar = gravar
sys.argv = ['revisar.py', 'satiro', '--rodada', 'ENVIO_2026-10-22',
            '--entrega', 'pasta de envio de 22/10/2026 (IFC de entrega sem a marcação interna; pranchas de EXECUTIVO_2026-10-21)',
            '--ifc', os.path.join(REL, 'ENVIO_2026-10-22', '03_IFC'), '--envio', ENVIO]
revisar.main()
