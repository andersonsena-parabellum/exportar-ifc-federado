# -*- coding: utf-8 -*-
"""Pojuca — pranchas no padrão de executivo final (fluxo novo, 26/10/2026), como na Catu (catu/exe/cat_exec.py):
1) pojuca/ifc/pjc_mudancas.py junta as mudanças em UTM (profundidade do estudo de cota, contornos de PV/fundação, caixas de passagem,
   postes e caixas de gravidade deslocadas);
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez, espera os das outras threads) a partir do
   PROJETO_ORIGINAL -> EXECUTIVO_2026-10-26/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com as linhas novas no quadro de revisões e o PDF A0. A revisão do piloto de
   19/10 (que está no CDE) entra no quadro como a anterior.
Uso: python -X utf8 pjc_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, glob, json
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-POJUCA\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_2026-10-26'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_2026-10-25')
MUD = os.path.join(PRE, 'PJC_mudancas_UTM.json')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\exe'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\exe')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\exe'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\catu\exe')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\pojuca\ifc')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
L0 = 'ALTERAÇÃO DE TRAÇADOS E PROFUNDIDADES DAS REDES'          # linha da revisão do piloto (19/10), a que está no CDE
DATA = '26/10/2026'
_I, _C = '24-049-PJC-CTO-ETIB-IMP-PE-', '24-049-PJC-CTO-ETIB-CPS-PE-'
# folha -> (arquivo original, revisão nova, revisões intermediárias já emitidas pelo piloto)
FOLHAS = {'AF-001': (_I + 'AF-001-AFR-R00', 'R02', ['R01']), 'ESG-001': (_I + 'ESG-001-HIG-R00', 'R01', []),
          'DRE-001': (_I + 'DRE-001-DRG-R00', 'R01', []), 'EL-001': (_I + 'EL-001-ELG-R00', 'R02', ['R01']),
          'EL-002': (_I + 'EL-002-ELG-R00', 'R02', ['R01']), 'IC-001': (_I + 'IC-001-INC-R01', 'R03', ['R02']),
          'CPS-DRE-001': (_C + 'DRE-001-DRG-R01', 'R02', []), 'CPS-EL-001': (_C + 'EL-001-ELG-R01', 'R03', ['R02'])}


def ct_pelo_terreno():
    """CT/CF incoerente com o terreno executado (aplicar e avisar: CT corrigida na prancha com nova revisão): as caixas de esgoto e
    drenagem têm todas CT 61,00 no projeto e o terreno do IMP as built vai de 59,8 a 62,8. Na prancha, o texto "CT.: 61.00" de cada
    caixa (MTEXT ao lado do símbolo) passa a ter a CT do terreno, quando a diferença passa de 0,10 m; o CF não muda.
    Cada texto vai para a caixa mais perto (atribuição única, do par mais perto para o mais longe, até 4 m). ESG-001 e DRE-001 usam a
    mesma transformação local -> UTM (só translação)."""
    import csv, numpy as np, asbuilt as ab
    from preclash.terreno import Terreno
    T = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\pojuca_terreno.npz')
    t0 = np.array([572432.856588, 8626427.301743])
    CX = []
    for fn in ('PJC_fase2_ESG_caixas.csv', 'PJC_fase2_DRE_caixas.csv'):
        folha = 'ESG-001' if '_ESG_' in fn else 'DRE-001'
        for r in csv.DictReader(open(os.path.join(REL, fn), encoding='utf-8-sig'), delimiter=';'):
            try: ct = float(r['CT'])
            except (TypeError, ValueError): continue
            p = np.array([float(r['E']), float(r['N'])]); z = float(T.z([p])[0])
            CX.append(dict(caixa=r['caixa'], local=p - t0, ct=ct, novo=round(z, 2), folha=folha))
    REG = []
    import rever
    F0 = rever.Folha
    ATUAL = {}

    class Folha(F0):                                   # a folha que o rever.py está abrindo (cada prancha só com as caixas dela)
        def __init__(self, dwg, *a, **k):
            ATUAL['dwg'] = dwg; super().__init__(dwg, *a, **k)
    rever.Folha = Folha
    Pl0 = ab.Plano

    class Plano(Pl0):
        def __init__(self, ents, *a, **k):
            super().__init__(ents, *a, **k)
            txt = [e for e in self.textos if re.match(r'^\s*CT\.?\s*:?\s*\d+[.,]\d+\s*$', e['txt'])]
            if len(txt) < 10: return                    # só ESG-001 e DRE-001 têm os rótulos de CT
            f = 'ESG-001' if 'ESG-001' in ATUAL.get('dwg', '') else 'DRE-001' if 'DRE-001' in ATUAL.get('dwg', '') else None
            cx = [c for c in CX if c['folha'] == f]
            pares = sorted(((float(np.hypot(*(e['p'] - c['local']))), i, j) for i, e in enumerate(txt) for j, c in enumerate(cx)), key=lambda x: x[0])
            ut, uc = set(), set()
            for d, i, j in pares:
                if d > 4.0: break
                if i in ut or j in uc: continue
                ut.add(i); uc.add(j); e, c = txt[i], cx[j]
                if abs(c['novo'] - c['ct']) <= 0.10: continue
                self.L.append(f"ST\t{e['h']}\tCT.: {c['novo']:.2f}")
                REG.append(dict(caixa=c['caixa'], folha=f, ct_projeto=c['ct'], ct_nova=c['novo'], texto=e['h'], dist=round(d, 2)))
                self.log.append(f"CT da {c['caixa']}: {c['ct']:.2f} -> {c['novo']:.2f} (texto a {d:.1f} m)")
            json.dump(REG, open(os.path.join(OUT, 'PJC_ct_corrigidas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ab.Plano = Plano


def contorno_no_arco():
    """na EL-001/EL-002 da Pojuca parte dos eletrodutos é ARC (curvas do projetista) e o traçado do modelo junta linhas da prancha que se
    encontram num canto (EL2-001: a linha do corredor e o ramal até o QD-GUA): o Plano não acha a linha que contém o traçado inteiro e o
    contorno de PV/fundação ficava só no IFC. Quando isso acontece, cada pedaço que mudou (onde o traçado novo sai do antigo) é aplicado
    na linha ou no arco de eletroduto da prancha que contém a entrada e a saída do pedaço (até 0,10 m): a entidade antes do pedaço, o pedaço novo e a
    entidade depois (LWPOLYLINE: REPL; LINE/ARC: polilinha nova com o mesmo molde, PLC + DEL)."""
    import numpy as np, asbuilt as ab
    from shapely.geometry import LineString, Point
    orig = ab.Plano.contorno

    def contorno(self, A, B, rotulo, raio_tag=1.5):
        n0, l0 = len(self.L), len(self.log); r = orig(self, A, B, rotulo, raio_tag)
        if len(self.L) > n0 or any('igual ao original' in x for x in self.log[l0:]): return r
        if str(rotulo).startswith('CPS-'): return r       # a CPS EL-001 não desenha os eletrodutos (só tocos): o contorno fica no IFC
        A = np.asarray(A, float)[:, :2]; B = np.asarray(B, float)[:, :2]
        LA = LineString(A); fora = np.array([LA.distance(Point(q)) > 0.02 for q in B])
        pecas, k = [], 0
        while k < len(B):
            if not fora[k]: k += 1; continue
            k1 = k
            while k1 + 1 < len(B) and fora[k1 + 1]: k1 += 1
            pecas.append(B[max(k - 1, 0):min(k1 + 2, len(B))]); k = k1 + 1
        if not hasattr(self, '_geo'): self._geo = {}
        feitas = 0
        for Pc in pecas:
            cand = []
            for e in self.tracos:
                if e['typ'] not in ('LINE', 'LWPOLYLINE', 'ARC') or 'ELETRODUTO' not in str(e['lay']).upper(): continue
                if e['h'] in self.feitos and e['h'] not in self._geo: continue
                G = self._geo.get(e['h'], np.asarray(e['pts'], float)[:, :2]); Ls = LineString(G)
                d = max(Ls.distance(Point(Pc[0])), Ls.distance(Point(Pc[-1])))
                if d < 0.10: cand.append((d, e, G, Ls))
            if not cand: continue
            d, e, G, Ls = min(cand, key=lambda x: x[0])
            s0, s1 = Ls.project(Point(Pc[0])), Ls.project(Point(Pc[-1]))
            if s0 > s1: s0, s1 = s1, s0; Pc = Pc[::-1]
            S_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(G, axis=0).T))])
            Q = np.array([p for p, s in zip(G, S_) if s < s0 - 0.02] + [np.array(Ls.interpolate(s0).coords[0])] + list(Pc[1:-1])
                         + [np.array(Ls.interpolate(s1).coords[0])] + [p for p, s in zip(G, S_) if s > s1 + 0.02])
            keep = [0] + [m for m in range(1, len(Q)) if np.hypot(*(Q[m] - Q[m - 1])) > 1e-4]
            G2 = ab.simplificar(Q[keep], 0.03); self._geo[e['h']] = G2; self.feitos.add(e['h']); feitas += 1
            if not hasattr(self, '_idx'): self._idx = {}
            txt = (f"REPL	{e['h']}	" if e['typ'] == 'LWPOLYLINE' else f"PLC	{e['h']}	0	") + self._xy(G2)
            if e['h'] in self._idx: self.L[self._idx[e['h']]] = txt          # segundo pedaço na mesma entidade: a mesma linha
            else:
                self._idx[e['h']] = len(self.L); self.L.append(txt)
                if e['typ'] != 'LWPOLYLINE': self.L.append(f"DEL	{e['h']}")
            self.log.append(f'{rotulo}: pedaço novo aplicado na {e["typ"]} {e["h"]} da prancha (entrada e saída a {d:.2f} m)')
        return r

    ab.Plano.contorno = contorno


def pranchas():
    return {FOLHAS[m['folha']][0]: FOLHAS[m['folha']][1:] for m in json.load(open(MUD, encoding='utf-8'))['mudancas']}


def plotar_origem():
    """a revisão de origem plotada do DWG do projetista do mesmo jeito que a revisada (sem o CTB do projetista: regra da entrada), em
    EXECUTIVO_2026-10-26/_origem_plotada, para a conferência de cor, legenda e etiquetas (E7, E11) comparar geometria com geometria
    (o mesmo da Catu, catu/exe/cat_exec.py)."""
    import carimbo_qg as CQ, rever, cat_exec
    cat_exec.plot_janela(CQ)
    pasta = os.path.join(OUT, '_origem_plotada'); os.makedirs(pasta, exist_ok=True)
    import escolas.pojuca as S
    for f, (orig, _, _) in FOLHAS.items():
        if os.path.exists(os.path.join(pasta, orig + '.pdf')): continue
        src = os.path.join(S.BASE, S._DWG[f].replace('/', os.sep)); cp = os.path.join(pasta, orig + '.dwg'); shutil.copy2(src, cp)
        car = CQ.trocar(cp, so_ler=True)['carimbos'][0]; cat_exec.JANELA['canto'] = car['canto']
        pdf = os.path.join(pasta, orig + '.pdf')
        lsp = os.path.join(pasta, orig + '_plot.lsp'); open(lsp, 'w', encoding='ascii').write(CQ.lisp_pdf(os.path.join(pasta, orig), [car['layout']]))
        print(orig, rever.console(cp, ['SECURELOAD 0', 'FILEDIA 0', 'CMDDIA 0', '(load "%s")' % lsp.replace(os.sep, '/'), '_.QUIT', '_Y'], cp + '.plot.log', {})[-80:],
              os.path.exists(pdf))


def carimbo():
    import carimbo_qg as CQ, cat_exec
    cat_exec.plot_janela(CQ)            # PDF pela janela da folha A0 a partir do canto do carimbo (Catu, 25/10)
    EXTRA = []
    _ler = CQ.ler_carimbo

    def ler2(ent, c):
        F, revs, hs, topo = _ler(ent, c)
        revs = [r for r in revs if r['rev'] not in {x['rev'] for x in EXTRA}] + EXTRA
        return F, revs, hs, topo
    CQ.ler_carimbo = ler2
    os.makedirs(os.path.join(OUT, '_copias'), exist_ok=True)
    for orig, (rn, inter) in pranchas().items():
        src = os.path.join(OUT, orig + '_REVISADO.dwg')
        if not os.path.exists(src): print('sem prancha revisada:', orig); continue
        nome = orig[:-3] + rn; dst = os.path.join(OUT, nome + '.dwg')
        if os.path.exists(dst): shutil.move(dst, os.path.join(OUT, '_copias', nome + '_anterior.dwg'))
        shutil.copy2(src, dst)
        for lg in glob.glob(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo\carimbo_qg\CARIMBO_QG_logo_*.png'): shutil.copy2(lg, OUT)
        EXTRA[:] = [dict(rev=r[1:], data='OUT/2026', desc=L0, resp='POPULUS') for r in inter] + [dict(rev=rn[1:], data='OUT/2026', desc=L1, resp='POPULUS')]
        print('==', nome)
        car0 = CQ.trocar(dst, data=DATA, so_ler=True)['carimbos'][0]; cp0 = car0['campos']; f0 = cp0.get('FOLHA', '')
        cat_exec.JANELA['canto'] = car0['canto']
        cmp = {'FOLHA': re.sub(r'R\d\d$', rn, f0)} if f0 else {}
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


if __name__ == '__main__':
    import alh_exec, sat_exec, onn_exec, cat_exec          # mesmos ajustes do rever.py de Alagoinhas, Sátiro, Olindina e Catu
    alh_exec.caixa_explodida()
    alh_exec.textos_de_bloco()
    sat_exec.caixas_e_postes()
    sat_exec.nota_mais_longe()
    sat_exec.caixa_inteira()
    onn_exec.texto_da_caixa()
    cat_exec.contorno_exato()
    cat_exec.nota_na_etiqueta()
    contorno_no_arco()
    ct_pelo_terreno()
    os.environ.update(PRECLASH_MUDANCAS=MUD, PRECLASH_EXEC_SAIDA=OUT)          # o import do alh_exec/sat_exec/onn_exec troca
    if '--so-carimbo' not in sys.argv:
        import pjc_mudancas
        pjc_mudancas.main()
        import rever
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('pojuca', so_comandos='--so-comandos' in sys.argv)
    if '--origem' in sys.argv:
        plotar_origem(); sys.exit()
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
