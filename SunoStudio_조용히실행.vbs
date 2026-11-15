Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = strPath
' Run Python in hidden background window (0 = hide)
WshShell.Run "cmd /c python app.py", 0, False

WScript.Sleep 1500
WshShell.Run "http://127.0.0.1:8000"
