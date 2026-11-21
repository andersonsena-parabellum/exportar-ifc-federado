# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — estrutura as built (fundações, pilares e baldrames) como obstáculo do clash (disciplina EST).
Fonte: RVTs de fundação de REFERENCIAS_RVT (copiados para o scratch e lidos no Revit com imp/ler_fundacoes.cs.txt ->
<arquivo>_est.csv em coordenadas internas de cada RVT) + posição/rotação de cada vínculo no IMP as built (imp/imp_vinculos.csv).
UTM = origem do vínculo + x·bx + y·by; cota = origem z + z interno.
Saída: RELATORIOS/FASE2_REDES_2026-10-18/SAT_fase2_estrutura.csv e caixas_estrutura(md) para o adaptador do preclash."""
import os, sys, csv, glob, math, json
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sat_comum as sc   # noqa: E402

FUN_DIR = os.path.join(sc.DXF_DIR.replace(os.sep + 'work' + os.sep + 'geo', ''), 'imp', 'fun')
VINC = os.path.join(AQUI, 'imp', 'imp_vinculos.csv')
SAIDA = os.path.join(sc.REL, 'SAT_fase2_estrutura.csv')
# guarda uma cópia dos CSVs lidos no Revit junto do script (o scratch pode sumir)
GUARDA = os.path.join(AQUI, 'imp', 'fun')


def vinculos():
    V = {}
    for r in csv.DictReader(open(VINC, encoding='utf-8'), delimiter=';'):
        O = np.array(list(map(float, r['origem'].split(','))))
        bx = np.array(list(map(float, r['bx'].split(','))))
        V[r['tipo'].lower()] = (O, bx)
    return V


def converter():
    import shutil
    os.makedirs(GUARDA, exist_ok=True)
    for fn in glob.glob(os.path.join(FUN_DIR, '*_est.csv')): shutil.copy2(fn, GUARDA)
    V = vinculos(); out = []
    for fn in sorted(glob.glob(os.path.join(GUARDA, '*_est.csv'))):
        rvt = os.path.basename(fn).replace('_est.csv', '.rvt').lower()
        if rvt not in V: print('sem vínculo no IMP:', rvt); continue
        O, bx = V[rvt]; by = np.array([-bx[1], bx[0]]); ang = math.atan2(bx[1], bx[0])
        bloco = rvt.split('-etib-')[1].split('-')[0].upper()
        aj = np.zeros(2)
        if bloco == 'BP4' and os.path.exists(os.path.join(AQUI, 'imp', 'bp4_ajuste.json')):   # vínculo do BP4 no IMP fora da obra
            J = json.load(open(os.path.join(AQUI, 'imp', 'bp4_ajuste.json'), encoding='utf-8')); aj = np.array([J['dE'], J['dN']])
        U = lambda x, y, O=O, bx=bx, by=by, aj=aj: O[:2] + x * bx + y * by + aj
        for r in csv.DictReader(open(fn, encoding='utf-8'), delimiter=';'):
            mn = np.array([float(r['minx']), float(r['miny']), float(r['minz'])]); mx = np.array([float(r['maxx']), float(r['maxy']), float(r['maxz'])])
            cat = r['categoria']; ehviga = 'Quadro' in cat or 'Framing' in cat or 'Vigas' in cat or 'quadro' in cat.lower()
            c = (mn + mx) / 2; lx, ly = mx[0] - mn[0], mx[1] - mn[1]; rot = ang
            if ehviga and r['p0'] and r['p1']:
                a = np.array(list(map(float, r['p0'].split(','))))[:2]; b = np.array(list(map(float, r['p1'].split(','))))[:2]
                d = b - a; L = float(np.hypot(*d)); al = math.atan2(d[1], d[0])
                if abs(((math.degrees(al) + 45) % 90) - 45) > 2:            # viga inclinada em planta: eixo + largura de premissa
                    c[:2] = (a + b) / 2; lx, ly = L, 0.20; rot = ang + al
            if lx < 0.05 or ly < 0.05 or mx[2] - mn[2] < 0.05: continue
            E, N = U(c[0], c[1])
            out.append({'id': f"EST:{bloco}-{r['id']}", 'bloco': bloco, 'categoria': cat, 'familia': r['familia'], 'tipo': r['tipo'],
                        'E': round(float(E), 3), 'N': round(float(N), 3), 'lx': round(float(lx), 3), 'ly': round(float(ly), 3), 'rot_graus': round(math.degrees(rot), 4),
                        'zb': round(float(O[2] + mn[2]), 3), 'zt': round(float(O[2] + mx[2]), 3), 'arquivo': os.path.basename(fn).replace('_est.csv', '.rvt')})
    if out:
        with open(SAIDA, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()), delimiter=';'); w.writeheader(); w.writerows(out)
    return out


def caixas_estrutura(md, ter=None, so_enterrado=True):
    """prismas da estrutura para o clash; só a parte até 0,50 m acima do terreno (o resto não cruza rede enterrada)."""
    if not os.path.exists(SAIDA): return []
    out = []
    for r in csv.DictReader(open(SAIDA, encoding='utf-8-sig'), delimiter=';'):
        zb, zt = float(r['zb']), float(r['zt'])
        if so_enterrado and ter is not None:
            z = float(ter.z([[float(r['E']), float(r['N'])]])[0])
            if not np.isnan(z): zt = min(zt, z + 0.50)
            if zt <= zb + 0.02: continue
        out.append(md.caixa_retangular(r['id'], 'EST', 'EST', float(r['E']), float(r['N']), float(r['lx']), float(r['ly']), math.radians(float(r['rot_graus'])),
                                       zb, zt, nome=r['id'].split(':', 1)[1], tipo=f"{r['categoria']} ({r['bloco']})", cota='as built (RVT de fundação + vínculo do IMP)'))
    return out


if __name__ == '__main__':
    out = converter()
    import collections
    print(len(out), 'peças', collections.Counter((o['bloco'], o['categoria']) for o in out))
