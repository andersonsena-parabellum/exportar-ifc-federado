# -*- coding: utf-8 -*-
"""Grava o JSON consolidado das transformações local -> UTM da ETIB Sátiro Dias.
Calcula também a transformação alternativa "pelo terreno" de PCI/ELE (textos do terreno da base deles x SIT R06)."""
import sys, os, re, json, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casar
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work')
out = sys.argv[1]


def un(g):
    d = collections.defaultdict(list)
    for t in g['texts']:
        s = re.sub(r'\\[A-Za-z][^;]*;|[{}]', '', t['t']).strip()
        if len(s) >= 3:
            d[s].append(t)
    return {k: v[0] for k, v in d.items() if len(v) == 1}


I = un(casar.cache_load(os.path.join(W, 'dxf', '24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03.dxf')))
R = un(casar.cache_load(os.path.join(W, 'geo', '24-049-STK-XXX-ETIB-IMP-PE-URB-002-SIT-R06_GEO.dxf')))
ks = sorted(set(I) & set(R))
V = np.array([(R[k]['p'][0] - I[k]['p'][0], R[k]['p'][1] - I[k]['p'][1]) for k in ks])
med = np.median(V, axis=0)
grp = np.hypot(V[:, 0] - med[0], V[:, 1] - med[1]) < 0.005
t_site_in = V[grp].mean(0)
print('PCI pelo terreno: %d de %d textos, t=(%.6f, %.6f), dispersão %.2f mm' % (grp.sum(), len(ks), *t_site_in, np.hypot(*(V[grp] - t_site_in).T).max() * 1000))
d_in_el2 = np.array([504288.527602, 8651102.586050])   # IN local + d = EL-002 local (mesma base zw$5548)
t_site_el2 = t_site_in - d_in_el2
th12 = math.radians(37.6709627884); t12 = np.array([5392103.376627, 1495285.590372])  # EL-001 -> EL-002
t_site_el1 = t12 + t_site_el2

T = collections.OrderedDict()
def put(arq, disc, rot, tx, ty, metodo, conferencia, obs='', alt=None):
    e = collections.OrderedDict([('arquivo_original', arq), ('arquivo_geo', arq[:-4] + '_GEO.dwg'), ('disciplina', disc),
                                 ('rot_deg', rot), ('t', [tx, ty]), ('metodo', metodo), ('conferencia', conferencia)])
    if obs:
        e['obs'] = obs
    if alt:
        e['alternativa'] = alt
    T[arq] = e

P = 'PROJETO_ORIGINAL/IMP/'
put(P + '00_BASE/24-049-STK-XXX-ETIB-IMP-PE-URB-002-SIT-R06.dwg', 'BASE (SIT atual)', 0.0, -339.472979, 0.0,
    'blocos e textos comuns com TER-001-SIT, PAV e DRE (translação pura, dispersão 0,00 mm)',
    'rótulos da malha de coordenadas (PRO_COORD) do próprio SIT R06 confirmam o deslocamento de 339,473 m em X',
    'O SIT R06 do Drive está deslocado +339,473 m em E em relação ao UTM; o _GEO corrige. Removidos 2 objetos perdidos a milhares de km (Porta abrigo, 09-PISO).')
for n, disc in (('URB-001-PAV-R07', 'BASE (pavimentação)'), ('TER-001-SIT-R03', 'BASE (terraplanagem, situação)'),
                ('TER-001-PLT-R00', 'BASE (terraplanagem, planta)'), ('TOP-001-PLT-R00', 'TOPOGRAFIA')):
    put(P + '00_BASE/24-049-STK-XXX-ETIB-IMP-PE-%s.dwg' % n, disc, 0.0, 0.0, 0.0, 'já em UTM SIRGAS 2000 / 24S (malha E/N rotulada confere)',
        'TOP x TER-001-SIT: postes (bloco PT) a 1,2 cm; PAV = TER-001-SIT (0,00 mm)',
        'Cópia _GEO só com INSUNITS = metros' + ('; removidos 9 blocos vazios com coordenadas da ETIB Alagoinhas (~60 km)' if n.startswith('TOP') else ''))
for n in ('DRE-001-DRG-R02', 'DRE-002-DRG-R02'):
    put(P + '03_DRE/24-049-STK-XXX-ETIB-IMP-PE-%s.dwg' % n, 'DRE', 0.0, 0.0, 0.0, 'já em UTM', 'blocos de arquitetura x SIT R06 (UTM): 0,00 mm')
for n, d in (('01_AF/24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R00.dwg', 'AF'), ('02_ESG/24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R00.dwg', 'ESG + AP (pluvial)')):
    put(P + n, d, 0.0, 545929.370875, 8716089.409625,
        'poses de 6 blocos da arquitetura embutida (ARQ_BASE: quadras, porta, nível) x SIT R06/PAV, dispersão 0,00 mm',
        'ICP ponto-segmento sobre a PAV R07: correção 0,1 mm; 42% dos pontos da arquitetura a < 5 mm (o resto não existe na PAV)',
        'No ESG há uma 2ª cópia da ARQ_BASE em escala 0,7836 (detalhe ampliado da prancha): a rede desenhada sobre ela não é a rede real.')
