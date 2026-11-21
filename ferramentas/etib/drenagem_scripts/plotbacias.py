import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,math
from PIL import Image,ImageDraw,ImageFont
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
D=pickle.load(open('work/v2_net.pkl','rb'))
L=lambda p:(p[0]-561500,p[1]-8658000)
COL=[(0,90,255),(230,90,0),(0,160,60),(160,0,200)]
outs=D['outs']; cmap={o:COL[i] for i,o in enumerate(outs)}
def plot(box,fn,W=2600,title=''):
    x0,x1,y0,y1=box; s=W/(x1-x0); H=int((y1-y0)*s)+90
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im); T=lambda p:((p[0]-x0)*s,(y1-p[1])*s+90)
    f=ImageFont.truetype('arialbd.ttf',30); fs=ImageFont.truetype('arial.ttf',16)
    for e in E:
        if e[1]=='AP-Condutos' and e[0] in('LINE','LWPOLYLINE'): d.line([T(L(q)) for q in e[3]],fill=(205,205,205),width=1)
    for e in D['edges']:
        c=cmap.get(e.get('bacia'),(255,0,0)); w=2 if (e['d'] or 0.03)<0.06 else (4 if (e['d'] or 0)<0.17 else 7)
        d.line([T(e['pa']),T(e['pb'])],fill=c,width=w)
        pu=D['nodes'][e['up']]['p']; pd=D['nodes'][e['dn']]['p']
        if e['L']>2.5:
            m=((e['pa'][0]+e['pb'][0])/2,(e['pa'][1]+e['pb'][1])/2); ux,uy=pd[0]-pu[0],pd[1]-pu[1]; n=math.hypot(ux,uy) or 1
            ux,uy=ux/n,uy/n; tip=(m[0]+ux*0.9,m[1]+uy*0.9); l=(m[0]-uy*0.4,m[1]+ux*0.4); r=(m[0]+uy*0.4,m[1]-ux*0.4)
            d.polygon([T(tip),T(l),T(r)],fill=(0,0,0))
    for b in D['boxes']:
        X,Y=T(b['p']); r=max(5,b['r']*s)
        if b['tipo']=='PV': d.ellipse([X-r,Y-r,X+r,Y+r],outline=(200,0,0),width=3)
        else: d.rectangle([X-r,Y-r,X+r,Y+r],outline=(200,0,0),width=3)
    for c in D['cols']:
        X,Y=T(c); d.ellipse([X-6,Y-6,X+6,Y+6],fill=(255,200,0),outline=(0,0,0))
    for o in outs:
        X,Y=T(D['nodes'][o]['p']); d.text((X-60,Y-50),'LANÇAMENTO',fill=cmap[o],font=f)
    d.text((20,15),title,fill='black',font=f)
    im.save(fn)
if __name__=='__main__':
    plot((-30,105,-112,65),'work/p/bacias.png',title='Mapa da rede por bacia (cor = lançamento); seta = sentido; amarelo = prumada AP; vermelho = caixa/PV')
