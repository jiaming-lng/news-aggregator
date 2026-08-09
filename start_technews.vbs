' TechNews Auto-Start Script
' Launches Flask server in background (no console window)
' Place a copy of this file in the Startup folder for auto-start on login

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Workbuddy.Web\8.4\news-aggregator\backend"
WshShell.Run """C:\Users\22867\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"" ""D:\Workbuddy.Web\8.4\news-aggregator\backend\app.py""", 0, False
