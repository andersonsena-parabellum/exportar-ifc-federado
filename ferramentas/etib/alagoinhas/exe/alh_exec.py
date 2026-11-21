# -*- coding: utf-8 -*-
"""Alagoinhas (implantação) — pranchas no padrão de executivo final a partir do modelo compatibilizado (R03, 21/10/2026):
1) alagoinhas/ifc/alh_mudancas.py junta as mudanças (estudo de cota, contornos, caixas deslocadas) em UTM;
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez) -> EXECUTIVO_R03/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com a linha nova no quadro de revisões, na revisão seguinte, e o PDF A0.
O IN-001 (incêndio) usa o DWG salvo de novo pelo Anderson em RELATORIOS/EXECUTIVO_R03/_fonte_IN001 (o do Drive não abre no
console: ErrorStatus 53); o alh_in001_pdf.py (revisão sobre o PDF) ficou superado em 22/10.
Uso: python -X utf8 alh_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, subprocess, glob
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-ALAGOINHAS\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_R03'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_IMP_R03')
os.environ.update(PRECLASH_MUDANCAS=os.path.join(PRE, 'ALI_mudancas_UTM.json'), PRECLASH_EXEC_SAIDA=OUT)
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\ifc')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
# original -> (revisão nova, linha do quadro)
PRANCHAS = {'24-049-ALH-SLJ-ETIB-IMP-PE-AGF-001-R06': 'R07', '24-049-ALH-SLJ-ETIB-IMP-PE-ESG-001-HIG-R06': 'R07',
            '24-049-ALH-SLJ-ETIB-IMP-PE-DRE-001-DRG-R04': 'R05', '24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R07': 'R08',
            '24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R05': 'R06', '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05': 'R06'}


def carimbo():
    import carimbo_qg as CQ
    EXTRA = []
    _ler = CQ.ler_carimbo

    def ler2(ent, c):
        F, revs, hs, topo = _ler(ent, c)
        revs = [r for r in revs if r['rev'] not in {x['rev'] for x in EXTRA}] + EXTRA
        return F, revs, hs, topo
    CQ.ler_carimbo = ler2
    for orig, rn in PRANCHAS.items():
        src = os.path.join(OUT, orig + '_REVISADO.dwg')
        if not os.path.exists(src): print('sem prancha revisada:', orig); continue
        nome = orig[:-3] + rn; dst = os.path.join(OUT, nome + '.dwg')
        if os.path.exists(dst): shutil.move(dst, os.path.join(OUT, '_copias', nome + '_anterior.dwg'))
        shutil.copy2(src, dst)
        for lg in glob.glob(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo\carimbo_qg\CARIMBO_QG_logo_*.png'): shutil.copy2(lg, OUT)
        EXTRA[:] = [dict(rev=rn[1:], data='OUT/2026', desc=L1, resp='POPULUS')]
        print('==', nome)
        cp0 = CQ.trocar(dst, data='21/10/2026', so_ler=True)['carimbos'][0]['campos']; f0 = cp0.get('FOLHA', '')
        cmp = {'FOLHA': re.sub(r'R\d\d$', rn, f0)} if f0 else {}
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data='21/10/2026', campos=cmp or None)


def caixa_explodida():
    """as caixas das pranchas da implantação (QiBuilder) são LINEs soltas, não bloco nem polilinha fechada: quando o rever.py não
    acha o símbolo, as linhas/arcos que cabem inteiros no quadrado da caixa andam juntos, o texto dela e as pontas das linhas que
    chegam nela acompanham (mesmo comportamento do rever.py para bloco)."""
    import numpy as np, asbuilt as ab
    orig = ab.Plano.caixa

    def caixa(self, de, para, lado, rotulo):
        orig(self, de, para, lado, rotulo)
        if not self.log or not self.log[-1].startswith(f'{rotulo}: caixa NÃO achada'): return
        self.log.pop()
        de = np.asarray(de, float); v = np.asarray(para, float) - de; h = lado / 2 + 0.12
        dentro = [e for e in self.E if e['h'] not in self.feitos and e['typ'] in ('LINE', 'LWPOLYLINE', 'ARC') and len(e.get('pts', []))
                  and np.all(np.abs(e['pts'] - de).max(1) <= h)]
        if len(dentro) < 3:
            # caixa marcada só pelo texto "Cx. 80x80 cm" no vértice do eletroduto (EL-002): modo sem símbolo do rever.py
            s0 = self.sem_simbolo; self.sem_simbolo = True
            try: orig(self, de, para, lado, rotulo)
            finally: self.sem_simbolo = s0
            return
        for e in dentro + [e for e in self.E if e['typ'] == 'HATCH' and e['h'] not in self.feitos and np.hypot(*(e['p'] - de)) < h]:
            self.L.append(f"MV	{e['h']}	{v[0]:.4f}	{v[1]:.4f}"); self.feitos.add(e['h'])
        for e in self.textos:
            if e['h'] not in self.feitos and np.hypot(*(e['p'] - de)) < lado + 0.8:
                self.L.append(f"MV	{e['h']}	{v[0]:.4f}	{v[1]:.4f}"); self.feitos.add(e['h'])
        n = 0
        for e in self.linhas:
            if e['h'] in self.feitos or e.get('fechada'): continue
            for k, p in ((0, e['pts'][0]), (-1, e['pts'][-1])):
                if np.abs(p - de).max() < h + 0.05:
                    q = p + v; self.L.append(f"VTX	{e['h']}	{k if e['typ'] == 'LWPOLYLINE' else (0 if k == 0 else 1)}	{q[0]:.4f}	{q[1]:.4f}"); n += 1
        self.log.append(f'{rotulo}: caixa (linhas soltas, {len(dentro)}) movida, {n} ponta(s) de linha acompanharam')
    ab.Plano.caixa = caixa


def textos_de_bloco():
    """a nota "PROF." não pode cair sobre texto de bloco ("Cx. 80x80 cm", "HIDRÔMETRO", "RAMPA i=7,50%", "GUA" — Revisão de
    21/10): o Plano do rever.py passa a ver os textos de dentro dos blocos (asbuilt.entidades com blocos=True)."""
    import asbuilt as ab
    orig = ab.entidades
    ab.entidades = lambda fn, arcos=False, blocos=False: orig(fn, arcos=arcos, blocos=True)


if __name__ == '__main__':
    caixa_explodida()
    textos_de_bloco()
    if '--so-carimbo' not in sys.argv:
        import alh_mudancas
        alh_mudancas.main()
        import rever
        # o SAVEAS do rever.py para perguntando se o _REVISADO já existe (o console fica parado): a versão anterior sai do caminho
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('alagoinhas', so_comandos='--so-comandos' in sys.argv)
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
