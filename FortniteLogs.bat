@echo off

color 1

title Fortnite Logs

:showlogs

timeout /t 60 /nobreak >nul

type %localappdata%\FortniteGame\Saved\Logs\FortniteGame.log

goto showlogs

:disableproxy

tasklist /fi "IMAGENAME eq FortniteLauncher.exe" 2>NUL | find /i "FortniteLauncher.exe" >nul

if errorlevel 1 (
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul
)

goto disableproxy
