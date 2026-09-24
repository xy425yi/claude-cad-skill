;;; lib.lsp — helpers for editing DWGs inside accoreconsole (headless AutoCAD / AutoCAD LT 2024+).
;;; Plain DXF-list LISP only: entget / entmod / entmake / entdel / command.
;;; accoreconsole has NO ActiveX object model: vla-* / vlax-* calls fail silently — never use them here.
;;; Every function prints a one-line result starting with a tag (SET / DEL / MOVE / …) so the log is greppable.

(vl-load-com)
;; ---------- generic entity access ----------
(defun hl-ent (h) (handent h))                                            ; handle -> ename or nil
(defun hl-get (h code) (cdr (assoc code (entget (handent h)))))           ; one DXF group of an entity
(defun hl-type (h) (hl-get h 0))
(defun hl-log (tag h ok) (princ (strcat "\n" tag " " h " " (if ok "OK" "FAIL"))) ok)

;; replace ALL occurrences of group `code` with `val` (or the first only when `first` is T)
(defun hl-set-group (h code val first / ed out done item)
  (setq ed (entget (handent h)) out nil done nil)
  (foreach item ed
    (if (and (= (car item) code) (or (not first) (not done)))
      (progn (setq out (cons (cons code val) out)) (setq done T))
      (setq out (cons item out))))
  (if done (entmod (reverse out)))
  done)

;; ---------- text ----------
;; TEXT: group 1.  MTEXT: group 1 holds the last ≤250 chars, extra 3-groups hold earlier chunks -> drop the 3s.
(defun set-text (h str / ed out item ok)
  (setq ed (entget (handent h)) out nil ok nil)
  (foreach item ed
    (cond ((= (car item) 3) nil)
          ((= (car item) 1) (setq out (cons (cons 1 str) out)) (setq ok T))
          (T (setq out (cons item out)))))
  (if ok (entmod (reverse out)))
  (hl-log "SET-TEXT" h ok))

;; ---------- block reference attributes (INSERT -> ATTRIB chain) ----------
(defun get-insert-attr (h tag / en at val)
  (setq en (handent h) val nil)
  (if (= (cdr (assoc 66 (entget en))) 1)
    (progn (setq at (entnext en))
      (while (and at (= (cdr (assoc 0 (entget at))) "ATTRIB"))
        (if (= (strcase (cdr (assoc 2 (entget at)))) (strcase tag)) (setq val (cdr (assoc 1 (entget at)))))
        (setq at (entnext at)))))
  val)
(defun set-insert-attr (h tag val / en at ok ed)
  (setq en (handent h) ok nil)
  (if (= (cdr (assoc 66 (entget en))) 1)
    (progn (setq at (entnext en))
      (while (and at (= (cdr (assoc 0 (entget at))) "ATTRIB"))
        (if (= (strcase (cdr (assoc 2 (entget at)))) (strcase tag))
          (progn (setq ed (entget at)) (entmod (subst (cons 1 val) (assoc 1 ed) ed)) (setq ok T)))
        (setq at (entnext at)))
      (entupd en)))
  (hl-log (strcat "SET-ATTR " tag "=" val) h ok))

;; ---------- MULTILEADER with block content (keynote bubbles etc.) ----------
;; attributes live inside the MLEADER entity as 330 (ATTDEF id) / 302 (value) pairs — no ATTRIB chain.
(defun ml-get-attr (h tag / en ed item attid val)
  (setq en (handent h) val nil attid nil)
  (if en
    (foreach item (entget en)
      (cond ((= (car item) 330) (setq attid (cdr item)))
            ((and (= (car item) 302) attid (null val)
                  (= (strcase (cdr (assoc 2 (entget attid)))) (strcase tag)))
             (setq val (cdr item))))))
  val)
