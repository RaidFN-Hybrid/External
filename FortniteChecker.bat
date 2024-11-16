@echo off

color 1

title Fortnite Checker

:status

tasklist /fi "IMAGENAME eq FortniteLauncher.exe" 2>nul | find /i "FortniteLauncher.exe" >nul

if errorlevel 1 (
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul
)

goto status
