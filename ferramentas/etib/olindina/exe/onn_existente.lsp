;; Olindina — ESG-001 / DRE-001: a rede existente da prancha (layer "Tubulação existente", tudo dentro de um bloco anônimo do
;; projetista) saía em magenta e com os textos de 0,40 m sobrepostos (Anderson, 22/10/2026). Aqui:
;;   - a cor do layer passa a ONN_COR (variável de ambiente; padrão 136, ciano escuro: o magenta era feio, o cinza apagado e o laranja
;;     é a cor do esgoto de gordura na legenda da folha; Anderson 22/10, "importante olhar a legenda tbm");
;;   - a legenda ganha a linha da rede existente (ONNLEG: quadro novo no papel, logo abaixo das notas, com a amostra no próprio layer);
;;   - os textos do layer (TEXT/MTEXT, dentro de qualquer bloco ou no modelo) ficam com a altura multiplicada por ONN_FATOR
;;     (variável de ambiente; padrão 0,55), no mesmo ponto de inserção.
;; Uso no accoreconsole: (load ".../onn_existente.lsp") ONNEXIST e depois _.QSAVE.
(defun onn:lay ( / r nm out)
  (setq r (tblnext "LAYER" T))
  (while r
    (setq nm (cdr (assoc 2 r)))
    (if (wcmatch (strcase nm) "TUBULA*EXISTENTE") (setq out nm))
    (setq r (tblnext "LAYER")))
  out)
