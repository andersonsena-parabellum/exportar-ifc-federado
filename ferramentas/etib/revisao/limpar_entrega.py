# Cópia de entrega (último passo, depois do APROVADO): tira do IFC as propriedades de trabalho (fora_do_comercial, angulo_real,
# deflexao_junta_graus), que ficam só no registro interno (CSV na pasta revisao da escola). Uso: python limpar_entrega.py <pasta 03_IFC do envio> <csv interno>
import sys, os, glob, csv, ifcopenshell, ifcopenshell.util.element as U
TIRAR = {'fora_do_comercial', 'angulo_real', 'deflexao_junta_graus'}
pasta, saida = sys.argv[1], sys.argv[2]; reg = {}
for fn in sorted(glob.glob(os.path.join(pasta, '*.ifc'))):
    f = ifcopenshell.open(fn); n = 0
    for el in f.by_type('IfcProduct'):
        d = U.get_psets(el).get('Dados_ETIB', {})
        if any(k in d for k in TIRAR):
            reg[el.GlobalId] = dict(nome=el.Name, classe=el.is_a(), sistema=d.get('sistema'), **{k: d.get(k) for k in sorted(TIRAR)})
    for ps in f.by_type('IfcPropertySet'):
        props = list(ps.HasProperties or []); fica = [p for p in props if p.Name not in TIRAR]
        if len(fica) != len(props):
            ps.HasProperties = fica
            for p in props:
                if p.Name in TIRAR and not f.get_inverse(p): f.remove(p); n += 1
    f.write(fn); print(os.path.basename(fn), n, 'propriedades tiradas')
with open(saida, 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo, delimiter=';'); w.writerow(['guid', 'nome', 'classe', 'sistema', *sorted(TIRAR)])
    for g, r in reg.items(): w.writerow([g, r['nome'], r['classe'], r['sistema'], *[r[k] for k in sorted(TIRAR)]])
print(len(reg), 'peças no registro interno:', saida)
