# -*- coding: utf-8 -*-
"""Leitura dos CSVs padrão das fases 2 (redes extraídas) e 3 (cotas) feitos sem Revit nas threads das escolas.
Formato (separador ';', UTF-8 com BOM), o mesmo de escola C/escola G/escola H:
  *_fase3_pressurizadas_cotas.csv : sistema;trecho;perna;rede;DE_mm;L_m;E_ini;N_ini;E_fim;N_fim;terreno_ini;terreno_fim;eixo_ini;eixo_fim;...;recobrimento_exigido
  *_fase2_<REDE>_trechos.csv (gravidade): trecho;de;para;L_m;DN_mm;material;i_rotulo_pct;CF_montante;CF_jusante;...;classe;E_ini;N_ini;E_fim;N_fim;obs
  *_fase2_<REDE>_caixas.csv : caixa;tipo;E;N;lado_ou_raio_m;CT;CF;...
  *_fase2_DRE_galeria.csv    : trecho;descricao;DN_mm;L_m;GI_montante;GI_jusante;i_pct;E_ini;N_ini;E_fim;N_fim;obs
  *_fase2_ELE_nos.csv / *_fase2_PCI_nos.csv : no;...;tipo;E;N
Cada escola tem um adaptador em escolas/<escola>.py que chama estas funções com os nomes dos arquivos dela."""
import csv, collections
import numpy as np
from . import modelo as md


def ler_csv(fn):
    with open(fn, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f, delimiter=';'))


def fl(v):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ pressurizadas (fase 3: pernas já com cota de eixo)
def pressurizadas(fn, mapa_disc, mapa_rede=None, ignorar=()):
    """mapa_disc: sistema -> disciplina (ex.: {'AF':'AF','HID':'HID','SDAI':'SDAI','ELE':'ELE'})."""
    por = collections.OrderedDict()
    for r in ler_csv(fn):
        if r['sistema'] in ignorar: continue
        por.setdefault((r['sistema'], r['trecho']), []).append(r)
    out = []
    for (sis, tr), rs in por.items():
        rs.sort(key=lambda r: int(r['perna']))
        P = [(fl(rs[0]['E_ini']), fl(rs[0]['N_ini']), fl(rs[0]['eixo_ini']))]
        for r in rs:
            a = (fl(r['E_ini']), fl(r['N_ini']), fl(r['eixo_ini'])); b = (fl(r['E_fim']), fl(r['N_fim']), fl(r['eixo_fim']))
            if np.hypot(a[0] - P[-1][0], a[1] - P[-1][1]) > 0.01 or abs(a[2] - P[-1][2]) > 0.001: P.append(a)   # perna não contínua
            P.append(b)
        disc = mapa_disc[sis]
        rede = (mapa_rede or {}).get(sis, disc)
        out.append(md.elemento(f'{disc}:{tr}', disc, rede, tr, 'pressao', fl(rs[0]['DE_mm']) / 1000.0, P,
                               cob_min=fl(rs[0]['recobrimento_exigido']), sub=rs[0].get('rede', ''), cota='fase 3 (recobrimento mínimo sobre o terreno)'))
    return out