(defun ml-set-attr (h tag val / en ed out item attid ok)
  (setq en (handent h) ok nil)
  (if en
    (progn (setq ed (entget en) out nil attid nil)
      (foreach item ed
        (cond ((= (car item) 330) (setq attid (cdr item)) (setq out (cons item out)))
              ((and (= (car item) 302) attid (= (strcase (cdr (assoc 2 (entget attid)))) (strcase tag)))
               (setq out (cons (cons 302 val) out)) (setq ok T))
              (T (setq out (cons item out)))))
      (if ok (entmod (reverse out)))))
  (hl-log (strcat "ML-SET " tag "=" val) h ok))
;; MLEADER with MTEXT content: the text is group 304
(defun ml-set-text (h str) (hl-log "ML-SET-TEXT" h (hl-set-group h 304 str T)))

;; ---------- delete / move / layer / color ----------
(defun del-handle (h / en) (setq en (handent h)) (if en (entdel en)) (hl-log "DEL" h (if en T nil)))
(defun move-handle (h dx dy / en)
  (setq en (handent h))
  (if en (command "_.MOVE" en "" "_none" (list 0.0 0.0 0.0) "_none" (list dx dy 0.0)))
  (hl-log (strcat "MOVE " (rtos dx 2 2) "," (rtos dy 2 2)) h (if en T nil)))
(defun set-layer (h lay) (hl-log (strcat "LAYER " lay) h (hl-set-group h 8 lay T)))
(defun set-color (h c / ed)      ; c = ACI number; 256 = ByLayer
  (setq ed (entget (handent h)))
  (entmod (if (assoc 62 ed) (subst (cons 62 c) (assoc 62 ed) ed) (append ed (list (cons 62 c)))))
  (hl-log (strcat "COLOR " (itoa c)) h T))

;; ---------- layers ----------
(defun ensure-layer (name color / )
  (if (not (tblsearch "LAYER" name))
    (entmake (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord") '(100 . "AcDbLayerTableRecord")
                   (cons 2 name) '(70 . 0) (cons 62 color) '(6 . "Continuous"))))
  name)
