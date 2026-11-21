"""Conferência: toda ponta 'caixa' tem de estar na face da caixa; pontas soltas perto de caixa da mesma rede."""
import json, math, collections
from shapely.geometry import Polygon, Point
BX={}
for t in ['EL1','EL2','CF1','CF2']:
    for b in json.load(open(f'work/modelo_{t}.json'))['boxes']:
        h=b['dim'][0]/200; a=b['ang']; cx,cy=b['c']
        BX[b['id']]=Polygon([(cx+h*(math.cos(a)*u-math.sin(a)*v),cy+h*(math.sin(a)*u+math.cos(a)*v)) for u,v in ((-1,-1),(1,-1),(1,1),(-1,1))])
st=collections.Counter(); ex=[]
for t in ['EL1','EL2','CF1','CF2']:
    for c in json.load(open(f'work/modelo_{t}.json'))['conduits']:
        for e,P in ((c['ini'],c['segs'][0]['a']),(c['fim'],c['segs'][-1]['b'])):
            p=Point(P[0],P[1])
            if e.startswith('caixa'):
                d=BX[e.split()[1]].exterior.distance(p); st[(t,'na face' if d<0.01 else 'FORA DA FACE')]+=1
                if d>=0.01: ex.append((c['trecho'],e,round(d,3),c['trecho'].endswith(('/1','/2'))))
            elif e=='ponta':
                dn,idn=min((pg.exterior.distance(p) if not pg.contains(p) else 0,i) for i,pg in BX.items() if i.startswith(t))
                st[(t,'ponta solta, caixa da rede a <1,5 m' if dn<1.5 else 'ponta solta longe de caixa')]+=1
                if dn<1.5: ex.append((c['trecho'],'ponta perto de '+idn,round(dn,2)))
for k,v in sorted(st.items()): print(k,v)
for x in ex: print(x)
