# -*- coding: utf-8 -*-
"""Sátiro Dias — conjunto de entrega IFC (fluxo novo, 21/10/2026), a partir da rodada do preclash (escolas/satiro.py, sigla SAT):
  ETIB-SATIRO-DIAS/RELATORIOS/PRECLASH_2026-10-21/IFC_POR_DISCIPLINA_AD -> ETIB-SATIRO-DIAS/RELATORIOS/ENTREGA_IFC_2026-10-21/
  STK_IMP_HIDRO / _ELE / _PCIP, STK_TERRENO e STK_FEDERADO (_R01.ifc). Só rede externa (21/10).
- As canaletas de superfície não entram (não são rede enterrada).
- Terreno: o do IMP as built levado às CT das caixas das pranchas, na malha de 0,50 m em que as redes foram estudadas.
- Federado: a soma dos IFC de entrega + terreno + um marcador por colisão crítica que sobra (as pendências declaradas).
Uso: python -X utf8 sat_entrega.py"""
import os, sys, csv, glob, shutil
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
from preclash.export_ifc import Ifc
from preclash.terreno import Terreno
import alh_entrega as AE
import escolas.satiro as S

PRE = S.SAIDA
OUT = os.environ.get('SAT_ENTREGA') or os.path.join(S.REL, 'ENTREGA_IFC_2026-10-21')
REV = 'R01'
REVQ = os.path.join(r'D:\Projeto Modelagem\FERRAMENTAS', 'revisao', 'relatorios', 'ETIB-SATIRO-DIAS', '_ifc')


def nao_canaleta(p):
    return not str(p.Name or '').endswith('(canaleta)')


def main():
    os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): os.remove(x)
    arqs = []
    for g in ('HIDRO', 'ELE', 'PCIP'):
        fonte = os.path.join(PRE, 'IFC_POR_DISCIPLINA_AD', f'SAT_{g}_compatibilizado.ifc')
        dst = os.path.join(OUT, f'STK_IMP_{g}_{REV}.ifc')
        f = Ifc(f'ETIB Sátiro Dias — implantação — {g}', S.ORIGEM, S.EPSG); n = AE.copiar(fonte, f, nao_canaleta); f.salvar(dst)
        print(os.path.basename(dst), n, 'elementos'); arqs.append(dst)
    # a mesma malha de 0,50 m do clash (o adaptador já reamostra o terreno nela e as tampas das caixas saem dela)
    T = Terreno(S.TERRENO); V, F = T.pts, T.tri
    f = Ifc('ETIB Sátiro Dias — terreno', S.ORIGEM, S.EPSG); el = f.terreno(V, F, 'Terreno (IMP as built)'); el.Description = 'terreno as built nas cotas das pranchas'
    f.salvar(os.path.join(OUT, f'STK_TERRENO_{REV}.ifc'))
    fed = Ifc('ETIB Sátiro Dias — FEDERADO (redes externas da implantação)', S.ORIGEM, S.EPSG)
    n = sum(AE.copiar(a, fed) for a in arqs)
    el = fed.terreno(V, F, 'Terreno (IMP as built)'); el.Description = 'terreno as built nas cotas das pranchas'
    k = 0
    fl = lambda v: float(v.replace(',', '.'))
    for r in csv.DictReader(open(os.path.join(PRE, 'SAT_preclash_AD_conflitos_depois.csv'), encoding='utf-8-sig'), delimiter=';'):
        if r['gravidade'] != 'CRÍTICA' or '(canaleta)' in r['trecho_A'] + r['trecho_B']: continue
        k += 1
        fed.conflito({'E': fl(r['E']), 'N': fl(r['N']), 'z': fl(r['z']), 'gravidade': 'CRÍTICA'}, f'P{k:03d}',
                     {'gravidade': 'CRÍTICA', 'descricao': r['descricao'], 'folga_m': fl(r['folga_m']), 'A': r['trecho_A'], 'B': r['trecho_B']})
    fn = os.path.join(OUT, f'STK_FEDERADO_{REV}.ifc'); fed.salvar(fn)
    print('federado', n, 'elementos +', k, 'pendências', f'{os.path.getsize(fn) / 1e6:.1f} MB')
    os.makedirs(REVQ, exist_ok=True)
    for x in glob.glob(os.path.join(REVQ, '*.ifc')): os.remove(x)
    for x in glob.glob(os.path.join(OUT, '*.ifc')): shutil.copy2(x, REVQ)


if __name__ == '__main__':
    main()
