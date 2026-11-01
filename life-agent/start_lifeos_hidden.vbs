' Start de Life OS-server onzichtbaar op de achtergrond (voor autostart bij inloggen).
' Output komt in lifeos.log in deze map. Stoppen: Taakbeheer -> python.exe beeindigen,
' of verwijder de snelkoppeling "Life OS" uit de Opstarten-map (Win+R -> shell:startup).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
map = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = map
sh.Run "cmd /c python server.py --no-browser > lifeos.log 2>&1", 0, False
