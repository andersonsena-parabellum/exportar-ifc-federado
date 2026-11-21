# -*- coding: utf-8 -*-
"""Camada de compatibilidade para rodar as FERRAMENTAS (escritas para o Windows do notebook) na nuvem, sem reescrever os scripts.
Carregada sozinha quando esta pasta está no PYTHONPATH (o launcher etib-python faz isso).
- 'D:\\Projeto Modelagem\\...' vira $ETIB_RAIZ/... e 'G:\\Meu Drive\\...' vira $ETIB_G/...
- barras invertidas viram '/' em toda função de arquivo (open, os.*, os.path.*, glob, ifcopenshell, pymupdf, ezdxf);
- nome de pasta/arquivo com maiúsculas diferentes é achado como no Windows (busca sem diferenciar maiúsculas).
Só age no Linux; no notebook não faz nada."""
import os, sys
if os.name != 'nt':
    import builtins, glob as _glob, posixpath, re, functools
    RAIZ = os.environ.get('ETIB_RAIZ', '/mnt/project-files/dados_nuvem')
    RAIZ_G = os.environ.get('ETIB_G', os.path.join(RAIZ, '_G'))
    _PREF = [(re.compile(r'^[dD]:/+projeto modelagem(?=/|$)', re.I), RAIZ),
             (re.compile(r'^[gG]:/+meu drive(?=/|$)', re.I), RAIZ_G)]
    _stat, _listdir, _pjoin, _pnorm = os.stat, os.listdir, posixpath.join, posixpath.normpath

    def _existe(p):
        try: _stat(p); return True
        except OSError: return False

    @functools.lru_cache(maxsize=20000)
    def _resolver(p):
        """acha o caminho como o Windows acharia (sem diferenciar maiúsculas)."""
        if _existe(p) or not p.startswith('/'): return p
        partes = p.split('/'); atual = '/'
        for i, nome in enumerate(partes[1:], 1):
            if not nome: continue
            cand = _pjoin(atual, nome)
            if not _existe(cand):
                try: achados = [x for x in _listdir(atual) if x.lower() == nome.lower()]
                except OSError: return p
                if not achados: return p
                cand = posixpath.join(atual, achados[0])
            atual = cand
        return atual

    def N(p, resolver=True):
        if isinstance(p, os.PathLike): p = os.fspath(p)
        if not isinstance(p, str) or ('\\' not in p and ':' not in p[:2] and not resolver): return p
        q = p.replace('\\', '/')
        for rx, alvo in _PREF:
            if rx.match(q): q = rx.sub(alvo.replace('\\', '/'), q, count=1); break
        if resolver and q.startswith('/'):
            q = _resolver(_pnorm(q)) if '..' not in q else _resolver(q)
        return q

    def _emb(f, *idx, resolver=True):
        if getattr(f, '_etib', False): return f
        @functools.wraps(f)
        def g(*a, **k):
            a = list(a)
            for i in idx:
                if i < len(a): a[i] = N(a[i], resolver)
            for nome in ('path', 'file', 'filename', 'src', 'dst', 'fp', 'fname'):
                if nome in k: k[nome] = N(k[nome], resolver)
            return f(*a, **k)
        g._etib = True
        return g

    builtins.open = _emb(builtins.open, 0)
    import io; io.open = builtins.open
    for nome in ('stat', 'lstat', 'listdir', 'scandir', 'mkdir', 'rmdir', 'remove', 'unlink', 'chdir', 'utime', 'access', 'open', 'startfile'):
        if hasattr(os, nome): setattr(os, nome, _emb(getattr(os, nome), 0))
    for nome in ('rename', 'replace', 'link', 'symlink'):
        setattr(os, nome, _emb(getattr(os, nome), 0, 1))
    os.makedirs = _emb(os.makedirs, 0)
    for nome in ('basename', 'dirname', 'split', 'splitext', 'normpath', 'isabs'):
        setattr(posixpath, nome, _emb(getattr(posixpath, nome), 0, resolver=False))
    for nome in ('abspath', 'realpath', 'exists', 'isfile', 'isdir', 'islink', 'getsize', 'getmtime', 'getctime', 'lexists'):
        setattr(posixpath, nome, _emb(getattr(posixpath, nome), 0))
    _join = posixpath.join
    def _join_n(a, *p):
        if isinstance(a, bytes): return _join(a, *p)
        r = _join(N(a, False), *[N(x, False) for x in p])
        return N(r) if r.startswith('/') else r
    posixpath.join = _join_n
    _relpath = posixpath.relpath
    posixpath.relpath = lambda p, start=None: _relpath(N(p), N(start) if start else start)
    _glob.glob = _emb(_glob.glob, 0, resolver=False); _glob.iglob = _emb(_glob.iglob, 0, resolver=False)
    import shutil
    for nome in ('copy', 'copy2', 'copyfile', 'copytree', 'move', 'rmtree'):
        setattr(shutil, nome, _emb(getattr(shutil, nome), 0, 1))

    # imports: entradas do sys.path com caminho do Windows
    import importlib.machinery as _m
    _ff = _m.FileFinder.path_hook((_m.ExtensionFileLoader, _m.EXTENSION_SUFFIXES), (_m.SourceFileLoader, _m.SOURCE_SUFFIXES),
                                  (_m.SourcelessFileLoader, _m.BYTECODE_SUFFIXES))
    def _hook(entrada):
        if isinstance(entrada, str) and ('\\' in entrada or entrada[1:2] == ':'):
            return _ff(N(entrada))
        raise ImportError
    sys.path_hooks.insert(0, _hook); sys.path_importer_cache.clear()

    # bibliotecas que abrem arquivo no C/C++: importadas já envolvidas (custa ~0,5 s)
    try:
        import ifcopenshell; ifcopenshell.open = _emb(ifcopenshell.open, 0)
    except ImportError: pass
    try:
        import ezdxf
        from ezdxf.document import Drawing
        ezdxf.readfile = _emb(ezdxf.readfile, 0); Drawing.saveas = _emb(Drawing.saveas, 1)
    except ImportError: pass
    try:
        import pymupdf
        D = pymupdf.Document; _ini = D.__init__
        def __init__(s, filename=None, *a, **k): _ini(s, N(filename) if isinstance(filename, str) else filename, *a, **k)
        D.__init__ = __init__
        for cls, met in ((D, 'save'), (D, 'ez_save'), (pymupdf.Pixmap, 'save'), (pymupdf.Pixmap, 'pil_save')):
            if hasattr(cls, met): setattr(cls, met, _emb(getattr(cls, met), 1))
    except ImportError: pass
    os.environ.setdefault('PYTHONUTF8', '1')
