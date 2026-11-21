# -*- coding: utf-8 -*-
"""Jandaíra (padrão novo, 19/10/2026 noite) — lista única de mudanças para as pranchas, em UTM (rever.py com PRECLASH_UTM=1):
  - do preclash (JAN_preclash_AD_mudancas.json): profundidade de cada trecho pelo estudo de cota (nota "PROF. x,xx m") e caixas
    de elétrica deslocadas pela ferramenta;
  - do adaptador (FERRAMENTAS/jandaira/ifc/jan_ajustes.py, gravado em RELATORIOS/IFC_R02): contornos curtos das pressurizadas em
    volta das caixas fundas de DRE/ESG, caixas de elétrica que saíram de cima da drenagem, caixas e junções de DRE/ESG deslocadas.
Cada mudança ganha 'folha' (EL-001, EL-002, AF-001, IN-001, DRE-001, ESG-001, CPS-DRE-001, CPS-EL-001).
Grava RELATORIOS/EXECUTIVO_R02_IFC/JAN_mudancas_UTM.json."""
import os, json, math, collections
import numpy as np
BASE = r'D:\Projeto Modelagem\ETIB-JANDAIRA'
PRE = os.path.join(BASE, r'RELATORIOS\PRECLASH_R02'); AJ = os.path.join(BASE, r'RELATORIOS\IFC_R02')
OUT = os.environ.get('JAN_EXEC_OUT') or os.path.join(BASE, r'RELATORIOS\EXECUTIVO_R02_IFC'); os.makedirs(OUT, exist_ok=True)
# campo 50x30 (CPS): centro e ângulo em UTM do georreferenciamento do CPS
CC = np.array([631597.0557, 8721148.2573]); A = math.radians(25.7107)


def no_campo(p, folga=4.0):
    d = np.asarray(p[:2], float) - CC; x = d[0] * math.cos(A) + d[1] * math.sin(A); y = -d[0] * math.sin(A) + d[1] * math.cos(A)
    return abs(x) < 25 + folga and abs(y) < 15 + folga


def folhas(m):
    d = m['disc']; t = m.get('trecho') or ''; circ = (m.get('info') or {}).get('circuito', '')
    p = (m['E'], m['N']) if m.get('E') is not None else (m.get('novo') or m.get('planta'))[0]
    if d == 'ELE':
        if m['tipo'] == 'caixa deslocada':
            return ['EL-002'] if t.startswith('CX-I') else (['CPS-EL-001'] if t.startswith('CX-C') else ['EL-001'])
        if 'CPS' in circ or t.startswith('ELE-CPS'): return ['CPS-EL-001']
        if circ: return ['EL-002'] if 'EL-002' in circ else ['EL-001']
        return ['EL-002'] if t.startswith('ELE-I') else ['EL-001']          # contornos do adaptador (sem o circuito no registro)
    if d in ('HID', 'SDAI'): return ['IN-001']
    if d == 'AF': return ['AF-001']
    if d == 'ESG': return ['ESG-001']
    if d == 'DRE': return ['DRE-001', 'CPS-DRE-001'] if (t.startswith('DRE-CPS') or no_campo(p)) else ['DRE-001']
    return []


br = lambda v: ('%.2f' % v).replace('.', ',')
mud = []
for m in json.load(open(os.path.join(PRE, 'JAN_preclash_AD_mudancas.json'), encoding='utf-8'))['mudancas']:
    if m['tipo'] == 'mergulho':
        m['nota'] = 'PROF. %s m' % br(m['prof_topo'])
    mud.append(m)
# contornos curtos em volta das caixas fundas (o mesmo trecho pode contornar várias caixas: fica o traçado final, com o original)
ult = {}
for r in json.load(open(os.path.join(AJ, 'JAN_contornos.json'), encoding='utf-8')):
    k = r.get('elemento', r['trecho'])
    if k in ult: r = dict(r, caixa=ult[k]['caixa'] + ', ' + r['caixa'])
    ult[k] = r
for r in ult.values():
    nov = np.array(r['pontos']); mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r.get('elemento', r['trecho']), info={},
                                                antigo=r['antigo'], novo=r['pontos'], E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()),
                                                nota=f"contorno da caixa {r['caixa']}"))
# caixas de elétrica que saíram de cima da drenagem/esgoto
for r in json.load(open(os.path.join(AJ, 'JAN_caixas_ele.json'), encoding='utf-8')):
    if r['status'] != 'caixa deslocada': continue
    mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                    lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma='r', nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
