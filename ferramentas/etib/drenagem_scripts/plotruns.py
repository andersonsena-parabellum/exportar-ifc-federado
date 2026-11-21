import sys,pickle,math; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
from plotdrn import plot
E,segs,mlines,arrows,P=pickle.load(open(CACHE,'rb'))
R,nomatch=pickle.load(open('D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/runs.pkl','rb'))
def colr(d):
    return (0,0,0) if d<0.06 else ((0,150,0) if d<0.09 else ((0,0,255) if d<0.13 else ((255,0,255) if d<0.17 else (255,120,0))))
def extra(dr,T,s):
    for m in mlines: dr.line([T(p) for p in m],fill=(120,120,120),width=1)
    for r in R:
        dr.line([T(r['p0']),T(r['p1'])],fill=colr(r['d']),width=2)
    for k in nomatch:
        a,b=arrows[k]; X,Y=T(((a[0]+b[0])/2,(a[1]+b[1])/2)); dr.ellipse([X-4,Y-4,X+4,Y+4],outline=(255,0,0),width=2)
if __name__=='__main__':
    box=[float(v) for v in sys.argv[1].split(',')]
    plot(E,box,sys.argv[2],int(sys.argv[3]),layers=['AP-Condutos'],extra=extra)
