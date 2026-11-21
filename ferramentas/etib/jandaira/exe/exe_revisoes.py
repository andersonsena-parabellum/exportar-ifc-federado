# -*- coding: utf-8 -*-
"""Pranchas executivas revisadas (R01) da Jandaíra: monta, para cada DWG de projeto com mudança, um arquivo de comandos em coordenadas
do próprio DWG (lido por revisao_r01.lsp no accoreconsole), com:
  layer R01-NOVO        traçado novo (desvios, caixas e linhas em posição nova, ligações do campo)
  layer R01-SUBSTITUIDO traçado que sai (tracejado por cima do original)
  layer R01-NUVEM       nuvens de revisão numeradas
  layer R01-NOTA        notas curtas junto da mudança e o quadro "REVISÃO R01" com a lista numerada
Fontes: compat_R01/geo (hoje) e geo_exec (modelos revisados), ele_instrucoes.tsv, cps_dre_instrucoes.tsv, rel/dados.json do relatório.
Transformações: EXECUTIVO_R01/transformacoes_dwg_interno.json (exe_transf.py) e o JSON do CPS DRE."""
import sys, os, re, json, math, collections, numpy as np
sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\compat_geral"); sys.path.insert(0, r"D:\Projeto Modelagem\FERRAMENTAS\georef_dxf")
import jan_dados as JD, dxfgeo
sys.stdout.reconfigure(encoding='utf-8')
C = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\compat_R01"; OUT = r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\EXECUTIVO_R01"
DX = r"C:\Users\ander\AppData\Local\Temp\claude\D--Projeto-Modelagem\4fcc3e25-69da-482c-a9ae-2fbcd452044d\scratchpad\jan\cps\dxf\24-049-JDI-CTO-ETIB-"
TF = json.load(open(os.path.join(OUT, 'transformacoes_dwg_interno.json'), encoding='utf-8'))
TC = json.load(open(r"D:\Projeto Modelagem\ETIB-JANDAIRA\CAD_GEORREFERENCIADO\transformacao_CPS_DRE-001-DRG-R01_local_para_UTM.json", encoding='utf-8'))
rot = lambda a: np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
def num(v, d=2): return ('%.' + str(d) + 'f') % v
def br(v, d=2): return num(v, d).replace('.', ',')
DIR = ['a leste', 'a nordeste', 'ao norte', 'a noroeste', 'a oeste', 'a sudoeste', 'ao sul', 'a sudeste']


