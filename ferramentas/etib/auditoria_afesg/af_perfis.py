"""Perfis longitudinais da AF: terreno as built, topo do tubo antigo e novo (PIL, sem matplotlib)."""
import sys, json, csv, math, collections
sys.path.insert(0, 'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from common import pipes, D
from PIL import Image, ImageDraw, ImageFont

P = {p['id']: p for p in pipes('Água fria')}
R = json.load(open(D + 'af_renivel.json'))['legs']
S = collections.defaultdict(list)
for r in csv.DictReader(open(D + 'af_amostras_z.csv'), delimiter=';'):
    S[r['id']].append((float(r['s']), float(r['x']), float(r['y']), float(r['zt'])))
CH = {'A - Abastecimento: hidrômetro -> reservatório': ['443432', '443435', '443438', '443441', '443444', '443447', '443450', '443453', '443456'],
      'B - Recalque: bombas -> ADM / Refeitório': ['443486', '443489', '443492', '443495', '443498', '443501', '443504', '443507', '443510', '443513', '443516', '443519'],
      'C - Recalque: bombas -> 24 Salas / Auditório (área de veículos = 0,60 m)': ['443531', '443537', '443540', '443543', '443546', '443549', '443552', '443555']}

def chain(ids):
    """devolve listas de (x_dist, z) por série"""
    terr, terr30, old, new, marks = [], [], [], [], []
    pos = 0; prev = None
    for k, i in enumerate(ids):
        p = P[i]; a, b = p['a'], p['b']
        if k == 0:
            n = P[ids[1]]
            rev = min(math.dist(a[:2], n['a'][:2]), math.dist(a[:2], n['b'][:2])) < min(math.dist(b[:2], n['a'][:2]), math.dist(b[:2], n['b'][:2]))
        else:
            rev = math.dist(b[:2], prev[:2]) < math.dist(a[:2], prev[:2])
        ini, fim = (b, a) if rev else (a, b)
        if prev is not None: pos += math.dist(prev[:2], ini[:2])
        Lh = math.dist(a[:2], b[:2])
        sm = sorted(S[i], key=lambda q: (Lh - q[0]) if rev else q[0])
        terr.append([(pos + ((Lh - q[0]) if rev else q[0]), q[3]) for q in sm])
        terr30.append([(x, z - 0.30) for x, z in terr[-1]])
        old.append([(pos, ini[2] + p['dn'] / 2000), (pos + Lh, fim[2] + p['dn'] / 2000)])
        for r in [r for r in R if r['orig'] == i]:
            sp = lambda pt: pos + ((Lh - math.dist(pt, a[:2])) if rev else math.dist(pt, a[:2]))
            new.append([(sp(r['a']), r['za'] + r['dn'] / 2000), (sp(r['b']), r['zb'] + r['dn'] / 2000)])
        marks.append((pos + Lh / 2, i[-3:]))
        pos += Lh; prev = fim
    return terr, terr30, old, new, marks, pos

W, Hp, M = 2000, 520, 70
img = Image.new('RGB', (W, Hp * 3 + 90), 'white'); d = ImageDraw.Draw(img)
try:
    F = ImageFont.truetype('arial.ttf', 18); Fs = ImageFont.truetype('arial.ttf', 14); Fb = ImageFont.truetype('arialbd.ttf', 22)
except Exception:
    F = Fs = Fb = ImageFont.load_default()
d.text((M, 15), 'ETIB Alagoinhas - AF: renivelamento proposto sobre o terreno as built (topo do tubo = terreno - 0,30 m; 0,60 m em área de veículos)', fill='black', font=Fb)
leg = [('terreno as built (IMP)', (139, 90, 43)), ('terreno - 0,30 m', (200, 160, 120)), ('topo do tubo ANTIGO', (220, 30, 30)), ('topo do tubo NOVO (proposta)', (0, 87, 184))]
for k, (t, c) in enumerate(leg):
    x = M + k * 360; d.line([(x, 62), (x + 40, 62)], fill=c, width=5); d.text((x + 50, 52), t, fill='black', font=F)
for j, (nome, ids) in enumerate(CH.items()):
    terr, terr30, old, new, marks, Ltot = chain(ids)
    zs = [z for s in terr + old + new for _, z in s]
    z0, z1 = min(zs) - 0.3, max(zs) + 0.3
    top = 90 + j * Hp + 40; bot = 90 + (j + 1) * Hp - 50
    X = lambda x: M + 40 + x / Ltot * (W - 2 * M - 40)
    Y = lambda z: bot - (z - z0) / (z1 - z0) * (bot - top)
    d.text((M, top - 35), nome, fill='black', font=Fb)
    d.rectangle([X(0), top, X(Ltot), bot], outline=(180, 180, 180))
    zt = math.floor(z0 * 2) / 2
    while zt <= z1:
        if zt >= z0: d.line([(X(0), Y(zt)), (X(Ltot), Y(zt))], fill=(235, 235, 235)); d.text((M - 30, Y(zt) - 8), f'{zt:.1f}', fill='gray', font=Fs)
        zt += 0.5
    for s, c, w in [(t, (200, 160, 120), 1) for t in terr30] + [(t, (139, 90, 43), 3) for t in terr] + [(t, (220, 30, 30), 3) for t in old] + [(t, (0, 87, 184), 5) for t in new]:
        d.line([(X(x), Y(z)) for x, z in s], fill=c, width=w)
    for x, t in marks: d.text((X(x) - 12, bot + 5), t, fill='gray', font=Fs)
    for x in range(0, int(Ltot) + 1, 20): d.text((X(x) - 10, bot + 24), f'{x} m', fill=(120, 120, 120), font=Fs)
img.save('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/AF_renivelamento_perfis_proposta_2026-10-14.png')
print('ok')
