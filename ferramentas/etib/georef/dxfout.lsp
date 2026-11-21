;; Exporta a cópia aberta para DXF ASCII (R2018, 16 casas) no caminho da variável DXF_OUT. Rápido (comando nativo).
(defun c:dxfx ( / out)
  (setvar "TILEMODE" 1)
  (setq out (getenv "DXF_OUT"))
  (command "_.DXFOUT" out "_V" "_2018" "16")
  (princ))
