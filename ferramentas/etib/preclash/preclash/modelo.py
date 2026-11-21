# -*- coding: utf-8 -*-
"""Modelo da pré-compatibilização: elementos lineares (eixo 3D + diâmetro externo) e caixas.
Tudo em UTM (E, N) e cota absoluta (m).

Elemento (dict):
  id        identificador único ('ELE:IE-003')
  disc      disciplina do clash: AF, ESG, AP (pluvial), DRE (drenagem do campo/macro), ELE, HID, SDAI ...
  rede      rede/arquivo de origem (dois elementos da mesma rede não se testam entre si)
  trecho    nome do trecho no projeto
  tipo      'pressao' (cota é premissa, pode ser mudada) | 'gravidade' (cota do projeto, fixa)
  de        diâmetro externo (m)
  pts       eixo (n,3) — a versão original; a solução fica em 'pts_sol'
  cob_min   recobrimento mínimo (m) sobre o topo do tubo (redes pressurizadas)
  info      dict de texto livre (material, DN, origem da cota, observações)
  pendente  True se o elemento ainda não é certo (ex.: galeria 'rede futura') — cenário próprio
Caixa (dict): id, disc, rede, forma ('q' quadrada | 'c' circular | 'r' retangular girada), E, N, meia (meio lado ou raio, com parede;
  na 'r' é o raio que a envolve), zb, zt, info; só na 'r': mx, my (meios lados, com parede) e rot (giro em planta, rad, anti-horário a partir do E)
"""
import numpy as np

# DN nominal (mm) -> diâmetro externo (mm) das tubulações por gravidade (PVC esgoto/pluvial; PVC rígido corrugado ~ +12 %)
DE_GRAV = {40: 40, 50: 50, 75: 75, 100: 110, 150: 160, 200: 225, 250: 280, 300: 335, 400: 450}


def de_gravidade(dn_mm, material=''):
    dn = int(round(float(dn_mm)))
    de = DE_GRAV.get(dn, dn * 1.1)
    if 'PVCR' in (material or '') or 'DR' in (material or ''):
        de = max(de, dn * 1.12)
    return de / 1000.0


def comprimento_planta(pts):
    d = np.diff(np.asarray(pts)[:, :2], axis=0)
    return np.concatenate([[0.0], np.cumsum(np.hypot(d[:, 0], d[:, 1]))])


def elemento(id, disc, rede, trecho, tipo, de, pts, cob_min=None, movel=None, pendente=False, **info):
    pts = np.asarray(pts, float)
    return {'id': id, 'disc': disc, 'rede': rede, 'trecho': trecho, 'tipo': tipo, 'de': float(de), 'pts': pts,
            'pts_sol': pts.copy(), 'cob_min': cob_min, 'movel': (tipo == 'pressao') if movel is None else movel,
            'pendente': pendente, 'info': info}


def caixa(id, disc, rede, forma, E, N, meia, zb, zt, mx=None, my=None, rot=0.0, **info):
    c = {'id': id, 'disc': disc, 'rede': rede, 'forma': forma, 'E': float(E), 'N': float(N), 'meia': float(meia),
         'zb': float(zb), 'zt': float(zt), 'info': info}
    if forma == 'r':
        c['mx'] = float(mx if mx is not None else meia); c['my'] = float(my if my is not None else meia); c['rot'] = float(rot)
        c['meia'] = float(np.hypot(c['mx'], c['my']))
    return c


def caixa_retangular(id, disc, rede, E, N, lx, ly, rot, zb, zt, **info):
    """atalho: prisma lx × ly (m, já com parede) girado rot (rad) — pilar, quadro, evaporadora, abrigo, reservatório..."""
    return caixa(id, disc, rede, 'r', E, N, 0.0, zb, zt, mx=lx / 2, my=ly / 2, rot=rot, **info)


def planta_local(c, x, y):
    """distância por eixo (|dx| − meio lado, |dy| − meio lado) do ponto à caixa quadrada ou retangular girada."""
    dx = np.asarray(x) - c['E']; dy = np.asarray(y) - c['N']
    if c['forma'] == 'r':
        cs, sn = np.cos(c['rot']), np.sin(c['rot'])
        lx, ly = dx * cs + dy * sn, -dx * sn + dy * cs
        return np.abs(lx) - c['mx'], np.abs(ly) - c['my']
    return np.abs(dx) - c['meia'], np.abs(dy) - c['meia']
