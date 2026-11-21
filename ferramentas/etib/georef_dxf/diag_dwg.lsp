;; Diagnóstico de DWG para georreferenciamento (sem ActiveX: roda no accoreconsole).
;; Saída: arquivo em DIAG_TXT (barras normais).
;; Grava: variáveis de unidade/extensão, tabela de layers, tabela de blocos (xref/anônimo) e
;; contagem de INSERT por nome no espaço do modelo.
(defun dg:str (x)
  (cond ((= (type x) 'STR) x)
        ((= (type x) 'INT) (itoa x))
        ((= (type x) 'REAL) (rtos x 2 6))
        ((= (type x) 'LIST) (strcat (rtos (car x) 2 4) "," (rtos (cadr x) 2 4) (if (caddr x) (strcat "," (rtos (caddr x) 2 4)) "")))
        (T "?")))
(defun c:diag ( / out f r ss i ed nm cnt pair)
  (setvar "TILEMODE" 1)
  (setq out (getenv "DIAG_TXT"))
  (setq f (open out "w"))
  (foreach v '("DWGNAME" "ACADVER" "INSUNITS" "MEASUREMENT" "LUNITS" "AUNITS" "ANGBASE" "ANGDIR" "EXTMIN" "EXTMAX" "LIMMIN" "LIMMAX" "UCSORG" "UCSXDIR" "WORLDUCS")
    (write-line (strcat "VAR\t" v "\t" (dg:str (getvar v))) f))
  (setq r (tblnext "LAYER" T))
  (while r
    (write-line (strcat "LAYER\t" (cdr (assoc 2 r)) "\t" (itoa (cdr (assoc 70 r))) "\t" (itoa (cdr (assoc 62 r)))) f)
    (setq r (tblnext "LAYER")))
  (setq r (tblnext "BLOCK" T))
  (while r
    (write-line (strcat "BLOCK\t" (cdr (assoc 2 r)) "\t" (itoa (cdr (assoc 70 r))) "\t" (if (assoc 1 r) (cdr (assoc 1 r)) "") "\t" (dg:str (cdr (assoc 10 r)))) f)
    (setq r (tblnext "BLOCK")))
  (setq cnt nil)
  (setq ss (ssget "X" '((0 . "INSERT") (410 . "Model"))))
  (setq i 0)
  (if ss
    (repeat (sslength ss)
      (setq ed (entget (ssname ss i)) nm (cdr (assoc 2 ed)))
      (if (setq pair (assoc nm cnt))
        (setq cnt (subst (cons nm (1+ (cdr pair))) pair cnt))
        (setq cnt (cons (cons nm 1) cnt)))
      (setq i (1+ i))))
  (foreach p cnt (write-line (strcat "INSCOUNT\t" (car p) "\t" (itoa (cdr p))) f))
  (setq ss (ssget "X" '((410 . "Model"))))
  (write-line (strcat "NENT_MODEL\t" (if ss (itoa (sslength ss)) "0")) f)
  (close f)
  (princ))
