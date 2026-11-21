import sys,pickle,math,collections,re; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts')
from drn_geom import *
E,segs,mlines,arrows,P=pickle.load(open(CACHE,'rb'))
R,nomatch=pickle.load(open('D:/Projeto Modelagem/FERRAMENTAS/drenagem_scripts/work/runs.pkl','rb'))
def labels():
    T=[e for e in E if e[0]=='MTEXT' and e[1] in('AP-Textos conduto','AF-Textos conduto')]
    mats=[t for t in T if re.fullmatch(r'PVCR?|PVC-V|PVC-DR|PVCR?-?\w*',t[5]) and not re.search(r'\d',t[5])]
    sizes=[t for t in T if re.fullmatch(r'\d+ ?mm',t[5])]
    slopes=[t for t in T if re.fullmatch(r'i ?= ?[\d.,]+ ?%?',t[5])]
    out=[]
    used_s=set();used_i=set()
    for m in mats:
        def best(lst,used):
            b=None
            for k,t in enumerate(lst):
                da=abs(t[4]-m[4]); da=min(da,2*math.pi-da)
                if da>0.02: continue
                d=math.dist(t[3],m[3])
                if d<3.2 and (b is None or d<b[0]): b=(d,k)
            return b
        bs=best(sizes,used_s); bi=best(slopes,used_i)
        if not bs: continue
        size=int(re.match(r'\d+',sizes[bs[1]][5]).group())
        slope=slopes[bi[1]][5] if bi else None
        out.append({'mat':m[5],'size':size,'slope':slope,'pos':m[3],'rot':m[4]})
    # tamanhos sem material (so "100 mm"): rotulo de continuacao
    return out,len(mats),len(sizes),len(slopes)
if __name__=='__main__':
    L,nm,ns,ni=labels(); print(len(L),nm,ns,ni)
    print(collections.Counter((l['mat'],l['size']) for l in L))
