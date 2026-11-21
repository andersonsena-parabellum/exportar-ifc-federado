import pymupdf, json, numpy as np, math
p=pymupdf.open(r'D:/Projeto Modelagem/ETIB-ALAGOINHAS/4 - IMPLANTAÇÃO-20261008T151806Z-1-001/4 - IMPLANTAÇÃO/14 - COMBATE A INCÊNDIO/24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05.pdf')[0]
# âncoras (PDF pt -> modelo m)
A=np.array([[473.8,-1814.1],[2149.2,-804.8]]); B=np.array([[-19.67,-76.25],[98.2,-4.85]])
va=A[1]-A[0]; vb=B[1]-B[0]
s=np.linalg.norm(vb)/np.linalg.norm(va); th=math.atan2(vb[1],vb[0])-math.atan2(va[1],va[0])
R=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]]); t=B[0]-s*R@A[0]
print('escala %.5f m/pt (1:200 = 0.07056) rot %.2f°'%(s,math.degrees(th)))
f=lambda x,y: s*R@np.array([x,-y])+t
d=json.load(open('in_geom.json',encoding='utf-8'))
NUM=[x['p'][:2] for x in d if x['t']=='B' and x['n']=='NUM' and x['p'][0]<110]
print('NUM no desenho',len(NUM))
nums=[]
for b in p.get_text('dict')['blocks']:
    for l in b.get('lines',[]):
        for sp in l['spans']:
            tx=sp['text'].strip()
            if tx.isdigit() and 1<=int(tx)<=40 and sp['bbox'][0]<2300 and sp['bbox'][1]<2200:
                x0,y0,x1,y1=sp['bbox']; c=sp['color']; nums.append((int(tx),(x0+x1)/2,(y0+y1)/2,sp['size'],c))
print('números no PDF (planta)',len(nums))
used=set(); out=[]
for n,x,y,sz,c in nums:
    m=f(x,y); dd=[np.linalg.norm(np.array(q)-m) for q in NUM]; k=int(np.argmin(dd))
    out.append((n,round(x),round(y),round(sz,1),hex(c),k,round(dd[k],2),[round(v,2) for v in NUM[k]]))
for o in sorted(out,key=lambda z:z[6]): print(o)
