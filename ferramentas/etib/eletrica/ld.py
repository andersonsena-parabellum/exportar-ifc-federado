import re,collections,math
TYPES=('LINE','LWPOLYLINE','CIRCLE','ARC','MLINE','MTEXT','TEXT','INSERT','HATCH','MULTILEADER')
def load(tag):
    rows=[];cur=None
    for l in open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/dump_{tag}.tsv',encoding='latin-1'):
        l=l.rstrip('\n'); p=l.split('\t',3)
        if len(p)==4 and p[0] in TYPES: cur=p; rows.append(cur)
        elif cur: cur[3]+=' '+l
    return rows
def pts(s): return [tuple(map(float,t)) for t in re.findall(r'(-?\d+\.?\d*),(-?\d+\.?\d*)',s)]
