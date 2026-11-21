import sys,csv,math,re,collections
sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg')
from load_dump import load
OX,OY=561500.0,8658000.0
D='D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg/'
def num(s):
    try: return float(str(s).replace(',','.'))
    except: return None
def rd(fn): return list(csv.DictReader(open(D+fn,encoding='utf-8-sig'),delimiter=';'))
def pipes(prefix):
    out=[]
    for p in rd('hs_pipes.csv'):
        s=p['sistema']
        if not s.startswith(prefix): continue
        out.append(dict(id=p['id'],sis=s,tipo=p['tipo'],dn=num(p['dn_mm']),a=(num(p['x0']),num(p['y0']),num(p['z0'])),b=(num(p['x1']),num(p['y1']),num(p['z1'])),L=num(p['comp_m']),livres=int(p['conectores_livres'])))
    return out
def L(p): return (p[0]-OX,p[1]-OY)
def pts(s):
    return [tuple(map(float,t.split(','))) for t in re.findall(r'-?\d+\.?\d*,-?\d+\.?\d*',s)]
def dseg(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; n=dx*dx+dy*dy
    t=0 if n==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/n))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def txt(r):
    # r[3]: "x,y h=.. rot=.. TEXT"
    m=re.match(r'(-?[\d.]+),(-?[\d.]+) h=([\d.]+) rot=([-\d.]+) (.*)',r[3],re.S)
    if not m: return None
    t=re.sub(r'\\p[a-z0-9,.]+;','',m.group(5)).strip()
    return (float(m.group(1))-OX,float(m.group(2))-OY,float(m.group(4)),t)
