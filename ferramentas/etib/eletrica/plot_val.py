import sys,json,math
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/eletrica'); from ld import load,pts
tag=sys.argv[1]
N=json.load(open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/cotas_{tag}.json'))
X0,X1,Y0,Y1=-40,112,-120,72; S=15
F=ImageFont.truetype('arial.ttf',15); FB=ImageFont.truetype('arialbd.ttf',30); FM=ImageFont.truetype('arial.ttf',22)
P=lambda p:((p[0]-X0)*S,(Y1-p[1])*S+120)
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)+120),'white'); d=ImageDraw.Draw(img)
L=lambda p:(p[0]-561500.0,p[1]-8658000.0)
for r in load('SIT2'):
    if r[0] in('LINE','LWPOLYLINE') and not r[1].startswith(('TOP','MB_','PB_','T-HM','GER','_TG')):
        q=[P(L(p)) for p in pts(r[3])]
        if len(q)>=2: d.line(q,fill=(215,215,215),width=1)
COR={'3/4':(150,150,150),'1':(0,160,220),'1.1/4':(0,90,220),'1 1/4':(0,90,220),'1.1/2':(0,160,90),'1 1/2':(0,160,90),'2':(230,150,0),'3':(220,60,0),'4':(170,0,150),'6':(120,0,0)}
for i,p in enumerate(N['pieces']):
    c=COR.get(p['pol'],(0,0,0)); w=4 if p['rot']['origem']!='nota do projeto (não cotado)' else 2
    for l in p['legs']: d.line([P(l['a']),P(l['b'])],fill=c,width=w)
    m=p['pts'][len(p['pts'])//2]; d.text((P(m)[0]+4,P(m)[1]+2),f"{i:03d}",fill=c,font=F)
for j,b in enumerate(N['boxes']):
    q=P(b['c']); h=S*0.45; d.rectangle([q[0]-h,q[1]-h,q[0]+h,q[1]+h],outline=(0,0,0),width=2)
d.text((20,15),f"{N['rede']} — fase 2: rede extraída com Ø e cotas (topo {'0,70 m / 1,00 m veículos' if tag.startswith('EL') else '0,60 m'} abaixo do terreno as built)",fill='black',font=FB)
x=20
used=sorted({p['pol'] for p in N['pieces']},key=lambda s:eval(s.replace(' ','+').replace('.1/','+1/')) if s else 0)
for pol in used:
    c=COR.get(pol,(0,0,0)); d.line([x,85,x+40,85],fill=c,width=6); d.text((x+48,72),f'Ø{pol}"',fill='black',font=FM); x+=150
d.text((x+20,72),'linha fina = Ø pela nota (não cotado) | □ caixa | nº = trecho no CSV',fill='black',font=FM)
img.save(f'D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase2_{tag}_validacao_2026-10-15.png'); print('ok',tag)