# ------------------------------------------------------------------ gravidade (fase 2: CF das caixas + declividade)
def gravidade(fn, disc, rede, ter, excluir_classe=('calha',), cob_estimada=0.60):
    """GI nas pontas: CF do projeto; sem CF numa ponta, a declividade do rótulo a partir da outra; sem nenhuma, a cota
    do nó propagada dos trechos vizinhos; sem nada, terreno − cob_estimada − DE (marcado como estimado)."""
    T = [r for r in ler_csv(fn) if not any(r.get('classe', '').startswith(c) for c in excluir_classe)]
    gi = {}
    for r in T:
        L = fl(r['L_m']) or 0.0; i = (fl(r.get('i_rotulo_pct')) or 1.0) / 100.0
        a, b = fl(r.get('CF_montante')), fl(r.get('CF_jusante')); org = 'projeto (CF)'
        if a is None and b is not None: a = b + i * L; org = 'CF + declividade do rótulo'
        if b is None and a is not None: b = a - i * L; org = 'CF + declividade do rótulo'
        gi[r['trecho']] = [a, b, org if a is not None else None]
    # propagação pelos nós (montante de quem sai = jusante de quem chega)
    for _ in range(50):
        mud = False
        zno = collections.defaultdict(list)
        for r in T:
            a, b, _o = gi[r['trecho']]
            if a is not None: zno[r['de']].append(a)
            if b is not None: zno[r['para']].append(b)
        for r in T:
            g = gi[r['trecho']]
            if g[0] is not None: continue
            L = fl(r['L_m']) or 0.0; i = (fl(r.get('i_rotulo_pct')) or 1.0) / 100.0
            if zno.get(r['para']):
                b = min(zno[r['para']]); g[:] = [b + i * L, b, 'propagada pelo nó de jusante']; mud = True
            elif zno.get(r['de']):
                a = min(zno[r['de']]); g[:] = [a, a - i * L, 'propagada pelo nó de montante']; mud = True
        if not mud: break
    out = []
    for r in T:
        a = np.array([fl(r['E_ini']), fl(r['N_ini'])]); b = np.array([fl(r['E_fim']), fl(r['N_fim'])])
        de = md.de_gravidade(fl(r['DN_mm']) or 100, r.get('material', ''))
        ga, gb, org = gi[r['trecho']]
        if ga is None:
            za, zb = ter.z(np.vstack([a, b]))
            ga, gb, org = za - cob_estimada - de, zb - cob_estimada - de, f'estimada (terreno − {cob_estimada:.2f} m)'
        P = [(a[0], a[1], ga + de / 2), (b[0], b[1], gb + de / 2)]
        out.append(md.elemento(f'{rede}:{r["trecho"]}', disc, rede, r['trecho'], 'gravidade', de, P, de_no=r['de'], para_no=r['para'],
                               DN_mm=r['DN_mm'], material=r.get('material', ''), classe=r.get('classe', ''), cota=org,
                               GI_mont=round(ga, 3), GI_jus=round(gb, 3), obs=r.get('obs', '')))
    return out


def caixas(fn, disc, rede, ter, trechos, parede=0.10, ignorar_tipos=(), circulares=('PVE', 'PVP', 'PV')):
    """Caixa = prisma do CT ao fundo (CF − 0,10 − 0,05 de laje). Sem CT: terreno. Sem CF: GI mais baixa que chega nela."""
    gi_no = collections.defaultdict(list)
    for e in trechos:
        gi_no[e['info']['de_no']].append(e['info']['GI_mont']); gi_no[e['info']['para_no']].append(e['info']['GI_jus'])
    out = []
    for r in ler_csv(fn):
        if r['tipo'] in ignorar_tipos: continue
        E, N = fl(r['E']), fl(r['N']); m = fl(r.get('lado_ou_raio_m')) or 0.6
        forma = 'c' if r['tipo'] in circulares else 'q'
        meia = (m if forma == 'c' else m / 2) + parede
        ct, cf = fl(r.get('CT')), fl(r.get('CF')); org = 'projeto'
        if ct is None: ct = float(ter.z([[E, N]])[0]); org = 'CT = terreno'
        if cf is None:
            cf = min(gi_no[r['caixa']]) if gi_no.get(r['caixa']) else ct - 0.6; org += ', CF = GI mais baixa ligada'
        out.append(md.caixa(f'{rede}:{r["caixa"]}', disc, rede, forma, E, N, meia, cf - 0.15, ct, nome=r['caixa'], tipo=r['tipo'],
                            CT=round(ct, 3), CF=round(cf, 3), cota=org))
    return out


def galeria(fn, disc, rede, parede=0.10, pendente=True):
    out = []
    for r in ler_csv(fn):
        dn = fl(r['DN_mm']) / 1000.0; de = dn + 2 * parede
        P = [(fl(r['E_ini']), fl(r['N_ini']), fl(r['GI_montante']) + dn / 2), (fl(r['E_fim']), fl(r['N_fim']), fl(r['GI_jusante']) + dn / 2)]
        out.append(md.elemento(f'{rede}:{r["trecho"]}', disc, rede, r['trecho'], 'gravidade', de, P, pendente=pendente, DN_mm=r['DN_mm'],
                               material='concreto (premissa: parede 0,10 m)', cota='projeto (GI das pontas)', descricao=r.get('descricao', ''),
                               GI_mont=fl(r['GI_montante']), GI_jus=fl(r['GI_jusante']), obs=r.get('obs', '')))
    return out