# caixas e junções de DRE/ESG
F = json.load(open(os.path.join(AJ, 'JAN_ajustes_gravidade_final.json'), encoding='utf-8'))
for r in F['caixas']:
    mud.append(dict(tipo='caixa deslocada', disc=r['disc'], trecho=r['caixa'], elemento=r['elemento'], info={}, E=r['E'], N=r['N'], de=r['de'],
                    lado=r['lado'], lado_y=r['lado_y'], rot=r['rot'], forma=r['forma'], nota=f"caixa {r['caixa']} deslocada {br(r['desloc'])} m"))
for r in F['tubos']:
    nov = np.array(r['novo']); mud.append(dict(tipo='contorno', disc=r['disc'], trecho=r['trecho'], elemento=r['elemento'], info={}, antigo=r['antigo'], novo=r['novo'],
                                              E=float(nov[:, 0].mean()), N=float(nov[:, 1].mean()), nota='junção deslocada'))
# junções de DRE/ESG que subiram/desceram (jan_ajustes2.cota_grav, 20/10): nota "PROF. x,xx m" (topo do tubo) na junção, porque a
# prancha só cota as caixas
fn = os.path.join(AJ, 'JAN_cota_grav_registro.json')
if os.path.exists(fn):
    import sys as _s
    _s.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')
    from preclash.terreno import Terreno
    TT = Terreno(r'D:\Projeto Modelagem\FERRAMENTAS\preclash\escolas\dados\jandaira_terreno.npz')
    J = json.load(open(os.path.join(PRE, 'JAN.json'), encoding='utf-8')); O = (631578.10, 8721003.57); zr = J['zref']
    pontas = []
    for e in J['elementos']:
        if e['disc'] not in ('DRE', 'ESG') or 'AD' not in e['cen']: continue
        P = np.array((e['sol'] or {}).get('AD') or e['p'], float); P[:, 0] += O[0]; P[:, 1] += O[1]; P[:, 2] += zr
        for k in (0, -1): pontas.append((e['disc'], e['trecho'], P[k], e['de']))
    mov = [(np.array(t['antigo'][k]), np.array(t['novo'][k])) for t in F['tubos'] for k in (0, -1)]
    for r in json.load(open(fn, encoding='utf-8')):
        if r.get('status') != 'cota ajustada': continue
        for n in r['nos']:
            if not n.startswith('J:'): continue
            p = np.array([float(x) for x in n[2:].split(',')])
            p = next((b for a, b in mov if np.hypot(*(a - p)) < 0.15), p)          # junção que também andou em planta
            perto = [x for x in pontas if np.hypot(*(x[2][:2] - p)) < 0.20]
            if not perto: continue
            d, tr, q, de = min(perto, key=lambda x: x[2][2])
            zt = float(TT.z(np.array([q[:2]]))[0]); prof = zt - (q[2] + de / 2)
            u = np.array([0.5, 0.0])
            mud.append(dict(tipo='mergulho', origem='cota da gravidade', disc=d, trecho=tr, elemento=tr, info={}, E=float(q[0]), N=float(q[1]),
                            planta=[(q[:2] - u).tolist(), (q[:2] + u).tolist()], prof_topo=round(prof, 2), extensao=1.0, eixo_depois=float(q[2]),
                            nota='PROF. %s m' % br(prof)))
# a mesma caixa deslocada duas vezes (ferramenta + adaptador) fica uma só: de = a primeira origem, para = a última posição
vistas = {}
for m in mud:
    if m['tipo'] != 'caixa deslocada': continue
    k = m['trecho']
    if k in vistas: vistas[k]['E'], vistas[k]['N'] = m['E'], m['N']; m['_dup'] = True
    else: vistas[k] = m
mud = [m for m in mud if not m.get('_dup')]
saida = []
for m in mud:
    for f in folhas(m): saida.append(dict(m, folha=f))
json.dump({'mudancas': saida, 'coordenadas': 'UTM SIRGAS 2000 24S (m)'}, open(os.path.join(OUT, 'JAN_mudancas_UTM.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1, default=float)
c = collections.Counter((m['folha'], m['tipo']) for m in saida)
for k in sorted(c): print(k, c[k])
print('maior PROF. nas notas: %s m' % br(max(m['prof_topo'] for m in saida if m['tipo'] == 'mergulho')))
