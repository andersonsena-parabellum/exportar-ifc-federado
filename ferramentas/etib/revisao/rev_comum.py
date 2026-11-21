# -*- coding: utf-8 -*-
"""Revisão de qualidade (analista de qualidade do contrato): peças comuns às conferências.
Achado = uma linha do relatório: item do checklist, onde (arquivo/prancha + local), o que está errado, regra, nível.
Níveis: PENDENCIA (corrigir antes do envio), OBSERVACAO (não bloqueia), INFO (evidência/contagem), AGUARDANDO (item suspenso).
A revisão só LÊ os arquivos das escolas; tudo o que ela grava fica em FERRAMENTAS\\revisao\\relatorios\\<ESCOLA>\\."""
import os, re, sys, csv, json, math, hashlib, datetime, collections
from dataclasses import dataclass, field, asdict

RAIZ = r'D:\Projeto Modelagem'
FERR = os.path.join(RAIZ, 'FERRAMENTAS')
PRECLASH = os.path.join(FERR, 'preclash')
SAIDA = os.path.join(FERR, 'revisao', 'relatorios')
if PRECLASH not in sys.path: sys.path.append(PRECLASH)

NIVEIS = ('PENDENCIA', 'OBSERVACAO', 'AGUARDANDO', 'INFO')


@dataclass
class Achado:
    item: str            # id do checklist (ex.: 'D3')
    nivel: str           # PENDENCIA | OBSERVACAO | AGUARDANDO | INFO
    onde: str            # arquivo ou prancha
    local: str           # trecho/caixa + coordenada, ou região da folha
    problema: str        # o que está errado (curto, objetivo)
    regra: str = ''      # regra violada (texto curto do checklist)
    E: float = None
    N: float = None
    extra: dict = field(default_factory=dict)


class Revisao:
    def __init__(self, escola, sigla):
        self.escola, self.sigla = escola, sigla
        self.achados = []; self.evidencias = collections.OrderedDict()   # item -> lista de linhas de evidência

    def add(self, *a, **k):
        x = Achado(*a, **k); self.achados.append(x); return x

    def ev(self, item, linha):
        self.evidencias.setdefault(item, []).append(linha)

    def por_item(self):
        d = collections.OrderedDict()
        for a in self.achados: d.setdefault(a.item, []).append(a)
        return d


def coord(E, N):
    return '' if E is None else f'E {E:.1f} / N {N:.1f}'


def sha1(fn, bloco=1 << 20):
    h = hashlib.sha1()
    with open(fn, 'rb') as f:
        while True:
            b = f.read(bloco)
            if not b: break
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- nomes de folha
RX_FOLHA = re.compile(r'^(?P<ano>\d{2})-(?P<ctr>\d{3})-(?P<mun>[A-Z0-9]{3})-(?P<loc>[A-Z]{3})-(?P<empr>[A-Z]+)-(?P<setor>[A-Z0-9]+)-(?P<etapa>[A-Z]{2})-'
                      r'(?P<dis>[A-Z]+)-(?P<num>\d{3})-(?:(?P<cont>[A-Z]{3})-)?R(?P<rev>\d{2})$')


def folha(nome):
    """'AA-CTR-MUN-LOC-ETIB-IMP-PE-AF-001-HIG-R03(.pdf)' -> dict(setor, dis, num, cont, rev, base, curto) ou None."""
    st = os.path.splitext(os.path.basename(nome))[0]
    m = RX_FOLHA.match(st)
    if not m: return None
    d = m.groupdict(); d['rev'] = int(d['rev']); d['stem'] = st
    d['base'] = st[:st.rfind('-R')]
    d['curto'] = f"{'' if d['setor'] == 'IMP' else d['setor'] + ' '}{d['dis']}-{d['num']}"
    return d


# ---------------------------------------------------------------- relatório
TIT = {'A': 'Entregável e pasta de envio', 'B': 'IFC: informação (classes, material, diâmetro, sistema)',
       'C': 'IFC: continuidade e conexões', 'D': 'IFC: regras de compatibilização', 'E': 'Pranchas (PDF e DWG)'}


def veredito(rv):
    n = collections.Counter(a.nivel for a in rv.achados)
    if n['PENDENCIA']: return 'REPROVADO', n
    if n['AGUARDANDO']: return 'APROVADO COM ITEM SUSPENSO', n
    return 'APROVADO', n


