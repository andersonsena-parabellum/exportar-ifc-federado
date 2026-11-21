"""Plota o DWG (camadas AP) numa janela, sem a rede extraída. Uso: python plotdwg.py x0,x1,y0,y1 saida.png [W]"""
import sys; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
import pickle,math
from PIL import Image,ImageDraw,ImageFont
from drn_geom import CACHE
E,segs,ml,arr,P=pickle.load(open(CACHE,'rb'))
L=lambda p:(p[0]-561500,p[1]-8658000)
COL={'AP-Condutos':(0,60,230),'AP-Sentido conduto':(255,150,0),'AP-Indicação coluna':(200,0,200),'Simbolos':(220,0,0),'AP-Caixa de alvenaria':(220,0,0),'AP-Conexões':(0,170,170),'AP-Textos conduto':(0,130,0),'TQ-Textos conduto':(120,80,0)}
def plot(box,fn,W=2400):
    x0,x1,y0,y1=box; s=W/(x1-x0); H=int((y1-y0)*s)
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im); T=lambda p:((p[0]-x0)*s,(y1-p[1])*s)
    f=ImageFont.truetype('arial.ttf',13)
    for e in E:
        c=COL.get(e[1])
        if not c: continue
        if e[0] in('LINE','LWPOLYLINE'): d.line([T(L(q)) for q in e[3]],fill=c,width=1 if e[1]!='AP-Sentido conduto' else 2)
        elif e[0]=='CIRCLE':
            X,Y=T(L(e[3])); r=(e[4] if isinstance(e[4],(int,float)) else 0.1)*s; d.ellipse([X-r,Y-r,X+r,Y+r],outline=c)
        elif e[0]=='MTEXT':
            p=L(e[3])
            if x0<p[0]<x1 and y0<p[1]<y1: d.text(T(p),e[5][:16],fill=c,font=f)
    im.save(fn)
if __name__=='__main__':
    plot([float(v) for v in sys.argv[1].split(',')],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 2400)
