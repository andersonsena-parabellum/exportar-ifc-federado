;; Aplica a transformação rígida (rotação em torno de 0,0 e depois translação) a TODO o espaço do modelo
;; e grava a cópia _GEO. Lê da variável de ambiente GEO_PARAMS: "<rot_graus> <tx> <ty> <saida.dwg>"
;; (barras normais no caminho; sem espaços no caminho de saída não é exigido: o caminho é o resto da linha).
;; Destrava/descongela/liga os layers para o ROTATE/MOVE pegarem tudo e depois devolve o estado original.
;; Também grava INSUNITS = 6 (metros), porque alguns DWGs vêm marcados em polegadas/pés com geometria em metros.
(defun gg:split (s / i out tok c)
  (setq out nil tok "" i 1)
  (while (<= i (strlen s))
    (setq c (substr s i 1))
    (if (and (= c " ") (< (length out) 3))
      (progn (if (/= tok "") (setq out (cons tok out))) (setq tok ""))
      (setq tok (strcat tok c)))
    (setq i (1+ i)))
  (if (/= tok "") (setq out (cons tok out)))
  (reverse out))
(defun c:georefgeo ( / par ang tx ty saida r frz lck off nm fl ss n0 ce)
  (setvar "TILEMODE" 1)
  (setvar "CMDECHO" 0)
  (setq par (gg:split (getenv "GEO_PARAMS")))
  (setq ang (atof (nth 0 par)) tx (atof (nth 1 par)) ty (atof (nth 2 par)) saida (nth 3 par))
  ;; guarda o estado dos layers
  (setq frz nil lck nil off nil r (tblnext "LAYER" T))
  (while r
    (setq nm (cdr (assoc 2 r)) fl (cdr (assoc 70 r)))
    (if (= 1 (logand fl 1)) (setq frz (cons nm frz)))
    (if (= 4 (logand fl 4)) (setq lck (cons nm lck)))
    (if (< (cdr (assoc 62 r)) 0) (setq off (cons nm off)))
    (setq r (tblnext "LAYER")))
  (setq ce (getvar "CLAYER"))
  (setvar "CLAYER" "0")
  (command "_.-LAYER" "_T" "*" "_ON" "*" "_U" "*" "")
  (setq ss (ssget "X" '((410 . "Model"))))
  (setq n0 (if ss (sslength ss) 0))
  (if ss
    (progn
      (if (/= ang 0.0) (command "_.ROTATE" ss "" (list 0.0 0.0 0.0) ang))
      (command "_.MOVE" ss "" (list 0.0 0.0 0.0) (list tx ty 0.0))))
  ;; devolve o estado dos layers
  (foreach nm frz (if (/= nm "0") (command "_.-LAYER" "_F" nm "")))
  (foreach nm off (if (/= nm "0") (command "_.-LAYER" "_OFF" nm "")))
  (foreach nm lck (command "_.-LAYER" "_LO" nm ""))
  (if (tblsearch "LAYER" ce) (setvar "CLAYER" ce))
  (setvar "INSUNITS" 6)
  (command "_.ZOOM" "_E")
  (princ (strcat "\nGEOREF: " (itoa n0) " entidades; rot=" (rtos ang 2 12) " t=" (rtos tx 2 6) "," (rtos ty 2 6) "\n"))
  (command "_.SAVEAS" "2018" saida)
  (princ))