def gravar(rv, pasta, titulo_entrega, checklist_itens, cabecalho_extra=(), sufixo=''):
    os.makedirs(pasta, exist_ok=True)
    hoje = datetime.date.today().isoformat()
    base = f'REVISAO_{rv.sigla}_{hoje}{sufixo}'
    k = 2
    while os.path.exists(os.path.join(pasta, base + '.md')):          # nunca sobrescreve um relatório já entregue
        base = f'REVISAO_{rv.sigla}_{hoje}{sufixo}_{k}'; k += 1
    ver, n = veredito(rv)
    L = [f'# Revisão de qualidade: {rv.escola} ({rv.sigla})', '',
         f'- Entrega revisada: {titulo_entrega}', f'- Data da revisão: {hoje}',
         f'- Checklist: `FERRAMENTAS\\revisao\\CHECKLIST.md`', *cabecalho_extra, '',
         f'## Veredito: **{ver}**', '',
         f'{len({(a.item, a.onde, re.sub(r"-?[0-9]+(?:[.,][0-9]+)?", "#", a.problema)) for a in rv.achados if a.nivel == "PENDENCIA"})} grupos de pendência '
         f'({n["PENDENCIA"]} ocorrências), {n["OBSERVACAO"]} observações, {n["AGUARDANDO"]} ocorrências em itens suspensos.', '']
    def grupos(niveis):
        g = collections.OrderedDict()
        for a in rv.achados:
            if a.nivel not in niveis: continue
            k = (a.item, a.nivel, a.onde, re.sub(r'-?\d+(?:[.,]\d+)?', '#', a.problema), a.regra)
            g.setdefault(k, []).append(a)
        return g
    pend = grupos(('PENDENCIA',))
    if pend:
        L += ['## Pendências (corrigir antes do envio)', '', 'Achados iguais estão agrupados; a lista completa, com coordenadas, está no CSV ao lado.', '',
              '| # | Item | Onde | Qtd. | Problema (exemplo) | Locais (até 4) | Regra |', '|---|---|---|---|---|---|---|']
        for k, ((it, nv, onde, _, regra), aa) in enumerate(pend.items(), 1):
            L.append(f'| {k} | {it} | {onde} | {len(aa)} | {aa[0].problema} | {"<br>".join(a.local for a in aa[:4])} | {regra} |')
        L.append('')
    obs = grupos(('OBSERVACAO', 'AGUARDANDO'))
    if obs:
        L += ['## Observações e itens suspensos', '', '| Nível | Item | Onde | Qtd. | Observação (exemplo) | Locais (até 3) |', '|---|---|---|---|---|---|']
        for (it, nv, onde, _, regra), aa in obs.items():
            L.append(f'| {nv.lower()} | {it} | {onde} | {len(aa)} | {aa[0].problema} | {"<br>".join(a.local for a in aa[:3])} |')
        L.append('')
    L += ['## Resultado por item do checklist', '']
    por = rv.por_item()
    for it, desc in checklist_itens:
        ach = por.get(it, [])
        c = collections.Counter(a.nivel for a in ach)
        so_visual = it in rv.evidencias and all(e.startswith('conferência visual') for e in rv.evidencias[it])
        st = ('PENDENTE' if c['PENDENCIA'] else 'SUSPENSO' if c['AGUARDANDO'] else 'OK com observação' if c['OBSERVACAO'] else
              'conferência visual (analista)' if so_visual else 'OK' if it in rv.evidencias or ach else 'não conferido')
        L.append(f'- **{it}** {desc}: {st}' + (f' ({c["PENDENCIA"]} pendência(s))' if c['PENDENCIA'] else ''))
        for e in rv.evidencias.get(it, [])[:12]:
            L.append(f'  - {e}')
    open(os.path.join(pasta, base + '.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    with open(os.path.join(pasta, base + '_achados.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['item', 'nivel', 'onde', 'local', 'problema', 'regra', 'E', 'N'])
        for a in rv.achados:
            w.writerow([a.item, a.nivel, a.onde, a.local, a.problema, a.regra,
                        '' if a.E is None else f'{a.E:.2f}', '' if a.N is None else f'{a.N:.2f}'])
    return os.path.join(pasta, base + '.md'), ver, n
