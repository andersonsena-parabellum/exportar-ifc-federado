import json,sys,math
from PIL import Image,ImageDraw,ImageFont
d=json.load(open('in_geom.json',encoding='utf-8'))
H=[x for x in d if x['l'].startswith('HI-Condutos') and x['in'].startswith('24-049')]
box=[float(v) for v in sys.argv[1].split(',')]; W=int(sys.argv[3])
s=W/(box[1]-box[0]); Hh=int((box[3]-box[2])*s)
im=Image.new('RGB',(W,Hh),'white'); dr=ImageDraw.Draw(im)
try: f=ImageFont.truetype('arial.ttf',13)
except: f=None
T=lambda p:((p[0]-box[0])*s,(box[3]-p[1])*s)
for x in d:
    if x['t']=='B' or not x['in'].startswith('24-049'): continue
    if x['l'].startswith('0. F_PCI - Det'): dr.line([T(p) for p in x['pts']],fill=(230,150,230),width=1)
for i,x in enumerate(H):
    c=(0,120,255) if x['t']=='A' else (220,0,0)
    dr.line([T(p) for p in x['pts']],fill=c,width=3)
    if x['t']!='A':
        L=sum(math.dist(x['pts'][k][:2],x['pts'][k+1][:2]) for k in range(len(x['pts'])-1))
        if L>1:
            for p in x['pts']: X,Y=T(p); dr.ellipse([X-3,Y-3,X+3,Y+3],outline=(0,0,0))
            m=x['pts'][len(x['pts'])//2]; X,Y=T(m); dr.text((X+5,Y+5),f'#{i}',fill=(0,0,0),font=f)
for gx in range(int(box[0]//5)*5,int(box[1])+1,5):
    X,_=T((gx,0)); dr.line([(X,0),(X,Hh)],fill=(238,238,238)); dr.text((X+2,2),str(gx),fill=(120,120,120))
for gy in range(int(box[2]//5)*5,int(box[3])+1,5):
    _,Y=T((0,gy)); dr.line([(0,Y),(W,Y)],fill=(238,238,238)); dr.text((2,Y+2),str(gy),fill=(120,120,120))
im.save(sys.argv[2])
