import sys,pickle,math; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
from plotdrn import plot
W='D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/'
E,segs,mlines,arrows,P=pickle.load(open(CACHE,'rb'))
nodes,edges,boxes,segs3=pickle.load(open(W+'topo.pkl','rb'))
trip,assign,CE,CS=pickle.load(open(W+'cotas.pkl','rb'))
def colr(d):
    if d is None: return (120,120,120)
    return (0,0,0) if d<0.06 else ((0,150,0) if d<0.09 else ((0,0,255) if d<0.13 else ((255,0,255) if d<0.17 else (255,120,0))))
def extra(dr,T,s):
    for e in edges:
        dr.line([T(e['p0']),T(e['p1'])],fill=colr(e['d']),width=3)
        if e['sgn']!=0:
            m=((e['p0'][0]+e['p1'][0])/2,(e['p0'][1]+e['p1'][1])/2); ux,uy=e['dir']; sg=1 if e['sgn']>0 else -1
            a=T(m); b=T((m[0]+ux*sg*0.5,m[1]+uy*sg*0.5)); dr.line([a,b],fill=(255,0,0),width=2)
    for i,n in enumerate(nodes):
        X,Y=T(n['pos']); c={'box':(220,0,0),'jun':(0,170,0),'end':(255,150,0)}[n['kind']]
        r=6 if n['kind']=='box' else 3
        dr.rectangle([X-r,Y-r,X+r,Y+r],outline=c,width=2)
    for t in trip:
        X,Y=T(t['pos']); dr.ellipse([X-5,Y-5,X+5,Y+5],outline=(0,120,255),width=2)
if __name__=='__main__':
    box=[float(v) for v in sys.argv[1].split(',')]
    plot(E,box,sys.argv[2],int(sys.argv[3]),layers=['AP-Condutos'],extra=extra,labels={'TQ-Textos conduto':(0,0,200)})
