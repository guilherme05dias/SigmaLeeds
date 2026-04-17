Set WshShell = CreateObject("WScript.Shell")
' 0 significa ocultar a janela completamente (rodar em background)
WshShell.Run chr(34) & "C:\Users\user\Desktop\SigmaLeeds\SigmaHub.bat" & Chr(34), 0
Set WshShell = Nothing
