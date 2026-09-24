;; Revision clouds as closed calligraphy LWPOLYLINEs (same look as REVCLOUD style "Calligraphy").
;; All arcs in a set have the same chord; polygon must be CCW so arcs bulge outward. Coordinates = paper inches
;; (run in the layout) or model units (then scale *rc-chord* by the viewport scale).
;; Set these to match the office's existing clouds (entget one first) before calling:
(setq *rc-chord* 0.25)
(setq *rc-bulge* 0.520567)
(setq *rc-width* 0.1)
(setq *rc-tag-block* "REV-DELTA")
(setq *rc-tag-scale* 1.0)
(setq *rc-tag-attr* "REVISION")
(setq *rc-rev* "1")
(setq *rc-tag-dx* 0.36 *rc-tag-dy* 0.08)
;; *rc-chord* arc chord | *rc-bulge* arc bulge | *rc-width* end width = this x chord (start width 0)
;; *rc-tag-block* delta block (must exist in the drawing; -WBLOCK it from a sheet that has one, then -INSERT)
;; *rc-tag-scale* delta scale | *rc-tag-attr* attribute holding the number | *rc-rev* number written
;; *rc-tag-dx* / *rc-tag-dy* delta offset from the cloud corner (outside)

(defun rc-side (pts a b n / i) (setq i 0) (while (< i n) (setq pts (cons (list (+ (car a) (* (/ (- (car b) (car a)) n) i)) (+ (cadr a) (* (/ (- (cadr b) (cadr a)) n) i))) pts)) (setq i (1+ i))) pts)
;; (revpoly (list p1 p2 ...) "LAYER") -> cloud along any CCW polygon; each side gets the whole number of arcs closest to *rc-chord*
(defun revpoly (poly lay / pts n i a b l d w)
  (setq pts nil n (length poly) i 0 w (* *rc-width* *rc-chord*))
  (while (< i n) (setq a (nth i poly) b (nth (rem (1+ i) n) poly) d (distance a b))
    (setq pts (rc-side pts a b (max 1 (fix (+ 0.5 (/ d *rc-chord*)))))) (setq i (1+ i)))
  (setq pts (reverse pts))
  (setq l (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 lay) (cons 100 "AcDbPolyline") (cons 90 (length pts)) (cons 70 1)))
  (foreach p pts (setq l (append l (list (cons 10 p) (cons 40 0.0) (cons 41 w) (cons 42 *rc-bulge*)))))
  (entmake l) (princ (strcat "\nCLOUD|" (cdr (assoc 5 (entget (entlast)))))) (entlast))
;; (revcloud x0 y0 x1 y1 "LAYER") -> rectangular cloud
(defun revcloud (x0 y0 x1 y1 lay) (revpoly (list (list x0 y0) (list x1 y0) (list x1 y1) (list x0 y1)) lay))
;; (revtag x y "LAYER") -> insert the delta block and fill its revision attribute
(defun revtag (x y lay / e a ed)
  (setvar "ATTREQ" 0) (setvar "CLAYER" lay) (setvar "OSMODE" 0)
  (command "_.-INSERT" *rc-tag-block* (strcat (rtos x 2 4) "," (rtos y 2 4)) (rtos *rc-tag-scale* 2 4) (rtos *rc-tag-scale* 2 4) "0")
  (setq e (entlast) a (entnext e))
  (while (and a (= (cdr (assoc 0 (entget a))) "ATTRIB")) (setq ed (entget a)) (if (= (cdr (assoc 2 ed)) *rc-tag-attr*) (entmod (subst (cons 1 *rc-rev*) (assoc 1 ed) ed))) (setq a (entnext a)))
  (entupd e) (setvar "CLAYER" "0") (princ (strcat "\nTAG|" (cdr (assoc 5 (entget e))))) e)
;; (cloudtag x0 y0 x1 y1 "LAYER" "TR") -> rectangular cloud + delta outside the given corner: "TR" | "TL" | "BR" | "BL"
(defun cloudtag (x0 y0 x1 y1 lay side)
  (revcloud x0 y0 x1 y1 lay)
  (cond ((= side "TL") (revtag (- x0 *rc-tag-dx*) (- y1 *rc-tag-dy*) lay))
        ((= side "BL") (revtag (- x0 *rc-tag-dx*) (+ y0 0.02) lay))
        ((= side "BR") (revtag (+ x1 *rc-tag-dx*) (+ y0 0.02) lay))
        (T (revtag (+ x1 *rc-tag-dx*) (- y1 *rc-tag-dy*) lay))))
;; (clear-rev "LAYER" "LAYOUT") -> delete everything on a cloud layer in one layout (to regenerate a round)
(defun clear-rev (lay layout / ss i) (setq ss (ssget "_X" (list (cons 8 lay) (cons 410 layout))))
  (if ss (progn (setq i 0) (while (< i (sslength ss)) (entdel (ssname ss i)) (setq i (1+ i))) (princ (strcat "\nCLEARED|" (itoa (sslength ss)))))))
;; (find-clouds) -> list LWPOLYLINEs whose segments are > 80% arcs: leftover clouds from earlier rounds
(defun find-clouds (/ ss i e ed nb nv)
  (setq ss (ssget "_X" (list (cons 0 "LWPOLYLINE"))) i 0)
  (if ss (while (< i (sslength ss))
    (setq e (ssname ss i) ed (entget e) nb 0 nv 0)
    (foreach x ed (if (= (car x) 42) (progn (setq nv (1+ nv)) (if (/= (cdr x) 0.0) (setq nb (1+ nb))))))
    (if (and (> nv 4) (> (/ (float nb) nv) 0.8))
      (princ (strcat "\nCLOUD?|" (cdr (assoc 5 ed)) "|" (cdr (assoc 8 ed)) "|" (cdr (assoc 410 ed)))))
    (setq i (1+ i))))
  (princ))