;; Freeze every layer that is OFF (62 < 0).  DWG To PDF exports OFF layers as hidden PDF layers (OCG /OFF);
;; merging such PDFs (PyMuPDF / pypdf) drops the /OFF config and the hidden geometry shows up.  Frozen
;; layers are not exported at all, so call this in every plot --pre (after CLAYER is set to "0").
(defun freeze-off-layers (/ l names)
  (setq l (tblnext "LAYER" T))
  (while l
    (if (and (< (cdr (assoc 62 l)) 0) (/= (cdr (assoc 2 l)) (getvar "CLAYER")))
      (setq names (cons (cdr (assoc 2 l)) names)))
    (setq l (tblnext "LAYER")))
  (foreach n names (command "_.-LAYER" "_F" n ""))
  (princ (strcat "
FREEZE-OFF " (itoa (length names)) " layers"))
  names)
;; non-plotting review layer (290 . 0): boxes + notes that tell the human where things changed
(defun ensure-review-layer (name color / )
  (if (not (tblsearch "LAYER" name))
    (entmake (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord") '(100 . "AcDbLayerTableRecord")
                   (cons 2 name) '(70 . 0) (cons 62 color) '(6 . "Continuous") '(290 . 0))))
  name)
(defun layer-onoff (name on) (command "_.-LAYER" (if on "_ON" "_OFF") name "") (princ (strcat "\nLAYER " name (if on " ON" " OFF"))))
(defun layer-freeze (name) (command "_.-LAYER" "_F" name "") (princ (strcat "\nLAYER " name " FROZEN")))

;; ---------- drawing on the review layer ----------
(defun review-box (x0 y0 x1 y1 lay)
  (entmake (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay) '(100 . "AcDbPolyline") '(90 . 4) '(70 . 1)
                 (list 10 x0 y0) (list 10 x1 y0) (list 10 x1 y1) (list 10 x0 y1))))
(defun review-note (x y h s lay)
  (entmake (list '(0 . "TEXT") '(100 . "AcDbEntity") (cons 8 lay) '(100 . "AcDbText") (list 10 x y 0.0) (cons 40 h) (cons 1 s) '(7 . "Standard"))))
(defun add-line (x0 y0 x1 y1 lay)
  (entmake (list '(0 . "LINE") '(100 . "AcDbEntity") (cons 8 lay) '(100 . "AcDbLine") (list 10 x0 y0 0.0) (list 11 x1 y1 0.0))))

;; ---------- survey: dump entities to a pipe-separated text file ----------
;; handle|type|layer|space(0=model,1=paper)|xmin,ymin,xmax,ymax|name|attrs|text
(defun hl-pts (ed / pts item)
  (setq pts nil)
  (foreach item ed (if (member (car item) '(10 11 12 13 14 15)) (if (= (type (cdr item)) 'LIST) (setq pts (cons (cdr item) pts)))))
  pts)
(defun hl-bbox (ed / pts xs ys)
  (setq pts (hl-pts ed))
  (if pts (progn (setq xs (mapcar 'car pts) ys (mapcar 'cadr pts))
                 (strcat (rtos (apply 'min xs) 2 2) "," (rtos (apply 'min ys) 2 2) "," (rtos (apply 'max xs) 2 2) "," (rtos (apply 'max ys) 2 2)))
          ",,,"))
(defun hl-row (en / ed ty nm av txt item attid at)
  (setq ed (entget en) ty (cdr (assoc 0 ed)) nm "" av "" txt "")
  (cond
    ((= ty "MULTILEADER")
     (foreach item ed
       (cond ((= (car item) 344) (setq nm (cdr (assoc 2 (entget (cdr item))))))
             ((= (car item) 330) (setq attid (cdr item)))
             ((= (car item) 302) (setq av (strcat av (if attid (cdr (assoc 2 (entget attid))) "?") "=" (cdr item) ";")))
             ((= (car item) 304) (setq txt (strcat txt (cdr item)))))))
    ((= ty "INSERT")
     (setq nm (cdr (assoc 2 ed)))
     (if (= (cdr (assoc 66 ed)) 1)
       (progn (setq at (entnext en))
         (while (and at (= (cdr (assoc 0 (entget at))) "ATTRIB"))
           (setq av (strcat av (cdr (assoc 2 (entget at))) "=" (cdr (assoc 1 (entget at))) ";"))
           (setq at (entnext at))))))
    ((member ty '("TEXT" "MTEXT" "DIMENSION" "ATTDEF"))
     (foreach item ed (if (member (car item) '(1 3)) (setq txt (strcat (cdr item) txt))))
     (if (= ty "DIMENSION") (setq nm (cdr (assoc 3 ed)))))
    ((= ty "ACAD_TABLE") (setq nm "TABLE"))
    ((= ty "VIEWPORT") (setq nm (strcat "vp" (itoa (cdr (assoc 69 ed))))))
    (T nil))
  (strcat (cdr (assoc 5 ed)) "|" ty "|" (cdr (assoc 8 ed)) "|" (itoa (if (cdr (assoc 67 ed)) (cdr (assoc 67 ed)) 0)) "|"
          (hl-bbox ed) "|" (if nm nm "") "|" av "|" (hl-clean txt)))
(defun hl-clean (s / i c out)         ; strip newlines / pipes so one entity = one row
  (setq out "" i 1)
  (repeat (strlen s)
    (setq c (substr s i 1))
    (setq out (strcat out (if (or (= c "\n") (= c "\r") (= c "|")) " " c)))
    (setq i (1+ i)))
  out)
(defun hl-survey (path ty lay / f ss i n dz)
  (setq dz (getvar "DIMZIN")) (setvar "DIMZIN" 0)          ; rtos with leading zeros
  (setq f (open path "w") n 0)
  (setq ss (ssget "_X" (append (if (= ty "ALL") nil (list (cons 0 ty))) (list (cons 8 lay)))))
  (if ss (progn (setq i 0)
    (repeat (sslength ss) (write-line (hl-row (ssname ss i)) f) (setq i (1+ i) n (1+ n)))))
  (close f)
  (princ (strcat "\nSURVEY " ty " on layer " lay ": " (itoa n) " rows -> " path))
  (princ))

;; ---------- drawing info ----------
(defun hl-layout-names ( / d out item)   ; pure entget: walk the ACAD_LAYOUT dictionary (layoutlist is not defined in accoreconsole)
  (setq d (dictsearch (namedobjdict) "ACAD_LAYOUT") out nil)
  (foreach item d (if (= (car item) 3) (if (/= (strcase (cdr item)) "MODEL") (setq out (cons (cdr item) out)))))
  (reverse out))
(defun hl-layouts ( / )
  (foreach l (hl-layout-names) (princ (strcat "\nLAYOUT|" l))) (princ))
;; ---------- plot style tables (CTB/STB) ----------
;; the plot style of a layout lives in its LAYOUT object (AcDbPlotSettings group 7)
(defun hl-layout-obj (name / d) (setq d (dictsearch (namedobjdict) "ACAD_LAYOUT")) (if d (dictsearch (cdr (assoc -1 d)) name)))
(defun hl-ctb-report ( / ed)            ; CTBDIR|<folder>  then  CTB|<layout>|<style table>
  (princ (strcat "\nCTBDIR|" (vl-string-translate "\\" "/" (getenv "PrinterStyleSheetDir"))))
  (foreach l (hl-layout-names)
    (setq ed (hl-layout-obj l))
    (princ (strcat "\nCTB|" l "|" (if (and ed (assoc 7 ed)) (cdr (assoc 7 ed)) ""))))
  (princ))
(defun hl-set-ctb (lay ctb / ed)          ; for this plot only - the drawing is not saved by core.py plot
  (setq ed (hl-layout-obj lay))
  (if ed (entmod (if (assoc 7 ed) (subst (cons 7 ctb) (assoc 7 ed) ed) (append ed (list (cons 7 ctb))))))
  (hl-log (strcat "CTB " ctb) lay (if ed T nil)))
(defun hl-info ( / ss cnt ty tbl r)
  (princ (strcat "\nPRODUCT|" (getvar "PRODUCT") " " (getvar "ACADVER")))
  (princ (strcat "\nDWG|" (getvar "DWGPREFIX") (getvar "DWGNAME")))
  (princ (strcat "\nINSUNITS|" (itoa (getvar "INSUNITS")) "  (1=in 2=ft 4=mm 6=m 0=unitless)"))
  (princ (strcat "\nDIMSCALE|" (rtos (getvar "DIMSCALE") 2 2) "  LTSCALE|" (rtos (getvar "LTSCALE") 2 2)))
  (hl-layouts)
  (setq cnt nil ss (ssget "_X"))
  (if ss (progn (setq r 0)
    (repeat (sslength ss)
      (setq ty (cdr (assoc 0 (entget (ssname ss r)))))
      (if (assoc ty cnt) (setq cnt (subst (cons ty (1+ (cdr (assoc ty cnt)))) (assoc ty cnt) cnt)) (setq cnt (cons (cons ty 1) cnt)))
      (setq r (1+ r)))))
  (princ (strcat "\nENTITIES|" (if ss (itoa (sslength ss)) "0")))
  (foreach c cnt (princ (strcat "\n  " (car c) "|" (itoa (cdr c)))))
  (setq tbl (tblnext "LAYER" T) r 0)
  (while tbl (setq r (1+ r)) (setq tbl (tblnext "LAYER")))
  (princ (strcat "\nLAYERS|" (itoa r)))
  (setq tbl (tblnext "BLOCK" T))
  (while tbl
    (if (= (logand (cdr (assoc 70 tbl)) 4) 4)
      (princ (strcat "\nXREF|" (cdr (assoc 2 tbl)) "|" (if (assoc 1 tbl) (cdr (assoc 1 tbl)) "") "|" (if (= (logand (cdr (assoc 70 tbl)) 32) 32) "resolved" "NOT-resolved"))))
    (setq tbl (tblnext "BLOCK")))
  (princ))

(princ "\nHL-LIB LOADED")
(princ)