def caixas_de_nos(fn, disc, rede, ter, elementos, tipos, prof_sob_eixo=0.15, raio_busca=1.0):
    """Caixas de passagem das redes pressurizadas (ELE/SDAI): topo no terreno, fundo abaixo do eixo mais baixo que chega."""
    out = []
    pts = [(e, p) for e in elementos for p in e['pts']]
    for r in ler_csv(fn):
        t = r['tipo']
        lad = next((v for k, v in tipos.items() if t.startswith(k)), None)
        if lad is None: continue
        E, N = fl(r['E']), fl(r['N']); zt = float(ter.z([[E, N]])[0])
        zs = [p[2] - e['de'] / 2 for e, p in pts if np.hypot(p[0] - E, p[1] - N) < raio_busca]
        zb = (min(zs) if zs else zt - 0.6) - prof_sob_eixo
        out.append(md.caixa(f'{rede}:{r["no"]}', disc, rede, 'q', E, N, lad / 2 + 0.05, zb, zt, nome=r['no'], tipo=t,
                            cota='topo no terreno; fundo 0,15 m abaixo do eletroduto mais baixo' if zs else 'sem eletroduto chegando: 0,60 m'))
    return out


# ------------------------------------------------------------------ para escolas sem a fase 3 das pressurizadas
def perfil_por_recobrimento(pts2d, de, cob, ter, passo=0.5, desvio=0.20, trecho_min=2.0):
    """Eixo 3D de uma rede pressurizada/eletroduto a partir do traçado 2D: algoritmo da skill (amostra a cada 0,5 m,
    Douglas-Peucker 0,20 m / 2 m sobre o perfil exigido, abaixa os nós até nenhum ponto ficar com recobrimento < cob).
    Devolve (n,3). Mesmo critério da fase 3 da escola C (fase3_sat.py), sem a regra de nó compartilhado."""
    P = [np.asarray(p[:2], float) for p in pts2d]
    S, Q = [0.0], [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = np.linalg.norm(b - a); k = max(1, int(L / passo))
        for j in range(1, k + 1): Q.append(a + (b - a) * j / k); S.append(S[-1] + L / k)
    S = np.array(S); Q = np.array(Q)
    zt = ter.z(Q)
    if np.isnan(zt).all(): raise ValueError('trecho fora do terreno')
    zt = np.where(np.isnan(zt), np.nanmin(zt), zt)
    zr = zt - cob - de / 2
    cum = np.cumsum([0] + [np.linalg.norm(b - a) for a, b in zip(P[:-1], P[1:])])
    qb = {0, len(S) - 1} | {int(np.argmin(np.abs(S - s))) for s in cum}

    def dp(i0, i1):
        if i1 <= i0 + 1: return
        line = zr[i0] + (zr[i1] - zr[i0]) * (S[i0 + 1:i1] - S[i0]) / (S[i1] - S[i0] + 1e-12)
        dev = line - zr[i0 + 1:i1]; k = int(np.argmax(dev)) + i0 + 1
        if dev.max() > desvio and S[k] - S[i0] >= trecho_min and S[i1] - S[k] >= trecho_min:
            qb.add(k); dp(i0, k); dp(k, i1)
    for i0, i1 in zip(sorted(qb)[:-1], sorted(qb)[1:]): dp(i0, i1)
    qs = sorted(qb); z = {i: zr[i] for i in qs}
    for _ in range(50):
        ok = True
        for i0, i1 in zip(qs[:-1], qs[1:]):
            if i1 - i0 < 2: continue
            line = z[i0] + (z[i1] - z[i0]) * (S[i0:i1 + 1] - S[i0]) / (S[i1] - S[i0] + 1e-12)
            exc = (line - zr[i0:i1 + 1]).max()
            if exc > 0.001: z[i0] -= exc; z[i1] -= exc; ok = False
        if ok: break
    return np.array([(Q[i][0], Q[i][1], z[i]) for i in qs])


def elemento_3d(id, disc, rede, trecho, tipo, de, pts3d, **info):
    """atalho para formatos que já trazem o eixo 3D (ex.: CSVs 'revit/' da escola F: x0_utm;y0_utm;z0_eixo;x1_utm;...)."""
    return md.elemento(id, disc, rede, trecho, tipo, de, pts3d, **info)