alt_in = {'rot_deg': 0.0, 't': [float(t_site_in[0]), float(t_site_in[1])],
          'nota': 'alinha o TERRENO da base deles (muros, rua, textos da topografia) ao SIT R06; os blocos ficam girados 0,57°'}
put(P + '05_PCI/24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R03.dwg', 'PCI', 0.5674960469, 545931.222845, 8716090.163514,
    'poses de 74–79 blocos de mobiliário dentro das edificações (base zw$5548) x SIT R06/PAV; base idêntica à do EL-002 (translação pura)',
    'ICP nas edificações: 0,0 mm; 33% dos pontos da base a < 5 mm',
    'A base de arquitetura do PCI/ELE tem as EDIFICAÇÕES giradas 0,5675° em relação ao TERRENO (o terreno da base deles bate com o SIT só por translação). '
    'A rede do PCI é paralela às edificações (37,398° local), por isso vale a transformação pelas edificações. Diferença entre as duas hipóteses: 0,3 a 1,3 m na divisa do lote.',
    alt_in)
put(P + '04_ELE/24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R01.dwg', 'ELE (alimentação)', 0.5674960469, 127352.385312, 60417.189666,
    'poses de 74 blocos de mobiliário (base zw$46AE>zw$5548) x SIT R06/PAV, dispersão 0,00 mm', 'ICP: 1,3 mm',
    'Mesma base girada do PCI. Os eletrodutos de alimentação longos seguem a rua (38,37° local), não as edificações: na divisa podem estar até ~1 m deslocados do SIT.',
    {'rot_deg': 0.0, 't': [float(t_site_el2[0]), float(t_site_el2[1])], 'nota': 'pelo terreno (ver PCI)'})
put(P + '04_ELE/24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R01.dwg', 'ELE (iluminação externa)', 38.2384588353, 5504381.199564, 1609035.590598,
    'poses de 74 blocos de mobiliário (base zw$46AE girada -37,671° na prancha) x SIT R06/PAV', 'ICP: 1,3 mm',
    'O bloco zw$6305 (subestação) desta prancha está girado 0,126° diferente da base: usar a subestação do EL-002. Removidas 2 polilinhas perdidas a ~8 000 km.',
    {'rot_deg': 37.6709627884, 't': [float(t_site_el1[0]), float(t_site_el1[1])], 'nota': 'pelo terreno (ver PCI)'})
C = 'PROJETO_ORIGINAL/CPS/'
cps = {l.split()[0]: l.split()[1:] for l in open(os.path.join(W, 'out', 'cps_transf.txt'))}
for n, sub, disc in (('ETIB-CPS-PE-DRE-001-DRG-R01', '03_DRE', 'DRE (campo society)'), ('CP1-CPS-PE-ELE-001-ELG-R00', '04_ELE', 'ELE (campo society, 380/220 V)'),
                     ('CP1-CPS-PE-ELE-002-ELG-R00', '04_ELE', 'ELE (campo society, 220/127 V)'), ('ETIB-CPS-PE-IN-001-ING-R01', '05_PCI', 'PCI (campo society: só sinalização e extintores)')):
    r, tx, ty = map(float, cps[n])
    put(C + sub + '/24-049-STK-XXX-%s.dwg' % n, disc, r, tx, ty,
        'APROXIMADO: centro do retângulo do campo do desenho local -> centro do campo na PAV (545903,871; 8716168,206), eixo maior a 127,743934°; '
        'sentido escolhido pelo QDLT-CAMPO no canto norte (igual ao EL-002 da implantação)',
        'sem blocos comuns; o campo do projeto CPS mede 54,3 x 34,3 m e o da implantação 52,8 x 33,4 m (até ~0,75 m de diferença nas pontas)',
        'O IN-002 (CPS) só tem detalhes, sem planta: não há o que vincular.' if 'IN-001' in n else '')
doc = collections.OrderedDict([
    ('escola', 'ETIB Sátiro Dias-BA (contrato 24-049)'),
    ('sistema', 'UTM SIRGAS 2000, fuso 24S (MC -39°); cotas = altitude do levantamento'),
    ('convencao', 'p_utm = R(rot_deg) · p_local + t   (rotação anti-horária em torno de (0,0), depois translação)'),
    ('referencia_utm', 'TOP-001 (levantamento), TER-001-SIT R03, TER-001-PLT R00, URB-001-PAV R07 e DRE-001/002 R02 já estão em UTM e coincidem'),
    ('origem_revit_proposta', {'E': 546000.0, 'N': 8716200.0, 'cota': 0.0, 'rotacao': 0.0}),
    ('gerado_em', '2026-10-18'),
    ('arquivos', T)])
json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', out, len(T), 'arquivos')
