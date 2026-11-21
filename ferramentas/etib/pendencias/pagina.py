# -*- coding: utf-8 -*-
"""Gerador ÚNICO da página de pendências de uma escola (PDCA A5, 22/10/2026; checklist seção F; regra em AGENTS.md > Forma de trabalho).
Uma ficha por colisão ou decisão, em dois blocos: "Precisa de decisão" e "Aplicado (pode reverter)" (o que entrou pelo aplicar e avisar).
Cada ficha: recorte da prancha do projetista centrado no ponto e marcado, com os códigos citados escritos em azul ao lado dos
elementos; vistas 3D e em planta do modelo de entrega; campo de decisão, de texto e de imagem (print da solução sugerida).
Todas as imagens geradas vão embutidas na página em base64 (abre no celular); a conferência F1–F3 roda no fim e grava
<saida>/CONFERENCIA_F.md. Publicar o index.html com capabilities {db: {}, user: {}, assets: {}}; as decisões ficam na coleção
'decisoes' (docs d01, d02…: decisao, nota, imagem = id do asset, em, por) e se leem com ArtifactData.
Uso: ..\\.venv\\Scripts\\python.exe -X utf8 pagina.py <config.json> [--sem-recortes] [--sem-vistas]   (formato da config: LEIA-ME.md)"""
import os, sys, io, json, glob, base64, html, re, argparse, datetime
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\revisao'); sys.path.insert(0, r'D:\Projeto Modelagem\FERRAMENTAS\preclash')

LIMITE_PAGINA = 15 * 1024 * 1024          # o Artifact aceita 16 MB


def normalizar(F):
    """aceita o formato da Sátiro/Alagoinhas (grupo D/G, a/b) e o novo (bloco, quem, codigos)."""
    out = []
    for f in F:
        f = dict(f)
        g = f.get('grupo')
        f['bloco'] = f.get('bloco') or ('aplicado' if g == 'A' else 'decisao')
        if f['bloco'] not in ('decisao', 'aplicado'): raise ValueError(f'ficha {f.get("n")}: bloco "{f["bloco"]}" (use decisao ou aplicado)')
        f.setdefault('quem', 'Anderson' if g == 'D' else ('projetista' if g == 'G' else ''))
        if 'codigos' not in f: f['codigos'] = [x for x in (f.get('a'), f.get('b')) if x]
        f.setdefault('folhas', [])
        out.append(f)
    ns = [f['n'] for f in out]
    if len(set(ns)) != len(ns): raise ValueError('números de ficha repetidos')
    return out


def _perto(P, q):
    """ponto da polilinha P (n×2+) mais perto de q."""
    melhor = None
    for a, b in zip(P[:-1, :2], P[1:, :2]):
        d = b - a; t = float(np.clip(((q - a) @ d) / max(d @ d, 1e-12), 0, 1)); x = a + t * d
        dist = float(np.linalg.norm(x - q))
        if melhor is None or dist < melhor[0]: melhor = (dist, x)
    return melhor


def posicoes(f, R):
    """[(código, E, N)] dos elementos citados na ficha, na posição mais perto do ponto da ficha; e a lista dos não achados."""
    q = np.array([f['E'], f['N']]); out, falta, nomes = [], [], []
    for c in f['codigos']:
        if isinstance(c, dict):
            out.append((c['codigo'], c['E'], c['N'])); nomes.append(c.get('nome', c['codigo'])); continue
        cand = []
        if R is not None:
            for s in R['seg']:
                if c in (s['nome'], s.get('trecho')):
                    d, x = _perto(s['P'], q); cand.append((d, x, s['nome']))
            for k in R['cx']:
                if c in (k['reg']['nome'], k['reg'].get('trecho'), k['reg'].get('tag')):
                    cand.append((float(np.hypot(k['E'] - q[0], k['N'] - q[1])), np.array([k['E'], k['N']]), k['reg']['nome']))
        if not cand: falta.append(c); continue
        d, x, nome = min(cand, key=lambda z: z[0])
        out.append((c, float(x[0]), float(x[1]))); nomes.append(nome)
    f['codigos_nomes'] = nomes
    return out, falta


def embutir(pasta, nomes):
    from PIL import Image
    IMG = {}
    for x in nomes:
        im = Image.open(os.path.join(pasta, x)).convert('RGB'); im.thumbnail((960, 960))
        b = io.BytesIO(); im.save(b, 'JPEG', quality=72, optimize=True); IMG[x] = base64.b64encode(b.getvalue()).decode()
    return IMG


