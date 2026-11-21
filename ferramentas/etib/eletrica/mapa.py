import sys,math,re,csv; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
from ld import load,pts
from geo import tf
from PIL import Image,ImageDraw,ImageFont
F=ImageFont.truetype('arial.ttf',22); F2=ImageFont.truetype('arial.ttf',13)
X0,X1,Y0,Y1=-110,125,-125,85; S=10
def P(p): return ((p[0]-X0)*S,(Y1-p[1])*S)
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)),'white'); d=ImageDraw.Draw(img)
L=lambda p:(p[0]-561500.0,p[1]-8658000.0)
for r in load('SIT2'):
    if r[0] in('LINE','LWPOLYLINE') and not r[1].startswith(('TOP','MB_','PB_','T-HM','GER','_TG')):
        q=[P(L(p)) for p in pts(r[3])]
        if len(q)>=2: d.line(q,fill=(200,200,200),width=1)
# AF modelada (referência)
for p in csv.DictReader(open('D:/Projeto Modelagem/FERRAMENTAS/auditoria_afesg/hs_pipes.csv',encoding='utf-8-sig'),delimiter=';'):
    if p['sistema'].startswith('Esgoto'):
        a=(float(p['x0'].replace(',','.')),float(p['y0'].replace(',','.'))); b=(float(p['x1'].replace(',','.')),float(p['y1'].replace(',','.')))
        d.line([P(a),P(b)],fill=(150,90,40),width=2)
cores={'EL1':((0,150,0),'EL-001 alimentação BT'),'EL2':((240,130,0),'EL-002 iluminação externa'),'CF1':((0,70,230),'CF-001 CFTV'),'CF2':((210,0,170),'CF-002 dados/telefonia')}
for k,(tag,(c,nome)) in enumerate(cores.items()):
    f=tf(tag)
    for r in load(tag):
        if not r[1].startswith('02. F_ELETRODUTO'): continue
        if r[0] in('LINE','LWPOLYLINE'):
            q=[P(f(p)) for p in pts(r[3])]
            if len(q)>=2: d.line(q,fill=c,width=2)
        elif r[0]=='ARC':
            m=re.match(r'(-?[\d.]+),(-?[\d.]+) r=([\d.]+) a=([-\d.]+),([-\d.]+)',r[3]); cx,cy,rr,a0,a1=map(float,m.groups())
            if a1<a0: a1+=2*math.pi
            d.line([P(f((cx+rr*math.cos(a0+(a1-a0)*i/16),cy+rr*math.sin(a0+(a1-a0)*i/16)))) for i in range(17)],fill=c,width=2)
    d.rectangle([20,20+32*k,50,40+32*k],fill=c); d.text((60,18+32*k),nome,fill='black',font=F)
d.line([20,20+32*4+10,50,20+32*4+10],fill=(150,90,40),width=3); d.text((60,18+32*4),'ESG modelado (referência de posição)',fill='black',font=F)
img.save(sys.argv[1] if len(sys.argv)>1 else 'png/mapa_eletrica_sobre_SIT.png'); print('ok')
