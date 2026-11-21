# -*- coding: utf-8 -*-
"""Gera o pranchas.json lido pela aba "Pranchas" do visualizador (artifact Pré-compatibilização ETIB), a partir da lista
de folhas (originais.py) e dos IDs do Google Drive (drive_ids.py, pasta ETIB_PRANCHAS_CDE).
Situação: 'Original' (sem revisão), 'Em revisão' (vale a original até a nova versão), 'Modificada' (MODIFICADAS abaixo).
Uso: python -X utf8 pranchas_json.py [saida.json]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from originais import L
from drive_ids import IDS, PASTAS, PASTA, INDICE

SIGLA = {'ETIB-ALAGOINHAS': 'ALH', 'ETIB-APORA-PROF-AUREA': 'AUR', 'ETIB-CATU': 'CAT', 'ETIB-APORA-ITAMIRA': 'ITA',
         'ETIB-JANDAIRA': 'JAN', 'ETIB-POJUCA': 'PJC', 'ETIB-SATIRO-DIAS': 'SAT', 'ETIB-OLINDINA': 'ONN'}
NOME = {'ETIB-ALAGOINHAS': 'Alagoinhas', 'ETIB-APORA-ITAMIRA': 'Aporá – Itamira', 'ETIB-APORA-PROF-AUREA': 'Aporá – Prof. Áurea',
        'ETIB-CATU': 'Catu', 'ETIB-JANDAIRA': 'Jandaíra', 'ETIB-POJUCA': 'Pojuca', 'ETIB-SATIRO-DIAS': 'Sátiro Dias', 'ETIB-OLINDINA': 'Olindina'}
SUB = {'IMP': 'Implantação', 'BA2': 'Bloco BA2', 'CPS': 'Campo society'}
OBS = {'ETIB-APORA-ITAMIRA': 'Intervenção = campo society + pista. Compatibilização entregue em 24/10/2026: drenagem (DRE-001) redesenhada pela rede executada do campo e elétrica (EL-001) com a alimentação até o QD1 executado. O Drive não traz água fria, esgoto nem incêndio da implantação.',
       'ETIB-APORA-PROF-AUREA': 'Compatibilização entregue em 23/10/2026. A lista mestra da construtora traz na implantação só a drenagem da quadra (folha AF-002), a elétrica e o incêndio.',
       'ETIB-OLINDINA': 'Ampliação do bloco BA5 ligada às redes existentes da escola. Compatibilização entregue em 22/10/2026.',
       'ETIB-POJUCA': 'A implantação do projetista da quadra (PI000) não é desta obra e ficou fora.'}
# folhas já substituídas pela versão revisada: (escola, sub, código da folha) -> {'rev': 'R0x', 'id': '<id do Drive>', 'arquivo': '<nome.pdf>'}
MODIFICADAS = {
    # Jandaíra, 20/10/2026: R03 com o carimbo QG as built (EXECUTIVO_R03_IFC/PDF_QG, jan_cde_r03.py); as R02/R01/R04 foram para _SUPERADAS
    # (a CPS DRE-001 continua R02, sobrescrita no mesmo arquivo do Drive)
    ('ETIB-JANDAIRA', 'IMP', 'AF-001'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-AF-001-HIG-R03.pdf'},
    ('ETIB-JANDAIRA', 'IMP', 'ESG-001'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-ESG-001-HIG-R03.pdf'},
    ('ETIB-JANDAIRA', 'IMP', 'DRE-001'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-DRE-001-DRG-R02.pdf'},
    ('ETIB-JANDAIRA', 'IMP', 'EL-001'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-EL-001-ELG-R03.pdf'},
    ('ETIB-JANDAIRA', 'IMP', 'EL-002'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-EL-002-ELG-R03.pdf'},
    ('ETIB-JANDAIRA', 'IMP', 'IN-001'): {'rev': 'R05', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-IMP-PE-IN-001-ING-R05.pdf'},
    ('ETIB-JANDAIRA', 'CPS', 'DRE-001'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-CPS-PE-DRE-001-DRG-R02.pdf'},
    ('ETIB-JANDAIRA', 'CPS', 'EL-001'): {'rev': 'R03', 'id': '<ID_DRIVE>', 'arquivo': '24-049-JDI-CTO-ETIB-CPS-PE-EL-001-ELG-R03.pdf'},
    # Pojuca, 19/10/2026: piloto do padrão de campo (work/POJUCA/scripts/executivo_campo_pojuca.py + pranchas_campo_pojuca.py)
    ('ETIB-POJUCA', 'IMP', 'AF-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-PJC-CTO-ETIB-IMP-PE-AF-001-AFR-R01.pdf'},
    ('ETIB-POJUCA', 'IMP', 'EL-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-PJC-CTO-ETIB-IMP-PE-EL-001-ELG-R01.pdf'},
    ('ETIB-POJUCA', 'IMP', 'EL-002'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-PJC-CTO-ETIB-IMP-PE-EL-002-ELG-R01.pdf'},
    ('ETIB-POJUCA', 'IMP', 'IC-001'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-PJC-CTO-ETIB-IMP-PE-IC-001-INC-R02.pdf'},
    ('ETIB-POJUCA', 'CPS', 'EL-001'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-PJC-CTO-ETIB-CPS-PE-EL-001-ELG-R02.pdf'},
    # Aporá Prof. Áurea, 23/10/2026: R01 com o carimbo QG as built (aurea/exe/aur_cde.py); a IN-001 não mudou
    ('ETIB-APORA-PROF-AUREA', 'IMP', 'AF-002'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-APR-CTO-ETIB-IMP-PE-AF-002-HIG-R01.pdf'},
    ('ETIB-APORA-PROF-AUREA', 'IMP', 'EL-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-APR-CTO-ETIB-IMP-PE-EL-001-ELG-R01.pdf'},
    # Alagoinhas, 22/10/2026: R03 da compatibilização com o carimbo QG as built (alagoinhas/exe/alh_envio.py); anteriores em _SUPERADAS
    ('ETIB-ALAGOINHAS', 'IMP', 'AGF-001'): {'rev': 'R07', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-AGF-001-R07.pdf'},
    ('ETIB-ALAGOINHAS', 'IMP', 'ESG-001'): {'rev': 'R07', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-ESG-001-HIG-R07.pdf'},
    ('ETIB-ALAGOINHAS', 'IMP', 'DRE-001'): {'rev': 'R05', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-DRE-001-DRG-R05.pdf'},
    ('ETIB-ALAGOINHAS', 'IMP', 'EL-001'): {'rev': 'R08', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-001-ELG-R08.pdf'},
    ('ETIB-ALAGOINHAS', 'IMP', 'EL-002'): {'rev': 'R06', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-EL-002-ELG-R06.pdf'},
    ('ETIB-ALAGOINHAS', 'IMP', 'IN-001'): {'rev': 'R06', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R06.pdf'},
    # Sátiro Dias, 22/10/2026: revisão seguinte com o carimbo QG as built (satiro/exe/sat_cde.py)
    ('ETIB-SATIRO-DIAS', 'IMP', 'AF-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-IMP-PE-AF-001-HIG-R01.pdf'},
    ('ETIB-SATIRO-DIAS', 'IMP', 'ESG-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-IMP-PE-ESG-001-HIG-R01.pdf'},
    ('ETIB-SATIRO-DIAS', 'IMP', 'EL-001'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-IMP-PE-EL-001-ELG-R02.pdf'},
    ('ETIB-SATIRO-DIAS', 'IMP', 'EL-002'): {'rev': 'R02', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-IMP-PE-EL-002-ELG-R02.pdf'},
    ('ETIB-SATIRO-DIAS', 'IMP', 'IN-001'): {'rev': 'R04', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-IMP-PE-IN-001-ING-R04.pdf'},
    ('ETIB-SATIRO-DIAS', 'CPS', 'ELE-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-STK-XXX-ETIB-CPS-PE-ELE-001-ELG-R01.pdf'},
    # Olindina, 22/10/2026: R01 com o carimbo QG as built (olindina/exe/onn_envio.py)
    ('ETIB-OLINDINA', 'IMP', 'ESG-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ONN-CTO-ETIB-IMP-PE-ESG-001-HIG-R01.pdf'},
    ('ETIB-OLINDINA', 'IMP', 'DRE-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ONN-CTO-ETIB-IMP-PE-DRE-001-DRG-R01.pdf'},
    ('ETIB-OLINDINA', 'IMP', 'EL-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-ONN-CTO-ETIB-IMP-PE-EL-001-ELG-R01.pdf'},
    # Aporá Itamira, 23/10/2026: DRE-001 redesenhada pela drenagem executada do campo (itamira/exe/ita_cde.py)
    ('ETIB-APORA-ITAMIRA', 'IMP', 'DRE-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-APR-ITA-ETIB-IMP-PE-DRE-001-DRG-R01.pdf'},
    # Aporá Itamira, 24/10/2026: EL-001 com a alimentação nova (ELE-06) até o QD1 executado (itamira/exe/ita_el_r01.py, ita_cde.py)
    ('ETIB-APORA-ITAMIRA', 'IMP', 'EL-001'): {'rev': 'R01', 'id': '<ID_DRIVE>', 'arquivo': '24-049-APR-ITA-ETIB-IMP-PE-EL-001-ELG-R01.pdf'},
}


def url(i): return f'https://drive.google.com/file/d/{i}/view'
def baixar(i): return f'https://drive.google.com/uc?export=download&id={i}'


esc = {}
for e, s, f, rev, x, m in L:
    nome = os.path.splitext(os.path.basename(x[1] if isinstance(x, tuple) else x))[0]
    i = IDS[nome[len('24-049-'):]]
    item = {'grupo': SUB[s], 'folha': f, 'situacao': 'Em revisão' if m else 'Original', 'rev': rev, 'arquivo': nome + '.pdf',
            'ver': url(i), 'baixar': baixar(i)}
    mod = MODIFICADAS.get((e, s, f.split()[0]))
    if mod:
        item.update(situacao='Modificada', rev=mod['rev'], arquivo=mod['arquivo'], ver=url(mod['id']), baixar=baixar(mod['id']))
    esc.setdefault(e, []).append(item)
saida = {'atualizado': time.strftime('%d/%m/%Y'), 'pasta': f'https://drive.google.com/drive/folders/{PASTA}',
         'indice': url(INDICE),
         'escolas': [{'sigla': SIGLA[e], 'nome': NOME[e], 'pasta': f'https://drive.google.com/drive/folders/{PASTAS[e]}',
                      'obs': OBS.get(e, ''), 'folhas': esc[e]} for e in NOME if e in esc]}
fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pranchas.json')
json.dump(saida, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(fn, sum(len(v) for v in esc.values()), 'folhas')