class Rev:
    def __init__(self, chave, arquivo, Rinv, tinv, h):
        self.k, self.arq, self.R, self.t, self.h = chave, arquivo, Rinv, np.asarray(tinv), h
        self.L = []; self.notas = []
    def P(self, p): return self.R @ np.asarray(p[:2], float) + self.t
    def nota(self, txt, p, r=None, linha=True):
        n = len(self.notas) + 1; self.notas.append(txt); q = self.P(p); r = r or 6 * self.h
        self.L.append('CLOUD\tR01-NUVEM\t%.4f\t%.4f\t%.4f' % (q[0], q[1], r))
        self.L.append('TX\tR01-NOTA\t%.4f\t%.4f\t%.4f\t0\tR01-%d' % (q[0] + r * 0.75, q[1] + r * 0.75, self.h * 1.6, n))
        return n
    def pl(self, pts, lay='R01-NOVO'):
        Q = [self.P(p) for p in pts]
        self.L.append('PL\t%s\t0\t%s' % (lay, '\t'.join('%.4f\t%.4f' % (q[0], q[1]) for q in Q)))
    def quadrado(self, c, lado, ang=0.0, lay='R01-NOVO'):
        u = np.array([math.cos(ang), math.sin(ang)]); v = np.array([-u[1], u[0]]); c = np.asarray(c[:2]); h = lado / 2
        Q = [self.P(c + su * u * h + sv * v * h) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        self.L.append('PL\t%s\t1\t%s' % (lay, '\t'.join('%.4f\t%.4f' % (q[0], q[1]) for q in Q)))
    def gravar(self, ext):
        x0, y0, x1, y1 = ext; texto = ['REVISÃO R01 — COMPATIBILIZAÇÃO (Populus, 19/10/2026)',
                                     'Só profundidade: nota na planta. Traçado novo: layer R01-NOVO; traçado que sai: R01-SUBSTITUIDO (tracejado).'] + ['R01-%d  %s' % (i + 1, t) for i, t in enumerate(self.notas)]
        cab = ['LAYER\tR01-NOVO\t1\tContinuous', 'LAYER\tR01-SUBSTITUIDO\t8\tDASHED', 'LAYER\tR01-NUVEM\t1\tContinuous', 'LAYER\tR01-NOTA\t1\tContinuous']
        larg = max(60.0, (x1 - x0) * 0.35)
        cab.append('MT\tR01-NOTA\t%.4f\t%.4f\t%.4f\t%.4f\t%s' % (x0, y1 + 3 * self.h * (len(texto) + 4), self.h * 1.6, larg, '\\P'.join(texto)))
        fn = os.path.join(OUT, '_cmd_%s.txt' % self.k); open(fn, 'w', encoding='utf-8').write('\n'.join(cab + self.L) + '\n')
        print('%-8s %3d notas, %4d entidades -> %s' % (self.k, len(self.notas), len(self.L), os.path.basename(fn))); return fn


def extents(arq):
    g = dxfgeo.load(DX + arq + '.dxf'); P = np.array([q[:2] for s in g['segs'] for q in s['p']])
    lo, hi = np.percentile(P, 1, 0), np.percentile(P, 99, 0); return (lo[0], lo[1], hi[0], hi[1])


def rev_de(k, h):
    d = TF[k]; return Rev(k, d['arquivo'], rot(math.radians(d['rot_inv_graus'])), d['t_inv'], h)


SH, MH = JD.carregar(g=os.path.join(C, 'geo'), est=None); JD.agrupar_caixas(SH, MH)
SX, MX = JD.carregar(g=os.path.join(C, 'geo_exec'), est=None); JD.agrupar_caixas(SX, MX)
S0 = {s['id']: s for s in SH}
REL = json.load(open(r"D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\fonte_relatorio_R01\rel\dados.json", encoding='utf-8'))
cmds = {}

# ================================ ELÉTRICA (EL-001 força / EL-002 iluminação externa)
ele = {k: rev_de(k, 0.30) for k in ('EL-001', 'EL-002')}
lin = [l.rstrip('\n').split('\t') for l in open(os.path.join(C, 'ele_instrucoes.tsv'), encoding='utf-8') if l.strip()]
por = collections.defaultdict(list)
for r in lin:
    if r[0] == 'SEG': por[r[1]].append(r)
qual = lambda pid: 'EL-002' if 'Fonte: EL-002' in (S0[pid].get('desc') or '') else 'EL-001'
for pid, rr in por.items():
    o = S0[pid]; R = ele[qual(pid)]; mk = o['trecho'] if not o['trecho'].startswith(('.', 'Pluvial')) else 'eletroduto'
    pts = [(float(r[2]), float(r[3]), float(r[4])) for r in rr] + [(float(rr[-1][5]), float(rr[-1][6]), float(rr[-1][7]))]
    zs = [float(r[4]) for r in rr] + [float(r[7]) for r in rr]; z0 = min(o['a0'][2], o['b0'][2])
    if any('desvio' in r[9] for r in rr):
        segs = [((float(r[2]), float(r[3])), (float(r[5]), float(r[6]))) for r in rr]
        for a, b in segs: R.pl([a, b])
        R.pl([o['a0'], o['b0']], 'R01-SUBSTITUIDO')
        mot = re.search(r'desvio em planta \(([^)]*)\)', ' '.join(r[9] for r in rr))
        R.nota('%s: desvio curto em planta (contorna %s), mesma cota' % (mk, mot.group(1) if mot else 'obstáculo'), np.mean([p[:2] for p in pts], 0))
    elif any('acompanha caixa' in r[9] for r in rr):
        for r in rr: R.pl([(float(r[2]), float(r[3])), (float(r[5]), float(r[6]))])
        R.pl([o['a0'], o['b0']], 'R01-SUBSTITUIDO')
    elif min(zs) < z0 - 0.05:
        k = int(np.argmin([min(float(r[4]), float(r[7])) for r in rr])); r = rr[k]
        c = ((float(r[2]) + float(r[5])) / 2, (float(r[3]) + float(r[6])) / 2)
        atual = [s for s in SX if s['disc'] == 'ELE' and (s['trecho'] == mk or s['trecho'].startswith(mk + '.m')) and np.linalg.norm(np.array(c) - (s['a'][:2] + s['b'][:2]) / 2) < 8]
        if atual: zs = [min(s['a'][2], s['b'][2]) for s in atual]           # cota que está no modelo (o ELE-I-14 foi refeito depois)
        R.nota('%s: mergulho no cruzamento, eixo na cota %s (desce %s m); planta não muda' % (mk, br(147 + min(zs)), br(z0 - min(zs))), c, r=4 * R.h)
PLE = json.load(open(os.path.join(C, 'ele_plano_atual.json'), encoding='utf-8'))['caixas']
cx_h = {}
for M in MH:
    if M['disc'] == 'ELE' and str(M.get('grupo', '')).startswith('CX-') and M.get('glo') is not None: cx_h[M['grupo']] = M
for r in lin:
    if r[0] != 'CX': continue
    g = r[1]; M = cx_h.get(g)
    if M is None: continue
    c0 = (M['glo'] + M['ghi']) / 2; dx, dy, pr = float(r[2]), float(r[3]), float(r[4]); d = math.hypot(dx, dy)
    R = ele['EL-002' if g.startswith('CX-I') else 'EL-001']; h0 = float(PLE[g]['prof_hoje'])
    if d > 0.01:
        c1 = c0[:2] + np.array([dx, dy]); R.quadrado(c1, 1.0); R.pl([c0[:2], c1])
        a = DIR[int(((math.degrees(math.atan2(dy, dx)) % 360 + 22.5) % 360) // 45)]
        R.nota('%s em posição nova (%s m %s)%s' % (g, br(d, 1), a, '' if abs(pr - h0) < 0.01 else ', profundidade %s m' % br(pr)), c1)
    elif abs(pr - h0) > 0.01:
        R.nota('%s com profundidade %s m (hoje %s m)' % (g, br(pr), br(h0)), c0, r=3 * R.h)
q = [m for m in MX if m.get('grupo') == 'QDLT-CAMPO']
if q: ele['EL-001'].nota('Iluminação do campo society conforme CPS EL-001 R01 (campo 50×30), saindo do QDLT-CAMPO', (q[0]['glo'] + q[0]['ghi']) / 2)
for k, R in ele.items(): cmds[k] = (R, R.gravar(extents(TF[k]['arquivo'][len('24-049-JDI-CTO-ETIB-'):])))

# ================================ ÁGUA FRIA (AF-001)
R = rev_de('AF-001', 0.30)
desl = {'AL-20': '2,0 m a oeste', 'AL-04': '2,0 m a oeste', 'AL-19.t': '2,0 m a oeste', 'AL-21': '1,8 m ao norte', 'AL-22': '1,8 m ao norte', 'AR-16': '1,0 m ao sul'}
porm = collections.defaultdict(list)
for s in SX:
    if s['disc'] == 'AF': porm[re.sub(r'\.g\d+$', '', s['trecho'])].append(s)
h0m = collections.defaultdict(list)
for s in SH:
    if s['disc'] == 'AF': h0m[s['trecho']].append(s)
feitos = set()
for mk, quanto in desl.items():
    for s in porm.get(mk, []): R.pl([s['a'], s['b']])
    for s in h0m.get(mk, []): R.pl([s['a0'], s['b0']], 'R01-SUBSTITUIDO')
for grupo, mks, txt in ((1, ('AL-20', 'AL-04', 'AL-19.t'), 'Linha leste da alimentação (AL-20, AL-04, AL-19.t) deslocada 2,0 m a oeste, mesma cota: sai de cima das caixas da drenagem e dos poços do esgoto'),
                        (2, ('AL-21', 'AL-22'), 'Linha sul da alimentação (AL-21, AL-22) deslocada 1,8 m ao norte, mesma cota (AL-21 desce 8 cm num ponto, sob eletroduto)'),
                        (3, ('AR-16',), 'Reúso AR-16 deslocado 1,0 m ao sul, com mergulhos sob os coletores da drenagem')):
    pts = np.array([p[:2] for m in mks for s in porm.get(m, []) for p in (s['a'], s['b'])])
    R.nota(txt, pts.mean(0), r=8 * R.h)
for mk in ('AR-01', 'AR-08', 'AR-11', 'AR-14'):
    gs = [s for s in porm.get(mk, []) if re.search(r'\.g\d+$', s['trecho'])]
    if not gs: continue
    z = min(min(s['a'][2], s['b'][2]) for s in gs); low = min(gs, key=lambda s: min(s['a'][2], s['b'][2]))
    R.nota('%s (reúso): mergulho local, eixo até a cota %s, rampas a 45°; planta não muda' % (mk, br(147 + z)), (low['a'] + low['b']) / 2, r=4 * R.h)
cmds['AF-001'] = (R, R.gravar(extents(TF['AF-001']['arquivo'][len('24-049-JDI-CTO-ETIB-'):])))

# ================================ INCÊNDIO (IN-001: hidrantes e alarme)
R = rev_de('IN-001', 0.30)
mid = {}
for s in SX:
    if s['disc'] in ('INC', 'SDAI'): mid.setdefault(re.sub(r'\.d\d+$', '', s['trecho']).replace('PCI-', ''), []).append(s)
for l in REL['prof']:
    if l['p0'] is None or l['p1'] is None or abs(l['p1'] - l['p0']) < 0.02:
        if l['p0'] is None and l['trecho'].split(' ')[0] in mid:
            ss = mid[l['trecho'].split(' ')[0]]
            for s in ss: R.pl([s['a'], s['b']])
        continue
    ss = mid.get(l['trecho'])
    if not ss: continue
    s = max(ss, key=lambda s: np.linalg.norm(s['b'][:2] - s['a'][:2]))
    R.nota('%s: eixo a %s m da cota 147,00 (cota %s; hoje %s m); planta não muda' % (l['trecho'], br(l['p1']), br(147 - l['p1']), br(l['p0'])), (s['a'] + s['b']) / 2, r=4 * R.h)
for c in REL['cx_sdai']:
    E = [m for m in MX if m.get('grupo') == c['cx']]
    if not E: continue
    cc = (E[0]['glo'] + E[0]['ghi']) / 2
    if c['d'] > 0.05:
        R.quadrado(cc, 0.5); Eh = [m for m in MH if m.get('grupo') == c['cx']]
        if Eh: R.quadrado((Eh[0]['glo'] + Eh[0]['ghi']) / 2, 0.5, lay='R01-SUBSTITUIDO')
        R.nota('%s em posição nova (%s m a noroeste, sai de cima do DRE-046), profundidade %s m; eletrodutos EL-01b e EL-03a novos' % (c['cx'], br(c['d'], 1), br(c['h1'])), cc)
    elif abs(c['h1'] - c['h0']) > 0.02:
        R.nota('%s com profundidade %s m (hoje %s m)' % (c['cx'], br(c['h1']), br(c['h0'])), cc, r=3 * R.h)
cmds['IN-001'] = (R, R.gravar(extents(TF['IN-001']['arquivo'][len('24-049-JDI-CTO-ETIB-'):])))

# ================================ DRENAGEM (DRE-001 da implantação) e CPS DRE-001 (campo)
R = rev_de('DRE-001', 0.40)
ins = [l.rstrip('\n').split('\t') for l in open(os.path.join(C, 'cps_dre_instrucoes.tsv'), encoding='utf-8') if l.strip()]
for r in ins:
    if r[0] == 'DEL':
        s = S0.get(r[1])
        if s: R.pl([s['a0'], s['b0']], 'R01-SUBSTITUIDO')
    elif r[0] in ('MOD', 'NEW'):
        v = [float(x) for x in r[3:9]]; R.pl([v[0:2], v[3:5]])
c43 = [m for m in MX if m.get('grupo') == 'CX-43'][0]; cc = (c43['glo'] + c43['ghi']) / 2
R.nota('Drenagem do campo conforme CPS DRE-001 R01 (campo 50×30), com a espinha descarregando a OESTE nesta caixa; sai a espinha de peixe do campo 45×25', (90.95, 114.11), r=18)
R.nota('CX-43 mais funda: profundidade 0,96 m (fundo interno na cota %s)' % br(147 + float([r for r in ins if r[0] == 'CX'][0][2])), cc, r=3 * R.h)
d60 = [r for r in ins if r[0] == 'MOD' and r[2] == 'DRE-060'][0]
R.nota('DRE-060 refeito a 1 %%: eixo de %s (CX-43) a %s (poço de infiltração PI-01)' % (br(147 + float(d60[5])), br(147 + float(d60[8]))), ((float(d60[3]) + float(d60[6])) / 2, (float(d60[4]) + float(d60[7])) / 2), r=4 * R.h)
for r in ins:
    if r[0] == 'MOD' and r[2] != 'DRE-060':
        R.nota('%s encurtado até a canaleta do campo 50×30; começa na cota %s' % (r[2], br(147 + float(r[5]))), (float(r[3]), float(r[4])), r=3 * R.h)
cmds['DRE-001'] = (R, R.gravar(extents('IMP-PE-DRE-001-DRG-R00')))
# CPS DRE-001: interno -> local do CPS = inverso de (local -> interno)
a = math.radians(TC['rot_int_graus']); Rl = rot(-a); tl = -Rl @ np.array(TC['t_int'])
R = Rev('CPS-DRE', '24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R01', Rl, tl, 0.20)
for r in ins:
    if r[0] in ('MOD', 'NEW'):
        v = [float(x) for x in r[3:9]]; R.pl([v[0:2], v[3:5]])
esp = [r for r in ins if r[0] == 'NEW' and r[2].startswith('DRE-CPS-E')]
R.nota('Espinha com caimento para OESTE (i = 1 %%), do eixo %s a %s, descarregando na CX-43 existente (a leste não há rede)' % (br(147 + max(float(r[5]) for r in esp)), br(147 + min(float(r[8]) for r in esp))), (90.95, 114.11), r=6)
loc = lambda P: Rl @ np.asarray(P, float) + tl
for lado, cxs in (('norte', 'CX-40, CX-41 e CX-42'), ('sul', 'CX-14, CX-16 e CX-19')):
    y = 1 if lado == 'norte' else -1
    p = (90.95 - 5.38 * 0 , 114.11 + y * 20.5)
    R.nota('Saídas das canaletas do lado %s ligadas às caixas existentes %s; não executar as caixas de areia e as saídas "interligar" deste lado' % (lado, cxs), p, r=5)
R.nota('Não executar a caixa de areia e a saída a leste da espinha', (123.36 - 2, 109.66 + 0.2), r=3)
cmds['CPS-DRE'] = (R, R.gravar(extents('CPS-PE-DRE-001-DRG-R01')))
json.dump({k: dict(arquivo=R.arq, cmd=fn, notas=R.notas) for k, (R, fn) in cmds.items()}, open(os.path.join(OUT, 'revisoes_R01.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
