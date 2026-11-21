# FERRAMENTAS na nuvem

Cópia do `D:\Projeto Modelagem\FERRAMENTAS` do notebook (sem `.venv`, `work` e dados), com histórico git nesta pasta.
Os scripts NÃO foram reescritos: a camada `_nuvem/sitecustomize.py` traduz na hora os caminhos do Windows.

    bash /mnt/project-files/ferramentas_nuvem/ambiente/preparar_nuvem.sh      # 1x por sessão, < 1 min
    export ETIB_RAIZ=$HOME/etib-raiz                                           # árvore igual à do D:\Projeto Modelagem
    cd $ETIB_RAIZ/FERRAMENTAS/revisao && bash $ETIB_RAIZ/FERRAMENTAS/_nuvem/etib-python revisar.py exemplo --sem-envio

- `D:\Projeto Modelagem\...` → `$ETIB_RAIZ/...`; `G:\Meu Drive\...` → `$ETIB_G/...` (padrão `$ETIB_RAIZ/_G`).
- Barra invertida vira `/` e nome com maiúscula diferente é achado como no Windows.
- Passos que chamam accoreconsole, Revit, powershell ou tasklist NÃO rodam aqui (ver plano <link privado da página>).
- Commits: `git -c safe.directory=* commit` (a pasta do projeto tem outro dono).

Teste 26/10: revisar.py exemplo --sem-envio rodou em 3,5 min; itens B, C, D e E1–E11 batem com os relatórios do notebook,
fora o que mudou no código depois deles (B9 jargão e E6 folha inteira).
