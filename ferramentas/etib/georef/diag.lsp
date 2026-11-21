;; Diagnóstico do DWG (accoreconsole): unidades, extensão, layers com contagem, blocos com inserções no modelo,
;; xrefs e imagens. Saída: arquivo da variável de ambiente DIAG_TXT (barras normais).
;; Uso (.scr com CRLF): SECURELOAD 0 / (load "D:/.../diag.lsp") / DIAG / _.QUIT / _Y
(defun dg-n (ss) (if ss (sslength ss) 0))
(defun dg-pt (p) (strcat (rtos (car p) 2 4) "," (rtos (cadr p) 2 4) (if (caddr p) (strcat "," (rtos (caddr p) 2 4)) "")))
(defun c:diag ( / f tb n nm fl ss i e ed typ cnt pr)
  (setvar "TILEMODE" 1)
  (setq f (open (getenv "DIAG_TXT") "w"))
  (foreach v '("INSUNITS" "MEASUREMENT" "LUNITS" "ANGBASE" "ANGDIR" "AUNITS")
    (write-line (strcat "VAR\t" v "\t" (if (= (type (getvar v)) 'INT) (itoa (getvar v)) (rtos (getvar v) 2 6))) f))
  (foreach v '("EXTMIN" "EXTMAX" "INSBASE" "LIMMIN" "LIMMAX")
    (write-line (strcat "VAR\t" v "\t" (dg-pt (getvar v))) f))
  ;; contagem por tipo de entidade no modelo
  (setq ss (ssget "X" '((410 . "Model"))) cnt nil i 0)
  (write-line (strcat "MODEL_ENTS\t" (itoa (dg-n ss))) f)
  (if ss
    (repeat (sslength ss)
      (setq typ (cdr (assoc 0 (entget (ssname ss i)))))
      (if (setq pr (assoc typ cnt))
        (setq cnt (subst (cons typ (1+ (cdr pr))) pr cnt))
        (setq cnt (cons (cons typ 1) cnt)))
      (setq i (1+ i))))
  (foreach pr cnt (write-line (strcat "TYPE\t" (car pr) "\t" (itoa (cdr pr))) f))
  ;; layers: nome, entidades no modelo, flags (1 congelado, 4 travado), cor<0 = desligado
  (setq tb (tblnext "LAYER" T))
  (while tb
    (setq nm (cdr (assoc 2 tb)))
    (setq n (dg-n (ssget "X" (list (cons 8 nm) '(410 . "Model")))))
    (write-line (strcat "LAYER\t" nm "\t" (itoa n) "\tflags=" (itoa (cdr (assoc 70 tb))) "\tcor=" (itoa (cdr (assoc 62 tb)))) f)
    (setq tb (tblnext "LAYER")))
  ;; blocos: nome, flags (4 = xref), caminho do xref, inserções no modelo
  (setq tb (tblnext "BLOCK" T))
  (while tb
    (setq nm (cdr (assoc 2 tb)) fl (cdr (assoc 70 tb)))
    (if (/= (substr nm 1 1) "*")
      (write-line (strcat "BLOCK\t" nm "\tflags=" (itoa fl)
                          "\tins=" (itoa (dg-n (ssget "X" (list '(0 . "INSERT") (cons 2 nm) '(410 . "Model")))))
                          (if (assoc 1 tb) (strcat "\txref=" (cdr (assoc 1 tb))) "")) f))
    (setq tb (tblnext "BLOCK")))
  ;; layouts
  (foreach l (layoutlist) (write-line (strcat "LAYOUT\t" l) f))
  (close f)
  (princ))
