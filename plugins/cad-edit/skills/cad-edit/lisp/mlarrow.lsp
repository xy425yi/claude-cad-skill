(defun ml-arrow (h ax ay / ed out inll done)
  (setq ed (entget (handent h)) out nil inll nil done nil)
  (foreach x ed
    (cond ((and (= (car x) 304) (= (cdr x) "LEADER_LINE{")) (setq inll T) (setq out (cons x out)))
          ((and inll (not done) (= (car x) 10)) (setq out (cons (list 10 ax ay 0.0) out)) (setq done T))
          (T (setq out (cons x out)))))
  (entmod (reverse out))
  (princ (strcat "\nARROW|" h "|" (if done "OK" "FAIL"))))