(defun onn:texto (e f / d)
  (setq d (entget e))
  (if (member (cdr (assoc 0 d)) '("TEXT" "MTEXT"))
    (progn
      (setq d (subst (cons 40 (* f (cdr (assoc 40 d)))) (assoc 40 d) d))
      (if (and (= (cdr (assoc 0 d)) "MTEXT") (assoc 41 d) (> (cdr (assoc 41 d)) 0.0))
        (setq d (subst (cons 41 (* f (cdr (assoc 41 d)))) (assoc 41 d) d)))
      (entmod d) T)))
(defun c:onnexist ( / lay f b e n nb ss i cor)
  (setvar "CMDECHO" 0)
  (setq lay (onn:lay) n 0 nb 0)
  (setq f (if (getenv "ONN_FATOR") (atof (getenv "ONN_FATOR")) 0.55))
  (setq cor (if (getenv "ONN_COR") (getenv "ONN_COR") "136"))
  (if (null lay) (princ "\nONNEXIST: layer da rede existente nao achado")
    (progn
      (command "_.-LAYER" "_C" cor lay "")
      ;; textos dentro dos blocos
      (setq b (tblnext "BLOCK" T))
      (while b
        (setq e (cdr (assoc -2 b)))
        (while e
          (if (= (cdr (assoc 8 (entget e))) lay) (if (onn:texto e f) (setq nb (1+ nb))))
          (setq e (entnext e)))
        (setq b (tblnext "BLOCK")))
      ;; textos soltos no modelo
      (if (setq ss (ssget "X" (list '(0 . "TEXT,MTEXT") (cons 8 lay) '(410 . "Model"))))
        (progn (setq i 0) (repeat (sslength ss) (if (onn:texto (ssname ss i) f) (setq n (1+ n))) (setq i (1+ i)))))
      (command "_.REGENALL")
      (princ (strcat "\nONNEXIST_OK layer na cor " cor "; textos reduzidos: " (itoa nb) " em blocos, " (itoa n) " no modelo; fator " (rtos f 2 2)))))
  (princ))

;; ---- legenda: quadro "REDE EXISTENTE" no papel, abaixo das notas, na coluna da legenda do projetista
;; posição no papel do layout da legenda (bloco LEGENDA - ETIBs inserido em -702,11 / 477,36): coluna x 603,18 a 763,18;
;; as notas terminam em y ~373 e o quadro de revisões começa em y ~87 (lido do PDF da R01)
(defun onn:leg_layout ( / ss i e d out)
  (if (setq ss (ssget "X" '((0 . "INSERT") (67 . 1))))
    (progn (setq i 0)
      (repeat (sslength ss)
        (setq d (entget (ssname ss i)))
        (if (and (null out) (onn:tem_dreno (cdr (assoc 2 d)))) (setq out (cdr (assoc 410 d))))
        (setq i (1+ i)))))
  out)
(defun onn:tem_dreno (nome / b e r)
  (if (setq b (tblobjname "BLOCK" nome))
    (progn (setq e (entnext b))
      (while (and e (not r))
        (if (and (= (cdr (assoc 0 (entget e))) "MTEXT") (wcmatch (cdr (assoc 1 (entget e))) "*Dreno AC*")) (setq r T))
        (setq e (entnext e)))))
  r)
(defun onn:estilo ( / b e d r)
  ;; estilo e altura do texto da legenda do projetista
  (if (setq b (tblobjname "BLOCK" "LEGENDA - ETIBs"))
    (progn (setq e (entnext b))
      (while (and e (not r))
        (setq d (entget e))
        (if (and (= (cdr (assoc 0 d)) "MTEXT") (wcmatch (cdr (assoc 1 d)) "*Dreno AC*")) (setq r (list (cdr (assoc 7 d)) (cdr (assoc 40 d)))))
        (setq e (entnext e)))))
  (if r r (list "Standard" 2.2)))
(defun onn:pl (lay pts lo fecha / ok)
  (entmake (append (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(67 . 1) (cons 410 lo) (cons 8 lay) '(100 . "AcDbPolyline")
                         (cons 90 (length pts)) (cons 70 (if fecha 1 0)))
                   (mapcar '(lambda (p) (cons 10 p)) pts))))
(defun onn:mt (lay lo p h w at txt st)
  (entmake (list '(0 . "MTEXT") '(100 . "AcDbEntity") '(67 . 1) (cons 410 lo) (cons 8 lay) '(100 . "AcDbMText")
                 (cons 10 (list (car p) (cadr p) 0.0)) (cons 40 h) (cons 41 w) (cons 71 at) (cons 7 st) (cons 1 txt))))
(defun c:onnleg ( / lay lo est st h x0 x1 y0 r a b c d n)
  (setvar "CMDECHO" 0)
  (setq lay (onn:lay) lo (onn:leg_layout) est (onn:estilo) st (car est) h (cadr est) n 0)
  (if (or (null lay) (null lo)) (princ "
ONNLEG: layer ou layout da legenda nao achado")
    (progn
      (setq x0 603.18 x1 763.18 y0 360.0 r 5.845)
      (if (onn:pl "DI-Tabelas" (list (list x0 y0) (list x1 y0) (list x1 (- y0 (* 2 r))) (list x0 (- y0 (* 2 r)))) lo T) (setq n (1+ n)))
      (if (onn:pl "DI-Tabelas" (list (list x0 (- y0 r)) (list x1 (- y0 r))) lo nil) (setq n (1+ n)))
      (if (onn:mt "DI-Tabelas" lo (list (/ (+ x0 x1) 2) (- y0 (/ r 2))) h 0.0 5 "REDE EXISTENTE (CADASTRO DO PROJETO)" st) (setq n (1+ n)))
      ;; amostra no próprio layer da rede existente (a cor acompanha o layer)
      (if (onn:pl lay (list (list (+ x0 4.0) (- y0 (* 1.5 r))) (list (+ x0 22.0) (- y0 (* 1.5 r)))) lo nil) (setq n (1+ n)))
      (if (onn:mt "DI-Tabelas" lo (list (+ x0 26.0) (- y0 (* 1.5 r))) h 0.0 4 "Redes existentes de esgoto e de drenagem pluvial (PVC)" st) (setq n (1+ n)))
      (princ (strcat "
ONNLEG_OK " (itoa n) " de 5 entidades no layout " lo " (estilo " st ")"))))
  (princ))
