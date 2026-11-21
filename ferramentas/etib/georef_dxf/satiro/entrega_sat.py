# -*- coding: utf-8 -*-
"""ETIB Sátiro Dias — entrega em IFC (19/10/2026): roda o preclash da escola (escolas/satiro.py: cenários A, B, AD, BD)
e grava os IFC com os EQUIPAMENTOS (equip_sat.py) além de tubos, caixas, subidas e canaletas:
  - federados: SAT_preclash_projeto.ifc e SAT_preclash_solucao_<cenário>.ifc (com as esferas dos conflitos que sobram);
  - por disciplina do contrato (HIDRO, ELE, PCIP) + TERRENO, para AD (entrega: sem a galeria + desvios em planta) e BD (com a galeria).
Não altera a ferramenta (FERRAMENTAS/preclash): só troca a função de exportação do IFC do rodar.py nesta execução.
Uso: .venv/Scripts/python.exe -X utf8 FERRAMENTAS/georef_dxf/satiro/entrega_sat.py"""
import os, sys, math, collections
import numpy as np
PRECLASH = r'D:\Projeto Modelagem\FERRAMENTAS\preclash'
sys.path.insert(0, PRECLASH)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rodar                                   # noqa: E402
from preclash.export_ifc import Ifc, COR       # noqa: E402
import ifcopenshell, ifcopenshell.guid         # noqa: E402
import equip_sat                               # noqa: E402

ENTREGAS = ('AD', 'BD')
PASSO_TERRENO = 1.0
PRED = {'IfcLightFixture': 'POINTSOURCE', 'IfcElectricDistributionBoard': 'DISTRIBUTIONBOARD', 'IfcFlowMeter': 'ENERGYMETER',
        'IfcFireSuppressionTerminal': 'FIREHYDRANT', 'IfcUnitaryControlElement': 'ALARMPANEL', 'IfcTank': 'STORAGE', 'IfcValve': 'FAUCET'}
NOME_GRUPO = {'ELE': 'Elétrica — equipamentos', 'HID': 'Hidrantes (PCI) — equipamentos', 'SDAI': 'SDAI (PCI) — equipamentos', 'AF': 'Água fria — equipamentos'}


class IfcSat(Ifc):
    def terreno(self, V, F, nome='Terreno (IMP as built)'):
        el = super().terreno(V, F, nome)
        el.Description = 'terreno acabado do IMP as built (sólidos topográficos + pisos), grade de 1 m'
        return el

    def caixa(self, c, grupo):
        """estrutura as built: IfcFooting / IfcColumn / IfcBeam em vez de câmara."""
        if c['disc'] != 'EST': return super().caixa(c, grupo)
        f = self.f; h = max(0.05, c['zt'] - c['zb']); rot = c.get('rot', 0.0)
        item = self._solido_caixa((c['E'], c['N']), 2 * c.get('mx', c['meia']), 2 * c.get('my', c['meia']), h, c['zb'], rot)
        t = c['info'].get('tipo', '')
        classe, pred = (('IfcColumn', 'COLUMN') if 'Pilar' in t else ('IfcBeam', 'BEAM') if 'Quadro' in t else ('IfcFooting', 'PAD_FOOTING'))
        ps = {'disciplina': 'EST', 'tipo': t, 'fundo': c['zb'], 'topo_no_modelo': c['zt'], 'origem': c['info'].get('cota')}
        return self._produto(classe, c['info'].get('nome', c['id']), t, item, 'SweptSolid', 'EST', ps, grupo, pred, transp=0.4)

    def _solido_caixa(self, c, a, b, h, z0, rot):
        f = self.f
        u = (math.cos(rot), math.sin(rot), 0.0)
        pos = f.createIfcAxis2Placement3D(self.p((c[0], c[1], z0)), f.createIfcDirection((0.0, 0.0, 1.0)), f.createIfcDirection(u))
        p2 = f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((0.0, 0.0)), None)
        return f.createIfcExtrudedAreaSolid(f.createIfcRectangleProfileDef('AREA', None, p2, float(a), float(b)), pos, f.createIfcDirection((0.0, 0.0, 1.0)), float(h))

    def _solido_cil(self, c, d, h, z0):
        f = self.f
        pos = f.createIfcAxis2Placement3D(self.p((c[0], c[1], z0)), None, None)
        p2 = f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((0.0, 0.0)), None)
        return f.createIfcExtrudedAreaSolid(f.createIfcCircleProfileDef('AREA', None, p2, float(d) / 2), pos, f.createIfcDirection((0.0, 0.0, 1.0)), float(h))

    def equipamento(self, q):
        f = self.f
        c = (q['E'], q['N']); zt = q['terreno']; z0 = zt + float(q['base_sobre_terreno']); rot = math.radians(q['rot_graus'])
        a, b, h = float(q['dim_a']), float(q['dim_b']), float(q['altura'])
        if q['forma'] == 'poste':
            it = [self._solido_cil(c, a, h, zt)]
            u = np.array([math.cos(rot), math.sin(rot)]); cab = np.array(c) + u * b / 2 * (0.0 if b > 1 else 1.0)
            it.append(self._solido_caixa(cab, b, 0.30, 0.15, zt + h - 0.15, rot))
        elif q['forma'] == 'cil':
            it = [self._solido_cil(c, a, h, z0)]
        elif q['forma'] == 'taca':
            hc = 55.0 / (math.pi * (b / 2) ** 2)
            it = [self._solido_cil(c, a, h - hc, zt), self._solido_cil(c, b, hc, zt + h - hc)]
        else:
            it = [self._solido_caixa(c, a, b, h, z0, rot)]
        cor = q['disciplina']
        for x in it: f.createIfcStyledItem(x, [self.estilo(cor)], None)
        rep = f.createIfcShapeRepresentation(self.body, 'Body', 'SweptSolid', it)
        shp = f.createIfcProductDefinitionShape(None, None, [rep])
        pl = f.createIfcLocalPlacement(self.site_pl, self.wcs)
        classe = q['classe_ifc']
        pred = q.get('pred') or PRED.get(classe)
        if q['id'] == 'HID-RECALQUE': pred = 'BREECHINGINLET'
        if q['id'] == 'MEDICAO': pred = 'ENERGYMETER'
        el = f.create_entity(classe, GlobalId=ifcopenshell.guid.new(), Name=q['id'], Description=q['tipo'], ObjectPlacement=pl, Representation=shp, PredefinedType=pred)
        self.contidos.append(el)
        self.pset(el, 'EQUIPAMENTO', {'disciplina': q['disciplina'], 'tipo': q['tipo'], 'origem': q['origem'], 'premissa': q['premissa'],
                                      'terreno': q['terreno'], 'altura_m': h, 'E': q['E'], 'N': q['N']})
        self.grupos.setdefault(NOME_GRUPO.get(q['disciplina'], q['disciplina'] + ' — equipamentos'), []).append(el)
        return el


