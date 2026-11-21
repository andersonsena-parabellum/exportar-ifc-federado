;; Plota cada layout de papel da cópia aberta em PDF A0 (DWG To PDF.pc3, Extents, Fit, centrado, cores do desenho).
;; Variável: PLOT_BASE (caminho sem extensão; sai <base>__<n>.pdf, n = posição da aba do layout)
(defun c:plottodos ( / d g n k lay)
  (setvar "CMDECHO" 1) (setvar "FILEDIA" 0) (setvar "BACKGROUNDPLOT" 0)
  (setq d (dictsearch (namedobjdict) "ACAD_LAYOUT") k 0)
  (while d
    (setq g (car d) d (cdr d))
    (if (and (= (car g) 3) (/= (strcase (cdr g)) "MODEL"))
      (progn
        (setq lay (cdr g) n (cdr (assoc 71 (entget (cdr (car d))))) k (1+ k))
        (setvar "CTAB" lay)
        (command "_.-PLOT" "_Y" lay "DWG To PDF.pc3" "ISO full bleed A0 (841.00 x 1189.00 MM)" "_M" "_L" "_N" "_E" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N"
                 (strcat (getenv "PLOT_BASE") "__" (itoa n) ".pdf") "_N" "_Y")
        (princ (strcat "\nPLOT_OK " (itoa n) " " lay)))))
  (princ (strcat "\nPLOT_FIM " (itoa k) " layouts"))
  (princ))
