import json, math, numpy as np
d=json.load(open('in_geom.json',encoding='utf-8'))
TOP='24-049-ALH-SLJ-ETIB-IMP-PE-IN-001-ING-R05'
S=[x for x in d if x['l'].startswith('0. F_PCI - Det') and x['in']==TOP and x['t'] in 'LP']
polys=[[tuple(q[:2]) for q in x['pts']] for x in S]
polys=[p for p in polys if sum(math.dist(p[i],p[i+1]) for i in range(len(p)-1))>0.3]
print('polilinhas SDAI',len(polys), 'L total %.1f'%sum(sum(math.dist(p[i],p[i+1]) for i in range(len(p)-1)) for p in polys))
# caixas: centro e tamanho a partir da geometria do bloco *U32 (uma instância por caixa)
cxb=[x for x in d if x['t']=='B' and x['l'].startswith('0. F_CAIXA') and x['p'][0]<110]
cxg=[x for x in d if x['l'].startswith('0. F_CAIXA') and x['t']!='B']
boxes=[]
for b in cxb:
    pts=[q for g in cxg for q in g['pts'] if math.dist(q[:2],b['p'][:2])<1.0]
    xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
    c=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2) if pts else tuple(b['p'][:2])
    boxes.append(dict(c=c,r=b['r'],w=max(max(xs)-min(xs),max(ys)-min(ys)) if pts else 0.4))
print('caixas',len(boxes),'tamanhos',sorted(set(round(b['w'],2) for b in boxes)))
NUM=[x['p'][:2] for x in d if x['t']=='B' and x['n']=='NUM' and x['p'][0]<110]
# mapa número -> NUM (do casamento com o PDF)
num_of={(90.19,6.96):4,(81.72,7.52):4,(61.92,4.65):4,(50.71,0.44):5,(45.26,2.23):4,(31.73,0.27):4,(22.07,7.4):11,(29.71,16.46):9,(17.43,-1.8):3,(14.16,-44.17):2,(11.29,-24.38):2,(21.22,-67.75):7,(10.06,-12.75):9,(16.75,-62.0):2,(8.87,-7.69):2,(5.18,-3.58):8,(7.29,3.18):10,(12.46,-69.01):1,(3.56,-75.38):6,(-0.54,-70.9):1}
json.dump({'polys':polys,'boxes':boxes,'num':[[k[0],k[1],v] for k,v in num_of.items()]},open('sdai_raw.json','w'))
for i,p in enumerate(polys): print(i,len(p),[ [round(c,2) for c in v] for v in (p[0],p[-1])],'L=%.1f'%sum(math.dist(p[k],p[k+1]) for k in range(len(p)-1)))
