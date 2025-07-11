Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "taskkill /f /im python.exe /im ngrok.exe", 0, True
MsgBox "Servidor y Ngrok detenidos correctamente", vbInformation, "Servidor Detenido"