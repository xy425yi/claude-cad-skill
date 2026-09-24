;; (text-census)  -> one line per  TYPE | space | layer | text style | height  with a count, so a new note / tag /
;; title copies the style that is already dominant in THIS drawing instead of guessing.
;; space: M = model, P:<layout>.  MULTILEADER: style column = the text style its context uses.
(defun tc-mlstyle (ed / d n r)
  ;; mleader style name = key of the ACAD_MLEADERSTYLE dictionary entry that owns the 340 object
  (setq d (dictsearch (namedobjdict) "ACAD_MLEADERSTYLE") n (cdr (assoc 340 ed)) r "?")
  (if (and d n) (foreach x d (if (and (= (car x) 3)) (setq last3 (cdr x))) (if (and (= (car x) 350) (eq (cdr x) n)) (setq r last3))))
  r)
(defun tc-key (ed / ty sp lay st h ctx tso)
  (setq ty (cdr (assoc 0 ed)) lay (cdr (assoc 8 ed)))
  (setq sp (if (= (cdr (assoc 67 ed)) 1) (strcat "P:" (cdr (assoc 410 ed))) "M"))
  (cond
    ((member ty '("MTEXT" "TEXT" "ATTDEF")) (setq st (cdr (assoc 7 ed)) h (cdr (assoc 40 ed))))
    ((= ty "MULTILEADER") (setq ctx (cdr (member (assoc 300 ed) ed)) tso (cdr (assoc 340 ctx))
                           st (if tso (cdr (assoc 2 (entget tso))) "?") h (cdr (assoc 42 ctx))))
    ((= ty "DIMENSION") (setq st (cdr (assoc 3 ed)) h 0.0)))
  (if st (strcat ty "|" sp "|" (if lay lay "?") "|" (if st st "?") "|" (rtos (if h h 0.0) 2 3)) nil))
(defun text-census ( / ss i ed k tbl pair)
  (setq ss (ssget "_X" '((0 . "MTEXT,TEXT,ATTDEF,MULTILEADER,DIMENSION"))) tbl nil i 0)
  (if ss (while (< i (sslength ss))
    (setq ed (entget (ssname ss i)) k (tc-key ed))
    (if k (progn (setq pair (assoc k tbl)) (if pair (setq tbl (subst (cons k (1+ (cdr pair))) pair tbl)) (setq tbl (cons (cons k 1) tbl)))))
    (setq i (1+ i))))
  (foreach p tbl (princ (strcat "\nCENSUS|" (car p) "|" (itoa (cdr p)))))
  (princ "\nCENSUS-DONE") (princ))
(defun style-font (name / s) (setq s (tblsearch "STYLE" name)) (if s (cdr (assoc 3 s)) "?"))
