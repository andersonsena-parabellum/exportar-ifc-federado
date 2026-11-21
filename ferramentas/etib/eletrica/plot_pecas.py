import sys,json,math
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/eletrica'); from ld import load,pts
tag=sys.argv[1]; win=[float(v) for v in sys.argv[2].split(',')] if len(sys.argv)>2 else [-40,110,-118,70]
N=json.load(open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/pecas_{tag}.json'))
X0,X1,Y0,Y1=win; S=min(2600/(X1-X0),2600/(Y1-Y0))
F=ImageFont.truetype('arial.ttf',max(11,int(S*0.55))); FB=ImageFont.truetype('arialbd.ttf',24)
P=lambda p:((p[0]-X0)*S,(Y1-p[1])*S+60)
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)+60),'white'); d=ImageDraw.Draw(img)
L=lambda p:(p[0]-561500.0,p[1]-8658000.0)
for r in load('SIT2'):
    if r[0] in('LINE','LWPOLYLINE') and not r[1].startswith(('TOP','MB_','PB_','T-HM','GER','_TG')):
        q=[P(L(p)) for p in pts(r[3])]
        if len(q)>=2: d.line(q,fill=(220,220,220),width=1)
cor={'rótulo':(0,140,0),'herdado do mesmo eletroduto':(0,90,220),'nota do projeto (não cotado)':(230,0,0),'herdado pela caixa (continuidade presumida)':(240,140,0)}
for i,p in enumerate(N['pieces']):
    c=cor[p['rot']['origem']]; d.line([P(q) for q in p['pts']],fill=c,width=3)
    m=p['pts'][len(p['pts'])//2]; d.text((P(m)[0]+3,P(m)[1]+2),f"{i}:{p['pol']}",fill=c,font=F)
for b in N['boxes']:
    q=P(b['c']); h=S*0.4; d.rectangle([q[0]-h,q[1]-h,q[0]+h,q[1]+h],outline=(0,0,0),width=2)
d.text((10,10),f"{tag} {N['rede']} — verde: Ø do rótulo | azul: herdado | laranja: herdado pela caixa | vermelho: sem rótulo (Ø da nota) | quadrado: caixa",fill='black',font=FB)
img.save(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/png/pecas_{tag}.png'); print('ok')
