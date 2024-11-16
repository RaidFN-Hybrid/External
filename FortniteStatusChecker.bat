@echo off

color 1

title Fortnite Status Checker

:logs

type %localappdata%\FortniteGame\Saved\Logs\FortniteGame.log

tasklist /fi "IMAGENAME eq FortniteLauncher.exe" 2>NUL | find /i "FortniteLauncher.exe" >nul

if errorlevel 1 (
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul
)

goto logs
