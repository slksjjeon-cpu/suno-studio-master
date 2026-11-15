Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = strPath
' Run web_launcher in hidden background window (0 = hide)
WshShell.Run "cmd /c python web_launcher.py", 0, False
