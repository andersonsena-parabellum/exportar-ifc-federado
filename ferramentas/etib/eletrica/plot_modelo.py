"""Imagem de conferência da fase 4 (antes do Revit): blocos, eletrodutos cortados, caixas orientadas, pontas."""
import json, math
from PIL import Image, ImageDraw, ImageFont
W='D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
X0,Y0,X1,Y1,S=-40,-120,115,75,8
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)),'white'); d=ImageDraw.Draw(img)
f=lambda p:((p[0]-X0)*S,(Y1-p[1])*S)
fn=ImageFont.truetype('arial.ttf',13); fb=ImageFont.truetype('arialbd.ttf',22)
for o in json.load(open(W+'blocos.json')):
    d.polygon([f(p) for p in o['coords']],fill=(232,232,232),outline=(90,90,90))
    xs=[p[0] for p in o['coords']]; ys=[p[1] for p in o['coords']]
    d.text(f((sum(xs)/len(xs)-3,sum(ys)/len(ys)+1)),o['bloco'],fill=(60,60,60),font=fb)
COR={'EL1':(220,0,0),'EL2':(230,150,0),'CF1':(0,140,0),'CF2':(0,0,220)}
pontas=[]
for t,cor in COR.items():
    M=json.load(open(W+f'modelo_{t}.json'))
    for c in M['conduits']:
        for s in c['segs']: d.line([f(s['a']),f(s['b'])],fill=cor,width=2)
        for e,P in ((c['ini'],c['segs'][0]['a']),(c['fim'],c['segs'][-1]['b'])):
            x,y=f(P)
            if e.startswith('face'): d.line([x-6,y-6,x+6,y+6],fill=(0,0,0),width=3); d.line([x-6,y+6,x+6,y-6],fill=(0,0,0),width=3)
            elif e=='ponta': d.ellipse([x-5,y-5,x+5,y+5],outline=cor,width=2); d.text((x+6,y-8),c['trecho'],fill=cor,font=fn); pontas.append((t,c['trecho'],round(P[0],1),round(P[1],1)))
    for b in M['boxes']:
        h=b['dim'][0]/200; a=b['ang']; cx,cy=b['c']
        P=[(cx+h*(math.cos(a)*u-math.sin(a)*v),cy+h*(math.sin(a)*u+math.cos(a)*v)) for u,v in ((-1,-1),(1,-1),(1,1),(-1,1))]
        d.polygon([f(p) for p in P],outline=cor,fill=(255,255,255) if not b['obs'] else (255,255,0))
d.text((10,10),'ELE fase 4 - rede para o Revit: X = corte na face do bloco | o = ponta sem caixa | caixa amarela = sem eletroduto ligado',fill=(0,0,0),font=fn)
y=30
for t,cor in COR.items(): d.text((10,y),t,fill=cor,font=fb); y+=24
img.save('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase4_rede_para_revit_2026-10-15.png')
print(len(pontas),'pontas sem caixa:',pontas)
