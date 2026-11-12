Option Explicit

Dim shell, fso, home, pythonExe, appDir, appScript, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

home = shell.ExpandEnvironmentStrings("%USERPROFILE%")
pythonExe = fso.BuildPath(home, "AppData\Local\wechat-chat-export\venv\Scripts\pythonw.exe")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
appScript = fso.BuildPath(appDir, "wechat_export_gui.py")

If Not fso.FileExists(pythonExe) Then
    MsgBox "Python environment not found:" & vbCrLf & pythonExe, 16, "WeChat Exporter"
    WScript.Quit 1
End If

If Not fso.FileExists(appScript) Then
    MsgBox "GUI script not found:" & vbCrLf & appScript, 16, "WeChat Exporter"
    WScript.Quit 1
End If

command = Chr(34) & pythonExe & Chr(34) & " " & Chr(34) & appScript & Chr(34)
shell.Run command, 1, False
