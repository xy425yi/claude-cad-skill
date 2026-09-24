// Table helpers for FULL AutoCAD's accoreconsole (loaded with dynblock.dll):
//   (tblrows "B096D")                    -> number of rows
//   (tblrowh "B096D" 1)                  -> row height (drawing units)
//   (tblinsrow "B096D" 2 1)              -> insert one row at index 2, format inherited from row 1; T
//   (tblset  "B096D" 2 0 "AL.2")         -> set cell text (keeps cell style); T
//   (tblget  "B096D" 2 0)                -> cell text
//   (tblcols "B096D") -> number of columns ; (tblcolw "B096D" 0 [w]) -> get / set column width
//   (tbldelcols "B096D" 4 3) -> delete 3 columns starting at 4; T
//   (tblsetval "B096D" r c "txt") -> set the cell VALUE (data) as well as its text; T
//   (tblregen "B096D")                   -> rebuild the table graphics block (call after edits, before saving); T
using System;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;

public class Tbl
{
    static TypedValue[] A(ResultBuffer rb) { return rb == null ? new TypedValue[0] : rb.AsArray(); }
    static Table Get(Transaction tr, string h, OpenMode m)
    {
        var db = HostApplicationServices.WorkingDatabase;
        var id = db.GetObjectId(false, new Handle(Convert.ToInt64(h, 16)), 0);
        return tr.GetObject(id, m) as Table;
    }
    static int I(TypedValue v) { return Convert.ToInt32(v.Value); }

    [LispFunction("tblrows")]
    public static object Rows(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction()) { var t = Get(tr, a[0].Value.ToString(), OpenMode.ForRead); tr.Commit(); return t.Rows.Count; }
    }
    [LispFunction("tblrowh")]
    public static object RowH(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction()) { var t = Get(tr, a[0].Value.ToString(), OpenMode.ForRead); var h = t.Rows[I(a[1])].Height; tr.Commit(); return h; }
    }
    [LispFunction("tblinsrow")]
    public static object InsRow(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            int at = I(a[1]), from = I(a[2]);
            var h = t.Rows[from].Height;
            t.InsertRowsAndInherit(at, from, 1);
            t.Rows[at].Height = h;
            t.GenerateLayout(); t.RecomputeTableBlock(true); tr.Commit(); return true;
        }
    }
    [LispFunction("tblset")]
    public static object Set(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            t.Cells[I(a[1]), I(a[2])].TextString = a[3].Value.ToString();
            t.GenerateLayout(); tr.Commit(); return true;
        }
    }
    [LispFunction("tblget")]
    public static object GetText(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction()) { var t = Get(tr, a[0].Value.ToString(), OpenMode.ForRead); var s = t.Cells[I(a[1]), I(a[2])].TextString; tr.Commit(); return s; }
    }

    [LispFunction("tblregen")]
    public static object Regen(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            t.GenerateLayout(); t.RecomputeTableBlock(true); tr.Commit(); return true;
        }
    }

    [LispFunction("tblcols")]
    public static object Cols(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction()) { var t = Get(tr, a[0].Value.ToString(), OpenMode.ForRead); tr.Commit(); return t.Columns.Count; }
    }
    [LispFunction("tblcolw")]
    public static object ColW(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), a.Length > 2 ? OpenMode.ForWrite : OpenMode.ForRead);
            int c = I(a[1]);
            if (a.Length > 2) { t.Columns[c].Width = Convert.ToDouble(a[2].Value); t.GenerateLayout(); t.RecomputeTableBlock(true); }
            var w = t.Columns[c].Width; tr.Commit(); return w;
        }
    }
    [LispFunction("tbldelcols")]
    public static object DelCols(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            t.DeleteColumns(I(a[1]), I(a[2])); t.GenerateLayout(); t.RecomputeTableBlock(true); tr.Commit(); return true;
        }
    }

    [LispFunction("tblsetval")]
    public static object SetVal(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            var cell = t.Cells[I(a[1]), I(a[2])]; var s = a[3].Value.ToString();
            cell.Value = s; cell.TextString = s;
            t.GenerateLayout(); tr.Commit(); return true;
        }
    }

    [LispFunction("tbldelrows")]
    public static object DelRows(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            t.DeleteRows(I(a[1]), I(a[2])); t.GenerateLayout(); t.RecomputeTableBlock(true); tr.Commit(); return true;
        }
    }

    [LispFunction("tblsetrowh")]
    public static object SetRowH(ResultBuffer rb)
    {
        var a = A(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var t = Get(tr, a[0].Value.ToString(), OpenMode.ForWrite);
            t.Rows[I(a[1])].Height = Convert.ToDouble(a[2].Value); t.GenerateLayout(); t.RecomputeTableBlock(true);
            var h = t.Rows[I(a[1])].Height; tr.Commit(); return h;
        }
    }
}
