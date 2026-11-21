# -*- coding: utf-8 -*-
"""Olindina — conjunto de entrega IFC (fluxo novo, 21/10/2026), a partir da rodada do preclash (escolas/olindina.py, sigla ONN):
  ETIB-OLINDINA/RELATORIOS/PRECLASH_2026-10-21/IFC_POR_DISCIPLINA_AD -> ETIB-OLINDINA/RELATORIOS/ENTREGA_IFC_2026-10-21/
  ONN_IMP_HIDRO / _ELE / _PCIP, ONN_EST_BA5_asbuilt (referência, quando houver), ONN_TERRENO e ONN_FEDERADO (_R01.ifc).
- Só rede externa (21/10); as redes existentes da prancha (cadastro) saem com 'situacao' = existente.
- Terreno: o mesmo das redes (escolas/dados/olindina_terreno.npz).
- Federado: a soma dos IFC de entrega + terreno + estrutura + um marcador por colisão crítica que sobra (as pendências declaradas).
Uso: python -X utf8 onn_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.olindina as S

PRE = S.SAIDA
OUT = os.environ.get('ONN_ENTREGA') or os.path.join(S.REL, 'ENTREGA_IFC_2026-10-21')
EST = os.path.join(PRE, 'ONN_EST_BA5_asbuilt.ifc')          # estrutura as built do BA5 (olindina/ifc/onn_estrutura.py)
REV = 'R01'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-OLINDINA', '_ifc')
NOME = 'ETIB Olindina'


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in ('HIDRO', 'ELE', 'PCIP'):
        fonte = os.path.join(PRE, 'IFC_POR_DISCIPLINA_AD', f'ONN_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'ONN_IMP_{g}_{REV}.ifc')
        f = Ifc(f'{NOME} — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    if os.path.exists(EST):
        dst = os.path.join(OUT, f'ONN_EST_BA5_asbuilt_{REV}.ifc'); shutil.copy2(EST, dst); arqs.append(dst)
        print(os.path.basename(dst), '(referência)')
    T = Terreno(S.TERRENO); V, F = T.pts, T.tri
    desc = 'terreno as built nas cotas das pranchas' if os.path.exists(S.TER_IMP) else 'terreno pelas cotas das pranchas (CT das caixas e cotas de piso)'
    f = Ifc(f'{NOME} — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno'); el.Description = desc
    f.salvar(os.path.join(OUT, f'ONN_TERRENO_{REV}.ifc'))
    fed = Ifc(f'{NOME} — FEDERADO (redes externas da implantação)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno'); el.Description = desc
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, 'ONN_preclash_AD_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA': continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'ONN_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
