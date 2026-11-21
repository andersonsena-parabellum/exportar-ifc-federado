# -*- coding: utf-8 -*-
"""Sátiro Dias — pranchas no padrão de executivo final a partir do modelo compatibilizado (fluxo novo, 21/10/2026), como em
Alagoinhas (alagoinhas/exe/alh_exec.py):
1) satiro/ifc/sat_mudancas.py junta as mudanças (estudo de cota, contornos, caixas deslocadas) em UTM;
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez) -> EXECUTIVO_2026-10-21/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com a linha nova no quadro de revisões, na revisão seguinte, e o PDF A0.
Uso: python -X utf8 sat_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, glob
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-SATIRO-DIAS\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_2026-10-21'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_2026-10-21')
os.environ.update(PRECLASH_MUDANCAS=os.path.join(PRE, 'SAT_mudancas_UTM.json'), PRECLASH_EXEC_SAIDA=OUT)
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\ifc'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\exe')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
DATA = '21/10/2026'
# original -> revisão nova
PRANCHAS = {'24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00': 'R01', '24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00': 'R01',
            '24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01': 'R02', '24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R01': 'R02',
            '24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03': 'R04', '24-049-STK-XXX-ETIB-CPS-PE-DRE-001-DRG-R01': 'R02',
            '24-049-STK-XXX-CP1-CPS-PE-ELE-001-ELG-R00': 'R01'}


# o arquivo do projetista do campo vem como CP1-CPS; a lista mestra (24-049_STK_LISTA MESTRA_R07) dá ETIB-CPS: a revisão sai com o
# código da lista mestra
NOME_LM = {'24-049-STK-XXX-CP1-CPS-PE-ELE-001-ELG-R00': '24-049-STK-XXX-ETIB-CPS-PE-ELE-001-ELG-R00'}


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
    for orig, rn in PRANCHAS.items():
        src = os.path.join(OUT, orig + '_REVISADO.dwg')
        if not os.path.exists(src): print('sem prancha revisada:', orig); continue
        nome = NOME_LM.get(orig, orig)[:-3] + rn; dst = os.path.join(OUT, nome + '.dwg')
        if os.path.exists(dst): shutil.move(dst, os.path.join(OUT, '_copias', nome + '_anterior.dwg'))
        shutil.copy2(src, dst)
        for lg in glob.glob(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo\carimbo_qg\CARIMBO_QG_logo_*.png'): shutil.copy2(lg, OUT)
        EXTRA[:] = [dict(rev=rn[1:], data='OUT/2026', desc=L1, resp='POPULUS')]
        print('==', nome)
        cp0 = CQ.trocar(dst, data=DATA, so_ler=True)['carimbos'][0]['campos']; f0 = cp0.get('FOLHA', '')
        cmp = {'FOLHA': re.sub(r'R\d\d$', rn, f0)} if f0 else {}
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


def caixas_e_postes():
    """o que o rever.py não faz nas pranchas da Sátiro (exec de 21/10):
    - poste da iluminação/campo deslocado com a caixa da base: na EL-001 o poste é um bloco só ("POSTE UMA PETALA", com a caixa
      desenhada dentro), e o rever.py não mexe em poste; aqui o bloco anda junto;
    - caixa de passagem de alarme/elétrica deslocada por onde o eletroduto da prancha passa direto (sem vértice na caixa, "0 ponta(s)
      acompanharam"): o eletroduto ganha um vértice na posição nova da caixa, como no modelo (os dois trechos chegam nela)."""
    import re as _re, numpy as np, asbuilt as ab
    orig = ab.Plano.caixa
    RX = _re.compile(r'ELETRODUTO|ALARME|DETEC|SDAI|F_PCI', _re.I)

    def caixa(self, de, para, lado, rotulo):
        n0 = len(self.log); orig(self, de, para, lado, rotulo)
        de = np.asarray(de, float); v = np.asarray(para, float) - de; novo = de + v
        msg = ' '.join(self.log[n0:])
        if 'POSTE' in rotulo:
            blocos = [e for e in self.E if e['typ'] == 'INSERT' and e['h'] not in self.feitos and 'POSTE' in str(e.get('nome') or e.get('blk') or '').upper()
                      and np.hypot(*(np.asarray(e['p'])[:2] - de)) < 1.0]
            for e in blocos: self.L.append(f"MV	{e['h']}	{v[0]:.4f}	{v[1]:.4f}"); self.feitos.add(e['h'])
            if blocos: self.log[n0:] = [f'{rotulo}: poste (bloco) deslocado {np.hypot(*v):.2f} m junto com a caixa da base']
            return
        if ' 0 ponta(s)' not in msg and 'nada a mover' not in msg: return
        n = 0
        for e in self.E:
            if e['typ'] not in ('LINE', 'LWPOLYLINE') or e['h'] in self.feitos or not RX.search(str(e.get('lay', ''))): continue
            P = np.asarray(e['pts'], float)[:, :2]
            if len(P) < 2: continue
            dv = np.hypot(*(P - de).T); j = int(np.argmin(dv))
            if dv[j] < lado / 2 + 0.15:                  # vértice do eletroduto na caixa (ponta ou meio da polilinha): ele anda
                Q = P.copy(); Q[j] = Q[j] + v; xy = '	'.join(f'{x:.4f}	{y:.4f}' for x, y in Q)
                if e['typ'] == 'LWPOLYLINE': self.L.append(f"REPL	{e['h']}	{xy}")
                else: self.L.append(f"PLC	{e['h']}	0	{xy}"); self.L.append(f"DEL	{e['h']}")
                self.feitos.add(e['h']); n += 1; continue
            best = None
            for i, (a, b) in enumerate(zip(P[:-1], P[1:])):
                ab_ = b - a; L2 = float(ab_ @ ab_)
                if L2 < 1e-9: continue
                t = float(np.clip((de - a) @ ab_ / L2, 0, 1)); d = float(np.hypot(*(a + ab_ * t - de)))
                if 0.02 < t < 0.98 and d < lado / 2 + 0.05 and (best is None or d < best[0]): best = (d, i)
            if best is None: continue
            i = best[1]; Q = np.vstack([P[:i + 1], novo[None], P[i + 1:]])
            xy = '	'.join(f'{x:.4f}	{y:.4f}' for x, y in Q)
            if e['typ'] == 'LWPOLYLINE': self.L.append(f"REPL	{e['h']}	{xy}")
            else: self.L.append(f"PLC	{e['h']}	0	{xy}"); self.L.append(f"DEL	{e['h']}")
            self.feitos.add(e['h']); n += 1
        if n: self.log.append(f'{rotulo}: {n} eletroduto(s) que passavam pela caixa ganharam o vértice na posição nova')
    ab.Plano.caixa = caixa


def caixa_inteira():
    """caixa da drenagem pluvial deslocada na ESG-001 (CA-01 e CA-05, decisão do Anderson de 22/10):
    - o contorno do símbolo (polilinha "Simbolos" de 6 vértices, um pouco maior que o quadrado procurado) só tinha a 1ª e a última
      ponta levadas como "linha que chega", e ficava o quadrado velho no lugar: polilinha inteira dentro da caixa anda inteira;
    - o tubo que chega na caixa desenhado como MLINE (o rever.py não lê MLINE) não acompanhava: a ponta vai para a posição nova e o
      tubo é redesenhado com as duas linhas do próprio estilo (mesma layer e cor), no lugar da MLINE."""
    import numpy as np, asbuilt as ab
    ent0 = ab.entidades

    def entidades(fn, arcos=False, blocos=False):
        out = ent0(fn, arcos=arcos, blocos=blocos)
        _, model = ab.dxfgeo.parse(fn)
        for typ, data in model:
            d = ab.dxfgeo._first(data)
            if typ != 'MLINE' or str(d.get(67, '0')).strip() == '1' or 5 not in d: continue
            xs = [float(v) for c, v in data if c == 11]; ys = [float(v) for c, v in data if c == 21]
            off = sorted({abs(float(v)) for c, v in data if c == 41 and abs(float(v)) > 1e-6})
            if len(xs) >= 2 and off:      # 'mpts' (não 'pts'): fora das linhas que o Plano edita
                out.append({'h': str(d[5]).strip(), 'typ': 'MLINE', 'lay': d.get(8, ''), 'mpts': np.column_stack([xs, ys]), 'off': off[0]})
        return out
    ab.entidades = entidades
    orig = ab.Plano.caixa

    def paralelas(P, o):
        U = np.diff(P, axis=0); U = U / np.hypot(*U.T)[:, None]; N = np.column_stack([-U[:, 1], U[:, 0]])
        M = [N[0]] + [(a + b) / np.hypot(*(a + b)) / max(0.2, float((a + b) @ b / np.hypot(*(a + b)))) for a, b in zip(N[:-1], N[1:])] + [N[-1]]
        M = np.array(M)
        return P + M * o, P - M * o

    def caixa(self, de, para, lado, rotulo):
        n0 = len(self.L); orig(self, de, para, lado, rotulo)
        de = np.asarray(de, float); v = np.asarray(para, float) - de
        if np.hypot(*v) < 1e-3 or len(self.L) == n0: return
        h = lado / 2 + 0.25
        inteiras = {e['h'] for e in self.E if e['typ'] == 'LWPOLYLINE' and len(e['pts']) > 2 and np.all(np.abs(e['pts'] - de).max(1) <= h)
                    and any(x.startswith(f"VTX\t{e['h']}\t") for x in self.L[n0:])}
        if inteiras:
            self.L[n0:] = [x for x in self.L[n0:] if x.split('\t')[0] != 'VTX' or x.split('\t')[1] not in inteiras]
            for k in sorted(inteiras): self.L.append(f"MV\t{k}\t{v[0]:.4f}\t{v[1]:.4f}"); self.feitos.add(k)
        n = 0
        for e in self.E:
            if e['typ'] != 'MLINE' or e['h'] in self.feitos: continue
            P = e['mpts'].copy(); mud = False
            for k in (0, -1):
                if np.hypot(*(P[k] - de)) < lado / 2 + 0.15: P[k] = P[k] + v; mud = True
            if not mud: continue
            for Q in paralelas(P, e['off']):
                self.L.append(f"PLC\t{e['h']}\t0\t" + '\t'.join(f'{x:.4f}\t{y:.4f}' for x, y in Q))
            self.L.append(f"DEL\t{e['h']}"); self.feitos.add(e['h']); n += 1
        if inteiras or n: self.log.append(f'{rotulo}: {len(inteiras)} contorno(s) do símbolo inteiro(s), {n} tubo(s) MLINE acompanharam')
    ab.Plano.caixa = caixa


def trocar_textos():
    """etiquetas de cota trocadas na própria prancha (sat_mudancas.TEXTOS): o texto igual ao atual no ponto (a 10 cm) vira o novo
    (comando ST do revisao.lsp, mesma entidade, mesmo estilo), como na Olindina."""
    import numpy as np, asbuilt as ab, rever, sat_mudancas as SM
    import escolas.satiro as S
    init0 = ab.Plano.__init__

    def init(self, *a, **k):
        init0(self, *a, **k)
        for t in SM.TEXTOS:
            for rot, tt in rever.transformacoes(S).values():
                c = np.array([t['E'], t['N']]) - tt; a_ = np.radians(-rot); R = np.array([[np.cos(a_), -np.sin(a_)], [np.sin(a_), np.cos(a_)]]); q = R @ c
                # o texto no ponto (a 10 cm; a etiqueta "i=1%" do AP-108 fica a menos de 1,5 m da do ESG-014)
                cand = [e for e in self.textos if str(e.get('txt', '')).strip() == t['de'] and e['h'] not in self.feitos
                        and np.hypot(*(np.asarray(e["p"])[:2] - q)) < 0.10]
                if cand:
                    e = min(cand, key=lambda e: np.hypot(*(np.asarray(e['p'])[:2] - q)))
                    self.L.append(f"ST	{e['h']}	{t['para']}"); self.feitos.add(e['h']); self.log.append(f"{t['caixa']}: etiqueta {t['de']} -> {t['para']}")
    ab.Plano.__init__ = init


def nota_mais_longe():
    """a nota "PROF." que não acha lugar livre em 4 m (o AF-16 corre colado no texto "REDE FUTURA SE NECESSÁRIO" de 27 m da AF-001;
    o EL-002 junto de "Cx. 60x60 cm" e "Ø4\"") procura até 8 m em volta, em vez de ficar por cima de outro texto (Revisão, E6)."""
    import inspect, textwrap, asbuilt as ab
    src = textwrap.dedent(inspect.getsource(ab.Plano.nota))
    velho = '(0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)'
    assert velho in src
    src = src.replace(velho, '(0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0)')
    # o filtro de textos "perto" mede pelo centro do retângulo: o "REDE FUTURA SE NECESSÁRIO" (27 m) tem o centro longe da nota
    # e ficava de fora; com 40 m entra
    velho2 = '< w + 6)'
    assert velho2 in src
    src = src.replace(velho2, '< w + 40)')
    # E11 (PDCA A3, 22/10): a nota não sai maior que as etiquetas de rede do projetista (o molde perto do trecho podia ser um texto
    # grande, 6 a 8 pt contra 3,4 pt das etiquetas na EL-001/EL-002/IN-001): altura limitada à mais comum das etiquetas da folha
    velho3 = "h = molde['alt'] if molde['alt'] > 0 else 0.25"
    assert velho3 in src
    src = src.replace(velho3, "h = min(molde['alt'] if molde['alt'] > 0 else 0.25, _alt_etiqueta(self))")
    import collections
    rx = re.compile(r'(Ø|ø|DN\s*\d|\d+\s*mm\b|\d+(?:\.\d/\d)?"|\bPVC\b|PEAD|\bC[TFSE]\b|i\s*=)', re.I)

    def _alt_etiqueta(pl):
        if not hasattr(pl, '_alt_etq'):
            c = collections.Counter(round(t['alt'], 3) for t in pl.textos if t['alt'] > 0 and rx.search(str(t.get('txt', ''))))
            pl._alt_etq = c.most_common(1)[0][0] if c else 9e9
        return pl._alt_etq
    ab._alt_etiqueta = _alt_etiqueta
    ns = {}; exec(compile(src, ab.__file__, 'exec'), ab.__dict__, ns)
    ab.Plano.nota = ns['nota']


if __name__ == '__main__':
    import alh_exec                      # mesmos ajustes do rever.py de Alagoinhas (caixa em linhas soltas, textos de bloco)
    alh_exec.caixa_explodida()
    alh_exec.textos_de_bloco()
    nota_mais_longe()
    caixas_e_postes()
    caixa_inteira()
    trocar_textos()
    os.environ.update(PRECLASH_MUDANCAS=os.path.join(PRE, 'SAT_mudancas_UTM.json'), PRECLASH_EXEC_SAIDA=OUT)   # o import do alh_exec troca
    if '--so-carimbo' not in sys.argv:
        import sat_mudancas
        sat_mudancas.main()
        import rever
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('satiro', so_comandos='--so-comandos' in sys.argv)
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
