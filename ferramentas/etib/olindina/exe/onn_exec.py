# -*- coding: utf-8 -*-
"""Olindina — pranchas no padrão de executivo final a partir do modelo compatibilizado (fluxo novo, 21/10/2026), como na Sátiro
(satiro/exe/sat_exec.py) e em Alagoinhas (alagoinhas/exe/alh_exec.py):
1) olindina/ifc/onn_mudancas.py junta as mudanças (estudo de cota, caixas deslocadas) em UTM;
2) preclash/executivo/rever.py planeja e aplica cada prancha no accoreconsole (um por vez) -> EXECUTIVO_2026-10-21/<original>_REVISADO.dwg;
3) carimbo QG as built (preclash/executivo/carimbo_qg.py) com a linha nova no quadro de revisões, na revisão seguinte, e o PDF A0.
Só sai revisada a folha que tem mudança (a cota da água fria é premissa e não muda a prancha).
Uso: python -X utf8 onn_exec.py [--so-comandos] [--sem-carimbo] [--so-carimbo]"""
import os, sys, re, shutil, glob, json
sys.stdout.reconfigure(encoding='utf-8')
REL = r'D:\Projeto Modelagem\ETIB-OLINDINA\RELATORIOS'
OUT = os.path.join(REL, 'EXECUTIVO_2026-10-21'); PDF = os.path.join(OUT, 'PDF'); os.makedirs(PDF, exist_ok=True)
PRE = os.path.join(REL, 'PRECLASH_2026-10-21')
MUD = os.path.join(PRE, 'ONN_mudancas_UTM.json')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash\executivo'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\olindina\ifc'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\alagoinhas\exe')
sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\satiro\exe')
L1 = 'COMPATIBILIZAÇÃO COM AS DEMAIS DISCIPLINAS'
DATA = '21/10/2026'
# folha -> (original, revisão nova); só as que têm mudança entram (onn_mudancas)
FOLHAS = {'AF-001': ('24-049-ONN-CTO-ETIB-IMP-PE-AF-001-AFR-R00', 'R01'), 'ESG-001': ('24-049-ONN-CTO-ETIB-IMP-PE-ESG-001-HIG-R00', 'R01'),
          'DRE-001': ('24-049-ONN-CTO-ETIB-IMP-PE-DRE-001-DRG-R00', 'R01'), 'EL-001': ('24-049-ONN-CTO-ETIB-IMP-PE-EL-001-ELG-R00', 'R01'),
          'IN-001': ('24-049-ONN-CTO-ETIB-IMP-PE-IN-001-ING-R00', 'R01')}


def pranchas():
    fs = {m['folha'] for m in json.load(open(MUD, encoding='utf-8'))['mudancas']}
    return {FOLHAS[f][0]: FOLHAS[f][1] for f in sorted(fs)}


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
        # o DRE-001 é o mesmo arquivo do ESG-001 e veio com o código curto do esgoto: a folha da drenagem leva o dela
        if '-DRE-001-' in orig and cmp.get('FOLHA', '').startswith('ESG_'): cmp['FOLHA'] = 'DRE_' + cmp['FOLHA'][4:]
        if cp0.get('ESCALA', '').strip().upper() in ('', 'ESCALA'): cmp['ESCALA'] = 'INDICADA'
        CQ.trocar(dst, pdf_dir=PDF, data=DATA, campos=cmp or None)


def _wipeouts(dxf):
    """(handle, ponto de inserção) dos WIPEOUT do espaço do modelo (o asbuilt não lê WIPEOUT)."""
    L = open(dxf, encoding='utf-8', errors='replace').read().split('\n'); out = []; i = 0
    while i < len(L) - 1:
        if L[i].strip() == '0' and L[i + 1].strip() == 'WIPEOUT':
            j = i + 2; d = {}
            while L[j].strip() != '0': d.setdefault(L[j].strip(), L[j + 1].strip()); j += 2
            out.append((d.get('5'), float(d.get('10', 0)), float(d.get('20', 0)))); i = j
        else: i += 2
    return out


def texto_da_caixa():
    """na EL-001 o texto "Cx. 80x80 cm" fica a até 2 m da caixa (o rever.py só leva o texto a até lado + 0,8 m): o texto "Cx." mais
    perto da posição antiga, a até 2,5 m, anda junto com a caixa. O símbolo da caixa tem um WIPEOUT (o asbuilt não lê): ele anda junto."""
    import numpy as np, asbuilt as ab
    orig = ab.Plano.caixa
    ent0 = ab.entidades; arq = {}

    def entidades(dxf, *a, **k):
        arq['dxf'] = dxf; return ent0(dxf, *a, **k)
    ab.entidades = entidades

    def caixa(self, de, para, lado, rotulo):
        n0 = len(self.L); orig(self, de, para, lado, rotulo)
        de = np.asarray(de, float); v = np.asarray(para, float) - de
        for h, x, y in (_wipeouts(arq['dxf']) if arq.get('dxf') else []):
            if h not in self.feitos and abs(x - de[0]) <= lado / 2 + 0.12 and abs(y - de[1]) <= lado / 2 + 0.12:
                self.L.append(f"MV	{h}	{v[0]:.4f}	{v[1]:.4f}"); self.feitos.add(h)
        cx = [e for e in self.textos if e['h'] not in self.feitos and re.match(r'\s*Cx\.', str(e.get('t') or e.get('txt') or ''))
              and np.hypot(*(np.asarray(e['p'])[:2] - de)) < 2.5]
        if cx:
            e = min(cx, key=lambda e: np.hypot(*(np.asarray(e['p'])[:2] - de)))
            self.L.append(f"MV	{e['h']}	{v[0]:.4f}	{v[1]:.4f}"); self.feitos.add(e['h'])
            self.log.append(f'{rotulo}: texto da caixa acompanhou')
    ab.Plano.caixa = caixa


