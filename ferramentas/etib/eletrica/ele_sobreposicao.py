"""Sobreposição física entre eletrodutos modelados (geometria lida do Revit, DE real). Separa cruzamento x paralelo (banco)."""
import math, collections, csv, numpy as np
W='D:/Projeto Modelagem/FERRAMENTAS/eletrica/work/'
def segdist(p1,q1,p2,q2):
    d1=q1-p1; d2=q2-p2; r=p1-p2; a=d1@d1; e=d2@d2; f=d2@r; c=d1@r; b=d1@d2; den=a*e-b*b
    s=np.clip((b*f-c*e)/den,0,1) if den>1e-12 else 0.0
    t=(b*s+f)/e if e>1e-12 else 0
    if t<0: t=0; s=np.clip(-c/a,0,1)
    elif t>1: t=1; s=np.clip((b-c)/a,0,1)
    P=p1+d1*s; Q=p2+d2*t; return np.linalg.norm(P-Q),(P+Q)/2
S=[]
for l in open(W+'revit_leitura_fase4.tsv',encoding='utf-8'):
    r=l.rstrip('\n').split('\t')
    if r[0]=='C': S.append((r[3],r[1],np.array(list(map(float,r[6:9]))),np.array(list(map(float,r[9:12]))),float(r[5])/1000))
res={}
for i in range(len(S)):
    ti,ii,ai,bi,di=S[i]
    for j in range(i+1,len(S)):
        tj,ij,aj,bj,dj=S[j]
        if ti.split('.')[0]==tj.split('.')[0]: continue
        if max(ai[0],bi[0])+0.3<min(aj[0],bj[0]) or max(aj[0],bj[0])+0.3<min(ai[0],bi[0]) or max(ai[1],bi[1])+0.3<min(aj[1],bj[1]) or max(aj[1],bj[1])+0.3<min(ai[1],bi[1]): continue
        d,m=segdist(ai,bi,aj,bj); g=d-(di+dj)/2
        if g<0:
            u=(bi-ai)[:2]/np.linalg.norm((bi-ai)[:2]); v=(bj-aj)[:2]/np.linalg.norm((bj-aj)[:2]); ang=math.degrees(math.acos(min(1,abs(u@v))))
            k=(ti.split('.')[0],tj.split('.')[0])
            if k not in res or g<res[k][0]: res[k]=(g,ang,m,ii,ij,di,dj)
rows=[]
for (a,b),(g,ang,m,ii,ij,di,dj) in sorted(res.items(),key=lambda x:x[1][0]):
    tipo='paralelo (banco/mesma vala)' if ang<20 else 'cruzamento'
    rows.append([a,b,ii,ij,f'{di*1000:.1f}',f'{dj*1000:.1f}',f'{-g*1000:.0f}',f'{ang:.0f}',tipo,f'{m[0]:.2f}',f'{m[1]:.2f}',f'{m[2]:.2f}'])
with open('D:/Projeto Modelagem/ETIB-ALAGOINHAS/RELATORIOS/ELE_fase4_sobreposicoes_internas_2026-10-15.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(['trecho A','trecho B','id A','id B','DE A mm','DE B mm','sobreposição mm','ângulo °','tipo','x','y','z']); w.writerows(rows)
c=collections.Counter(r[8] for r in rows); print(len(rows),'pares |',dict(c))
print('mesma rede:',sum(1 for r in rows if r[0][:3]==r[1][:3]),'| entre redes:',collections.Counter(tuple(sorted((r[0][:3],r[1][:3]))) for r in rows if r[0][:3]!=r[1][:3]))
print('sobreposição mm: máx',max(int(r[6]) for r in rows),'mediana',sorted(int(r[6]) for r in rows)[len(rows)//2])
for r in rows[:8]: print(r)