def exportar_ifc_sat(S, D, res):
    ter = D['terreno']
    V, F = ter.grade(S.CAIXA_OBRA, PASSO_TERRENO)
    Q = equip_sat.equipamentos(ter)
    print(f'  equipamentos: {len(Q)}', dict(collections.Counter(q["grupo_entrega"] for q in Q)))
    kp = getattr(S, 'CENARIO_PROJETO', None) or next(iter(D['cenarios']))
    casos = [('projeto', 'Projeto (antes das soluções)', kp, 'pts')] + [(f'solucao_{k}', f"Solução {k} — {r['nome']}", k, 'pts_sol') for k, r in res.items()]
    for nomearq, titulo, k, campo in casos:
        r = res[k]; cx = r['caixas']
        f = IfcSat(f'{S.ESCOLA} — federado — {titulo}', S.ORIGEM, S.EPSG)
        f.terreno(V, F, 'Terreno (IMP as built)')
        porel = collections.defaultdict(list)
        for s in r['sol']: porel[s['elemento']].append(s)
        for e in r['E']:
            s = porel.get(e['id']) if campo == 'pts_sol' else None
            ps = rodar.pset_el(e, k, s)
            if campo == 'pts_sol' and e.get('desvio'): ps['desvio_em_planta'] = 'sim'
            f.tubo(e, e[campo], ps, S.NOMES_DISC.get(e['disc'], e['disc']))
        for c in (D['caixas'] if campo == 'pts' else cx):
            if not c['info'].get('equipamento'): f.caixa(c, S.NOMES_DISC.get(c['disc'], c['disc']) + ' — caixas')
        mv = {c['info'].get('nome'): c for c in cx if c['info'].get('equipamento') and 'E0' in c} if campo == 'pts_sol' else {}
        for q in Q: f.equipamento(dict(q, E=mv[q['id']]['E'], N=mv[q['id']]['N']) if q['id'] in mv else q)
        conf = r['antes'] if campo == 'pts' else r['final']
        for n, c in enumerate([c for c in conf if not c['ligacao']], 1):
            txt, est = rodar.desc_conf(c, r['ids'], {q['id']: q for q in cx})
            f.conflito(c, f'C{n:03d}', {'gravidade': c['gravidade'], 'descricao': txt, 'folga_m': c['folga'], 'A': c['a'], 'B': c['b'], 'cota_estimada': 'sim' if est else None})
        fn = os.path.join(S.SAIDA, f'{S.SIGLA}_preclash_{nomearq}.ifc'); f.salvar(fn)
        print('  IFC', os.path.basename(fn), f'{os.path.getsize(fn) / 1e6:.1f} MB')
    grupo_disc = {'HIDRO': ('AF',), 'ELE': ('ELE',), 'PCIP': ('HID', 'SDAI')}
    for k in ENTREGAS:
        if k not in res: continue
        r = res[k]; pasta = os.path.join(S.SAIDA, f'IFC_POR_DISCIPLINA_{k}'); os.makedirs(pasta, exist_ok=True)
        porel = collections.defaultdict(list)
        for s in r['sol']: porel[s['elemento']].append(s)
        for grupo, discs in S.DISCIPLINAS_ENTREGA.items():
            f = IfcSat(f'{S.ESCOLA} — {grupo} — compatibilizado (cenário {k}: {r["nome"]})', S.ORIGEM, S.EPSG)
            for e in r['E']:
                if e['disc'] not in discs: continue
                ps = rodar.pset_el(e, k, porel.get(e['id']))
                if e.get('desvio'): ps['desvio_em_planta'] = 'sim'
                f.tubo(e, e['pts_sol'], ps, S.NOMES_DISC.get(e['disc'], e['disc']))
            for c in r['caixas']:
                if c['disc'] in discs and not c['info'].get('equipamento'): f.caixa(c, S.NOMES_DISC.get(c['disc'], c['disc']) + ' — caixas')
            mv = {c['info'].get('nome'): c for c in r['caixas'] if c['info'].get('equipamento') and 'E0' in c}
            for q in Q:
                if q['grupo_entrega'] == grupo: f.equipamento(dict(q, E=mv[q['id']]['E'], N=mv[q['id']]['N']) if q['id'] in mv else q)
            fn = os.path.join(pasta, f'{S.SIGLA}_{grupo}_compatibilizado.ifc'); f.salvar(fn)
            print('  IFC', os.path.relpath(fn, S.SAIDA), f'{os.path.getsize(fn) / 1e6:.2f} MB')
        f = IfcSat(f'{S.ESCOLA} — terreno acabado (IMP as built)', S.ORIGEM, S.EPSG); f.terreno(V, F, 'Terreno (IMP as built)')
        f.salvar(os.path.join(pasta, f'{S.SIGLA}_TERRENO.ifc'))
    dump_geometria(S, res)


