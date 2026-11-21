# -*- coding: utf-8 -*-
"""Pojuca — etapa 2 do pjc_ifc_redes.py: com as linhas guardadas (PJC_ifc_asbuilt_redes_linhas.json), monta os pontos de cada elemento
de tubulação em coordenadas do arquivo (posicionamento local encadeado, itens mapeados, extrusões e B-rep), tira o eixo pela direção
principal e grava PJC_ifc_asbuilt_redes.csv (sem UTM ainda: o arquivo usa as coordenadas compartilhadas do IMP)."""
import os, re, csv, json, math
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
L = {int(k): v for k, v in json.load(open(os.path.join(D, 'PJC_ifc_asbuilt_redes_linhas.json'))).items()}
REF = re.compile(r'#(\d+)')
NUM = re.compile(r'-?\d+\.?\d*(?:E[-+]?\d+)?')


def args(a):
    """divide os argumentos de topo (respeitando parênteses e aspas)."""
    out, d, q, cur = [], 0, False, ''
    for ch in a:
        if ch == "'" : q = not q
        if not q and ch == '(': d += 1
        if not q and ch == ')': d -= 1
        if not q and d == 0 and ch == ',': out.append(cur); cur = ''; continue
        cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def ref(s):
    m = REF.match(s.strip()); return int(m.group(1)) if m else None


def refs(s): return [int(x) for x in REF.findall(s)]


def nums(s): return [float(x) for x in NUM.findall(s)]


def ponto(i):
    t, a = L[i]; return np.array((nums(a) + [0.0, 0.0, 0.0])[:3])


def direcao(i):
    t, a = L[i]; v = np.array((nums(a) + [0.0, 0.0, 0.0])[:3]); return v / (np.linalg.norm(v) or 1)


def ax3(i):
    """IfcAxis2Placement3D/2D -> matriz 4x4."""
    t, a = L[i]; p = args(a)
    o = ponto(ref(p[0])); z = direcao(ref(p[1])) if len(p) > 1 and ref(p[1]) else np.array([0, 0, 1.0])
    x = direcao(ref(p[2])) if len(p) > 2 and ref(p[2]) else np.array([1.0, 0, 0])
    if t == 'IFCAXIS2PLACEMENT2D':
        z = np.array([0, 0, 1.0]); x = direcao(ref(p[1])) if len(p) > 1 and ref(p[1]) else np.array([1.0, 0, 0])
    x = x - z * (x @ z); x /= np.linalg.norm(x) or 1; y = np.cross(z, x)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, o
    return M


_LP = {}


def local(i):
    if i is None: return np.eye(4)
    if i in _LP: return _LP[i]
    t, a = L[i]; p = args(a)
    M = local(ref(p[0])) @ ax3(ref(p[1])); _LP[i] = M
    return M


def operador(i):
    t, a = L[i]; p = args(a)
    x = direcao(ref(p[0])) if ref(p[0]) else np.array([1.0, 0, 0]); y = direcao(ref(p[1])) if ref(p[1]) else np.array([0, 1.0, 0])
    o = ponto(ref(p[2])); s = float(p[3]) if p[3] not in ('$', '') else 1.0
    z = direcao(ref(p[4])) if len(p) > 4 and ref(p[4]) else np.cross(x, y)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x * s, y * s, z * s, o
    return M


def perfil(i):
    t, a = L[i]; p = args(a)
    if t == 'IFCCIRCLEPROFILEDEF':
        r = float(p[3]); M = ax3(ref(p[2])) if ref(p[2]) else np.eye(4)
        P = np.array([[r * math.cos(k * math.pi / 4), r * math.sin(k * math.pi / 4), 0, 1] for k in range(8)])
        return (M @ P.T).T[:, :3], r
    if t == 'IFCCIRCLEHOLLOWPROFILEDEF':
        r = float(p[3]); M = ax3(ref(p[2])) if ref(p[2]) else np.eye(4)
        P = np.array([[r * math.cos(k * math.pi / 4), r * math.sin(k * math.pi / 4), 0, 1] for k in range(8)])
        return (M @ P.T).T[:, :3], r
    if t == 'IFCRECTANGLEPROFILEDEF':
        hx, hy = float(p[3]) / 2, float(p[4]) / 2; M = ax3(ref(p[2])) if ref(p[2]) else np.eye(4)
        P = np.array([[sx * hx, sy * hy, 0, 1] for sx in (-1, 1) for sy in (-1, 1)])
        return (M @ P.T).T[:, :3], None
    return pontos_brutos(i), None


