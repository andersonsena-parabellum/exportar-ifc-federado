# pares (pressurizada, caixa de DRE/ESG) que sobraram críticos na rodada: contorno curto na próxima (contornar_extra.json)
import csv, json, os, sys
OUT = r'D:\Projeto Modelagem\ETIB-JANDAIRA\RELATORIOS\PRECLASH_R02'
f = os.path.join(OUT, 'JAN_preclash_AD_conflitos_depois.csv')
fn = os.path.join(OUT, 'contornar_extra.json')
atual = {tuple(x) for x in json.load(open(fn, encoding='utf-8')) if not x[0].startswith('CX-')} if os.path.exists(fn) else set()   # tubo (A) × caixa (B)
novos = set()
for r in csv.DictReader(open(f, encoding='utf-8-sig'), delimiter=';'):
    if r['gravidade'] != 'CRÍTICA' or r['tipo'] != 'tubo×caixa': continue
    if r['disc_A'] in ('ELE', 'SDAI', 'AF', 'HID') and r['disc_B'] in ('DRE', 'ESG', 'ELE', 'SDAI', 'AF') and r['disc_A'] != r['disc_B']             and not r['trecho_B'].startswith('ELE_') and 'Poste' not in r['trecho_B']: novos.add((r['trecho_A'], r['trecho_B']))
tudo = sorted(atual | novos)
json.dump(tudo, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('novos', sorted(novos - atual), '| total', len(tudo))