def conferir(F, pag, IMG, faltas, sem_recorte):
    """checklist F: F1 abre no celular, F2 dois blocos, F3 conteúdo de cada ficha. Devolve [(item, nível, texto)]."""
    ach = []
    # F1: nenhuma imagem fora da página
    ext = re.findall(r'<img[^>]+src="(?!data:|/_blob/|\$\{src\()([^"]+)"', pag)     # ${src(...)} = imagem embutida, montada no script + re.findall(r"src=['\"](https?:[^'\"]+)['\"]", pag)
    ext += re.findall(r"""['"`]img/[^'"`]+""", pag)
    for x in ext[:5]: ach.append(('F1', 'PENDENCIA', f'imagem fora da página: {x[:80]}'))
    for f in F:
        for v in f['vistas']:
            if v['arquivo'] not in IMG: ach.append(('F1', 'PENDENCIA', f'ficha {f["n"]}: imagem {v["arquivo"]} não embutida'))
    tam = len(pag.encode('utf-8'))
    if tam > LIMITE_PAGINA: ach.append(('F1', 'PENDENCIA', f'página com {tam / 2**20:.1f} MB (limite do artifact 16 MB): reduzir as imagens'))
    # F2: dois blocos
    n = {b: sum(f['bloco'] == b for f in F) for b in ('decisao', 'aplicado')}
    for f in F:
        if f['bloco'] == 'aplicado' and not (f.get('reverter') or f.get('p')):
            ach.append(('F2', 'PENDENCIA', f'ficha {f["n"]} (aplicado): falta dizer como reverter (campo "reverter")'))
    # F3: recorte da prancha, códigos escritos, 3D e planta, campos
    for f in F:
        tipos = {v['tipo'] for v in f['vistas']}
        if 'prancha' not in tipos:
            ach.append(('F3', 'PENDENCIA', f'ficha {f["n"]}: sem recorte da prancha do projetista'
                        + (' (rodado com --sem-recortes)' if sem_recorte else (' (ponto fora das folhas citadas)' if f['folhas'] else ' (ficha sem "folhas")'))))
        for t in ('3d', 'planta'):
            if t not in tipos: ach.append(('F3', 'PENDENCIA', f'ficha {f["n"]}: sem a vista {t} do modelo'))
        if not f['codigos']: ach.append(('F3', 'OBSERVACAO', f'ficha {f["n"]}: nenhum código citado para escrever no recorte'))
        for c in faltas.get(f['n'], []):
            ach.append(('F3', 'PENDENCIA', f'ficha {f["n"]}: código "{c}" não achado no modelo; dar {{"codigo", "E", "N"}} na ficha'))
        for k in ('titulo', 'o', 't'):
            if not str(f.get(k, '')).strip(): ach.append(('F3', 'PENDENCIA', f'ficha {f["n"]}: texto "{k}" vazio'))
    for marca, item in (('type="radio"', 'campo de decisão'), ('<textarea', 'campo de texto'), ('type="file"', 'campo de imagem')):
        if marca not in pag: ach.append(('F3', 'PENDENCIA', f'página sem {item}'))
    return ach, n, tam


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('config'); ap.add_argument('--sem-recortes', action='store_true'); ap.add_argument('--sem-vistas', action='store_true')
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding='utf-8'))
    base_cfg = os.path.dirname(os.path.abspath(a.config))
    caminho = lambda p: p if os.path.isabs(p) else os.path.join(base_cfg, p)
    F = normalizar(json.load(open(caminho(cfg['fichas']), encoding='utf-8')))
    saida = caminho(cfg['saida']); img = os.path.join(saida, 'img'); os.makedirs(img, exist_ok=True)
    # modelo de entrega
    R = T = None
    if cfg.get('ifc'):
        import ifc_conf as IC
        arqs = sorted(glob.glob(caminho(cfg['ifc'])))
        arqs = [x for x in arqs if 'FEDERADO' not in os.path.basename(x).upper()] or arqs
        print(f'lendo {len(arqs)} IFC'); R = IC.ler(arqs, log=lambda *x: None)
    if cfg.get('terreno'):
        from preclash.terreno import Terreno
        T = Terreno(caminho(cfg['terreno']))
    faltas = {}; pos = {}
    for f in F:
        pos[f['n']], fl = posicoes(f, R)
        if fl: faltas[f['n']] = fl; print(f'  ficha {f["n"]}: código(s) não achado(s) no modelo: {", ".join(fl)}')
    # recortes da prancha
    for f in F: f['vistas'] = []
    if not a.sem_recortes and cfg.get('folhas'):
        import recortes as RC
        for d in cfg['folhas'].values():
            d['dxf'], d['pdf'] = caminho(d['dxf']), caminho(d['pdf'])
        if cfg.get('transf_json'): cfg['transf_json'] = caminho(cfg['transf_json'])
        FL = RC.folhas(cfg)
        for k, f in enumerate(F):
            for nome in f['folhas']:
                if nome not in FL: print(f'  ficha {f["n"]}: folha {nome} não está na config'); continue
                arq = RC.recortar(f, k, nome, FL[nome], img, pos[f['n']])
                if arq: f['vistas'].append(dict(tipo='prancha', rotulo=f'Prancha {nome}', arquivo=arq, folha=nome, prancha=FL[nome][2]))
                else: print(f'  ficha {f["n"]}: ponto fora da folha {nome}')
    # vistas do modelo
    if not a.sem_vistas and R is not None:
        import vistas as VS
        VS.gerar(F, R, T, img, log=lambda *x: None)
    for k, f in enumerate(F):
        for t, rot in (('3d', 'Modelo 3D'), ('planta', 'Modelo em planta')):
            if os.path.exists(os.path.join(img, f'{k:02d}_{t}.jpg')): f['vistas'].append(dict(tipo=t, rotulo=rot, arquivo=f'{k:02d}_{t}.jpg'))
        if not f['vistas']: raise SystemExit(f'ficha {f["n"]}: nenhuma imagem (sem folha e sem IFC)')
    # ordem: decisões primeiro (é o que pede ação), depois o aplicado
    IMG = embutir(img, sorted({v['arquivo'] for f in F for v in f['vistas']}))
    dados = [{k: v for k, v in f.items() if k in ('n', 'bloco', 'quem', 'titulo', 'o', 't', 'p', 'reverter', 'E', 'N', 'vistas')}
             | {'codigos': [c['codigo'] if isinstance(c, dict) else c for c in f['codigos']]} for f in F]
    from vistas import legenda, COR
    discs = ({s['disc'] for s in R['seg']} | {c['disc'] for c in R['cx']}) & set(COR) if R else set(COR)
    esc = html.escape
    modelo = open(os.path.join(AQUI, 'modelo.html'), encoding='utf-8').read()
    titulo = cfg.get('titulo') or f'Pendências {cfg["escola"].replace("ETIB ", "")}'
    pag = (modelo.replace('__TITULO__', esc(titulo))
           .replace('__H1__', esc(cfg.get('h1') or f'Pendências da compatibilização: {cfg["escola"]}'))
           .replace('__SUBTITULO__', esc(cfg.get('subtitulo') or f'Redes externas da implantação (da face das paredes para fora), modelo e pranchas de {cfg.get("data", "")}. '
                                         'As fichas de "Precisa de decisão" esperam a sua resposta; as de "Aplicado" já estão no modelo e nas pranchas e podem ser revertidas.'))
           .replace('__SELO__', '<br>'.join(('<b>' + esc(x) + '</b>') if i == 0 else esc(x) for i, x in enumerate(
               cfg.get('selo') or ['Contrato 24-049', 'Implantação · redes externas', f'Modelo e pranchas de {cfg.get("data", "")}', 'Documento interno'])))
           .replace('__LEGENDA__', esc(legenda(discs)))
           .replace('__DADOS__', json.dumps(dados, ensure_ascii=False).replace('</', '<\\/'))
           .replace('__IMAGENS__', json.dumps(IMG)))
    fn = os.path.join(saida, 'index.html'); open(fn, 'w', encoding='utf-8').write(pag)
    ach, n, tam = conferir(F, pag, IMG, faltas, a.sem_recortes)
    ver = 'APROVADA' if not any(x[1] == 'PENDENCIA' for x in ach) else 'COM PENDÊNCIAS'
    linhas = [f'# Conferência da página de pendências: {cfg["escola"]} ({datetime.datetime.now():%d/%m/%Y %H:%M})', '',
              f'**{ver}** (checklist F). {len(F)} fichas: {n["decisao"]} precisam de decisão, {n["aplicado"]} aplicadas; '
              f'{len(IMG)} imagens embutidas; página com {tam / 2**20:.1f} MB.', '']
    linhas += [f'- {it} {nv}: {tx}' for it, nv, tx in ach] or ['- F1 abre no celular (imagens embutidas), F2 dois blocos, F3 recorte com códigos, 3D, planta e campos: ok']
    linhas += ['', 'Publicar `index.html` com capabilities `{db: {}, user: {}, assets: {}}`; as decisões ficam na coleção `decisoes` (docs d01, d02…).']
    open(os.path.join(saida, 'CONFERENCIA_F.md'), 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    print('\n'.join(linhas[2:])); print(fn)


if __name__ == '__main__':
    main()
