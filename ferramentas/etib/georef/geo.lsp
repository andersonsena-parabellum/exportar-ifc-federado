;; Georreferencia a CÓPIA aberta no accoreconsole: gira o espaço do modelo inteiro em torno de (0,0) e depois move.
;; Parâmetros por variável de ambiente (strings com todas as casas decimais):
;;   GEO_ROT (graus, opcional; "0" = sem rotação), GEO_DX, GEO_DY (translação, depois da rotação).
;; Destrava/descongela/liga tudo para o comando pegar todas as entidades e DEPOIS restaura o estado de cada layer.
;; Grava INSUNITS = 6 (metros), para o Revit ler a unidade certa ao vincular.
;; Uso (.scr CRLF): SECURELOAD 0 / FILEDIA 0 / (load ".../geo.lsp") / GEO / _.SAVEAS 2018 "saida_GEO.dwg" / _.QUIT / _Y
(defun c:geo ( / tb st ss rot e ed n)
  (setvar "TILEMODE" 1)
  (setvar "CTAB" "Model")
  (setq st nil tb (tblnext "LAYER" T))
  (while tb
    (setq st (cons (list (cdr (assoc 2 tb)) (cdr (assoc 70 tb)) (cdr (assoc 62 tb))) st))
    (setq tb (tblnext "LAYER")))
  (command "_.-LAYER" "_T" "*" "_ON" "*" "_U" "*" "")
  (setvar "CLAYER" "0")
  (setq ss (ssget "X" '((410 . "Model"))) n (if ss (sslength ss) 0))
  (princ (strcat "\nGEO_ENTIDADES=" (itoa n)))
  (setq rot (getenv "GEO_ROT"))
  (if (and ss rot (/= (atof rot) 0.0)) (command "_.ROTATE" ss "" "0,0" rot))
  (setq ss (ssget "X" '((410 . "Model"))))
  (if ss (command "_.MOVE" ss "" "0,0" (strcat (getenv "GEO_DX") "," (getenv "GEO_DY"))))
  ;; restaura congelado/travado (70) e ligado/desligado (sinal da cor, 62)
  (foreach s st
    (if (setq e (tblobjname "LAYER" (car s)))
      (progn
        (setq ed (entget e))
        (setq ed (subst (cons 70 (cadr s)) (assoc 70 ed) ed))
        (setq ed (subst (cons 62 (caddr s)) (assoc 62 ed) ed))
        (entmod ed))))
  (setvar "INSUNITS" 6)
  (command "_.ZOOM" "_E")
  (princ (strcat "\nGEO_OK EXTMIN=" (rtos (car (getvar "EXTMIN")) 2 3) "," (rtos (cadr (getvar "EXTMIN")) 2 3)
                 " EXTMAX=" (rtos (car (getvar "EXTMAX")) 2 3) "," (rtos (cadr (getvar "EXTMAX")) 2 3)))
  (princ))
