import json,math
T=json.load(open('D:/Projeto Modelagem/FERRAMENTAS/eletrica/transformacao_ELE_local_para_UTM.json'))
def tf(tag):
    R=T[tag]['R']; t=T[tag]['t']
    def f(p):
        x=R[0][0]*p[0]+R[0][1]*p[1]+t[0]; y=R[1][0]*p[0]+R[1][1]*p[1]+t[1]
        return (x-561500.0,y-8658000.0)
    return f
