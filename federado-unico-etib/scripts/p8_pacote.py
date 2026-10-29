# -*- coding: utf-8 -*-
"""Passo 8 — pacote de envio: envio/ETIB-<ESCOLA>-FEDERADO-UNICO_<data>_<REV>/ com 03_IFC, 04_PREVIA e LEIA-ME.txt, mais o .zip.
O LEIA-ME sai da configuração ("leia_me": o que mudou, valores adotados, o que não entra) e da conferência do passo 6.
Só roda com a conferência APROVADA (o arquivo <ifc>.conferencia.txt termina em APROVADO).
Uso: python p8_pacote.py escola.json R00 pasta_das_previas"""
import os, sys, shutil, datetime, zipfile, re, ifcopenshell
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import etib_fed as ef

def main(cfg, REV, previas):
    sig = cfg['sigla']; fn = os.path.join(ef.pasta(cfg, 'saida'), f'{sig}_FEDERADO-UNICO_{REV}.ifc')
    conf = open(fn + '.conferencia.txt', encoding='utf-8').read()
    if 'RESULTADO: APROVADO' not in conf: sys.exit('conferência não está APROVADA: rode o p6_conferir.py e corrija')
    png = [p for p in os.listdir(previas) if p.endswith('.png')] if os.path.isdir(previas) else []
    if not any('_planta' in p for p in png) or not any('_3d_geral' in p for p in png): sys.exit('faltam prévias (planta e 3d_geral): rode o p7_previas.py')
    hoje = datetime.date.today().isoformat(); nome = f"ETIB-{cfg['pasta_envio']}-FEDERADO-UNICO_{hoje}_{REV}"
    E = ef.pasta(cfg, 'envio', nome); os.makedirs(os.path.join(E, '03_IFC'), exist_ok=True); os.makedirs(os.path.join(E, '04_PREVIA'), exist_ok=True)
    shutil.copy2(fn, os.path.join(E, '03_IFC'))
    for p in sorted(os.listdir(previas)):
        if p.endswith('.png'): shutil.copy2(os.path.join(previas, p), os.path.join(E, '04_PREVIA', p))
    ed = re.findall(r'^   (.+?) (\d+)$', conf.split('edificações:')[1].split('elementos sem edificação')[0], re.M)
    L = cfg.get('leia_me', {}); g = cfg['georref']
    linhas = [f"ETIB {cfg['escola'].upper()} — MODELO IFC FEDERADO ÚNICO", f"Revisão {REV} — {datetime.date.today():%d/%m/%Y}" + (f" ({L['substitui']})" if L.get('substitui') else ''), '',
              'CONTEÚDO',
              f'  03_IFC/{os.path.basename(fn)}   um só arquivo IFC4 ({os.path.getsize(fn) / 1e6:.0f} MB) com a escola inteira: terreno, urbanização,',
              '      redes externas, estrutura e arquitetura dos módulos.',
              '  04_PREVIA   planta e vistas 3D (só para conferência).', '']
    if L.get('mudou'): linhas += ['O QUE MUDOU NESTA REVISÃO'] + [f'  - {x}' for x in L['mudou']] + ['']
    linhas += ['ORGANIZAÇÃO DO MODELO (IfcProject > IfcSite > IfcBuilding)', f"  Site \"ETIB {cfg['escola']}\" com o terreno e {len(ed)} edificações:"]
    linhas += [f"    {n}  ({f'{int(k):,}'.replace(',', '.')} elementos)" for n, k in ed]
    linhas += ['  Cada elemento traz o conjunto de propriedades Dados_ETIB (disciplina, sistema, modulo e origem; nas redes também',
               '  material, diâmetro e cotas). As redes estão agrupadas por sistema (IfcDistributionSystem).', '', 'FONTES E VALORES ADOTADOS']
    linhas += [f"  {k}: {m.get('origem', m['arquivo'])}" for k, m in cfg['modulos'].items()]
    linhas += [f'  {x}' for x in L.get('adotados', [])] + ['']
    if L.get('nao_entra'): linhas += ['NÃO ENTRA'] + [f'  {x}' for x in L['nao_entra']] + ['']
    linhas += ['COORDENADAS', f"  {g.get('nome', g['epsg'])} ({g['epsg']}), cota absoluta. Origem do arquivo: E {g['e0']}  N {g['n0']}.",
               '  É a mesma origem dos IFC por disciplina já entregues da escola.', '',
               'ABRIR NO REVIT', '  Abrir IFC; na vista 3D usar a Fase 3; VV > Local > desmarcar pontos de levantamento e base; depois ZF.',
               '  Estilo visual "Sombreado" (em "Linhas ocultas" o Revit mostra só os contornos).',
               '  Se o modelo já estiver vinculado, use Gerenciar vínculos > Recarregar de... e aponte para a revisão nova.', '',
               f'CONFERÊNCIA FEITA ({datetime.date.today():%d/%m/%Y})',
               '  Validação do esquema IFC4 sem erros; um site; nenhum elemento sem edificação, sem geometria ou com GUID repetido;',
               '  nenhuma propriedade de trabalho; todos os elementos com Dados_ETIB.']
    open(os.path.join(E, 'LEIA-ME.txt'), 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    z = E + '.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for r, _, fs in os.walk(E):
            for x in fs: zf.write(os.path.join(r, x), os.path.relpath(os.path.join(r, x), os.path.dirname(E)))
    print('pacote', E, '\nzip', z, round(os.path.getsize(z) / 1e6, 1), 'MB')

if __name__ == '__main__':
    main(ef.carregar(sys.argv[1]), sys.argv[2], sys.argv[3])
