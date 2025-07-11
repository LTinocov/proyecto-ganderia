Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Ejecutar servidor Flask en segundo plano
WshShell.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "python app.py", 0, False

' Esperar 3 segundos para asegurar inicio del servidor
WScript.Sleep 3000

' Ejecutar ngrok en segundo plano
WshShell.Run "ngrok http 5000", 0, False

' Esperar 5 segundos para ngrok
WScript.Sleep 5000

' Obtener URL de ngrok
On Error Resume Next
Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "GET", "http://localhost:4040/api/tunnels", False
http.Send

If Err.Number = 0 And http.Status = 200 Then
    Set json = ParseJson(http.responseText)
    ngrokUrl = json("tunnels")(0)("public_url")
    
    ' Mostrar mensaje final
    MsgBox "Servidor iniciado exitosamente!" & vbCrLf & vbCrLf & _
           "Enlace local: http://localhost:5000" & vbCrLf & _
           "Enlace ngrok: " & ngrokUrl, vbInformation, "Servidor Activo"
Else
    MsgBox "Error obteniendo URL de Ngrok", vbCritical, "Error"
End If

' Función para parsear JSON (Windows 10+)
Function ParseJson(json)
    Set sc = CreateObject("MSScriptControl.ScriptControl")
    sc.Language = "JScript"
    Set ParseJson = sc.Eval("(" + json + ")")
End Function