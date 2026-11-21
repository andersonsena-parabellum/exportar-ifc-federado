# -*- coding: utf-8 -*-
"""Pojuca — conjunto de entrega IFC (fluxo novo, 26/10/2026), a partir da rodada do preclash (escolas/pojuca.py,
sigla PJC), no mesmo esquema da Catu (catu/ifc/cat_entrega.py):
  ETIB-POJUCA/RELATORIOS/PRECLASH_2026-10-25/IFC_POR_DISCIPLINA_AD -> RELATORIOS/ENTREGA_IFC_2026-10-26/
  PJC_IMP_HIDRO / PJC_IMP_ELE / PJC_IMP_PCIP / PJC_IMP_EST (estrutura dos blocos, referência), PJC_TERRENO e PJC_FEDERADO (_R02.ifc; a R01 foi a do piloto de 19/10).
- Terreno: o do IMP as built (escolas/dados/pojuca_terreno.npz, escolas/pojuca_terreno.py), a mesma malha do clash.
- O que for só obstáculo do clash (so_clash) não entra.
- Federado: soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (as pendências declaradas).
Uso: .venv/Scripts/python.exe -X utf8 pojuca/ifc/pjc_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.pojuca as S

PRE = S.SAIDA
CEN = S.CENARIO_ENTREGA
OUT = os.environ.get('PJC_ENTREGA') or os.path.join(S.BASE, 'RELATORIOS', 'ENTREGA_IFC_2026-10-26')
REV = 'R02'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-POJUCA', '_ifc')
NOME = 'ETIB Pojuca'


def nao_canaleta(p):
    """canaleta do campo (só obstáculo do clash) e casa de bombas (prédio: fora da rede externa) não vão na entrega."""
    n = str(p.Name or '')
    return not n.endswith('(canaleta)') and 'casa de bombas' not in n.lower()


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in S.DISCIPLINAS_ENTREGA:
        fonte = os.path.join(PRE, f'IFC_POR_DISCIPLINA_{CEN}', f'PJC_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'PJC_IMP_{g}_{REV}.ifc')
        f = Ifc(f'{NOME} — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f, nao_canaleta); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    # a mesma malha de 0,50 m do clash (o terreno de entrega já é a malha; as tampas das caixas e as profundidades saem dela)
    T = Terreno(S.TERRENO); V, F = T.pts, T.tri
    desc = 'terreno acabado (IMP as built: pisos externos, plataformas, terreno modificado e natural)'
    f = Ifc(f'{NOME} — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno'); el.Description = desc
    f.salvar(os.path.join(OUT, f'PJC_TERRENO_{REV}.ifc'))
    fed = Ifc(f'{NOME} — FEDERADO (redes externas da implantação)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno'); el.Description = desc
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, f'PJC_preclash_{CEN}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA': continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'PJC_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
