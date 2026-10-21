' Runs start.sh in the background with no window. A shortcut to this file in the
' Windows Startup folder makes the subtitle page start when you log in.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run """C:\Program Files\Git\bin\bash.exe"" -l """ & folder & "\start.sh""", 0, False
