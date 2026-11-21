import json, math, sys
from PIL import Image, ImageDraw, ImageFont
def zoom(X0,Y0,X1,Y1,S,arq):
    img=Image.new('RGB',(int((X1-X0)*S),int((Y1-Y0)*S)),'white'); d=ImageDraw.Draw(img)
    f=lambda p:((p[0]-X0)*S,(Y1-p[1])*S); fn=ImageFont.truetype('arial.ttf',13)
    COR={'EL1':(220,0,0),'EL2':(230,150,0),'CF1':(150,0,150),'CF2':(0,0,220)}
    for t,cor in COR.items():
        M=json.load(open(f'work/modelo_{t}.json'))
        for b in M['boxes']:
            h=b['dim'][0]/200; a=b['ang']; cx,cy=b['c']
            P=[(cx+h*(math.cos(a)*u-math.sin(a)*v),cy+h*(math.sin(a)*u+math.cos(a)*v)) for u,v in ((-1,-1),(1,-1),(1,1),(-1,1))]
            d.polygon([f(p) for p in P],outline=(0,0,0)); d.text(f((cx-h,cy+h+0.25)),b['id'],fill=cor,font=fn)
        for c in M['conduits']:
            for s in c['segs']:
                w=max(1,int(c['de_mm']/1000*S)); d.line([f(s['a']),f(s['b'])],fill=cor,width=w)
    img.save(arq)
zoom(2,-12,18,0,60,'png/zoom_cx_a.png'); zoom(10,-60,22,-45,60,'png/zoom_cx_b.png'); print('ok')
