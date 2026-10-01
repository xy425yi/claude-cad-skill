// dynblock: read / set dynamic-block properties (visibility states, lookups, distances, flips) from LISP
// inside accoreconsole of FULL AutoCAD.  Usage from LISP after (command "_.NETLOAD" "<path>/dynblock.dll"):
//   (dynget "A2220")                           -> (("Visibility1" . "RoomName w/ Clng Height") ("Position1 X" . 0.0) ...)
//   (dynallowed "A2220" "Visibility1")          -> ("RoomName" "RoomName w/ Finish" ...)
//   (dynset "A2220" "Visibility1" "RoomName w/4Box")   -> T / nil    (numbers accepted for distance/angle properties)
using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;

public class Dyn
{
    static List<TypedValue> Args(ResultBuffer rb)
    {
        var l = new List<TypedValue>();
        if (rb != null) foreach (var tv in rb) l.Add(tv);
        return l;
    }
    static BlockReference Ref(Transaction tr, Database db, string handle, OpenMode mode)
    {
        var h = new Handle(Convert.ToInt64(handle, 16));
        var id = db.GetObjectId(false, h, 0);
        return tr.GetObject(id, mode) as BlockReference;
    }
    static void Log(string s) { Application.DocumentManager.MdiActiveDocument.Editor.WriteMessage("\n" + s); }

    [LispFunction("dynget")]
    public static ResultBuffer DynGet(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase; var outp = new ResultBuffer();
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var br = Ref(tr, db, a[0].Value.ToString(), OpenMode.ForRead);
            if (br == null || !br.IsDynamicBlock) { Log("DYNGET " + a[0].Value + " not a dynamic block"); return null; }
            foreach (DynamicBlockReferenceProperty p in br.DynamicBlockReferencePropertyCollection)
            {
                outp.Add(new TypedValue((int)LispDataType.ListBegin));
                outp.Add(new TypedValue((int)LispDataType.Text, p.PropertyName));
                outp.Add(new TypedValue((int)LispDataType.DottedPair));
                if (p.Value is string) outp.Add(new TypedValue((int)LispDataType.Text, (string)p.Value));
                else if (p.Value is Autodesk.AutoCAD.Geometry.Point3d) outp.Add(new TypedValue((int)LispDataType.Point3d, (Autodesk.AutoCAD.Geometry.Point3d)p.Value));
                else if (p.Value is Autodesk.AutoCAD.Geometry.Point2d) { var q = (Autodesk.AutoCAD.Geometry.Point2d)p.Value; outp.Add(new TypedValue((int)LispDataType.Point2d, q)); }
                else if (p.Value is IConvertible) outp.Add(new TypedValue((int)LispDataType.Double, Convert.ToDouble(p.Value)));
                else outp.Add(new TypedValue((int)LispDataType.Text, p.Value.ToString()));
                outp.Add(new TypedValue((int)LispDataType.ListEnd));
            }
            tr.Commit();
        }
        return outp;
    }

    [LispFunction("dynallowed")]
    public static ResultBuffer DynAllowed(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase; var outp = new ResultBuffer();
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var br = Ref(tr, db, a[0].Value.ToString(), OpenMode.ForRead);
            if (br == null || !br.IsDynamicBlock) return null;
            foreach (DynamicBlockReferenceProperty p in br.DynamicBlockReferencePropertyCollection)
                if (p.PropertyName == a[1].Value.ToString())
                    foreach (var v in p.GetAllowedValues())
                        outp.Add(v is string ? new TypedValue((int)LispDataType.Text, (string)v) : new TypedValue((int)LispDataType.Double, Convert.ToDouble(v)));
            tr.Commit();
        }
        return outp;
    }

    [LispFunction("dynreset")]          // (dynreset "A2220") -> reset the reference to the block's default state / parameter values
    public static object DynReset(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var br = Ref(tr, db, a[0].Value.ToString(), OpenMode.ForWrite);
            if (br == null || !br.IsDynamicBlock) return null;
            br.ResetBlock(); tr.Commit();
        }
        Log("DYNRESET " + a[0].Value + " OK"); return true;
    }

    [LispFunction("dynupdate")]         // (dynupdate "00-RMTAG-ANNO") -> after editing the definition's geometry with entmod, rebuild every *U representation
    public static object DynUpdate(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
            string name = a[0].Value.ToString();
            if (!bt.Has(name)) { Log("DYNUPDATE no block " + name); return null; }
            var btr = (BlockTableRecord)tr.GetObject(bt[name], OpenMode.ForWrite);
            if (!btr.IsDynamicBlock) { Log("DYNUPDATE " + name + " is not dynamic"); return null; }
            btr.UpdateAnonymousBlocks(); tr.Commit();
        }
        Log("DYNUPDATE " + a[0].Value + " OK"); return true;
    }

    [LispFunction("dynset")]
    public static object DynSet(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase; bool ok = false;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var br = Ref(tr, db, a[0].Value.ToString(), OpenMode.ForWrite);
            if (br == null || !br.IsDynamicBlock) { Log("DYNSET " + a[0].Value + " not a dynamic block"); return null; }
            string name = a[1].Value.ToString();
            foreach (DynamicBlockReferenceProperty p in br.DynamicBlockReferencePropertyCollection)
            {
                if (p.PropertyName != name || p.ReadOnly) continue;
                try
                {
                    object cur = p.Value;
                    if (cur is string) p.Value = a[2].Value.ToString();
                    else if (cur is short) p.Value = Convert.ToInt16(a[2].Value);
                    else if (cur is int) p.Value = Convert.ToInt32(a[2].Value);
                    else if (cur is Autodesk.AutoCAD.Geometry.Point3d && a[2].Value is Autodesk.AutoCAD.Geometry.Point3d) p.Value = a[2].Value;
                    else p.Value = Convert.ToDouble(a[2].Value);
                    ok = true;
                }
                catch (System.Exception ex) { Log("DYNSET " + a[0].Value + " " + name + " FAIL " + ex.Message); }
            }
            tr.Commit();
        }
        Log("DYNSET " + a[0].Value + " " + a[1].Value + "=" + a[2].Value + (ok ? " OK" : " FAIL (no such property)"));
        return ok ? (object)true : null;
    }
    [LispFunction("xrefpath")]          // (xrefpath "X_BASE 1ST FLOOR DOB" "..\..\00 Ref\X_BASE 1ST FLOOR DOB.dwg") -> set an xref's stored path (-XREF Path chokes on spaces in accoreconsole)
    public static object XrefPath(ResultBuffer rb)
    {
        var a = Args(rb); var db = HostApplicationServices.WorkingDatabase; bool ok = false;
        using (var tr = db.TransactionManager.StartTransaction())
        {
            var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
            string name = a[0].Value.ToString();
            if (!bt.Has(name)) { Log("XREFPATH no block " + name); return null; }
            var btr = (BlockTableRecord)tr.GetObject(bt[name], OpenMode.ForWrite);
            if (!btr.IsFromExternalReference) { Log("XREFPATH " + name + " is not an xref"); return null; }
            btr.PathName = a[1].Value.ToString();
            ok = true;
            tr.Commit();
        }
        Log("XREFPATH " + a[0].Value + " -> " + a[1].Value + (ok ? " OK" : " FAIL"));
        return ok ? (object)true : null;
    }
}
