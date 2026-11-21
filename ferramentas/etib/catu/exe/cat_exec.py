# -*- coding: utf-8 -*-
"""Catu — pranchas no padrão de executivo final (fluxo novo, 25/10/2026), como na Sátiro (satiro/exe/sat_exec.py) e na Prof. Áurea
(aurea/exe/aur_exec.py):
1) catu/ifc/cat_mudancas.py junta as mudanças em UTM (profundidade do estudo de cota, contornos, traçado novo do EL2-025, caixas
   deslocadas, hidrante H-10 recuado, chegadas de gravidade mais altas);
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez) -> EXECUTIVO_2026-10-25/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com a linha nova no quadro de revisões, na revisão seguinte, e o PDF A0.
Uso: python -X utf8 cat_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, glob, json
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-CATU\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_2026-10-25'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_2026-10-25')
MUD = os.path.join(PRE, 'CAT_mudancas_UTM.json')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\exe'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\exe')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\catu\ifc')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
DATA = '25/10/2026'
FOLHAS = {'AGF-001': ('24-049-CAU-RNV-ETIB-IMP-PE-AGF-001-R02', 'R03'), 'ESG-001': ('24-049-CAU-RNV-ETIB-IMP-PE-ESG-001-HIG-R02', 'R03'),
          'DRE-001': ('24-049-CAU-RNV-ETIB-IMP-PE-DRE-001-DRG-R02', 'R03'), 'EL-001': ('24-049-CAU-RNV-ETIB-IMP-PE-EL-001-ELG-R05', 'R06'),
          'EL-002': ('24-049-CAU-RNV-ETIB-IMP-PE-EL-002-ELG-R02', 'R03'), 'INC-001': ('24-049-CAU-RNV-ETIB-IMP-PE-INC-001-ING-R03', 'R04')}


def contorno_exato():
    """mudança de traçado casada com a entidade inteira da prancha (cat_mudancas.ajustar_ao_desenho: o traçado antigo É a linha da
    prancha): só essa entidade muda. Sem isso, no banco de eletrodutos (uma linha por eletroduto, 0,07 a 0,2 m uma da outra) a
    tolerância de 0,30 m do rever.py pegava as quatro linhas no primeiro eletroduto e as juntava num traçado só."""
    import numpy as np, asbuilt as ab
    orig = ab.Plano.contorno

    def contorno(self, A, B, rotulo, raio_tag=1.5):
        A_ = np.asarray(A, float)
        exata = next((e for e in self.linhas if e['h'] not in self.feitos and len(e['pts']) == len(A_)
                      and np.abs(np.asarray(e['pts'], float)[:, :2] - A_).max() < 1e-3), None)
        if exata is None: return orig(self, A, B, rotulo, raio_tag)
        outras = {e['h'] for e in self.linhas if e is not exata and e['h'] not in self.feitos}
        self.feitos |= outras
        try:
            return orig(self, A, B, rotulo, raio_tag)
        finally:
            self.feitos -= outras
    ab.Plano.contorno = contorno


def nota_na_etiqueta():
    """nota PROF. nunca maior que as etiquetas de rede do projetista (E11): o teto do EXECUTIVO_NOTA_ALT passa a ser, em cada folha,
    a altura mais comum das etiquetas (diâmetro, material, cota); na AGF-001 o molde de 0,50 m saía com 9,9 pt e as etiquetas têm 7,9 pt."""
    import collections, numpy as np, asbuilt as ab
    rx = re.compile(r'Ø|%%C|DN\s*\d|\d+\s*MM\b|\bPVC\b|PEAD|\bC[TFSE]\b|\bGI\b|I\s*=')

    def alt_etq(pl):
        # moda das etiquetas dentro da faixa EXECUTIVO_NOTA_ALT: fora dela há MTEXT de 0,05 m com a altura no código (\H), que
        # viravam a moda e a nota saía com 1 pt; e o sat_exec.nota_mais_longe reservava o lugar da nota com essa altura, menor que o
        # texto copiado (no INC-001 duas notas caíram uma sobre a outra)
        if not hasattr(pl, '_alt_etq'):
            lo, hi = getattr(pl, 'alt_nota', None) or (0.0, 9e9)
            c = collections.Counter(round(t['alt'], 3) for t in pl.textos if lo <= t['alt'] <= hi and rx.search(ab._limpo(t.get('txt', '')).upper()))
            pl._alt_etq = c.most_common(1)[0][0] if c else hi
        return pl._alt_etq
    ab._alt_etiqueta = alt_etq                 # o nota() do sat_exec lê este nome do módulo na hora da chamada
    orig = ab.Plano.nota

    def nota(self, P, texto, rotulo, disc=None):
        if not hasattr(self, '_alt0'):
            self._alt0 = getattr(self, 'alt_nota', None) or (0.0, 9e9); a = alt_etq(self)
            self.alt_nota = (min(self._alt0[0], a), a + 1e-3)
        n0 = len(getattr(self, 'notas_novas', []))
        r = orig(self, P, texto, rotulo, disc)
        # a reserva da nota cresce meia altura para cima e para baixo e 10 % nas pontas: o MTEXT copiado pode ter outro ponto de anexo
        # (no INC-001 a "PROF. 0,95 m" do alarme entrou colada embaixo da "PROF. 1,75 m" do hidrante, uma por cima da outra no PDF)
        if len(getattr(self, 'notas_novas', [])) > n0:
            R = self.notas_novas[-1]; u = R[1] - R[0]; v = R[3] - R[0]
            self.notas_novas[-1] = np.array([R[0] - 0.1 * u - 0.5 * v, R[1] + 0.1 * u - 0.5 * v, R[2] + 0.1 * u + 0.5 * v, R[3] - 0.1 * u + 0.5 * v])
        return r
    ab.Plano.nota = nota


def pranchas():
    return {FOLHAS[m['folha']][0]: FOLHAS[m['folha']][1] for m in json.load(open(MUD, encoding='utf-8'))['mudancas']}


JANELA = {}


def plot_janela(CQ):
    """o PDF sai pela janela da folha A0 (1189 × 841 mm, canto inferior direito = canto do carimbo), não pela extensão do layout: na
    DRE-001 há blocos e textos do projetista fora da folha, e a extensão encolhia a folha (o carimbo não ficava no canto do PDF)."""
    def lisp_pdf(base_pdf, layouts):
        x1, y1 = JANELA['canto']; x0, y0 = x1 - 1189.0, y1; xb, yb = x1, y1 + 841.0
        q = lambda s_: '"' + CQ.u(s_).replace('\\', '\\\\').replace('"', '\\"') + '"'
        L = ['(setvar "BACKGROUNDPLOT" 0) (setvar "FILEDIA" 0) (setvar "CMDECHO" 1)']
        for lay in layouts:
            L.append(f'(setvar "CTAB" {q(lay)})')
            L.append(f'(command "_.-PLOT" "_Y" {q(lay)} "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_W" '
                     f'"{x0:.4f},{y0:.4f}" "{xb:.4f},{yb:.4f}" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N" '
                     f'{q(base_pdf.replace(os.sep, "/") + ("_" + re.sub(r"[^A-Za-z0-9-]+", "_", lay) if len(layouts) > 1 else "") + ".pdf")} "_N" "_Y")')
        return '\n'.join(L + ['(princ)']) + '\n'
    CQ.lisp_pdf = lisp_pdf


def plotar_origem():
    """a revisão de origem plotada do DWG do projetista do mesmo jeito que a revisada (sem o CTB do projetista, que não veio: regra da
    entrada), em EXECUTIVO_2026-10-25/_origem_plotada: a conferência de cor, legenda e etiquetas (E7, E11) compara geometria com
    geometria, não o PDF do projetista (plotado com o CTB dele) com o nosso."""
    import carimbo_qg as CQ, rever
    plot_janela(CQ)
    pasta = os.path.join(OUT, '_origem_plotada'); os.makedirs(pasta, exist_ok=True)
    import escolas.catu as S
    for f, (orig, _) in FOLHAS.items():
        if os.path.exists(os.path.join(pasta, orig + '.pdf')): continue
        src = os.path.join(S.BASE, S._DWG[f].replace('/', os.sep)); cp = os.path.join(pasta, orig + '.dwg'); shutil.copy2(src, cp)
        car = CQ.trocar(cp, so_ler=True)['carimbos'][0]; JANELA['canto'] = car['canto']
        pdf = os.path.join(pasta, orig + '.pdf')
        lsp = os.path.join(pasta, orig + '_plot.lsp'); open(lsp, 'w', encoding='ascii').write(CQ.lisp_pdf(os.path.join(pasta, orig), [car['layout']]))
        print(orig, rever.console(cp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % lsp.replace(os.sep, '/'), '_.QUIT', '_Y'], cp + '.plot.log', {})[-80:],
              os.path.exists(pdf))


def carimbo():
    import carimbo_qg as CQ
    plot_janela(CQ)
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
        car0 = CQ.trocar(dst, data=DATA, so_ler=True)['carimbos'][0]; cp0 = car0['campos']; f0 = cp0.get('FOLHA', '')
        JANELA['canto'] = car0['canto']
        cmp = {'FOLHA': re.sub(r'R\d\d$', rn, f0)} if f0 else {}
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


if __name__ == '__main__':
    import alh_exec, sat_exec, onn_exec          # mesmos ajustes do rever.py de Alagoinhas, Sátiro e Olindina
    alh_exec.caixa_explodida()
    alh_exec.textos_de_bloco()
    sat_exec.caixas_e_postes()
    sat_exec.nota_mais_longe()
    sat_exec.caixa_inteira()
    onn_exec.texto_da_caixa()
    contorno_exato()
    nota_na_etiqueta()
    os.environ.update(PRECLASH_MUDANCAS=MUD, PRECLASH_EXEC_SAIDA=OUT)          # o import do alh_exec/sat_exec/onn_exec troca
    if '--so-carimbo' not in sys.argv:
        import cat_mudancas
        cat_mudancas.main()
        import rever
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('catu', so_comandos='--so-comandos' in sys.argv)
    if '--origem' in sys.argv:
        plotar_origem(); sys.exit()
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
