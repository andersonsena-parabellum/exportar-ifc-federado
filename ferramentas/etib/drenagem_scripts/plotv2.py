import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,math
from PIL import Image,ImageDraw,ImageFont
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
D=pickle.load(open('work/v2_net.pkl','rb'))
L=lambda p:(p[0]-561500,p[1]-8658000)
def plot(box,fn,W=2400,labels=True):
    x0,x1,y0,y1=box; s=W/(x1-x0); H=int((y1-y0)*s)
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im); T=lambda p:((p[0]-x0)*s,(y1-p[1])*s)
    f=ImageFont.truetype('arial.ttf',15)
    for e in E:
        if e[1]=='AP-Condutos' and e[0] in('LINE','LWPOLYLINE'): d.line([T(L(q)) for q in e[3]],fill=(190,190,190),width=1)
        if e[1]=='AP-Sentido conduto' and e[0]=='LWPOLYLINE': d.line([T(L(q)) for q in e[3]],fill=(255,170,0),width=3)
        if labels and e[0]=='MTEXT' and e[1] in('AP-Textos conduto','TQ-Textos conduto'):
            p=L(e[3])
            if x0<p[0]<x1 and y0<p[1]<y1: d.text(T(p),e[5][:14],fill=(0,130,0),font=f)
    for e in D['edges']:
        c=(0,80,255) if e.get('bacia') is not None else (255,0,0)
        pu=D['nodes'][e['up']]['p']; pd=D['nodes'][e['dn']]['p']
        d.line([T(e['pa']),T(e['pb'])],fill=c,width=3)
        m=((e['pa'][0]+e['pb'][0])/2,(e['pa'][1]+e['pb'][1])/2); ux,uy=pd[0]-pu[0],pd[1]-pu[1]; n=math.hypot(ux,uy) or 1
        a=T(m); b=T((m[0]+ux/n*0.6,m[1]+uy/n*0.6)); d.line([a,b],fill=(0,0,0),width=2)
    for b in D['boxes']:
        X,Y=T(b['p']); r=b['r']*s; d.rectangle([X-r,Y-r,X+r,Y+r],outline=(200,0,0),width=2)
    im.save(fn)
if __name__=='__main__':
    plot([float(v) for v in sys.argv[1].split(',')],sys.argv[2])
