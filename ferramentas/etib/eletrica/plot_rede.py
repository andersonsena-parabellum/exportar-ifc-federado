import sys,json,math,re; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
from PIL import Image,ImageDraw,ImageFont
from ld import load,pts
F=ImageFont.truetype('arial.ttf',14); FB=ImageFont.truetype('arialbd.ttf',22)
tag=sys.argv[1]; X=json.load(open(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/rede_{tag}.json'))
X0,X1,Y0,Y1=-110,125,-125,85; S=10
P=lambda p:((p[0]-X0)*S,(Y1-p[1])*S)
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)),'white'); d=ImageDraw.Draw(img)
L=lambda p:(p[0]-561500.0,p[1]-8658000.0)
for r in load('SIT2'):
    if r[0] in('LINE','LWPOLYLINE') and not r[1].startswith(('TOP','MB_','PB_','T-HM','GER','_TG')):
        q=[P(L(p)) for p in pts(r[3])]
        if len(q)>=2: d.line(q,fill=(215,215,215),width=1)
for i,r in enumerate(X['runs']):
    d.line([P(p) for p in r['pts']],fill=(0,120,0),width=3)
    m=r['pts'][len(r['pts'])//2]; d.text((P(m)[0]+4,P(m)[1]+2),str(i),fill=(0,90,0),font=F)
    for e in (r['pts'][0],r['pts'][-1]): d.ellipse([P(e)[0]-3,P(e)[1]-3,P(e)[0]+3,P(e)[1]+3],fill=(255,0,0))
for b in X['boxes']:
    c=P(b['c']); d.rectangle([c[0]-5,c[1]-5,c[0]+5,c[1]+5],outline=(0,0,255),width=2)
for t in X['textos']:
    if re.search(r'(?i)cx',t['t']): c=P(t['p']); d.text(c,t['t'][:12],fill=(150,0,150),font=F)
d.text((20,20),f"{tag}: verde = eletroduto (nº do trecho), vermelho = ponta, azul = caixa detectada, roxo = texto Cx",fill='black',font=FB)
img.save(f'D:/Projeto Modelagem/FERRAMENTAS/eletrica/png/rede_{tag}.png'); print('ok',tag)
