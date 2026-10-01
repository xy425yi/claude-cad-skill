# dynblock — .NET helper for accoreconsole (full AutoCAD)

accoreconsole has no ActiveX, so plain LISP cannot switch a dynamic block's visibility state, stretch a
parameter, or edit a table through the AutoCAD API. Full AutoCAD's console *can* `NETLOAD` a .NET
plug-in; this one exposes those APIs to LISP. `core.py run … --dyn` loads it for you.
(AutoCAD LT has no .NET API and cannot load it.)

## Dynamic blocks (`Dyn.cs`)

```lisp
(dynget "A2220")                          ; (("Visibility1" . "Name only") ("Distance1" . 12.0) ...)
(dynallowed "A2220" "Visibility1")        ; ("Name only" "Name + finish" ...)
(dynset "A2220" "Visibility1" "Name + finish")   ; T  (numbers for distance / angle / flip)
(dynreset "A2220")                        ; back to the definition's defaults (also re-syncs ATTRIB positions)
(dynupdate "ROOM-TAG")                    ; after entmod-ing the DEFINITION's geometry: rebuild every *U
                                          ; representation (what saving in BEDIT does)
(xrefpath "X-BASE" "..\\Ref\\X-BASE.dwg")  ; set an xref's saved path (-XREF _P chokes on spaces)
```

Attribute positions are per instance: after a state switch, move / refill ATTRIBs with entmod.
`dynupdate` / `dynreset` put ATTRIBs back at their ATTDEF positions, so re-apply your moves after it.

## Tables (`Tbl.cs`)

See `reference/table-edit.md`.

## Rebuilding

`bin/dynblock.dll` is built against AutoCAD 2027 (.NET 10). For another release:

```
dotnet build -c Release -p:AcadDir="C:/Program Files/Autodesk/AutoCAD 2026"
```

Match the target framework in `dynblock.csproj` to that AutoCAD: 2025 / 2026 → `net8.0-windows`,
2027 → `net10.0-windows`. You need the matching .NET SDK.
