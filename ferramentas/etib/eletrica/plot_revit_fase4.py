"""Planta da rede como está no Revit (leitura de volta), com contorno dos blocos, caixas e pontos de sobreposição entre eletrodutos."""
import json, csv
from PIL import Image, ImageDraw, ImageFont
W='D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
X0,Y0,X1,Y1,S=-40,-120,115,75,8
img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)+90),'white'); d=ImageDraw.Draw(img)
f=lambda p:((p[0]-X0)*S,(Y1-p[1])*S+90)
fn=ImageFont.truetype('arial.ttf',14); fb=ImageFont.truetype('arialbd.ttf',20); ft=ImageFont.truetype('arialbd.ttf',18)
for o in json.load(open(W+'blocos.json')):
    d.polygon([f(p) for p in o['coords']],fill=(230,230,230),outline=(100,100,100))
    xs=[p[0] for p in o['coords']]; ys=[p[1] for p in o['coords']]; d.text(f((sum(xs)/len(xs)-3,sum(ys)/len(ys)+1)),o['bloco'],fill=(80,80,80),font=fb)
COR={'EL1':(220,0,0),'EL2':(230,150,0),'CF1':(0,150,0),'CF2':(0,0,220)}
W2={0.0267:2,0.0334:2,0.0422:2,0.0483:3,0.0603:3,0.0889:4,0.1143:4,0.1683:5}
for l in open(W+'revit_leitura_fase4.tsv',encoding='utf-8'):
    r=l.rstrip('\n').split('\t')
    if r[0]=='C':
        de=float(r[5]); wd=2 if de<45 else 3 if de<70 else 4
        d.line([f((float(r[6]),float(r[7]))),f((float(r[9]),float(r[10])))],fill=COR[r[3][:3]],width=wd)
    else:
        x,y=f((float(r[4]),float(r[5]))); d.rectangle([x-4,y-4,x+4,y+4],outline=(0,0,0),fill=(255,255,255))
for r in csv.DictReader(open('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase4_sobreposicoes_internas_2026-10-15.csv',encoding='utf-8-sig'),delimiter=';'):
    x,y=f((float(r['x']),float(r['y']))); d.ellipse([x-7,y-7,x+7,y+7],outline=(200,0,200),width=3)
d.text((10,8),'ELE fase 4 - modelo lido do Revit (MODELAGEM-ELETRICA.rvt, 15/10/2026 16:25)',fill=(0,0,0),font=ft)
d.text((10,32),'449 eletrodutos / 2.772 m  |  88 caixas (quadrado preto)  |  cinza = blocos (corte na face)  |  círculo lilás = sobreposição entre eletrodutos (48)',fill=(0,0,0),font=fn)
x=10
for t,c in COR.items(): d.text((x,56),{'EL1':'EL1 Alimentação BT','EL2':'EL2 Iluminação externa','CF1':'CF1 CFTV','CF2':'CF2 Dados/telefonia'}[t],fill=c,font=ft); x+=260
img.save('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase4_modelo_Revit_2026-10-15.png'); print('ok')
