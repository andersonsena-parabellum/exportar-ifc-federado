;; Entrada da escola: lista folhas (CTB de cada layout), estilos de texto (fontes) e xrefs do DWG aberto.
;; Sem ActiveX (o accoreconsole não tem): lê o dicionário ACAD_LAYOUT e as tabelas STYLE/BLOCK. Saída: arquivo em ENT_OUT.
(defun ent-s (x) (if x (if (= (type x) 'STR) x (vl-princ-to-string x)) ""))
(defun c:ENTDUMP ( / f d e n st b)
  (setq f (open (getenv "ENT_OUT") "w"))
  (write-line "ABRIU\t1" f)
  (write-line (strcat "PSTYLEMODE\t" (ent-s (getvar "PSTYLEMODE"))) f)
  (setq d (dictsearch (namedobjdict) "ACAD_LAYOUT"))
  (foreach p d
    (if (= (car p) 3) (setq n (cdr p)))
    (if (= (car p) 350)
      (progn
        (setq e (entget (cdr p)))
        (write-line (strcat "LAYOUT\t" (ent-s n) "\t" (ent-s (cdr (assoc 7 e))) "\t" (ent-s (cdr (assoc 2 e)))) f))))
  (setq st (tblnext "STYLE" T))
  (while st
    (write-line (strcat "STYLE\t" (ent-s (cdr (assoc 2 st))) "\t" (ent-s (cdr (assoc 3 st))) "\t" (ent-s (cdr (assoc 4 st)))) f)
    (setq st (tblnext "STYLE")))
  (setq b (tblnext "BLOCK" T))
  (while b
    (if (= 4 (logand 4 (cdr (assoc 70 b))))
      (write-line (strcat "XREF\t" (ent-s (cdr (assoc 2 b))) "\t" (ent-s (cdr (assoc 1 b)))) f))
    (setq b (tblnext "BLOCK")))
  (close f)
  (princ))
