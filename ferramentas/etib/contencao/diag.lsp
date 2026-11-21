;; Diagnóstico do DWG: variáveis, layers e blocos -> arquivo em DIAG_TXT
(defun sslength-safe (ss) (if ss (sslength ss) 0))
(defun c:diag ( / f tb n)
  (setvar "TILEMODE" 1)
  (setq f (open (getenv "DIAG_TXT") "w"))
  (write-line (strcat "INSUNITS\t" (itoa (getvar "INSUNITS"))) f)
  (write-line (strcat "EXTMIN\t" (rtos (car (getvar "EXTMIN")) 2 4) "," (rtos (cadr (getvar "EXTMIN")) 2 4)) f)
  (write-line (strcat "EXTMAX\t" (rtos (car (getvar "EXTMAX")) 2 4) "," (rtos (cadr (getvar "EXTMAX")) 2 4)) f)
  (setq tb (tblnext "LAYER" T))
  (while tb
    (setq n (sslength-safe (ssget "X" (list (cons 8 (cdr (assoc 2 tb))) '(410 . "Model")))))
    (write-line (strcat "LAYER\t" (cdr (assoc 2 tb)) "\t" (itoa n)) f)
    (setq tb (tblnext "LAYER")))
  (setq tb (tblnext "BLOCK" T))
  (while tb
    (write-line (strcat "BLOCK\t" (cdr (assoc 2 tb))) f)
    (setq tb (tblnext "BLOCK")))
  (close f)
  (princ))
