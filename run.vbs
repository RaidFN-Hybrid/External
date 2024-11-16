Set oShell = CreateObject ("Wscript.Shell") 
Dim strArgs
strArgs = "cmd /c FortniteChecker.bat"
oShell.Run strArgs, 0, false