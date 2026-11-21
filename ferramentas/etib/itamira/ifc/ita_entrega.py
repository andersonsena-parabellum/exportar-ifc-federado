# -*- coding: utf-8 -*-
"""Aporá Itamira — conjunto de entrega IFC (fluxo novo, 22/10/2026), a partir da rodada do preclash (escolas/itamira.py, sigla ITA),
no mesmo esquema da Olindina (olindina/ifc/onn_entrega.py):
  ETIB-APORA-ITAMIRA/RELATORIOS/PRECLASH_2026-10-24/IFC_POR_DISCIPLINA_AD -> RELATORIOS/ENTREGA_IFC_2026-10-24/
  ITA_IMP_HIDRO / ITA_IMP_ELE, ITA_TERRENO e ITA_FEDERADO (_R02.ifc). Sem PCIP: a Itamira não tem projeto de incêndio enterrado
  (o do campo é só sinalização e iluminação de emergência; o da implantação está no pedido à construtora).
- Terreno: o do IFC as built do IMP (escolas/dados/itamira_terreno.npz), o mesmo das redes.
- Federado: soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (nenhuma nesta rodada).
Uso: .venv/Scripts/python.exe -X utf8 itamira/ifc/ita_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.itamira as S

PRE = S.SAIDA
CEN = S.CENARIO_ENTREGA
OUT = os.environ.get('ITA_ENTREGA') or os.path.join(S.BASE, 'RELATORIOS', 'ENTREGA_IFC_2026-10-24')
REV = 'R02'                # R02 (24/10/2026): ELE-06 até o QD1, decisão I1
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-APORA-ITAMIRA', '_ifc')
NOME = 'ETIB Aporá Itamira'


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in S.DISCIPLINAS_ENTREGA:
        fonte = os.path.join(PRE, f'IFC_POR_DISCIPLINA_{CEN}', f'ITA_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'ITA_IMP_{g}_{REV}.ifc')
        f = Ifc(f'{NOME} — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    T = Terreno(S.TERRENO); V, F = T.pts, T.tri
    desc = 'terreno as built (IFC do IMP executado)'
    f = Ifc(f'{NOME} — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno'); el.Description = desc
    f.salvar(os.path.join(OUT, f'ITA_TERRENO_{REV}.ifc'))
    fed = Ifc(f'{NOME} — FEDERADO (redes externas da implantação e do campo)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno'); el.Description = desc
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, f'ITA_preclash_{CEN}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA': continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'ITA_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