def dump_geometria(S, res):
    """geometria das soluções (para a revisão dos executivos em DWG): trechos com mergulho/desvio e caixas deslocadas, em UTM."""
    import json
    out = {}
    for k in ENTREGAS:
        if k not in res: continue
        r = res[k]
        els = []
        for e in r['E']:
            if not (e.get('desvio') or e.get('janelas')): continue
            els.append({'id': e['id'], 'disc': e['disc'], 'rede': e['rede'], 'trecho': e['trecho'], 'desvio': bool(e.get('desvio')),
                        'pts_original': np.round(e.get('pts_original', e['pts']), 4).tolist(), 'pts': np.round(e['pts'], 4).tolist(),
                        'pts_sol': np.round(e['pts_sol'], 4).tolist(), 'desvios': [{kk: float(v) for kk, v in d.items() if kk in ('s0', 's1', 'o')} for d in e.get('desvio', []) if 's0' in d]})
        cxs = [{'id': c['id'], 'disc': c['disc'], 'nome': c['info'].get('nome'), 'E0': c['E0'], 'N0': c['N0'], 'E': c['E'], 'N': c['N'], 'meia': c['meia']}
               for c in r['caixas'] if 'E0' in c]
        sol = [{kk: (float(v) if isinstance(v, (np.floating, float)) else v) for kk, v in s.items() if kk in
                ('elemento', 'disc', 'trecho', 'modo', 'E', 'N', 's0', 's1', 'extensao', 'eixo_antes', 'eixo_depois', 'dz', 'txt')} for s in r['sol']]
        dv = [{kk: (float(v) if isinstance(v, (np.floating, float)) else v) for kk, v in d.items() if kk in
               ('elemento', 'disc', 'trecho', 'tipo', 'status', 'desloc', 'E', 'N', 's0', 's1', 'txt')} for d in r['desvios']]
        out[k] = {'nome': r['nome'], 'elementos': els, 'caixas_deslocadas': cxs, 'mergulhos': sol, 'desvios': dv}
    fn = os.path.join(S.SAIDA, f'{S.SIGLA}_entrega_geometria.json')
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, default=float)
    print('  geometria das soluções ->', os.path.basename(fn))


if __name__ == '__main__':
    rodar.exportar_ifc = exportar_ifc_sat
    rodar.main('satiro')
