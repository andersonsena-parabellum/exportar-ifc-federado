# -*- coding: utf-8 -*-
"""Catu — conjunto de entrega IFC (fluxo novo, 25/10/2026), a partir da rodada do preclash (escolas/catu.py,
sigla CAT), no mesmo esquema da Prof. Áurea (aurea/ifc/aur_entrega.py):
  ETIB-CATU/RELATORIOS/PRECLASH_2026-10-25/IFC_POR_DISCIPLINA_AD -> RELATORIOS/ENTREGA_IFC_2026-10-25/
  CAT_IMP_HIDRO / CAT_IMP_ELE / CAT_IMP_PCIP / CAT_IMP_EST (estrutura dos blocos novos, referência), CAT_TERRENO e CAT_FEDERADO (_R01.ifc).
- Terreno: o do IMP as built levado às cotas da base (escolas/dados/catu_terreno_base.npz, catu/ifc/cat_terreno.py), a mesma malha de 0,50 m das redes.
- As canaletas do campo não entram (não são rede enterrada; só obstáculo do clash).
- Federado: soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (as pendências declaradas).
Uso: .venv/Scripts/python.exe -X utf8 catu/ifc/cat_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.catu as S

PRE = S.SAIDA
CEN = S.CENARIO_ENTREGA
OUT = os.environ.get('CAT_ENTREGA') or os.path.join(S.BASE, 'RELATORIOS', 'ENTREGA_IFC_2026-10-25')
REV = 'R01'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-CATU', '_ifc')
NOME = 'ETIB Catu'


def nao_canaleta(p):
    """canaleta do campo (só obstáculo do clash) e casa de bombas (prédio: fora da rede externa) não vão na entrega."""
    n = str(p.Name or '')
    return not n.endswith('(canaleta)') and 'casa de bombas' not in n.lower()


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in S.DISCIPLINAS_ENTREGA:
        fonte = os.path.join(PRE, f'IFC_POR_DISCIPLINA_{CEN}', f'CAT_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'CAT_IMP_{g}_{REV}.ifc')
        f = Ifc(f'{NOME} — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f, nao_canaleta); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    # a mesma malha de 0,50 m do clash (o terreno de entrega já é a malha; as tampas das caixas e as profundidades saem dela)
    T = Terreno(S.TERRENO); V, F = T.pts, T.tri
    desc = 'terreno acabado (IMP as built com os platôs nas cotas da implantação e das caixas de esgoto e drenagem)'
    f = Ifc(f'{NOME} — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno'); el.Description = desc
    f.salvar(os.path.join(OUT, f'CAT_TERRENO_{REV}.ifc'))
    fed = Ifc(f'{NOME} — FEDERADO (redes externas da implantação)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno'); el.Description = desc
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, f'CAT_preclash_{CEN}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA': continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'CAT_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
