import re
TYPES=('LINE','LWPOLYLINE','CIRCLE','ARC','MLINE','MTEXT','TEXT','INSERT','HATCH','MULTILEADER')
def load(tag):
    rows=[];cur=None
    for l in open(f'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg/dump_{tag}.tsv',encoding='latin-1'):
        l=l.rstrip('\n')
        p=l.split('\t',3)
        if len(p)==4 and p[0] in TYPES:
            cur=p; rows.append(cur)
        elif cur is not None: cur[3]+=' '+l
    return rows
