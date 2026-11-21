import json,sys,math
from PIL import Image,ImageDraw,ImageFont
d=json.load(open('in_geom.json',encoding='utf-8'))
box=[float(v) for v in sys.argv[1].split(',')]; W=int(sys.argv[3])
s=W/(box[1]-box[0]); Hh=int((box[3]-box[2])*s)
im=Image.new('RGB',(W,Hh),'white'); dr=ImageDraw.Draw(im)
try: f=ImageFont.truetype('arial.ttf',12)
except: f=None
T=lambda p:((p[0]-box[0])*s,(box[3]-p[1])*s)
for x in d:
    if x['t']=='B' or x['l'].startswith('HI-Condutos')==False: continue
    dr.line([T(p) for p in x['pts']],fill=(255,190,190),width=2)
cols={'*U21':(200,0,200),'*U45':(0,160,0),'24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05':(0,0,0)}
for i,x in enumerate(d):
    if x['t']=='B' or not x['l'].startswith('0. F_PCI - Det'): continue
    c=cols.get(x['in'],(255,120,0))
    dr.line([T(p) for p in x['pts']],fill=c,width=2)
for x in d:
    if x['l'].startswith('0. F_CAIXA') and x['t']!='B':
        dr.line([T(p) for p in x['pts']],fill=(0,0,255),width=1)
    if x['t']=='B' and x['l'].startswith('0. F_CAIXA'):
        X,Y=T(x['p']); dr.text((X+4,Y+4),'CX',fill=(0,0,255),font=f)
for gx in range(int(box[0]//5)*5,int(box[1])+1,5):
    X,_=T((gx,0)); dr.line([(X,0),(X,Hh)],fill=(238,238,238)); dr.text((X+2,2),str(gx),fill=(120,120,120))
for gy in range(int(box[2]//5)*5,int(box[3])+1,5):
    _,Y=T((0,gy)); dr.line([(0,Y),(W,Y)],fill=(238,238,238)); dr.text((2,Y+2),str(gy),fill=(120,120,120))
im.save(sys.argv[2])
