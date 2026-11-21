# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — conjunto de entrega IFC (fluxo novo, 23/10/2026), a partir da rodada do preclash (escolas/apora_aurea.py,
sigla AUR), no mesmo esquema da Itamira (itamira/ifc/ita_entrega.py):
  ETIB-APORA-PROF-AUREA/RELATORIOS/PRECLASH_2026-10-23/IFC_POR_DISCIPLINA_AD -> RELATORIOS/ENTREGA_IFC_2026-10-23/
  AUR_IMP_HIDRO / AUR_IMP_ELE / AUR_IMP_PCIP / AUR_IMP_EST (fundação da quadra, referência), AUR_TERRENO e AUR_FEDERADO (_R01.ifc).
- Terreno: o do IMP as built ajustado à base (escolas/dados/apora_aurea_terreno_imp_base.npz), o mesmo das redes.
- Federado: soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (nenhuma nesta rodada).
Uso: .venv/Scripts/python.exe -X utf8 aurea/ifc/aur_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.apora_aurea as S

PRE = S.SAIDA
CEN = S.CENARIO_ENTREGA
OUT = os.environ.get('AUR_ENTREGA') or os.path.join(S.BASE, 'RELATORIOS', 'ENTREGA_IFC_2026-10-23')
REV = 'R01'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-APORA-PROF-AUREA', '_ifc')
NOME = 'ETIB Aporá Prof. Áurea'


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in S.DISCIPLINAS_ENTREGA:
        fonte = os.path.join(PRE, f'IFC_POR_DISCIPLINA_{CEN}', f'AUR_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'AUR_IMP_{g}_{REV}.ifc')
        f = Ifc(f'{NOME} — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    # malha regular pelo z() da ferramenta (TIN + platô da terraplanagem a 188,00), a mesma superfície das profundidades do modelo
    T = Terreno(S.TERRENO); x0, y0 = T.pts[:, :2].min(0); x1, y1 = T.pts[:, :2].max(0)
    V, F = T.grade((x0, y0, x1, y1), passo=1.0)
    desc = 'terreno acabado (IMP as built nas cotas da terraplanagem e das caixas da drenagem)'
    f = Ifc(f'{NOME} — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno'); el.Description = desc
    f.salvar(os.path.join(OUT, f'AUR_TERRENO_{REV}.ifc'))
    fed = Ifc(f'{NOME} — FEDERADO (redes externas da implantação)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno'); el.Description = desc
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, f'AUR_preclash_{CEN}_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA': continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'AUR_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