def trocar_textos():
    """etiqueta de cota corrigida (onn_mudancas.TEXTOS): o texto igual ao atual a até 1,5 m do ponto vira o novo (comando ST do
    revisao.lsp, mesma entidade, mesmo estilo)."""
    import numpy as np, asbuilt as ab, rever, onn_mudancas as OM
    init0 = ab.Plano.__init__

    def init(self, *a, **k):
        init0(self, *a, **k)
        for t in OM.TEXTOS:
            for tr in rever.transformacoes(__import__('escolas.olindina', fromlist=['x'])).values():
                rot, tt = tr
                c = np.array([t['E'], t['N']]) - tt; a_ = np.radians(-rot); R = np.array([[np.cos(a_), -np.sin(a_)], [np.sin(a_), np.cos(a_)]]); q = R @ c
                for e in self.textos:
                    if str(e.get('txt', '')).strip() == t['de'] and np.hypot(*(np.asarray(e['p'])[:2] - q)) < 1.5 and e['h'] not in self.feitos:
                        self.L.append(f"ST	{e['h']}	{t['para']}"); self.feitos.add(e['h']); self.log.append(f"{t['caixa']}: etiqueta {t['de']} -> {t['para']}")
    ab.Plano.__init__ = init


def rede_existente(fator=0.65, cor=136):
    """ESG-001 / DRE-001 (Anderson, 22/10/2026: "ficou um rosa feião, e os textos estão grandes, aí ficou sobreposto"): a rede
    existente do cadastro (layer "Tubulação existente") passa a ciano escuro (136: o cinza ficou apagado e o laranja é o esgoto de
    gordura na legenda, Anderson 22/10), os textos dela a 65 % da altura e a legenda ganha a linha dela (onn_existente.lsp),
    no _REVISADO, antes do carimbo. Um console por vez (acc_fila.ps1)."""
    import subprocess
    lsp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'onn_existente.lsp').replace(chr(92), '/')
    fila = 'D:/Projeto Modelagem/FERRAMENTAS/georef/work/OLINDINA/scripts/acc_fila.ps1'
    for f in ('ESG-001-HIG', 'DRE-001-DRG'):
        dwg = os.path.join(OUT, f'24-049-ONN-CTO-ETIB-IMP-PE-{f}-R00_REVISADO.dwg')
        if not os.path.exists(dwg): continue
        q = lambda x: "'" + x.replace("'", "''") + "'"
        linhas = ['SECURELOAD 0', 'FILEDIA 0', f'(load "{lsp}")', 'ONNEXIST', 'ONNLEG', '_.QSAVE', '_.QUIT', '_Y']
        ps = (f"& {q(fila)} -Dwg {q(dwg)} -ScrLines @(" + ','.join(q(x) for x in linhas) + f") -Log {q(dwg + '.exist.log')} -TimeoutSec 600"
              f" -EnvVars @{{ONN_FATOR={q(str(fator))};ONN_COR={q(str(cor))}}}")
        r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], capture_output=True, text=True, encoding='mbcs', errors='replace')
        log = open(dwg + '.exist.log', 'rb').read().replace(bytes(1), b'').decode('utf-8', 'replace') if os.path.exists(dwg + '.exist.log') else ''
        print(f, (r.stdout or '').strip(), '|', ' | '.join(l for l in log.splitlines() if 'ONNEXIST_' in l or 'ONNLEG' in l) or 'sem retorno')


if __name__ == '__main__':
    import alh_exec, sat_exec            # mesmos ajustes do rever.py de Alagoinhas e da Sátiro (caixa em linhas soltas, textos de bloco, nota)
    alh_exec.caixa_explodida()
    alh_exec.textos_de_bloco()
    sat_exec.nota_mais_longe()
    texto_da_caixa()
    trocar_textos()
    os.environ.update(PRECLASH_MUDANCAS=MUD, PRECLASH_EXEC_SAIDA=OUT)          # o import do alh_exec/sat_exec troca
    if '--so-carimbo' not in sys.argv:
        import onn_mudancas
        onn_mudancas.main()
        import rever
        os.makedirs(os.path.join(OUT, '_copias', '_anterior'), exist_ok=True)
        for x in glob.glob(os.path.join(OUT, '*_REVISADO.dwg')): shutil.move(x, os.path.join(OUT, '_copias', '_anterior', os.path.basename(x)))
        os.chdir(r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
        rever.main('olindina', so_comandos='--so-comandos' in sys.argv)
        if '--so-comandos' not in sys.argv: rede_existente()
    if '--so-comandos' not in sys.argv and '--sem-carimbo' not in sys.argv:
        carimbo()