def pontos_brutos(i, prof=0):
    out = []
    if prof > 12: return out
    t, a = L.get(i, ('', ''))
    if t == 'IFCCARTESIANPOINT': return [ponto(i)]
    if t in ('IFCDIRECTION', 'IFCOWNERHISTORY', 'IFCSTYLEDITEM', 'IFCGEOMETRICREPRESENTATIONCONTEXT', 'IFCGEOMETRICREPRESENTATIONSUBCONTEXT'): return out
    for r in refs(a):
        out += pontos_brutos(r, prof + 1)
    return out


RAIOS = []


def item(i, M):
    t, a = L[i]; p = args(a)
    if t == 'IFCMAPPEDITEM':
        rm = L[ref(p[0])][1]; q = args(rm)
        O = ax3(ref(q[0])); Tg = operador(ref(p[1]))
        return rep(ref(q[1]), M @ Tg @ O)
    if t == 'IFCEXTRUDEDAREASOLID':
        P, r = perfil(ref(p[0])); Mp = ax3(ref(p[1])) if ref(p[1]) else np.eye(4)
        d = direcao(ref(p[2])); h = float(p[3])
        if r: RAIOS.append(r)
        Q = np.vstack([P, P + d * h]); Q = np.column_stack([Q, np.ones(len(Q))])
        return list(((M @ Mp @ Q.T).T)[:, :3])
    if t in ('IFCBOOLEANCLIPPINGRESULT', 'IFCBOOLEANRESULT'):
        return item(ref(p[1]), M)
    P = pontos_brutos(i)
    if not P: return []
    Q = np.column_stack([np.array(P), np.ones(len(P))]); return list(((M @ Q.T).T)[:, :3])


def rep(i, M):
    t, a = L[i]; p = args(a); out = []
    for it in refs(p[3]): out += item(it, M)
    return out


def elemento(i):
    t, a = L[i]; p = args(a)
    M = local(ref(p[5])); pr = ref(p[6]); out = []
    if pr is None: return np.zeros((0, 3))
    for r in refs(args(L[pr][1])[2]):
        rt, ra = L[r]; q = args(ra)
        if q[1].strip("'") in ('Body', 'Facetation', 'Mesh'): out += rep(r, M)
    return np.array(out)


def sistemas():
    """elemento -> nome do grupo/sistema (IfcRelAssignsToGroup)."""
    out = {}
    for i, (t, a) in L.items():
        if t != 'IFCRELASSIGNSTOGROUP': continue
        p = args(a); g = ref(p[-1])
        nome = args(L[g][1])[2].strip("'") if g in L else ''
        for e in refs(p[4]): out.setdefault(e, nome)
    return out


def dec(s):
    s = s.strip("'")
    s = re.sub(r'\\X\\([0-9A-F]{2})', lambda m: bytes([int(m.group(1), 16)]).decode('latin-1'), s)
    return s


if __name__ == '__main__':
    SIS = sistemas(); W = []
    for i, (t, a) in L.items():
        if t not in ('IFCFLOWSEGMENT', 'IFCFLOWFITTING', 'IFCFLOWTERMINAL', 'IFCFLOWCONTROLLER', 'IFCDISTRIBUTIONFLOWELEMENT'): continue
        p = args(a); RAIOS.clear()
        try: P = elemento(i)
        except Exception as ex: P = np.zeros((0, 3)); print('falhou', i, ex)
        if len(P) == 0: continue
        c = P.mean(0); U, S, Vt = np.linalg.svd(P - c, full_matrices=False); u = Vt[0]
        s = (P - c) @ u; a0, b0 = c + u * s.min(), c + u * s.max()
        perp = np.linalg.norm((P - c) - np.outer(s, u), axis=1)
        W.append(dict(id=i, tipo=t[3:].lower(), nome=dec(p[2]), tipo_familia=dec(p[4]), tag=dec(p[7]) if len(p) > 7 else '', sistema=dec(SIS.get(i, '')),
                      E_ini=round(a0[0], 3), N_ini=round(a0[1], 3), z_ini=round(a0[2], 3), E_fim=round(b0[0], 3), N_fim=round(b0[1], 3), z_fim=round(b0[2], 3),
                      L=round(float(s.max() - s.min()), 3), diam=round(2 * max(RAIOS), 4) if RAIOS else round(2 * float(np.percentile(perp, 95)), 4),
                      zmin=round(float(P[:, 2].min()), 3), zmax=round(float(P[:, 2].max()), 3)))
    with open(os.path.join(D, 'PJC_ifc_asbuilt_redes.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(W[0]), delimiter=';'); w.writeheader(); w.writerows(W)
    print(len(W), 'elementos gravados')
