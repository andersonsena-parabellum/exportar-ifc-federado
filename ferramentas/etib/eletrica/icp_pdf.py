"""Refina a calibração PDF->modelo de uma prancha por ICP: centros dos quadrados azuis (caixas) x linha de eletroduto mais próxima."""
import sys,json,math; sys.path.insert(0,'D:/Projeto Modelagem/FERRAMENTAS/eletrica')
import numpy as np, pymupdf as fitz, pdf_calib as pc
tag=sys.argv[1]
T=json.load(open(f'work/pdf_T_{tag}.json')); s,R,t=T['s'],np.array(T['R']),np.array(T['t'])
page=fitz.open(pc.PDF[tag])[0]
Q=np.array([[q[0],-q[1]] for q in pc.blue_squares(page)])
X=json.load(open(f'work/rede_{tag}.json'))
segs=[(a,b) for r in X['runs'] for a,b in zip(r['pts'],r['pts'][1:])]
LOT=lambda p:-38<p[0]<110 and -118<p[1]<70
def nearest(p):
    best=(99,None)
    for a,b in segs:
        dx,dy=b[0]-a[0],b[1]-a[1]; n=dx*dx+dy*dy; u=0 if n==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/n))
        q=(a[0]+u*dx,a[1]+u*dy); d=math.dist(p,q)
        if d<best[0]: best=(d,q)
    return best
for it,tol in enumerate([2.5,1.5,1.0,0.6,0.4,0.3,0.3]):
    M=[(s*R@q+t) for q in Q]
    pares=[(q,nearest(m)[1]) for q,m in zip(Q,M) if LOT(m) and nearest(m)[0]<tol]
    A=np.array([p[0] for p in pares]); B=np.array([p[1] for p in pares])
    ca,cb=A.mean(0),B.mean(0); H=(A-ca).T@(B-cb); U,S,Vt=np.linalg.svd(H); R2=Vt.T@U.T
    s2=S.sum()/((A-ca)**2).sum(); t2=cb-s2*R2@ca
    dt=(s2*R2@ca+t2)-(s*R@ca+t)
    s,R,t=s2,R2,t2
    res=[nearest(s*R@q+t)[0] for q in A]
    print(f'it{it} tol {tol}: pares {len(pares)}, escala {s:.5f}, rot {math.degrees(math.atan2(R[1,0],R[0,0])):.4f}°, deslocamento {dt.round(3)}, resíduo méd {np.mean(res):.3f} máx {max(res):.3f}')
T.update(s=float(s),R=R.tolist(),t=t.tolist(),origem=T.get('origem','')+' + ICP caixas x eletroduto')
json.dump(T,open(f'work/pdf_T_{tag}.json','w'),indent=1)
