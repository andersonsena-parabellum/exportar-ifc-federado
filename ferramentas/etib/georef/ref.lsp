;; Limpeza de uma cópia de BASE (SIT/TOP/TER) para vincular no Revit (_REF), a partir de uma lista feita em Python.
;; Arquivo REF_TXT: 1ª linha "cx cy raio" (centro da obra e raio); depois "D <handle>" (apagar) e "X <handle>" (explodir).
;;   D: entidades de nível superior inteiramente longe da obra (carimbo, legenda, notas) ou cópias deslocadas.
;;   X: inserções cujo PONTO BASE está longe da obra mas o conteúdo está nela (o Revit desloca esses blocos ao vincular).
;;      Explode em cascata (os blocos internos com ponto base longe também), convertendo atributos em textos antes.
;; Rode DEPOIS de geo.lsp quando a cópia também precisar ser movida (a lista já deve estar no sistema final).
;; Uso (.scr CRLF): SECURELOAD 0 / FILEDIA 0 / (load ".../ref.lsp") / REFLIMPA / _.SAVEAS 2018 "saida_REF.dwg" / _.QUIT / _Y
(defun ref-longe (p) (> (distance (list (car p) (cadr p)) (list ref-cx ref-cy)) ref-r))
(defun ref-split (s / i c cur out)
  (setq out nil cur "" i 1)
  (while (<= i (strlen s))
    (setq c (substr s i 1))
    (if (= c " ") (progn (if (/= cur "") (setq out (cons cur out))) (setq cur "")) (setq cur (strcat cur c)))
    (setq i (1+ i)))
  (if (/= cur "") (setq out (cons cur out)))
  (reverse out))
;; atributos da inserção -> TEXT soltos (o EXPLODE os transformaria em ATTDEF, mostrando o nome da etiqueta)
(defun ref-atts ( e / a ed tx)
  (setq a (entnext e))
  (while (and a (= (cdr (assoc 0 (setq ed (entget a)))) "ATTRIB"))
    (if (/= 1 (logand 1 (cdr (assoc 70 ed))))   ; ignora atributo invisível
      (progn
        (setq tx (list '(0 . "TEXT") (assoc 8 ed) (assoc 10 ed) (assoc 40 ed) (assoc 1 ed)))
        (foreach c '(50 7 41 51 72 11 210 62) (if (assoc c ed) (setq tx (append tx (list (assoc c ed))))))
        (if (assoc 74 ed) (setq tx (append tx (list (cons 73 (cdr (assoc 74 ed)))))))
        (entmake tx)))
    (setq a (entnext a))))
(defun ref-explode (e0 / q e ult n ed nx nd)
  (setq q (list e0) nx 0 nd 0)
  (while q
    (setq e (car q) q (cdr q))
    (if (= 1 (cdr (assoc 66 (entget e)))) (ref-atts e))
    (setq ult (entlast))
    (command "_.EXPLODE" e)
    (if (entget e) (princ (strcat "\nREF_NAO_EXPLODIU " (cdr (assoc 5 (entget e))) " " (cdr (assoc 2 (entget e)))))
      (setq nx (1+ nx)))
    (setq n (entnext ult))
    (while n
      (setq ed (entget n))
      (cond
        ((= (cdr (assoc 0 ed)) "ATTDEF") (entdel n) (setq nd (1+ nd)))
        ((and (= (cdr (assoc 0 ed)) "INSERT") (ref-longe (cdr (assoc 10 ed)))) (setq q (cons n q))))
      (setq n (entnext n))))
  (list nx nd))
(defun c:reflimpa ( / f ln p e nd nx r tb trav)
  (setvar "TILEMODE" 1)
  (setvar "CTAB" "Model")
  (setvar "QAFLAGS" 0)
  (setq f (open (getenv "REF_TXT") "r") ln (read-line f) p (ref-split ln))
  (setq ref-cx (atof (car p)) ref-cy (atof (cadr p)) ref-r (atof (caddr p)) nd 0 nx 0)
  ;; destrava os layers (EXPLODE/ERASE não mexem em layer travado); depois retrava
  (setq tb (tblnext "LAYER" T) trav nil)
  (while tb (if (= 4 (logand 4 (cdr (assoc 70 tb)))) (setq trav (cons (cdr (assoc 2 tb)) trav))) (setq tb (tblnext "LAYER")))
  (command "_.-LAYER" "_U" "*" "")
  (while (setq ln (read-line f))
    (setq p (ref-split ln) e (handent (cadr p)))
    (cond
      ((null e) (princ (strcat "\nREF_SEM_HANDLE " (cadr p))))
      ((= (car p) "D") (entdel e) (setq nd (1+ nd)))
      ((= (car p) "X") (setq r (ref-explode e) nx (+ nx (car r))))))
  (close f)
  (foreach l trav (command "_.-LAYER" "_LO" l ""))
  (setvar "INSUNITS" 6)
  (command "_.ZOOM" "_E")
  (princ (strcat "\nREF_OK apagadas=" (itoa nd) " explodidas=" (itoa nx)
                 " EXTMIN=" (rtos (car (getvar "EXTMIN")) 2 3) "," (rtos (cadr (getvar "EXTMIN")) 2 3)
                 " EXTMAX=" (rtos (car (getvar "EXTMAX")) 2 3) "," (rtos (cadr (getvar "EXTMAX")) 2 3)))
  (princ))
