# -*- coding: utf-8 -*-
"""Aporá Prof. Áurea — pranchas no padrão de executivo final (fluxo novo, 23/10/2026), como na Olindina (olindina/exe/onn_exec.py):
1) junta as mudanças em UTM: a CX-03 da EL-001 deslocada (preclash, cenário AD) e as etiquetas de cota do AF-002 (TEXTOS);
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez) -> EXECUTIVO_2026-10-23/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com a linha nova no quadro de revisões, na revisão seguinte, e o PDF A0.
AF-002 (aplicar e avisar, decisão A3 da página de entrada): CT 188,00 nas caixas do lado leste e nos PVP-01/02, mantendo a
profundidade (a CF desce o mesmo), e a declividade do DRE-066 (CA-10 -> PVP-02) que passa a chegar no fundo do PVP-02.
EL-001: CX-03 deslocada 0,78 m (estava sobre o coletor executado da drenagem da quadra), os eletrodutos acompanham.
Uso: python -X utf8 aur_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, glob, json
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-APORA-PROF-AUREA\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_2026-10-23'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_2026-10-23')
MUD = os.path.join(PRE, 'AUR_mudancas_UTM.json')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\exe'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\exe')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
DATA = '23/10/2026'
FOLHAS = {'AF-002': ('24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R00', 'R01'), 'EL-001': ('24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R00', 'R01'),
          'IN-001': ('24-049-APR-CTO-ETIB-IMP-PE-IN-001-ING-R00', 'R01')}
# etiquetas do AF-002 (handle do DWG original -> texto novo): CT 188,00 com a mesma profundidade de cada caixa (dre_caixas_B.csv)
TEXTOS = [('23DC8F', 'CT.: 190.00', 'CT.: 188.00', 'CA-06'), ('23DC91', 'CF.: 189.25', 'CF.: 187.25', 'CA-06'),
          ('23DC3F', 'CT.: 190.00', 'CT.: 188.00', 'CA-07'), ('23DC41', 'CF.: 189.35', 'CF.: 187.35', 'CA-07'),
          ('23DBC4', 'CT.: 190.00', 'CT.: 188.00', 'CA-08'), ('23DC18', 'CF.: 189.40', 'CF.: 187.40', 'CA-08'),
          ('23DCBC', 'CT.: 190.00', 'CT.: 188.00', 'CA-09'), ('23DCBE', 'CF.: 189.15', 'CF.: 187.15', 'CA-09'),
          ('23DCF7', 'CT.: 190.00', 'CT.: 188.00', 'CA-10'), ('23DCF9', 'CF.: 189.07', 'CF.: 187.07', 'CA-10'),
          ('23DE1D', 'CT.: 189.00', 'CT.: 188.00', 'PVP-01'), ('23DE1F', 'CF.: 187.83', 'CF.: 186.83', 'PVP-01'),
          ('240149', 'CT.: 189.00', 'CT.: 188.00', 'PVP-02'), ('24014B', 'CF.: 188.00', 'CF.: 187.00', 'PVP-02'),
          ('2401DC', 'i=1%', 'i=0.67%', 'DRE-066')]


def mudancas():
    """as mudanças do cenário de entrega (AD) + uma marca 'texto' para o AF-002 (o rever.py só abre a folha que tem mudança)."""
    d = json.load(open(os.path.join(PRE, 'AUR_preclash_AD_mudancas.json'), encoding='utf-8'))
    M = [dict(m, folha='EL-001') for m in d['mudancas'] if m['disc'] == 'ELE']
    M.append(dict(tipo='texto', disc='DRE', folha='AF-002', trecho='CT 188 a leste', E=600072.0, N=8711370.0))
    d['mudancas'] = M
    json.dump(d, open(MUD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return M


def pranchas():
    return {FOLHAS[m['folha']][0]: FOLHAS[m['folha']][1] for m in json.load(open(MUD, encoding='utf-8'))['mudancas']}


def trocar_textos():
    """etiquetas do AF-002: o texto do handle, conferido pelo conteúdo atual, vira o novo (comando ST do revisao.lsp: mesma entidade,
    mesmo estilo e posição)."""
    import asbuilt as ab
    init0 = ab.Plano.__init__

    def init(self, *a, **k):
        init0(self, *a, **k)
        hs = {e['h']: e for e in self.textos}
        for h, de, para, rot in TEXTOS:
            e = hs.get(h)
            if e is None or re.sub(r'\\[A-Za-z][^;\\]*;|[{}]', '', str(e.get('txt', ''))).strip() != de: continue
            self.L.append(f"ST\t{h}\t{para}"); self.feitos.add(h); self.log.append(f'{rot}: {de} -> {para}')
    ab.Plano.__init__ = init


def carimbo():
    import carimbo_qg as CQ
    EXTRA = []
    _ler = CQ.ler_carimbo

    def ler2(ent, c):
        F, revs, hs, topo = _ler(ent, c)
        revs = [r for r in revs if r['rev'] not in {x['rev'] for x in EXTRA}] + EXTRA
        return F, revs, hs, topo
    CQ.ler_carimbo = ler2
    os.makedirs(os.path.join(OUT, '_copias'), exist_ok=True)
    for orig, rn in pranchas().items():
        src = os.path.join(OUT, orig + '_REVISADO.dwg')
        if not os.path.exists(src): print('sem prancha revisada:', orig); continue
        nome = orig[:-3] + rn; dst = os.path.join(OUT, nome + '.dwg')
        if os.path.exists(dst): shutil.move(dst, os.path.join(OUT, '_copias', nome + '_anterior.dwg'))
        shutil.copy2(src, dst)
        for lg in glob.glob(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo\carimbo_qg\CARIMBO_QG_logo_*.png'): shutil.copy2(lg, OUT)
        EXTRA[:] = [dict(rev=rn[1:], data='OUT/2026', desc=L1, resp='POPULUS')]
        print('==', nome)
        cp0 = CQ.trocar(dst, data=DATA, so_ler=True)['carimbos'][0]['campos']; f0 = cp0.get('FOLHA', '')
        cmp = {'FOLHA': re.sub(r'R\d\d$', rn, f0)} if f0 else {}
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


if __name__ == '__main__':
    import alh_exec, sat_exec, onn_exec          # mesmos ajustes do rever.py de Alagoinhas, Sátiro e Olindina
    alh_exec.caixa_explodida()
    alh_exec.textos_de_bloco()
    sat_exec.nota_mais_longe()
    onn_exec.texto_da_caixa()
    trocar_textos()
    os.environ.update(PRECLASH_MUDANCAS=MUD, PRECLASH_EXEC_SAIDA=OUT)          # o import do alh_exec/sat_exec/onn_exec troca
    if '--so-carimbo' not in sys.argv:
        mudancas()
        import rever
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('apora_aurea', so_comandos='--so-comandos' in sys.argv)
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
